<script setup lang="ts">
// 分类页：左侧分类/系列侧栏 + 右侧文章卡片流
import type { ArticleMeta } from '~/composables/useArticleMeta'

const route = useRoute()
const categoryKey = computed(() => route.params.name as string)
const category = computed(() => getCategory(categoryKey.value))

if (!category.value) {
  throw createError({ statusCode: 404, statusMessage: '分类不存在', fatal: true })
}

const { data: docs } = await useAsyncData(`category-${categoryKey.value}`, () =>
  queryCollection('content')
    .where('category', '=', categoryKey.value)
    .select('title', 'description', 'category', 'series', 'seriesOrder', 'tags', 'date', 'path')
    .order('date', 'DESC')
    .all()
)

const articles = computed<ArticleMeta[]>(() =>
  (docs.value || []).map(d => toArticleMeta(d as never)).filter((a): a is ArticleMeta => a !== null)
)

// 当前分类下的系列（去重）
const seriesInCategory = computed(() => {
  const keys = new Set(articles.value.map(a => a.series).filter((s): s is string => Boolean(s)))
  return SERIES.filter(s => keys.has(s.key))
})

useSeoMeta({
  title: () => `${category.value?.name}教程 | 余先森的技术站`,
  description: () => category.value?.description || ''
})
</script>

<template>
  <div class="mx-auto flex max-w-6xl gap-8 px-4 py-8 animate-fade-in">
    <!-- 侧栏 -->
    <aside class="hidden w-56 shrink-0 lg:block">
      <div class="sticky top-24 space-y-6">
        <div>
          <p class="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">全部分类</p>
          <ul class="space-y-1">
            <li v-for="cat in CATEGORIES" :key="cat.key">
              <NuxtLink
                :to="`/category/${cat.key}`"
                class="flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-sm hover:bg-slate-100 dark:hover:bg-slate-800"
                :class="cat.key === categoryKey ? 'font-semibold text-primary-brand' : ''"
              >
                <span class="h-2 w-2 rounded-full" :style="{ backgroundColor: cat.color }" />
                {{ cat.name }}
              </NuxtLink>
            </li>
          </ul>
        </div>
        <div v-if="seriesInCategory.length">
          <p class="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">系列教程</p>
          <ul class="space-y-1">
            <li v-for="s in seriesInCategory" :key="s.key">
              <NuxtLink
                :to="`/series/${s.key}`"
                class="block rounded-lg px-2.5 py-1.5 text-sm hover:bg-slate-100 dark:hover:bg-slate-800"
              >{{ s.title }}</NuxtLink>
            </li>
          </ul>
        </div>
      </div>
    </aside>

    <!-- 文章流 -->
    <div class="min-w-0 flex-1">
      <header class="mb-6">
        <h1 class="mb-2 text-2xl font-bold">{{ category?.name }}教程</h1>
        <p class="text-sm text-slate-500 dark:text-slate-400">{{ category?.description }} · 共 {{ articles.length }} 篇</p>
      </header>
      <div v-if="articles.length" class="grid grid-cols-1 gap-4 md:grid-cols-2">
        <ArticleCard v-for="a in articles" :key="a.slug" :article="a" />
      </div>
      <div v-else class="rounded-xl border border-dashed border-slate-300 p-12 text-center text-sm text-slate-400 dark:border-slate-600">
        该分类下的文章正在迁移中
      </div>
    </div>
  </div>
</template>
