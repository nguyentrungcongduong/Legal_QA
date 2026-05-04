import { defineStore } from 'pinia'
import api from '@/plugins/api'

export const useHistoryStore = defineStore('history', {
  state: () => ({
    sessions: [],
    currentSessionId: localStorage.getItem('currentSessionId') || null,
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
      localStorage.setItem('currentSessionId', sessionId)
      this.messages = []  // clear ngay để ChatView hiện empty state trước khi load

      try {
        const res = await api.get(`/api/history/sessions/${sessionId}/messages`)
        // Normalize field names — Spring Boot có thể trả về snake_case hoặc camelCase
        this.messages = (res.data || []).map(m => ({
          role:      m.role,
          content:   m.content || m.message || '',
          citations: m.citations || [],
          createdAt: m.createdAt || m.created_at || new Date().toISOString(),
        }))
      } catch (e) {
        console.error('[HistoryStore] loadSession failed:', e)
        this.messages = []
      }
    },

    async createSession(firstQuery) {
      const title = firstQuery.length > 40
        ? firstQuery.substring(0, 40) + '...'
        : firstQuery

      const res = await api.post('/api/history/sessions', { title })
      this.sessions.unshift(res.data)
      this.currentSessionId = res.data.id
      localStorage.setItem('currentSessionId', res.data.id)
      this.messages = []
      return res.data
    },

    async deleteSession(sessionId) {
      await api.delete(`/api/history/sessions/${sessionId}`)
      this.sessions = this.sessions.filter(s => s.id !== sessionId)
      if (this.currentSessionId === sessionId) {
        this.currentSessionId = null
        localStorage.removeItem('currentSessionId')
        this.messages = []
      }
    },

    addMessage(message) {
      this.messages.push(message)
    },

    // Lưu message lên server — dùng axios trực tiếp với token từ localStorage
    // để tránh mọi race condition với Pinia/HMR interceptor
    async saveMessageToServer(sessionId, message) {
      const token = localStorage.getItem('token')
      if (!token || token === 'null' || token === 'undefined') {
        console.warn('[HistoryStore] saveMessage bỏ qua: không có token hợp lệ')
        return
      }
      try {
        await api.post(
          `/api/history/sessions/${sessionId}/messages`,
          {
            role:      message.role,
            content:   message.content,
            citations: message.citations || [],
          },
          {
            headers: { Authorization: `Bearer ${token}` }  // explicit — không qua interceptor
          }
        )
      } catch (e) {
        console.warn('[HistoryStore] saveMessage failed:', e.response?.status, e.message)
      }
    }
  }
})
