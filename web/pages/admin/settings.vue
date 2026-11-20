<script setup lang="ts">
// 站点设置：站点名称/SEO/Hero 简介/公告/备案号/开源链接（保存后前台立即生效）
import { KeyRound, Save } from 'lucide-vue-next'

definePageMeta({ layout: 'admin', middleware: 'admin-auth' })

const { authFetch } = useAuth()

const fields: Array<{ key: string; label: string; type?: string; help?: string }> = [
  { key: 'site_name', label: '站点名称' },
  { key: 'seo_description', label: 'SEO 描述', type: 'textarea' },
  { key: 'hero_intro', label: '首页 Hero 简介', type: 'textarea' },
  { key: 'announcement', label: '全站公告', help: '留空则不展示' },
  { key: 'icp', label: 'ICP 备案号', help: '备案通过后填写，如：粤ICP备XXXXXXXX号' },
  { key: 'github_url', label: 'GitHub 主页' },
  { key: 'gitee_url', label: 'Gitee 主页' }
]

const form = ref<Record<string, string>>({})
const loaded = ref(false)
const saving = ref(false)
const saved = ref(false)
const errorMsg = ref('')

onMounted(async () => {
  try {
    const data = await authFetch<Record<string, string>>('/api/admin/settings')
    form.value = Object.fromEntries(fields.map(f => [f.key, String(data[f.key] ?? '')]))
    loaded.value = true
  } catch (err) {
    console.error('读取站点设置失败', err)
    errorMsg.value = '读取设置失败'
  }
})

const save = async () => {
  saving.value = true
  errorMsg.value = ''
  try {
    await authFetch('/api/admin/settings', { method: 'PUT', body: { values: form.value } })
    saved.value = true
    setTimeout(() => { saved.value = false }, 1500)
  } catch (err) {
    console.error('保存站点设置失败', err)
    errorMsg.value = '保存失败'
  } finally {
    saving.value = false
  }
}

// 修改密码
const oldPwd = ref('')
const newPwd = ref('')
const pwdMsg = ref('')
const pwdError = ref('')
const changing = ref(false)

const changePassword = async () => {
  pwdError.value = ''
  pwdMsg.value = ''
  if (newPwd.value.length < 8) {
    pwdError.value = '新密码至少 8 位'
    return
  }
  changing.value = true
  try {
    await authFetch('/api/admin/change-password', {
      method: 'POST',
      body: { old_password: oldPwd.value, new_password: newPwd.value }
    })
    pwdMsg.value = '密码已修改，所有设备已下线，请用新密码重新登录'
  } catch (err: unknown) {
    const e = err as { data?: { message?: string } }
    pwdError.value = e?.data?.message || '修改失败'
  } finally {
    changing.value = false
  }
}
</script>

<template>
  <div class="animate-fade-in">
    <h1 class="mb-6 text-xl font-semibold">站点设置</h1>

    <div class="site-card mb-8 p-6">
      <div v-if="!loaded" class="text-sm text-slate-400">加载中…</div>
      <div v-else class="max-w-xl space-y-4">
        <div v-for="f in fields" :key="f.key">
          <label class="mb-1.5 block text-sm font-medium">{{ f.label }}</label>
          <textarea
            v-if="f.type === 'textarea'"
            v-model="form[f.key]"
            rows="3"
            class="w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 text-sm outline-none focus:border-primary-brand dark:border-slate-600"
          />
          <input
            v-else
            v-model="form[f.key]"
            type="text"
            class="w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 text-sm outline-none focus:border-primary-brand dark:border-slate-600"
          />
          <p v-if="f.help" class="mt-1 text-xs text-slate-400">{{ f.help }}</p>
        </div>
        <div class="flex items-center gap-3">
          <button
            class="flex cursor-pointer items-center gap-2 rounded-lg bg-primary-brand px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-brand-dark disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="saving"
            @click="save"
          >
            <Save class="h-4 w-4" />{{ saving ? '保存中…' : saved ? '已保存' : '保存设置' }}
          </button>
          <span v-if="errorMsg" class="text-sm text-red-500">{{ errorMsg }}</span>
        </div>
      </div>
    </div>

    <!-- 修改密码 -->
    <div class="site-card p-6">
      <h2 class="mb-1 flex items-center gap-2 text-base font-semibold">
        <KeyRound class="h-4 w-4 text-primary-brand" />修改管理员密码
      </h2>
      <p class="mb-4 text-xs text-slate-400">上线后首次登录请立即修改默认密码；改密后所有设备将被踢下线</p>
      <div class="flex max-w-xl flex-col gap-3 sm:flex-row">
        <input
          v-model="oldPwd"
          type="password"
          placeholder="原密码"
          class="flex-1 rounded-lg border border-slate-300 bg-transparent px-3 py-2 text-sm outline-none focus:border-primary-brand dark:border-slate-600"
        />
        <input
          v-model="newPwd"
          type="password"
          placeholder="新密码（至少 8 位）"
          class="flex-1 rounded-lg border border-slate-300 bg-transparent px-3 py-2 text-sm outline-none focus:border-primary-brand dark:border-slate-600"
        />
        <button
          class="shrink-0 cursor-pointer rounded-lg border border-primary-brand px-4 py-2 text-sm text-primary-brand hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-50 dark:hover:bg-slate-700"
          :disabled="changing"
          @click="changePassword"
        >{{ changing ? '修改中…' : '修改密码' }}</button>
      </div>
      <p v-if="pwdMsg" class="mt-3 rounded-lg bg-emerald-50 px-3 py-2 text-xs text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400">{{ pwdMsg }}</p>
      <p v-if="pwdError" class="mt-3 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600 dark:bg-red-900/30 dark:text-red-400">{{ pwdError }}</p>
    </div>
  </div>
</template>
