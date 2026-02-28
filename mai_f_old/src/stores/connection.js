import { defineStore } from 'pinia'

export const useConnectionStore = defineStore('connection', {
  state: () => ({
    status: 'closed'
  }),
  getters: {
    isOnline: (state) => state.status === 'open' || state.status === 'message'
  },
  actions: {
    setStatus(status) {
      this.status = status
    }
  }
})

