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

/** /api/posts 返回的在线文章行 */
export interface DbArticleRow {
  id: number
  slug: string
  title: string
  description: string
  category: string
  tags: string[]
  date: string | null
  series: string
  seriesOrder: number | null
  sourceRepo: string
  status: string
  featured: boolean
  pinned: boolean
}

/** 把在线文章行规整为 ArticleMeta（与静态文章共用卡片渲染）。 */
export function toDbArticleMeta(row: DbArticleRow): ArticleMeta {
  return {
    title: row.title,
    description: row.description || '',
    category: row.category,
    series: row.series || undefined,
    seriesOrder: row.seriesOrder ?? undefined,
    tags: row.tags || [],
    date: (row.date || '').slice(0, 10),
    sourceRepo: row.sourceRepo || undefined,
    slug: row.slug
  }
}

/** 拉取在线文章列表（已发布；失败静默返回空数组，不影响静态内容渲染）。 */
export async function fetchDbArticles(
  apiBase: string,
  opts: { category?: string; size?: number } = {}
): Promise<ArticleMeta[]> {
  try {
    const res = await $fetch<{ code: number; data: { items: DbArticleRow[] } }>('/api/posts', {
      baseURL: apiBase,
      query: { category: opts.category || '', size: opts.size || 20 }
    })
    return (res.data?.items || []).map(toDbArticleMeta)
  } catch {
    return []
  }
}

/** 静态 + 在线文章合并：按 slug 去重（在线优先），日期倒序。 */
export function mergeArticles(staticList: ArticleMeta[], dbList: ArticleMeta[]): ArticleMeta[] {
  const seen = new Set(dbList.map(a => a.slug))
  const merged = [...dbList, ...staticList.filter(a => !seen.has(a.slug))]
  return merged.sort((a, b) => (b.date || '').localeCompare(a.date || ''))
}
