import { defineStore } from 'pinia'
import api from '@/plugins/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || null,
    user: JSON.parse(localStorage.getItem('user') || 'null')
  }),

  getters: {
    isAuthenticated: (state) => !!state.token,
    isAdmin: (state) => state.user?.role === 'admin'
  },

  actions: {
    async login(email, password) {
      try {
        const res = await api.post('/api/auth/login', { email, password })
        this.token = res.data.token
        this.user = { email: res.data.email, userId: res.data.userId, role: res.data.role || 'user' }
        localStorage.setItem('token', this.token)
        localStorage.setItem('user', JSON.stringify(this.user))
        api.defaults.headers.common['Authorization'] = `Bearer ${this.token}`
      } catch (e) {
        if (e.response && e.response.data && e.response.data.message) {
            throw new Error(e.response.data.message)
        }
        // Network Error (không kết nối được server)
        if (!e.response) {
          throw new Error('Lỗi kết nối: Không thể kết nối đến server. Vui lòng kiểm tra backend đang chạy.')
        }
        throw e
      }
    },

    async register(email, password) {
      try {
        const res = await api.post('/api/auth/register', { email, password })
        this.token = res.data.token
        this.user = { email: res.data.email, role: res.data.role || 'user' }
        localStorage.setItem('token', this.token)
        localStorage.setItem('user', JSON.stringify(this.user))
        api.defaults.headers.common['Authorization'] = `Bearer ${this.token}`
      } catch (e) {
        if (e.response && e.response.data && e.response.data.message) {
            throw new Error(e.response.data.message)
        }
        if (!e.response) {
          throw new Error('Lỗi kết nối: Không thể kết nối đến server. Vui lòng kiểm tra backend đang chạy.')
        }
        throw e
      }
    },

    logout() {
      this.token = null
      this.user = null
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      localStorage.removeItem('ragas_job_id')
      localStorage.removeItem('ragas_total')
      delete api.defaults.headers.common['Authorization']
    }
  }
})
