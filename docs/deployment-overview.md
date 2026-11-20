# yuxm-site 总部署流程（从零到上线一条主线）

> 本文档是全项目部署的**总纲**，把分散在各文档中的步骤串成一条可执行的主线。
> 各阶段细节见对应专项文档：
> - 服务器初始化/加固：`docs/server-setup.md`
> - 首次上线与回滚：`docs/release.md`
> - Jenkins CI/CD 配置：`docs/jenkins-setup.md`
> - 教程内容迁移：`docs/content-migration.md`

## 总览

```
阶段0 ICP备案（先办，1-2周）
  → 阶段1 服务器初始化与安全加固
  → 阶段2 首次部署（docker compose 拉起全栈 + 种子数据）
  → 阶段3 备案期间临时端口验证（可选，走 8080）
  → 阶段4 HTTPS 证书上线
  → 阶段5 Jenkins CI/CD 流水线
  → 阶段6 OAuth / SMS 等第三方服务配置
  → 阶段7 上线前安全复查
  → 日常发布：git push → Jenkins 自动构建部署 → 健康检查
  → 异常处理：rollback.sh 一键回滚 / 数据库备份恢复
```

生产拓扑（`deploy/docker-compose.yml`，共 6 个服务）：

| 服务 | 说明 | 对外端口 |
|---|---|---|
| nginx | 统一入口，80/443 + HTTPS + 反代 | 80, 443 |
| web | Nuxt3 前端（前台 + /admin） | 仅容器网络 |
| api | FastAPI 后端 | 仅容器网络 |
| mysql | MySQL 8（utf8mb4） | 仅容器网络 |
| redis | Redis 7（AOF + 密码） | 仅容器网络 |
| jenkins | CI/CD（docker.sock 挂载，JVM 限 512M） | 8080（仅自己 IP） |

---

## 阶段 0：ICP 备案（必须最先办，约 1-2 周）

1. 腾讯云控制台 → 备案 → 开始备案（个人备案，网站内容填"个人技术博客"）
2. 域名 yuxm.site 需在腾讯云且已实名，服务器为大陆地域备案授权服务器
3. 备案期间域名不可解析到大陆服务器 80/443，**调试一律走 `服务器IP:8080` 等非标准端口**
4. 通过后：域名 A 记录指向服务器 IP；工信部备案号填入后台「站点设置 → ICP 备案号」（页脚自动展示）

## 阶段 1：服务器初始化与安全加固

按 `docs/server-setup.md` 自上而下执行：

1. 系统更新、时区 `Asia/Shanghai`、安装 Docker + compose 插件（配腾讯云镜像加速）
2. SSH 加固：密钥登录验证通过后，禁密码登录、禁 root 直登（可改端口）
3. 安全组只放行：22/2222（SSH）、80/443、8080（Jenkins，仅自己 IP /32）；**3306/6379/8000/3000 一律不放行**
4. fail2ban 防 SSH 爆破
5. 目录规划：`/opt/yuxm-site`，拉取代码 `git clone https://github.com/yuxmgit/yuxm-site.git .`
6. 环境变量：`cp .env.example .env`，必改 `JWT_SECRET`（≥32 字节随机）、`MYSQL_ROOT_PASSWORD`、`MYSQL_PASSWORD`、`REDIS_PASSWORD`

## 阶段 2：首次部署

```bash
cd /opt/yuxm-site
cp .env.example .env && vim .env       # 填强随机密钥/密码
cd deploy && docker compose up -d      # nginx/web/api/mysql/redis 一起拉起
docker compose logs -f api web         # 确认无报错
docker compose exec api python -m app.seed   # 创建管理员（首次必须）
curl http://127.0.0.1/api/health       # {"code":0,...} 即正常
```

依赖关系已由 compose 健康检查保证：mysql/redis healthy → api → web → nginx。

## 阶段 3：备案期间临时验证（无域名时）

- 安全组临时放行 8080（仅自己 IP）
- `deploy/docker-compose.yml` 中 nginx ports 临时加 `"8080:80"`
- 浏览器 `http://服务器IP:8080` 验证全站功能；备案通过后删除该映射与安全组规则

## 阶段 4：HTTPS（备案通过后）

1. 腾讯云控制台 → SSL 证书 → 申请免费 DV 证书（yuxm.site）
2. 下载 Nginx 版证书，上传 `deploy/nginx/certs/`（`yuxm.site_bundle.pem` / `yuxm.site.key`）
3. 按 `deploy/nginx/nginx.conf` 内注释启用 443 段
4. `docker compose restart nginx`，验证：
   - `http://yuxm.site` 301 → `https://yuxm.site`
   - `/admin` 后台登录正常，**立即修改管理员默认密码**（初始 yuxiangming/yuxiangming）
   - 三种登录方式可用：短信验证码、GitHub OAuth、Gitee OAuth

## 阶段 5：Jenkins CI/CD

按 `docs/jenkins-setup.md` 全程约 30 分钟：

1. `cd deploy && docker compose up -d jenkins`（已随 compose 编排，docker.sock 挂载 + 国内插件源）
2. 解锁 → 装推荐插件 → 补装 GitHub（或 Gitee）插件 → 配置拉码凭据（`repo-credentials`，GitHub 私人令牌）
3. 新建 Pipeline 任务，SCM 指向 `https://github.com/yuxmgit/yuxm-site`，脚本路径 `deploy/jenkins/Jenkinsfile`
4. （可选）配置 webhook 实现 git push 自动触发

流水线阶段（`deploy/jenkins/Jenkinsfile`）：

```
检出代码 → 前端 npm install + build → 后端 compileall 语法检查
→ 构建双标签镜像 yuxm-web/api:<BUILD_NUMBER> + :latest
→ docker compose up -d --no-build web api
→ 健康检查（curl /api/health 与 /，重试 5 次）
→ 记录回滚点（.deployed_build / .rollback_build）
```

安全要求：8080 端口安全组仅放行自己 IP，绝不对公网开放。

## 阶段 6：第三方服务配置（一次性）

| 项 | 配置位置 | 回调/说明 |
|---|---|---|
| GitHub OAuth App | Settings → Developer settings → OAuth Apps | `https://yuxm.site/server/auth/github/callback` |
| Gitee 第三方应用 | 设置 → 安全设置 → 第三方应用 | `https://yuxm.site/server/auth/gitee/callback` |
| 腾讯云 SMS | 短信控制台申请签名/模板 | 验证码登录，IP+手机号双重限频 |

Client ID / Secret / SDK 凭据填入 `.env` 后 `docker compose up -d api` 重启生效。

## 阶段 7：上线前安全复查清单

- [ ] `.env` 中所有 `change-me` 已替换为强随机值
- [ ] 后台管理员默认密码已修改
- [ ] SSH 已禁密码登录，fail2ban 运行中
- [ ] 安全组未放行 3306/6379/8000/3000，8080 仅限自己 IP
- [ ] 备份 cron 已启用且验证过恢复流程（见下文"备份与恢复"）
- [ ] `/api/docs` 生产环境已关闭（APP_ENV=prod 自动关闭）
- [ ] 页脚 ICP 备案号已配置

---

## 日常发布（上线后的标准流程）

```
本地改代码 → git push →（webhook 或手动）Jenkins 构建
→ 镜像按构建号版本化保存 → compose 部署 → 健康检查
→ 通过：记录回滚点；失败：流水线报错，执行 rollback.sh 恢复
```

排查命令：

```bash
cd /opt/yuxm-site/deploy
docker compose ps                      # 各服务状态（应全部 healthy）
docker compose logs -f api web         # 业务日志
```

## 回滚

**方式一（推荐）：一键脚本，秒级，无需重新构建**

```bash
bash deploy/scripts/rollback.sh status   # 查看当前版本 / 回滚点 / 可用镜像
bash deploy/scripts/rollback.sh          # 回滚到上一个成功部署版本
bash deploy/scripts/rollback.sh 42       # 回滚到指定构建版本
```

**方式二**：Jenkins 构建历史 → 上次成功构建 → Replay（重新构建部署该次代码）。

**方式三（兜底）**：git 回退代码后重建：

```bash
cd /opt/yuxm-site/deploy
git checkout <上一个可用 tag/commit>
docker compose up -d --build
```

## 备份与恢复

- 定时备份：`deploy/scripts/backup-mysql.sh`，cron `30 3 * * *`（见 server-setup.md 第 5 节）
- 恢复：

```bash
gunzip < backups/yuxm_XXXX.sql.gz | docker exec -i \
  $(docker compose ps -q mysql) sh -c \
  'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"'
```

## 演示集群（与生产隔离，可选）

教程演示用 Redis Cluster 3主3从 / MySQL 主从，独立编排文件，不影响生产：

```bash
docker compose -f docker-compose.demo.yml --profile init up redis-cluster-init
```
