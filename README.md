# yuxm-site

个人技术教程网站，域名 `yuxm.site`（部署于腾讯云）。
代码仓库：[https://github.com/yuxmgit/yuxm-site](https://github.com/yuxmgit/yuxm-site)
网站本身的技术栈（Nuxt3 + FastAPI + Docker + Jenkins + JWT/OAuth2 + Redis 黑名单踢下线）就是架构实践作品的一部分，教程内容与实现代码互相印证。

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Nuxt3 (Vue3 + TypeScript) + TailwindCSS + TDesign，@nuxt/content 渲染 Markdown，SSR/SSG |
| 后端 | FastAPI + SQLAlchemy(async) + MySQL 8 + Redis |
| 认证 | JWT 双 token（含 jti）+ Redis 黑名单/版本号实时踢下线；GitHub / Gitee OAuth2；腾讯云 SMS 验证码（IP+手机号双重限频） |
| 管理 | /admin 后台：站点设置、文章管理、用户管理（踢下线/封禁）、数据看板 |
| 部署 | Docker Compose + Nginx + HTTPS + Jenkins 流水线 |

## 目录结构

```
yuxm-site/
├── web/        # Nuxt3 前端（前台 + /admin 管理端）
│   └── content/  # Markdown 教程文章（迁移自三个教程仓库）
├── api/        # FastAPI 后端
├── deploy/     # 生产编排、演示集群编排、nginx、Jenkinsfile、备份脚本
└── docs/       # 内容迁移规范、服务器加固、上线流程
```

## 本地开发

### 前端

```bash
cd web
npm install
npm run dev        # http://localhost:3000
```

### 后端

```bash
cd api
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy ..\.env.example .env     # 修改数据库/Redis 连接后使用
uvicorn app.main:app --reload --port 8000    # http://localhost:8000/api/docs
```

依赖服务（MySQL + Redis）可用 `deploy/docker-compose.demo.yml` 或本机 Docker 快速拉起。

## 管理后台

- 地址：`http://localhost:3000/admin`
- 初始账号：`yuxiangming` / `yuxiangming`（由种子脚本创建，**上线前必须修改密码**）

## 部署（腾讯云）

1. **先备案**：域名 yuxm.site 绑定大陆服务器必须完成 ICP 备案（腾讯云备案控制台，约 1-2 周）；备案期间用 `服务器IP + 非标准端口` 调试
2. 服务器初始化与加固清单见 `docs/server-setup.md`
3. 生产编排：`deploy/docker-compose.yml`（nginx / web / api / mysql / redis）
4. HTTPS：腾讯云免费证书，配置模板见 `deploy/nginx/nginx.conf`
5. CI/CD：`deploy/jenkins/Jenkinsfile`；教程演示集群（Redis Cluster 3主3从、MySQL 主从）单独用 `deploy/docker-compose.demo.yml`，与生产隔离
6. 上线步骤与内容维护说明见 `docs/release.md`；**端到端总部署流程总纲见 `docs/deployment-overview.md`**

## 教程内容来源

首批文章迁移自本人三个开源教程仓库：

- `fullstack-cluster-tutorial`：前后端分离、Session 集中管理、MySQL 主从读写分离、Redis、腾讯云部署实战
- `sso-oauth-tutorial`：SSO 演进、Session vs JWT、手写 OAuth2、OIDC、安全攻防
- `cicd-tutorial`：Jenkins Pipeline 与共享库、Docker、Nginx/HTTPS、发布治理

迁移规范见 `docs/content-migration.md`。

## 代码仓库

代码已托管至 GitHub：`https://github.com/yuxmgit/yuxm-site`

```bash
cd yuxm-site
git remote add origin https://github.com/yuxmgit/yuxm-site.git
git push -u origin main
# 供 Jenkins 拉取；如需 Gitee 双平台可另行添加第二个 remote
```

