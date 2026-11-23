<script setup lang="ts">
// 系列页：进度时间线 + 章节卡片（按 seriesOrder 排序）
import type { ArticleMeta } from '~/composables/useArticleMeta'

const route = useRoute()
const seriesKey = computed(() => route.params.name as string)
const series = computed(() => getSeries(seriesKey.value))

if (!series.value) {
  throw createError({ statusCode: 404, statusMessage: '系列不存在', fatal: true })
}

const { data: docs } = await useAsyncData(`series-${seriesKey.value}`, () =>
  queryCollection('content')
    .where('series', '=', seriesKey.value)
    .select('title', 'description', 'category', 'series', 'seriesOrder', 'tags', 'date', 'path')
    .order('seriesOrder', 'ASC')
    .order('date', 'ASC')
    .all()
)

const articles = computed<ArticleMeta[]>(() =>
  (docs.value || []).map(d => toArticleMeta(d as never)).filter((a): a is ArticleMeta => a !== null)
)

useSeoMeta({
  title: () => `${series.value?.title}系列 | 虞先森的技术站`,
  description: () => series.value?.description || ''
})
</script>

<template>
  <div class="mx-auto max-w-4xl px-4 py-8 animate-fade-in">
    <header class="mb-10 text-center">
      <span
        v-if="getCategory(series?.category || '')"
        class="mb-3 inline-block rounded-full px-3 py-1 text-xs font-medium text-white"
        :style="{ backgroundColor: getCategory(series?.category || '')?.color }"
      >{{ getCategory(series?.category || '')?.name }}系列</span>
      <h1 class="mb-2 text-3xl font-bold">{{ series?.title }}</h1>
      <p class="text-sm text-slate-500 dark:text-slate-400">{{ series?.description }} · {{ articles.length }} 篇</p>
    </header>

    <!-- 时间线 -->
    <ol v-if="articles.length" class="relative ml-3 border-l-2 border-slate-200 dark:border-slate-700">
      <li v-for="(a, i) in articles" :key="a.slug" class="relative mb-8 pl-8">
        <span
          class="absolute -left-[13px] top-1 flex h-6 w-6 items-center justify-center rounded-full bg-primary-brand text-xs font-bold text-white"
        >{{ i + 1 }}</span>
        <NuxtLink :to="`/posts/${a.slug}`" class="site-card group block p-5">
          <div class="mb-1.5 flex items-center gap-2 text-xs text-slate-400">
            <span>第 {{ i + 1 }} 章</span>
            <span>{{ a.date }}</span>
          </div>
          <h3 class="mb-1 text-lg font-semibold group-hover:text-primary-brand">{{ a.title }}</h3>
          <p class="line-clamp-2 text-sm text-slate-500 dark:text-slate-400">{{ a.description }}</p>
        </NuxtLink>
      </li>
    </ol>
    <div v-else class="rounded-xl border border-dashed border-slate-300 p-12 text-center text-sm text-slate-400 dark:border-slate-600">
      该系列文章正在迁移中
    </div>
  </div>
</template>
