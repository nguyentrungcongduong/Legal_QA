<template>
  <div class="app-layout">
    <!-- Main content -->
    <div class="main-content">
      <router-view />
    </div>

    <!-- Toast system: teleports to <body> tự động -->
    <LegalToast />
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'
import LegalToast from '@/components/LegalToast.vue'
import { useAuthStore } from '@/stores/authStore'

const route = useRoute()
const authStore = useAuthStore()
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
