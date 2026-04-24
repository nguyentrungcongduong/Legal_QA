import { defineStore } from 'pinia'
import api from '@/plugins/api'

export const useHistoryStore = defineStore('history', {
  state: () => ({
    sessions: [],
    currentSessionId: null,
    messages: []
  }),

  getters: {
    currentSession: (state) =>
      state.sessions.find(s => s.id === state.currentSessionId)
  },

  actions: {
    async fetchSessions() {
      const res = await api.get('/api/history/sessions')
      this.sessions = res.data
    },

    async loadSession(sessionId) {
      this.currentSessionId = sessionId
      const res = await api.get(`/api/history/sessions/${sessionId}/messages`)
      this.messages = res.data
    },

    async createSession(firstQuery) {
      const title = firstQuery.length > 40
        ? firstQuery.substring(0, 40) + '...'
        : firstQuery

      const res = await api.post('/api/history/sessions', { title })
      this.sessions.unshift(res.data)
      this.currentSessionId = res.data.id
      this.messages = []
      return res.data
    },

    async deleteSession(sessionId) {
      await api.delete(`/api/history/sessions/${sessionId}`)
      this.sessions = this.sessions.filter(s => s.id !== sessionId)
      if (this.currentSessionId === sessionId) {
        this.currentSessionId = null
        this.messages = []
      }
    },

    addMessage(message) {
      this.messages.push(message)
    }
  }
})
