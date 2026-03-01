import { defineStore } from 'pinia'
import { getMessages, getMessagesByType, markMessageRead } from '@/api/messages'
import { handleApiError, showApiErrorNotification, showErrorNotification } from '@/utils/api'

export const useMessageStore = defineStore('messages', {
  state: () => ({
    items: [],
    loading: false,
    loaded: false,
    page: 1,
    pageSize: 20,
    hasMore: true,
    byType: {
      notification: {
        items: [],
        loading: false,
        loaded: false,
        page: 1,
        pageSize: 20,
        hasMore: true
      },
      like: {
        items: [],
        loading: false,
        loaded: false,
        page: 1,
        pageSize: 20,
        hasMore: true
      },
      comment: {
        items: [],
        loading: false,
        loaded: false,
        page: 1,
        pageSize: 20,
        hasMore: true
      }
    }
  }),
  getters: {
    unreadCount: (state) => state.items.filter((item) => !item.is_read).length
  },
  actions: {
    async fetchMessages(force = false) {
      if (this.loading) {
        return
      }
      if (this.loaded && !force && this.items.length) {
        return
      }
      this.loading = true
      try {
        // 强制刷新时重置分页
        if (force) {
          this.page = 1
          this.hasMore = true
        }
        const response = await getMessages(this.page, this.pageSize)
        if (response && response.success) {
          const rawData = response.data
          const newItems = Array.isArray(rawData) ? rawData : (rawData?.data || [])
          this.items = newItems
          this.loaded = true
          this.hasMore = newItems.length >= this.pageSize
        } else {
          showErrorNotification((response && response.msg) || '获取消息列表失败')
        }
      } catch (error) {
        showApiErrorNotification(error, '获取消息列表失败，请检查网络连接')
      } finally {
        this.loading = false
      }
    },
    async refreshMessages() {
      // 刷新时重置分页状态
      this.page = 1
      this.hasMore = true
      await this.fetchMessages(true)
      // 同时刷新各分类 tab 中已加载过的数据，确保消息列表实时更新
      const typeKeys = Object.keys(this.byType)
      const tasks = typeKeys
        .filter((key) => this.byType[key].loaded)
        .map((key) => {
          this.byType[key].page = 1
          this.byType[key].hasMore = true
          return this.fetchMessagesByType(key, true)
        })
      await Promise.all(tasks)
    },
    async fetchMessagesByType(type, force = false) {
      const key = type || 'notification'
      const bucket = this.byType[key]
      if (!bucket || bucket.loading) {
        return
      }
      if (bucket.loaded && !force && bucket.items.length) {
        return
      }
      bucket.loading = true
      try {
        // 强制刷新时重置分页
        if (force) {
          bucket.page = 1
          bucket.hasMore = true
        }
        // 映射前端 tab 名称到后端 message_type 编号
        // 0=系统通知, 1=评论, 2=回复, 3=点赞, 4=审核
        const typeMap = {
          notification: '0,4', // 系统通知 + 审核通知
          like: '3',           // 点赞
          comment: '1,2'       // 评论 + 回复
        }
        const messageType = typeMap[key] || '0'
        const response = await getMessagesByType(messageType, bucket.page, bucket.pageSize)
        if (response && response.success) {
          const rawData = response.data
          const newItems = Array.isArray(rawData) ? rawData : (rawData?.data || [])
          bucket.items = newItems
          bucket.loaded = true
          bucket.hasMore = newItems.length >= bucket.pageSize
        } else {
          showErrorNotification((response && response.msg) || '获取消息列表失败')
        }
      } catch (error) {
        showApiErrorNotification(error, '获取消息列表失败，请检查网络连接')
      } finally {
        bucket.loading = false
      }
    },
    async loadMoreByType(type) {
      /**
       * 滚动到底部时加载下一页消息
       */
      const key = type || 'notification'
      const bucket = this.byType[key]
      if (!bucket || bucket.loading || !bucket.hasMore) {
        return
      }
      bucket.loading = true
      try {
        const typeMap = {
          notification: '0,4',
          like: '3',
          comment: '1,2'
        }
        const messageType = typeMap[key] || '0'
        const nextPage = bucket.page + 1
        const response = await getMessagesByType(messageType, nextPage, bucket.pageSize)
        if (response && response.success) {
          const rawData = response.data
          const newItems = Array.isArray(rawData) ? rawData : (rawData?.data || [])
          if (newItems.length > 0) {
            bucket.items.push(...newItems)
            bucket.page = nextPage
          }
          bucket.hasMore = newItems.length >= bucket.pageSize
        }
      } catch (error) {
        showApiErrorNotification(error, '加载更多消息失败')
      } finally {
        bucket.loading = false
      }
    },
    async markAllRead() {
      const unreadMessages = this.items.filter((item) => !item.is_read)
      if (!unreadMessages.length) {
        return
      }
      try {
        const tasks = unreadMessages.map((msg) =>
          markMessageRead(msg.id).then((response) => {
            if (response && response.success) {
              msg.is_read = true
            }
          })
        )
        await Promise.all(tasks)
        // 同步更新各分类 tab 中对应消息的已读状态
        const readIds = new Set(unreadMessages.filter((m) => m.is_read).map((m) => m.id))
        for (const bucket of Object.values(this.byType)) {
          for (const item of bucket.items) {
            if (readIds.has(item.id)) {
              item.is_read = true
            }
          }
        }
      } catch (error) {
        showApiErrorNotification(error, '一键标记已读失败，请检查网络连接')
      }
    },
    async markRead(message) {
      if (!message || !message.id) {
        return
      }
      if (message.is_read) {
        return
      }
      try {
        const response = await markMessageRead(message.id)
        if (response && response.success) {
          message.is_read = true
        } else if (response && response.message) {
          showErrorNotification(response.message)
        }
      } catch (error) {
        showApiErrorNotification(error, '标记消息已读失败，请检查网络连接')
      }
    }
  }
})
