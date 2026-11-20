/** 管理端路由守卫：非管理员访问 /admin/* 时跳转管理端登录页。 */
export default defineNuxtRouteMiddleware((to) => {
  if (to.path === '/admin/login') return
  const auth = useAuth()
  if (import.meta.client) {
    auth.restore()
  }
  if (!auth.isLoggedIn.value || !auth.isAdmin.value) {
    return navigateTo('/admin/login')
  }
})
