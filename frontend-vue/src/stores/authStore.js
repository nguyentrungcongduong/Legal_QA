import { defineStore } from 'pinia'
import axios from 'axios'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || null,
    user: JSON.parse(localStorage.getItem('user') || 'null')
  }),

  getters: {
    isAuthenticated: (state) => !!state.token
  },

  actions: {
    async login(email, password) {
      // Sửa URL API từ '/api/auth/login' thành API của bạn
      try {
        const res = await axios.post('/api/auth/login', { email, password })
        this.token = res.data.token
        this.user = { email: res.data.email, userId: res.data.userId }
        localStorage.setItem('token', this.token)
        localStorage.setItem('user', JSON.stringify(this.user))
        axios.defaults.headers.common['Authorization'] = `Bearer ${this.token}`
      } catch (e) {
        if (e.response && e.response.data && e.response.data.message) {
            throw new Error(e.response.data.message)
        }
        throw e
      }
    },

    async register(email, password) {
      try {
        const res = await axios.post('/api/auth/register', { email, password })
        this.token = res.data.token
        this.user = { email: res.data.email }
        localStorage.setItem('token', this.token)
        localStorage.setItem('user', JSON.stringify(this.user))
        axios.defaults.headers.common['Authorization'] = `Bearer ${this.token}`
      } catch (e) {
        if (e.response && e.response.data && e.response.data.message) {
            throw new Error(e.response.data.message)
        }
        throw e
      }
    },

    logout() {
      this.token = null
      this.user = null
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      delete axios.defaults.headers.common['Authorization']
    }
  }
})
