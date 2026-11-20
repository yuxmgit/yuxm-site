<script setup lang="ts">
// 全站默认布局：导航栏（固定顶部）+ 内容区 + 页脚
const { init: initDark } = useDarkMode()
onMounted(() => initDark())
</script>

<template>
  <div class="flex min-h-screen flex-col">
    <SiteHeader />
    <main class="flex-1 pt-16">
      <slot />
    </main>
    <SiteFooter />
  </div>
</template>
