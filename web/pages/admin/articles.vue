<script setup lang="ts">
// 文章管理：内容目录文章列表 + 后台覆盖信息（发布状态/精选/置顶/摘要）
import { Search, Star, Pin } from 'lucide-vue-next'

definePageMeta({ layout: 'admin', middleware: 'admin-auth' })

const { authFetch } = useAuth()

interface OverrideRow {
  slug: string
  status: string
  featured: boolean
  pinned: boolean
  summary: string
  cover: string
}

/** 从 content 目录取全部文章（frontmatter + slug） */
const { data: contentDocs } = await useAsyncData('admin-content-list', () =>
  queryCollection('content')
    .select('title', 'description', 'category', 'date', 'path')
    .order('date', 'DESC')
    .all()
)

/** 从后台取已有覆盖信息 */
const { data: overridesResp } = await useAsyncData('admin-overrides', () =>
  authFetch<{ items: OverrideRow[] }>('/api/admin/articles', { method: 'GET' }).then(r => r),
  { server: false }
)

const overrideMap = computed(() => {
  const map = new Map<string, OverrideRow>()
  const resp = overridesResp.value as unknown as OverrideRow[] | null
  for (const row of resp || []) map.set(row.slug, row)
  return map
})

interface ArticleRow {
  slug: string
  title: string
  category: string
  date: string
  status: string
  featured: boolean
  pinned: boolean
  summary: string
}

const keyword = ref('')
const rows = computed<ArticleRow[]>(() => {
  const docs = (contentDocs.value || []) as Array<{ title: string; description?: string; category: string; date: string; path?: string }>
  const list = docs.map(d => {
    const slug = (d.path || '').replace(/^\//, '')
    const ov = overrideMap.value.get(slug)
    return {
      slug,
      title: d.title,
      category: d.category,
      date: d.date,
      status: ov?.status || 'published',
      featured: ov?.featured || false,
      pinned: ov?.pinned || false,
      summary: ov?.summary || ''
    }
  })
  if (!keyword.value) return list
  const kw = keyword.value.toLowerCase()
  return list.filter(r => r.title.toLowerCase().includes(kw) || r.slug.includes(kw))
})

const savingSlug = ref<string | null>(null)
const savedSlug = ref<string | null>(null)

const saveRow = async (row: ArticleRow) => {
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
    alert('保存失败，请查看控制台日志')
  } finally {
    savingSlug.value = null
  }
}
</script>

<template>
  <div class="animate-fade-in">
    <div class="mb-4 flex items-center justify-between">
      <h1 class="text-xl font-semibold">文章管理</h1>
      <div class="relative">
        <Search class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <input
          v-model="keyword"
          type="text"
          placeholder="搜索标题或路径"
          class="w-56 rounded-lg border border-slate-300 bg-white py-2 pl-9 pr-3 text-sm outline-none focus:border-primary-brand dark:border-slate-600 dark:bg-slate-800"
        />
      </div>
    </div>
    <p class="mb-4 text-xs text-slate-400">
      共 {{ rows.length }} 篇 · 修改展示细节存于数据库覆盖表，不改动 Markdown 源文件；「草稿」状态的文章前台不展示
    </p>

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
          <tr v-for="row in rows" :key="row.slug" class="border-b border-slate-100 last:border-0 dark:border-slate-700/50">
            <td class="px-4 py-3">
              <NuxtLink :to="`/posts/${row.slug}`" target="_blank" class="font-medium hover:text-primary-brand">{{ row.title }}</NuxtLink>
              <span class="block font-mono text-xs text-slate-400">{{ row.category }} · {{ row.slug }}</span>
              <input
                v-model="row.summary"
                type="text"
                placeholder="自定义摘要（可选）"
                class="mt-1.5 w-full rounded-md border border-slate-200 bg-transparent px-2 py-1 text-xs outline-none focus:border-primary-brand dark:border-slate-600"
              />
            </td>
            <td class="px-3 py-3">
              <select v-model="row.status" class="cursor-pointer rounded-md border border-slate-300 bg-transparent px-2 py-1.5 text-xs dark:border-slate-600">
                <option value="published">已发布</option>
                <option value="draft">草稿</option>
              </select>
            </td>
            <td class="px-2 py-3 text-center">
              <button
                class="cursor-pointer rounded-md p-1.5"
                :class="row.featured ? 'text-amber-500' : 'text-slate-300 dark:text-slate-600'"
                :title="row.featured ? '取消精选' : '设为精选'"
                @click="row.featured = !row.featured"
              >
                <Star class="h-4 w-4" :fill="row.featured ? 'currentColor' : 'none'" />
              </button>
            </td>
            <td class="px-2 py-3 text-center">
              <button
                class="cursor-pointer rounded-md p-1.5"
                :class="row.pinned ? 'text-primary-brand' : 'text-slate-300 dark:text-slate-600'"
                :title="row.pinned ? '取消置顶' : '置顶'"
                @click="row.pinned = !row.pinned"
              >
                <Pin class="h-4 w-4" :fill="row.pinned ? 'currentColor' : 'none'" />
              </button>
            </td>
            <td class="px-3 py-3">
              <button
                class="cursor-pointer rounded-lg bg-primary-brand px-3 py-1.5 text-xs font-medium text-white hover:bg-primary-brand-dark disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="savingSlug === row.slug"
                @click="saveRow(row)"
              >
                {{ savingSlug === row.slug ? '保存中' : savedSlug === row.slug ? '已保存' : '保存' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
