<template>
  <div class="sidebar">

    <!-- Header -->
    <div class="sidebar-header">
      <span class="sidebar-title">LỊCH SỬ</span>
      <button class="new-chat-btn" @click="startNewChat">
        + MỚI
      </button>
    </div>

    <!-- Search -->
    <div class="search-wrap">
      <input
        v-model="searchQuery"
        class="search-input"
        placeholder="Tìm kiếm..."
      />
    </div>

    <!-- Loading -->
    <div v-if="loading" class="sidebar-loading">
      <span>Đang tải...</span>
    </div>

    <!-- Empty state -->
    <div v-else-if="filteredSessions.length === 0" class="empty-state">
      <p>Chưa có lịch sử hội thoại</p>
      <span>Đặt câu hỏi đầu tiên để bắt đầu</span>
    </div>

    <!-- Session list -->
    <div v-else class="session-list">
      <!-- Group theo ngày -->
      <div
        v-for="(group, date) in groupedSessions"
        :key="date"
        class="session-group"
      >
        <p class="group-label">{{ date }}</p>

        <div
          v-for="session in group"
          :key="session.id"
          class="session-item"
          :class="{ active: session.id === historyStore.currentSessionId }"
          @click="loadSession(session.id)"
        >
          <div class="session-content">
            <p class="session-title">{{ session.title }}</p>
            <p class="session-time">{{ formatTime(session.createdAt) }}</p>
          </div>

          <button
            class="delete-btn"
            @click.stop="confirmDelete(session)"
            title="Xóa"
          >×</button>
        </div>
      </div>
    </div>

    <!-- User info bottom -->
    <div class="sidebar-footer">
      <div class="user-info">
        <div class="user-avatar">
          {{ userInitial }}
        </div>
        <div class="user-details">
          <p class="user-email">{{ authStore.user?.email }}</p>
          <p class="user-role">Legal Researcher</p>
        </div>
      </div>
      <button class="logout-btn" @click="logout">THOÁT</button>
    </div>

    <!-- Delete confirm modal -->
    <div
      v-if="sessionToDelete"
      class="modal-overlay"
      @click="sessionToDelete = null"
    >
      <div class="modal" @click.stop>
        <p class="modal-title">Xóa hội thoại?</p>
        <p class="modal-text">
          "{{ sessionToDelete.title }}" sẽ bị xóa vĩnh viễn.
        </p>
        <div class="modal-actions">
          <button class="modal-cancel" @click="sessionToDelete = null">
            Hủy
          </button>
          <button class="modal-confirm" @click="deleteSession">
            Xóa
          </button>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useHistoryStore } from '@/stores/historyStore'
import { useAuthStore } from '@/stores/authStore'
import { useRouter } from 'vue-router'

const emit = defineEmits(['new-chat', 'load-session'])

const historyStore = useHistoryStore()
const authStore = useAuthStore()
const router = useRouter()

const searchQuery = ref('')
const loading = ref(false)
const sessionToDelete = ref(null)

const userInitial = computed(() =>
  authStore.user?.email?.[0]?.toUpperCase() ?? 'U'
)

const filteredSessions = computed(() => {
  if (!searchQuery.value) return historyStore.sessions
  return historyStore.sessions.filter(s =>
    s.title.toLowerCase().includes(searchQuery.value.toLowerCase())
  )
})

// Group sessions theo ngày
const groupedSessions = computed(() => {
  const groups = {}
  filteredSessions.value.forEach(session => {
    const date = formatDate(session.createdAt)
    if (!groups[date]) groups[date] = []
    groups[date].push(session)
  })
  return groups
})

onMounted(async () => {
  loading.value = true
  await historyStore.fetchSessions()
  loading.value = false
})

function startNewChat() {
  historyStore.currentSessionId = null
  historyStore.messages = []
  emit('new-chat')
}

async function loadSession(sessionId) {
  loading.value = true
  await historyStore.loadSession(sessionId)
  loading.value = false
  emit('load-session', sessionId)
}

function confirmDelete(session) {
  sessionToDelete.value = session
}

async function deleteSession() {
  if (!sessionToDelete.value) return
  await historyStore.deleteSession(sessionToDelete.value.id)
  sessionToDelete.value = null
}

function logout() {
  authStore.logout()
  router.push('/login')
}

function formatDate(dateStr) {
  const date = new Date(dateStr)
  const today = new Date()
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)

  if (date.toDateString() === today.toDateString()) return 'Hôm nay'
  if (date.toDateString() === yesterday.toDateString()) return 'Hôm qua'
  return date.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' })
}

function formatTime(dateStr) {
  return new Date(dateStr).toLocaleTimeString('vi-VN', {
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped>
.sidebar {
  width: 100%;
  min-width: 0;
  background: #1a1a1a;
  display: flex;
  flex-direction: column;
  height: 100%;
  font-family: 'IBM Plex Mono', monospace;
  overflow-y: auto;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 16px 12px;
  border-bottom: 1px solid #2a2a2a;
}

.sidebar-title {
  font-size: 10px;
  letter-spacing: 0.2em;
  color: #666;
}

.new-chat-btn {
  font-size: 10px;
  letter-spacing: 0.1em;
  color: #B8860B;
  background: transparent;
  border: 1px solid #B8860B;
  padding: 4px 10px;
  cursor: pointer;
  transition: all 0.15s;
}

.new-chat-btn:hover {
  background: #B8860B;
  color: #1a1a1a;
}

.search-wrap { padding: 12px 16px; }

.search-input {
  width: 100%;
  padding: 8px 10px;
  background: #2a2a2a;
  border: 1px solid #333;
  color: #ccc;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 12px;
  outline: none;
  box-sizing: border-box;
}

.search-input:focus { border-color: #B8860B; }
.search-input::placeholder { color: #555; }

.sidebar-loading,
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #555;
  font-size: 12px;
  gap: 8px;
  padding: 20px;
  text-align: center;
}

.empty-state span { font-size: 11px; color: #444; }

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.session-list::-webkit-scrollbar { width: 4px; }
.session-list::-webkit-scrollbar-track { background: transparent; }
.session-list::-webkit-scrollbar-thumb { background: #333; }

.session-group { margin-bottom: 8px; }

.group-label {
  font-size: 9px;
  letter-spacing: 0.15em;
  color: #555;
  padding: 8px 16px 4px;
  margin: 0;
}

.session-item {
  display: flex;
  align-items: center;
  padding: 10px 16px;
  cursor: pointer;
  transition: background 0.15s;
  border-left: 2px solid transparent;
}

.session-item:hover { background: #222; }

.session-item.active {
  background: #222;
  border-left-color: #B8860B;
}

.session-content { flex: 1; min-width: 0; }

.session-title {
  font-size: 12px;
  color: #ccc;
  margin: 0 0 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.session-item.active .session-title { color: #fff; }

.session-time {
  font-size: 10px;
  color: #555;
  margin: 0;
}

.delete-btn {
  background: transparent;
  border: none;
  color: #444;
  font-size: 16px;
  cursor: pointer;
  padding: 2px 4px;
  opacity: 0;
  transition: all 0.15s;
  line-height: 1;
}

.session-item:hover .delete-btn { opacity: 1; }
.delete-btn:hover { color: #c0392b; }

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid #2a2a2a;
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-info {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #B8860B;
  color: #1a1a1a;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
}

.user-details { min-width: 0; }

.user-email {
  font-size: 11px;
  color: #aaa;
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-role {
  font-size: 10px;
  color: #555;
  margin: 2px 0 0;
}

.logout-btn {
  font-size: 9px;
  letter-spacing: 0.1em;
  color: #555;
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 4px;
  transition: color 0.15s;
  flex-shrink: 0;
}

.logout-btn:hover { color: #c0392b; }

/* Modal */
.modal-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0,0,0,0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
}

.modal {
  background: #1a1a1a;
  border: 1px solid #333;
  padding: 24px;
  width: 220px;
}

.modal-title {
  font-size: 13px;
  color: #fff;
  margin: 0 0 8px;
}

.modal-text {
  font-size: 11px;
  color: #888;
  margin: 0 0 20px;
  line-height: 1.5;
}

.modal-actions {
  display: flex;
  gap: 8px;
}

.modal-cancel {
  flex: 1;
  padding: 8px;
  background: transparent;
  border: 1px solid #333;
  color: #888;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 11px;
  cursor: pointer;
}

.modal-confirm {
  flex: 1;
  padding: 8px;
  background: #c0392b;
  border: none;
  color: white;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 11px;
  cursor: pointer;
}
</style>
