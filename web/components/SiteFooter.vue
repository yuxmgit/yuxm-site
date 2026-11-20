<script setup lang="ts">
// 页脚：分类速览 + 备案号 + 开源链接（备案号预留后台可配）
const config = useRuntimeConfig()
const year = new Date().getFullYear()

// 备案号：后台 site_settings 的 icp_key，未配置时显示占位提示
const { data: settings } = useFetch('/api/site/settings', {
  baseURL: config.public.apiBase,
  key: 'site-settings-footer',
  server: true,
  default: () => null as null | { icp?: string }
})
</script>

<template>
  <footer class="border-t border-slate-200 py-8 dark:border-slate-700">
    <div class="mx-auto flex max-w-6xl flex-col items-center gap-4 px-4 text-sm text-slate-500 dark:text-slate-400">
      <div class="flex flex-wrap items-center justify-center gap-x-6 gap-y-2">
        <NuxtLink
          v-for="cat in CATEGORIES"
          :key="cat.key"
          :to="`/category/${cat.key}`"
          class="hover:text-primary-brand"
        >
          {{ cat.name }}
        </NuxtLink>
      </div>
      <div class="flex flex-wrap items-center justify-center gap-x-4 gap-y-1">
        <a :href="config.public.githubUrl" target="_blank" rel="noopener" class="hover:text-primary-brand">GitHub</a>
        <a :href="config.public.giteeUrl" target="_blank" rel="noopener" class="hover:text-primary-brand">Gitee</a>
        <span>© {{ year }} yuxm.site</span>
        <span v-if="settings?.icp">
          <a href="https://beian.miit.gov.cn/" target="_blank" rel="noopener" class="hover:text-primary-brand">{{ settings.icp }}</a>
        </span>
        <span v-else class="text-slate-400 dark:text-slate-500">ICP 备案号（备案通过后在后台配置）</span>
      </div>
    </div>
  </footer>
</template>
