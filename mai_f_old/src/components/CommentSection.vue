<template>
  <div class="comment-section">
    <div class="comment-input-card">
      <div class="comment-input-header">
        <span class="comment-input-title">评论区</span>
        <span v-if="muteInfo" class="comment-mute-tip">
          {{ muteInfo }}
        </span>
      </div>
      <el-input
        v-model="content"
        type="textarea"
        :rows="3"
        :maxlength="500"
        show-word-limit
        :placeholder="muteInfo ? '当前处于禁言状态，无法发表评论' : '发表你的看法（最多500字）'"
        :disabled="!!muteInfo || submitting"
      />
      <div class="comment-input-actions">
        <el-button
          class="comment-submit-button"
          type="primary"
          size="small"
          :disabled="!!muteInfo"
          :loading="submitting"
          @click="handleSubmit"
        >
          发布评论
        </el-button>
      </div>
    </div>

    <div
      v-if="lastDeleted"
      class="comment-undo-bar"
    >
      <span>已删除一条评论</span>
      <el-button
        text
        size="small"
        @click="handleUndoDelete"
      >
        撤销
      </el-button>
    </div>

    <div class="comment-list-card">
      <div v-if="loading" class="comment-loading">
        正在加载评论...
      </div>
      <div v-else-if="items.length === 0" class="comment-empty">
        暂无评论，快来抢沙发吧～
      </div>
      <div v-else class="comment-list">
        <div
          v-for="item in topLevelComments"
          :key="item.id"
          class="comment-item"
        >
          <div class="comment-main">
            <el-avatar
              :size="32"
              :src="resolveAvatarUrl(item)"
              class="comment-avatar"
            >
              <template #default>
                {{ getInitial(item.username) }}
              </template>
            </el-avatar>
            <div class="comment-body">
              <div class="comment-meta">
                <span class="comment-username">{{ item.username }}</span>
                <span
                  v-if="item.isOwner"
                  class="comment-tag comment-tag-owner"
                >
                  作者
                </span>
                <span
                  v-if="item.isAdmin"
                  class="comment-tag comment-tag-admin"
                >
                  管理员
                </span>
                <span class="comment-time">{{ formatTime(item.createdAt) }}</span>
              </div>
              <div class="comment-content">
                {{ item.content }}
              </div>
              <div class="comment-actions">
                <div class="comment-ops">
                  <el-button
                    v-if="canDelete(item)"
                    text
                    size="small"
                    @click="handleDelete(item)"
                  >
                    <el-icon class="comment-delete-icon">
                      <Delete />
                    </el-icon>
                  </el-button>
                  <el-button
                    v-if="canReply"
                    text
                    size="small"
                    @click="startReply(item)"
                  >
                    回复
                  </el-button>
                </div>
                <div class="comment-reactions">
                  <div
                    class="comment-reaction-button"
                    :class="{
                      'is-active': item.myReaction === 'dislike',
                      'is-disabled': reactingIds.has && reactingIds.has(item.id)
                    }"
                    @click="handleReact(item, 'dislike')"
                  >
                    <span class="comment-reaction-icon">
                      <svg
                        class="comment-thumb comment-thumb-down"
                        viewBox="0 0 24 24"
                        aria-hidden="true"
                      >
                        <path
                          d="M15 3H6c-.83 0-1.54.5-1.84 1.22L1.14 11.27C1.05 11.5 1 11.74 1 12v1c0 1.1.9 2 2 2h6.31l-.95 4.57-.03.32c0 .41.17.79.44 1.06L9.83 22 16.41 15.41C16.78 15.05 17 14.55 17 14V5c0-1.1-.9-2-2-2zm4 0v12h4V3h-4z"
                          fill-rule="evenodd"
                          clip-rule="evenodd"
                        />
                      </svg>
                    </span>
                    <span class="comment-reaction-count">
                      {{
                        item.dislikeCount && item.dislikeCount > 0
                          ? formatCount(item.dislikeCount)
                          : ''
                      }}
                    </span>
                  </div>
                  <div
                    class="comment-reaction-button"
                    :class="{
                      'is-active': item.myReaction === 'like',
                      'is-disabled': reactingIds.has && reactingIds.has(item.id)
                    }"
                    @click="handleReact(item, 'like')"
                  >
                    <span class="comment-reaction-icon">
                      <svg
                        class="comment-heart"
                        viewBox="0 0 24 24"
                        aria-hidden="true"
                      >
                        <path
                          d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 6 4 4 6.5 4c1.74 0 3.41 1.01 4.22 2.61C11.53 5.01 13.2 4 14.94 4 17.44 4 19.44 6 19.44 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"
                        />
                      </svg>
                    </span>
                    <span class="comment-reaction-count">
                      {{
                        item.likeCount && item.likeCount > 0
                          ? formatCount(item.likeCount)
                          : ''
                      }}
                    </span>
                  </div>
                </div>
              </div>
              <div
                v-if="replyingTo && replyingTo.id === item.id"
                class="reply-input"
              >
                <el-input
                  v-model="replyContent"
                  type="textarea"
                  :rows="2"
                  :maxlength="500"
                  show-word-limit
                  :placeholder="replyPlaceholder"
                  :disabled="!!muteInfo || submittingReply"
                />
                <div class="comment-input-actions">
                  <el-button
                    size="small"
                    @click="cancelReply"
                  >
                    取消
                  </el-button>
                  <el-button
                    class="comment-submit-button"
                    type="primary"
                    size="small"
                    :disabled="!replyContent.trim() || !!muteInfo"
                    :loading="submittingReply"
                    @click="handleSubmitReply"
                  >
                    发送回复
                  </el-button>
                </div>
              </div>
            </div>
          </div>
          <div class="comment-replies">
            <div
              v-for="reply in repliesMap[item.id] || []"
              :key="reply.id"
              class="comment-item reply-item"
            >
              <el-avatar
                :size="24"
                :src="resolveAvatarUrl(reply, 32)"
                class="comment-avatar reply-avatar"
              >
                <template #default>
                  {{ getInitial(reply.username) }}
                </template>
              </el-avatar>
              <div class="comment-body">
                <div class="comment-meta">
                  <span class="comment-username">{{ reply.username }}</span>
                  <span
                    v-if="reply.isOwner"
                    class="comment-tag comment-tag-owner"
                  >
                    作者
                  </span>
                  <span
                    v-if="reply.isAdmin"
                    class="comment-tag comment-tag-admin"
                  >
                    管理员
                  </span>
                  <span class="comment-time">{{ formatTime(reply.createdAt) }}</span>
                </div>
                <div class="comment-content">
                  <span v-if="reply.replyToName" class="comment-reply-to">回复 @{{ reply.replyToName }}</span>
                  {{ reply.content }}
                </div>
                <div class="comment-actions">
                  <div class="comment-ops">
                    <el-button
                      v-if="canDelete(reply)"
                      text
                      size="small"
                      @click="handleDelete(reply)"
                    >
                      <el-icon class="comment-delete-icon">
                        <Delete />
                      </el-icon>
                    </el-button>
                    <el-button
                      v-if="canReply"
                      text
                      size="small"
                      @click="startReply(item, reply)"
                    >
                      回复
                    </el-button>
                  </div>
                  <div class="comment-reactions">
                    <div
                      class="comment-reaction-button"
                      :class="{
                        'is-active': reply.myReaction === 'dislike',
                        'is-disabled': reactingIds.has && reactingIds.has(reply.id)
                      }"
                      @click="handleReact(reply, 'dislike')"
                    >
                      <span class="comment-reaction-icon">
                        <svg
                          class="comment-thumb comment-thumb-down"
                          viewBox="0 0 24 24"
                          aria-hidden="true"
                        >
                          <path
                            d="M15 3H6c-.83 0-1.54.5-1.84 1.22L1.14 11.27C1.05 11.5 1 11.74 1 12v1c0 1.1.9 2 2 2h6.31l-.95 4.57-.03.32c0 .41.17.79.44 1.06L9.83 22 16.41 15.41C16.78 15.05 17 14.55 17 14V5c0-1.1-.9-2-2-2zm4 0v12h4V3h-4z"
                            fill-rule="evenodd"
                            clip-rule="evenodd"
                          />
                        </svg>
                      </span>
                      <span class="comment-reaction-count">
                        {{
                          reply.dislikeCount && reply.dislikeCount > 0
                            ? formatCount(reply.dislikeCount)
                            : ''
                        }}
                      </span>
                    </div>
                    <div
                      class="comment-reaction-button"
                      :class="{
                        'is-active': reply.myReaction === 'like',
                        'is-disabled': reactingIds.has && reactingIds.has(reply.id)
                      }"
                      @click="handleReact(reply, 'like')"
                    >
                      <span class="comment-reaction-icon">
                        <svg
                          class="comment-heart"
                          viewBox="0 0 24 24"
                          aria-hidden="true"
                        >
                          <path
                            d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 6 4 4 6.5 4c1.74 0 3.41 1.01 4.22 2.61C11.53 5.01 13.2 4 14.94 4 17.44 4 19.44 6 19.44 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"
                          />
                        </svg>
                      </span>
                      <span class="comment-reaction-count">
                        {{
                          reply.likeCount && reply.likeCount > 0
                            ? formatCount(reply.likeCount)
                            : ''
                        }}
                      </span>
                    </div>
                  </div>
                </div>
                <div
                  v-if="replyingTo && replyingTo.id === reply.id"
                  class="reply-input"
                >
                  <el-input
                    v-model="replyContent"
                    type="textarea"
                    :rows="2"
                    :maxlength="500"
                    show-word-limit
                    :placeholder="replyPlaceholder"
                    :disabled="!!muteInfo || submittingReply"
                  />
                  <div class="comment-input-actions">
                    <el-button
                      size="small"
                      @click="cancelReply"
                    >
                      取消
                    </el-button>
                    <el-button
                      class="comment-submit-button"
                      type="primary"
                      size="small"
                      :disabled="!replyContent.trim() || !!muteInfo"
                      :loading="submittingReply"
                      @click="handleSubmitReply"
                    >
                      发送回复
                    </el-button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessageBox } from 'element-plus'
import { Delete } from '@element-plus/icons-vue'
import { getComments, createComment, deleteComment, reactComment, restoreComment } from '@/api/comments'
import { handleApiError, showApiErrorNotification, showErrorNotification, showSuccessNotification, showWarningNotification } from '@/utils/api'
import { useUserStore } from '@/stores/user'

const props = defineProps({
  targetType: {
    type: String,
    required: true
  },
  targetId: {
    type: String,
    required: true
  },
  ownerId: {
    type: String,
    required: false,
    default: ''
  }
})

const userStore = useUserStore()
const { user, isAdmin } = storeToRefs(userStore)

const items = reactive([])
const repliesMap = reactive({})
const loading = ref(false)
const content = ref('')
const submitting = ref(false)
const replyingTo = ref(null)
const replyContent = ref('')
const submittingReply = ref(false)
const reactingIds = ref(new Set())
const deletingIds = ref(new Set())
const lastDeleted = ref(null)

const apiBase = import.meta.env.VITE_API_BASE_URL || `${window.location.protocol}//${window.location.hostname}:9278/api`

const muteInfo = computed(() => {
  if (!user.value || !user.value.is_muted) {
    return ''
  }
  const until = user.value.muted_until
  if (!until) {
    return '当前账户已被永久禁言，无法发表评论'
  }
  const date = new Date(until)
  if (Number.isNaN(date.getTime())) {
    return '当前账户已被禁言，无法发表评论'
  }
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  const hh = String(date.getHours()).padStart(2, '0')
  const mm = String(date.getMinutes()).padStart(2, '0')
  return `当前账户已被禁言，解禁时间：${y}-${m}-${d} ${hh}:${mm}`
})

const canReply = computed(() => {
  return !!user.value && !muteInfo.value
})

const replyPlaceholder = computed(() => {
  if (muteInfo.value) {
    return '当前处于禁言状态，无法发表评论'
  }
  if (replyingTo.value && replyingTo.value._replyToName) {
    return `回复 @${replyingTo.value._replyToName}（最多500字）`
  }
  return '回复内容（最多500字）'
})

const compareByCreatedDesc = (a, b) => {
  const ta = a && a.createdAt ? new Date(a.createdAt).getTime() : 0
  const tb = b && b.createdAt ? new Date(b.createdAt).getTime() : 0
  return tb - ta
}

const formatCount = (value) => {
  const n = Number(value || 0)
  if (!Number.isFinite(n) || n <= 0) {
    return ''
  }
  if (n < 1000) {
    return `${n}`
  }
  if (n < 10000) {
    const k = n / 1000
    const s = Math.round(k * 10) / 10
    return `${s}k`
  }
  const w = n / 10000
  const s = Math.round(w * 10) / 10
  return `${s}w`
}

const topLevelComments = computed(() => {
  return items
    .filter((item) => !item.parentId)
    .slice()
    .sort(compareByCreatedDesc)
})

const currentUserId = computed(() => {
  return user.value && user.value.id ? user.value.id : ''
})

const isOwnerUser = (userId) => {
  if (!userId || !props.ownerId) {
    return false
  }
  return String(userId) === String(props.ownerId)
}

const canDelete = (item) => {
  if (!item || !currentUserId.value) {
    return false
  }
  if (item.userId === currentUserId.value) {
    return true
  }
  if (isOwnerUser(currentUserId.value)) {
    return true
  }
  if (isAdmin.value) {
    return true
  }
  return false
}

const resolveAvatarUrl = (item, size = 40) => {
  if (!item || !item.userId) {
    return ''
  }
  const base = apiBase || ''
  const trimmedBase = base.endsWith('/') ? base.slice(0, -1) : base
  let url = `${trimmedBase}/users/${item.userId}/avatar?size=${size}`
  if (item.avatarUpdatedAt) {
    url += `&t=${encodeURIComponent(item.avatarUpdatedAt)}`
  }
  return url
}

const getInitial = (name) => {
  if (!name) {
    return '?'
  }
  return name.trim().slice(0, 1)
}

const formatTime = (value) => {
  if (!value) {
    return ''
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return ''
  }
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSeconds = Math.floor(diffMs / 1000)
  if (diffSeconds < 60) {
    return '刚刚'
  }
  const diffMinutes = Math.floor(diffSeconds / 60)
  if (diffMinutes < 60) {
    return `${diffMinutes}分钟前`
  }
  const diffHours = Math.floor(diffMinutes / 60)
  if (diffHours < 24) {
    return `${diffHours}小时前`
  }
  const diffDays = Math.floor(diffHours / 24)
  if (diffDays < 3) {
    return `${diffDays}天前`
  }
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  const hh = String(date.getHours()).padStart(2, '0')
  const mm = String(date.getMinutes()).padStart(2, '0')
  return `${y}-${m}-${d} ${hh}:${mm}`
}

const rebuildTree = (list) => {
  items.splice(0, items.length)
  Object.keys(repliesMap).forEach((key) => {
    delete repliesMap[key]
  })
  const userId = currentUserId.value
  const admin = isAdmin.value

  // 将后端 snake_case 字段映射为前端 camelCase
  const mapComment = (raw) => ({
    ...raw,
    userId: raw.userId || raw.user,
    parentId: raw.parentId || raw.parent,
    username: raw.username || raw.user_name,
    avatar: raw.avatar || raw.user_avatar,
    likeCount: raw.likeCount ?? raw.like_count ?? 0,
    dislikeCount: raw.dislikeCount ?? raw.dislike_count ?? 0,
    myReaction: raw.myReaction || raw.my_reaction || (raw.is_liked ? 'like' : null),
    replyToName: raw.replyToName || raw.reply_to_name || null,
    createdAt: raw.createdAt || raw.create_datetime,
    // 递归映射子评论
    replies: Array.isArray(raw.replies) ? raw.replies.map(mapComment) : [],
  })

  // 扁平化树形结构（后端返回嵌套的 replies）
  const flatList = []
  const flatten = (commentList) => {
    commentList.forEach((c) => {
      const mapped = mapComment(c)
      flatList.push(mapped)
      if (Array.isArray(mapped.replies) && mapped.replies.length > 0) {
        flatten(c.replies || [])
      }
    })
  }
  flatten(list)

  flatList.forEach((item) => {
    item.isOwner = isOwnerUser(item.userId)
    item.isAdmin = admin && item.userId === userId
    if (!item.parentId) {
      items.push(item)
    } else {
      if (!repliesMap[item.parentId]) {
        repliesMap[item.parentId] = []
      }
      repliesMap[item.parentId].push(item)
    }
  })

  Object.keys(repliesMap).forEach((key) => {
    repliesMap[key].sort(compareByCreatedDesc)
  })
}

const fetchComments = async () => {
  if (!props.targetId || !props.targetType) {
    return
  }
  loading.value = true
  try {
    const response = await getComments({
      target_type: props.targetType,
      target_id: props.targetId
    })
    if (response && response.data) {
      rebuildTree(response.data)
    } else if (response && response.items) {
      rebuildTree(response.items)
    } else {
      rebuildTree([])
    }
  } catch (error) {
    showApiErrorNotification(error, '获取评论失败')
  } finally {
    loading.value = false
  }
}

const handleSubmit = async () => {
  const text = content.value.trim()
  if (!text) {
    return
  }
  if (text.length > 500) {
    showErrorNotification('评论内容不能超过500字')
    return
  }
  submitting.value = true
  try {
    const payload = {
      target_type: props.targetType,
      target_id: props.targetId,
      content: text
    }
    const response = await createComment(payload)
    if (response && response.data) {
      content.value = ''
      await fetchComments()
      showSuccessNotification('评论已发布')
    }
  } catch (error) {
    const response = error && error.response
    const data = response && response.data
    const rawMessage =
      (data && data.message) ||
      (data && data.error && data.error.message) ||
      ''
    if (rawMessage && rawMessage.includes('麦麦')) {
      await ElMessageBox.alert(rawMessage, '通知', {
        confirmButtonText: '知道了'
      })
    } else {
      showApiErrorNotification(error, '发表评论失败')
    }
  } finally {
    submitting.value = false
  }
}

const startReply = (root, reply = null) => {
  if (!user.value || muteInfo.value) {
    return
  }
  replyingTo.value = reply || root
  // 记录一级评论 ID，确保所有回复都挂在一级评论下
  replyingTo.value._rootId = root.id
  // 回复二级评论时，记录被回复评论的 ID 和用户名
  replyingTo.value._replyToId = reply ? reply.id : null
  replyingTo.value._replyToName = reply ? reply.username : null
  replyContent.value = ''
}

const cancelReply = () => {
  replyingTo.value = null
  replyContent.value = ''
}

const handleSubmitReply = async () => {
  if (!replyingTo.value) {
    return
  }
  const text = replyContent.value.trim()
  if (!text) {
    return
  }
  if (text.length > 500) {
    showErrorNotification('回复内容不能超过500字')
    return
  }
  submittingReply.value = true
  try {
    const payload = {
      target_type: props.targetType,
      target_id: props.targetId,
      content: text,
      // 始终以一级评论作为 parent，保持两层结构
      parent: replyingTo.value._rootId || replyingTo.value.id
    }
    // 回复二级评论时，传 reply_to 记录被回复的评论
    if (replyingTo.value._replyToId) {
      payload.reply_to = replyingTo.value._replyToId
    }
    const response = await createComment(payload)
    if (response && response.data) {
      replyContent.value = ''
      replyingTo.value = null
      await fetchComments()
      showSuccessNotification('回复已发布')
    }
  } catch (error) {
    const response = error && error.response
    const data = response && response.data
    const rawMessage =
      (data && data.message) ||
      (data && data.error && data.error.message) ||
      ''
    if (rawMessage && rawMessage.includes('麦麦')) {
      await ElMessageBox.alert(rawMessage, '通知', {
        confirmButtonText: '知道了'
      })
    } else {
      showApiErrorNotification(error, '发送回复失败')
    }
  } finally {
    submittingReply.value = false
  }
}

const handleDelete = async (item) => {
  if (!item || !item.id) {
    return
  }
  if (deletingIds.value.has(item.id)) {
    return
  }
  try {
    await ElMessageBox.confirm(
      '删除后该评论将被隐藏，确认删除吗？',
      '确认删除评论',
      {
        type: 'warning'
      }
    )
  } catch {
    return
  }
  deletingIds.value.add(item.id)
  try {
    await deleteComment(item.id)
    lastDeleted.value = {
      id: item.id,
      parentId: item.parentId
    }
    showSuccessNotification('评论已删除', {
      duration: 3000,
      onClose: () => {
        lastDeleted.value = null
      }
    })
    await fetchComments()
  } catch (error) {
    showApiErrorNotification(error, '删除评论失败')
  } finally {
    deletingIds.value.delete(item.id)
  }
}

const handleUndoDelete = async () => {
  const payload = lastDeleted.value
  if (!payload || !payload.id) {
    return
  }
  try {
    await restoreComment(payload.id)
    lastDeleted.value = null
    await fetchComments()
    showSuccessNotification('已撤销删除')
  } catch (error) {
    showApiErrorNotification(error, '撤销删除失败')
  }
}

const handleReact = async (item, action) => {
  if (!item || !item.id) {
    return
  }
  if (!user.value) {
    showWarningNotification('请先登录后再进行互动')
    return
  }
  if (reactingIds.value.has(item.id)) {
    return
  }
  let nextAction = action
  if (item.myReaction === action) {
    nextAction = 'clear'
  }
  reactingIds.value.add(item.id)
  try {
    await reactComment(item.id, nextAction)
    // 操作成功后重新拉取评论列表，确保数据同步
    await fetchComments()
  } catch (error) {
    showApiErrorNotification(error, '操作失败，请稍后重试')
  } finally {
    reactingIds.value.delete(item.id)
  }
}

watch(
  () => [props.targetType, props.targetId],
  () => {
    fetchComments()
  },
  { immediate: true }
)
</script>
