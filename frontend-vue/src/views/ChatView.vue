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
        <router-link to="/admin" class="nav-link nav-link--admin">Quản lý</router-link>
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
              <h2 class="empty-title">Trợ lý <em>Pháp luật</em> AI</h2>
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
              <!-- Orphan: câu hỏi không có AI reply (session cũ bị lỗi lưu) -->
              <div
                v-if="isOrphanQuestion(i)"
                class="orphan-hint"
              >
                <span>⚠ Câu trả lời chưa được lưu</span>
                <button class="orphan-resend" @click="resendQuestion(msg.content)">
                  Hỏi lại →
                </button>
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
                <!-- Model used badge -->
                <span v-if="msg.modelUsed" class="model-used-badge" :class="'model-used-badge--' + msg.modelUsed">
                  {{ modelBadgeText(msg.modelUsed) }}
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
                <span v-else class="answer-text" v-html="formatAnswer(msg.content, msg.citations)" />

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
          <!-- Model selector (dropup, trái khung chat) -->
          <div class="input-toolbar">
            <div class="model-dropdown-wrap" ref="modelDropWrap">
              <button class="model-dropdown-btn" @click="modelDropOpen = !modelDropOpen">
                <span class="model-dropdown-icon">{{ currentModel.icon }}</span>
                <span class="model-dropdown-title">{{ currentModel.label }}</span>
                <svg class="model-dropdown-chevron" :class="{ open: modelDropOpen }"
                  width="13" height="13" viewBox="0 0 24 24" fill="none"
                  stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
                  <polyline points="6 9 12 15 18 9"/>
                </svg>
              </button>

              <!-- Dropup panel -->
              <transition name="dropup">
                <div v-if="modelDropOpen" class="model-dropdown-panel model-dropdown-panel--up">
                  <div
                    v-for="m in modelOptions"
                    :key="m.value"
                    class="model-dropdown-item"
                    :class="{ 'model-dropdown-item--active': selectedModel === m.value }"
                    @click="selectModel(m.value)"
                  >
                    <span class="mdi-icon">{{ m.icon }}</span>
                    <div class="mdi-info">
                      <span class="mdi-name">{{ m.label }}</span>
                      <span class="mdi-desc">{{ m.desc }}</span>
                    </div>
                    <svg v-if="selectedModel === m.value" class="mdi-check"
                      width="14" height="14" viewBox="0 0 24 24" fill="none"
                      stroke="currentColor" stroke-width="2.8" stroke-linecap="round">
                      <polyline points="20 6 9 17 4 12"/>
                    </svg>
                  </div>
                </div>
              </transition>
            </div>
          </div>

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
import { ref, watch, nextTick, onMounted, onUnmounted, computed } from 'vue'
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
const modelDropWrap = ref(null)

// State
const userInput    = ref('')
const messages     = ref([])   // [{id, role, content, createdAt, citations, rewrittenQuery, displayText, isStreaming, modelUsed}]
const loading      = ref(false)
const pendingRewrite = ref('')  // live thought-trace shown while loading

// ── Model selector ────────────────────────────────────────────────────────────
const selectedModel  = ref(localStorage.getItem('selectedModel') || 'auto')
const modelDropOpen  = ref(false)
watch(selectedModel, v => localStorage.setItem('selectedModel', v))

const modelOptions = [
  { value: 'auto',     icon: '⚡', label: 'Auto',    desc: 'Tự động chọn mô hình tốt nhất' },
  { value: 'groq',     icon: '🦙', label: 'Groq',    desc: 'Llama 3.3 70B — nhanh, chính xác' },
  { value: 'gemini',   icon: '✨', label: 'Gemini',  desc: 'Google Gemini 2.0 Flash' },
  { value: 'openai',   icon: '🤖', label: 'OpenAI',  desc: 'GPT-4o Mini' },
  { value: 'template', icon: '📄', label: 'Offline', desc: 'Template cơ bản — không cần API' },
]

const currentModel = computed(
  () => modelOptions.find(m => m.value === selectedModel.value) || modelOptions[0]
)

function selectModel(val) {
  selectedModel.value = val
  modelDropOpen.value = false
}

function modelBadgeText(modelUsed) {
  const map = { groq: '🦙 Groq', gemini: '✨ Gemini', openai: '🤖 OpenAI', template: '📄 Offline', none: '—' }
  return map[modelUsed] || modelUsed
}

// Click-outside để đóng dropdown
function onClickOutside(e) {
  if (modelDropWrap.value && !modelDropWrap.value.contains(e.target)) {
    modelDropOpen.value = false
  }
}

// Drawer
const drawerOpen    = ref(false)
const drawerCitation = ref(null)

// Suggestions cho Empty State — đa lĩnh vực
const suggestions = [
  'Vượt đèn đỏ xe máy bị phạt bao nhiêu?',
  'Tài sản chung của vợ chồng gồm những gì?',
  'Tranh chấp đất đai giữa hàng xóm giải quyết thế nào?',
  'Nồng độ cồn mức 3 bị xử lý thế nào?',
  'Quyền nuôi con sau ly hôn thuộc về ai?',
  'Điều kiện để được cấp Sổ đỏ lần đầu là gì?',
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

// Chuyển [1][2] trong text AI → span vàng clickable mở drawer
function formatAnswer(content, citations) {
  if (!content) return ''
  return content.replace(/\[(\d+)\]/g, (match, num) => {
    const idx = parseInt(num) - 1
    const hasCite = citations && citations[idx]
    if (!hasCite) return `<span class="cite-inline">[${num}]</span>`
    return `<span class="cite-inline cite-inline--link" data-cite-idx="${idx}">[${num}]</span>`
  })
}

// Delegate click cho cite-inline (vì v-html không bind @click)
if (typeof window !== 'undefined') {
  window.addEventListener('click', (e) => {
    const el = e.target.closest('[data-cite-idx]')
    if (!el) return
    // Tìm message chứa element này
    const bubble = el.closest('.bubble--ai')
    if (!bubble) return
    const msgRow = bubble.closest('.msg-row')
    if (!msgRow) return
    const msgIndex = Array.from(document.querySelectorAll('.msg-row--ai')).indexOf(msgRow)
    if (msgIndex < 0) return
    const aiMessages = messages.value.filter(m => m.role === 'assistant')
    const msg = aiMessages[msgIndex]
    if (!msg) return
    const idx = parseInt(el.dataset.citeIdx)
    const cite = msg.citations?.[idx]
    if (cite) openCitation(cite)
  })
}

function logout() {
  authStore.logout()
  router.push('/login')
}

// Phát hiện câu hỏi "mồ côi" — user message cuối không có AI reply tiếp theo
function isOrphanQuestion(index) {
  if (loading.value) return false  // đang load → không show
  const msgs = messages.value
  const current = msgs[index]
  if (current?.role !== 'user') return false
  const next = msgs[index + 1]
  // Orphan nếu: là message cuối, HOẶC message tiếp theo cũng là user (không có AI giữa)
  return !next || next.role === 'user'
}

// Gửi lại câu hỏi orphan — set vào input và submit
function resendQuestion(content) {
  userInput.value = content
  send()
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

  // 2b. Lưu user message ngay vào DB (trước khi gọi AI)
  //     → nếu AI fail, user vẫn thấy message khi reload và có thể "Hỏi lại"
  const sid = historyStore.currentSessionId
  if (sid) {
    historyStore.saveMessageToServer(sid, { role: 'user', content: q, citations: [] })
  }

  // 3. Build history from messages (before this turn)
  const history = messages.value
    .slice(0, -1)  // exclude just-added user msg
    .map(m => ({ role: m.role, content: m.content, domain: m.detectedDomain || null }))

  // 3b. Lay prev_domain tu AI message cuoi cung trong history
  const prevDomain = [...messages.value]
    .slice(0, -1)
    .reverse()
    .find(m => m.role === 'assistant' && m.detectedDomain)?.detectedDomain || null

  try {
    // 4. Call API với model preference
    const data = await queryLegalQA(q, history, 5, prevDomain, selectedModel.value)

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
      modelUsed:      data.model_used || null,
    })

    loading.value      = false
    pendingRewrite.value = ''

    // 9. Persist AI response lên server (user message đã lưu trước đó)
    if (sid) {
      const aiMsg = { role: 'assistant', content: data.answer, citations: data.citations || [] }
      historyStore.saveMessageToServer(sid, aiMsg)
    }

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
  historyStore.messages = []
  historyStore.currentSessionId = null
  userInput.value = ''
  inputEl.value?.focus()
}

function handleLoadSession() {
  // Được gọi khi sidebar emit 'load-session'
  // watch(historyStore.messages) sẽ tự sync — hàm này giữ lại để tương thích
  scrollToBottom('instant')
}

// Watch historyStore.messages — sync vào local messages[] ngay khi store có dữ liệu
// (trigger khi cụm vào sidebar, sau await loadSession() hoàn tất)
watch(
  () => historyStore.messages,
  (newMsgs) => {
    if (!newMsgs || newMsgs.length === 0) return
    messages.value = newMsgs.map(m => ({
      id:          newMsgId(),
      role:        m.role,
      content:     m.content,
      citations:   m.citations || [],
      createdAt:   m.createdAt || m.created_at || new Date().toISOString(),
      displayText: m.content,
      isStreaming:  false,
      domainEmoji:  m.domainEmoji || null,
      domainLabel:  m.domainLabel || null,
      rewrittenQuery: m.rewrittenQuery || null,
    }))
    scrollToBottom('instant')
  },
  { deep: true }
)

onMounted(async () => {
  inputEl.value?.focus()
  document.addEventListener('click', onClickOutside)

  // Auto-resume session cuối nếu có (tránh tạo session mới sau khi F5)
  const savedId = historyStore.currentSessionId
  try {
    await historyStore.fetchSessions()  // lấy danh sách mới nhất
    if (savedId && historyStore.sessions.some(s => s.id === savedId)) {
      await historyStore.loadSession(savedId)
    } else if (savedId) {
      // Session không còn tồn tại (bị xóa) — clear
      historyStore.currentSessionId = null
      localStorage.removeItem('currentSessionId')
    }
  } catch (e) {
    // fetchSessions lỗi (ví dụ: Spring Boot chưa sẵn sàng) — không crash app
    console.warn('[ChatView] fetchSessions failed on mount:', e.message)
  }
})

onUnmounted(() => {
  document.removeEventListener('click', onClickOutside)
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
.nav-link--admin { color: #6B6B6B; border-bottom: 1px dashed #ccc; }
.nav-link--admin:hover { color: #1A1A1A; border-bottom-color: #1A1A1A; }
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
  font-family: "Inter", "IBM Plex Mono", sans-serif;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.12em;
}
.msg-label--user { color: #888; }
.msg-label--ai   { color: #B8860B; }
.msg-time {
  font-family: "Inter", sans-serif;
  font-size: 11px;
  color: #BBBBBB;
}
.domain-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-family: "Inter", sans-serif;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #7A5C00;
  background: linear-gradient(135deg, #FFFBEB 0%, #FFF3CC 100%);
  border: 1px solid #F0D060;
  padding: 3px 10px;
  border-radius: 4px;
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
/* Orphan question — câu hỏi không có AI trả lời */
.orphan-hint {
  display: flex;
  align-items: center;
  gap: 10px;
  font-family: "IBM Plex Mono", monospace;
  font-size: 10px;
  color: #B8860B;
  padding: 4px 4px 0;
  animation: msgIn 0.3s ease-out;
}
.orphan-resend {
  background: transparent;
  border: 1px solid #B8860B;
  color: #B8860B;
  font-family: "IBM Plex Mono", monospace;
  font-size: 10px;
  letter-spacing: 0.05em;
  padding: 2px 10px;
  cursor: pointer;
  transition: all 0.15s;
}
.orphan-resend:hover {
  background: #B8860B;
  color: #fff;
}
.bubble--ai {
  background: #FFFDF5;
  border: 1px solid #F0E8D0;
  border-left: 3px solid #B8860B;
  font-family: "Inter", "Source Sans 3", sans-serif;
  font-style: normal;
  font-size: 15px;
  color: #1E1E1E;
  line-height: 1.8;
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
  font-family: "Inter", sans-serif;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.1em;
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
  font-family: "Inter", monospace;
  font-size: 12px;
  font-weight: 700;
  color: #B8860B;
  flex-shrink: 0;
}
.cite-name {
  font-family: "Inter", sans-serif;
  font-size: 13px;
  font-weight: 600;
  color: #1A1A1A;
  flex-shrink: 0;
}
.cite-article {
  font-family: "Inter", sans-serif;
  font-size: 12px;
  color: #777;
}

/* ═══ INPUT FOOTER ═══ */
.input-footer {
  flex-shrink: 0;
  padding: 20px 40px 24px;
  border-top: 1px solid #E8E4DF;
  background: rgba(255,255,255,0.95);
  backdrop-filter: blur(6px);
}

/* ── Input toolbar (model selector bar) ── */
.input-toolbar {
  max-width: 820px;
  margin: 0 auto 8px;
  display: flex;
  align-items: center;
}

/* ── Model Dropdown (dropup, footer trái) ── */
.model-dropdown-wrap {
  position: relative;
}
.model-dropdown-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  background: transparent;
  border: 1px solid #D0CDE8;
  border-radius: 8px;
  font-family: "Inter", sans-serif;
  font-size: 12px;
  font-weight: 600;
  color: #250EDE;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
  letter-spacing: -0.01em;
}
.model-dropdown-btn:hover {
  background: #EEF0FF;
  border-color: #250EDE;
}
.model-dropdown-icon { font-size: 14px; }
.model-dropdown-title { font-size: 12px; }
.model-dropdown-chevron {
  transition: transform 0.2s ease;
  color: #250EDE;
  opacity: 0.7;
  flex-shrink: 0;
}
/* chevron xoay lên khi mở (dropup) */
.model-dropdown-chevron.open { transform: rotate(180deg); }

/* Dropup panel — mở lên trên */
.model-dropdown-panel {
  position: absolute;
  bottom: calc(100% + 8px);
  left: 0;
  min-width: 240px;
  background: #FFFFFF;
  border: 1px solid #D8D5F0;
  border-radius: 10px;
  box-shadow: 0 -4px 24px rgba(37,14,222,0.10), 0 2px 8px rgba(0,0,0,0.08);
  z-index: 9999;
  overflow: hidden;
  padding: 6px;
}

/* Dropdown items */
.model-dropdown-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 7px;
  cursor: pointer;
  transition: background 0.12s;
}
.model-dropdown-item:hover {
  background: #EEF0FF;
}
.model-dropdown-item--active {
  background: #F0F0FF;
}
.mdi-icon {
  font-size: 18px;
  flex-shrink: 0;
  width: 24px;
  text-align: center;
}
.mdi-info {
  display: flex;
  flex-direction: column;
  gap: 1px;
  flex: 1;
  min-width: 0;
}
.mdi-name {
  font-family: "Inter", sans-serif;
  font-size: 13px;
  font-weight: 600;
  color: #1A1A1A;
  line-height: 1.3;
}
.mdi-desc {
  font-family: "Inter", sans-serif;
  font-size: 11px;
  color: #999;
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.mdi-check {
  color: #250EDE;
  flex-shrink: 0;
}

/* Dropup animation (mở lên) */
.dropup-enter-active, .dropup-leave-active {
  transition: opacity 0.15s, transform 0.15s;
}
.dropup-enter-from, .dropup-leave-to {
  opacity: 0;
  transform: translateY(8px) scale(0.97);
}

/* Model used badge on AI message */
.model-used-badge {
  display: inline-flex;
  align-items: center;
  font-family: "IBM Plex Mono", monospace;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.04em;
  padding: 2px 8px;
  border-radius: 3px;
  border: 1px solid transparent;
}
.model-used-badge--groq    { color: #250EDE; background: #EEEEFF; border-color: #B0B8FF; }
.model-used-badge--gemini  { color: #1A5276; background: #EBF5FB; border-color: #AED6F1; }
.model-used-badge--openai  { color: #145A32; background: #EAFAF1; border-color: #A9DFBF; }
.model-used-badge--template{ color: #777; background: #F5F5F5; border-color: #DDD; }


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
  font-family: "Inter", "Source Sans 3", sans-serif;
  font-size: 15px;
  font-style: normal;
  color: #1A1A1A;
  resize: none;
  overflow-y: hidden;
  transition: border-color 0.2s, box-shadow 0.2s;
  line-height: 1.6;
  min-height: 52px;
}
.chat-input:focus {
  outline: none;
  border-color: #B8860B;
  box-shadow: 0 0 0 1px #B8860B;
}
.chat-input:disabled { opacity: 0.6; }
.input-hint {
  font-family: "Inter", sans-serif;
  font-size: 12px;
  color: #BBBBBB;
  letter-spacing: 0.02em;
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

/* ═══ LOADING / THINKING DOTS ═══ */
.bubble--loading {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  background: #F5F2EC;
  border: 1px solid #E8E0D0;
  min-height: 48px;
}
.thinking-dots {
  display: flex;
  align-items: center;
  gap: 5px;
  flex-shrink: 0;
}
.thinking-dots span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #B8860B;
  opacity: 0.3;
  animation: dotPulse 1.4s ease-in-out infinite;
}
.thinking-dots span:nth-child(1) { animation-delay: 0s; }
.thinking-dots span:nth-child(2) { animation-delay: 0.2s; }
.thinking-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes dotPulse {
  0%, 80%, 100% { opacity: 0.2; transform: scale(0.85); }
  40%            { opacity: 1;   transform: scale(1.2);  }
}
.thinking-label {
  font-size: 13px;
  color: #8A7A60;
  font-style: italic;
  animation: textFade 2s ease-in-out infinite;
}
@keyframes textFade {
  0%, 100% { opacity: 0.6; }
  50%       { opacity: 1;   }
}
.thought-trace--live {
  font-size: 12px;
  color: #8A6400;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
  animation: textFade 1.5s ease-in-out infinite;
}


/* ═══ INLINE CITATION SPANS (trong text AI) ═══ */
.cite-inline {
  display: inline-block;
  font-size: 11px;
  font-weight: 700;
  color: #B8860B;
  vertical-align: super;
  line-height: 1;
  margin: 0 1px;
}
.cite-inline--link {
  cursor: pointer;
  text-decoration: none;
  border-bottom: 1px dashed #B8860B;
  transition: color 0.15s, border-color 0.15s;
}
.cite-inline--link:hover {
  color: #8A6400;
  border-bottom-style: solid;
}

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
