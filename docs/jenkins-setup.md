# Jenkins 从零部署到云服务器详细配置指南

> 与业务服务同机部署（`deploy/docker-compose.yml` 里的 `jenkins` 服务）。
> 全程约 30 分钟。完成后效果：git push → Jenkins 自动构建前端/后端 → 镜像部署 → 健康检查 → 失败告警。

## 0. 前置条件

- 服务器已按 `docs/server-setup.md` 完成初始化（Docker + compose 插件）
- 业务服务已跑通：`cd deploy && docker compose up -d`（流水线依赖的目标环境必须先存在）
- **腾讯云安全组**：放行 8080 端口，来源限制为 `你的常用IP/32`——Jenkins 控制台绝不能对公网开放
- Jenkins 与业务同机较吃内存（JVM 已限 512M），2C4G 可跑，但建议 2C8G

## 1. 启动 Jenkins 容器

```bash
cd /opt/yuxm-site/deploy
docker compose up -d jenkins
docker compose logs -f jenkins    # 看到 "Jenkins is fully up and running" 即成功
```

容器做了三件关键配置（见 compose 中 `jenkins` 服务定义）：

| 配置 | 作用 |
|---|---|
| `jenkins_data` volume | 任务/插件/凭据持久化，容器重建不丢配置 |
| 挂载 `/var/run/docker.sock` | 流水线里能直接执行 `docker build` / `docker compose` 命令（DooD 模式，镜像跑在宿主机 Docker 上） |
| `JAVA_OPTS: -Xmx512m` | 限制 JVM 堆内存，防止挤占 nginx/web/api 业务服务 |

> **DooD 说明**：容器内构建的镜像实际存在宿主机 Docker 里，与业务 compose 共享镜像缓存，`docker compose build` 能直接利用已有缓存层，构建很快。

## 2. 首次初始化（解锁 → 插件 → 管理员）

### 2.1 解锁

浏览器打开 `http://服务器IP:8080`，获取初始密码：

```bash
docker compose exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

### 2.2 插件安装（国内加速）

进入"自定义 Jenkins"页面，选 **"安装推荐的插件"**（会装 Git、Pipeline、Credentials 等）。

如果插件下载慢/失败，先换国内更新源再装：

```bash
# 容器内把清华镜像源写入更新配置（在"插件安装"之前执行）
docker compose exec jenkins sh -c \
  'sed -i "s#https://updates.jenkins.io/update-center.json#https://mirrors.tuna.tsinghua.edu.cn/jenkins/updates/update-center.json#g" \
  /var/jenkins_home/hudson.model.UpdateCenter.xml'
docker compose restart jenkins
```

装完推荐插件后，再到 **系统管理 → 插件管理 → Available plugins** 补装：

| 插件 | 用途 |
|---|---|
| Gitee / GitHub | 配合 webhook 推送自动触发构建（按仓库平台二选一） |
| Blue Ocean（可选） | 更友好的流水线可视化界面 |

### 2.3 创建管理员账号

按页面引导创建本地管理员（不要用 admin 弱密码，记录到密码管理器）。

## 3. 配置凭据（拉代码用）

**系统管理 → Credentials → System → Global credentials → Add Credentials**：

- Kind：`Username with password`
- ID：`repo-credentials`（GitHub 仓库用；如配置了 Gitee 镜像仓库则为 `gitee-credentials`，需与 Jenkinsfile 中凭据约定一致）
- Username：GitHub 用户名（`yuxmgit`）
- Password：填 **私人令牌**（GitHub：Settings → Developer settings → Personal access tokens，勾选 `repo`；Gitee：设置→私人令牌，勾选 `projects`），不要填网页登录密码——令牌可随时吊销

## 4. 创建流水线任务

1. 首页 → **新建 Item** → 名称 `yuxm-site` → 类型选 **Pipeline（流水线）** → 确定
2. **构建触发器**：勾选 `Gitee webhook`（或 GitHub hook），记下页面提示的 webhook URL：
   - Gitee：`http://服务器IP:8080/gitee-hook/`（装了 Gitee 插件后自动生成，含随机 token）
   - GitHub：`http://服务器IP:8080/github-webhook/`
3. **Pipeline 定义**：选 **Pipeline script from SCM**：
   - SCM：Git → 仓库地址 `https://github.com/yuxmgit/yuxm-site.git`
   - Credentials：选 `repo-credentials`（Gitee 双平台备选时可用 `gitee-credentials`）
   - 指定分支：`*/main`
   - Script Path：`deploy/jenkins/Jenkinsfile`（流水线定义随代码入库，改流水线也是 git commit）
4. 保存 → 点 **立即构建（Build Now）** 手动跑一次验证

### 配置 Gitee/GitHub Webhook（自动触发）

仓库端 → 管理 → WebHooks → 添加：

- URL：上面任务页提示的地址
- 密码：与任务页 webhook 配置一致（防伪造触发）
- 触发事件：`Push`

## 5. 流水线会做什么（对照 `deploy/jenkins/Jenkinsfile`）

```
检出代码 → 前端 npm build → 后端 compileall 语法检查
        → docker build web/api 镜像（双标签：BUILD_NUMBER 版本号 + latest）
        → docker compose up -d --no-build（部署刚构建的镜像）
        → curl 健康检查（失败重试 5 次，每次间隔 10s）
        → 记录回滚点（.deployed_build / .rollback_build 状态文件）
```

- `disableConcurrentBuilds()`：同一时间只跑一个构建，防止并发部署打架
- `buildDiscarder(20)`：只保留最近 20 次构建记录，控制磁盘
- **镜像版本化**：每次部署的镜像以 `yuxm-web:<BUILD_NUMBER>` 保留，`latest` 才是运行引用——这是回滚的基础
- **回滚点只在健康检查通过后记录**：健康检查失败的部署不会污染回滚点
- `post.failure`：构建失败时提示排查命令与一键回滚脚本；**部署失败时旧版本容器仍在运行**（`up -d` 是原子替换，新容器起不来旧的还在），这是兜底回滚保障

### 回滚（详见 `docs/release.md` 回滚章节）

```bash
bash deploy/scripts/rollback.sh status    # 查看当前版本 / 回滚点
bash deploy/scripts/rollback.sh           # 一键回滚到上一个成功版本（秒级，无需重新构建）
```

注意：Jenkinsfile 中 `ROLLBACK_STATE_DIR` 默认 `/opt/yuxm-site/deploy`（宿主机部署路径），若部署目录不同需同步修改脚本与流水线。

## 6. 首次构建常见报错速查

| 报错 | 原因 | 解决 |
|---|---|---|
| `docker: command not found`（流水线里） | 容器内没有 docker CLI | 镜像 `jenkins/jenkins:lts` 自带 docker CLI；若用了精简镜像需在容器内安装或改挂载宿主机 `/usr/bin/docker` |
| `permission denied ... /var/run/docker.sock` | sock 文件属主是宿主机 docker 组 | compose 已用 `user: root` 规避；更安全的做法：`group_add: [宿主机docker组GID]`（`stat -c %g /var/run/docker.sock` 查询） |
| `npm install` 超时 | 容器内没配 npm 镜像 | Jenkinsfile 中已用 `--registry=https://registry.npmmirror.com`，无需处理 |
| 健康检查一直失败 | api/web 容器起不来 | `docker compose logs api web` 看日志；常见是 `.env` 缺配置 |
| 磁盘满 | 构建镜像层积累 | 定期 `docker image prune -f`；流水线 post 阶段已自动清理 |

## 7. 日常运维

**备份 Jenkins 配置**（任务和凭据都在这个卷里）：

```bash
docker run --rm -v yuxm-site_jenkins_data:/data -v /opt/backups:/backup \
  alpine tar czf /backup/jenkins_$(date +%Y%m%d).tar.gz -C /data .
```

**升级 Jenkins**：

```bash
docker compose pull jenkins && docker compose up -d jenkins
```

**内存吃紧时**（2C4G）：临时停 Jenkins 释放 512M——`docker compose stop jenkins`，要用再启。

## 8. 安全清单（上线前必查）

- [ ] 8080 端口安全组仅放行自己 IP（最重要的一条）
- [ ] Jenkins 管理员使用强密码，且关闭"允许匿名读"
- [ ] 凭据用的是令牌而非账号密码；令牌最小权限（只勾 repo/projects）
- [ ] webhook 开启了密码校验
- [ ] 不需要在公网暴露 50000 端口（本站单机无 agent，安全组可不放行）
- [ ] 进阶：HTTPS 化——备案通过后可用 nginx 反代 Jenkins 并挂证书，8080 不再直接暴露
