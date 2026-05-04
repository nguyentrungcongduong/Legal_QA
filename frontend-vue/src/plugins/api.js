import axios from 'axios'
import { useAuthStore } from '@/stores/authStore'

// Axios instance dùng chung cho toàn app — tự động đính JWT token
const api = axios.create()

// Interceptor: thêm Authorization header trước mỗi request
api.interceptors.request.use((config) => {
  const authStore = useAuthStore()
  const storeToken  = authStore.token
  const lsToken     = localStorage.getItem('token')
  const token       = storeToken || lsToken

  // DEBUG: log token source và prefix để phát hiện "null"/"undefined" string
  if (config.url?.includes('/api/history/sessions') && config.url?.includes('/messages')) {
    console.log(`[REQ] saveMessage → storeToken: ${storeToken ? storeToken.substring(0,20)+'...' : storeToken} | lsToken: ${lsToken ? lsToken.substring(0,20)+'...' : lsToken}`)
  }

  if (token && token !== 'null' && token !== 'undefined') {
    config.headers['Authorization'] = `Bearer ${token}`
  } else if (token) {
    console.error(`[REQ] Token là string rác: "${token}" — bỏ qua!`)
  }
  return config
})

// Interceptor: chỉ logout khi CHÍNH Spring Boot từ chối token (không phải lỗi từ FastAPI downstream)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    const url = error.config?.url || ''

    // DEBUG: log mọi lỗi để trace nguyên nhân logout
    if (status === 401 || status === 403) {
      console.error(`[API] ${status} on: ${url}`, error.response?.data)
    }

    // Chỉ logout khi ĐÚNG /api/auth/login hoặc /api/auth/register bị 401
    // (tức là token thực sự bị từ chối khi đăng nhập/đăng ký)
    // KHÔNG logout vì bất kỳ endpoint nào khác — kể cả /api/history/ hay /api/ai/
    const isLoginOrRegister = url.includes('/api/auth/login') || url.includes('/api/auth/register')

    if ((status === 401 || status === 403) && isLoginOrRegister) {
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
