<script setup lang="ts">
// 用户管理：列表、踢下线、封禁/解封（危险操作二次确认）
import { ShieldBan, ShieldCheck, LogOut } from 'lucide-vue-next'

definePageMeta({ layout: 'admin', middleware: 'admin-auth' })

const { authFetch, user: me } = useAuth()

interface UserRow {
  id: number
  username: string | null
  phone: string | null
  nickname: string
  role: string
  is_banned: boolean
  created_at: string | null
}

const items = ref<UserRow[]>([])
const total = ref(0)
const page = ref(1)
const size = 20
const loading = ref(false)

const load = async () => {
  loading.value = true
  try {
    const data = await authFetch<{ total: number; items: UserRow[] }>(`/api/admin/users?page=${page.value}&size=${size}`)
    items.value = data.items
    total.value = data.total
  } catch (err) {
    console.error('读取用户列表失败', err)
  } finally {
    loading.value = false
  }
}

await load()

const totalPages = computed(() => Math.max(Math.ceil(total.value / size), 1))

const kickedId = ref<number | null>(null)
const kick = async (row: UserRow) => {
  if (!confirm(`确认踢下线「${row.nickname}」？该用户所有登录将立即失效。`)) return
  try {
    await authFetch(`/api/admin/users/${row.id}/kick`, { method: 'POST' })
    kickedId.value = row.id
    setTimeout(() => { kickedId.value = null }, 1500)
  } catch (err) {
    console.error('踢下线失败', err)
    alert('操作失败')
  }
}

const toggleBan = async (row: UserRow) => {
  const action = row.is_banned ? '解封' : '封禁'
  if (!confirm(`确认${action}「${row.nickname}」？${row.is_banned ? '' : '封禁将同时踢下线。'}`)) return
  try {
    await authFetch(`/api/admin/users/${row.id}/ban?banned=${!row.is_banned}`, { method: 'POST' })
    await load()
  } catch (err: unknown) {
    const e = err as { data?: { message?: string } }
    alert(e?.data?.message || '操作失败')
  }
}

const fmtDate = (iso: string | null) => (iso ? iso.slice(0, 10) : '-')
</script>

<template>
  <div class="animate-fade-in">
    <h1 class="mb-4 text-xl font-semibold">用户管理</h1>
    <p class="mb-4 text-xs text-slate-400">共 {{ total }} 个用户 · 踢下线通过递增 token 版本号实现，所有旧凭证立即失效</p>

    <div class="site-card overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-slate-200 bg-slate-50 text-left text-xs text-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400">
            <th class="px-4 py-3">用户</th>
            <th class="px-3 py-3">角色</th>
            <th class="px-3 py-3">状态</th>
            <th class="px-3 py-3">注册时间</th>
            <th class="px-3 py-3">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="5" class="px-4 py-8 text-center text-slate-400">加载中…</td>
          </tr>
          <tr v-for="row in items" v-else :key="row.id" class="border-b border-slate-100 last:border-0 dark:border-slate-700/50">
            <td class="px-4 py-3">
              <span class="font-medium">{{ row.nickname }}</span>
              <span class="block text-xs text-slate-400">
                {{ row.username ? `管理员账号 ${row.username}` : row.phone ? `手机 ${row.phone}` : `ID ${row.id}` }}
              </span>
            </td>
            <td class="px-3 py-3">
              <span
                class="rounded-full px-2 py-0.5 text-xs font-medium"
                :class="row.role === 'admin' ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400' : 'bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-300'"
              >{{ row.role === 'admin' ? '管理员' : '用户' }}</span>
            </td>
            <td class="px-3 py-3">
              <span v-if="row.is_banned" class="rounded-full bg-red-50 px-2 py-0.5 text-xs text-red-500 dark:bg-red-900/30">已封禁</span>
              <span v-else class="rounded-full bg-emerald-50 px-2 py-0.5 text-xs text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400">正常</span>
            </td>
            <td class="px-3 py-3 text-xs text-slate-400">{{ fmtDate(row.created_at) }}</td>
            <td class="px-3 py-3">
              <div class="flex gap-2">
                <button
                  v-if="row.id !== me?.id"
                  class="flex cursor-pointer items-center gap-1 rounded-lg border border-slate-300 px-2.5 py-1.5 text-xs hover:border-amber-400 hover:text-amber-500 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-600"
                  :disabled="kickedId === row.id"
                  @click="kick(row)"
                >
                  <LogOut class="h-3.5 w-3.5" />{{ kickedId === row.id ? '已踢下线' : '踢下线' }}
                </button>
                <button
                  v-if="row.id !== me?.id"
                  class="flex cursor-pointer items-center gap-1 rounded-lg border px-2.5 py-1.5 text-xs"
                  :class="row.is_banned
                    ? 'border-emerald-300 text-emerald-600 hover:bg-emerald-50 dark:border-emerald-700 dark:hover:bg-emerald-900/30'
                    : 'border-red-200 text-red-500 hover:bg-red-50 dark:border-red-800 dark:hover:bg-red-900/30'"
                  @click="toggleBan(row)"
                >
                  <ShieldCheck v-if="row.is_banned" class="h-3.5 w-3.5" />
                  <ShieldBan v-else class="h-3.5 w-3.5" />
                  {{ row.is_banned ? '解封' : '封禁' }}
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="totalPages > 1" class="mt-4 flex items-center justify-center gap-2">
      <button
        class="cursor-pointer rounded-lg border border-slate-300 px-3 py-1.5 text-sm disabled:cursor-not-allowed disabled:opacity-40 dark:border-slate-600"
        :disabled="page <= 1"
        @click="page--; load()"
      >上一页</button>
      <span class="text-sm text-slate-500">{{ page }} / {{ totalPages }}</span>
      <button
        class="cursor-pointer rounded-lg border border-slate-300 px-3 py-1.5 text-sm disabled:cursor-not-allowed disabled:opacity-40 dark:border-slate-600"
        :disabled="page >= totalPages"
        @click="page++; load()"
      >下一页</button>
    </div>
  </div>
</template>
