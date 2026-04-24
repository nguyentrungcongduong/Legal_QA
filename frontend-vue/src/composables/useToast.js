/**
 * useToast.js — Legal Toast System
 * Global composable, dùng Pinia store để quản lý toasts
 * Không cần library bên ngoài.
 */
import { defineStore } from 'pinia'

// ─── Store ───────────────────────────────────────────────────
export const useToastStore = defineStore('toast', {
  state: () => ({
    toasts: []
  }),
  actions: {
    show({ message, type = 'info', label = null, duration = 4000 }) {
      const id = Date.now() + Math.random()
      this.toasts.push({ id, message, type, label, duration })
      if (duration > 0) {
        setTimeout(() => this.dismiss(id), duration)
      }
      return id
    },
    dismiss(id) {
      const idx = this.toasts.findIndex(t => t.id === id)
      if (idx > -1) this.toasts.splice(idx, 1)
    },
    clear() { this.toasts = [] }
  }
})

// ─── Convenience composable ───────────────────────────────────
export function useToast() {
  const store = useToastStore()

  return {
    success: (message, label = 'Thao tác thành công')  => store.show({ message, type: 'success', label }),
    error:   (message, label = 'Lỗi hệ thống')          => store.show({ message, type: 'error',   label }),
    warning: (message, label = 'Cảnh báo')               => store.show({ message, type: 'warning', label }),
    info:    (message, label = 'Thông báo hệ thống')     => store.show({ message, type: 'info',    label }),
    legal:   (message, label = 'Văn bản pháp lý')        => store.show({ message, type: 'legal',   label }),
    dismiss: (id) => store.dismiss(id),
  }
}
