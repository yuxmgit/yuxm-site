// OAuth 回调中转（Nitro 服务端路由）：
// 第三方重定向到这里 → 服务端拿 code/state 调 FastAPI 换 token → 302 回首页并携带登录数据
export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  const code = String(query.code || '')
  const state = String(query.state || '')
  const config = useRuntimeConfig()
  const apiBase = config.public.apiBase

  if (!code || !state) {
    return sendRedirect(event, '/?auth_error=missing_code')
  }

  try {
    const res = await $fetch<{ code: number; data: { access_token: string; refresh_token: string; user: unknown } }>(
      `/api/auth/oauth/github/callback`,
      { baseURL: apiBase, method: 'POST', body: { code, state } }
    )
    // token 通过 URL fragment（#）传给前端，不会进入服务器日志
    const payload = Buffer.from(JSON.stringify(res.data)).toString('base64url')
    return sendRedirect(event, `/#auth_callback=${payload}`)
  } catch (err) {
    console.error('GitHub OAuth 回调失败', err)
    return sendRedirect(event, '/?auth_error=github_callback_failed')
  }
})
