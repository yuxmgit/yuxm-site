<script setup lang="ts">
// 文章详情页：正文渲染 + 代码高亮 + 右侧 TOC + 上下篇 + 阅读数
import { Calendar, ChevronLeft, ChevronRight, Eye, Tag } from 'lucide-vue-next'

const route = useRoute()
const config = useRuntimeConfig()

// 路径如 /posts/redis-cluster/01-intro，取 redis-cluster/01-intro 作为内容路径
const contentPath = computed(() =>
  (route.params.slug as string[]).join('/')
)

const { data: doc, error } = await useAsyncData(`post-${contentPath.value}`, () =>
  queryCollection('content').path(`/${contentPath.value}`).first()
)

if (error.value || !doc.value) {
  throw createError({ statusCode: 404, statusMessage: '文章不存在', fatal: true })
}

const article = computed(() => toArticleMeta(doc.value as never))
const category = computed(() => getCategory(article.value?.category || ''))
const series = computed(() => article.value?.series ? getSeries(article.value.series) : undefined)

// 同系列上下篇（按 seriesOrder 排序）
const { data: siblings } = await useAsyncData(`post-siblings-${contentPath.value}`, () =>
  queryCollection('content')
    .where('series', '=', article.value?.series || '__none__')
    .select('title', 'path', 'seriesOrder', 'date')
    .order('seriesOrder', 'ASC')
    .order('date', 'ASC')
    .all()
)

const siblingList = computed(() => (siblings.value || []).map(d => toArticleMeta(d as never)).filter(Boolean))
const currentIndex = computed(() => siblingList.value.findIndex(a => a?.slug === article.value?.slug))
const prevArticle = computed(() => currentIndex.value > 0 ? siblingList.value[currentIndex.value - 1] : null)
const nextArticle = computed(() => currentIndex.value >= 0 && currentIndex.value < siblingList.value.length - 1 ? siblingList.value[currentIndex.value + 1] : null)

// 阅读数：上报到 FastAPI（失败静默，不影响阅读）
const views = ref<number | null>(null)
onMounted(async () => {
  try {
    const res = await $fetch<{ code: number; data: { views: number } }>(`/api/stats/views/${encodeURIComponent(contentPath.value)}`, {
      method: 'POST',
      baseURL: config.public.apiBase
    })
    views.value = res.data.views
  } catch (err) {
    console.error('阅读数上报失败', err)
  }
})

// 目录锚点：v3 直接提供 body.toc.links（h2/h3，含嵌套 children）
const toc = computed(() => {
  interface TocLinkLike { id: string; text: string; depth: number; children?: TocLinkLike[] }
  const links = (doc.value as unknown as { body?: { toc?: { links?: TocLinkLike[] } } } | null)?.body?.toc?.links || []
  const items: Array<{ id: string; text: string; level: number }> = []
  const walk = (ls: TocLinkLike[]) => {
    for (const l of ls) {
      items.push({ id: l.id, text: l.text, level: l.depth >= 3 ? 3 : 2 })
      if (l.children?.length) walk(l.children)
    }
  }
  walk(links)
  return items
})

useSeoMeta({
  title: () => `${article.value?.title} | 虞先森的技术站`,
  description: () => article.value?.description || ''
})
</script>

<template>
  <div class="mx-auto flex max-w-6xl gap-8 px-4 py-8 animate-fade-in">
    <!-- 正文 -->
    <article class="min-w-0 flex-1">
      <!-- 标题区 -->
      <div class="mb-8 border-b border-slate-200 pb-6 dark:border-slate-700">
        <nav class="mb-3 flex items-center gap-1.5 text-sm text-slate-500 dark:text-slate-400">
          <NuxtLink to="/" class="hover:text-primary-brand">首页</NuxtLink>
          <ChevronRight class="h-3.5 w-3.5" />
          <NuxtLink v-if="category" :to="`/category/${category.key}`" class="hover:text-primary-brand">{{ category.name }}</NuxtLink>
        </nav>
        <div class="mb-3 flex items-center gap-2">
          <span
            class="inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400"
            title="本站自身的技术实践"
          >本站实际使用的方案</span>
          <span v-if="series" class="rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-600 dark:bg-blue-900/30 dark:text-blue-400">
            {{ series.title }} #{{ article?.seriesOrder }}
          </span>
        </div>
        <h1 class="mb-3 text-2xl font-bold leading-snug md:text-3xl">{{ article?.title }}</h1>
        <div class="flex flex-wrap items-center gap-4 text-sm text-slate-500 dark:text-slate-400">
          <span class="flex items-center gap-1"><Calendar class="h-4 w-4" />{{ article?.date }}</span>
          <span v-if="views !== null" class="flex items-center gap-1"><Eye class="h-4 w-4" />{{ views }} 阅读</span>
          <span v-if="article?.tags?.length" class="flex items-center gap-1">
            <Tag class="h-4 w-4" />
            <span v-for="t in article.tags" :key="t" class="mr-1">{{ t }}</span>
          </span>
          <a v-if="article?.sourceRepo" :href="article.sourceRepo" target="_blank" rel="noopener" class="text-primary-brand hover:underline">配套仓库</a>
        </div>
      </div>

      <!-- 正文（@nuxt/content 渲染，Shiki 高亮） -->
      <div class="prose-nuxt">
        <ContentRenderer :value="doc" />
      </div>

      <!-- 上下篇 -->
      <div v-if="prevArticle || nextArticle" class="mt-10 grid grid-cols-1 gap-3 border-t border-slate-200 pt-6 sm:grid-cols-2 dark:border-slate-700">
        <NuxtLink v-if="prevArticle" :to="`/posts/${prevArticle.slug}`" class="site-card group p-4">
          <span class="flex items-center gap-1 text-xs text-slate-400"><ChevronLeft class="h-3.5 w-3.5" />上一篇</span>
          <span class="mt-1 block text-sm font-medium group-hover:text-primary-brand">{{ prevArticle.title }}</span>
        </NuxtLink>
        <NuxtLink v-if="nextArticle" :to="`/posts/${nextArticle.slug}`" class="site-card group p-4 sm:text-right">
          <span class="flex items-center gap-1 text-xs text-slate-400 sm:justify-end">下一篇<ChevronRight class="h-3.5 w-3.5" /></span>
          <span class="mt-1 block text-sm font-medium group-hover:text-primary-brand">{{ nextArticle.title }}</span>
        </NuxtLink>
      </div>
    </article>

    <!-- 右侧目录 -->
    <aside v-if="toc.length" class="hidden w-56 shrink-0 xl:block">
      <div class="sticky top-24 border-l border-slate-200 pl-4 dark:border-slate-700">
        <p class="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">目录</p>
        <ul class="space-y-1.5">
          <li v-for="item in toc" :key="item.id">
            <a
              :href="`#${item.id}`"
              class="block text-xs leading-relaxed text-slate-500 hover:text-primary-brand dark:text-slate-400"
              :class="item.level === 3 ? 'pl-3' : ''"
            >{{ item.text }}</a>
          </li>
        </ul>
      </div>
    </aside>
  </div>
</template>

<style>
/* @nuxt/content 渲染的正文排版（Shiki 代码块适配暗色模式） */
.prose-nuxt {
  line-height: 1.8;
}
.prose-nuxt h2 {
  margin: 2rem 0 1rem;
  font-size: 1.4rem;
  font-weight: 600;
  scroll-margin-top: 5rem;
}
.prose-nuxt h3 {
  margin: 1.5rem 0 0.75rem;
  font-size: 1.15rem;
  font-weight: 600;
  scroll-margin-top: 5rem;
}
.prose-nuxt p {
  margin: 0.75rem 0;
  color: rgb(71 85 105);
}
.dark .prose-nuxt p {
  color: rgb(203 213 225);
}
.prose-nuxt ul,
.prose-nuxt ol {
  margin: 0.75rem 0;
  padding-left: 1.5rem;
}
.prose-nuxt ul { list-style: disc; }
.prose-nuxt ol { list-style: decimal; }
.prose-nuxt li { margin: 0.35rem 0; }
.prose-nuxt a {
  color: #2563eb;
  text-decoration: underline;
  text-underline-offset: 3px;
}
.prose-nuxt blockquote {
  margin: 1rem 0;
  border-left: 3px solid #2563eb;
  padding: 0.25rem 0 0.25rem 1rem;
  color: rgb(100 116 139);
  background: rgb(248 250 252);
}
.dark .prose-nuxt blockquote {
  background: rgb(30 41 59);
}
.prose-nuxt pre {
  margin: 1.25rem 0;
  padding: 1rem;
  border-radius: 0.75rem;
  overflow-x: auto;
  font-size: 0.85rem;
  line-height: 1.6;
}
.prose-nuxt code {
  font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace;
}
.prose-nuxt :not(pre) > code {
  padding: 0.15rem 0.4rem;
  border-radius: 0.375rem;
  background: rgb(241 245 249);
  font-size: 0.85em;
}
.dark .prose-nuxt :not(pre) > code {
  background: rgb(30 41 59);
}
.prose-nuxt table {
  width: 100%;
  margin: 1rem 0;
  border-collapse: collapse;
  font-size: 0.9rem;
}
.prose-nuxt th,
.prose-nuxt td {
  border: 1px solid rgb(226 232 240);
  padding: 0.5rem 0.75rem;
  text-align: left;
}
.dark .prose-nuxt th,
.dark .prose-nuxt td {
  border-color: rgb(51 65 85);
}
.prose-nuxt img {
  margin: 1rem 0;
  border-radius: 0.75rem;
}
</style>
