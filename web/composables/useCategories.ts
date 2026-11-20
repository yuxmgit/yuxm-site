/** 站点分类与系列的静态配置：与 content/ 目录一一对应。 */
export interface CategoryMeta {
  key: string
  name: string
  description: string
  icon: string
  color: string
}

export const CATEGORIES: CategoryMeta[] = [
  { key: 'redis-cluster', name: 'Redis 集群', description: 'Cluster 原理、3主3从搭建、常见坑', icon: 'Database', color: '#EF4444' },
  { key: 'mysql', name: 'MySQL', description: '主从复制、读写分离、索引优化', icon: 'Database', color: '#2563EB' },
  { key: 'jenkins', name: 'Jenkins', description: 'Pipeline 语法、共享库、生产治理', icon: 'GitCommit', color: '#F59E0B' },
  { key: 'docker', name: 'Docker', description: '镜像与容器、Compose 编排、部署实践', icon: 'Container', color: '#06B6D4' },
  { key: 'jwt', name: 'JWT', description: '无状态登录、双 token、黑名单踢下线', icon: 'Key', color: '#10B981' },
  { key: 'oauth2', name: 'OAuth2', description: '授权码模式、GitHub/Gitee 登录、OIDC', icon: 'Shield', color: '#8B5CF6' },
  { key: 'python-frameworks', name: 'Python 框架', description: 'FastAPI / Flask / Django 对比实战', icon: 'Code', color: '#0EA5E9' }
]

export function getCategory(key: string): CategoryMeta | undefined {
  return CATEGORIES.find(c => c.key === key)
}

export interface SeriesMeta {
  /** 系列名与文章 frontmatter 的 series 字段一致 */
  key: string
  category: string
  title: string
  description: string
}

export const SERIES: SeriesMeta[] = [
  { key: 'redis-cluster-in-action', category: 'redis-cluster', title: 'Redis 集群实战', description: '从单机到 Cluster 3主3从的完整落地' },
  { key: 'mysql-replication', category: 'mysql', title: 'MySQL 主从与读写分离', description: '复制原理、搭建与验证' },
  { key: 'jenkins-pipeline', category: 'jenkins', title: 'Jenkins 生产级流水线', description: '从语法到共享库与治理' },
  { key: 'jwt-deep-dive', category: 'jwt', title: 'JWT 深入与踢下线', description: '本站正在使用的认证方案' }
]

export function getSeries(key: string): SeriesMeta | undefined {
  return SERIES.find(s => s.key === key)
}
