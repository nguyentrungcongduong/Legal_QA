import axios from 'axios'
import { useAuthStore } from '@/stores/authStore'

// Axios instance dùng chung cho toàn app — tự động đính JWT token
const api = axios.create()

// Interceptor: thêm Authorization header trước mỗi request
api.interceptors.request.use((config) => {
  const authStore = useAuthStore()
  const token = authStore.token || localStorage.getItem('token')
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})

// Interceptor: chỉ logout khi CHÍNH Spring Boot từ chối token (không phải lỗi từ FastAPI downstream)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    const url = error.config?.url || ''

    // Chỉ logout khi các API auth/history bị 401/403
    // KHÔNG logout khi /api/ai/* bị lỗi — có thể do FastAPI chưa chạy
    const isAuthEndpoint = url.includes('/api/auth/') || url.includes('/api/history/')
    const isAiEndpoint = url.includes('/api/ai/')

    if ((status === 401 || status === 403) && isAuthEndpoint) {
      const authStore = useAuthStore()
      if (authStore.token) {
        authStore.logout()
        window.location.href = '/login'
      }
    }

    return Promise.reject(error)
  }
)

export default api
