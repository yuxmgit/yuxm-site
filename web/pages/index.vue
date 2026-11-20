<script setup lang="ts">
// 首页：Hero（个人简介+架构亮点+开源入口）→ 精选分类 → 最新文章
import { Book, Container, Database, GitBranch, KeyRound, Server, ShieldCheck, Workflow } from 'lucide-vue-next'
import type { ArticleMeta } from '~/composables/useArticleMeta'

const config = useRuntimeConfig()

// 最新文章：从 content 目录按日期倒序取 6 篇（后台覆盖信息后续由 API 合并）
const { data: latestDocs } = await useAsyncData('latest-posts', () =>
  queryCollection('content')
    .select('title', 'description', 'category', 'series', 'seriesOrder', 'tags', 'date', 'path')
    .order('date', 'DESC')
    .limit(6)
    .all()
)

const latestArticles = computed<ArticleMeta[]>(() =>
  (latestDocs.value || []).map(doc => toArticleMeta(doc as never)).filter((a): a is ArticleMeta => a !== null)
)

// 架构亮点：网站自身的实践，即求职展示
const highlights = [
  { icon: Server, title: 'FastAPI 后端', desc: '本站 API 即 FastAPI 实现，异步 SQLAlchemy + Pydantic' },
  { icon: Database, title: 'MySQL + Redis', desc: '双 token 校验走 Redis O(1) 读，无查询热点' },
  { icon: KeyRound, title: 'JWT 踢下线', desc: 'jti 黑名单 + token_version，实时强制下线' },
  { icon: ShieldCheck, title: 'OAuth2 登录', desc: 'GitHub / Gitee 授权码模式接入' },
  { icon: Container, title: 'Docker Compose', desc: 'nginx/web/api/mysql/redis 五容器编排' },
  { icon: Workflow, title: 'Jenkins CI/CD', desc: '流水线构建镜像并部署，健康检查' },
  { icon: GitBranch, title: '整站开源', desc: '代码与教程同仓库，面试可现场演示' },
  { icon: Book, title: 'SSG 静态化', desc: 'Nuxt Content 构建期索引，SEO 友好' }
]

useSeoMeta({
  title: '余先森的技术站 | Redis 集群 · MySQL · Jenkins · Docker · JWT · OAuth2',
  description: '开发者求职向技术教程站：Redis 集群、MySQL 主从、Jenkins 流水线、Docker、JWT、OAuth2、Python 框架实战。本站自身架构即教程的最佳示例。'
})
</script>

<template>
  <div>
    <!-- Hero 区 -->
    <section class="border-b border-slate-200 bg-gradient-to-b from-slate-50 to-white dark:border-slate-700 dark:from-slate-800 dark:to-slate-900">
      <div class="mx-auto max-w-6xl px-4 py-16 text-center animate-fade-in">
        <h1 class="mb-4 text-3xl font-bold md:text-4xl">
          写教程，也在<span class="text-primary-brand">跑</span>教程
        </h1>
        <p class="mx-auto mb-8 max-w-2xl text-base leading-relaxed text-slate-600 dark:text-slate-300">
          你正在访问的这个网站，就是我的架构实践：Nuxt3 SSR/SSG + FastAPI + MySQL + Redis +
          JWT 黑名单踢下线 + OAuth2 + Docker Compose + Jenkins 流水线。
          每一篇教程标注「本站实际使用的方案」，代码全部开源。
        </p>
        <div class="mb-10 flex items-center justify-center gap-3">
          <a
            :href="config.public.githubUrl"
            target="_blank"
            rel="noopener"
            class="rounded-lg bg-primary-brand px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary-brand-dark"
          >GitHub 仓库</a>
          <a
            :href="config.public.giteeUrl"
            target="_blank"
            rel="noopener"
            class="rounded-lg border border-slate-300 px-5 py-2.5 text-sm font-medium transition-colors hover:border-primary-brand hover:text-primary-brand dark:border-slate-600"
          >Gitee 仓库</a>
          <NuxtLink
            to="/about"
            class="rounded-lg border border-slate-300 px-5 py-2.5 text-sm font-medium transition-colors hover:border-primary-brand hover:text-primary-brand dark:border-slate-600"
          >关于我</NuxtLink>
        </div>

        <!-- 架构亮点卡片 -->
        <div class="grid grid-cols-1 gap-4 text-left sm:grid-cols-2 lg:grid-cols-4">
          <div v-for="h in highlights" :key="h.title" class="site-card p-4">
            <component :is="h.icon" class="mb-2 h-5 w-5 text-primary-brand" />
            <h3 class="mb-1 text-sm font-semibold">{{ h.title }}</h3>
            <p class="text-xs leading-relaxed text-slate-500 dark:text-slate-400">{{ h.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- 精选分类 -->
    <section class="mx-auto max-w-6xl px-4 py-12">
      <h2 class="mb-6 text-xl font-semibold">教程分类</h2>
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <NuxtLink v-for="cat in CATEGORIES" :key="cat.key" :to="`/category/${cat.key}`" class="site-card group p-5">
          <span class="mb-2 inline-block h-2.5 w-2.5 rounded-full" :style="{ backgroundColor: cat.color }" />
          <h3 class="mb-1 font-semibold group-hover:text-primary-brand">{{ cat.name }}</h3>
          <p class="text-sm text-slate-500 dark:text-slate-400">{{ cat.description }}</p>
        </NuxtLink>
      </div>
    </section>

    <!-- 最新文章 -->
    <section class="mx-auto max-w-6xl px-4 pb-16">
      <h2 class="mb-6 text-xl font-semibold">最新文章</h2>
      <div v-if="latestArticles.length" class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        <ArticleCard v-for="a in latestArticles" :key="a.slug" :article="a" />
      </div>
      <div v-else class="rounded-xl border border-dashed border-slate-300 p-12 text-center text-sm text-slate-400 dark:border-slate-600">
        文章将在内容迁移后展示（content/ 目录下的 Markdown 即文章）
      </div>
    </section>
  </div>
</template>
