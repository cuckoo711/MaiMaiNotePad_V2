import { defineStore } from 'pinia'

export const useKnowledgeStore = defineStore('knowledge', {
  state: () => ({
    currentKB: null
  }),
  actions: {
    setCurrentKB(kb) {
      this.currentKB = kb || null
    },
    clearCurrentKB() {
      this.currentKB = null
    }
  }
})

