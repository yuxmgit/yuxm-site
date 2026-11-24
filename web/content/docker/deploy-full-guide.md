---
title: "第 1 章：本站部署实录——从裸机到全栈上线，每一条命令都带注释"
description: "腾讯云 2C4G 单机部署完整复刻：服务器初始化、生产 compose 逐行拆解、Redis Cluster 3主3从与 MySQL 主从的配置详解与踩坑，全部命令可直接复制执行。"
category: docker
series: deploy-in-action
seriesOrder: 1
tags: ["Docker", "部署", "Redis Cluster", "MySQL 主从", "运维"]
date: 2026-11-24
sourceRepo: https://github.com/yuxiangming/yuxm-site
---

> 本文是本站（yuxm.site）真实部署过程的完整复刻，环境为腾讯云 CVM 2C4G / Ubuntu。所有命令均为实际执行过的版本，**每行都有注释说明它在干什么、为什么这么干**。涉及文件：`deploy/docker-compose.yml`（生产）、`deploy/docker-compose.demo.yml`（集群演示）、`deploy/demo/mysql/`（主从配置）。

## 1. 先看全景：两条部署线

```
生产线（一直跑）：  nginx -> web -> api -> mysql + redis + jenkins
演示线（按需起）：  Redis Cluster 3主3从（7001-7006）+ MySQL 主从（3307/3308）
```

- **生产线**解决"网站怎么跑起来"：6 个容器组成全栈，配置在 `deploy/docker-compose.yml`
- **演示线**解决"集群怎么搭、怎么验"：与生产完全隔离，用完可随时销毁，配置在 `deploy/docker-compose.demo.yml`（用 `profiles` 分组，不影响生产）

两条线在同一台 3.7G 内存的机器上共存：生产约占 1.5G，Redis 6 节点约 300M，MySQL 双实例约 800M。

## 2. 服务器初始化（一次性）

```bash
# 系统更新到最新（补内核漏洞）
sudo apt update && sudo apt upgrade -y

# 时区设为上海，日志时间戳才和本地对得上
sudo timedatectl set-timezone Asia/Shanghai

# 官方脚本安装 Docker（腾讯云内网走 mirror 加速）
curl -fsSL https://get.docker.com | sudo sh

# 设置开机自启并立即启动
sudo systemctl enable --now docker

# 配置 Docker 镜像加速（腾讯云内网 mirror，拉镜像快一个数量级）
sudo mkdir -p /etc/docker
cat <<'EOF' | sudo tee /etc/docker/daemon.json
{ "registry-mirrors": ["https://mirror.ccs.tencentyun.com"] }
EOF
sudo systemctl restart docker     # 重启守护进程使加速生效
```

## 3. 拉代码与环境变量（核心安全步骤）

```bash
# 统一部署目录：所有东西都在 /opt/yuxm-site 下
sudo mkdir -p /opt/yuxm-site && cd /opt/yuxm-site

# 从 GitHub 拉仓库（"."表示克隆到当前目录）
sudo git clone https://github.com/yuxmgit/yuxm-site.git .

# 生成环境变量文件：compose 和 api 容器共用同一份 deploy/.env
cp .env.example deploy/.env

# 必须手改的 4 项（都是弱默认值，不改等于裸奔）：
vim deploy/.env
#   JWT_SECRET          登录令牌签名密钥，>=32位随机串，泄露=任何人可伪造登录态
#   MYSQL_ROOT_PASSWORD MySQL root 密码
#   MYSQL_PASSWORD      业务账号 yuxm 的密码（api 容器用这个连库）
#   REDIS_PASSWORD      Redis 密码（黑名单/版本号/限流都在里面）
```

> 生成强随机串的方法：`openssl rand -hex 32`，跑四次把结果分别填进四项。

## 4. 生产全栈启动（compose 依赖链帮你排好顺序）

```bash
cd /opt/yuxm-site/deploy

# 一条命令拉起 6 个容器。
# compose 会按 healthcheck 依赖自动排序：
#   mysql/redis 先起（各自健康检查通过）-> api -> web -> nginx
# 中途任何一个 unhealthy，后面的容器不会启动，避免"起了一半"的烂状态
docker compose up -d

# 跟踪 api 和 web 的启动日志，看到 Uvicorn running / Nuxt ready 即成功（Ctrl+C 退出跟踪）
docker compose logs -f api web

# 健康检查：返回 {"code":0,...} 说明整条链路（nginx->api->mysql/redis）都通了
curl http://127.0.0.1/api/health

# 首次部署必做：创建管理员账号（幂等，重复执行无害）
docker compose exec api python -m app.seed
```

对应的 `docker-compose.yml` 关键配置逐行解读：

```yaml
mysql:
  healthcheck:                          # 每 10s 探活一次
    test: ["CMD", "mysqladmin", "ping", "-h", "127.0.0.1"]
  expose: ["3306"]                      # expose 只在 compose 内部网络开端口，
                                        # 绝不映射到宿主机（公网摸不到 MySQL）
  command: --character-set-server=utf8mb4   # 全库 utf8mb4，中文/emoji 不乱码

redis:
  command: redis-server --appendonly yes     # AOF 持久化：断电最多丢 1 秒
             --requirepass ${REDIS_PASSWORD} # 密码保护，容器网络内也加一道锁

api:
  depends_on:
    mysql: { condition: service_healthy }  # 等数据库真正可用才启动 api，
    redis: { condition: service_healthy }  # 避免"连不上库"的启动竞态

jenkins:
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock  # 流水线能直接操作宿主机 docker
  environment:
    JAVA_OPTS: -Xmx512m                    # 2C4G 机器，JVM 堆必须限死，否则挤垮业务
```

<!-- PART2 -->
## 5. Redis Cluster 3主3从：配置逐行拆解（重点）

演示集群由 `deploy/docker-compose.demo.yml` 定义。先启动 6 个节点，再一次性建集群：

```bash
cd /opt/yuxm-site/deploy

# 启动 6 个 Redis 节点（7001-7006）
docker compose -f docker-compose.demo.yml up -d

# 初始化集群：3 主（7001-7003）+ 每主 1 从（7004-7006）
# --profile init 是因为这个容器是"一次性"的，建完集群就没用了，
# 放在 profile 里避免每次 up -d 都重建它
docker compose -f docker-compose.demo.yml --profile init up redis-cluster-init -d

# 等 15 秒让节点完成握手后验证
docker exec yuxm-demo-redis-node1-1 redis-cli -p 7001 cluster info
# 必须看到：cluster_state:ok  cluster_slots_assigned:16384  cluster_known_nodes:6
```

### 5.1 节点配置：一段 printf 生成的 redis.conf

6 个节点共用一段配置模板（YAML 锚点 `x-redis-conf`），每个节点只差一个端口号：

```yaml
x-redis-conf: &redis-conf
  image: redis:7
  restart: unless-stopped
  network_mode: host          # ★ 关键决策 1：host 网络（后面解释为什么）
  command:
    - sh
    - -c
    - |
      # 按环境变量 REDIS_PORT 动态生成每个节点的配置文件：
      printf 'port %s\n                      # 节点服务端口（7001..7006）
              bind 127.0.0.1\n             # ★ 只监听回环：公网完全摸不到这些节点
              cluster-enabled yes\n        # 打开集群模式（不开就是普通单机 Redis）
              cluster-config-file nodes.conf\n  # 集群拓扑由节点自动维护
              cluster-node-timeout 5000\n  # 5 秒无响应即判"疑似下线"（故障转移的计时起点）
              appendonly yes\n             # AOF 持久化，断电不丢数据
              cluster-announce-ip 127.0.0.1\n      # ★ 告诉别的节点"来 127.0.0.1 找我"
              cluster-announce-port %s\n           # 告知服务端口
              cluster-announce-bus-port %s\n' \    # 告知总线端口 = 服务端口 + 10000
        "$$REDIS_PORT" "$$REDIS_PORT" "$$((REDIS_PORT + 10000))" > /tmp/redis.conf
      # $$ 是 compose 转义：文件里写 $REDIS_PORT 交给容器内 shell 展开
      exec redis-server /tmp/redis.conf   # 前台启动（容器要求前台进程）
```

**为什么必须 host 网络？** 这是本配置最核心的一课。`cluster-announce-ip 127.0.0.1` 的意思是"节点之间用 127.0.0.1 互相寻址"。这只在 host 网络模式下成立——6 个节点共享宿主机网络栈，7002 真的在"本机"上。如果 6 个节点各在独立容器网络里，节点 1 去 `MEET 127.0.0.1:7002` 时连到的是**它自己容器内部**的 7002（不存在）——集群握手永远失败，症状就是 `cluster_known_nodes:1` + `CLUSTERDOWN`。

**端口拓扑**（host 模式下直接监听宿主机端口）：

```
7001-7006    6 个节点服务端口（bind 127.0.0.1，仅本机可访问）
17001-17006  集群总线端口（节点间 gossip 通信：故障检测/选主/槽迁移）
             规律：总线端口 = 服务端口 + 10000，Redis 自动推导，无需手配
```

### 5.2 建集群：一条命令做了 5 件事

```bash
echo yes | redis-cli --cluster create \
  127.0.0.1:7001 127.0.0.1:7002 127.0.0.1:7003 \   # 前三个为 Master
  127.0.0.1:7004 127.0.0.1:7005 127.0.0.1:7006 \   # 后三个自动成为 Slave
  --cluster-replicas 1                              # 每个主配 1 个从
```

它内部依次完成：节点两两 `CLUSTER MEET` 握手 -> 分配 16384 个槽（0-5460 / 5461-10922 / 10923-16383 三等分）-> 为每个主选一个从 -> 询问确认（`echo yes` 自动应答）-> 打印分配方案。

### 5.3 验证：写数据看分片，杀主节点看自救

```bash
# 1) 写一个 key，看它被路由到哪个节点（-c 表示跟随 MOVED 重定向）
docker exec yuxm-demo-redis-node1-1 redis-cli -p 7001 -c set demo:key1 value-1

# 2) 查这个 key 属于哪个槽（CRC16(key) % 16384）
docker exec yuxm-demo-redis-node1-1 redis-cli -p 7001 cluster keyslot demo:key1
# -> 2914，落在主 7001 的 [0-5460] 区间

# 3) 【重头戏】直接 kill 主节点 7001，模拟宕机
docker stop yuxm-demo-redis-node1-1

# 4) 等 12 秒（cluster-node-timeout 5s + 从节点选举），看集群视角：
docker exec yuxm-demo-redis-node2-1 redis-cli -p 7002 cluster nodes
# 预期：7001 标记为 master,fail；它的从 7006 变成 master 并接管 0-5460 全部槽

# 5) 数据还在吗？从任意节点读：
docker exec yuxm-demo-redis-node2-1 redis-cli -p 7002 -c get demo:key1
# -> "value-1"  业务无感知，故障转移全程约 10 秒

# 6) 把 7001 启回来，它会自动降级为 7006 的从节点
docker start yuxm-demo-redis-node1-1
```

<!-- PART3 -->
## 6. MySQL 主从：配置逐行拆解（重点）

`docker-compose.demo.yml` 里两个 MySQL 容器 + `deploy/demo/mysql/` 下 4 个配置文件，构成全自动主从。

### 6.1 启动与自动初始化

```bash
# 启动主从（master 宿主机 3307 / replica 3308，容器内部都是 3306）
docker compose -f docker-compose.demo.yml --profile mysql up -d

# 首次启动要 60-90 秒（MySQL 初始化 + 从库自动配复制），等健康检查变绿：
docker compose -f docker-compose.demo.yml ps
```

### 6.2 主库配置 `master.cnf` 逐行注释

```ini
[mysqld]
server-id = 1                    # 复制拓扑中每个节点的唯一 ID，主从绝不能相同
log-bin = mysql-bin              # 开启二进制日志：所有写操作记录在这里，
                                 # 这是复制的"数据源"，从库就是重放它
binlog_format = ROW              # 记录"行变化"而非 SQL 语句，
                                 # 避免 NOW()/UUID() 这类函数在主从产生不同值
gtid_mode = ON                   # 全局事务 ID：每个事务有全局唯一编号
enforce_gtid_consistency = ON    # 禁止会产生不确定 GTID 的写法（GTID 安全的前提）
```

`gtid_mode=ON` 不是可选项——从库用了 `SOURCE_AUTO_POSITION=1`（自动定位），它依赖 GTID 知道"哪些事务我已经执行过"。只开主库不开从库会报 `ERROR 1777`（真实踩过）。

### 6.3 主库 init SQL `master/init/01-create-repl-user.sql`

```sql
-- 复制专用账号：专号专用，权限只给复制，不用 root 做复制
CREATE USER 'repl'@'%' IDENTIFIED BY 'repl123';
GRANT REPLICATION SLAVE ON *.* TO 'repl'@'%';   -- 仅复制权限，读库都不行
FLUSH PRIVILEGES;
```

这个文件放在 `/docker-entrypoint-initdb.d/` 挂载目录里——MySQL 官方镜像**只在数据卷为空的首次启动**执行它，之后重启不会重复执行（幂等由"首次"保证）。

### 6.4 从库配置 `replica.cnf` 逐行注释

```ini
[mysqld]
server-id = 2                    # 与主库不同的唯一 ID
relay-log = relay-bin            # 中继日志：先存下主库发来的 binlog，再由 SQL 线程重放
character-set-server = utf8mb4
# ★★★ 这里绝不能写 read_only / super_read_only！★★★
# Docker 首次初始化（设 root 密码、执行 init SQL）需要写权限，
# 配在 cnf 里会让初始化自己写不了自己：ERROR 1290，root 密码停留为空，复制不配置。
# 只读保护放到 init SQL 的最后一步用 SET GLOBAL 设置（见下）。
```

### 6.5 从库 init SQL `replica/init/01-configure-replica.sql`

```sql
-- 配置复制源：GTID 自动定位，不需要手动找 binlog 文件名和位置
CHANGE REPLICATION SOURCE TO
  SOURCE_HOST = 'mysql-master',        -- compose 服务名即容器网络 DNS，免写 IP
  SOURCE_PORT = 3306,                  -- 容器内部端口（不是宿主机的 3307）
  SOURCE_USER = 'repl',
  SOURCE_PASSWORD = 'repl123',
  SOURCE_AUTO_POSITION = 1,            -- GTID 自动定位：从库自己算还差哪些事务
  GET_MASTER_PUBLIC_KEY = 1;           -- caching_sha2_password 认证需要拉取公钥
START REPLICA;                         -- 启动复制（IO 线程 + SQL 线程）

-- 最后一步才开只读保护：初始化已全部完成，之后人为误写会被拒绝
SET GLOBAL read_only = 1;              -- 普通账号不可写
SET GLOBAL super_read_only = 1;        -- 连 SUPER 权限账号也不可写（防 root 手滑）
```

> 注意 `SET GLOBAL` 不持久化：容器重启后只读会失效，需要重跑这两行。这是演示环境的取舍，生产请用初始化脚本+运维手册固化。

### 6.6 验证主从（三条命令）

```bash
# 1) 从库复制状态：两个 Yes + 延迟 0 才算健康
docker exec yuxm-demo-mysql-replica-1 mysql -uroot -proot -e "SHOW REPLICA STATUS\G" | grep -E 'Running|Behind'
#   Replica_IO_Running: Yes          <- 从库在拉主库 binlog
#   Replica_SQL_Running: Yes         <- 从库在重放 binlog
#   Seconds_Behind_Source: 0         <- 复制延迟 0 秒

# 2) 主库写入，从库立即可见（从库没执行过任何写操作）
docker exec yuxm-demo-mysql-master-1  mysql -uroot -proot demo -e "INSERT INTO t VALUES(1,'m');"
docker exec yuxm-demo-mysql-replica-1 mysql -uroot -proot demo -e "SELECT * FROM t;"   # -> 1 | m

# 3) 从库写入被只读保护拒绝（保护数据单向流）
docker exec yuxm-demo-mysql-replica-1 mysql -uroot -proot demo -e "INSERT INTO t VALUES(2,'x');"
#   ERROR 1290: The MySQL server is running with the --super-read-only option
```

### 6.7 两类文件传输的隐形炸弹：BOM 与 CRLF

从 Windows 编辑过的 `.cnf`/`.sql` 如果带 UTF-8 BOM（文件头 `EF BB BF`）或 CRLF 行尾，MySQL 会报 `Found option without preceding group at line 1`，**整个配置静默失效**（server-id 没了、binlog 没了）。检查与修复：

```bash
file master.cnf replica.cnf                    # 看到 "with BOM" 就有问题
sed -i '1s/^\xEF\xBB\xBF//' master.cnf         # 去掉 BOM
sed -i 's/\r$//' master.cnf                    # 去掉行尾 \r
```

**经验法则：给 Linux 容器用的配置文件，要么在 Linux 侧生成，要么传完必查 `file`。**

## 7. 日常运维三件套

```bash
# ---- 更新发布：git push 后 Jenkins 自动构建部署，手动方式如下 ----
cd /opt/yuxm-site && git pull
cd deploy && docker compose up -d --build api web   # 重建并滚动更新 api/web

# ---- 一键回滚（Jenkins 每次部署自动留回滚点）----
bash deploy/scripts/rollback.sh status             # 看有哪些版本
bash deploy/scripts/rollback.sh 42                 # 回滚到第 42 次构建

# ---- 每日备份（已配 cron：每天 03:30）----
crontab -l | grep backup                           # 确认定时任务在
ls -lh /opt/yuxm-site/backups/                     # 检查备份文件在生成
# 手动恢复演练（强烈建议上线前真实演练一次）：
gunzip < backups/yuxm_site_YYYYMMDD.sql.gz | docker compose exec -T mysql mysql -uroot -p"$MYSQL_ROOT_PASSWORD" yuxm_site
```

## 8. 演示集群的启停与清理

```bash
# 演示集群常驻约 1.1G 内存（MySQL 双实例占大头），小内存机器用完要收：
docker compose -f docker-compose.demo.yml --profile init --profile mysql down -v
#   --profile init  把一次性建集群容器也纳入 down 范围（不带 profile 的 down 不会停它们！）
#   -v              连数据卷一起删（演示数据无保留价值）

# 重新起一遍（全是幂等操作）：
docker compose -f docker-compose.demo.yml up -d
docker compose -f docker-compose.demo.yml --profile init up redis-cluster-init -d
docker compose -f docker-compose.demo.yml --profile mysql up -d
```

## 9. 部署检查清单

- [ ] `.env` 四项密钥全部替换为强随机值
- [ ] `curl http://127.0.0.1/api/health` 返回 `{"code":0,...}`
- [ ] `python -m app.seed` 已执行（管理员可登录）
- [ ] 安全组只放行 SSH/80/443/8080(仅自己 IP)，3306/6379/7001-7006/3307/3308 全部未暴露
- [ ] Redis：`cluster_state:ok`（演示）/ AOF 开启 + 密码（生产）
- [ ] MySQL：`Replica_IO_Running:Yes` + `Replica_SQL_Running:Yes` + `Seconds_Behind_Source:0`
- [ ] 备份 cron 运行中，且**真实演练过一次恢复**
- [ ] Jenkins 8080 未对公网开放