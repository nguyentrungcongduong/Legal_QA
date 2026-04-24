<template>
  <div class="app-layout">
    <!-- Sidebar lịch sử (ẩn ở compare/evaluate để có full width) -->
    <ChatHistorySidebar
      v-if="authStore.isAuthenticated && showSidebar"
      @new-chat="handleNewChat"
      @load-session="handleLoadSession"
    />

    <!-- Main content -->
    <div class="main-content">
      <router-view />
    </div>

    <!-- Toast system: teleports to <body> tự động -->
    <LegalToast />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import ChatHistorySidebar from '@/components/ChatHistorySidebar.vue'
import LegalToast from '@/components/LegalToast.vue'
import { useHistoryStore } from '@/stores/historyStore'
import { useAuthStore } from '@/stores/authStore'

const route = useRoute()
const historyStore = useHistoryStore()
const authStore = useAuthStore()

// An sidebar o App-level cho chat (ChatView tu quan ly sidebar rieng),
// compare va evaluate can full width
const FULLWIDTH_ROUTES = ['/compare', '/evaluate', '/chat']
const showSidebar = computed(() => !FULLWIDTH_ROUTES.some(r => route.path.startsWith(r)))

function handleNewChat() {
  historyStore.currentSessionId = null;
  historyStore.messages = [];
}

function handleLoadSession(sessionId) {
  // Messages actually already loaded into historyStore inside Sidebar's loadSession dispatch
}
</script>

<style>
.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: #fafaf8;
  font-family: "Source Sans 3", Georgia, serif;
}

.main-content {
  flex: 1;
  overflow-y: auto;
  position: relative;
}
</style>
