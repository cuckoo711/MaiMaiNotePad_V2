import { defineStore } from 'pinia'
import { getCurrentUser } from '@/api/user'

export const useUserStore = defineStore('user', {
  state: () => ({
    user: null,
    role: 'user',
    loading: false,
    loaded: false
  }),
  getters: {
    isAdmin: (state) => {
      const user = state.user || {}
      return !!user.is_admin
    }
  },
  actions: {
    async fetchCurrentUser(force = false) {
      if (this.loading) {
        return this.user
      }
      if (this.loaded && !force && this.user) {
        return this.user
      }
      this.loading = true
      try {
        const response = await getCurrentUser()
        let data = null
        if (response && response.success && response.data) {
          data = response.data
        } else if (response && response.data) {
          data = response.data
        } else if (response) {
          data = response
        }
        if (!data) {
          this.user = null
          this.role = 'user'
          this.loaded = false
          return null
        }
        this.user = data
        this.role = data.role || 'user'
        this.loaded = true
        return this.user
      } catch (error) {
        this.user = null
        this.role = 'user'
        this.loaded = false
        throw error
      } finally {
        this.loading = false
      }
    },
    clearUser() {
      this.user = null
      this.role = 'user'
      this.loading = false
      this.loaded = false
    }
  }
})
