<script setup lang="ts">
// 登录弹窗：手机验证码 / GitHub / Gitee 三种方式 Tab 切换
import { X } from 'lucide-vue-next'

const config = useRuntimeConfig()
const { isOpen, close } = useLoginModal()
const { setAuth } = useAuth()

const tab = ref<'sms' | 'password' | 'oauth'>('sms')
const phone = ref('')
const code = ref('')
const sending = ref(false)
const loggingIn = ref(false)
const countdown = ref(0)
const errorMsg = ref('')
const devCode = ref('') // 开发环境未配置 SMS 时后端返回的验证码提示

// 密码登录 / 注册
const accountMode = ref<'login' | 'register'>('login')
const username = ref('')
const password = ref('')
const nickname = ref('')

let timer: ReturnType<typeof setInterval> | null = null

const startCountdown = () => {
  countdown.value = 60
  timer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0 && timer) {
      clearInterval(timer)
      timer = null
    }
  }, 1000)
}

onUnmounted(() => {
  if (timer) clearInterval(timer)
})

const sendCode = async () => {
  errorMsg.value = ''
  devCode.value = ''
  if (!/^1[3-9]\d{9}$/.test(phone.value)) {
    errorMsg.value = '请输入正确的手机号'
    return
  }
  sending.value = true
  try {
    const res = await $fetch<{ code: number; message: string; data: { dev_code?: string } | null }>(
      '/api/auth/sms/send',
      { baseURL: config.public.apiBase, method: 'POST', body: { phone: phone.value } }
    )
    startCountdown()
    if (res.data?.dev_code) {
      devCode.value = `开发模式（未配置腾讯云 SMS），验证码：${res.data.dev_code}`
    }
  } catch (err: unknown) {
    const e = err as { data?: { message?: string } }
    errorMsg.value = e?.data?.message || '验证码发送失败'
  } finally {
    sending.value = false
  }
}

const smsLogin = async () => {
  errorMsg.value = ''
  if (!/^1[3-9]\d{9}$/.test(phone.value) || !code.value) {
    errorMsg.value = '请输入手机号和验证码'
    return
  }
  loggingIn.value = true
  try {
    const res = await $fetch<{
      code: number
      data: { access_token: string; refresh_token: string; user: never }
    }>('/api/auth/sms/login', {
      baseURL: config.public.apiBase,
      method: 'POST',
      body: { phone: phone.value, code: code.value }
    })
    setAuth(res.data)
    close()
  } catch (err: unknown) {
    const e = err as { data?: { message?: string } }
    errorMsg.value = e?.data?.message || '登录失败'
  } finally {
    loggingIn.value = false
  }
}

const accountSubmit = async () => {
  errorMsg.value = ''
  if (!username.value || password.value.length < 8) {
    errorMsg.value = '用户名不能为空，密码至少 8 位'
    return
  }
  loggingIn.value = true
  try {
    const url = accountMode.value === 'login' ? '/api/auth/login' : '/api/auth/register'
    const body =
      accountMode.value === 'login'
        ? { username: username.value, password: password.value }
        : { username: username.value, password: password.value, nickname: nickname.value }
    const res = await $fetch<{
      code: number
      data: { access_token: string; refresh_token: string; user: never }
    }>(url, { baseURL: config.public.apiBase, method: 'POST', body })
    setAuth(res.data)
    close()
  } catch (err: unknown) {
    const e = err as { data?: { message?: string } }
    errorMsg.value = e?.data?.message || (accountMode.value === 'login' ? '登录失败' : '注册失败')
  } finally {
    loggingIn.value = false
  }
}

const oauthLogin = async (provider: 'github' | 'gitee') => {
  errorMsg.value = ''
  try {
    const res = await $fetch<{ code: number; data: { authorize_url: string } }>(
      `/api/auth/oauth/${provider}/authorize`,
      { baseURL: config.public.apiBase }
    )
    window.location.href = res.data.authorize_url
  } catch (err) {
    console.error('OAuth 跳转失败', err)
    errorMsg.value = '第三方登录暂不可用（请确认已在 .env 配置 OAuth 应用）'
  }
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="isOpen"
      class="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/50 px-4 backdrop-blur-sm"
      @click.self="close"
    >
      <div class="w-full max-w-sm rounded-2xl bg-white p-6 shadow-xl animate-fade-in dark:bg-slate-800">
        <div class="mb-5 flex items-center justify-between">
          <h2 class="text-lg font-semibold">登录</h2>
          <button
            class="cursor-pointer rounded-lg p-1.5 hover:bg-slate-100 dark:hover:bg-slate-700"
            aria-label="关闭"
            @click="close"
          >
            <X class="h-5 w-5" />
          </button>
        </div>

        <div class="mb-5 grid grid-cols-3 gap-1 rounded-lg bg-slate-100 p-1 dark:bg-slate-700">
          <button
            class="cursor-pointer rounded-md px-2 py-1.5 text-sm font-medium transition-colors"
            :class="tab === 'sms' ? 'bg-white shadow dark:bg-slate-800' : 'text-slate-500'"
            @click="tab = 'sms'"
          >验证码</button>
          <button
            class="cursor-pointer rounded-md px-2 py-1.5 text-sm font-medium transition-colors"
            :class="tab === 'password' ? 'bg-white shadow dark:bg-slate-800' : 'text-slate-500'"
            @click="tab = 'password'"
          >账号密码</button>
          <button
            class="cursor-pointer rounded-md px-2 py-1.5 text-sm font-medium transition-colors"
            :class="tab === 'oauth' ? 'bg-white shadow dark:bg-slate-800' : 'text-slate-500'"
            @click="tab = 'oauth'"
          >第三方</button>
        </div>

        <div v-if="tab === 'sms'" class="space-y-3">
          <input
            v-model="phone"
            type="tel"
            maxlength="11"
            placeholder="手机号"
            class="w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2.5 text-sm outline-none transition-colors focus:border-primary-brand dark:border-slate-600"
          />
          <div class="flex gap-2">
            <input
              v-model="code"
              type="text"
              maxlength="6"
              placeholder="验证码"
              class="min-w-0 flex-1 rounded-lg border border-slate-300 bg-transparent px-3 py-2.5 text-sm outline-none transition-colors focus:border-primary-brand dark:border-slate-600"
            />
            <button
              class="shrink-0 cursor-pointer rounded-lg border border-primary-brand px-3 py-2.5 text-sm text-primary-brand transition-colors hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-50 dark:hover:bg-slate-700"
              :disabled="sending || countdown > 0"
              @click="sendCode"
            >
              {{ countdown > 0 ? `${countdown}s` : sending ? '发送中' : '获取验证码' }}
            </button>
          </div>
          <p
            v-if="devCode"
            class="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-600 dark:bg-amber-900/30 dark:text-amber-400"
          >{{ devCode }}</p>
          <button
            class="w-full cursor-pointer rounded-lg bg-primary-brand px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary-brand-dark disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="loggingIn"
            @click="smsLogin"
          >{{ loggingIn ? '登录中…' : '登录' }}</button>
        </div>

        <!-- 账号密码登录 / 注册 -->
        <div v-else-if="tab === 'password'" class="space-y-3">
          <div class="grid grid-cols-2 gap-2 text-center text-xs">
            <button
              class="cursor-pointer rounded-lg py-1.5 font-medium transition-colors"
              :class="accountMode === 'login' ? 'bg-primary-brand text-white' : 'bg-slate-100 text-slate-500 dark:bg-slate-700'"
              @click="accountMode = 'login'"
            >登录</button>
            <button
              class="cursor-pointer rounded-lg py-1.5 font-medium transition-colors"
              :class="accountMode === 'register' ? 'bg-primary-brand text-white' : 'bg-slate-100 text-slate-500 dark:bg-slate-700'"
              @click="accountMode = 'register'"
            >注册新账号</button>
          </div>
          <input
            v-model="username"
            type="text"
            maxlength="32"
            placeholder="用户名（3-32 位字母/数字/下划线）"
            class="w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2.5 text-sm outline-none transition-colors focus:border-primary-brand dark:border-slate-600"
          />
          <input
            v-model="password"
            type="password"
            maxlength="64"
            placeholder="密码（至少 8 位）"
            class="w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2.5 text-sm outline-none transition-colors focus:border-primary-brand dark:border-slate-600"
            @keyup.enter="accountSubmit"
          />
          <input
            v-if="accountMode === 'register'"
            v-model="nickname"
            type="text"
            maxlength="32"
            placeholder="昵称（选填，默认同用户名）"
            class="w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2.5 text-sm outline-none transition-colors focus:border-primary-brand dark:border-slate-600"
          />
          <button
            class="w-full cursor-pointer rounded-lg bg-primary-brand px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary-brand-dark disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="loggingIn"
            @click="accountSubmit"
          >{{ loggingIn ? '提交中…' : accountMode === 'login' ? '登录' : '注册并登录' }}</button>
        </div>

        <div v-else class="space-y-3">
          <button
            class="flex w-full cursor-pointer items-center justify-center gap-2 rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90 dark:bg-slate-700"
            @click="oauthLogin('github')"
          >
            <svg class="h-4 w-4" viewBox="0 0 16 16" fill="currentColor">
              <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z" />
            </svg>
            使用 GitHub 登录
          </button>
          <button
            class="flex w-full cursor-pointer items-center justify-center gap-2 rounded-lg bg-red-500 px-4 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90"
            @click="oauthLogin('gitee')"
          >
            <span class="font-bold">G</span>
            使用 Gitee 登录
          </button>
        </div>

        <p v-if="errorMsg" class="mt-3 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600 dark:bg-red-900/30 dark:text-red-400">
          {{ errorMsg }}
        </p>
      </div>
    </div>
  </Teleport>
</template>
