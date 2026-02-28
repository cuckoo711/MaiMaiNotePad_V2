<template>
  <div class="home-container">
    <!-- 左侧整列菜单 -->
    <aside :class="['side-menu', { collapsed: isCollapsed }]">
      <div class="side-header">
        <div class="logo-wrapper">
          <img src="/logo.svg" alt="麦麦笔记本" class="logo-img" />
          <div class="product-info">
            <h1>麦麦笔记本</h1>
            <p class="slogan">知识库与人设卡分享平台</p>
          </div>
        </div>
      </div>
      <el-menu
        class="menu-wrapper"
        router
        :collapse="isCollapsed"
        :unique-opened="true"
        :default-active="$route.path"
        :collapse-transition="false"
      >
        <el-sub-menu index="/square-group">
          <template #title>
            <el-icon>
              <Collection />
            </el-icon>
            <span class="menu-label">广场</span>
          </template>
          <el-menu-item index="/persona-card">
            <span class="menu-label">人设卡广场</span>
          </el-menu-item>
          <el-menu-item index="/knowledge-base">
            <span class="menu-label">知识库广场</span>
          </el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="/my-group">
          <template #title>
            <el-icon>
              <UserFilled />
            </el-icon>
            <span class="menu-label">我的</span>
          </template>
          <el-menu-item index="/my-persona">
            <span class="menu-label">我的人设卡</span>
          </el-menu-item>
          <el-menu-item index="/my-knowledge">
            <span class="menu-label">我的知识库</span>
          </el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="/favorite-group">
          <template #title>
            <el-icon>
              <StarFilled />
            </el-icon>
            <span class="menu-label">收藏</span>
          </template>
          <el-menu-item index="/favorite-persona">
            <span class="menu-label">人设卡</span>
          </el-menu-item>
          <el-menu-item index="/favorite-knowledge">
            <span class="menu-label">知识库</span>
          </el-menu-item>
        </el-sub-menu>
        <el-sub-menu v-if="isAdmin" index="/review-group">
          <template #title>
            <el-icon>
              <Check />
            </el-icon>
            <span class="menu-label">管理</span>
          </template>
          <el-menu-item index="/admin-dashboard">
            <span class="menu-label">运营看板</span>
          </el-menu-item>
          <el-menu-item index="/knowledge-review">
            <span class="menu-label">知识库审核</span>
          </el-menu-item>
          <el-menu-item index="/persona-review">
            <span class="menu-label">人设卡审核</span>
          </el-menu-item>
          <el-menu-item index="/admin-users">
            <span class="menu-label">用户管理</span>
          </el-menu-item>
          <el-menu-item index="/admin-mute">
            <span class="menu-label">禁言管理</span>
          </el-menu-item>
          <el-menu-item index="/admin-announcement">
            <span class="menu-label">发布公告</span>
          </el-menu-item>
        </el-sub-menu>
      </el-menu>
    </aside>

    <!-- 右侧主区域 -->
    <div class="main-layout">
      <header class="top-header">
        <div class="header-left">
          <el-button class="collapse-btn" text circle @click="toggleCollapse">
            <el-icon>
              <Fold v-if="!isCollapsed" />
              <Expand v-else />
            </el-icon>
          </el-button>
          <h2 class="page-title">
            {{ currentPageTitle }}
          </h2>
        </div>
        <div class="header-right">
          <el-popover
            placement="bottom"
            width="360"
            trigger="click"
            v-model:visible="messagePopoverVisible"
          >
            <template #reference>
              <el-badge
                :value="unreadCount"
                :max="99"
                :hidden="unreadCount === 0"
                class="message-badge"
              >
                <el-button class="message-btn" text circle>
                  <el-icon>
                    <Bell />
                  </el-icon>
                </el-button>
              </el-badge>
            </template>
            <div class="message-list-container">
              <div class="message-list-header">
                <span class="message-list-title">消息通知</span>
                <div class="message-list-actions">
                  <el-button
                    v-if="unreadCount > 1"
                    class="message-mark-all-btn"
                    text
                    @click.stop="handleMarkAllRead"
                  >
                    一键已读
                  </el-button>
                  <el-button class="message-refresh-btn" text circle @click.stop="refreshMessages">
                    <el-icon>
                      <RefreshRight />
                    </el-icon>
                  </el-button>
                </div>
              </div>
              <div class="message-list-body">
                <el-tabs v-model="activeMessageTab" class="message-tabs" @tab-change="handleMessageTabChange">
                  <el-tab-pane label="通知" name="notification">
                    <div v-if="messageLoading" class="message-loading">
                      加载中...
                    </div>
                    <div
                      v-for="msg in messages"
                      :key="msg.id"
                      class="message-item"
                      :class="{ 'is-unread': !msg.is_read }"
                      @click="handleMessageClick(msg)"
                    >
                      <div class="message-title-row">
                        <span class="message-title">{{ msg.title }}</span>
                        <span v-if="!msg.is_read" class="unread-dot"></span>
                      </div>
                      <div class="message-summary">
                        {{ msg.summary || msg.content }}
                      </div>
                      <div class="message-meta">
                        {{ formatMessageTime(msg.create_datetime) }}
                      </div>
                    </div>
                    <div v-if="!messageLoading && messages.length === 0" class="message-empty">
                      暂无消息
                    </div>
                  </el-tab-pane>
                  <el-tab-pane label="点赞" name="like">
                    <div v-if="likeMessagesLoading" class="message-loading">
                      加载中...
                    </div>
                    <div
                      v-for="msg in likeMessages"
                      :key="msg.id"
                      class="message-item"
                      :class="{ 'is-unread': !msg.is_read }"
                      @click="handleMessageClick(msg)"
                    >
                      <div class="message-title-row">
                        <span class="message-title">{{ msg.title }}</span>
                        <span v-if="!msg.is_read" class="unread-dot"></span>
                      </div>
                      <div class="message-summary">
                        {{ msg.summary || msg.content }}
                      </div>
                      <div class="message-meta">
                        {{ formatMessageTime(msg.create_datetime) }}
                      </div>
                    </div>
                    <div v-if="!likeMessagesLoading && likeMessages.length === 0" class="message-empty">
                      暂无点赞消息
                    </div>
                  </el-tab-pane>
                  <el-tab-pane label="评论" name="comment">
                    <div v-if="commentMessagesLoading" class="message-loading">
                      加载中...
                    </div>
                    <div
                      v-for="msg in commentMessages"
                      :key="msg.id"
                      class="message-item"
                      :class="{ 'is-unread': !msg.is_read }"
                      @click="handleMessageClick(msg)"
                    >
                      <div class="message-title-row">
                        <span class="message-title">{{ msg.title }}</span>
                        <span v-if="!msg.is_read" class="unread-dot"></span>
                      </div>
                      <div class="message-summary">
                        {{ msg.summary || msg.content }}
                      </div>
                      <div class="message-meta">
                        {{ formatMessageTime(msg.create_datetime) }}
                      </div>
                    </div>
                    <div v-if="!commentMessagesLoading && commentMessages.length === 0" class="message-empty">
                      暂无评论消息
                    </div>
                  </el-tab-pane>
                </el-tabs>
              </div>
            </div>
          </el-popover>

          <el-dialog
            v-model="messageDialogVisible"
            :title="selectedMessage ? selectedMessage.title : ''"
            width="480px"
            destroy-on-close
          >
            <div class="message-dialog-content" v-if="selectedMessage">
              <div class="message-dialog-meta">
                <span>时间：{{ formatMessageTime(selectedMessage.create_datetime) }}</span>
              </div>
              <div class="message-dialog-body">
                {{ selectedMessage.content }}
              </div>
            </div>
            <template #footer>
              <div class="message-dialog-footer">
                <div class="message-dialog-footer-left">
                  <el-button
                    v-if="hasPrevMessage"
                    class="message-nav-btn"
                    plain
                    size="small"
                    @click="handleShowPrevMessage"
                  >
                    上一条
                  </el-button>
                </div>
                <div class="message-dialog-footer-right">
                  <el-button
                    v-if="hasNextMessage"
                    class="message-nav-btn"
                    plain
                    size="small"
                    @click="handleShowNextMessage"
                  >
                    下一条
                  </el-button>
                </div>
              </div>
            </template>
          </el-dialog>

          <el-dropdown @command="handleUserCommand">
            <span class="user-dropdown-trigger">
              <div class="user-avatar-wrapper">
                <el-avatar
                  :size="32"
                  :src="userAvatar"
                  class="user-avatar"
                >
                  <template #default>
                    <span class="avatar-placeholder-small">
                      {{ user && user.username ? user.username.charAt(0).toUpperCase() : 'U' }}
                    </span>
                  </template>
                </el-avatar>
                <span
                  class="user-status-dot"
                  :class="isOnline ? 'user-status-online' : 'user-status-offline'"
                ></span>
              </div>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="user-center">个人中心</el-dropdown-item>
                <el-dropdown-item command="my-data">我的数据</el-dropdown-item>
                <el-dropdown-item divided command="logout">登出</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <div class="content-wrapper">
        <router-view></router-view>
      </div>

      <el-drawer
        v-model="myDataVisible"
        title="我的数据"
        direction="rtl"
        size="420px"
        :with-header="true"
        destroy-on-close
      >
        <div class="my-data-panel">
          <div class="my-data-section">
            <h3 class="my-data-section-title">下载与收藏概览</h3>
            <div v-if="dashboardLoading" class="my-data-section-placeholder">
              正在加载下载和收藏数据...
            </div>
            <div
              v-else-if="dashboardStats"
              class="my-data-summary-grid"
            >
              <div class="my-data-summary-item">
                <div class="my-data-summary-label">知识库下载</div>
                <div class="my-data-summary-value">
                  {{ dashboardStats.knowledgeDownloads ?? 0 }}
                </div>
              </div>
              <div class="my-data-summary-item">
                <div class="my-data-summary-label">人设卡下载</div>
                <div class="my-data-summary-value">
                  {{ dashboardStats.personaDownloads ?? 0 }}
                </div>
              </div>
              <div class="my-data-summary-item">
                <div class="my-data-summary-label">知识库收藏</div>
                <div class="my-data-summary-value">
                  {{ dashboardStats.knowledgeStars ?? 0 }}
                </div>
              </div>
              <div class="my-data-summary-item">
                <div class="my-data-summary-label">人设卡收藏</div>
                <div class="my-data-summary-value">
                  {{ dashboardStats.personaStars ?? 0 }}
                </div>
              </div>
            </div>
            <div v-else class="my-data-section-placeholder">
              暂无下载和收藏数据
            </div>
          </div>

          <div class="my-data-section">
            <h3 class="my-data-section-title">最近30天趋势</h3>
            <div v-if="dashboardLoading" class="my-data-section-placeholder">
              正在加载趋势数据...
            </div>
            <div
              v-else-if="dashboardTrends && dashboardTrends.items && dashboardTrends.items.length"
              class="my-data-chart-wrapper"
            >
              <div ref="trendChartRef" class="my-data-chart"></div>
            </div>
            <div v-else class="my-data-section-placeholder">
              暂无趋势数据
            </div>
          </div>
        </div>
      </el-drawer>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, watch, nextTick } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter, useRoute } from 'vue-router'
import { UserFilled, Collection, Fold, Expand, Bell, RefreshRight, Check, StarFilled } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { handleApiError, showApiErrorNotification } from '@/utils/api'
import websocket from '@/utils/websocket'
import { useUserStore } from '@/stores/user'
import { useMessageStore } from '@/stores/messages'
import { useConnectionStore } from '@/stores/connection'
import { getMyDashboardStats, getMyDashboardTrends } from '@/api/stats'
import { apiBase } from '@/api/index'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const messageStore = useMessageStore()
const connectionStore = useConnectionStore()
const { user, isAdmin } = storeToRefs(userStore)
const { items: messages, unreadCount, byType, loading: messageLoading } = storeToRefs(messageStore)
const { isOnline } = storeToRefs(connectionStore)
let messagePollTimer = null
const isCollapsed = ref(false)

// 侧边栏自动折叠的窗口宽度阈值
const COLLAPSE_THRESHOLD = 768

const checkAutoCollapse = () => {
  isCollapsed.value = window.innerWidth < COLLAPSE_THRESHOLD
}

const messagePopoverVisible = ref(false)
const messageDialogVisible = ref(false)
const selectedMessage = ref(null)
const activeMessageTab = ref('notification')
const myDataVisible = ref(false)
const dashboardLoading = ref(false)
const dashboardStats = ref(null)
const dashboardTrends = ref(null)
const trendChartRef = ref(null)
let trendChartInstance = null

const userAvatar = computed(() => {
  return resolveAvatarUrl(user.value)
})

const currentMessageIndex = computed(() => {
  if (!selectedMessage.value) {
    return -1
  }
  return messages.value.findIndex((item) => item.id === selectedMessage.value.id)
})

const hasPrevMessage = computed(() => {
  return currentMessageIndex.value > 0
})

const hasNextMessage = computed(() => {
  return currentMessageIndex.value >= 0 && currentMessageIndex.value < messages.value.length - 1
})

const likeMessages = computed(() => byType.value.like.items || [])
const likeMessagesLoading = computed(() => byType.value.like.loading)
const commentMessages = computed(() => byType.value.comment.items || [])
const commentMessagesLoading = computed(() => byType.value.comment.loading)

const resolveAvatarUrl = (userData) => {
  if (!userData || !userData.id) {
    return ''
  }
  const base = apiBase || ''
  const trimmedBase = base.endsWith('/') ? base.slice(0, -1) : base
  let url = `${trimmedBase}/users/${userData.id}/avatar?size=64`
  if (userData.avatar_updated_at) {
    url += `&t=${encodeURIComponent(userData.avatar_updated_at)}`
  }
  return url
}

const pageTitleMap = {
  '/persona-card': '人设卡广场',
  '/my-persona': '我的人设卡',
  '/persona-upload': '创建人设卡',
  '/persona-review': '人设卡审核',
  '/knowledge-base': '知识库广场',
  '/my-knowledge': '我的知识库',
  '/knowledge-review': '知识库审核',
  '/favorite-persona': '收藏人设卡',
  '/favorite-knowledge': '收藏知识库',
  '/user-center': '个人中心',
  '/admin-dashboard': '运营看板',
  '/admin-users': '用户管理',
  '/admin-mute': '禁言管理'
}

const currentPageTitle = computed(() => {
  return pageTitleMap[route.path] || '麦麦笔记本'
})

const formatMessageTime = (value) => {
  if (!value) {
    return ''
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return ''
  }
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  const hh = String(date.getHours()).padStart(2, '0')
  const mm = String(date.getMinutes()).padStart(2, '0')
  return `${y}-${m}-${d} ${hh}:${mm}`
}

const refreshMessages = () => {
  messageStore.refreshMessages()
}

const startMessagePoll = () => {
  if (messagePollTimer) {
    return
  }
  messagePollTimer = setInterval(() => {
    messageStore.fetchMessages()
  }, 10000)
}

const stopMessagePoll = () => {
  if (!messagePollTimer) {
    return
  }
  clearInterval(messagePollTimer)
  messagePollTimer = null
}

const handleWebsocketMessage = () => {
  messageStore.refreshMessages()
}

const handleMarkAllRead = async () => {
  await messageStore.markAllRead()
}

const handleMessageTabChange = async (name) => {
  if (name === 'notification') {
    await messageStore.fetchMessages()
  } else {
    await messageStore.fetchMessagesByType(name)
  }
}

const getUserInfo = async () => {
  try {
    await userStore.fetchCurrentUser()
  } catch (error) {
    const errorMessage = handleApiError(error, '获取用户信息失败，请检查网络连接')
    console.error('获取用户信息错误:', errorMessage)
  }
}

const handleMessageClick = async (msg) => {
  if (!msg) {
    return
  }
  messagePopoverVisible.value = false
  selectedMessage.value = msg
  messageDialogVisible.value = true

  await messageStore.markRead(msg)
}

const showMessageAtIndex = async (index) => {
  if (index < 0 || index >= messages.value.length) {
    return
  }
  const msg = messages.value[index]
  if (!msg) {
    return
  }
  messagePopoverVisible.value = false
  selectedMessage.value = msg
  messageDialogVisible.value = true

  await messageStore.markRead(msg)
}

const handleShowPrevMessage = () => {
  if (!hasPrevMessage.value) {
    return
  }
  const targetIndex = currentMessageIndex.value - 1
  showMessageAtIndex(targetIndex)
}

const handleShowNextMessage = () => {
  if (!hasNextMessage.value) {
    return
  }
  const targetIndex = currentMessageIndex.value + 1
  showMessageAtIndex(targetIndex)
}

const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value
}

const handleUserCommand = (command) => {
  if (command === 'user-center') {
    router.push('/user-center')
  } else if (command === 'my-data') {
    myDataVisible.value = true
  } else if (command === 'logout') {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('rememberedLogin')
    window.location.href = '/login'
  }
}

onMounted(() => {
  checkAutoCollapse()
  window.addEventListener('resize', checkAutoCollapse)
  getUserInfo()
  messageStore.fetchMessages()
  websocket.subscribeStatus((status) => {
    connectionStore.setStatus(status)
    if (status === 'open' || status === 'message') {
      stopMessagePoll()
      messageStore.refreshMessages()
    } else if (status === 'closed' || status === 'error') {
      startMessagePoll()
    }
  })
  websocket.init(handleWebsocketMessage)
  startMessagePoll()
})

const initMyDataCharts = async () => {
  if (!myDataVisible.value) {
    return
  }
  dashboardLoading.value = true
  try {
    const [dashboardResp, trendResp] = await Promise.all([
      getMyDashboardStats(),
      getMyDashboardTrends({ days: 30 })
    ])

    if (dashboardResp && dashboardResp.success && dashboardResp.data) {
      dashboardStats.value = dashboardResp.data
    } else if (dashboardResp && dashboardResp.data) {
      dashboardStats.value = dashboardResp.data
    } else if (dashboardResp) {
      dashboardStats.value = dashboardResp
    }

    if (trendResp && trendResp.success && trendResp.data) {
      dashboardTrends.value = trendResp.data
    } else if (trendResp && trendResp.data) {
      dashboardTrends.value = trendResp.data
    } else if (trendResp) {
      dashboardTrends.value = trendResp
    }
  } catch (error) {
    showApiErrorNotification(error, '获取下载、收藏数据失败，请稍后重试')
    dashboardStats.value = null
    dashboardTrends.value = null
  } finally {
    dashboardLoading.value = false
  }
  await nextTick()
  initTrendChart()
}

const initTrendChart = () => {
  if (!trendChartRef.value || !dashboardTrends.value || !dashboardTrends.value.items) {
    return
  }

  const el = trendChartRef.value
  if (!trendChartInstance) {
    trendChartInstance = echarts.init(el)
  }

  const items = dashboardTrends.value.items || []
  const dates = items.map((item) => item.date)
  const knowledgeDownloads = items.map((item) => item.knowledgeDownloads ?? 0)
  const personaDownloads = items.map((item) => item.personaDownloads ?? 0)
  const knowledgeStars = items.map((item) => item.knowledgeStars ?? 0)
  const personaStars = items.map((item) => item.personaStars ?? 0)

  const option = {
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      data: ['知识库下载', '人设卡下载', '知识库收藏', '人设卡收藏']
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: dates
    },
    yAxis: {
      type: 'value',
      minInterval: 1
    },
    series: [
      {
        name: '知识库下载',
        type: 'line',
        smooth: true,
        data: knowledgeDownloads
      },
      {
        name: '人设卡下载',
        type: 'line',
        smooth: true,
        data: personaDownloads
      },
      {
        name: '知识库收藏',
        type: 'line',
        smooth: true,
        data: knowledgeStars
      },
      {
        name: '人设卡收藏',
        type: 'line',
        smooth: true,
        data: personaStars
      }
    ]
  }

  trendChartInstance.setOption(option, true)
}

onUnmounted(() => {
  window.removeEventListener('resize', checkAutoCollapse)
  stopMessagePoll()
  websocket.unsubscribeStatus()
  websocket.close()
})

watch(
  messagePopoverVisible,
  (visible) => {
    if (!visible) {
      return
    }
    if (activeMessageTab.value === 'notification') {
      if (messages.value.length === 0 && !messageStore.loading) {
        messageStore.fetchMessages()
      }
    } else if (activeMessageTab.value === 'like') {
      if (!byType.value.like.loaded && !byType.value.like.loading) {
        messageStore.fetchMessagesByType('like')
      }
    } else if (activeMessageTab.value === 'comment') {
      if (!byType.value.comment.loaded && !byType.value.comment.loading) {
        messageStore.fetchMessagesByType('comment')
      }
    }
  }
)

watch(
  myDataVisible,
  (visible) => {
    if (visible) {
      initMyDataCharts()
    } else if (trendChartInstance) {
      trendChartInstance.dispose()
      trendChartInstance = null
    }
  }
)
</script>

<style scoped>
.home-container {
  width: 100%;
  height: 100vh;
  background-color: var(--primary-color);
  display: flex;
}

.header-left {
  display: flex;
  align-items: center;
}

.logo-wrapper {
  display: flex;
  align-items: center;
  overflow: hidden;
}

.logo-img {
  width: 40px;
  height: 40px;
  border-radius: 5px;
  margin-right: 12px;
  object-fit: contain;
}

.product-info {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  max-width: 180px;
  transition: opacity 0.2s ease, max-width 0.2s ease, margin-left 0.2s ease;
}

.side-menu.collapsed .product-info {
  opacity: 0;
  max-width: 0;
  margin-left: 0;
}

.menu-wrapper :deep(.el-menu-item) {
  display: flex;
  align-items: center;
  transition: justify-content 0.2s ease;
}

.menu-label {
  margin-left: 8px;
  white-space: nowrap;
  max-width: 120px;
  overflow: hidden;
}

/* el-menu collapse 模式下自动隐藏文字并居中图标 */
.menu-wrapper.el-menu--collapse :deep(.el-sub-menu__title) {
  padding: 0 !important;
  justify-content: center;
}

.menu-wrapper.el-menu--collapse :deep(.el-menu-item) {
  padding: 0 !important;
  justify-content: center;
}

.product-info h1 {
  color: var(--secondary-color);
  font-size: 20px;
  margin: 0;
}

.slogan {
  font-size: 12px;
  color: var(--muted-text-color);
  margin: 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-avatar-wrapper {
  position: relative;
  display: inline-flex;
}

.user-avatar {
  cursor: pointer;
  width: 32px;
  height: 32px;
}

.user-dropdown-trigger {
  display: inline-flex;
  align-items: center;
}

.user-status-dot {
  position: absolute;
  right: -1px;
  bottom: -1px;
  width: 10px;
  height: 10px;
  border-radius: 9999px;
  border: 2px solid var(--card-background);
  box-sizing: border-box;
}

.user-status-online {
  background-color: #52c41a;
}

.user-status-offline {
  background-color: #bfbfbf;
}

.message-badge {
  display: inline-flex;
  align-items: center;
}

.message-btn {
  width: 36px;
  height: 36px;
  padding: 0;
  border-radius: 9999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.message-btn :deep(.el-icon) {
  font-size: 18px;
}

.message-list-container {
  padding: 4px 0 0;
}

.message-list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 8px 8px;
  border-bottom: 1px solid var(--border-color);
}

.message-list-title {
  font-size: 14px;
}

.message-list-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.message-mark-all-btn {
  font-size: 12px;
  padding: 0 6px;
}

.message-refresh-btn {
  width: 28px;
  height: 28px;
  padding: 0;
  border-radius: 9999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.message-refresh-btn :deep(.el-icon) {
  font-size: 16px;
}

.message-list-body {
  max-height: 360px;
  padding: 8px;
  overflow-y: auto;
}

.message-item {
  background-color: var(--card-background);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 8px 10px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: background-color 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
}

.message-item:last-child {
  margin-bottom: 0;
}

.message-item:hover {
  background-color: var(--hover-color);
  border-color: var(--secondary-color);
  box-shadow: 0 0 0 1px var(--secondary-color);
}

.message-item.is-unread {
  border-left: 3px solid var(--secondary-color);
}

.message-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}

.message-title {
  font-size: 14px;
  font-weight: 500;
  margin-right: 6px;
}

.unread-dot {
  width: 8px;
  height: 8px;
  border-radius: 9999px;
  background-color: var(--secondary-color);
}

.message-summary {
  font-size: 12px;
  color: var(--muted-text-color);
  margin-bottom: 4px;
  display: -webkit-box;
  line-clamp: 2;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.message-meta {
  font-size: 11px;
  color: var(--muted-text-color);
  text-align: right;
}

.message-loading,
.message-empty {
  padding: 12px 0;
  text-align: center;
  font-size: 12px;
  color: var(--muted-text-color);
}

.message-dialog-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.message-dialog-meta {
  font-size: 12px;
  color: var(--muted-text-color);
}

.message-dialog-body {
  font-size: 14px;
  line-height: 1.6;
  height: 260px;
  overflow-y: auto;
  white-space: pre-wrap;
}

.message-dialog-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 4px;
}

.message-nav-btn {
  min-width: 80px;
  padding: 4px 12px;
  font-size: 12px;
  border-radius: 9999px;
  background-color: transparent;
}

.side-menu {
  width: 220px;
  background-color: var(--primary-color);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  transition: width 0.2s ease;
}

.side-menu.collapsed {
  width: 64px;
}

.side-header {
  height: 60px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  box-sizing: border-box;
  border-bottom: 1px solid var(--border-color);
}

.side-menu.collapsed .side-header {
  justify-content: center;
  padding: 0;
}

.side-menu.collapsed .logo-img {
  margin-right: 0;
}

.menu-wrapper {
  flex: 1;
  border-right: none;
}

.main-layout {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.top-header {
  height: 60px;
  background-color: var(--card-background);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  box-sizing: border-box;
}

.collapse-btn {
  margin-right: 8px;
}

.page-title {
  margin: 0;
  font-size: 18px;
}

.content-wrapper {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  overflow-x: hidden;
  background-color: var(--primary-color);
}

.my-data-panel {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.my-data-summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.my-data-summary-item {
  background-color: var(--card-background);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 8px 10px;
}

.my-data-summary-label {
  font-size: 12px;
  color: var(--muted-text-color);
  margin-bottom: 4px;
}

.my-data-summary-value {
  font-size: 16px;
  font-weight: 600;
}

.my-data-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.my-data-section-title {
  margin: 0;
  font-size: 16px;
}

.my-data-chart-wrapper {
  width: 100%;
  height: 220px;
}

.my-data-chart {
  width: 100%;
  height: 100%;
}

.my-data-section-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 220px;
  font-size: 13px;
  color: var(--muted-text-color);
}

.avatar-placeholder-small {
  font-size: 14px;
  font-weight: bold;
  color: var(--el-text-color-primary);
}
</style>
