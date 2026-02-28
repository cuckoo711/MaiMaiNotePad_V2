import { defineStore } from 'pinia'

export const usePersonaStore = defineStore('persona', {
  state: () => ({
    currentPersona: null
  }),
  actions: {
    setCurrentPersona(card) {
      this.currentPersona = card || null
    },
    clearCurrentPersona() {
      this.currentPersona = null
    }
  }
})

