import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/authStore'
import ChatView from '@/views/ChatView.vue'
import LoginView from '@/views/LoginView.vue'
import RegisterView from '@/views/RegisterView.vue'
import CompareView from '@/views/CompareView.vue'
import EvaluationView from '@/views/EvaluationView.vue'
import AdminView from '@/views/AdminView.vue'

const routes = [
  { path: '/', redirect: '/chat' },
  { path: '/chat',     component: ChatView,       meta: { requiresAuth: true } },
  { path: '/login',    component: LoginView },
  { path: '/register', component: RegisterView },
  { path: '/compare',  component: CompareView,    meta: { requiresAuth: true } },
  { path: '/evaluate', component: EvaluationView, meta: { requiresAuth: true } },
  { path: '/admin',    component: AdminView,       meta: { requiresAuth: true, requiresAdmin: true } },
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return { path: '/login' }
  }

  if (to.meta.requiresAdmin && !authStore.isAdmin) {
    return { path: '/chat' }   // redirect user thường về chat
  }

  return true
})

export default router
