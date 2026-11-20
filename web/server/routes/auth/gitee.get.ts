// Gitee OAuth 回调中转（与 github.get.ts 流程一致）
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
      `/api/auth/oauth/gitee/callback`,
      { baseURL: apiBase, method: 'POST', body: { code, state } }
    )
    const payload = Buffer.from(JSON.stringify(res.data)).toString('base64url')
    return sendRedirect(event, `/#auth_callback=${payload}`)
  } catch (err) {
    console.error('Gitee OAuth 回调失败', err)
    return sendRedirect(event, '/?auth_error=gitee_callback_failed')
  }
})
