<script setup lang="ts">
// 关于页：个人介绍、技能矩阵、开源项目、联系方式
import { Github, Mail } from 'lucide-vue-next'

const config = useRuntimeConfig()

const skills = [
  { name: 'Python / FastAPI', level: 90, desc: '本站后端即 FastAPI 实现' },
  { name: 'Vue3 / Nuxt3', level: 85, desc: 'SSR/SSG，本站前端技术栈' },
  { name: 'MySQL / 主从架构', level: 85, desc: '读写分离实践与教程' },
  { name: 'Redis / Cluster', level: 80, desc: '缓存、黑名单踢下线、3主3从' },
  { name: 'Docker / Compose', level: 85, desc: '本站五容器编排' },
  { name: 'Jenkins / CI-CD', level: 80, desc: '共享库与生产治理' }
]

const projects = [
  { name: 'fullstack-cluster-tutorial', desc: '前后端分离 + Session 集中管理 + MySQL 主从 + 腾讯云部署', url: `${config.public.githubUrl}/fullstack-cluster-tutorial` },
  { name: 'sso-oauth-tutorial', desc: 'SSO 演进、Session vs JWT、手写 OAuth2、OIDC 与安全攻防', url: `${config.public.githubUrl}/sso-oauth-tutorial` },
  { name: 'cicd-tutorial', desc: 'Jenkins Pipeline 与共享库、Docker、Nginx/HTTPS、发布治理', url: `${config.public.githubUrl}/cicd-tutorial` }
]

useSeoMeta({
  title: '关于我 | 余先森的技术站',
  description: '开发者 yuxiangming：Python 后端 / 全栈，专注 Redis、MySQL、Jenkins、Docker、JWT、OAuth2 的工程化实践。'
})
</script>

<template>
  <div class="mx-auto max-w-4xl px-4 py-10 animate-fade-in">
    <!-- 简介 -->
    <section class="mb-10">
      <h1 class="mb-4 text-3xl font-bold">关于我</h1>
      <p class="mb-3 leading-relaxed text-slate-600 dark:text-slate-300">
        你好，我是余先森（yuxiangming），一名后端方向的开发者。这个网站是我求职展示的一部分：
        它不只是教程，教程里讲的每一项技术（JWT 踢下线、OAuth2 登录、Docker 编排、Jenkins 流水线）
        都被网站本身真实使用着——你可以把本站当作一份"可运行的简历"。
      </p>
      <p class="leading-relaxed text-slate-600 dark:text-slate-300">
        教程内容来自我持续维护的三个开源项目，覆盖集群、CI/CD 与认证体系，均配有可运行的代码示例。
      </p>
    </section>

    <!-- 技能矩阵 -->
    <section class="mb-10">
      <h2 class="mb-5 text-xl font-semibold">技能矩阵</h2>
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div v-for="s in skills" :key="s.name" class="site-card p-4">
          <div class="mb-1.5 flex items-center justify-between text-sm">
            <span class="font-medium">{{ s.name }}</span>
            <span class="text-slate-400">{{ s.level }}%</span>
          </div>
          <div class="mb-1.5 h-1.5 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-700">
            <div class="h-full rounded-full bg-primary-brand transition-all" :style="{ width: `${s.level}%` }" />
          </div>
          <p class="text-xs text-slate-500 dark:text-slate-400">{{ s.desc }}</p>
        </div>
      </div>
    </section>

    <!-- 开源项目 -->
    <section class="mb-10">
      <h2 class="mb-5 text-xl font-semibold">开源项目</h2>
      <div class="space-y-3">
        <a v-for="p in projects" :key="p.name" :href="p.url" target="_blank" rel="noopener" class="site-card group flex items-start gap-3 p-4">
          <Github class="mt-0.5 h-5 w-5 shrink-0 text-slate-400 group-hover:text-primary-brand" />
          <span>
            <span class="block font-mono text-sm font-semibold group-hover:text-primary-brand">{{ p.name }}</span>
            <span class="block text-sm text-slate-500 dark:text-slate-400">{{ p.desc }}</span>
          </span>
        </a>
      </div>
    </section>

    <!-- 联系方式 -->
    <section>
      <h2 class="mb-5 text-xl font-semibold">联系方式</h2>
      <div class="flex flex-wrap gap-3">
        <a
          href="mailto:me@yuxm.site"
          class="flex items-center gap-2 rounded-lg border border-slate-300 px-4 py-2.5 text-sm transition-colors hover:border-primary-brand hover:text-primary-brand dark:border-slate-600"
        ><Mail class="h-4 w-4" />me@yuxm.site</a>
        <a
          :href="config.public.githubUrl"
          target="_blank"
          rel="noopener"
          class="flex items-center gap-2 rounded-lg border border-slate-300 px-4 py-2.5 text-sm transition-colors hover:border-primary-brand hover:text-primary-brand dark:border-slate-600"
        ><Github class="h-4 w-4" />GitHub</a>
        <a
          :href="config.public.giteeUrl"
          target="_blank"
          rel="noopener"
          class="flex items-center gap-2 rounded-lg border border-slate-300 px-4 py-2.5 text-sm transition-colors hover:border-primary-brand hover:text-primary-brand dark:border-slate-600"
        >Gitee</a>
      </div>
    </section>
  </div>
</template>
