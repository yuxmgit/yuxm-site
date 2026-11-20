<script setup lang="ts">
// 文章卡片：分类页 / 系列页 / 首页列表通用
import { Calendar, Eye } from 'lucide-vue-next'
import type { ArticleMeta } from '~/composables/useArticleMeta'

const props = defineProps<{
  article: ArticleMeta
  views?: number
}>()

const category = computed(() => getCategory(props.article.category))
</script>

<template>
  <NuxtLink :to="`/posts/${article.slug}`" class="site-card group block p-5">
    <div class="mb-2 flex items-center gap-2">
      <span
        v-if="category"
        class="rounded-full px-2.5 py-0.5 text-xs font-medium text-white"
        :style="{ backgroundColor: category.color }"
      >{{ category.name }}</span>
      <span
        v-for="tag in article.tags.slice(0, 3)"
        :key="tag"
        class="rounded-full border border-slate-200 px-2.5 py-0.5 text-xs text-slate-600 dark:border-slate-600 dark:text-slate-300"
      >{{ tag }}</span>
    </div>
    <h3 class="mb-1.5 text-lg font-semibold leading-snug group-hover:text-primary-brand">
      {{ article.title }}
    </h3>
    <p class="mb-3 line-clamp-2 text-sm leading-relaxed text-slate-500 dark:text-slate-400">
      {{ article.description }}
    </p>
    <div class="flex items-center gap-4 text-xs text-slate-400 dark:text-slate-500">
      <span class="flex items-center gap-1"><Calendar class="h-3.5 w-3.5" />{{ article.date }}</span>
      <span v-if="views !== undefined" class="flex items-center gap-1"><Eye class="h-3.5 w-3.5" />{{ views }} 阅读</span>
    </div>
  </NuxtLink>
</template>
