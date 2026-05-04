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
.admin-page {
  padding: 32px 40px;
  background: #FAFAF8;
  min-height: 100vh;
  font-family: 'IBM Plex Mono', monospace;
  max-width: 1200px;
  margin: 0 auto;
}

/* ─ Header ─ */
.admin-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 28px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e8e4dc;
}
.admin-title {
  font-family: 'Playfair Display', serif;
  font-size: 26px;
  color: #1a1a1a;
  margin: 0 0 4px;
}
.admin-sub { font-size: 11px; color: #999; margin: 0; }

/* ─ Tabs ─ */
.tab-group { display: flex; }
.tab-btn {
  padding: 8px 20px;
  font-size: 11px;
  letter-spacing: 0.12em;
  border: 1px solid #ddd;
  background: transparent;
  color: #888;
  cursor: pointer;
  font-family: 'IBM Plex Mono', monospace;
  margin-left: -1px;
  transition: all .15s;
}
.tab-btn.active { background: #1a1a1a; color: #FAFAF8; border-color: #1a1a1a; z-index: 1; }
.tab-btn:hover:not(.active) { border-color: #B8860B; color: #B8860B; }

/* ─ Common ─ */
.tab-content { display: flex; flex-direction: column; gap: 16px; }

.section-card {
  background: white;
  border: 1px solid #eee;
  padding: 24px;
}
.section-label {
  font-size: 10px;
  letter-spacing: 0.2em;
  color: #aaa;
  margin: 0 0 18px;
  text-transform: uppercase;
}
.section-header-row { display: flex; justify-content: space-between; align-items: center; }
.refresh-btn {
  background: none; border: 1px solid #ddd; cursor: pointer;
  padding: 4px 10px; font-size: 14px; color: #888; transition: all .15s;
}
.refresh-btn:hover { border-color: #B8860B; color: #B8860B; }

.loading-msg, .empty-msg { text-align: center; color: #aaa; font-size: 13px; padding: 32px 0; }

/* ─ Stats ─ */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}
.stat-card {
  background: white;
  border: 1px solid #eee;
  padding: 20px 24px;
  text-align: center;
}
.stat-label { font-size: 10px; letter-spacing: 0.15em; color: #aaa; margin: 0 0 10px; }
.stat-value { font-family: 'Playfair Display', serif; font-size: 36px; color: #1a1a1a; margin: 0; }

/* ─ Domain bars ─ */
.domain-bars { display: flex; flex-direction: column; gap: 14px; }
.domain-row { display: flex; align-items: center; gap: 14px; }
.domain-name { width: 130px; font-size: 12px; color: #666; flex-shrink: 0; }
.bar-track { flex: 1; height: 6px; background: #f0ede8; border-radius: 3px; overflow: hidden; }
.bar-fill { height: 100%; background: #B8860B; border-radius: 3px; transition: width 1s ease; }
.bar-num { font-size: 12px; color: #333; min-width: 100px; font-weight: 500; }
.bar-docs { font-size: 11px; color: #bbb; min-width: 50px; }

/* ─ Form ─ */
.form-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 20px;
}
.field-label { display: block; font-size: 10px; letter-spacing: 0.15em; color: #aaa; margin-bottom: 6px; }
.field-input {
  width: 100%;
  padding: 8px 0;
  border: none;
  border-bottom: 1px solid #ddd;
  background: transparent;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 13px;
  outline: none;
  box-sizing: border-box;
  transition: border-color .2s;
}
.field-input:focus { border-bottom-color: #B8860B; }

/* ─ Drop zone ─ */
.drop-zone {
  border: 2px dashed #ddd;
  padding: 36px 20px;
  text-align: center;
  cursor: pointer;
  margin-bottom: 16px;
  transition: all .2s;
  font-size: 13px;
  color: #888;
  line-height: 1.8;
}
.drop-zone:hover, .drop-zone.dragging { border-color: #B8860B; background: #fffbf0; }
.drop-zone.has-file { border-color: #27ae60; border-style: solid; background: #f0fff4; }
.drop-icon { font-size: 28px; display: block; margin-bottom: 6px; }
.drop-sub { font-size: 11px; color: #bbb; margin: 2px 0 0; }
.file-name { font-size: 14px; font-weight: 600; color: #1a1a1a; }

/* ─ Action buttons ─ */
.action-row { display: flex; gap: 12px; }
.upload-btn {
  flex: 1;
  padding: 13px;
  background: #1a1a1a;
  border: none;
  color: #FAFAF8;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 11px;
  letter-spacing: 0.2em;
  cursor: pointer;
  transition: background .2s;
}
.upload-btn:hover:not(:disabled) { background: #B8860B; }
.upload-btn:disabled { opacity: 0.4; cursor: not-allowed; }

/* ─ Progress ─ */
.progress-bar { height: 4px; background: #eee; margin-bottom: 14px; }
.progress-fill { height: 100%; background: #B8860B; transition: width .6s ease; }
.ingest-logs { background: #111; padding: 12px 16px; height: 160px; overflow-y: auto; border-radius: 2px; }
.log-line { font-size: 11px; display: flex; gap: 12px; margin: 4px 0; line-height: 1.5; }
.log-time { color: #444; min-width: 72px; flex-shrink: 0; }
.log-line.info    { color: #6c8ebf; }
.log-line.success { color: #82b366; }
.log-line.error   { color: #e06c75; }

/* ─ Doc table ─ */
.doc-table { display: flex; flex-direction: column; }
.doc-row {
  display: grid;
  grid-template-columns: 3fr 1.2fr 1.2fr 0.8fr 1.5fr auto;
  gap: 12px;
  padding: 11px 0;
  border-bottom: 1px solid #f5f5f5;
  align-items: center;
  font-size: 12px;
}
.doc-row.header {
  font-size: 10px;
  letter-spacing: 0.1em;
  color: #bbb;
  padding-bottom: 8px;
  border-bottom: 1px solid #eee;
}
.doc-name { font-weight: 500; color: #1a1a1a; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.doc-domain { color: #B8860B; }
.doc-date { color: #888; }
.doc-chunks { font-weight: 500; }
.status-active  { color: #27ae60; }
.status-expired { color: #c0392b; }
.doc-actions { display: flex; gap: 6px; }
.action-btn {
  font-size: 11px;
  padding: 4px 9px;
  border: 1px solid #ddd;
  background: transparent;
  cursor: pointer;
  font-family: 'IBM Plex Mono', monospace;
  transition: all .15s;
  white-space: nowrap;
}
.action-btn:hover:not(:disabled) { border-color: #B8860B; color: #B8860B; }
.action-btn.danger:hover:not(:disabled) { border-color: #c0392b; color: #c0392b; }
.action-btn:disabled { opacity: 0.3; cursor: not-allowed; }

/* ─ Role badges ─ */
.doc-row.user-row {
  grid-template-columns: 3fr 1fr 1.2fr auto;
}

.action-btn.warn:hover:not(:disabled) { border-color: #e67e22; color: #e67e22; }

/* ─ Role badges ─ */
.role-admin { color: #B8860B; font-weight: 700; letter-spacing: 0.05em; }
.role-user  { color: #aaa; }
</style>
