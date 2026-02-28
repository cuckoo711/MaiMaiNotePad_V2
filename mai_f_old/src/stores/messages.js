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
    byType: {
      notification: {
        items: [],
        loading: false,
        loaded: false,
        page: 1,
        pageSize: 20
      },
      like: {
        items: [],
        loading: false,
        loaded: false,
        page: 1,
        pageSize: 20
      },
      comment: {
        items: [],
        loading: false,
        loaded: false,
        page: 1,
        pageSize: 20
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
        const response = await getMessages(this.page, this.pageSize)
        if (response && response.success) {
          const rawData = response.data
          // 后端分页返回 data 可能是数组或 { data: [...], total: ... }
          this.items = Array.isArray(rawData) ? rawData : (rawData?.data || [])
          this.loaded = true
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
      await this.fetchMessages(true)
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
        const response = await getMessagesByType(key === 'notification' ? 'direct' : key === 'like' ? 'reaction' : 'comment', bucket.page, bucket.pageSize)
        if (response && response.success) {
          const rawData = response.data
          bucket.items = Array.isArray(rawData) ? rawData : (rawData?.data || [])
          bucket.loaded = true
        } else {
          showErrorNotification((response && response.msg) || '获取消息列表失败')
        }
      } catch (error) {
        showApiErrorNotification(error, '获取消息列表失败，请检查网络连接')
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
