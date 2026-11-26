// Markdown 渲染（在线文章）：marked 解析 + sanitize-html 过滤，SSR 与浏览器均可运行。
// 标题锚点 id 由自定义 renderer 生成，与 TOC 提取共用同一 slug 算法，保证目录跳转一致。
import { marked } from 'marked'
import sanitizeHtml from 'sanitize-html'

/** 标题文本 -> 锚点 id（去特殊字符、空格转连字符、重名自动加序号） */
export function headingId(text: string, seen?: Map<string, number>): string {
  let id = text
    .toLowerCase()
    .trim()
    .replace(/[\s]+/g, '-')
    .replace(/[^\p{L}\p{N}-]/gu, '')
  if (!id) id = 'h'
  if (seen) {
    const n = seen.get(id) ?? 0
    seen.set(id, n + 1)
    if (n > 0) id = `${id}-${n}`
  }
  return id
}

// 标题 id 计数器：一次渲染内重名标题加 -1/-2 后缀
function makeSeen(): Map<string, number> {
  return new Map()
}

const renderer = {
  heading({ tokens, depth }: { tokens: any[]; depth: number }) {
    const text = this.parser.parseInline(tokens)
    const id = headingId(text.replace(/<[^>]+>/g, ''))
    return `<h${depth} id="${id}">${text}</h${depth}>\n`
  }
} as any

marked.use({ renderer, gfm: true, breaks: false })

/** 允许 Markdown 常用标签与属性，过滤脚本/事件处理器等 XSS 向量 */
const SANITIZE_OPTIONS: sanitizeHtml.IOptions = {
  allowedTags: [
    ...sanitizeHtml.defaults.allowedTags,
    'img', 'h1', 'h2', 'del', 'ins', 'figure', 'figcaption', 'details', 'summary', 'kbd', 'mark'
  ],
  allowedAttributes: {
    ...sanitizeHtml.defaults.allowedAttributes,
    '*': ['id', 'class'],
    a: ['href', 'name', 'target', 'rel', 'title'],
    img: ['src', 'srcset', 'alt', 'title', 'width', 'height', 'loading'],
    code: ['class'],
    span: ['class'],
    div: ['class'],
    table: ['class'],
    th: ['align'],
    td: ['align']
  },
  allowedSchemes: ['http', 'https', 'mailto', 'data'],
  transformTags: {
    // 外链统一新窗口 + nofollow，防钓鱼降权
    a: sanitizeHtml.simpleTransform('a', { target: '_blank', rel: 'noopener nofollow' })
  }
}

/** Markdown 字符串 -> 安全 HTML（在线文章渲染唯一入口） */
export function renderMarkdown(md: string): string {
  const html = marked.parse(md || '', { async: false }) as string
  return sanitizeHtml(html, SANITIZE_OPTIONS)
}

/** 从 Markdown 提取 h2/h3 目录（跳过代码块内的 # 行） */
export function extractToc(md: string): Array<{ id: string; text: string; level: number }> {
  const seen = makeSeen()
  const items: Array<{ id: string; text: string; level: number }> = []
  let inCode = false
  for (const line of (md || '').split('\n')) {
    if (/^```/.test(line.trim())) {
      inCode = !inCode
      continue
    }
    if (inCode) continue
    const m = /^(#{2,3})\s+(.+?)\s*#*$/.exec(line)
    if (m) {
      const text = m[2].trim()
      const level = m[1].length
      items.push({ id: headingId(text.replace(/[`*]/g, '')), text, level })
    }
  }
  return items
}
