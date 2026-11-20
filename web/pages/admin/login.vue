<script setup lang="ts">
// 管理端登录：账号密码（初始 yuxiangming / yuxiangming，上线后必须修改）
import { Lock, User } from 'lucide-vue-next'

definePageMeta({ layout: 'admin' })

const config = useRuntimeConfig()
const { setAuth } = useAuth()
const router = useRouter()

const username = ref('')
const password = ref('')
const errorMsg = ref('')
const loading = ref(false)

const doLogin = async () => {
  errorMsg.value = ''
  if (!username.value || !password.value) {
    errorMsg.value = '请输入用户名和密码'
    return
  }
  loading.value = true
  try {
    const res = await $fetch<{ code: number; data: { access_token: string; refresh_token: string; user: never } }>(
      '/api/auth/admin/login',
      { baseURL: config.public.apiBase, method: 'POST', body: { username: username.value, password: password.value } }
    )
    setAuth(res.data)
    router.push('/admin')
  } catch (err: unknown) {
    const e = err as { data?: { message?: string } }
    errorMsg.value = e?.data?.message || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="flex min-h-screen items-center justify-center bg-slate-50 dark:bg-slate-900">
    <div class="w-full max-w-sm rounded-2xl bg-white p-8 shadow-md dark:bg-slate-800">
      <div class="mb-6 text-center">
        <span class="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-primary-brand font-mono text-lg font-bold text-white">Y</span>
        <h1 class="text-lg font-semibold">yuxm.site 管理后台</h1>
        <p class="mt-1 text-xs text-slate-400">初始账号 yuxiangming，上线后请立即修改密码</p>
      </div>
      <div class="space-y-3">
        <div class="relative">
          <User class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            v-model="username"
            type="text"
            placeholder="用户名"
            class="w-full rounded-lg border border-slate-300 bg-transparent py-2.5 pl-9 pr-3 text-sm outline-none transition-colors focus:border-primary-brand dark:border-slate-600"
            @keyup.enter="doLogin"
          />
        </div>
        <div class="relative">
          <Lock class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            v-model="password"
            type="password"
            placeholder="密码"
            class="w-full rounded-lg border border-slate-300 bg-transparent py-2.5 pl-9 pr-3 text-sm outline-none transition-colors focus:border-primary-brand dark:border-slate-600"
            @keyup.enter="doLogin"
          />
        </div>
        <button
          class="w-full cursor-pointer rounded-lg bg-primary-brand px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary-brand-dark disabled:cursor-not-allowed disabled:opacity-50"
          :disabled="loading"
          @click="doLogin"
        >{{ loading ? '登录中…' : '登录' }}</button>
        <p v-if="errorMsg" class="rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600 dark:bg-red-900/30 dark:text-red-400">{{ errorMsg }}</p>
      </div>
    </div>
  </div>
</template>
