/**
 * 教程内容迁移脚本
 * 用法：node scripts/migrate-content.mjs
 *
 * 职责：
 * 1. 按映射表从三个教程项目读取章节 Markdown
 * 2. 生成新站 frontmatter（title/category/series/seriesOrder/tags/date/sourceRepo）
 * 3. 清理跨文件链接（[text](xx.md) → text；../demos 链接 → text）
 * 4. 写入 web/content/<分类>/<slug>.md
 *
 * 映射表与规范详见 docs/content-migration.md
 */
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const ROOT = resolve(__dirname, '..')
const WORKSPACE = resolve(ROOT, '..')

const SOURCES = {
  fullstack: join(WORKSPACE, 'fullstack-cluster-tutorial', 'docs'),
  sso: join(WORKSPACE, 'sso-oauth-tutorial', 'docs'),
  cicd: join(WORKSPACE, 'cicd-tutorial', 'docs')
}

const REPOS = {
  fullstack: 'https://github.com/yuxiangming/fullstack-cluster-tutorial',
  sso: 'https://github.com/yuxiangming/sso-oauth-tutorial',
  cicd: 'https://github.com/yuxiangming/cicd-tutorial'
}

const CATEGORY_TAGS = {
  'redis-cluster': ['Redis', '集群'],
  mysql: ['MySQL', '主从复制'],
  jenkins: ['Jenkins', 'CI/CD'],
  docker: ['Docker', '部署'],
  jwt: ['JWT', '认证'],
  oauth2: ['OAuth2', 'SSO'],
  'python-frameworks': ['Python', 'FastAPI']
}

/**
 * 映射表：源项目 / 源文件 / 目标路径 / 分类 / 系列 / 序号
 * series 为空表示不进系列（附录等独立文章）
 */
const MAPPING = [
  // ===== fullstack-cluster-tutorial =====
  { src: 'fullstack/01-前后端分离与跨域.md', dest: 'python-frameworks/fastapi-vue-separation', category: 'python-frameworks', series: 'fullstack-cluster-in-action', order: 1, date: '2026-08-01' },
  { src: 'fullstack/02-Session集中式管理.md', dest: 'jwt/session-cluster', category: 'jwt', series: 'fullstack-cluster-in-action', order: 2, date: '2026-08-02' },
  { src: 'fullstack/03-集群与负载均衡.md', dest: 'docker/cluster-load-balancing', category: 'docker', series: 'fullstack-cluster-in-action', order: 3, date: '2026-08-03' },
  { src: 'fullstack/04-MySQL主从与读写分离.md', dest: 'mysql/replication-read-write-split', category: 'mysql', series: 'fullstack-cluster-in-action', order: 4, date: '2026-08-04' },
  { src: 'fullstack/05-Redis详解.md', dest: 'redis-cluster/redis-deep-dive', category: 'redis-cluster', series: 'fullstack-cluster-in-action', order: 5, date: '2026-08-05' },
  { src: 'fullstack/06-部署实战与验证.md', dest: 'docker/deploy-in-action', category: 'docker', series: 'fullstack-cluster-in-action', order: 6, date: '2026-08-06' },
  { src: 'fullstack/07-常见坑与进阶.md', dest: 'docker/pitfalls-and-advanced', category: 'docker', series: 'fullstack-cluster-in-action', order: 7, date: '2026-08-07' },
  { src: 'fullstack/08-腾讯云自动化部署.md', dest: 'jenkins/tencent-cloud-auto-deploy', category: 'jenkins', series: 'fullstack-cluster-in-action', order: 8, date: '2026-08-08' },

  // ===== sso-oauth-tutorial =====
  { src: 'sso/01-sso-起源与演进.md', dest: 'oauth2/sso-origins', category: 'oauth2', series: 'sso-oauth-series', order: 1, date: '2026-09-01' },
  { src: 'sso/02-oauth演变史.md', dest: 'oauth2/oauth-history', category: 'oauth2', series: 'sso-oauth-series', order: 2, date: '2026-09-02' },
  { src: 'sso/03-session与jwt.md', dest: 'jwt/session-vs-jwt', category: 'jwt', series: 'sso-oauth-series', order: 3, date: '2026-09-03' },
  { src: 'sso/04-手写OAuth2服务器.md', dest: 'oauth2/handwritten-oauth2-server', category: 'oauth2', series: 'sso-oauth-series', order: 4, date: '2026-09-04' },
  { src: 'sso/05-cas与saml.md', dest: 'oauth2/cas-and-saml', category: 'oauth2', series: 'sso-oauth-series', order: 5, date: '2026-09-05' },
  { src: 'sso/06-oidc身份层.md', dest: 'oauth2/oidc-identity-layer', category: 'oauth2', series: 'sso-oauth-series', order: 6, date: '2026-09-06' },
  { src: 'sso/07-安全攻防.md', dest: 'oauth2/security-attack-defense', category: 'oauth2', series: 'sso-oauth-series', order: 7, date: '2026-09-07' },
  { src: 'sso/08-总结与面试.md', dest: 'jwt/sso-summary-interview', category: 'jwt', series: 'sso-oauth-series', order: 8, date: '2026-09-08' },
  { src: 'sso/09-JWE令牌加密.md', dest: 'jwt/jwe-token-encryption', category: 'jwt', series: 'sso-oauth-series', order: 9, date: '2026-09-09' },
  { src: 'sso/10-JWT与OAuth的区别.md', dest: 'jwt/jwt-vs-oauth', category: 'jwt', series: 'sso-oauth-series', order: 10, date: '2026-09-10' },

  // ===== cicd-tutorial 正文 =====
  { src: 'cicd/00-环境与基本功.md', dest: 'jenkins/cicd-00-environment', category: 'jenkins', series: 'cicd-pipeline-series', order: 0, date: '2026-10-01' },
  { src: 'cicd/01-CICD到底是什么.md', dest: 'jenkins/cicd-01-what-is-cicd', category: 'jenkins', series: 'cicd-pipeline-series', order: 1, date: '2026-10-02' },
  { src: 'cicd/02-Git工作流.md', dest: 'jenkins/cicd-02-git-workflow', category: 'jenkins', series: 'cicd-pipeline-series', order: 2, date: '2026-10-03' },
  { src: 'cicd/03-Jenkins落地.md', dest: 'jenkins/cicd-03-jenkins-landing', category: 'jenkins', series: 'cicd-pipeline-series', order: 3, date: '2026-10-04' },
  { src: 'cicd/04-Pipeline语法.md', dest: 'jenkins/cicd-04-pipeline-syntax', category: 'jenkins', series: 'cicd-pipeline-series', order: 4, date: '2026-10-05' },
  { src: 'cicd/05-Jenkins工程化能力.md', dest: 'jenkins/cicd-05-engineering', category: 'jenkins', series: 'cicd-pipeline-series', order: 5, date: '2026-10-06' },
  { src: 'cicd/06-一条流水线的三种写法.md', dest: 'jenkins/cicd-06-three-pipeline-styles', category: 'jenkins', series: 'cicd-pipeline-series', order: 6, date: '2026-10-07' },
  { src: 'cicd/07-前端流水线实战.md', dest: 'jenkins/cicd-07-frontend-pipeline', category: 'jenkins', series: 'cicd-pipeline-series', order: 7, date: '2026-10-08' },
  { src: 'cicd/08-后端流水线实战.md', dest: 'jenkins/cicd-08-backend-pipeline', category: 'jenkins', series: 'cicd-pipeline-series', order: 8, date: '2026-10-09' },
  { src: 'cicd/09-质量与安全门禁.md', dest: 'jenkins/cicd-09-quality-gates', category: 'jenkins', series: 'cicd-pipeline-series', order: 9, date: '2026-10-10' },
  { src: 'cicd/10-镜像与制品管理.md', dest: 'docker/cicd-10-images-artifacts', category: 'docker', series: 'cicd-pipeline-series', order: 10, date: '2026-10-11' },
  { src: 'cicd/11-服务器初始化.md', dest: 'docker/cicd-11-server-init', category: 'docker', series: 'cicd-pipeline-series', order: 11, date: '2026-10-12' },
  { src: 'cicd/12-部署方式演进.md', dest: 'jenkins/cicd-12-deploy-evolution', category: 'jenkins', series: 'cicd-pipeline-series', order: 12, date: '2026-10-13' },
  { src: 'cicd/13-Nginx与HTTPS.md', dest: 'docker/cicd-13-nginx-https', category: 'docker', series: 'cicd-pipeline-series', order: 13, date: '2026-10-14' },
  { src: 'cicd/14-配置管理与数据持久化.md', dest: 'jenkins/cicd-14-config-persistence', category: 'jenkins', series: 'cicd-pipeline-series', order: 14, date: '2026-10-15' },
  { src: 'cicd/15-端到端完整实战.md', dest: 'jenkins/cicd-15-end-to-end', category: 'jenkins', series: 'cicd-pipeline-series', order: 15, date: '2026-10-16' },
  { src: 'cicd/16-流水线工程化与提速.md', dest: 'jenkins/cicd-16-speedup', category: 'jenkins', series: 'cicd-pipeline-series', order: 16, date: '2026-10-17' },
  { src: 'cicd/17-Jenkins生产级治理.md', dest: 'jenkins/cicd-17-production-governance', category: 'jenkins', series: 'cicd-pipeline-series', order: 17, date: '2026-10-18' },
  { src: 'cicd/18-发布治理与可观测.md', dest: 'jenkins/cicd-18-release-observability', category: 'jenkins', series: 'cicd-pipeline-series', order: 18, date: '2026-10-19' },
  { src: 'cicd/19-故障演练手册.md', dest: 'jenkins/cicd-19-chaos-drill', category: 'jenkins', series: 'cicd-pipeline-series', order: 19, date: '2026-10-20' },
  { src: 'cicd/20-从单机到集群的演进信号.md', dest: 'jenkins/cicd-20-scale-out', category: 'jenkins', series: 'cicd-pipeline-series', order: 20, date: '2026-10-21' },

  // ===== cicd-tutorial 附录（独立文章，不进系列） =====
  { src: 'cicd/附录A-命令速查.md', dest: 'jenkins/cicd-appendix-a-commands', category: 'jenkins', series: null, order: null, date: '2026-10-22' },
  { src: 'cicd/附录B-配置模板大全.md', dest: 'jenkins/cicd-appendix-b-templates', category: 'jenkins', series: null, order: null, date: '2026-10-23' },
  { src: 'cicd/附录C-面试高频题.md', dest: 'jenkins/cicd-appendix-c-interview', category: 'jenkins', series: null, order: null, date: '2026-10-24' },
  { src: 'cicd/附录E-Jenkins凭据详解.md', dest: 'jenkins/cicd-appendix-e-credentials', category: 'jenkins', series: null, order: null, date: '2026-10-25' }
]

/** 从正文提取标题与描述 */
function parseBody(raw) {
  const lines = raw.split(/\r?\n/)
  let title = ''
  const descLines = []
  for (const line of lines) {
    const h1 = line.match(/^#\s+(.+)$/)
    if (h1 && !title) {
      title = h1[1].trim()
      continue
    }
    if (title && descLines.length < 4) {
      const t = line.trim().replace(/^>\s*/, '')
      if (t && !t.startsWith('#') && !t.startsWith('---')) descLines.push(t)
    }
  }
  return { title, description: descLines.join(' ').slice(0, 90) }
}

/** 清理跨文件链接与源站导流 */
function cleanBody(raw) {
  return raw
    // [text](xxx.md) / [text](../demos/xxx) → 保留文字去掉链接
    .replace(/\[([^\]]+)\]\([^)]*\.(?:md|MD)[^)]*\)/g, '$1')
    .replace(/\[([^\]]+)\]\((?:\.\.\/)?demos\/[^)]*\)/g, '$1')
    // 章末"下一章"导流行整行移除
    .replace(/^>?\s*下一章[:：].*$/gm, '')
    .replace(/^>?\s*上一篇[:：].*$/gm, '')
    .trim()
}

function buildFrontmatter(m, meta) {
  const tags = CATEGORY_TAGS[m.category] || []
  const fm = [
    '---',
    `title: ${JSON.stringify(meta.title)}`,
    `description: ${JSON.stringify(meta.description)}`,
    `category: ${m.category}`
  ]
  if (m.series) {
    fm.push(`series: ${m.series}`)
    fm.push(`seriesOrder: ${m.order}`)
  }
  fm.push(`tags: [${tags.map(t => JSON.stringify(t)).join(', ')}]`)
  fm.push(`date: ${m.date}`)
  fm.push(`sourceRepo: ${REPOS[m.src.split('/')[0]]}`)
  fm.push('---')
  return fm.join('\n')
}

let ok = 0
let failed = []
for (const m of MAPPING) {
  const [project, ...rest] = m.src.split('/')
  const srcPath = join(SOURCES[project], rest.join('/'))
  let raw
  try {
    raw = readFileSync(srcPath, 'utf-8')
  } catch (err) {
    console.error(`[SKIP] 找不到源文件: ${srcPath}`)
    failed.push(m.src)
    continue
  }
  const meta = parseBody(raw)
  const body = cleanBody(raw)
  // 去掉正文首个 H1（标题进 frontmatter）
  const bodyLines = body.split(/\r?\n/)
  const h1Idx = bodyLines.findIndex(l => /^#\s+/.test(l))
  if (h1Idx >= 0 && bodyLines.slice(0, h1Idx + 1).every(l => !l.trim() || /^#\s+/.test(l) || /^---/.test(l))) {
    bodyLines.splice(0, h1Idx + 1)
  }
  const finalBody = bodyLines.join('\n').trim()

  const destPath = join(ROOT, 'web', 'content', `${m.dest}.md`)
  mkdirSync(dirname(destPath), { recursive: true })
  writeFileSync(destPath, `${buildFrontmatter(m, meta)}\n\n${finalBody}\n`, 'utf-8')
  ok++
}

console.log(`迁移完成：成功 ${ok}/${MAPPING.length} 篇`)
if (failed.length) {
  console.log('失败清单：')
  for (const f of failed) console.log(`  - ${f}`)
}
