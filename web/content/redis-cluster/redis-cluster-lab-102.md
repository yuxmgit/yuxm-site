---
title: "第 2 章：亲手把 Redis Cluster 玩坏——3主3从搭建与故障转移实录"
description: "本文所有输出都是在一台真实服务器上逐步跑出来的：集群创建、数据分片、杀主节点看自动上位、MySQL 主从复制。以及路上踩到的 6 个真实的坑，每个坑都是一套通用经验。"
category: redis-cluster
series: redis-reliability-lab
seriesOrder: 2
tags: ["Redis Cluster", "故障转移", "MySQL 主从", "GTID", "Docker", "踩坑实录"]
date: 2026-11-24
sourceRepo: https://github.com/yuxiangming/yuxm-site
---

> 本文不是理论综述，是**一台 3.7G 内存的真实服务器**上的操作实录。所有输出原样保留（含报错）。环境：本站仓库的 `deploy/docker-compose.demo.yml`，与生产完全隔离。

## 1. 环境与一键启动

```bash
cd /opt/yuxm-site/deploy
# 6 个 Redis 节点（端口 7001-7006，host 网络模式，只绑 127.0.0.1）
docker compose -f docker-compose.demo.yml up -d
# 一次性建集群：3 主（7001-7003）+ 3 从（7004-7006）
docker compose -f docker-compose.demo.yml --profile init up redis-cluster-init
# MySQL 主从（master 3307 / replica 3308）
docker compose -f docker-compose.demo.yml --profile mysql up -d
```

## 2. 集群建起来了：真实输出

初始化容器打印的分配方案（3 主 3 从，槽均分）：

```
M: e6011bd7... 127.0.0.1:7001   slots:[0-5460]      (5461 slots) master
M: 12ab80d0... 127.0.0.1:7002   slots:[5461-10922]  (5462 slots) master
M: 4271d957... 127.0.0.1:7003   slots:[10923-16383] (5461 slots) master
S: 542e4409... 127.0.0.1:7004   replicates 12ab80d0...  (跟随主7002)
S: a03487b3... 127.0.0.1:7005   replicates 4271d957...  (跟随主7003)
S: e17fd8e7... 127.0.0.1:7006   replicates e6011bd7...  (跟随主7001)
```

最终状态检查：

```
cluster_state:ok
cluster_slots_assigned:16384     <- 16384 个槽全部有人管
cluster_known_nodes:6
cluster_size:3                   <- 3 个主节点
```

## 3. 数据自动分片：写 6 个 key 看路由

```bash
redis-cli -p 7001 -c set demo:key1 value-1   # -c 表示跟随集群重定向
redis-cli -p 7001 cluster keyslot demo:key1  # 算这个 key 属于哪个槽
```

结果（`CRC16(key) % 16384`）：key1 -> slot 2914（落在主7001 的 0-5460 区间）、key3 -> slot 11040（落在主7003 的 10923-16383 区间）……6 个 key 被自动摊到不同主节点。**你不用关心数据在哪，`-c` 模式下客户端自动跳转。**

## 4. 重头戏：杀掉主节点，看集群自救

```bash
docker stop yuxm-demo-redis-node1-1     # 主7001 正管着 demo:key1 所在槽
sleep 12                                 # cluster-node-timeout 5s + 从节点选举
redis-cli -p 7002 cluster nodes          # 从别的节点看集群视角
```

真实输出（12 秒后）：

```
127.0.0.1:7002 ... master - 5461-10922          <- 主7002 正常
127.0.0.1:7001 ... master,fail -                <- 主7001 被标记 fail
127.0.0.1:7006 ... master - 0-5460              <- 从7006 已上位，接管 0-5460！
127.0.0.1:7003 ... master - 10923-16383
```

**数据没丢**——从 7002 上读原来的 key：

```
redis-cli -p 7002 -c get demo:key1
"value-1"
```

再把 7001 启回来，它**自动降级为从节点**，跟在新主人 7006 身后：

```
b57d1740... 127.0.0.1:7001 slave 9a14f90a...  connected
```

整个自救过程约 10 秒，业务无感知。这就是第 1 章说的"Cluster 内置故障转移"。

## 5. MySQL 主从：同一台机器上的第二套集群

从库复制状态（`SHOW REPLICA STATUS` 关键字段）：

```
Source_Host: mysql-master
Replica_IO_Running: Yes      <- 抓 binlog 的线程在跑
Replica_SQL_Running: Yes     <- 重放 binlog 的线程在跑
Seconds_Behind_Source: 0     <- 延迟 0 秒
```

主库写入 -> 从库立即可读（从库**没执行过任何写操作**）：

```
主库: SELECT * FROM t;  ->  1 | written-at-master
从库: SELECT * FROM t;  ->  1 | written-at-master
从库尝试写入 -> 被只读保护拒绝
```

## 6. 踩坑实录：6 个真实的坑（每个都是通用经验）

理想教程只有成功，真实工程全是报错。以下是本次从零到集群全绿过程中真实踩到的坑：

### 坑 1：YAML 折叠标量拆散了多行命令

`entrypoint: >` 里写了带换行的 redis-cli 命令，YAML 把缩进的续行**当成了独立命令**，报 `Wrong number of arguments`。教训：**compose 里的 shell 命令尽量写成单行**，别依赖 YAML 的多行折叠。

### 坑 2：cluster-announce-ip 127.0.0.1 需要 host 网络

6 个节点跑在各自容器网络里时，announce 到 127.0.0.1 = 节点之间互相"约在自家门口见面"，谁也遇不到谁，`cluster_known_nodes:1`、`CLUSTERDOWN`。教训：**Redis Cluster 的 announce IP 必须是"对方真能访问到我的地址"**——要么 host 网络，要么容器真实 IP。

### 坑 3：docker compose down 不会停 profile 服务

带 `profiles` 的服务（如 redis-cluster-init）不在默认 down 范围内。旧的 init 容器卡死在"Waiting for the cluster to join"，新的 `--profile init up -d` 看到它 Running 就直接跳过，**什么都没做**。教训：排查前先 `docker ps -a`，怀疑有僵尸容器就 `--profile xxx down` 或 `docker rm -f`。

### 坑 4：BOM + CRLF 让 MySQL 配置全体失效

从 Windows 侧生成的 `master.cnf`/`replica.cnf` 带了 UTF-8 BOM（`EF BB BF`）和 CRLF，MySQL 报 `Found option without preceding group at line 1`——**server-id、log-bin、read_only 全部没生效**，主库没有 binlog、从库没有 server-id。教训：**跨平台同步的配置文件要过一遍编码检查**（`file xxx.cnf` 一眼看出 BOM）。

### 坑 5：cnf 里的 super_read_only 与 Docker 首次初始化自相残杀

`replica.cnf` 配了 `super_read_only=1`，而 Docker 的首次初始化（设 root 密码、跑 init SQL）本身要写库——被只读模式拒绝，`ERROR 1290`，root 密码停留在空、复制配置没执行。教训：**容器化 MySQL 的"初始化期"和"运行期"权限需求不同，运行期才该加的只读保护要用 init SQL 在初始化完成后 `SET GLOBAL` 设置**。

### 坑 6：GTID 自动定位要求两端都开

从库 init SQL 用了 `SOURCE_AUTO_POSITION=1`，但 GTID 只在主库开了，从库报 `ERROR 1777: GTID_MODE = OFF`。教训：**复制拓扑的机制性开关（GTID、binlog 格式）必须两端一致**，一端 ON 一端 OFF 就是最典型的静默错配。

## 7. 自己复刻一遍 & 用完收拾

```bash
# 停掉一切并清空演示数据（不影响生产容器）
docker compose -f docker-compose.demo.yml --profile init --profile mysql down -v
```

演示集群会占约 1G 内存（MySQL 两个实例占大头），小内存机器用完记得收。本站演示环境当前就跑在生产同机的 7001-7006/3307-3308 上，欢迎上去戳一戳——杀个主节点，看它自己爬起来。