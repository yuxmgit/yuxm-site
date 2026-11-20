# 内容迁移规范与映射表

首批文章迁移自三个教程仓库（迁移脚本：`scripts/migrate-content.mjs`，可重复执行）。

## frontmatter 规范

```yaml
---
title: 文章标题                       # 必填，详情页大标题
description: 一句话摘要（90字内）      # 必填，列表卡片与 SEO
category: redis-cluster              # 必填，见下方分类表
series: redis-cluster-in-action      # 可选，所属系列
seriesOrder: 1                       # 可选，系列内序号
tags: ["Redis", "集群"]              # 必填，2-3 个
date: 2026-08-01                     # 必填
sourceRepo: https://github.com/...   # 可选，源教程仓库
---
```

## 分类表（与 web/composables/useCategories.ts 对应）

| category | 名称 | 内容来源 |
|---|---|---|
| redis-cluster | Redis 集群 | fullstack 05 |
| mysql | MySQL | fullstack 04 |
| jenkins | Jenkins / CI-CD | cicd 21章 + 附录、fullstack 08 |
| docker | Docker | cicd 10/11/13、fullstack 03/06/07 |
| jwt | JWT / 认证 | sso 03/08/09/10、fullstack 02 |
| oauth2 | OAuth2 / SSO | sso 01/02/04/05/06/07 |
| python-frameworks | Python 框架 | fullstack 01 |

## 系列表（与 SERIES 常量对应）

| series | 名称 | 包含 |
|---|---|---|
| fullstack-cluster-in-action | 全栈集群实战 | fullstack 01-08 |
| sso-oauth-series | SSO 与 OAuth2 | sso 01-10 |
| cicd-pipeline-series | CI/CD 流水线 | cicd 00-20（附录不进系列） |

## 迁移处理规则

1. 源文件均为"无 frontmatter、无图片"的纯 Markdown，迁移零资产成本
2. 正文首个 `# H1` 移除（标题由 frontmatter 提供）
3. 跨文件 `.md` 链接 → 保留文字去链接；`../demos/` 链接 → 保留文字去链接
4. 章末"下一章/上一篇"导流行整行移除（系列导航由新站系列页承担）
5. `sourceRepo` 中的 GitHub 用户名需按实际仓库地址更新

## 后台展示覆盖（article_overrides）

迁移后的 Markdown 是"底稿"，后台可对每篇文章设置发布/草稿、精选、置顶、摘要、封面，
覆盖信息存 MySQL `article_overrides` 表（按 slug 关联），前台渲染时 DB 覆盖优先，不改源文件。

## 未迁移/后续批次

- cicd 附录 D（Runbook，依赖正文语境）
- sso GLOSSARY.md（可做成站点独立页面）
- 各项目 README（索引型，不迁移）
- Python 框架对比系列（FastAPI/Flask/Django）为新增原创内容，后续撰写
