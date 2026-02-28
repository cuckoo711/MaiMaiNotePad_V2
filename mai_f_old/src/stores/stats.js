import { defineStore } from 'pinia'
import { getMyUploadStats, getAdminUploadStats } from '@/api/stats'
import { getAdminStats } from '@/api/admin'
import { handleApiError, showApiErrorNotification, showErrorNotification } from '@/utils/api'

export const useStatsStore = defineStore('stats', {
  state: () => ({
    myStats: null,
    myStatsLoaded: false,
    myStatsLoading: false,
    adminStats: null,
    adminStatsLoaded: false,
    adminStatsLoading: false,
    adminUploadStats: null,
    adminUploadStatsLoaded: false,
    adminUploadStatsLoading: false
  }),
  actions: {
    async fetchMyStats(force = false) {
      if (this.myStatsLoading) {
        return
      }
      if (this.myStatsLoaded && !force && this.myStats) {
        return
      }
      this.myStatsLoading = true
      try {
        const response = await getMyUploadStats()
        if (response && response.success && response.data) {
          this.myStats = response.data
          this.myStatsLoaded = true
        } else if (response && response.data) {
          this.myStats = response.data
          this.myStatsLoaded = true
        } else {
          showErrorNotification((response && response.message) || '获取上传统计失败')
        }
      } catch (error) {
        showApiErrorNotification(error, '获取上传统计失败，请检查网络连接')
      } finally {
        this.myStatsLoading = false
      }
    },
    async fetchAdminStats(force = false) {
      if (this.adminStatsLoading) {
        return
      }
      if (this.adminStatsLoaded && !force && this.adminStats) {
        return
      }
      this.adminStatsLoading = true
      try {
        const response = await getAdminStats()
        if (response && response.success && response.data) {
          this.adminStats = response.data
          this.adminStatsLoaded = true
        } else if (response && response.data) {
          this.adminStats = response.data
          this.adminStatsLoaded = true
        } else if (response) {
          this.adminStats = response
          this.adminStatsLoaded = true
        } else {
          showErrorNotification((response && response.message) || '获取系统统计失败')
        }
      } catch (error) {
        showApiErrorNotification(error, '获取系统统计失败，请检查网络连接')
      } finally {
        this.adminStatsLoading = false
      }
    },
    async fetchAdminUploadStats(force = false) {
      if (this.adminUploadStatsLoading) {
        return
      }
      if (this.adminUploadStatsLoaded && !force && this.adminUploadStats) {
        return
      }
      this.adminUploadStatsLoading = true
      try {
        const response = await getAdminUploadStats()
        if (response && response.success && response.data) {
          this.adminUploadStats = response.data
          this.adminUploadStatsLoaded = true
        } else if (response && response.data) {
          this.adminUploadStats = response.data
          this.adminUploadStatsLoaded = true
        } else if (response) {
          this.adminUploadStats = response
          this.adminUploadStatsLoaded = true
        } else {
          showErrorNotification((response && response.message) || '获取上传统计失败')
        }
      } catch (error) {
        showApiErrorNotification(error, '获取上传统计失败，请检查网络连接')
      } finally {
        this.adminUploadStatsLoading = false
      }
    }
  }
})
