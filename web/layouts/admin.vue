<script setup lang="ts">
// 管理端布局：侧边栏 + 顶栏（TDesign 风格的简洁中后台）
import { ArrowLeft, FileText, LayoutDashboard, Settings, Users } from 'lucide-vue-next'

const route = useRoute()
const { user, logout } = useAuth()

const menus = [
  { path: '/admin', label: '仪表盘', icon: LayoutDashboard, exact: true },
  { path: '/admin/articles', label: '文章管理', icon: FileText, exact: false },
  { path: '/admin/settings', label: '站点设置', icon: Settings, exact: false },
  { path: '/admin/users', label: '用户管理', icon: Users, exact: false }
]

const isActive = (menu: { path: string; exact: boolean }) =>
  menu.exact ? route.path === menu.path : route.path.startsWith(menu.path)
</script>

<template>
  <div class="flex min-h-screen bg-slate-50 dark:bg-slate-900">
    <!-- 侧边栏 -->
    <aside class="flex w-56 shrink-0 flex-col border-r border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800">
      <div class="flex h-14 items-center gap-2 border-b border-slate-200 px-4 dark:border-slate-700">
        <span class="flex h-7 w-7 items-center justify-center rounded-lg bg-primary-brand font-mono text-xs font-bold text-white">Y</span>
        <span class="font-semibold">管理后台</span>
      </div>
      <nav class="flex-1 space-y-1 p-3">
        <NuxtLink
          v-for="menu in menus"
          :key="menu.path"
          :to="menu.path"
          class="flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm transition-colors"
          :class="isActive(menu)
            ? 'bg-primary-brand text-white'
            : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700'"
        >
          <component :is="menu.icon" class="h-4 w-4" />
          {{ menu.label }}
        </NuxtLink>
      </nav>
      <div class="border-t border-slate-200 p-3 dark:border-slate-700">
        <NuxtLink
          to="/"
          class="mb-1 flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700"
        >
          <ArrowLeft class="h-4 w-4" />返回前台
        </NuxtLink>
        <button
          class="flex w-full cursor-pointer items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30"
          @click="logout()"
        >
          退出登录（{{ user?.nickname }}）
        </button>
      </div>
    </aside>

    <!-- 内容区 -->
    <main class="min-w-0 flex-1 p-6">
      <slot />
    </main>
  </div>
</template>
