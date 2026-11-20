/** 文章 frontmatter 统一类型与读取辅助。 */
export interface ArticleMeta {
  title: string
  description: string
  category: string
  series?: string
  seriesOrder?: number
  tags: string[]
  date: string
  sourceRepo?: string
  demoLink?: string
  /** 路径即 slug，如 redis-cluster/01-intro */
  slug: string
}

export interface ArticleQueryResult extends Partial<ArticleMeta> {
  /** v3 字段名（v2 为 _path） */
  path?: string
  body?: unknown
  [key: string]: unknown
}

/** 把 @nuxt/content 查询结果规整为 ArticleMeta。 */
export function toArticleMeta(doc: ArticleQueryResult): ArticleMeta | null {
  const rawPath = doc?.path || doc?._path
  if (!doc?.title || !rawPath) return null
  return {
    title: doc.title,
    description: (doc.description as string) || '',
    category: (doc.category as string) || 'docker',
    series: doc.series as string | undefined,
    seriesOrder: doc.seriesOrder as number | undefined,
    tags: (doc.tags as string[]) || [],
    date: (doc.date as string) || '',
    sourceRepo: doc.sourceRepo as string | undefined,
    demoLink: doc.demoLink as string | undefined,
    slug: rawPath.replace(/^\/?posts\//, '').replace(/^\//, '')
  }
}
