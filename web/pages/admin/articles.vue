<script setup lang="ts">
// 文章管理：在线文章（数据库，支持新增/编辑/删除/批量）+ 仓库静态文章（展示覆盖）
import { Pencil, Plus, RefreshCw, Search, Star, Pin, Trash2 } from 'lucide-vue-next'
import type { ArticleMeta, DbArticleRow } from '~/composables/useArticleMeta'

definePageMeta({ layout: 'admin', middleware: 'admin-auth' })

const { authFetch } = useAuth()
const router = useRouter()

const activeTab = ref<'online' | 'repo'>('online')

// ---------------- 在线文章（数据库） ----------------

interface PostRow extends DbArticleRow {
  updatedAt: string | null
  viewCount: number
}

const keyword = ref('')
const filterCategory = ref('')
const filterStatus = ref('')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const items = ref<PostRow[]>([])
const loading = ref(false)
const selected = ref<Set<number>>(new Set())

// 搜索防抖 300ms
let searchTimer: ReturnType<typeof setTimeout> | null = null
watch([keyword, filterCategory, filterStatus], () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { page.value = 1; load() }, 300)
})

const load = async () => {
  loading.value = true
  try {
    const res = await authFetch<{ total: number; items: PostRow[]; page: number }>('/api/admin/posts', {
      method: 'GET',
      query: {
        page: page.value,
        size: pageSize.value,
        q: keyword.value,
        category: filterCategory.value,
        status: filterStatus.value
      }
    })
    total.value = res.total
    items.value = res.items
    selected.value = new Set()
  } catch (err) {
    console.error('加载在线文章失败', err)
  } finally {
    loading.value = false
  }
}

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))
const goPage = (p: number) => { page.value = Math.min(Math.max(1, p), totalPages.value); load() }

const toggleSelect = (id: number) => {
  const next = new Set(selected.value)
  if (next.has(id)) next.delete(id); else next.add(id)
  selected.value = next
}
const allChecked = computed(() => items.value.length > 0 && items.value.every(i => selected.value.has(i.id)))
const toggleAll = () => {
  selected.value = allChecked.value ? new Set() : new Set(items.value.map(i => i.id))
}

const busy = ref(false)
const flash = ref('')
const notify = (msg: string) => { flash.value = msg; setTimeout(() => { flash.value = '' }, 2000) }

const patchFlags = async (row: PostRow, field: 'status' | 'featured' | 'pinned') => {
  try {
    await authFetch(`/api/admin/posts/${row.id}/flags`, {
      method: 'PATCH',
      body: { [field]: row[field] }
    })
  } catch (err) {
    console.error('更新失败', err)
    await load() // 失败回滚为服务端状态
  }
}

const removeOne = async (row: PostRow) => {
  if (!window.confirm(`确定删除「${row.title}」？删除后前台立即不可见，且不可恢复。`)) return
  await authFetch(`/api/admin/posts/${row.id}`, { method: 'DELETE' })
  notify('已删除')
  await load()
}

const batchAction = async (action: 'publish' | 'draft' | 'feature' | 'delete') => {
  const ids = [...selected.value]
  if (!ids.length) return
  if (action === 'delete' && !window.confirm(`确定批量删除选中的 ${ids.length} 篇？不可恢复。`)) return
  busy.value = true
  try {
    const res = await authFetch<{ message?: string }>('/api/admin/posts/batch', { method: 'POST', body: { action, ids } })
    notify(res.message || '操作成功')
    await load()
  } catch (err) {
    console.error('批量操作失败', err)
  } finally {
    busy.value = false
  }
}

const publishOne = async (row: PostRow) => {
  row.status = row.status === 'published' ? 'draft' : 'published'
  await patchFlags(row, 'status')
}

// ---------------- 仓库静态文章（展示覆盖，原功能保留） ----------------

interface OverrideRow { slug: string; status: string; featured: boolean; pinned: boolean; summary: string }

const { data: contentDocs } = await useAsyncData('admin-content-list', () =>
  queryCollection('content')
    .select('title', 'description', 'category', 'date', 'path')
    .order('date', 'DESC')
    .all()
)

const { data: overridesResp } = await useAsyncData('admin-overrides', () =>
  authFetch('/api/admin/articles', { method: 'GET' }),
  { server: false }
)

const overrideMap = computed(() => {
  const map = new Map<string, OverrideRow>()
  const resp = overridesResp.value as unknown as OverrideRow[] | null
  for (const row of resp || []) map.set(row.slug, row)
  return map
})

interface RepoRow {
  slug: string; title: string; category: string; date: string
  status: string; featured: boolean; pinned: boolean; summary: string
}

const repoKeyword = ref('')
const repoRows = computed<RepoRow[]>(() => {
  const docs = (contentDocs.value || []) as Array<{ title: string; description?: string; category: string; date: string; path?: string }>
  const list = docs.map(d => {
    const slug = (d.path || '').replace(/^\//, '')
    const ov = overrideMap.value.get(slug)
    return { slug, title: d.title, category: d.category, date: d.date, status: ov?.status || 'published', featured: ov?.featured || false, pinned: ov?.pinned || false, summary: ov?.summary || '' }
  })
  if (!repoKeyword.value) return list
  const kw = repoKeyword.value.toLowerCase()
  return list.filter(r => r.title.toLowerCase().includes(kw) || r.slug.includes(kw))
})

const savingSlug = ref<string | null>(null)
const savedSlug = ref<string | null>(null)
const saveRepoRow = async (row: RepoRow) => {
  savingSlug.value = row.slug
  try {
    await authFetch(`/api/admin/articles/${row.slug}`, {
      method: 'PUT',
      body: { status: row.status, featured: row.featured, pinned: row.pinned, summary: row.summary, cover: '' }
    })
    savedSlug.value = row.slug
    setTimeout(() => { savedSlug.value = null }, 1500)
  } catch (err) {
    console.error('保存覆盖信息失败', err)
  } finally {
    savingSlug.value = null
  }
}

onMounted(load)
</script>

<template>
  <div class="animate-fade-in">
    <div class="mb-4 flex items-center justify-between">
      <h1 class="text-xl font-semibold">文章管理</h1>
      <div class="flex items-center gap-2">
        <span v-if="flash" class="rounded-md bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400">{{ flash }}</span>
        <button class="cursor-pointer rounded-lg border border-slate-300 px-3 py-1.5 text-xs dark:border-slate-600" @click="load"><RefreshCw class="inline h-3.5 w-3.5" /> 刷新</button>
        <button class="cursor-pointer rounded-lg bg-primary-brand px-3 py-1.5 text-xs font-medium text-white hover:bg-primary-brand-dark" @click="router.push('/admin/posts-edit')"><Plus class="inline h-3.5 w-3.5" /> 新增文章</button>
      </div>
    </div>

    <div class="mb-4 flex gap-2">
      <button v-for="t in [{ k: 'online', label: `在线文章（${total}）` }, { k: 'repo', label: '仓库文章' }]" :key="t.k"
        class="cursor-pointer rounded-lg px-4 py-2 text-sm font-medium"
        :class="activeTab === t.k ? 'bg-primary-brand text-white' : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'"
        @click="activeTab = t.k as 'online' | 'repo'"
      >{{ t.label }}</button>
    </div>

    <!-- ============ 在线文章（数据库） ============ -->
    <div v-if="activeTab === 'online'">
      <div class="mb-3 flex flex-wrap items-center gap-2">
        <div class="relative">
          <Search class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input v-model="keyword" type="text" placeholder="搜索标题或 slug"
            class="w-56 rounded-lg border border-slate-300 bg-white py-2 pl-9 pr-3 text-sm outline-none focus:border-primary-brand dark:border-slate-600 dark:bg-slate-800" />
        </div>
        <select v-model="filterCategory" class="cursor-pointer rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800">
          <option value="">全部分类</option>
          <option v-for="c in CATEGORIES" :key="c.key" :value="c.key">{{ c.name }}</option>
        </select>
        <select v-model="filterStatus" class="cursor-pointer rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800">
          <option value="">全部状态</option>
          <option value="published">已发布</option>
          <option value="draft">草稿</option>
        </select>
        <select v-model.number="pageSize" class="cursor-pointer rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800" @change="page = 1; load()">
          <option :value="10">10 条/页</option><option :value="20">20 条/页</option><option :value="50">50 条/页</option>
        </select>
      </div>

      <div v-if="selected.size" class="mb-3 flex items-center gap-2 rounded-lg border border-primary-brand/30 bg-primary-brand/5 px-4 py-2 text-sm">
        <span class="text-slate-600 dark:text-slate-300">已选 {{ selected.size }} 篇：</span>
        <button class="rounded-md bg-emerald-500 px-3 py-1 text-xs text-white disabled:opacity-50" :disabled="busy" @click="batchAction('publish')">发布</button>
        <button class="rounded-md bg-slate-500 px-3 py-1 text-xs text-white disabled:opacity-50" :disabled="busy" @click="batchAction('draft')">转草稿</button>
        <button class="rounded-md bg-amber-500 px-3 py-1 text-xs text-white disabled:opacity-50" :disabled="busy" @click="batchAction('feature')">设为精选</button>
        <button class="rounded-md bg-rose-500 px-3 py-1 text-xs text-white disabled:opacity-50" @click="batchAction('delete')">删除</button>
      </div>
      <div class="site-card overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-slate-200 bg-slate-50 text-left text-xs text-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400">
              <th class="px-3 py-3"><input type="checkbox" :checked="allChecked" @change="toggleAll" /></th>
              <th class="px-4 py-3">文章</th>
              <th class="px-3 py-3">状态</th>
              <th class="px-2 py-3 text-center">精选</th>
              <th class="px-2 py-3 text-center">置顶</th>
              <th class="px-3 py-3">浏览</th>
              <th class="px-3 py-3">更新时间</th>
              <th class="px-3 py-3">操作</th>
            </tr>
          </thead>
          <tbody v-if="!loading">
            <tr v-for="row in items" :key="row.id" class="border-b border-slate-100 last:border-0 dark:border-slate-700/50">
              <td class="px-3 py-3"><input type="checkbox" :checked="selected.has(row.id)" @change="toggleSelect(row.id)" /></td>
              <td class="px-4 py-3">
                <NuxtLink :to="`/posts/${row.slug}`" target="_blank" class="font-medium hover:text-primary-brand">{{ row.title }}</NuxtLink>
                <span class="block font-mono text-xs text-slate-400">{{ row.category }} · {{ row.slug }}</span>
              </td>
              <td class="px-3 py-3">
                <button class="cursor-pointer rounded-full px-2.5 py-1 text-xs font-medium"
                  :class="row.status === 'published' ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400' : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'"
                  @click="publishOne(row)"
                >{{ row.status === 'published' ? '已发布' : '草稿' }}</button>
              </td>
              <td class="px-2 py-3 text-center">
                <button class="cursor-pointer rounded-md p-1.5" :class="row.featured ? 'text-amber-500' : 'text-slate-300 dark:text-slate-600'" @click="row.featured = !row.featured; patchFlags(row, 'featured')">
                  <Star class="h-4 w-4" :fill="row.featured ? 'currentColor' : 'none'" />
                </button>
              </td>
              <td class="px-2 py-3 text-center">
                <button class="cursor-pointer rounded-md p-1.5" :class="row.pinned ? 'text-primary-brand' : 'text-slate-300 dark:text-slate-600'" @click="row.pinned = !row.pinned; patchFlags(row, 'pinned')">
                  <Pin class="h-4 w-4" :fill="row.pinned ? 'currentColor' : 'none'" />
                </button>
              </td>
              <td class="px-3 py-3 text-slate-500">{{ row.viewCount }}</td>
              <td class="px-3 py-3 text-xs text-slate-400">{{ row.updatedAt?.slice(0, 16).replace('T', ' ') }}</td>
              <td class="px-3 py-3">
                <div class="flex items-center gap-1.5">
                  <button class="cursor-pointer rounded-md border border-slate-300 p-1.5 hover:border-primary-brand hover:text-primary-brand dark:border-slate-600" title="编辑" @click="router.push(`/admin/posts-edit?id=${row.id}`)">
                    <Pencil class="h-3.5 w-3.5" />
                  </button>
                  <button class="cursor-pointer rounded-md border border-slate-300 p-1.5 text-rose-500 hover:border-rose-400 dark:border-slate-600" title="删除" @click="removeOne(row)">
                    <Trash2 class="h-3.5 w-3.5" />
                  </button>
                </div>
              </td>
            </tr>
            <tr v-if="!items.length"><td colspan="8" class="px-4 py-10 text-center text-sm text-slate-400">还没有在线文章，点右上角「新增文章」写第一篇</td></tr>
          </tbody>
        </table>
        <div v-if="loading" class="py-10 text-center text-sm text-slate-400">加载中…</div>
      </div>

      <div v-if="totalPages > 1" class="mt-3 flex items-center justify-between text-sm text-slate-500">
        <span>共 {{ total }} 篇 · 第 {{ page }}/{{ totalPages }} 页</span>
        <div class="flex gap-1.5">
          <button class="cursor-pointer rounded-md border border-slate-300 px-3 py-1 disabled:opacity-40 dark:border-slate-600" :disabled="page <= 1" @click="goPage(page - 1)">上一页</button>
          <button class="cursor-pointer rounded-md border border-slate-300 px-3 py-1 disabled:opacity-40 dark:border-slate-600" :disabled="page >= totalPages" @click="goPage(page + 1)">下一页</button>
        </div>
      </div>
    </div>
    <!-- ============ 仓库静态文章（展示覆盖） ============ -->
    <div v-else>
      <div class="mb-4 flex items-center justify-between">
        <p class="text-xs text-slate-400">共 {{ repoRows.length }} 篇 · 修改展示细节存于数据库覆盖表，不改动 Markdown 源文件；草稿状态前台不展示</p>
        <div class="relative">
          <Search class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input v-model="repoKeyword" type="text" placeholder="搜索标题或路径"
            class="w-56 rounded-lg border border-slate-300 bg-white py-2 pl-9 pr-3 text-sm outline-none focus:border-primary-brand dark:border-slate-600 dark:bg-slate-800" />
        </div>
      </div>
      <div class="site-card overflow-hidden">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-slate-200 bg-slate-50 text-left text-xs text-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400">
              <th class="px-4 py-3">文章</th>
              <th class="px-3 py-3">状态</th>
              <th class="px-2 py-3">精选</th>
              <th class="px-2 py-3">置顶</th>
              <th class="px-3 py-3">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in repoRows" :key="row.slug" class="border-b border-slate-100 last:border-0 dark:border-slate-700/50">
              <td class="px-4 py-3">
                <NuxtLink :to="`/posts/${row.slug}`" target="_blank" class="font-medium hover:text-primary-brand">{{ row.title }}</NuxtLink>
                <span class="block font-mono text-xs text-slate-400">{{ row.category }} · {{ row.slug }}</span>
                <input v-model="row.summary" type="text" placeholder="自定义摘要（可选）"
                  class="mt-1.5 w-full rounded-md border border-slate-200 bg-transparent px-2 py-1 text-xs outline-none focus:border-primary-brand dark:border-slate-600" />
              </td>
              <td class="px-3 py-3">
                <select v-model="row.status" class="cursor-pointer rounded-md border border-slate-300 bg-transparent px-2 py-1.5 text-xs dark:border-slate-600">
                  <option value="published">已发布</option>
                  <option value="draft">草稿</option>
                </select>
              </td>
              <td class="px-2 py-3 text-center">
                <button class="cursor-pointer rounded-md p-1.5" :class="row.featured ? 'text-amber-500' : 'text-slate-300 dark:text-slate-600'" @click="row.featured = !row.featured">
                  <Star class="h-4 w-4" :fill="row.featured ? 'currentColor' : 'none'" />
                </button>
              </td>
              <td class="px-2 py-3 text-center">
                <button class="cursor-pointer rounded-md p-1.5" :class="row.pinned ? 'text-primary-brand' : 'text-slate-300 dark:text-slate-600'" @click="row.pinned = !row.pinned">
                  <Pin class="h-4 w-4" :fill="row.pinned ? 'currentColor' : 'none'" />
                </button>
              </td>
              <td class="px-3 py-3">
                <button class="cursor-pointer rounded-lg bg-primary-brand px-3 py-1.5 text-xs font-medium text-white hover:bg-primary-brand-dark disabled:cursor-not-allowed disabled:opacity-50"
                  :disabled="savingSlug === row.slug" @click="saveRepoRow(row)"
                >{{ savingSlug === row.slug ? '保存中' : savedSlug === row.slug ? '已保存' : '保存' }}</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>