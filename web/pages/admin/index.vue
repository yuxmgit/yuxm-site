<script setup lang="ts">
// 管理端仪表盘：访问量、用户数、阅读 Top 文章 + 修改密码入口
import { BarChart, BookOpen, Eye, Users } from 'lucide-vue-next'

definePageMeta({ layout: 'admin', middleware: 'admin-auth' })

const { authFetch } = useAuth()

interface DashboardData {
  total_views: number
  total_users: number
  articles_read: number
  top_articles: Array<{ slug: string; views: number }>
}

const { data: dashboard, pending } = await useAsyncData('admin-dashboard', () =>
  authFetch<DashboardData>('/api/admin/dashboard'),
  { server: false }
)

const stats = computed(() => [
  { label: '总阅读量', value: dashboard.value?.total_views ?? 0, icon: Eye, color: '#2563EB' },
  { label: '注册用户', value: dashboard.value?.total_users ?? 0, icon: Users, color: '#10B981' },
  { label: '有阅读记录的文章', value: dashboard.value?.articles_read ?? 0, icon: BookOpen, color: '#F59E0B' }
])
</script>

<template>
  <div class="animate-fade-in">
    <h1 class="mb-6 text-xl font-semibold">仪表盘</h1>

    <div v-if="pending" class="text-sm text-slate-400">加载中…</div>
    <template v-else>
      <div class="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div v-for="s in stats" :key="s.label" class="site-card p-5">
          <div class="flex items-center justify-between">
            <span class="text-sm text-slate-500 dark:text-slate-400">{{ s.label }}</span>
            <component :is="s.icon" class="h-5 w-5" :style="{ color: s.color }" />
          </div>
          <p class="mt-2 text-3xl font-bold">{{ s.value }}</p>
        </div>
      </div>

      <div class="site-card p-5">
        <h2 class="mb-4 flex items-center gap-2 text-base font-semibold">
          <BarChart class="h-4 w-4 text-primary-brand" />阅读数 Top 10
        </h2>
        <div v-if="dashboard?.top_articles?.length" class="space-y-2">
          <div v-for="item in dashboard.top_articles" :key="item.slug" class="flex items-center gap-3">
            <span class="w-64 shrink-0 truncate font-mono text-xs text-slate-500">{{ item.slug }}</span>
            <div class="h-2 flex-1 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-700">
              <div
                class="h-full rounded-full bg-primary-brand"
                :style="{ width: `${Math.max((item.views / (dashboard.top_articles[0]?.views || 1)) * 100, 4)}%` }"
              />
            </div>
            <span class="w-12 shrink-0 text-right text-xs text-slate-400">{{ item.views }}</span>
          </div>
        </div>
        <p v-else class="text-sm text-slate-400">暂无阅读数据</p>
      </div>
    </template>
  </div>
</template>
