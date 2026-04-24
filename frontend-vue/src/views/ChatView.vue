<template>
  <div class="chat-shell">

    <!-- ═══ TOPBAR ═══ -->
    <header class="topbar">
      <div class="brand-group">
        <h1 class="brand">Legal AI <em class="accent">Assistant</em></h1>
        <span class="verified-badge">
          <span class="dot" />VERIFIED LAW SOURCE
        </span>
      </div>
      <nav class="header-nav">
        <router-link to="/compare" class="nav-link">So sánh mô hình</router-link>
        <router-link to="/evaluate" class="nav-link nav-link--gold">Evaluation</router-link>
        <button @click="logout" class="logout-btn">Đăng xuất</button>
      </nav>
    </header>

    <!-- ═══ BODY: SIDEBAR + THREAD ═══ -->
    <div class="body-layout">

      <!-- SIDEBAR: Chat sessions -->
      <aside class="session-sidebar">
        <ChatHistorySidebar
          @new-chat="handleNewChat"
          @load-session="handleLoadSession"
        />
      </aside>

      <!-- MAIN THREAD -->
      <main class="thread-main">

        <!-- Session header -->
        <div class="session-header">
          <span class="session-label">PHIÊN TƯ VẤN</span>
          <span class="session-title">
            {{ historyStore.currentSessionId ? `#${String(historyStore.currentSessionId).slice(-6).toUpperCase()}` : 'Mới' }}
          </span>
          <span class="session-model-badge">RAG · Hybrid Retrieval · Multi-turn</span>
        </div>

        <!-- ── MESSAGE THREAD ── -->
        <div ref="threadEl" class="message-thread" id="message-thread">

          <!-- EMPTY STATE -->
          <transition name="fade">
            <div v-if="messages.length === 0 && !loading" class="empty-state">
              <div class="empty-glyph">§</div>
              <h2 class="empty-title">Tư vấn <em>Pháp luật</em> Giao thông</h2>
              <p class="empty-sub">Đặt câu hỏi để bắt đầu phiên tư vấn. Hệ thống sẽ trích dẫn trực tiếp từ văn bản pháp luật hiện hành.</p>

              <div class="suggestion-grid">
                <button
                  v-for="s in suggestions" :key="s"
                  class="suggestion-chip"
                  @click="useSuggestion(s)"
                >{{ s }}</button>
              </div>
            </div>
          </transition>

          <!-- MESSAGES -->
          <div
            v-for="(msg, i) in messages"
            :key="msg.id || i"
            class="msg-row"
            :class="msg.role === 'user' ? 'msg-row--user' : 'msg-row--ai'"
          >
            <!-- USER bubble -->
            <template v-if="msg.role === 'user'">
              <div class="msg-meta">
                <span class="msg-label msg-label--user">Thân chủ</span>
                <span class="msg-time">{{ formatTime(msg.createdAt) }}</span>
              </div>
              <div class="bubble bubble--user">
                {{ msg.content }}
              </div>
            </template>

            <!-- AI bubble -->
            <template v-else>
              <div class="msg-meta">
                <span class="msg-label msg-label--ai">Hệ thống Luật sư AI</span>
                <!-- Domain badge -->
                <span v-if="msg.domainEmoji" class="domain-badge">
                  {{ msg.domainEmoji }} {{ msg.domainLabel }}
                </span>
                <span class="msg-time">{{ formatTime(msg.createdAt) }}</span>
              </div>

              <!-- Thought Trace badge (rewritten query) -->
              <div v-if="msg.rewrittenQuery" class="thought-trace">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
                Hệ thống hiểu câu hỏi là:
                <em>"{{ msg.rewrittenQuery }}"</em>
              </div>

              <!-- AI answer bubble (last AI = typewriter, rest = static) -->
              <div class="bubble bubble--ai">
                <template v-if="msg.isStreaming">
                  <span class="answer-text">{{ msg.displayText }}</span><span class="stream-caret">|</span>
                </template>
                <span v-else class="answer-text">{{ msg.content }}</span>

                <!-- Per-message Citations -->
                <div v-if="msg.citations && msg.citations.length" class="cite-strip">
                  <span class="cite-label">CĂN CỨ PHÁP LÝ</span>
                  <div class="cite-chips">
                    <button
                      v-for="(c, ci) in msg.citations"
                      :key="ci"
                      class="cite-chip"
                      :title="`${c.law_name} — ${c.article || ''}`"
                      @click="openCitation(c)"
                    >
                      <span class="cite-num">[{{ ci + 1 }}]</span>
                      <span class="cite-name">{{ c.law_name }}</span>
                      <span v-if="c.article" class="cite-article">{{ c.article }}</span>
                    </button>
                  </div>
                </div>
              </div>
            </template>
          </div>

          <!-- LOADING indicator -->
          <div v-if="loading" class="msg-row msg-row--ai">
            <div class="msg-meta">
              <span class="msg-label msg-label--ai">Hệ thống Luật sư AI</span>
            </div>
            <!-- Thought trace during loading: show thinking rewritten query -->
            <div v-if="pendingRewrite" class="thought-trace thought-trace--live">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
              Đang truy xuất theo:
              <em>"{{ pendingRewrite }}"</em>
            </div>
            <div class="bubble bubble--ai bubble--loading">
              <span class="thinking-dots">
                <span /><span /><span />
              </span>
              <span class="thinking-label">Đang truy xuất văn bản pháp luật...</span>
            </div>
          </div>

          <!-- Scroll anchor -->
          <div ref="bottomEl" id="thread-bottom" />
        </div>

        <!-- ── STICKY INPUT ── -->
        <footer class="input-footer">
          <form class="input-row" @submit.prevent="send">
            <div class="input-wrap">
              <textarea
                ref="inputEl"
                v-model="userInput"
                class="chat-input"
                rows="1"
                placeholder="Hỏi tiếp về vấn đề pháp luật..."
                :disabled="loading"
                @keydown.enter.exact.prevent="send"
                @keydown.enter.shift.exact="userInput += '\n'"
                @input="autoResize"
              />
              <span class="input-hint">Enter để gửi · Shift+Enter xuống dòng</span>
            </div>
            <button type="submit" class="send-btn" :disabled="loading || !userInput.trim()">
              <svg v-if="!loading" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
              <span v-else class="spinner" />
            </button>
          </form>
        </footer>

      </main>
    </div>

    <!-- Document Metadata Drawer -->
    <DocumentMetadataDrawer
      :is-open="drawerOpen"
      :data="drawerCitation"
      @close="drawerOpen = false"
    />
  </div>
</template>

<script setup>
import { ref, watch, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/authStore'
import { useHistoryStore } from '@/stores/historyStore'
import ChatHistorySidebar from '@/components/ChatHistorySidebar.vue'
import DocumentMetadataDrawer from '@/components/DocumentMetadataDrawer.vue'
import { queryLegalQA } from '@/services/api'
import { useToast } from '@/composables/useToast'

const router       = useRouter()
const authStore    = useAuthStore()
const historyStore = useHistoryStore()
const toast        = useToast()

// Refs
const threadEl   = ref(null)
const bottomEl   = ref(null)
const inputEl    = ref(null)

// State
const userInput    = ref('')
const messages     = ref([])   // [{id, role, content, createdAt, citations, rewrittenQuery, displayText, isStreaming}]
const loading      = ref(false)
const pendingRewrite = ref('')  // live thought-trace shown while loading

// Drawer
const drawerOpen    = ref(false)
const drawerCitation = ref(null)

// Suggestions cho Empty State
const suggestions = [
  'Vượt đèn đỏ xe máy phạt bao nhiêu?',
  'Nồng độ cồn mức 3 bị xử lý thế nào?',
  'Không đội mũ bảo hiểm bị phạt tiền mấy?',
  'Thủ tục xử phạt vi phạm giao thông?',
]

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })
}

function newMsgId() {
  return `msg-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`
}

async function scrollToBottom(behavior = 'smooth') {
  await nextTick()
  bottomEl.value?.scrollIntoView({ behavior, block: 'end' })
}

function autoResize(e) {
  const el = e.target
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 160) + 'px'
}

function resetInputHeight() {
  if (inputEl.value) inputEl.value.style.height = 'auto'
}

// ─── Typewriter effect (per-message) ──────────────────────────────────────────

function streamMessage(msgId, fullText) {
  const msg = messages.value.find(m => m.id === msgId)
  if (!msg) return Promise.resolve()

  msg.displayText = ''
  msg.isStreaming  = true

  return new Promise(resolve => {
    let i = 0
    const timer = setInterval(() => {
      i += 3  // 3 chars/tick = snappy but readable
      msg.displayText = fullText.slice(0, i)
      scrollToBottom()
      if (i >= fullText.length) {
        clearInterval(timer)
        msg.displayText = fullText
        msg.isStreaming  = false
        resolve()
      }
    }, 10)
  })
}

// ─── Core actions ──────────────────────────────────────────────────────────────

function useSuggestion(text) {
  userInput.value = text
  send()
}

function openCitation(c) {
  const page = c.page_number ? ` — trang ${c.page_number}` : ''
  toast.legal(
    `Đang tải bản gốc: ${c.law_name || 'Văn bản pháp lý'}${page}`,
    'Truy xuất tài liệu'
  )
  drawerCitation.value = c
  drawerOpen.value     = true
}

function logout() {
  authStore.logout()
  router.push('/login')
}

async function send() {
  const q = userInput.value.trim()
  if (!q || loading.value) return

  userInput.value = ''
  resetInputHeight()
  loading.value    = true
  pendingRewrite.value = ''

  // 1. Push user message immediately
  messages.value.push({
    id:        newMsgId(),
    role:      'user',
    content:   q,
    createdAt: new Date().toISOString(),
  })
  await scrollToBottom()

  // 2. Create session if needed
  if (!historyStore.currentSessionId) {
    await historyStore.createSession(q)
  }

  // 3. Build history from messages (before this turn)
  const history = messages.value
    .slice(0, -1)  // exclude just-added user msg
    .map(m => ({ role: m.role, content: m.content }))

  try {
    // 4. Call API
    const data = await queryLegalQA(q, history)

    // 5. Show pending rewrite during generation (retroactive)
    if (data.rewritten_query && data.rewritten_query !== q) {
      pendingRewrite.value = data.rewritten_query
    }

    // 6. Push AI message placeholder
    const aiMsgId = newMsgId()
    const userQ = q  // capture before async
    messages.value.push({
      id:             aiMsgId,
      role:           'assistant',
      content:        data.answer,
      citations:      data.citations || [],
      rewrittenQuery: data.rewritten_query !== userQ ? data.rewritten_query : null,
      createdAt:      new Date().toISOString(),
      displayText:    '',
      isStreaming:    false,
      // Multi-domain metadata
      detectedDomain: data.detected_domain || null,
      domainLabel:    data.domain_label || null,
      domainEmoji:    data.domain_emoji || null,
    })

    loading.value      = false
    pendingRewrite.value = ''

    // 7. Typewriter stream
    await streamMessage(aiMsgId, data.answer)

    // 8. Toast
    const n = (data.citations || []).length
    if (n > 0) {
      const domainTag = data.domain_emoji ? `${data.domain_emoji} ${data.domain_label} · ` : ''
      toast.success(
        `${domainTag}Nguồn đã được xác thực bởi ${n} văn bản pháp lý.`,
        'Tư vấn hoàn tất'
      )
    }

    // 9. Save to historyStore
    historyStore.addMessage({ role: 'user', content: q, createdAt: new Date().toISOString() })
    historyStore.addMessage({
      role: 'assistant', content: data.answer,
      citations: data.citations, createdAt: new Date().toISOString()
    })

    await scrollToBottom()
    inputEl.value?.focus()

  } catch (err) {
    loading.value = false
    pendingRewrite.value = ''
    const errMsgId = newMsgId()
    messages.value.push({
      id:        errMsgId,
      role:      'assistant',
      content:   `Lỗi kết nối: ${err.message}. Vui lòng thử lại.`,
      citations: [],
      createdAt: new Date().toISOString(),
      displayText: '',
      isStreaming: false,
    })
    await streamMessage(errMsgId, messages.value.at(-1).content)
    toast.error('Không thể kết nối đến máy chủ.', 'Lỗi kết nối')
  }
}

// ─── Session load from sidebar ─────────────────────────────────────────────────

function handleNewChat() {
  messages.value = []
  userInput.value = ''
  inputEl.value?.focus()
}

function handleLoadSession(session) {
  // Rebuild messages from historyStore.messages
  messages.value = historyStore.messages.map(m => ({
    id:        newMsgId(),
    role:      m.role,
    content:   m.content,
    citations: m.citations || [],
    createdAt: m.createdAt,
    displayText: m.content,
    isStreaming: false,
  }))
  scrollToBottom('instant')
}

watch(() => historyStore.currentSessionId, (newId, oldId) => {
  if (newId && newId !== oldId) {
    // Small delay to allow historyStore.messages to populate
    setTimeout(() => handleLoadSession(), 100)
  }
})

onMounted(() => {
  inputEl.value?.focus()
})
</script>

<style scoped>

/* ═══ SHELL ═══ */
.chat-shell {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  background: #FAFAF8;
  font-family: "Source Sans 3", Georgia, serif;
  -webkit-font-smoothing: antialiased;
  color: #1A1A1A;
}

/* ═══ TOPBAR ═══ */
.topbar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 32px;
  background: rgba(255,255,255,0.85);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid #E8E4DF;
  z-index: 20;
}
.brand-group { display: flex; align-items: center; gap: 16px; }
.brand {
  margin: 0;
  font-family: "Playfair Display", Georgia, serif;
  font-size: 26px;
  font-weight: 700;
  font-style: italic;
  letter-spacing: -0.02em;
}
.accent { color: #B8860B; }
.verified-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 9px;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: #6B6B6B;
  font-family: "IBM Plex Mono", monospace;
}
.dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: #22C55E;
  animation: pulse 2s infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
.header-nav { display: flex; align-items: center; gap: 20px; }
.nav-link {
  font-size: 11px;
  color: #1A1A1A;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-weight: 600;
  text-decoration: none;
  transition: color 0.2s;
}
.nav-link:hover { color: #B8860B; }
.nav-link--gold { color: #B8860B; border-bottom: 1px solid currentColor; }
.logout-btn {
  background: transparent;
  border: 1px solid #1A1A1A;
  padding: 5px 14px;
  font-size: 11px;
  cursor: pointer;
  border-radius: 3px;
  transition: all 0.2s;
}
.logout-btn:hover { background: #1A1A1A; color: #FAFAF8; }

/* ═══ BODY LAYOUT ═══ */
.body-layout {
  flex: 1;
  display: flex;
  min-height: 0;
  overflow: hidden;
}

/* ═══ SESSION SIDEBAR ═══ */
.session-sidebar {
  width: 260px;
  flex-shrink: 0;
  border-right: 1px solid #E8E4DF;
  overflow-y: auto;
  background: #fff;
}

/* ═══ THREAD MAIN ═══ */
.thread-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
}

/* Session header strip */
.session-header {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 40px;
  border-bottom: 1px solid #E8E4DF;
  background: #fff;
}
.session-label {
  font-family: "IBM Plex Mono", monospace;
  font-size: 9px;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: #B8860B;
  font-weight: 700;
}
.session-title {
  font-family: "IBM Plex Mono", monospace;
  font-size: 11px;
  color: #1A1A1A;
  font-weight: 600;
}
.session-model-badge {
  font-family: "IBM Plex Mono", monospace;
  font-size: 9px;
  color: #6B6B6B;
  margin-left: auto;
  letter-spacing: 0.05em;
}

/* ═══ MESSAGE THREAD ═══ */
.message-thread {
  flex: 1;
  overflow-y: auto;
  padding: 48px 40px 24px;
  scroll-behavior: smooth;
}

/* ── Empty State ── */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  text-align: center;
  gap: 16px;
  max-width: 600px;
  margin: 0 auto;
}
.empty-glyph {
  font-family: "Playfair Display", serif;
  font-size: 80px;
  color: #B8860B;
  opacity: 0.18;
  line-height: 1;
  font-weight: 700;
  font-style: italic;
}
.empty-title {
  margin: 0;
  font-family: "Playfair Display", serif;
  font-size: 32px;
  font-weight: 700;
  font-style: italic;
  color: #1A1A1A;
}
.empty-sub {
  margin: 0;
  font-size: 15px;
  color: #6B6B6B;
  line-height: 1.6;
}
.suggestion-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  width: 100%;
  margin-top: 16px;
}
.suggestion-chip {
  background: #fff;
  border: 1px solid #E8E4DF;
  padding: 14px 16px;
  text-align: left;
  font-family: "Playfair Display", serif;
  font-size: 13px;
  font-style: italic;
  color: #1A1A1A;
  cursor: pointer;
  transition: all 0.2s;
  line-height: 1.4;
}
.suggestion-chip:hover {
  border-color: #B8860B;
  background: #FFFBEB;
  color: #8A6400;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(184,134,11,0.08);
}

/* ── Message Row ── */
.msg-row {
  max-width: 820px;
  margin: 0 auto 36px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  animation: msgIn 0.3s ease-out;
}
@keyframes msgIn {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: none; }
}
.msg-row--user { align-items: flex-end; }
.msg-row--ai   { align-items: flex-start; }

.msg-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 4px;
}
.msg-label {
  font-family: "IBM Plex Mono", "Courier New", monospace;
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.18em;
}
.msg-label--user { color: #6B6B6B; }
.msg-label--ai   { color: #B8860B; }
.msg-time {
  font-family: "IBM Plex Mono", monospace;
  font-size: 9px;
  color: #BBBBBB;
}
.domain-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-family: "IBM Plex Mono", monospace;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #7A5C00;
  background: linear-gradient(135deg, #FFFBEB 0%, #FFF3CC 100%);
  border: 1px solid #F0D060;
  padding: 2px 8px;
  animation: badgePop 0.3s ease-out;
}
@keyframes badgePop {
  from { opacity: 0; transform: scale(0.85); }
  to   { opacity: 1; transform: scale(1); }
}

/* ── Bubbles ── */
.bubble {
  padding: 18px 22px;
  line-height: 1.75;
  max-width: 88%;
  position: relative;
}
.bubble--user {
  background: #FFFFFF;
  border: 1px solid #E8E4DF;
  font-family: "Source Sans 3", sans-serif;
  font-size: 15px;
  color: #1A1A1A;
  box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}
.bubble--ai {
  background: #FFFDF5;
  border-left: 3px solid #B8860B;
  border: 1px solid #F0E8D0;
  border-left: 3px solid #B8860B;
  font-family: "Playfair Display", Georgia, serif;
  font-style: italic;
  font-size: 16px;
  color: #2A2A2A;
  box-shadow: 0 2px 12px rgba(184,134,11,0.06);
  width: 100%;
}

/* Thought trace */
.thought-trace {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: "IBM Plex Mono", monospace;
  font-size: 10px;
  color: #B8860B;
  background: #FFFBEB;
  border: 1px solid #FDE68A;
  padding: 5px 10px;
  margin-bottom: 2px;
  letter-spacing: 0.02em;
  animation: fadeSlide 0.35s ease-out;
}
.thought-trace em {
  font-style: italic;
  font-weight: 600;
}
.thought-trace--live {
  animation: fadeSlide 0.35s ease-out, shimmer 1.5s ease-in-out infinite;
}
@keyframes fadeSlide {
  from { opacity: 0; transform: translateX(-6px); }
  to   { opacity: 1; transform: none; }
}
@keyframes shimmer {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.65; }
}

/* Loading bubble */
.bubble--loading {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 22px;
  min-width: 180px;
}
.thinking-dots {
  display: flex;
  gap: 5px;
  align-items: center;
}
.thinking-dots span {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: #B8860B;
  animation: dotBounce 1.2s ease-in-out infinite;
}
.thinking-dots span:nth-child(2) { animation-delay: 0.2s; }
.thinking-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes dotBounce {
  0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
  40% { transform: scale(1.1); opacity: 1; }
}
.thinking-label {
  font-family: "IBM Plex Mono", monospace;
  font-size: 10px;
  color: #9B8B5A;
  letter-spacing: 0.05em;
  font-style: normal;
}

/* Typewriter caret */
.stream-caret {
  margin-left: 2px;
  color: #B8860B;
  animation: blink 0.8s infinite;
}
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
.answer-text { white-space: pre-wrap; }

/* ── Citation chips (per-message) ── */
.cite-strip {
  margin-top: 18px;
  padding-top: 14px;
  border-top: 1px solid #EDE8D8;
}
.cite-label {
  display: block;
  font-family: "IBM Plex Mono", monospace;
  font-size: 8px;
  font-weight: 700;
  letter-spacing: 0.2em;
  color: #B8860B;
  text-transform: uppercase;
  margin-bottom: 10px;
}
.cite-chips {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.cite-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #FAFAF8;
  border: 1px solid #E8E4DF;
  padding: 8px 12px;
  cursor: pointer;
  text-align: left;
  font-style: normal;
  transition: all 0.2s;
}
.cite-chip:hover {
  border-color: #B8860B;
  background: #FFFBEB;
  transform: translateX(3px);
}
.cite-num {
  font-family: "IBM Plex Mono", monospace;
  font-size: 10px;
  font-weight: 700;
  color: #B8860B;
  flex-shrink: 0;
}
.cite-name {
  font-family: "Source Sans 3", sans-serif;
  font-size: 12px;
  font-weight: 600;
  color: #1A1A1A;
  flex-shrink: 0;
}
.cite-article {
  font-family: "IBM Plex Mono", monospace;
  font-size: 10px;
  color: #8B8B8B;
}

/* ═══ INPUT FOOTER ═══ */
.input-footer {
  flex-shrink: 0;
  padding: 20px 40px 24px;
  border-top: 1px solid #E8E4DF;
  background: rgba(255,255,255,0.95);
  backdrop-filter: blur(6px);
}
.input-row {
  max-width: 820px;
  margin: 0 auto;
  display: flex;
  gap: 12px;
  align-items: flex-end;
}
.input-wrap {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.chat-input {
  width: 100%;
  padding: 14px 16px;
  border: 1px solid #E8E4DF;
  background: #fff;
  font-family: "Playfair Display", serif;
  font-size: 16px;
  font-style: italic;
  color: #1A1A1A;
  resize: none;
  overflow-y: hidden;
  transition: border-color 0.2s, box-shadow 0.2s;
  line-height: 1.5;
  min-height: 52px;
}
.chat-input:focus {
  outline: none;
  border-color: #B8860B;
  box-shadow: 0 0 0 1px #B8860B;
}
.chat-input:disabled { opacity: 0.6; }
.input-hint {
  font-family: "IBM Plex Mono", monospace;
  font-size: 9px;
  color: #BBBBBB;
  letter-spacing: 0.05em;
  padding-left: 2px;
}
.send-btn {
  width: 52px;
  height: 52px;
  flex-shrink: 0;
  background: #B8860B;
  border: none;
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s, transform 0.1s;
}
.send-btn:hover:not(:disabled) {
  background: #8A6400;
  transform: scale(1.04);
}
.send-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.spinner {
  width: 16px; height: 16px;
  border: 2px solid rgba(255,255,255,0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ═══ TRANSITIONS ═══ */
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* ═══ SCROLLBAR ═══ */
.message-thread::-webkit-scrollbar { width: 4px; }
.message-thread::-webkit-scrollbar-track { background: transparent; }
.message-thread::-webkit-scrollbar-thumb { background: #E0DAD0; border-radius: 4px; }

/* ═══ RESPONSIVE ═══ */
@media (max-width: 960px) {
  .session-sidebar { width: 200px; }
  .message-thread { padding: 32px 20px 16px; }
  .input-footer { padding: 16px 20px; }
}
@media (max-width: 680px) {
  .session-sidebar { display: none; }
  .suggestion-grid { grid-template-columns: 1fr; }
}
</style>
