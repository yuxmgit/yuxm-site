<script setup lang="ts">
// 个人中心：我的收藏 / 我的笔记 / 我的评论（"空中课堂"式个人学习空间）
// 未登录时提示并唤起登录弹窗；文章标题由前端内容索引按 slug 解析
import { Bookmark, Loader2, MessageSquare, NotebookPen, Star, Trash2, UserCog } from 'lucide-vue-next'
import type { UserInfo } from '~/composables/useAuth'

const config = useRuntimeConfig()
const { isLoggedIn, user, authFetch, open, updateUser } = useAuth()

const tab = ref<'favorites' | 'notes' | 'comments'>('favorites')
const loading = ref(false)

interface StatOverview {
  favorites: number
  notes: number
  comments: number
}
const overview = ref<StatOverview | null>(null)

// slug → 文章标题（从内容索引构建映射）
const titleMap = ref<Record<string, string>>({})
onMounted(async () => {
  try {
    const docs = await queryCollection('content').select('title', 'path').all()
    const map: Record<string, string> = {}
    for (const d of docs as Array<{ title: string; path: string }>) {
      map[d.path.replace(/^\//, '')] = d.title
    }
    titleMap.value = map
  } catch (err) {
    console.error('内容索引加载失败', err)
  }
})
const titleOf = (slug: string) => titleMap.value[slug] || slug

interface FavoriteItem { slug: string; created_at: string }
interface NoteItem { slug: string; excerpt: string; updated_at: string }
interface CommentItem { id: number; slug: string; content: string; created_at: string }

const favorites = ref<FavoriteItem[]>([])
const notes = ref<NoteItem[]>([])
const comments = ref<CommentItem[]>([])
const loadedTabs = ref(new Set<string>())

const loadTab = async () => {
  if (!isLoggedIn.value || tab.value === 'settings') return
  if (loadedTabs.value.has(tab.value)) return
  loading.value = true
  try {
    if (tab.value === 'favorites') {
      favorites.value = await authFetch<FavoriteItem[]>('/api/interactive/my/favorites')
    } else if (tab.value === 'notes') {
      notes.value = await authFetch<NoteItem[]>('/api/interactive/my/notes')
    } else if (tab.value === 'comments') {
      comments.value = await authFetch<CommentItem[]>('/api/interactive/my/comments')
    }
    loadedTabs.value.add(tab.value)
  } catch (err) {
    console.error('个人中心数据加载失败', err)
  } finally {
    loading.value = false
  }
}

const loadOverview = async () => {
  if (!isLoggedIn.value) return
  try {
    overview.value = await authFetch<StatOverview>('/api/interactive/my/overview')
  } catch (err) {
    console.error('统计数据加载失败', err)
  }
}

// 登录态就绪后加载（restore 在 app.vue onMounted 执行，watch immediate 会在其后触发）
watch(isLoggedIn, (v) => {
  if (v) {
    loadOverview()
    loadTab()
  }
}, { immediate: true })

const removeFavorite = async (item: FavoriteItem) => {
  try {
    await authFetch(`/api/interactive/${item.slug}/favorite`, { method: 'POST' })
    favorites.value = favorites.value.filter(f => f.slug !== item.slug)
    if (overview.value) overview.value.favorites = Math.max(0, overview.value.favorites - 1)
  } catch (err) {
    console.error('取消收藏失败', err)
  }
}

const removeComment = async (item: CommentItem) => {
  if (!confirm('确定删除这条评论吗？')) return
  try {
    await authFetch(`/api/interactive/comments/${item.id}`, { method: 'DELETE' })
    comments.value = comments.value.filter(c => c.id !== item.id)
    if (overview.value) overview.value.comments = Math.max(0, overview.value.comments - 1)
  } catch (err: unknown) {
    const e = err as { data?: { message?: string } }
    alert(e?.data?.message || '删除失败')
  }
}

const fmtTime = (iso: string) => new Date(iso).toLocaleString('zh-CN', { hour12: false })

// ---- 账号设置 ----
const nicknameInput = ref('')
const avatarInput = ref('')
const profileSaving = ref(false)
const profileMsg = ref('')

const initSettings = () => {
  nicknameInput.value = user.value?.nickname || ''
  avatarInput.value = user.value?.avatar || ''
}

const saveProfile = async () => {
  profileMsg.value = ''
  if (!nicknameInput.value.trim()) {
    profileMsg.value = '昵称不能为空'
    return
  }
  profileSaving.value = true
  try {
    const data = await authFetch<UserInfo>(`/api/auth/profile`, {
      method: 'PUT',
      body: { nickname: nicknameInput.value.trim(), avatar: avatarInput.value.trim() }
    })
    updateUser(data)
    profileMsg.value = '资料已更新'
    loadOverview()
  } catch (err: unknown) {
    const e = err as { data?: { message?: string } }
    profileMsg.value = e?.data?.message || '保存失败'
  } finally {
    profileSaving.value = false
  }
}

const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const pwdSaving = ref(false)
const pwdMsg = ref('')
const pwdError = ref(false)

const savePassword = async () => {
  pwdMsg.value = ''
  pwdError.value = false
  if (newPassword.value.length < 8) {
    pwdMsg.value = '新密码至少 8 位'
    pwdError.value = true
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    pwdMsg.value = '两次输入的新密码不一致'
    pwdError.value = true
    return
  }
  pwdSaving.value = true
  const hadPassword = Boolean(user.value?.has_password)
  try {
    const data = await authFetch<UserInfo>(`/api/auth/password`, {
      method: 'POST',
      body: {
        old_password: hadPassword ? oldPassword.value : null,
        new_password: newPassword.value
      }
    })
    updateUser({ has_password: true })
    pwdMsg.value = hadPassword ? '密码已修改' : '密码已设置，以后可以用账号密码登录'
    oldPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
    pwdError.value = false
  } catch (err: unknown) {
    const e = err as { data?: { message?: string } }
    pwdMsg.value = e?.data?.message || '操作失败'
    pwdError.value = true
  } finally {
    pwdSaving.value = false
  }
}

watch(isLoggedIn, (v) => {
  if (v) initSettings()
}, { immediate: true })
watch(tab, () => {
  if (tab.value === 'settings') initSettings()
})

useSeoMeta({ title: '个人中心 | 虞先森的技术站' })
</script>

<template>
  <div class="mx-auto max-w-4xl px-4 py-8 pt-24 animate-fade-in">
    <!-- 未登录引导 -->
    <div v-if="!isLoggedIn" class="site-card mx-auto mt-16 max-w-md p-8 text-center">
      <h1 class="mb-2 text-xl font-bold">个人中心</h1>
      <p class="mb-6 text-sm text-slate-500 dark:text-slate-400">登录后可以管理你的收藏、笔记与评论</p>
      <button
        class="cursor-pointer rounded-lg bg-primary-brand px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary-brand-dark"
        @click="open()"
      >立即登录</button>
    </div>

    <template v-else>
      <!-- 用户信息 + 统计 -->
      <div class="site-card mb-6 flex flex-wrap items-center justify-between gap-4 p-6">
        <div class="flex items-center gap-4">
          <span class="flex h-14 w-14 items-center justify-center rounded-full bg-primary-brand text-xl font-bold text-white">
            {{ (user?.nickname || 'U').slice(0, 1) }}
          </span>
          <div>
            <p class="text-lg font-bold">{{ user?.nickname }}</p>
            <p class="text-xs text-slate-400">欢迎回来，继续你的学习之旅</p>
          </div>
        </div>
        <div class="flex gap-6 text-center">
          <div>
            <p class="text-xl font-bold text-primary-brand">{{ overview?.favorites ?? '-' }}</p>
            <p class="text-xs text-slate-400">收藏</p>
          </div>
          <div>
            <p class="text-xl font-bold text-primary-brand">{{ overview?.notes ?? '-' }}</p>
            <p class="text-xs text-slate-400">笔记</p>
          </div>
          <div>
            <p class="text-xl font-bold text-primary-brand">{{ overview?.comments ?? '-' }}</p>
            <p class="text-xs text-slate-400">评论</p>
          </div>
        </div>
      </div>

      <!-- Tab 切换 -->
      <div class="mb-5 flex gap-2">
        <button
          v-for="t in [
            { key: 'favorites', label: '我的收藏', icon: Bookmark },
            { key: 'notes', label: '我的笔记', icon: NotebookPen },
            { key: 'comments', label: '我的评论', icon: MessageSquare },
            { key: 'settings', label: '账号设置', icon: UserCog }
          ]" :key="t.key"
          class="flex cursor-pointer items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium transition-colors"
          :class="tab === t.key ? 'bg-primary-brand text-white' : 'bg-white text-slate-600 hover:bg-slate-100 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700'"
          @click="tab = t.key as typeof tab; loadTab()"
        >
          <component :is="t.icon" class="h-4 w-4" />{{ t.label }}
        </button>
      </div>

      <div v-if="loading" class="py-16 text-center text-slate-400"><Loader2 class="mx-auto h-6 w-6 animate-spin" /></div>

      <!-- 我的收藏 -->
      <div v-else-if="tab === 'favorites'">
        <div v-if="favorites.length === 0" class="site-card p-10 text-center text-sm text-slate-400">
          还没有收藏，去文章页点「收藏」吧
        </div>
        <ul v-else class="space-y-3">
          <li v-for="f in favorites" :key="f.slug" class="site-card flex items-center justify-between gap-4 p-4">
            <NuxtLink :to="`/posts/${f.slug}`" class="min-w-0 flex-1">
              <span class="block truncate text-sm font-medium hover:text-primary-brand">{{ titleOf(f.slug) }}</span>
              <span class="mt-1 block text-xs text-slate-400">收藏于 {{ fmtTime(f.created_at) }}</span>
            </NuxtLink>
            <button
              class="flex shrink-0 cursor-pointer items-center gap-1 rounded-lg border border-slate-200 px-3 py-1.5 text-xs text-slate-500 transition-colors hover:border-red-300 hover:text-red-500 dark:border-slate-600"
              @click="removeFavorite(f)"
            ><Star class="h-3.5 w-3.5" />取消收藏</button>
          </li>
        </ul>
      </div>

      <!-- 我的笔记 -->
      <div v-else-if="tab === 'notes'">
        <div v-if="notes.length === 0" class="site-card p-10 text-center text-sm text-slate-400">
          还没有笔记，去文章页「我的笔记」里记录学习心得吧
        </div>
        <ul v-else class="space-y-3">
          <li v-for="n in notes" :key="n.slug" class="site-card p-4">
            <NuxtLink :to="`/posts/${n.slug}`" class="text-sm font-medium hover:text-primary-brand">{{ titleOf(n.slug) }}</NuxtLink>
            <p class="mt-1.5 line-clamp-2 text-sm text-slate-500 dark:text-slate-400">{{ n.excerpt || '（空笔记）' }}</p>
            <p class="mt-1.5 text-xs text-slate-400">更新于 {{ fmtTime(n.updated_at) }}</p>
          </li>
        </ul>
      </div>

      <!-- 账号设置 -->
      <div v-else-if="tab === 'settings'" class="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <!-- 个人资料 -->
        <div class="site-card p-5">
          <h3 class="mb-4 text-sm font-semibold">个人资料</h3>
          <div class="space-y-3">
            <div>
              <label class="mb-1 block text-xs text-slate-500 dark:text-slate-400">昵称</label>
              <input
                v-model="nicknameInput"
                type="text"
                maxlength="32"
                class="w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 text-sm outline-none transition-colors focus:border-primary-brand dark:border-slate-600"
              />
            </div>
            <div>
              <label class="mb-1 block text-xs text-slate-500 dark:text-slate-400">头像图片 URL（选填）</label>
              <input
                v-model="avatarInput"
                type="url"
                maxlength="512"
                placeholder="https://..."
                class="w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 text-sm outline-none transition-colors focus:border-primary-brand dark:border-slate-600"
              />
            </div>
            <p
              v-if="profileMsg"
              class="rounded-lg px-3 py-2 text-xs"
              :class="profileMsg === '资料已更新'
                ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400'
                : 'bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-400'"
            >{{ profileMsg }}</p>
            <button
              class="w-full cursor-pointer rounded-lg bg-primary-brand px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary-brand-dark disabled:cursor-not-allowed disabled:opacity-50"
              :disabled="profileSaving"
              @click="saveProfile"
            >{{ profileSaving ? '保存中…' : '保存资料' }}</button>
          </div>
        </div>

        <!-- 密码 -->
        <div class="site-card p-5">
          <h3 class="mb-4 text-sm font-semibold">
            {{ user?.has_password ? '修改密码' : '设置密码' }}
            <span v-if="!user?.has_password" class="ml-1 text-xs font-normal text-slate-400">
              当前是短信/第三方登录，设置密码后可用账号密码登录
            </span>
          </h3>
          <div class="space-y-3">
            <div v-if="user?.has_password">
              <label class="mb-1 block text-xs text-slate-500 dark:text-slate-400">旧密码</label>
              <input
                v-model="oldPassword"
                type="password"
                maxlength="64"
                class="w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 text-sm outline-none transition-colors focus:border-primary-brand dark:border-slate-600"
              />
            </div>
            <div>
              <label class="mb-1 block text-xs text-slate-500 dark:text-slate-400">新密码（至少 8 位）</label>
              <input
                v-model="newPassword"
                type="password"
                maxlength="64"
                class="w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 text-sm outline-none transition-colors focus:border-primary-brand dark:border-slate-600"
              />
            </div>
            <div>
              <label class="mb-1 block text-xs text-slate-500 dark:text-slate-400">确认新密码</label>
              <input
                v-model="confirmPassword"
                type="password"
                maxlength="64"
                class="w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 text-sm outline-none transition-colors focus:border-primary-brand dark:border-slate-600"
              />
            </div>
            <p
              v-if="pwdMsg"
              class="rounded-lg px-3 py-2 text-xs"
              :class="pwdError
                ? 'bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-400'
                : 'bg-emerald-50 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400'"
            >{{ pwdMsg }}</p>
            <button
              class="w-full cursor-pointer rounded-lg bg-primary-brand px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary-brand-dark disabled:cursor-not-allowed disabled:opacity-50"
              :disabled="pwdSaving"
              @click="savePassword"
            >{{ pwdSaving ? '提交中…' : user?.has_password ? '修改密码' : '设置密码' }}</button>
          </div>
        </div>
      </div>

      <!-- 我的评论 -->
      <div v-else>
        <div v-if="comments.length === 0" class="site-card p-10 text-center text-sm text-slate-400">
          还没有发表过评论
        </div>
        <ul v-else class="space-y-3">
          <li v-for="c in comments" :key="c.id" class="site-card p-4">
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0 flex-1">
                <NuxtLink :to="`/posts/${c.slug}`" class="text-xs text-primary-brand hover:underline">
                  {{ titleOf(c.slug) }}
                </NuxtLink>
                <p class="mt-1 whitespace-pre-wrap break-words text-sm leading-relaxed text-slate-700 dark:text-slate-200">{{ c.content }}</p>
                <p class="mt-1.5 text-xs text-slate-400">发表于 {{ fmtTime(c.created_at) }}</p>
              </div>
              <button
                class="flex shrink-0 cursor-pointer items-center gap-1 rounded-lg border border-slate-200 px-3 py-1.5 text-xs text-slate-500 transition-colors hover:border-red-300 hover:text-red-500 dark:border-slate-600"
                @click="removeComment(c)"
              ><Trash2 class="h-3.5 w-3.5" />删除</button>
            </div>
          </li>
        </ul>
      </div>
    </template>
  </div>
</template>
