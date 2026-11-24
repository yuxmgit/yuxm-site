/** 认证状态管理：token 存储、登录态、401 拦截刷新、登出与退出所有设备。 */
export interface UserInfo {
  id: number
  nickname: string
  avatar: string
  role: string
  /** 是否设置了密码（SMS/OAuth 用户首次为 false，设置后为 true） */
  has_password?: boolean
}

const STORAGE_KEY = 'yuxm-auth'

interface AuthStorage {
  accessToken: string
  refreshToken: string
  user: UserInfo
}

export const useAuth = () => {
  const config = useRuntimeConfig()
  const user = useState<UserInfo | null>('auth-user', () => null)
  const accessToken = useState<string>('auth-access', () => '')
  const refreshToken = useState<string>('auth-refresh', () => '')

  const restore = () => {
    if (!import.meta.client) return
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (!raw) return
      const saved = JSON.parse(raw) as AuthStorage
      accessToken.value = saved.accessToken
      refreshToken.value = saved.refreshToken
      user.value = saved.user
    } catch (err) {
      console.error('恢复登录态失败', err)
    }
  }

  const persist = () => {
    if (!import.meta.client) return
    if (accessToken.value && user.value) {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ accessToken: accessToken.value, refreshToken: refreshToken.value, user: user.value })
      )
    } else {
      localStorage.removeItem(STORAGE_KEY)
    }
  }

  const setAuth = (data: { access_token: string; refresh_token: string; user: UserInfo }) => {
    accessToken.value = data.access_token
    refreshToken.value = data.refresh_token
    user.value = data.user
    persist()
  }

  const clearAuth = () => {
    accessToken.value = ''
    refreshToken.value = ''
    user.value = null
    persist()
  }

  /** 更新本地用户信息（修改资料/密码后同步 UI 与 localStorage） */
  const updateUser = (partial: Partial<UserInfo>) => {
    if (user.value) {
      user.value = { ...user.value, ...partial }
      persist()
    }
  }

  /** 用 refresh token 换新 token 对；失败则清登录态 */
  const tryRefresh = async (): Promise<boolean> => {
    if (!refreshToken.value) return false
    try {
      const res = await $fetch<{ code: number; data: AuthStorage }>(`/api/auth/refresh`, {
        baseURL: config.public.apiBase,
        method: 'POST',
        body: { refresh_token: refreshToken.value }
      })
      setAuth(res.data)
      return true
    } catch (err) {
      console.error('刷新凭证失败', err)
      clearAuth()
      return false
    }
  }

  /** 统一认证请求：401 时自动尝试刷新重试一次 */
  const authFetch = async <T>(url: string, options: Record<string, unknown> = {}): Promise<T> => {
    const doRequest = () =>
      $fetch<{ code: number; data: T }>(url, {
        baseURL: config.public.apiBase,
        ...options,
        headers: { ...(options.headers as object), Authorization: `Bearer ${accessToken.value}` }
      })
    try {
      const res = await doRequest()
      return res.data
    } catch (err: unknown) {
      const status = (err as { status?: number })?.status
      if (status === 401 && (await tryRefresh())) {
        const res = await doRequest()
        return res.data
      }
      throw err
    }
  }

  const logout = async () => {
    try {
      await authFetch('/api/auth/logout', {
        method: 'POST',
        body: { refresh_token: refreshToken.value }
      })
    } catch (err) {
      console.error('登出请求失败（本地状态仍清除）', err)
    }
    clearAuth()
  }

  /** 退出所有设备：服务端 INCR 版本号，全部旧 token 失效 */
  const logoutAll = async () => {
    await authFetch('/api/auth/logout-all', { method: 'POST' })
    clearAuth()
  }

  const isLoggedIn = computed(() => Boolean(user.value && accessToken.value))
  const isAdmin = computed(() => user.value?.role === 'admin')

  return {
    user,
    isLoggedIn,
    isAdmin,
    accessToken,
    refreshToken,
    restore,
    setAuth,
    clearAuth,
    updateUser,
    tryRefresh,
    authFetch,
    logout,
    logoutAll
  }
}
