<template>
  <div class="login-shell">
    <div class="login-card">
      <div class="brand-group">
        <h1 class="brand-title">Legal AI</h1>
        <p class="brand-subtitle">VERIFIED LAW SOURCE</p>
      </div>

      <form class="login-form" @submit.prevent="handleLogin">
        <div class="input-group">
          <label class="input-label" for="email">EMAIL</label>
          <input 
            type="email" 
            id="email" 
            v-model="email" 
            class="input-field" 
            placeholder="luatsu@example.com"
            required
          />
        </div>

        <div class="input-group">
          <label class="input-label" for="password">MẬT KHẨU</label>
          <input 
            type="password" 
            id="password" 
            v-model="password" 
            class="input-field" 
            placeholder="••••••••"
            required
          />
        </div>

        <button type="submit" class="submit-btn" :disabled="loading">
          {{ loading ? 'ĐANG XÁC THỰC...' : 'TRUY CẬP' }}
        </button>
      </form>
      
      <div class="footer-note">
        System secured for legal professionals
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const emit = defineEmits(['login-success']);

const email = ref('');
const password = ref('');
const loading = ref(false);

async function handleLogin() {
  loading.value = true;
  // TODO: Tích hợp gọi API Spring Boot ở đây
  // const response = await fetch('http://localhost:8082/login', { ... })
  
  // Giả lập delay mạng để thấy hiệu ứng loading
  setTimeout(() => {
    loading.value = false;
    emit('login-success', { token: 'dummy_token_abc' });
  }, 1000);
}
</script>

<style scoped>
.login-shell {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #FAFAF8; /* Ivory background */
  font-family: "Source Sans 3", Georgia, serif;
}

.login-card {
  background: #ffffff;
  padding: 50px 60px;
  width: 100%;
  max-width: 440px;
  border: 1px solid #B8860B; /* Vàng mảnh */
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.03);
  text-align: center;
}

.brand-group {
  margin-bottom: 45px;
}

.brand-title {
  margin: 0;
  font-family: "Playfair Display", Georgia, serif;
  font-size: 32px;
  font-weight: 700;
  font-style: italic;
  color: #1a1a1a;
  letter-spacing: -0.02em;
}

.brand-subtitle {
  margin: 8px 0 0;
  font-size: 10px;
  letter-spacing: 0.25em;
  color: #B8860B; /* Viền vàng / chữ vàng */
  text-transform: uppercase;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 24px;
  text-align: left;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.input-label {
  font-size: 11px;
  font-weight: 700;
  color: #1a1a1a;
  font-variant: small-caps;
  letter-spacing: 0.1em;
}

.input-field {
  padding: 14px 16px;
  border: 1px solid #e8e4df;
  background: #fafaf8;
  border-radius: 0; /* Vuông vức sang trọng */
  font-family: inherit;
  font-size: 15px;
  transition: all 0.2s ease;
}

.input-field:focus {
  outline: none;
  background: #ffffff;
  border-color: #B8860B;
  box-shadow: 0 0 0 1px #B8860B;
}

.input-field::placeholder {
  color: #b3b3b3;
  font-style: italic;
}

.submit-btn {
  margin-top: 10px;
  background: #1a1a1a; /* Đen tuyền */
  color: #ffffff;
  border: none;
  padding: 16px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.submit-btn:hover:not(:disabled) {
  background: #333333;
}

.submit-btn:disabled {
  background: #666666;
  cursor: not-allowed;
}

.footer-note {
  margin-top: 40px;
  font-size: 11px;
  color: #999999;
  font-style: italic;
  letter-spacing: 0.05em;
}
</style>
