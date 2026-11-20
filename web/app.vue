<script setup lang="ts">
// 根组件：恢复登录态、处理 OAuth 回调数据、挂载全局登录弹窗
const { restore, setAuth } = useAuth()
const route = useRoute()
const router = useRouter()

onMounted(() => {
  restore()
  // OAuth 回调：Nitro 服务端路由 302 回首页，token 在 URL fragment 中
  const hash = window.location.hash
  const match = hash.match(/#auth_callback=([A-Za-z0-9_-]+)/)
  if (match) {
    try {
      const data = JSON.parse(atob(match[1].replace(/-/g, '+').replace(/_/g, '/')))
      setAuth(data)
    } catch (err) {
      console.error('解析 OAuth 回调数据失败', err)
    }
    history.replaceState(null, '', window.location.pathname)
  } else if (route.query.auth_error) {
    console.error('OAuth 登录失败:', route.query.auth_error)
    router.replace({ path: route.path, query: {} })
  }
})
</script>

<template>
  <div class="min-h-screen bg-white text-slate-900 antialiased dark:bg-slate-900 dark:text-slate-100">
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
    <LoginModal />
  </div>
</template>
