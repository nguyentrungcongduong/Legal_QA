<template>
  <div class="admin-page">

    <!-- Header -->
    <div class="admin-header">
      <div>
        <h1 class="admin-title">Quản lý hệ thống</h1>
        <p class="admin-sub">Chỉ dành cho quản trị viên · {{ authStore.user?.email }}</p>
      </div>
      <div class="tab-group">
        <button
          v-for="tab in tabs" :key="tab.id"
          class="tab-btn" :class="{ active: activeTab === tab.id }"
          @click="activeTab = tab.id"
        >{{ tab.label }}</button>
      </div>
    </div>

    <!-- ═══════════ TAB: THỐNG KÊ ═══════════ -->
    <div v-if="activeTab === 'stats'" class="tab-content">

      <div class="stats-grid" v-if="stats">
        <div class="stat-card">
          <p class="stat-label">VĂN BẢN PHÁP LUẬT</p>
          <p class="stat-value">{{ stats.overview.total_docs }}</p>
        </div>
        <div class="stat-card">
          <p class="stat-label">TỔNG CHUNKS</p>
          <p class="stat-value">{{ stats.overview.total_chunks.toLocaleString() }}</p>
        </div>
        <div class="stat-card">
          <p class="stat-label">NGƯỜI DÙNG</p>
          <p class="stat-value">{{ stats.overview.total_users }}</p>
        </div>
        <div class="stat-card">
          <p class="stat-label">TỔNG CÂU HỎI</p>
          <p class="stat-value">{{ stats.overview.total_messages.toLocaleString() }}</p>
        </div>
      </div>
      <div v-else class="loading-msg">Đang tải thống kê...</div>

      <div class="section-card" v-if="stats?.domain_stats?.length">
        <p class="section-label">PHÂN BỔ THEO LĨNH VỰC</p>
        <div class="domain-bars">
          <div v-for="d in stats.domain_stats" :key="d.domain" class="domain-row">
            <span class="domain-name">{{ domainLabel(d.domain) }}</span>
            <div class="bar-track">
              <div class="bar-fill" :style="{ width: (d.chunk_count / maxChunks * 100) + '%' }"></div>
            </div>
            <span class="bar-num">{{ d.chunk_count.toLocaleString() }} chunks</span>
            <span class="bar-docs">{{ d.doc_count }} VB</span>
          </div>
        </div>
      </div>

    </div>

    <!-- ═══════════ TAB: TÀI LIỆU ═══════════ -->
    <div v-if="activeTab === 'documents'" class="tab-content">

      <!-- Upload form -->
      <div class="section-card">
        <p class="section-label">UPLOAD VĂN BẢN MỚI</p>

        <div class="form-row">
          <div class="field">
            <label class="field-label">LĨNH VỰC</label>
            <select v-model="form.domain" class="field-input">
              <option value="giao_thong">Giao thông</option>
              <option value="dat_dai">Đất đai</option>
              <option value="dan_su">Dân sự</option>
              <option value="lao_dong">Lao động</option>
              <option value="hon_nhan">Hôn nhân & Gia đình</option>
              <option value="hinh_su">Hình sự</option>
            </select>
          </div>
          <div class="field">
            <label class="field-label">TÊN VĂN BẢN</label>
            <input v-model="form.lawName" class="field-input" placeholder="Nghị định 100/2019/NĐ-CP" />
          </div>
          <div class="field">
            <label class="field-label">MÃ VĂN BẢN</label>
            <input v-model="form.documentCode" class="field-input" placeholder="100/2019/ND-CP" />
          </div>
          <div class="field">
            <label class="field-label">NGÀY HIỆU LỰC</label>
            <input v-model="form.effectiveDate" type="date" class="field-input" />
          </div>
        </div>

        <!-- Drop zone -->
        <div
          class="drop-zone"
          :class="{ dragging: isDragging, 'has-file': selectedFile }"
          @dragover.prevent="isDragging = true"
          @dragleave="isDragging = false"
          @drop.prevent="handleDrop"
          @click="$refs.fileInput.click()"
        >
          <input ref="fileInput" type="file" accept=".pdf,.docx" style="display:none"
            @change="e => selectedFile = e.target.files[0]" />
          <div v-if="!selectedFile">
            <span class="drop-icon">📄</span>
            <p>Kéo thả file PDF/DOCX vào đây</p>
            <p class="drop-sub">hoặc click để chọn</p>
          </div>
          <div v-else>
            <span class="drop-icon">✅</span>
            <p class="file-name">{{ selectedFile.name }}</p>
            <p class="drop-sub">{{ (selectedFile.size/1024/1024).toFixed(1) }} MB</p>
          </div>
        </div>

        <div class="action-row">
          <button
            class="upload-btn"
            @click="uploadDocument"
            :disabled="!canUpload || uploading"
          >{{ uploading ? 'ĐANG XỬ LÝ...' : '⬆ UPLOAD VÀ INGEST' }}</button>
        </div>
      </div>

      <!-- Progress ingest -->
      <div v-if="uploading || ingestLogs.length" class="section-card">
        <p class="section-label">TIẾN TRÌNH INGEST</p>
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: ingestProgress + '%' }"></div>
        </div>
        <div class="ingest-logs">
          <p v-for="(log, i) in ingestLogs" :key="i" class="log-line" :class="log.type">
            <span class="log-time">{{ log.time }}</span>{{ log.text }}
          </p>
        </div>
      </div>

      <!-- Danh sách tài liệu -->
      <div class="section-card">
        <div class="section-header-row">
          <p class="section-label">
            TÀI LIỆU HIỆN CÓ — {{ documents.length }} văn bản · {{ totalChunks.toLocaleString() }} chunks
          </p>
          <button class="refresh-btn" @click="fetchDocuments" title="Làm mới">↻</button>
        </div>

        <div v-if="!documents.length" class="empty-msg">Chưa có tài liệu nào được ingest.</div>

        <div v-else class="doc-table">
          <div class="doc-row header">
            <span>Tên văn bản</span>
            <span>Lĩnh vực</span>
            <span>Hiệu lực</span>
            <span>Chunks</span>
            <span>Trạng thái</span>
            <span>Thao tác</span>
          </div>
          <div v-for="doc in documents" :key="doc.id" class="doc-row">
            <span class="doc-name" :title="doc.document_code">{{ doc.law_name }}</span>
            <span class="doc-domain">{{ domainLabel(doc.domain) }}</span>
            <span class="doc-date">{{ doc.effective_date || '—' }}</span>
            <span class="doc-chunks">{{ doc.total_chunks }}</span>
            <span :class="doc.expiry_date ? 'status-expired' : 'status-active'">
              {{ doc.expiry_date ? '❌ Hết hiệu lực' : '✅ Đang áp dụng' }}
            </span>
            <div class="doc-actions">
              <button class="action-btn" @click="reIngest(doc)" title="Cập nhật (re-ingest)">↻</button>
              <button class="action-btn danger" @click="deleteDoc(doc)" title="Xóa khỏi hệ thống">🗑</button>
            </div>
          </div>
        </div>
      </div>

    </div>

    <!-- ═══════════ TAB: NGƯỜI DÙNG ═══════════ -->
    <div v-if="activeTab === 'users'" class="tab-content">
      <div class="section-card">
        <p class="section-label">DANH SÁCH NGƯỜI DÙNG ({{ users.length }})</p>

        <div v-if="!users.length" class="empty-msg">Đang tải...</div>
        <div v-else class="doc-table">
          <div class="doc-row user-row header">
            <span>Email</span>
            <span>Role</span>
            <span>Ngày tạo</span>
            <span>Thao tác</span>
          </div>
          <div v-for="u in users" :key="u.id" class="doc-row user-row">
            <span class="doc-name">{{ u.email }}</span>
            <span :class="u.role === 'admin' ? 'role-admin' : 'role-user'">{{ u.role }}</span>
            <span class="doc-date">{{ formatDate(u.created_at) }}</span>
            <div class="doc-actions">
              <button
                class="action-btn"
                :class="u.role === 'admin' ? 'warn' : ''"
                @click="toggleRole(u)"
                :disabled="u.email === authStore.user?.email"
                :title="u.role === 'admin' ? 'Hạ xuống user' : 'Nâng lên admin'"
              >
                {{ u.role === 'admin' ? '↓ User' : '↑ Admin' }}
              </button>
              <button
                class="action-btn danger"
                @click="deleteUser(u)"
                :disabled="u.email === authStore.user?.email"
                title="Xóa tài khoản"
              >🗑 Xóa</button>
            </div>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/plugins/api'
import { useAuthStore } from '@/stores/authStore'

const authStore = useAuthStore()

const activeTab = ref('stats')
const tabs = [
  { id: 'stats',     label: '📊 THỐNG KÊ' },
  { id: 'documents', label: '📁 TÀI LIỆU' },
  { id: 'users',     label: '👥 NGƯỜI DÙNG' },
]

// ─── State ────────────────────────────────────────────────────────────────────
const stats        = ref(null)
const documents    = ref([])
const users        = ref([])
const loadError    = ref(null)   // hiện lỗi nếu fetch thất bại
const selectedFile = ref(null)
const isDragging   = ref(false)
const uploading    = ref(false)
const ingestProgress = ref(0)
const ingestLogs   = ref([])

const form = ref({ domain: 'giao_thong', lawName: '', documentCode: '', effectiveDate: '' })

// ─── Computed ─────────────────────────────────────────────────────────────────
const canUpload = computed(() =>
  selectedFile.value && form.value.lawName && form.value.documentCode && form.value.effectiveDate
)

const totalChunks = computed(() => documents.value.reduce((s, d) => s + d.total_chunks, 0))

const maxChunks = computed(() =>
  Math.max(...(stats.value?.domain_stats.map(d => d.chunk_count) || [1]), 1)
)

// ─── Helpers ──────────────────────────────────────────────────────────────────
const DOMAIN_LABELS = {
  giao_thong: 'Giao thông', dat_dai: 'Đất đai', dan_su: 'Dân sự',
  lao_dong: 'Lao động', hon_nhan: 'Hôn nhân', hinh_su: 'Hình sự',
}
const domainLabel = d => DOMAIN_LABELS[d] || d

function formatDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('vi-VN')
}

function handleDrop(e) {
  isDragging.value = false
  selectedFile.value = e.dataTransfer.files[0]
}

function addLog(text, type = 'info') {
  ingestLogs.value.push({ text, type, time: new Date().toLocaleTimeString('vi-VN') })
}

// ─── API ──────────────────────────────────────────────────────────────────────
async function fetchStats() {
  try {
    const res = await api.get('/api/admin/stats')
    stats.value = res.data
  } catch (e) {
    console.error('Stats error:', e.response?.data || e.message)
    loadError.value = `Stats: ${e.response?.status || e.message}`
    stats.value = { overview: { total_docs: 0, total_chunks: 0, total_users: 0, total_messages: 0 }, domain_stats: [] }
  }
}

async function fetchDocuments() {
  try {
    const res = await api.get('/api/admin/documents')
    documents.value = res.data
  } catch (e) {
    console.error('Documents error:', e)
    documents.value = []
  }
}

async function fetchUsers() {
  try {
    const res = await api.get('/api/admin/users')
    users.value = res.data
  } catch (e) {
    console.error('Users error:', e)
    users.value = []
  }
}

async function uploadDocument() {
  uploading.value = true
  ingestLogs.value = []
  ingestProgress.value = 0

  const fd = new FormData()
  fd.append('file', selectedFile.value)
  fd.append('domain', form.value.domain)
  fd.append('law_name', form.value.lawName)
  fd.append('document_code', form.value.documentCode)
  fd.append('effective_date', form.value.effectiveDate)

  try {
    addLog('Đang upload file...', 'info')
    const res = await api.post('/api/admin/upload-document', fd)
    addLog(`Upload thành công: ${res.data.filename}`, 'success')
    ingestProgress.value = 15
    await pollIngestStatus(res.data.job_id)
    await fetchDocuments()
    await fetchStats()
    selectedFile.value = null
    form.value = { domain: 'giao_thong', lawName: '', documentCode: '', effectiveDate: '' }
  } catch (e) {
    addLog(`Lỗi: ${e.response?.data?.detail || e.message}`, 'error')
  } finally {
    uploading.value = false
  }
}

async function pollIngestStatus(jobId) {
  const steps = [
    [25, 'Extract text từ file...'],
    [40, 'Smart chunking theo Điều/Khoản...'],
    [60, 'Embedding với BAAI/bge-m3 (có thể mất vài phút)...'],
    [80, 'Lưu vectors vào Qdrant...'],
    [90, 'Cập nhật metadata PostgreSQL...'],
  ]
  for (const [pct, msg] of steps) {
    await new Promise(r => setTimeout(r, 2500))
    ingestProgress.value = pct
    addLog(msg, 'info')
  }

  let done = false
  let attempts = 0
  while (!done && attempts < 120) {
    await new Promise(r => setTimeout(r, 3000))
    attempts++
    try {
      const res = await api.get(`/api/admin/ingest-status/${jobId}`)
      if (res.data.status === 'done') {
        ingestProgress.value = 100
        addLog(`✅ Hoàn tất! ${res.data.total_chunks} chunks đã được ingest vào Qdrant + PostgreSQL`, 'success')
        done = true
      } else if (res.data.status === 'error') {
        addLog(`❌ Lỗi ingest: ${res.data.error}`, 'error')
        done = true
      }
    } catch { done = true }
  }
}

async function deleteDoc(doc) {
  if (!confirm(`Xóa "${doc.law_name}"?\n\nThao tác này sẽ xóa toàn bộ chunks khỏi Qdrant và PostgreSQL. Không thể hoàn tác.`)) return
  try {
    await api.delete(`/api/admin/documents/${doc.id}`)
    documents.value = documents.value.filter(d => d.id !== doc.id)
    await fetchStats()
    addLog(`Đã xóa: ${doc.law_name}`, 'success')
  } catch (e) {
    alert('Lỗi khi xóa: ' + (e.response?.data?.detail || e.message))
  }
}

async function reIngest(doc) {
  if (!confirm(`Re-ingest "${doc.law_name}"?\n\nSẽ xóa chunks cũ và tạo lại từ đầu.`)) return
  ingestLogs.value = []
  ingestProgress.value = 0
  uploading.value = true
  addLog(`Bắt đầu re-ingest: ${doc.law_name}`, 'info')
  try {
    const res = await api.post('/api/admin/re-ingest', { document_id: doc.id })
    ingestProgress.value = 15
    await pollIngestStatus(res.data.job_id)
    await fetchDocuments()
    await fetchStats()
  } catch (e) {
    addLog(`Lỗi: ${e.response?.data?.detail || e.message}`, 'error')
  } finally {
    uploading.value = false
  }
}

async function toggleRole(user) {
  const newRole = user.role === 'admin' ? 'user' : 'admin'
  if (!confirm(`Đổi role của ${user.email} từ "${user.role}" thành "${newRole}"?`)) return
  try {
    await api.patch(`/api/admin/users/${user.id}/role`, { role: newRole })
    await fetchUsers()
  } catch (e) {
    alert('Lỗi: ' + (e.response?.data?.detail || e.message))
  }
}

async function deleteUser(user) {
  if (!confirm(`Xóa tài khoản "${user.email}"?\n\nTất cả dữ liệu của người dùng này sẽ bị xóa. Không thể hoàn tác.`)) return
  try {
    await api.delete(`/api/admin/users/${user.id}`)
    users.value = users.value.filter(u => u.id !== user.id)
  } catch (e) {
    alert('Lỗi: ' + (e.response?.data?.detail || e.message))
  }
}

onMounted(async () => {
  await Promise.allSettled([fetchStats(), fetchDocuments(), fetchUsers()])
})
</script>

<style scoped>
/* ══ Base ══ */
.admin-page {
  padding: 36px 48px;
  background: #F5F6FA;
  min-height: 100vh;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  max-width: 1280px;
  margin: 0 auto;
  -webkit-font-smoothing: antialiased;
}

/* ══ Header ══ */
.admin-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 32px;
  padding-bottom: 24px;
  border-bottom: 2px solid #E8E8EC;
}
.admin-title {
  font-family: 'Playfair Display', Georgia, serif;
  font-size: 30px;
  font-weight: 700;
  color: #111827;
  margin: 0 0 5px;
  letter-spacing: -0.3px;
}
.admin-sub {
  font-size: 13.5px;
  color: #6B7280;
  margin: 0;
  font-weight: 400;
}

/* ══ Tabs ══ */
.tab-group {
  display: flex;
  gap: 4px;
  background: #EBEBF0;
  padding: 4px;
  border-radius: 10px;
}
.tab-btn {
  padding: 9px 20px;
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0.01em;
  border: none;
  background: transparent;
  color: #6B7280;
  cursor: pointer;
  font-family: 'Inter', sans-serif;
  border-radius: 7px;
  transition: all .18s;
}
.tab-btn.active {
  background: #ffffff;
  color: #111827;
  box-shadow: 0 1px 4px rgba(0,0,0,0.1);
  font-weight: 600;
}
.tab-btn:hover:not(.active) { color: #374151; background: rgba(255,255,255,0.5); }

/* ══ Layout ══ */
.tab-content { display: flex; flex-direction: column; gap: 20px; }

.section-card {
  background: #ffffff;
  border: 1px solid #E5E7EB;
  border-radius: 12px;
  padding: 28px 32px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.section-label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: #9CA3AF;
  margin: 0 0 20px;
  text-transform: uppercase;
}
.section-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.refresh-btn {
  background: none;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  cursor: pointer;
  padding: 6px 12px;
  font-size: 15px;
  color: #6B7280;
  transition: all .15s;
  line-height: 1;
}
.refresh-btn:hover { border-color: #B8860B; color: #B8860B; }

.loading-msg, .empty-msg {
  text-align: center;
  color: #9CA3AF;
  font-size: 14px;
  padding: 40px 0;
}

/* ══ Stats Cards ══ */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}
.stat-card {
  background: #ffffff;
  border: 1px solid #E5E7EB;
  border-radius: 12px;
  padding: 24px 28px;
  text-align: center;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  transition: box-shadow .2s;
}
.stat-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
.stat-label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: #9CA3AF;
  margin: 0 0 12px;
  text-transform: uppercase;
}
.stat-value {
  font-family: 'Playfair Display', serif;
  font-size: 40px;
  font-weight: 700;
  color: #111827;
  margin: 0;
  line-height: 1;
}

/* ══ Domain Bars ══ */
.domain-bars { display: flex; flex-direction: column; gap: 16px; }
.domain-row {
  display: flex;
  align-items: center;
  gap: 16px;
}
.domain-name {
  width: 140px;
  font-size: 13.5px;
  font-weight: 500;
  color: #374151;
  flex-shrink: 0;
}
.bar-track {
  flex: 1;
  height: 8px;
  background: #F3F4F6;
  border-radius: 4px;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #B8860B, #D4A017);
  border-radius: 4px;
  transition: width 1s ease;
}
.bar-num {
  font-size: 13px;
  font-weight: 600;
  color: #1F2937;
  min-width: 110px;
  text-align: right;
}
.bar-docs {
  font-size: 12px;
  color: #9CA3AF;
  min-width: 50px;
}

/* ══ Form ══ */
.form-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
  margin-bottom: 24px;
}
.field-label {
  display: block;
  font-size: 11.5px;
  font-weight: 600;
  letter-spacing: 0.06em;
  color: #6B7280;
  margin-bottom: 8px;
  text-transform: uppercase;
}
.field-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #D1D5DB;
  border-radius: 8px;
  background: #F9FAFB;
  font-family: 'Inter', sans-serif;
  font-size: 14px;
  color: #111827;
  outline: none;
  box-sizing: border-box;
  transition: border-color .2s, box-shadow .2s;
}
.field-input:focus {
  border-color: #B8860B;
  box-shadow: 0 0 0 3px rgba(184,134,11,0.1);
  background: #ffffff;
}

/* ══ Drop Zone ══ */
.drop-zone {
  border: 2px dashed #D1D5DB;
  border-radius: 10px;
  padding: 44px 24px;
  text-align: center;
  cursor: pointer;
  margin-bottom: 20px;
  transition: all .2s;
  font-size: 14px;
  color: #6B7280;
  line-height: 1.9;
}
.drop-zone:hover, .drop-zone.dragging {
  border-color: #B8860B;
  background: rgba(184,134,11,0.03);
}
.drop-zone.has-file {
  border-color: #10B981;
  border-style: solid;
  background: rgba(16,185,129,0.04);
}
.drop-icon { font-size: 32px; display: block; margin-bottom: 8px; }
.drop-sub { font-size: 12px; color: #9CA3AF; margin: 4px 0 0; }
.file-name { font-size: 15px; font-weight: 600; color: #111827; }

/* ══ Action Row ══ */
.action-row { display: flex; gap: 12px; }
.upload-btn {
  flex: 1;
  padding: 14px;
  background: #111827;
  border: none;
  border-radius: 8px;
  color: #F9FAFB;
  font-family: 'Inter', sans-serif;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.06em;
  cursor: pointer;
  transition: background .2s, transform .1s;
}
.upload-btn:hover:not(:disabled) { background: #B8860B; }
.upload-btn:active:not(:disabled) { transform: scale(0.99); }
.upload-btn:disabled { opacity: 0.35; cursor: not-allowed; }

/* ══ Progress ══ */
.progress-bar {
  height: 5px;
  background: #F3F4F6;
  border-radius: 3px;
  margin-bottom: 16px;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #B8860B, #D4A017);
  border-radius: 3px;
  transition: width .6s ease;
}
.ingest-logs {
  background: #0F172A;
  padding: 16px 18px;
  height: 170px;
  overflow-y: auto;
  border-radius: 8px;
  font-family: 'IBM Plex Mono', 'Fira Code', monospace;
}
.log-line {
  font-size: 12px;
  display: flex;
  gap: 14px;
  margin: 5px 0;
  line-height: 1.6;
}
.log-time { color: #475569; min-width: 72px; flex-shrink: 0; }
.log-line.info    { color: #60A5FA; }
.log-line.success { color: #34D399; }
.log-line.error   { color: #F87171; }

/* ══ Doc Table ══ */
.doc-table { display: flex; flex-direction: column; }
.doc-row {
  display: grid;
  grid-template-columns: 3fr 1.2fr 1.2fr 0.8fr 1.5fr auto;
  gap: 14px;
  padding: 13px 4px;
  border-bottom: 1px solid #F3F4F6;
  align-items: center;
  font-size: 13.5px;
}
.doc-row.header {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: #9CA3AF;
  padding-bottom: 10px;
  border-bottom: 1px solid #E5E7EB;
  text-transform: uppercase;
}
.doc-row:last-child { border-bottom: none; }
.doc-name {
  font-weight: 500;
  color: #111827;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 13.5px;
}
.doc-domain { color: #B8860B; font-weight: 500; }
.doc-date { color: #6B7280; }
.doc-chunks { font-weight: 600; color: #1F2937; }
.status-active  {
  color: #059669;
  font-weight: 500;
  font-size: 12.5px;
}
.status-expired {
  color: #DC2626;
  font-weight: 500;
  font-size: 12.5px;
}
.doc-actions { display: flex; gap: 6px; }
.action-btn {
  font-size: 12px;
  font-weight: 500;
  padding: 5px 11px;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  background: #F9FAFB;
  cursor: pointer;
  font-family: 'Inter', sans-serif;
  color: #374151;
  transition: all .15s;
  white-space: nowrap;
}
.action-btn:hover:not(:disabled) {
  border-color: #B8860B;
  color: #B8860B;
  background: rgba(184,134,11,0.05);
}
.action-btn.danger:hover:not(:disabled) {
  border-color: #DC2626;
  color: #DC2626;
  background: rgba(220,38,38,0.05);
}
.action-btn:disabled { opacity: 0.3; cursor: not-allowed; }
.action-btn.warn:hover:not(:disabled) {
  border-color: #D97706;
  color: #D97706;
  background: rgba(217,119,6,0.05);
}

/* ══ User Table ══ */
.doc-row.user-row {
  grid-template-columns: 3fr 1fr 1.2fr auto;
}

/* ══ Role Badges ══ */
.role-admin {
  display: inline-flex;
  align-items: center;
  background: rgba(184,134,11,0.1);
  color: #92680A;
  font-weight: 700;
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 20px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.role-user {
  display: inline-flex;
  align-items: center;
  background: #F3F4F6;
  color: #6B7280;
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 20px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
</style>

