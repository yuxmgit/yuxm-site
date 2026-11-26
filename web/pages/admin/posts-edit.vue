<script setup lang="ts">
// 文章编辑器：新建/编辑在线文章，支持实时预览
import { ArrowLeft, Eye, Save, Trash2 } from 'lucide-vue-next'

definePageMeta({ layout: 'admin', middleware: 'admin-auth' })

const route = useRoute()
const router = useRouter()
const { authFetch } = useAuth()

const editId = computed(() => (route.query.id ? Number(route.query.id) : null))

const form = reactive({
  slug: '',
  title: '',
  description: '',
  category: 'docker',
  tags: '',
  date: new Date().toISOString().slice(0, 10),
  series: '',
  seriesOrder: null as number | null,
  sourceRepo: '',
  contentMd: '',
  status: 'draft',
  featured: false,
  pinned: false
})

const showPreview = ref(false)
const saving = ref(false)
const errorMsg = ref('')
const okMsg = ref('')
const loaded = ref(!editId.value)

const notify = (msg: string) => { okMsg.value = msg; setTimeout(() => { okMsg.value = '' }, 2000) }

// 编辑态：拉全文回填
if (editId.value) {
  try {
    const res = await authFetch<{ id: number; slug: string; title: string; description: string; category: string; tags: string[]; date: string | null; series: string; seriesOrder: number | null; sourceRepo: string; contentMd: string; status: string; featured: boolean; pinned: boolean }>(`/api/admin/posts/${editId.value}`, { method: 'GET' })
    Object.assign(form, {
      slug: res.slug,
      title: res.title,
      description: res.description,
      category: res.category,
      tags: (res.tags || []).join(', '),
      date: res.date || new Date().toISOString().slice(0, 10),
      series: res.series,
      seriesOrder: res.seriesOrder,
      sourceRepo: res.sourceRepo,
      contentMd: res.contentMd,
      status: res.status,
      featured: res.featured,
      pinned: res.pinned
    })
    loaded.value = true
  } catch (err) {
    console.error('加载文章失败', err)
    errorMsg.value = '文章加载失败'
  }
}

// 标题 -> slug 建议（英文标题直接转，中文回退日期路径）
const suggestSlug = () => {
  const s = form.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').replace(/-{2,}/g, '-')
  form.slug = s || `post-${form.date}`
}

const wordCount = computed(() => form.contentMd.length)

const save = async () => {
  errorMsg.value = ''
  if (!form.title.trim()) { errorMsg.value = '标题不能为空'; return }
  if (!form.slug.trim()) { errorMsg.value = 'slug 不能为空'; return }
  if (!form.contentMd.trim()) { errorMsg.value = '正文不能为空'; return }
  saving.value = true
  try {
    const body = {
      slug: form.slug.trim(),
      title: form.title.trim(),
      description: form.description,
      category: form.category,
      tags: form.tags.split(',').map(t => t.trim()).filter(Boolean),
      date: form.date,
      series: form.series,
      seriesOrder: form.seriesOrder,
      sourceRepo: form.sourceRepo,
      contentMd: form.contentMd,
      status: form.status,
      featured: form.featured,
      pinned: form.pinned
    }
    if (editId.value) {
      await authFetch(`/api/admin/posts/${editId.value}`, { method: 'PUT', body })
      notify('已保存')
    } else {
      const res = await authFetch<{ id: number }>('/api/admin/posts', { method: 'POST', body })
      notify('创建成功')
      router.replace(`/admin/posts-edit?id=${res.id}`)
    }
  } catch (err: unknown) {
    const e = err as { data?: { message?: string }; message?: string }
    errorMsg.value = e.data?.message || e.message || '保存失败'
  } finally {
    saving.value = false
  }
}

const remove = async () => {
  if (!editId.value) return
  if (!window.confirm('确定删除这篇文章？前台立即不可见，不可恢复。')) return
  await authFetch(`/api/admin/posts/${editId.value}`, { method: 'DELETE' })
  router.push('/admin/articles')
}
</script>
<template>
  <div class="animate-fade-in">
    <div class="mb-4 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <button class="cursor-pointer rounded-lg border border-slate-300 p-2 dark:border-slate-600" title="返回列表" @click="router.push('/admin/articles')">
          <ArrowLeft class="h-4 w-4" />
        </button>
        <h1 class="text-xl font-semibold">{{ editId ? '编辑文章' : '新增文章' }}</h1>
      </div>
      <div class="flex items-center gap-2">
        <span v-if="okMsg" class="rounded-md bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400">{{ okMsg }}</span>
        <button v-if="editId" class="cursor-pointer rounded-lg border border-rose-300 px-3 py-2 text-xs text-rose-500 hover:bg-rose-50 dark:border-rose-800" @click="remove">
          <Trash2 class="inline h-3.5 w-3.5" /> 删除
        </button>
        <button class="cursor-pointer rounded-lg border border-slate-300 px-3 py-2 text-xs dark:border-slate-600" @click="showPreview = !showPreview">
          <Eye class="inline h-3.5 w-3.5" /> {{ showPreview ? '编辑' : '预览' }}
        </button>
        <select v-model="form.status" class="cursor-pointer rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs dark:border-slate-600 dark:bg-slate-800">
          <option value="draft">草稿</option>
          <option value="published">发布</option>
        </select>
        <button class="cursor-pointer rounded-lg bg-primary-brand px-4 py-2 text-xs font-medium text-white hover:bg-primary-brand-dark disabled:opacity-50" :disabled="saving" @click="save">
          <Save class="inline h-3.5 w-3.5" /> {{ saving ? '保存中…' : '保存' }}
        </button>
      </div>
    </div>

    <p v-if="errorMsg" class="mb-3 rounded-lg bg-rose-50 px-4 py-2 text-sm text-rose-600 dark:bg-rose-900/30 dark:text-rose-400">{{ errorMsg }}</p>
    <p v-if="!loaded" class="text-sm text-slate-400">加载中…</p>

    <div v-else class="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_280px]">
      <!-- 主编辑区 -->
      <div class="site-card p-4">
        <input v-model="form.title" type="text" placeholder="文章标题" @blur="!form.slug && suggestSlug()"
          class="mb-3 w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2.5 text-lg font-semibold outline-none focus:border-primary-brand dark:border-slate-600" />
        <div v-if="showPreview" class="prose-nuxt min-h-[480px]" v-html="renderMarkdown(form.contentMd)" />
        <textarea
          v-else
          v-model="form.contentMd"
          placeholder="用 Markdown 写正文……"
          class="min-h-[480px] w-full resize-y rounded-lg border border-slate-300 bg-transparent p-3 font-mono text-sm leading-relaxed outline-none focus:border-primary-brand dark:border-slate-600"
        />
        <p class="mt-1 text-right text-xs text-slate-400">{{ wordCount }} 字符 · {{ form.contentMd.split('\n').length }} 行</p>
      </div>

      <!-- 侧栏元信息 -->
      <div class="space-y-4">
        <div class="site-card p-4">
          <p class="mb-2 text-xs font-semibold text-slate-500">发布设置</p>
          <label class="mb-1 block text-xs text-slate-400">Slug（URL 路径，创建后改动会影响已有链接）</label>
          <div class="flex gap-1.5">
            <input v-model="form.slug" type="text" placeholder="blog/hello-world"
              class="w-full rounded-md border border-slate-300 bg-transparent px-2 py-1.5 font-mono text-xs outline-none focus:border-primary-brand dark:border-slate-600" />
            <button class="shrink-0 cursor-pointer rounded-md border border-slate-300 px-2 text-xs dark:border-slate-600" title="从标题生成" @click="suggestSlug">生成</button>
          </div>
          <label class="mb-1 mt-3 block text-xs text-slate-400">分类</label>
          <select v-model="form.category" class="w-full cursor-pointer rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-800">
            <option v-for="c in CATEGORIES" :key="c.key" :value="c.key">{{ c.name }}</option>
          </select>
          <label class="mb-1 mt-3 block text-xs text-slate-400">标签（英文逗号分隔）</label>
          <input v-model="form.tags" type="text" placeholder="Docker, 部署"
            class="w-full rounded-md border border-slate-300 bg-transparent px-2 py-1.5 text-sm outline-none focus:border-primary-brand dark:border-slate-600" />
          <label class="mb-1 mt-3 block text-xs text-slate-400">发布日期</label>
          <input v-model="form.date" type="date"
            class="w-full rounded-md border border-slate-300 bg-transparent px-2 py-1.5 text-sm outline-none focus:border-primary-brand dark:border-slate-600" />
        </div>

        <div class="site-card p-4">
          <p class="mb-2 text-xs font-semibold text-slate-500">可选字段</p>
          <label class="mb-1 block text-xs text-slate-400">系列（如 auth-state-lab）</label>
          <input v-model="form.series" type="text"
            class="w-full rounded-md border border-slate-300 bg-transparent px-2 py-1.5 font-mono text-xs outline-none focus:border-primary-brand dark:border-slate-600" />
          <label class="mb-1 mt-3 block text-xs text-slate-400">系列序号</label>
          <input v-model.number="form.seriesOrder" type="number" min="1"
            class="w-full rounded-md border border-slate-300 bg-transparent px-2 py-1.5 text-sm outline-none focus:border-primary-brand dark:border-slate-600" />
          <label class="mb-1 mt-3 block text-xs text-slate-400">摘要/描述（SEO 与卡片展示）</label>
          <textarea v-model="form.description" rows="3"
            class="w-full resize-y rounded-md border border-slate-300 bg-transparent px-2 py-1.5 text-xs outline-none focus:border-primary-brand dark:border-slate-600" />
          <label class="mb-1 mt-3 block text-xs text-slate-400">配套仓库 URL</label>
          <input v-model="form.sourceRepo" type="text" placeholder="https://github.com/..."
            class="w-full rounded-md border border-slate-300 bg-transparent px-2 py-1.5 font-mono text-xs outline-none focus:border-primary-brand dark:border-slate-600" />
          <div class="mt-3 flex gap-4 text-sm">
            <label class="flex cursor-pointer items-center gap-1.5"><input v-model="form.featured" type="checkbox" /> 精选</label>
            <label class="flex cursor-pointer items-center gap-1.5"><input v-model="form.pinned" type="checkbox" /> 置顶</label>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>