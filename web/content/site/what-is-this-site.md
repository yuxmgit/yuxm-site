---
title: 本站架构说明：你访问的这个网站是怎么跑起来的
description: yuxm.site 自身的完整技术架构——Nuxt3 SSR/SSG + FastAPI + MySQL + Redis 黑名单踢下线 + OAuth2 + Docker Compose + Jenkins，教程与实践同一份代码。
category: docker
tags:
  - Docker
  - Jenkins
  - Nuxt3
  - FastAPI
  - JWT
date: 2026-11-18
sourceRepo: https://github.com/yuxiangming
---

> 这是网站的"自我介绍"：文章里讲的每一项技术，都被网站本身真实使用着。

## 整体架构

```
浏览器 ──▶ Nginx (80/443, gzip, 限流)
             ├─▶ Nuxt3 web 容器（SSG/SSR 文章站）
             └─▶ FastAPI api 容器（/api 认证/阅读数）
                     ├─▶ MySQL 8（users / user_identities / site_settings）
                     └─▶ Redis（JWT 黑名单 / 版本号 / 验证码 / 限频）
Jenkins 流水线 ──▶ 构建镜像并部署
```

## 前端：Nuxt3 + @nuxt/content

文章全部是 Git 管理的 Markdown 文件，构建期由 @nuxt/content 索引并静态化，
访问快、SEO 好，且不需要内容管理数据库——分类与系列靠 frontmatter 组织：

```yaml
---
title: 文章标题
category: redis-cluster   # 分类目录
series: redis-cluster-in-action  # 所属系列
seriesOrder: 1            # 系列内序号
---
```

## 后端：FastAPI + Redis 黑名单踢下线

JWT 双 token（access 15 分钟 / refresh 7 天），每个 token 携带唯一 `jti`：

```python
# 受保护接口的校验流程（O(1)，仅 1-2 次 Redis 读）
payload = jwt.decode(token, settings.jwt_secret)
if await redis.get(f"auth:bl:{payload['jti']}"):   # 1. 单 token 黑名单
    raise Unauthorized
if payload["ver"] != await redis.get(f"auth:ver:{payload['sub']}"):  # 2. 版本号
    raise Unauthorized
```

"退出所有设备"只需 `INCR auth:ver:{user_id}`，该用户所有旧 token 瞬时失效。

## 部署：Docker Compose + Jenkins

- 生产编排：nginx / web / api / mysql / redis 五个服务，健康检查 + 数据卷持久化
- 教程演示集群（Redis Cluster 3主3从、MySQL 主从）独立编排文件，与生产完全隔离
- Jenkins 流水线：拉码 → 构建 → 镜像 → 部署 → 健康检查

## 系列文章导航

- **Redis 集群实战**：从单机到 Cluster 3主3从的完整落地
- **MySQL 主从与读写分离**：复制原理、搭建与验证
- **Jenkins 生产级流水线**：从语法到共享库与治理
- **JWT 深入与踢下线**：本站正在使用的认证方案
