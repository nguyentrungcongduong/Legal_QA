<template>
  <div class="login-page">
    <div class="login-card">

      <div class="login-header">
        <p class="login-tagline">HỆ THỐNG TRA CỨU PHÁP LUẬT</p>
        <h1 class="login-title">Legal AI</h1>
        <p class="login-subtitle">Verified Law Source</p>
      </div>

      <form class="login-form" @submit.prevent="handleLogin">
        <div class="field">
          <label class="field-label">EMAIL</label>
          <input
            v-model="email"
            type="email"
            class="field-input"
            placeholder="example@law.vn"
          />
        </div>

        <div class="field">
          <label class="field-label">MẬT KHẨU</label>
          <input
            v-model="password"
            type="password"
            class="field-input"
            placeholder="••••••••"
          />
        </div>

        <p v-if="error" class="error-msg">{{ error }}</p>

        <button
          type="submit"
          class="login-btn"
          :disabled="loading"
        >
          {{ loading ? 'ĐANG XỬ LÝ...' : 'TRUY CẬP' }}
        </button>

        <p class="register-link">
          Chưa có tài khoản?
          <span @click="$router.push('/register')">Đăng ký</span>
        </p>
      </form>

    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/authStore'

const router = useRouter()
const authStore = useAuthStore()

const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  error.value = ''
  loading.value = true

  try {
    await authStore.login(email.value, password.value)
    router.push('/chat')
  } catch (e) {
    error.value = e.message || 'Đăng nhập thất bại'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  background: #FAFAF8;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'IBM Plex Mono', monospace;
}

.login-card {
  width: 420px;
  background: #FFFFFF;
  border: 1px solid #B8860B;
  padding: 48px 40px;
}

.login-tagline {
  font-size: 10px;
  letter-spacing: 0.2em;
  color: #B8860B;
  margin: 0 0 12px;
}

.login-title {
  font-family: 'Playfair Display', serif;
  font-size: 36px;
  color: #1a1a1a;
  margin: 0 0 4px;
  font-weight: 700;
}

.login-subtitle {
  font-size: 11px;
  color: #888;
  letter-spacing: 0.1em;
  margin: 0 0 40px;
}

.field { margin-bottom: 24px; }

.field-label {
  display: block;
  font-size: 10px;
  letter-spacing: 0.15em;
  color: #666;
  margin-bottom: 8px;
}

.field-input {
  width: 100%;
  padding: 12px 0;
  border: none;
  border-bottom: 1px solid #ddd;
  background: transparent;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 14px;
  color: #1a1a1a;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.2s;
}

.field-input:focus { border-bottom-color: #B8860B; }

.error-msg {
  font-size: 12px;
  color: #c0392b;
  margin: -8px 0 16px;
}

.login-btn {
  width: 100%;
  padding: 14px;
  background: #1a1a1a;
  color: #FAFAF8;
  border: none;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 12px;
  letter-spacing: 0.2em;
  cursor: pointer;
  margin-top: 16px;
  transition: background 0.2s;
}

.login-btn:hover:not(:disabled) { background: #B8860B; }
.login-btn:disabled { opacity: 0.6; cursor: not-allowed; }

.register-link {
  text-align: center;
  font-size: 12px;
  color: #888;
  margin-top: 24px;
}

.register-link span {
  color: #B8860B;
  cursor: pointer;
  text-decoration: underline;
}
</style>
