# 上线流程（备案 → 部署 → HTTPS → CI/CD）

## 阶段 0：ICP 备案（必须最先办，约 1-2 周）

1. 腾讯云控制台 → 备案 → 开始备案（个人备案，网站内容填"个人技术博客"）
2. 域名 yuxm.site 需在腾讯云/已实名，服务器需为大陆地域的备案授权服务器
3. 期间域名不可解析到大陆服务器 80/443 端口；**调试用 `服务器IP:8080` 等非标准端口**
4. 通过后：域名解析 A 记录指向服务器 IP，工信部备案号写入后台「站点设置 → ICP 备案号」（页脚自动展示）

## 阶段 1：服务器就绪

按 `docs/server-setup.md` 完成：Docker 安装、SSH 加固、安全组、fail2ban、备份 cron。

## 阶段 2：首次部署

```bash
# 服务器上
cd /opt/yuxm-site
cp .env.example deploy/.env && vim deploy/.env   # 强随机密钥/密码
cd deploy && docker compose up -d
docker compose logs -f api web         # 确认无报错
docker compose exec api python -m app.seed
curl http://127.0.0.1:80/api/health    # {"code":0,...}
```

备案期间（无域名）临时访问：安全组放行 8080，compose 里 nginx ports 加 `"8080:80"`，验证全站功能。

## 阶段 3：HTTPS

见 server-setup.md 第 6 节。完成后删除临时调试端口，确认：
- http://yuxm.site 301 → https://yuxm.site
- 后台登录（/admin）正常，**立即修改默认密码**
- 登录页三种方式：短信验证码（需配置腾讯云 SMS）、GitHub/Gitee OAuth

## 阶段 4：CI/CD（Jenkins）

Jenkins 与业务服务同机部署，已加入 `deploy/docker-compose.yml`（`jenkins` 服务，docker.sock 挂载 + JVM 内存限制）。

完整从零配置（启动 → 解锁 → 国内插件源 → 凭据 → Pipeline 任务 → webhook → 报错速查）见 **`docs/jenkins-setup.md`**。概要：

1. `cd deploy && docker compose up -d jenkins`，按 `jenkins-setup.md` 完成初始化
2. 新建 Pipeline 任务，SCM 指向 GitHub/Gitee 仓库（webhook 自动触发可选）
3. Pipeline 脚本路径：`deploy/jenkins/Jenkinsfile`
4. 流水线阶段：检出 → 前端构建 → 后端语法检查 → 构建镜像 → compose 部署 → 健康检查（5 次重试）
5. 安全要求：8080 端口安全组仅放行自己 IP，不要对公网开放

## OAuth 应用配置（部署后一次性）

| 平台 | 创建位置 | 回调地址 |
|---|---|---|
| GitHub | Settings → Developer settings → OAuth Apps | `https://yuxm.site/server/auth/github/callback` |
| Gitee | 设置 → 安全设置 → 第三方应用 | `https://yuxm.site/server/auth/gitee/callback` |

Client ID/Secret 填入 `.env` 对应项后 `docker compose up -d api` 重启。

## 求职展示说明（内容维护）

- 每篇教程 frontmatter 的 `sourceRepo` 指向源仓库；"本站实际使用的方案"徽标出现在所有文章详情页
- 面试可现场演示的闭环：
  1. **JWT 踢下线**：登录 → 后台"用户管理"踢下线 → 前台立即 401 退出
  2. **OAuth2**：点击 GitHub 登录走完整授权码流程
  3. **限流防刷**：连续点"获取验证码"触发 60s 间隔 / 429
  4. **CI/CD**：git push → Jenkins 自动构建部署 → 健康检查
  5. **演示集群**：`docker compose -f docker-compose.demo.yml --profile init up redis-cluster-init` 起 Redis Cluster 3主3从，MySQL 主从自动复制
- 整站开源，仓库 README 即简历附件

## 回滚

**方式一（推荐）：一键脚本，秒级完成，无需重新构建**

Jenkins 每次部署成功后会自动记录回滚点（`.rollback_build`），镜像按构建号版本化保存：

```bash
bash deploy/scripts/rollback.sh status   # 查看当前版本 / 回滚点 / 可用镜像
bash deploy/scripts/rollback.sh          # 回滚到上一个成功部署的版本
bash deploy/scripts/rollback.sh 42       # 回滚到指定构建版本
```

**方式二：Jenkins 控制台 Replay**——构建历史里找到上次成功的构建，点 Replay 重跑（重新构建并部署该次代码），适合"代码层面回退"。

**方式三：git 版本回退**（前两种都不可用时的兜底）：

```bash
cd /opt/yuxm-site/deploy
git checkout <上一个可用 tag/commit>
docker compose up -d --build
```

数据库回滚：`gunzip < backups/yuxm_XXXX.sql.gz | docker exec -i $(docker compose ps -q mysql) sh -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"'`
