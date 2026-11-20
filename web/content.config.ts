import { defineContentConfig, defineCollection, z } from '@nuxt/content'

// @nuxt/content v3：显式定义内容集合与 frontmatter schema
// 文件路径 web/content/** → 文档 path 如 /docker/01-intro
export default defineContentConfig({
  collections: {
    content: defineCollection({
      type: 'page',
      source: 'content/**',
      schema: z.object({
        title: z.string(),
        description: z.string().optional(),
        category: z.string().optional(),
        series: z.string().optional(),
        seriesOrder: z.number().optional(),
        tags: z.array(z.string()).optional(),
        date: z.string().optional(),
        sourceRepo: z.string().optional(),
        demoLink: z.string().optional()
      })
    })
  }
})
