<template>
  <!-- Portal: fixed bottom-right, above everything -->
  <Teleport to="body">
    <div class="legal-toast-portal" aria-live="polite" aria-atomic="false">
      <TransitionGroup name="toast" tag="div" class="toast-stack">
        <div
          v-for="toast in toastStore.toasts"
          :key="toast.id"
          class="toast-item"
          :class="`toast--${toast.type}`"
          role="alert"
          @click="toastStore.dismiss(toast.id)"
        >
          <!-- Left accent bar (colored per type) -->
          <div class="toast-accent" />

          <!-- Icon -->
          <div class="toast-icon" :class="`icon--${toast.type}`">
            <!-- Success: checkmark -->
            <svg v-if="toast.type === 'success'" viewBox="0 0 16 16" fill="currentColor">
              <path d="M13.485 1.929a.75.75 0 0 1 .086 1.058l-7 8a.75.75 0 0 1-1.1.042l-3.5-3.5a.75.75 0 1 1 1.06-1.06l2.93 2.93 6.467-7.386a.75.75 0 0 1 1.057-.084z"/>
            </svg>
            <!-- Error: X -->
            <svg v-else-if="toast.type === 'error'" viewBox="0 0 16 16" fill="currentColor">
              <path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708z"/>
            </svg>
            <!-- Warning: ! -->
            <svg v-else-if="toast.type === 'warning'" viewBox="0 0 16 16" fill="currentColor">
              <path d="M8 1a.5.5 0 0 1 .5.5v5a.5.5 0 0 1-1 0v-5A.5.5 0 0 1 8 1zm0 9a1 1 0 1 1 0 2 1 1 0 0 1 0-2z"/>
            </svg>
            <!-- Legal: scales of justice -->
            <svg v-else-if="toast.type === 'legal'" viewBox="0 0 16 16" fill="currentColor">
              <path d="M2 2.5A.5.5 0 0 1 2.5 2h11a.5.5 0 0 1 0 1h-11A.5.5 0 0 1 2 2.5zm0 2A.5.5 0 0 1 2.5 4h7a.5.5 0 0 1 0 1h-7A.5.5 0 0 1 2 4.5zm0 2A.5.5 0 0 1 2.5 6h5a.5.5 0 0 1 0 1h-5A.5.5 0 0 1 2 6.5zm0 2A.5.5 0 0 1 2.5 8h3a.5.5 0 0 1 0 1h-3A.5.5 0 0 1 2 8.5zm10 4a.5.5 0 0 0 1 0V3.5a.5.5 0 0 0-1 0v9z"/>
            </svg>
            <!-- Info: i -->
            <svg v-else viewBox="0 0 16 16" fill="currentColor">
              <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
              <path d="m8.93 6.588-2.29.287-.082.38.45.083c.294.07.352.176.288.469l-.738 3.468c-.194.897.105 1.319.808 1.319.545 0 1.178-.252 1.465-.598l.088-.416c-.2.176-.492.246-.686.246-.275 0-.375-.193-.304-.533L8.93 6.588zM9 4.5a1 1 0 1 1-2 0 1 1 0 0 1 2 0z"/>
            </svg>
          </div>

          <!-- Content -->
          <div class="toast-content">
            <p class="toast-label">{{ toast.label || labelFor(toast.type) }}</p>
            <p class="toast-message">{{ toast.message }}</p>
          </div>

          <!-- Dismiss button -->
          <button class="toast-close" @click.stop="toastStore.dismiss(toast.id)" aria-label="Đóng">
            <svg viewBox="0 0 10 10" fill="currentColor" width="8" height="8">
              <path d="M1 1l8 8M9 1l-8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup>
import { useToastStore } from '@/composables/useToast'

const toastStore = useToastStore()

function labelFor(type) {
  const map = {
    success: 'Thao tác thành công',
    error:   'Lỗi hệ thống',
    warning: 'Cảnh báo pháp lý',
    info:    'Thông báo hệ thống',
    legal:   'Văn bản pháp lý',
  }
  return map[type] ?? 'Thông báo'
}
</script>

<style scoped>
/* ─── Portal Container ───────────────────────────────────────── */
.legal-toast-portal {
  position: fixed;
  bottom: 2rem;
  right: 2rem;
  z-index: 99999;
  pointer-events: none;
}

.toast-stack {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
  align-items: flex-end;
}

/* ─── Toast Card ─────────────────────────────────────────────── */
.toast-item {
  pointer-events: all;
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  min-width: 320px;
  max-width: 440px;
  background: #FAFAF8;
  border: 1px solid #E8E2D9;
  box-shadow:
    0 1px 3px rgba(26,20,10,0.08),
    0 8px 24px rgba(26,20,10,0.10);
  padding: 0.875rem 1rem 0.875rem 0;
  cursor: pointer;
  overflow: hidden;
  /* Editorial: NO border-radius — sharp, document-like */
  border-radius: 0;
}

/* ─── Left Accent Bar ────────────────────────────────────────── */
.toast-accent {
  flex-shrink: 0;
  width: 3px;
  align-self: stretch;
  margin-right: 0.5rem;
}

.toast--success .toast-accent { background: #2D6A4F; }
.toast--error   .toast-accent { background: #8B1A1A; }
.toast--warning .toast-accent { background: #B8860B; }
.toast--info    .toast-accent { background: #2C3E6B; }
.toast--legal   .toast-accent { background: #B8860B; }

/* ─── Icon ───────────────────────────────────────────────────── */
.toast-icon {
  flex-shrink: 0;
  width: 16px;
  height: 16px;
  margin-top: 2px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.icon--success { color: #2D6A4F; }
.icon--error   { color: #8B1A1A; }
.icon--warning { color: #B8860B; }
.icon--info    { color: #2C3E6B; }
.icon--legal   { color: #B8860B; }

/* ─── Text ───────────────────────────────────────────────────── */
.toast-content { flex: 1; min-width: 0; }

.toast-label {
  font-family: 'Courier New', Courier, monospace;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  margin: 0 0 0.25rem 0;
  line-height: 1;
}

.toast--success .toast-label { color: #2D6A4F; }
.toast--error   .toast-label { color: #8B1A1A; }
.toast--warning .toast-label { color: #B8860B; }
.toast--info    .toast-label { color: #2C3E6B; }
.toast--legal   .toast-label { color: #B8860B; }

.toast-message {
  font-family: Georgia, 'Times New Roman', serif;
  font-style: italic;
  font-size: 0.8125rem;
  color: #1A1A1A;
  margin: 0;
  line-height: 1.5;
  word-break: break-word;
}

/* ─── Close Button ───────────────────────────────────────────── */
.toast-close {
  flex-shrink: 0;
  background: none;
  border: none;
  padding: 2px;
  cursor: pointer;
  color: #9A9087;
  opacity: 0.6;
  margin-top: 1px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: opacity 0.15s;
}
.toast-close:hover { opacity: 1; }

/* ─── Transitions ────────────────────────────────────────────── */
/* Slide in from right, scale out on dismiss */
.toast-enter-active {
  transition: all 0.38s cubic-bezier(0.16, 1, 0.3, 1);
}
.toast-leave-active {
  transition: all 0.25s ease-in;
}
.toast-enter-from {
  opacity: 0;
  transform: translateX(24px);
}
.toast-leave-to {
  opacity: 0;
  transform: translateX(16px) scale(0.96);
}
/* Smooth reflow when items removed */
.toast-move {
  transition: transform 0.3s ease;
}
</style>
