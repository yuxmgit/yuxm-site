<script setup lang="ts">
// 文章互动区：点赞 / 收藏 / 评论（一层回复）/ 个人笔记（私有）
// 未登录时点击互动按钮唤起登录弹窗；所有数据以文章 slug 为键
import { Bookmark, Heart, Loader2, MessageSquare, NotebookPen, Send, Trash2 } from 'lucide-vue-next'

const props = defineProps<{ slug: string }>()

const config = useRuntimeConfig()
const { isLoggedIn, authFetch, open } = useAuth()

// ---- 状态总览 ----
interface InteractStatus {
  likes: number
  favorites: number
  comments: number
  liked: boolean
  favorited: boolean
}
const status = ref<InteractStatus | null>(null)

const loadStatus = async () => {
  try {
    if (isLoggedIn.value) {
      status.value = await authFetch<InteractStatus>(`/api/interactive/${props.slug}/status`)
    } else {
      const res = await $fetch<{ code: number; data: InteractStatus }>(
        `/api/interactive/${props.slug}/status`,
        { baseURL: config.public.apiBase }
      )
      status.value = res.data
    }
  } catch (err) {
    console.error('互动状态加载失败', err)
  }
}

// ---- 评论 ----
interface CommentItem {
  id: number
  parent_id: number | null
  content: string
  is_deleted: boolean
  created_at: string
  user: { id: number; nickname: string; avatar: string }
  can_delete: boolean
  replies: CommentItem[]
}
const comments = ref<CommentItem[]>([])
const commentTotal = ref(0)
const commentInput = ref('')
const replyTo = ref<CommentItem | null>(null)
const submitting = ref(false)
const commentsLoading = ref(false)

const loadComments = async () => {
  commentsLoading.value = true
  try {
    // 登录时带 token（接口返回 can_delete 标记），未登录走公开请求
    if (isLoggedIn.value) {
      const data = await authFetch<{ total: number; list: CommentItem[] }>(`/api/interactive/${props.slug}/comments`)
      comments.value = data.list
      commentTotal.value = data.total
    } else {
      const res = await $fetch<{ code: number; data: { total: number; list: CommentItem[] } }>(
        `/api/interactive/${props.slug}/comments`,
        { baseURL: config.public.apiBase }
      )
      comments.value = res.data.list
      commentTotal.value = res.data.total
    }
  } catch (err) {
    console.error('评论加载失败', err)
  } finally {
    commentsLoading.value = false
  }
}

const fmtTime = (iso: string) => new Date(iso).toLocaleString('zh-CN', { hour12: false })

const submitComment = async () => {
  const content = commentInput.value.trim()
  if (!content) return
  if (!isLoggedIn.value) {
    open()
    return
  }
  submitting.value = true
  try {
    const created = await authFetch<CommentItem>(`/api/interactive/${props.slug}/comments`, {
      method: 'POST',
      body: { content, parent_id: replyTo.value?.id ?? null }
    })
    if (replyTo.value) {
      replyTo.value.replies.push(created)
    } else {
      comments.value.push(created)
    }
    commentTotal.value++
    commentInput.value = ''
    replyTo.value = null
  } catch (err: unknown) {
    const e = err as { data?: { message?: string } }
    alert(e?.data?.message || '评论失败')
  } finally {
    submitting.value = false
  }
}

const deleteComment = async (item: CommentItem, parent: CommentItem | null) => {
  if (!confirm('确定删除这条评论吗？')) return
  try {
    await authFetch(`/api/interactive/comments/${item.id}`, { method: 'DELETE' })
    if (parent) {
      parent.replies = parent.replies.filter(r => r.id !== item.id)
    } else {
      const local = comments.value.find(c => c.id === item.id)
      if (local) {
        local.is_deleted = true
        local.content = ''
        local.can_delete = false
      } else {
        comments.value = comments.value.filter(c => c.id !== item.id)
      }
    }
    commentTotal.value = Math.max(0, commentTotal.value - 1)
    loadStatus()
  } catch (err: unknown) {
    const e = err as { data?: { message?: string } }
    alert(e?.data?.message || '删除失败')
  }
}

// ---- 点赞 / 收藏 ----
const toggling = ref<'like' | 'favorite' | null>(null)

const toggleLike = async () => {
  if (!isLoggedIn.value) {
    open()
    return
  }
  toggling.value = 'like'
  try {
    const data = await authFetch<{ liked: boolean; likes: number }>(`/api/interactive/${props.slug}/like`, { method: 'POST' })
    if (status.value) status.value = { ...status.value, liked: data.liked, likes: data.likes }
  } catch (err) {
    console.error('点赞失败', err)
  } finally {
    toggling.value = null
  }
}

const toggleFavorite = async () => {
  if (!isLoggedIn.value) {
    open()
    return
  }
  toggling.value = 'favorite'
  try {
    const data = await authFetch<{ favorited: boolean; favorites: number }>(`/api/interactive/${props.slug}/favorite`, { method: 'POST' })
    if (status.value) status.value = { ...status.value, favorited: data.favorited, favorites: data.favorites }
  } catch (err) {
    console.error('收藏失败', err)
  } finally {
    toggling.value = null
  }
}

// ---- 个人笔记（私有） ----
const noteContent = ref('')
const noteLoaded = ref(false)
const noteSaving = ref(false)
const noteSavedAt = ref('')

const loadNote = async () => {
  if (!isLoggedIn.value) return
  try {
    const data = await authFetch<{ content: string; updated_at: string } | null>(`/api/interactive/${props.slug}/note`)
    if (data) {
      noteContent.value = data.content
      noteSavedAt.value = fmtTime(data.updated_at)
    }
  } catch (err) {
    console.error('笔记加载失败', err)
  } finally {
    noteLoaded.value = true
  }
}

const saveNote = async () => {
  if (!isLoggedIn.value) {
    open()
    return
  }
  noteSaving.value = true
  try {
    const data = await authFetch<{ content: string; updated_at: string }>(`/api/interactive/${props.slug}/note`, {
      method: 'PUT',
      body: { content: noteContent.value }
    })
    noteSavedAt.value = fmtTime(data.updated_at)
  } catch (err: unknown) {
    const e = err as { data?: { message?: string } }
    alert(e?.data?.message || '保存失败')
  } finally {
    noteSaving.value = false
  }
}

onMounted(() => {
  loadStatus()
  loadComments()
  loadNote()
})

// 登录态变化（如在弹窗完成登录）后刷新本人相关数据
watch(isLoggedIn, (v) => {
  if (v) {
    loadStatus()
    loadComments()
    loadNote()
  }
})

const startReply = (item: CommentItem) => {
  if (!isLoggedIn.value) {
    open()
    return
  }
  replyTo.value = item
}
</script>

<template>
  <div class="mt-10 space-y-8 border-t border-slate-200 pt-8 dark:border-slate-700">
    <!-- 点赞 / 收藏操作条 -->
    <div class="flex items-center justify-center gap-4">
      <button
        class="flex cursor-pointer items-center gap-2 rounded-full border px-6 py-2.5 text-sm font-medium transition-colors"
        :class="status?.liked
          ? 'border-red-200 bg-red-50 text-red-500 dark:border-red-900 dark:bg-red-900/30'
          : 'border-slate-200 text-slate-600 hover:border-red-300 hover:text-red-500 dark:border-slate-600 dark:text-slate-300'"
        :disabled="toggling === 'like'"
        @click="toggleLike"
      >
        <Heart class="h-4 w-4" :fill="status?.liked ? 'currentColor' : 'none'" />
        {{ status?.liked ? '已赞' : '点赞' }} · {{ status?.likes ?? 0 }}
      </button>
      <button
        class="flex cursor-pointer items-center gap-2 rounded-full border px-6 py-2.5 text-sm font-medium transition-colors"
        :class="status?.favorited
          ? 'border-amber-200 bg-amber-50 text-amber-600 dark:border-amber-900 dark:bg-amber-900/30'
          : 'border-slate-200 text-slate-600 hover:border-amber-300 hover:text-amber-600 dark:border-slate-600 dark:text-slate-300'"
        :disabled="toggling === 'favorite'"
        @click="toggleFavorite"
      >
        <Bookmark class="h-4 w-4" :fill="status?.favorited ? 'currentColor' : 'none'" />
        {{ status?.favorited ? '已收藏' : '收藏' }} · {{ status?.favorites ?? 0 }}
      </button>
    </div>

    <!-- 个人笔记 -->
    <section class="site-card p-5">
      <div class="mb-3 flex items-center justify-between">
        <h3 class="flex items-center gap-2 text-sm font-semibold">
          <NotebookPen class="h-4 w-4 text-primary-brand" />我的笔记
          <span class="text-xs font-normal text-slate-400">仅自己可见</span>
        </h3>
        <span v-if="noteSavedAt" class="text-xs text-slate-400">上次保存 {{ noteSavedAt }}</span>
      </div>
      <template v-if="isLoggedIn">
        <textarea
          v-model="noteContent"
          rows="4"
          maxlength="20000"
          placeholder="记录学习心得、疑问、待办……"
          class="w-full resize-y rounded-lg border border-slate-300 bg-transparent px-3 py-2 text-sm leading-relaxed outline-none transition-colors focus:border-primary-brand dark:border-slate-600"
        ></textarea>
        <div class="mt-2 flex items-center justify-end">
          <button
            class="flex cursor-pointer items-center gap-1.5 rounded-lg bg-primary-brand px-4 py-2 text-xs font-medium text-white transition-colors hover:bg-primary-brand-dark disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="noteSaving"
            @click="saveNote"
          >
            <Loader2 v-if="noteSaving" class="h-3.5 w-3.5 animate-spin" />
            保存笔记
          </button>
        </div>
      </template>
      <p v-else class="rounded-lg bg-slate-50 px-3 py-3 text-sm text-slate-500 dark:bg-slate-700/50 dark:text-slate-400">
        登录后可在这篇文章下记录私有学习笔记
      </p>
    </section>

    <!-- 评论区 -->
    <section>
      <h3 class="mb-4 flex items-center gap-2 text-sm font-semibold">
        <MessageSquare class="h-4 w-4 text-primary-brand" />评论 · {{ commentTotal }}
      </h3>

      <!-- 发表框 -->
      <div class="mb-6">
        <p v-if="replyTo" class="mb-2 flex items-center gap-2 text-xs text-slate-500">
          回复 <span class="font-medium text-primary-brand">{{ replyTo.user.nickname }}</span>
          <button class="cursor-pointer underline hover:text-red-500" @click="replyTo = null">取消</button>
        </p>
        <textarea
          v-model="commentInput"
          rows="3"
          maxlength="500"
          :placeholder="isLoggedIn ? '写下你的评论或疑问…' : '登录后参与评论'"
          class="w-full resize-y rounded-lg border border-slate-300 bg-transparent px-3 py-2 text-sm leading-relaxed outline-none transition-colors focus:border-primary-brand dark:border-slate-600"
          @keydown.ctrl.enter="submitComment"
        ></textarea>
        <div class="mt-2 flex items-center justify-between">
          <span class="text-xs text-slate-400">{{ commentInput.length }}/500 · Ctrl+Enter 发送</span>
          <button
            class="flex cursor-pointer items-center gap-1.5 rounded-lg bg-primary-brand px-4 py-2 text-xs font-medium text-white transition-colors hover:bg-primary-brand-dark disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="submitting"
            @click="submitComment"
          >
            <Loader2 v-if="submitting" class="h-3.5 w-3.5 animate-spin" />
            <Send v-else class="h-3.5 w-3.5" />
            {{ replyTo ? '回复' : '发表评论' }}
          </button>
        </div>
      </div>

      <!-- 评论列表 -->
      <div v-if="commentsLoading" class="py-6 text-center text-sm text-slate-400">加载中…</div>
      <div v-else-if="comments.length === 0" class="py-6 text-center text-sm text-slate-400">
        还没有评论，来抢沙发～
      </div>
      <ul v-else class="space-y-5">
        <li v-for="item in comments" :key="item.id" class="border-b border-slate-100 pb-5 last:border-0 dark:border-slate-700/60">
          <div class="flex items-start gap-3">
            <span class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-brand text-xs font-bold text-white">
              {{ (item.user.nickname || 'U').slice(0, 1) }}
            </span>
            <div class="min-w-0 flex-1">
              <p class="flex flex-wrap items-center gap-2 text-xs text-slate-400">
                <span class="font-medium text-slate-700 dark:text-slate-300">{{ item.user.nickname }}</span>
                <span>{{ fmtTime(item.created_at) }}</span>
                <button
                  v-if="item.can_delete"
                  class="flex cursor-pointer items-center gap-0.5 hover:text-red-500"
                  @click="deleteComment(item, null)"
                ><Trash2 class="h-3 w-3" />删除</button>
              </p>
              <p v-if="item.is_deleted" class="mt-1 text-sm italic text-slate-400">该评论已删除</p>
              <p v-else class="mt-1 whitespace-pre-wrap break-words text-sm leading-relaxed text-slate-700 dark:text-slate-200">{{ item.content }}</p>
              <button
                class="mt-1 cursor-pointer text-xs text-slate-400 hover:text-primary-brand"
                @click="startReply(item)"
              >回复</button>

              <!-- 一层回复 -->
              <ul v-if="item.replies.length" class="mt-3 space-y-3 border-l-2 border-slate-100 pl-3 dark:border-slate-700">
                <li v-for="reply in item.replies" :key="reply.id" class="flex items-start gap-2">
                  <span class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-slate-400 text-[10px] font-bold text-white">
                    {{ (reply.user.nickname || 'U').slice(0, 1) }}
                  </span>
                  <div class="min-w-0 flex-1">
                    <p class="flex flex-wrap items-center gap-2 text-xs text-slate-400">
                      <span class="font-medium text-slate-600 dark:text-slate-300">{{ reply.user.nickname }}</span>
                      <span>{{ fmtTime(reply.created_at) }}</span>
                      <button
                        v-if="reply.can_delete"
                        class="flex cursor-pointer items-center gap-0.5 hover:text-red-500"
                        @click="deleteComment(reply, item)"
                      ><Trash2 class="h-3 w-3" />删除</button>
                    </p>
                    <p class="mt-0.5 whitespace-pre-wrap break-words text-sm leading-relaxed text-slate-700 dark:text-slate-200">{{ reply.content }}</p>
                    <button
                      class="mt-0.5 cursor-pointer text-xs text-slate-400 hover:text-primary-brand"
                      @click="startReply(item)"
                    >回复</button>
                  </div>
                </li>
              </ul>
            </div>
          </div>
        </li>
      </ul>
    </section>
  </div>
</template>
