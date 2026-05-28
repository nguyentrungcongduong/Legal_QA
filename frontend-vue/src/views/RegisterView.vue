<template>
  <div class="login-page">
    <div class="login-card">

      <div class="login-header">
        <p class="login-tagline">HỆ THỐNG TRA CỨU PHÁP LUẬT</p>
        <h1 class="login-title">Legal AI</h1>
        <p class="login-subtitle">Đăng Ký Tài Khoản</p>
      </div>

      <form class="login-form" @submit.prevent="handleRegister">
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
          <div class="password-wrap">
            <input
              v-model="password"
              :type="showPassword ? 'text' : 'password'"
              class="field-input"
              placeholder="••••••••"
            />
            <button type="button" class="eye-btn" @click="showPassword = !showPassword" :title="showPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'">
              <!-- Eye open -->
              <svg v-if="!showPassword" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                <circle cx="12" cy="12" r="3"/>
              </svg>
              <!-- Eye off -->
              <svg v-else xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
                <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
                <line x1="1" y1="1" x2="23" y2="23"/>
              </svg>
            </button>
          </div>
        </div>

        <div class="field">
          <label class="field-label">XÁC NHẬN MẬT KHẨU</label>
          <div class="password-wrap">
            <input
              v-model="confirmPassword"
              :type="showConfirm ? 'text' : 'password'"
              class="field-input"
              placeholder="••••••••"
            />
            <button type="button" class="eye-btn" @click="showConfirm = !showConfirm" :title="showConfirm ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'">
              <svg v-if="!showConfirm" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                <circle cx="12" cy="12" r="3"/>
              </svg>
              <svg v-else xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
                <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
                <line x1="1" y1="1" x2="23" y2="23"/>
              </svg>
            </button>
          </div>
        </div>

        <p v-if="error" class="error-msg">{{ error }}</p>

        <button
          type="submit"
          class="login-btn"
          :disabled="loading"
        >
          {{ loading ? 'ĐANG XỬ LÝ...' : 'ĐĂNG KÝ' }}
        </button>

        <p class="register-link">
          Đã có tài khoản?
          <span @click="$router.push('/login')">Đăng nhập ngay</span>
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
const confirmPassword = ref('')
const error = ref('')
const loading = ref(false)
const showPassword = ref(false)
const showConfirm = ref(false)

async function handleRegister() {
  error.value = ''
  
  if (password.value !== confirmPassword.value) {
    error.value = "Mật khẩu xác nhận không khớp";
    return;
  }
  
  loading.value = true

  try {
    await authStore.register(email.value, password.value)
    router.push('/chat')
  } catch (e) {
    error.value = e.message || 'Đăng ký thất bại'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Playfair+Display:wght@700&display=swap');

.login-page {
  min-height: 100vh;
  background: #FAFAF8;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'Inter', sans-serif;
}

.login-card {
  width: 440px;
  background: #FFFFFF;
  border: 1px solid #B8860B;
  padding: 52px 44px 44px;
  border-radius: 2px;
}

/* ── Header ── */
.login-tagline {
  font-family: 'Inter', sans-serif;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: #B8860B;
  margin: 0 0 16px;
}

.login-title {
  font-family: 'Playfair Display', serif;
  font-size: 38px;
  font-weight: 700;
  color: #111;
  margin: 0 0 6px;
  line-height: 1.1;
}

.login-subtitle {
  font-family: 'Inter', sans-serif;
  font-size: 13px;
  font-weight: 400;
  color: #888;
  letter-spacing: 0.03em;
  margin: 0 0 40px;
}

/* ── Form fields ── */
.field { margin-bottom: 28px; }

.field-label {
  display: block;
  font-family: 'Inter', sans-serif;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #444;
  margin-bottom: 10px;
}

.field-input {
  width: 100%;
  padding: 11px 0;
  border: none;
  border-bottom: 1.5px solid #DDD;
  background: transparent;
  font-family: 'Inter', sans-serif;
  font-size: 15px;
  font-weight: 400;
  color: #111;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.2s;
}

.field-input::placeholder {
  color: #BBB;
  font-weight: 400;
}

.field-input:focus {
  border-bottom-color: #B8860B;
}

.password-wrap {
  position: relative;
  display: flex;
  align-items: center;
}

.password-wrap .field-input {
  padding-right: 36px;
}

.eye-btn {
  position: absolute;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 4px;
  color: #BBB;
  display: flex;
  align-items: center;
  transition: color 0.15s;
}

.eye-btn:hover { color: #B8860B; }

.eye-btn svg {
  width: 18px;
  height: 18px;
}

/* ── Error ── */
.error-msg {
  font-family: 'Inter', sans-serif;
  font-size: 13px;
  font-weight: 500;
  color: #c0392b;
  margin: -10px 0 16px;
  letter-spacing: 0.01em;
}

/* ── Button ── */
.login-btn {
  width: 100%;
  padding: 15px;
  background: #111;
  color: #FAFAF8;
  border: none;
  font-family: 'Inter', sans-serif;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  cursor: pointer;
  margin-top: 12px;
  border-radius: 2px;
  transition: background 0.2s, transform 0.1s;
}

.login-btn:hover:not(:disabled) {
  background: #B8860B;
  transform: translateY(-1px);
}
.login-btn:active:not(:disabled) { transform: translateY(0); }
.login-btn:disabled { opacity: 0.55; cursor: not-allowed; }

/* ── Login link ── */
.register-link {
  text-align: center;
  font-family: 'Inter', sans-serif;
  font-size: 13px;
  font-weight: 400;
  color: #777;
  margin-top: 24px;
}

.register-link span {
  color: #B8860B;
  font-weight: 600;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 3px;
  transition: opacity 0.2s;
}
.register-link span:hover { opacity: 0.75; }
</style>
