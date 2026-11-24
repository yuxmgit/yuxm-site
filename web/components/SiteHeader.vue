<script setup lang="ts">
// 顶部导航：Logo、分类下拉、搜索入口、暗色切换、登录按钮/用户菜单（固定定位）
import { ChevronDown, LogOut, LogOut as LogOutAll, Moon, Search, Settings, Sun, User, UserCircle } from 'lucide-vue-next'

const { isDark, toggle } = useDarkMode()
const { open } = useLoginModal()
const { isLoggedIn, user, logout, logoutAll, isAdmin } = useAuth()

const mobileOpen = ref(false)
const catOpen = ref(false)
const userMenuOpen = ref(false)
const route = useRoute()
const router = useRouter()

const loginVisible = computed(() => route.path.startsWith('/admin') === false)

watch(() => route.fullPath, () => {
  mobileOpen.value = false
  catOpen.value = false
  userMenuOpen.value = false
})

const doLogout = async () => {
  await logout()
  userMenuOpen.value = false
}

const doLogoutAll = async () => {
  await logoutAll()
  userMenuOpen.value = false
}
</script>

<template>
  <header class="fixed inset-x-0 top-0 z-50 h-16 border-b border-slate-200 bg-white/85 backdrop-blur-md dark:border-slate-700 dark:bg-slate-900/85">
    <nav class="mx-auto flex h-full max-w-6xl items-center justify-between px-4">
      <NuxtLink to="/" class="flex items-center gap-2">
        <span class="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-brand font-mono text-sm font-bold text-white">Y</span>
        <span class="text-lg font-semibold">虞先森的技术站</span>
      </NuxtLink>

      <!-- 桌面端导航 -->
      <div class="hidden items-center gap-1 md:flex">
        <div
          class="relative"
          @mouseenter="catOpen = true"
          @mouseleave="catOpen = false"
        >
          <button class="flex cursor-pointer items-center gap-1 rounded-lg px-3 py-2 text-sm font-medium hover:bg-slate-100 dark:hover:bg-slate-800">
            分类
            <ChevronDown class="h-4 w-4 transition-transform" :class="catOpen ? 'rotate-180' : ''" />
          </button>
          <transition name="fade">
            <div
              v-if="catOpen"
              class="absolute left-0 top-full w-80 rounded-xl border border-slate-200 bg-white p-2 shadow-lg dark:border-slate-700 dark:bg-slate-800"
            >
              <NuxtLink
                v-for="cat in CATEGORIES"
                :key="cat.key"
                :to="`/category/${cat.key}`"
                class="flex items-start gap-3 rounded-lg p-2.5 hover:bg-slate-100 dark:hover:bg-slate-700"
              >
                <span class="mt-1 h-2 w-2 shrink-0 rounded-full" :style="{ backgroundColor: cat.color }" />
                <span>
                  <span class="block text-sm font-medium">{{ cat.name }}</span>
                  <span class="block text-xs text-slate-500 dark:text-slate-400">{{ cat.description }}</span>
                </span>
              </NuxtLink>
            </div>
          </transition>
        </div>

        <NuxtLink to="/series/redis-cluster-in-action" class="rounded-lg px-3 py-2 text-sm font-medium hover:bg-slate-100 dark:hover:bg-slate-800">系列</NuxtLink>
        <NuxtLink to="/about" class="rounded-lg px-3 py-2 text-sm font-medium hover:bg-slate-100 dark:hover:bg-slate-800">关于</NuxtLink>
      </div>

      <div class="flex items-center gap-1">
        <button
          class="cursor-pointer rounded-lg p-2 hover:bg-slate-100 dark:hover:bg-slate-800"
          aria-label="搜索"
          title="搜索"
        >
          <Search class="h-5 w-5" />
        </button>
        <button
          class="cursor-pointer rounded-lg p-2 hover:bg-slate-100 dark:hover:bg-slate-800"
          aria-label="切换暗色模式"
          @click="toggle"
        >
          <Sun v-if="isDark" class="h-5 w-5" />
          <Moon v-else class="h-5 w-5" />
        </button>
        <!-- 已登录：用户菜单 -->
        <div v-if="isLoggedIn && loginVisible" class="relative">
          <button
            class="flex cursor-pointer items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-slate-100 dark:hover:bg-slate-800"
            @click="userMenuOpen = !userMenuOpen"
          >
            <span class="flex h-7 w-7 items-center justify-center rounded-full bg-primary-brand text-xs font-bold text-white">
              {{ (user?.nickname || 'U').slice(0, 1) }}
            </span>
            <span class="hidden text-sm font-medium sm:block">{{ user?.nickname }}</span>
            <ChevronDown class="h-3.5 w-3.5" />
          </button>
          <transition name="fade">
            <div
              v-if="userMenuOpen"
              class="absolute right-0 top-full mt-1 w-44 rounded-xl border border-slate-200 bg-white p-1.5 shadow-lg dark:border-slate-700 dark:bg-slate-800"
            >
              <button
                class="flex w-full cursor-pointer items-center gap-2 rounded-lg px-3 py-2 text-sm hover:bg-slate-100 dark:hover:bg-slate-700"
                @click="router.push('/profile')"
              >
                <UserCircle class="h-4 w-4" />个人中心
              </button>
              <button
                v-if="isAdmin"
                class="flex w-full cursor-pointer items-center gap-2 rounded-lg px-3 py-2 text-sm hover:bg-slate-100 dark:hover:bg-slate-700"
                @click="router.push('/admin')"
              >
                <Settings class="h-4 w-4" />管理后台
              </button>
              <button
                class="flex w-full cursor-pointer items-center gap-2 rounded-lg px-3 py-2 text-sm hover:bg-slate-100 dark:hover:bg-slate-700"
                @click="doLogout"
              >
                <LogOut class="h-4 w-4" />退出登录
              </button>
              <button
                class="flex w-full cursor-pointer items-center gap-2 rounded-lg px-3 py-2 text-sm text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30"
                @click="doLogoutAll"
              >
                <LogOutAll class="h-4 w-4" />退出所有设备
              </button>
            </div>
          </transition>
        </div>
        <button
          v-else-if="loginVisible"
          class="ml-1 cursor-pointer rounded-lg bg-primary-brand px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-brand-dark"
          @click="open()"
        >
          <span class="flex items-center gap-1.5"><User class="h-4 w-4" />登录</span>
        </button>
        <!-- 移动端菜单按钮 -->
        <button
          class="cursor-pointer rounded-lg p-2 hover:bg-slate-100 md:hidden dark:hover:bg-slate-800"
          aria-label="菜单"
          @click="mobileOpen = !mobileOpen"
        >
          <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path v-if="!mobileOpen" d="M4 6h16M4 12h16M4 18h16" />
            <path v-else d="M6 6l12 12M18 6L6 18" />
          </svg>
        </button>
      </div>
    </nav>

    <!-- 移动端下拉菜单 -->
    <transition name="fade">
      <div v-if="mobileOpen" class="border-t border-slate-200 bg-white px-4 py-3 md:hidden dark:border-slate-700 dark:bg-slate-900">
        <NuxtLink to="/" class="block rounded-lg px-3 py-2 text-sm hover:bg-slate-100 dark:hover:bg-slate-800">首页</NuxtLink>
        <NuxtLink to="/about" class="block rounded-lg px-3 py-2 text-sm hover:bg-slate-100 dark:hover:bg-slate-800">关于</NuxtLink>
        <div class="mt-1 border-t border-slate-200 pt-2 dark:border-slate-700">
          <NuxtLink
            v-for="cat in CATEGORIES"
            :key="cat.key"
            :to="`/category/${cat.key}`"
            class="block rounded-lg px-3 py-2 text-sm hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            {{ cat.name }}
          </NuxtLink>
        </div>
      </div>
    </transition>
  </header>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
