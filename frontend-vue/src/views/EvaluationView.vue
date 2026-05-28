<template>
  <div class="eval-page">

    <!-- Header -->
    <div class="eval-header">
      <div>
        <h2 class="eval-title">Evaluation Dashboard</h2>
        <p class="eval-sub">
          Đánh giá định lượng khả năng chống hallucination
          <span v-if="result" style="margin-left:8px;opacity:.6;font-size:11px">
            · {{ useRagas ? 'RAGAS Official (Es et al. 2023)' : 'LLM Judge' }} · {{ result?.summary?.total ?? result?.summary?.total_cases }} cases
          </span>
        </p>
      </div>
      <div style="display:flex;align-items:center;gap:12px">
        <!-- Mode toggle -->
        <div class="mode-toggle">
          <button
            class="mode-btn" :class="{ active: !useRagas }"
            @click="useRagas = false" :disabled="loading"
          >LLM Judge</button>
          <button
            class="mode-btn ragas-btn" :class="{ active: useRagas }"
            @click="useRagas = true" :disabled="loading"
          >RAGAS</button>
        </div>

        <!-- So test cases -->
        <div class="count-selector">
          <label class="count-label">Test cases</label>
          <select v-model="testCount" class="count-select" :disabled="loading">
            <option :value="4">4 · nhanh nhất ({{ useRagas ? '~5 phút' : '~20s' }})</option>
            <option :value="8">8 · cân bằng ({{ useRagas ? '~10 phút' : '~40s' }})</option>
            <option v-if="!useRagas" :value="12">12 · đầy đủ hơn (~60s)</option>
            <option :value="20">20 · toàn bộ ({{ useRagas ? '~30 phút' : '~90s' }})</option>
          </select>
        </div>
        <button class="run-btn" @click="runEvaluation" :disabled="loading">
          {{ loading ? 'ĐANG CHẠY...' : (useRagas ? 'CHẠY RAGAS' : 'CHẠY ĐÁNH GIÁ') }}
        </button>
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="loading-state">
      <div class="loading-bar">
        <div class="loading-fill" :style="{ width: progress + '%' }"></div>
      </div>
      <p class="loading-text">
        <span v-if="!useRagas">{{'Đang chạy'}} {{ currentTest }}/{{ totalTests }} test cases...</span>
        <span v-else-if="ragasPhase === 'collecting'">
          📥 Thu thập dữ liệu: {{ ragasDone }}/{{ totalTests }} cases xong...
        </span>
        <span v-else-if="ragasPhase === 'evaluating'">
          ⚖️ RAGAS đang chấm điểm {{ totalTests }} cases... (có thể mất 2-5 phút)
        </span>
      </p>
      <!-- Live case list (RAGAS mode) -->
      <div v-if="useRagas && ragasDoneCases.length" class="ragas-live-list">
        <div v-for="c in ragasDoneCases" :key="c.index" class="ragas-live-item">
          <span class="live-index">#{{ c.index }}</span>
          <span class="live-badge" :class="'type-' + c.type">{{ typeLabel(c.type) }}</span>
          <span class="live-q">{{ c.question }}</span>
          <span class="live-check">✔</span>
        </div>
      </div>
    </div>

    <!-- Summary cards -->
    <div v-if="result" class="summary-grid">
      <div class="metric-card">
        <p class="metric-label">FAITHFULNESS</p>
        <p class="metric-value" :class="scoreClass(result.summary.avg_faithfulness)">
          {{ pct(result.summary.avg_faithfulness) }}
        </p>
        <p class="metric-desc">Câu trả lời bám vào nguồn</p>
      </div>
      <div class="metric-card">
        <p class="metric-label">HALLUCINATION RATE</p>
        <p class="metric-value text-danger">
          {{ pct(result.summary.hallucination_rate) }}
        </p>
        <p class="metric-desc">Tỷ lệ câu trả lời bịa</p>
      </div>
      <div class="metric-card">
        <p class="metric-label">ANSWER RELEVANCY</p>
        <p class="metric-value" :class="scoreClass(result.summary.avg_answer_relevancy)">
          {{ pct(result.summary.avg_answer_relevancy) }}
        </p>
        <p class="metric-desc">Độ liên quan câu trả lời</p>
      </div>
      <div class="metric-card">
        <p class="metric-label">CONTEXT PRECISION</p>
        <p class="metric-value" :class="scoreClass(result.summary.avg_context_precision)">
          {{ pct(result.summary.avg_context_precision) }}
        </p>
        <p class="metric-desc">Độ chính xác context</p>
      </div>
      <div class="metric-card">
        <p class="metric-label">CONTEXT RELEVANCE</p>
        <p class="metric-value" :class="scoreClass(result.summary.avg_context_relevance)">
          {{ pct(result.summary.avg_context_relevance) }}
        </p>
        <p class="metric-desc">Context có liên quan câu hỏi</p>
      </div>
      <div class="metric-card">
        <p class="metric-label">OUT-OF-DOMAIN</p>
        <p class="metric-value" :class="scoreClass(result.summary.out_of_domain_accuracy)">
          {{ pct(result.summary.out_of_domain_accuracy) }}
        </p>
        <p class="metric-desc">Từ chối đúng câu ngoài domain</p>
      </div>
      <div class="metric-card">
        <p class="metric-label">PASSED / FAILED</p>
        <p class="metric-value">
          <span class="text-success">{{ result.summary.passed }}</span>
          <span style="color: #ccc"> / </span>
          <span class="text-danger">{{ result.summary.failed }}</span>
        </p>
        <p class="metric-desc">Trên {{ result.summary.total }} test cases</p>
      </div>
    </div>

    <!-- Bar chart by type -->
    <div v-if="result" class="chart-section">
      <p class="section-title">FAITHFULNESS THEO LOẠI CÂU HỎI</p>
      <div class="bar-chart">
        <div v-for="(data, type) in result.by_type" :key="type" class="bar-row">
          <span class="bar-label">{{ typeLabel(type) }}</span>
          <div class="bar-track">
            <div class="bar-fill" :style="{
              width: (data.avg_faithfulness * 100) + '%',
              background: barColor(data.avg_faithfulness)
            }"></div>
          </div>
          <span class="bar-value">{{ pct(data.avg_faithfulness) }}</span>
        </div>
      </div>
    </div>

    <!-- Detail table -->
    <div v-if="result" class="detail-section">
      <div class="detail-header">
        <p class="section-title">CHI TIẾT {{ filteredResults.length }} TEST CASES</p>
        <div class="filter-group">
          <button v-for="f in filters" :key="f.value" class="filter-btn" :class="{ active: activeFilter === f.value }"
            @click="activeFilter = f.value">{{ f.label }}</button>
        </div>
      </div>

      <div class="result-list">
        <div v-for="r in filteredResults" :key="r.id" class="result-item" :class="{ failed: r.is_hallucinated }"
          @click="expandedId = expandedId === r.id ? null : r.id">
          <div class="result-row">
            <span class="result-id">{{ r.id }}</span>
            <span class="result-type-badge" :class="'type-' + r.type">
              {{ typeLabel(r.type) }}
            </span>
            <span class="result-question">{{ r.question }}</span>
            <div class="result-scores">
              <span class="score-pill" :class="scoreClass(r.faithfulness)">
                F: {{ r.faithfulness?.toFixed(2) ?? 'N/A' }}
              </span>
              <span class="verdict-pill" :class="r.is_hallucinated ? 'verdict-fail' : 'verdict-pass'">
                {{ r.is_hallucinated ? 'FAIL' : 'PASS' }}
              </span>
            </div>
          </div>

          <!-- Expanded detail -->
          <div v-if="expandedId === r.id" class="result-detail">
            <div class="detail-col">
              <p class="detail-label">CÂU HỎI</p>
              <p class="detail-text">{{ r.question }}</p>
            </div>
            <div class="detail-col">
              <p class="detail-label">ĐÁP ÁN CHUẨN</p>
              <p class="detail-text ground-truth">{{ r.ground_truth }}</p>
            </div>
            <div class="detail-col">
              <p class="detail-label">CÂU TRẢ LỜI GENERATED</p>
              <p class="detail-text generated">{{ r.generated_answer }}</p>
            </div>
            <div class="detail-scores">
              <div class="dscore">
                <span>Faithfulness</span>
                <strong :class="scoreClass(r.faithfulness)">{{ r.faithfulness?.toFixed(3) ?? 'N/A' }}</strong>
              </div>
              <div class="dscore">
                <span>Relevancy</span>
                <strong :class="scoreClass(r.answer_relevancy)">{{ r.answer_relevancy?.toFixed(3) ?? 'N/A' }}</strong>
              </div>
              <div class="dscore">
                <span>Precision</span>
                <strong :class="scoreClass(r.context_precision)">{{ r.context_precision?.toFixed(3) ?? 'N/A' }}</strong>
              </div>
              <div class="dscore">
                <span>Recall</span>
                <strong :class="scoreClass(r.context_recall)">{{ r.context_recall?.toFixed(3) ?? 'N/A' }}</strong>
              </div>
              <div v-if="r.has_conflict" class="dscore">
                <span>Conflict</span>
                <strong class="text-danger">⚠ Phát hiện</strong>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="!loading && !result" class="empty-eval">
      <div class="empty-icon">⚖</div>
      <p class="empty-title">Chưa có dữ liệu đánh giá</p>
      <p class="empty-sub">Nhấn "CHẠY ĐÁNH GIÁ" để bắt đầu kiểm tra {{ testCount }} test cases</p>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import api from '@/plugins/api'
const loading    = ref(false)
const result     = ref(null)
const expandedId = ref(null)
const activeFilter = ref('all')
const progress   = ref(0)
const currentTest = ref(0)
const totalTests  = ref(8)
const testCount   = ref(8)
const useRagas    = ref(false)
// RAGAS job state
const ragasPhase     = ref('collecting')   // collecting | evaluating
const ragasDone      = ref(0)
const ragasDoneCases = ref([])
watch(testCount, v => { totalTests.value = v })

onMounted(() => {
  const savedJobId = localStorage.getItem('ragas_job_id')
  if (savedJobId) {
    const total = localStorage.getItem('ragas_total')
    if (total) {
      testCount.value = parseInt(total, 10)
      totalTests.value = parseInt(total, 10)
    }
    useRagas.value = true
    resumeRagas(savedJobId)
  }
})

async function resumeRagas(jobId) {
  loading.value = true
  ragasPhase.value = 'collecting'
  ragasDone.value = 0
  ragasDoneCases.value = []
  progress.value = 0
  await pollRagas(jobId)
}

const filters = [
  { label: 'Tất cả', value: 'all' },
  { label: 'Factual', value: 'factual' },
  { label: 'Temporal', value: 'temporal' },
  { label: 'Conflict', value: 'conflict' },
  { label: 'Out of domain', value: 'out_of_domain' },
  { label: 'Chỉ FAIL', value: 'failed' },
]

const filteredResults = computed(() => {
  if (!result.value) return []
  const all = result.value.results
  if (activeFilter.value === 'all') return all
  if (activeFilter.value === 'failed') return all.filter(r => r.is_hallucinated)
  return all.filter(r => r.type === activeFilter.value)
})

async function runEvaluation() {
  loading.value = true
  result.value  = null
  progress.value = 0
  currentTest.value = 0
  totalTests.value  = testCount.value

  if (useRagas.value) {
    await runRagas()
  } else {
    await runLlmJudge()
  }
}

async function runLlmJudge() {
  const tickMs = 1200
  const interval = setInterval(() => {
    if (currentTest.value < totalTests.value - 1) {
      currentTest.value++
      progress.value = Math.round((currentTest.value / totalTests.value) * 85)
    }
  }, tickMs)
  try {
    const res = await api.post(`/api/ai/evaluate?count=${testCount.value}`, {}, { timeout: 180000 })
    result.value = res.data
  } catch (e) {
    handleError(e)
  } finally {
    clearInterval(interval)
    progress.value = 100
    currentTest.value = totalTests.value
    loading.value = false
  }
}

async function runRagas() {
  ragasPhase.value     = 'collecting'
  ragasDone.value      = 0
  ragasDoneCases.value = []
  progress.value       = 0

  let jobId
  try {
    const startRes = await api.post(`/api/ai/evaluate/ragas?count=${testCount.value}`, {}, { timeout: 10000 })
    console.log('[RAGAS] startRes.data =', JSON.stringify(startRes.data))
    // FastAPI returns {job_id, total} — handle both snake_case and possible wrapper
    const d = startRes.data
    jobId = d?.job_id ?? d?.jobId ?? d?.data?.job_id
    totalTests.value = d?.total ?? d?.data?.total ?? testCount.value
    console.log('[RAGAS] jobId =', jobId, '| total =', totalTests.value)
    if (!jobId) {
      alert('❌ Không nhận được job_id từ server. Response: ' + JSON.stringify(d))
      loading.value = false
      return
    }
    // Persist so Vite HMR reload doesn't lose it
    localStorage.setItem('ragas_job_id', jobId)
    localStorage.setItem('ragas_total', String(totalTests.value))
  } catch (e) {
    handleError(e)
    loading.value = false
    return
  }

  await pollRagas(jobId)
}

async function pollRagas(jobId) {
  // Poll every 3s
  const maxWait = 40 * 60 * 1000   // 40 phút max
  const started = Date.now()
  while (true) {
    await new Promise(r => setTimeout(r, 3000))
    if (Date.now() - started > maxWait) {
      alert('⏱ RAGAS đã chạy quá 40 phút. Kiểm tra lại kết nối hoặc giảm số test cases.')
      localStorage.removeItem('ragas_job_id')
      localStorage.removeItem('ragas_total')
      break
    }
    let status
    try {
      const statusRes = await api.get(`/api/ai/evaluate/ragas/status/${jobId}`)
      status = statusRes.data
    } catch { continue }

    // Job đã bị xóa khỏi server (FastAPI restart) → dừng vòng lặp
    if (status?.error === 'Job not found') {
      alert('⚠️ Job RAGAS không còn tồn tại trên server (server đã restart). Vui lòng chạy lại.')
      localStorage.removeItem('ragas_job_id')
      localStorage.removeItem('ragas_total')
      loading.value = false
      break
    }

    ragasPhase.value     = status.status
    ragasDone.value      = status.rag_done ?? 0
    ragasDoneCases.value = status.done_cases ?? []

    // Progress: phase 1 = 0-60%, phase 2 = 60-95%
    if (status.status === 'collecting') {
      progress.value = Math.round((ragasDone.value / totalTests.value) * 60)
    } else if (status.status === 'evaluating') {
      progress.value = 60 + Math.min(30, (Date.now() - started) / 10000)
    } else if (status.status === 'done') {
      progress.value = 100
      // Normalize RAGAS result
      const r = status.result
      result.value = {
        summary: {
          ...r.summary,
          total: r.summary.total_cases,
        },
        by_type: {},
        results: r.per_sample.map((s, i) => ({
          id: `R${String(i + 1).padStart(3, '0')}`,
          type: ragasDoneCases.value[i]?.type ?? 'factual',
          question: s.question,
          ground_truth: s.ground_truth,
          generated_answer: s.answer,
          faithfulness: s.faithfulness,
          answer_relevancy: s.answer_relevancy,
          context_precision: s.context_precision,
          context_recall: s.context_recall,
          is_hallucinated: s.faithfulness < 0.5,
          has_conflict: false,
        }))
      }
      localStorage.removeItem('ragas_job_id')
      localStorage.removeItem('ragas_total')
      break
    } else if (status.status === 'error') {
      alert(`❌ RAGAS gặp lỗi: ${status.error}\n\nGợi ý: Có thể do Groq rate-limit. Chờ 60s rồi thử lại.`)
      localStorage.removeItem('ragas_job_id')
      localStorage.removeItem('ragas_total')
      break
    }
  }
  loading.value = false
}

function handleError(e) {
  const status = e.response?.status
  let msg = ''
  if (e.code === 'ECONNABORTED' || e.message?.includes('timeout')) {
    msg = '⏱ Timeout. Thử giảm số test cases.'
  } else if (status === 401 || status === 403) {
    msg = '🔐 Phiên đăng nhập hết hạn.'
    setTimeout(() => { window.location.href = '/login' }, 2000)
  } else if (status === 503) {
    msg = '⚠️ FastAPI không phản hồi. Kiểm tra FastAPI :8000.'
  } else if (!e.response) {
    msg = '🔌 Không kết nối được server. Kiểm tra Spring Boot :8081.'
  } else {
    msg = `Lỗi ${status}: ${e.response?.data?.detail || e.message}`
  }
  alert(msg)
}

function pct(val) {
  if (val == null) return 'N/A'
  return Math.round(val * 100) + '%'
}

function scoreClass(val) {
  if (val == null) return ''
  if (val >= 0.8) return 'text-success'
  if (val >= 0.6) return 'text-warning'
  return 'text-danger'
}

function barColor(val) {
  if (val >= 0.8) return '#27ae60'
  if (val >= 0.6) return '#B8860B'
  return '#c0392b'
}

function typeLabel(type) {
  const map = {
    factual: 'Factual',
    temporal: 'Temporal',
    conflict: 'Conflict',
    out_of_domain: 'Out of domain',
  }
  return map[type] ?? type
}
</script>

<style scoped>
.eval-page {
  padding: 32px;
  background: #FAFAF8;
  min-height: 100vh;
  font-family: 'IBM Plex Mono', monospace;
}

.eval-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 32px;
}

.eval-title {
  font-family: 'Playfair Display', serif;
  font-size: 28px;
  color: #1a1a1a;
  margin: 0 0 4px;
}

.eval-sub {
  font-size: 12px;
  color: #888;
  margin: 0;
  letter-spacing: 0.05em;
}

.run-btn {
  padding: 12px 24px;
  background: #1a1a1a;
  color: #FAFAF8;
  border: none;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 11px;
  letter-spacing: 0.15em;
  cursor: pointer;
  transition: background 0.2s;
}

.run-btn:hover:not(:disabled) {
  background: #B8860B;
}

.run-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Mode toggle */
.mode-toggle {
  display: flex;
  border: 1px solid #ddd;
  overflow: hidden;
}

.mode-btn {
  padding: 8px 14px;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 10px;
  letter-spacing: 0.1em;
  border: none;
  background: white;
  color: #888;
  cursor: pointer;
  transition: all 0.15s;
}

.mode-btn:hover:not(:disabled) { background: #f5f5f5; color: #1a1a1a; }
.mode-btn.active { background: #1a1a1a; color: white; }
.mode-btn.ragas-btn.active { background: #7c3aed; color: white; }
.mode-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* Count selector */
.count-selector {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.count-label {
  font-size: 9px;
  letter-spacing: 0.12em;
  color: #aaa;
  text-transform: uppercase;
}

.count-select {
  padding: 8px 12px;
  background: white;
  border: 1px solid #ddd;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 11px;
  color: #1a1a1a;
  cursor: pointer;
  outline: none;
  transition: border-color 0.2s;
}

.count-select:hover:not(:disabled) { border-color: #B8860B; }
.count-select:focus { border-color: #1a1a1a; }
.count-select:disabled { opacity: 0.5; cursor: not-allowed; }


/* Loading */
.loading-state {
  margin-bottom: 32px;
  padding: 24px;
  background: white;
  border: 1px solid #eee;
}

.loading-bar {
  height: 4px;
  background: #eee;
  margin-bottom: 12px;
}

.loading-fill {
  height: 100%;
  background: #B8860B;
  transition: width 0.5s ease;
}

.loading-text {
  font-size: 12px;
  color: #888;
  margin: 0 0 16px;
}

/* RAGAS live case list */
.ragas-live-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 12px;
  border-top: 1px solid #f0ede8;
  padding-top: 12px;
}

.ragas-live-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 8px;
  background: #f9f9f7;
  border: 1px solid #eee;
  border-left: 3px solid #27ae60;
  animation: slideIn 0.3s ease;
}

@keyframes slideIn {
  from { opacity: 0; transform: translateY(-4px); }
  to   { opacity: 1; transform: translateY(0); }
}

.live-index {
  font-size: 10px;
  color: #B8860B;
  font-weight: 600;
  min-width: 24px;
}

.live-badge {
  font-size: 9px;
  padding: 2px 6px;
  flex-shrink: 0;
}

.live-q {
  flex: 1;
  font-size: 11px;
  color: #444;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.live-check {
  color: #27ae60;
  font-size: 12px;
  flex-shrink: 0;
}

/* Summary grid */
.summary-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
  margin-bottom: 32px;
}

@media (max-width: 1200px) {
  .summary-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

.metric-card {
  background: white;
  border: 1px solid #eee;
  padding: 20px 16px;
}

.metric-label {
  font-size: 9px;
  letter-spacing: 0.15em;
  color: #999;
  margin: 0 0 10px;
}

.metric-value {
  font-size: 26px;
  font-weight: 500;
  color: #1a1a1a;
  margin: 0 0 6px;
  font-family: 'Playfair Display', serif;
}

.metric-desc {
  font-size: 10px;
  color: #bbb;
  margin: 0;
  line-height: 1.4;
}

.text-success {
  color: #27ae60;
}

.text-warning {
  color: #B8860B;
}

.text-danger {
  color: #c0392b;
}

/* Bar chart */
.chart-section {
  background: white;
  border: 1px solid #eee;
  padding: 24px;
  margin-bottom: 24px;
}

.section-title {
  font-size: 10px;
  letter-spacing: 0.2em;
  color: #999;
  margin: 0 0 20px;
}

.bar-chart {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.bar-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.bar-label {
  width: 130px;
  font-size: 11px;
  color: #666;
  flex-shrink: 0;
}

.bar-track {
  flex: 1;
  height: 8px;
  background: #f0ede8;
  border-radius: 2px;
}

.bar-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.8s ease;
}

.bar-value {
  width: 40px;
  font-size: 12px;
  font-weight: 600;
  color: #1a1a1a;
  text-align: right;
  flex-shrink: 0;
}

/* Detail */
.detail-section {
  background: white;
  border: 1px solid #eee;
  padding: 24px;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}

.filter-group {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.filter-btn {
  padding: 4px 12px;
  font-size: 10px;
  letter-spacing: 0.1em;
  border: 1px solid #ddd;
  background: transparent;
  color: #888;
  cursor: pointer;
  font-family: 'IBM Plex Mono', monospace;
  transition: all 0.15s;
}

.filter-btn:hover {
  border-color: #B8860B;
  color: #B8860B;
}

.filter-btn.active {
  background: #1a1a1a;
  border-color: #1a1a1a;
  color: white;
}

/* Result list */
.result-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.result-item {
  border: 1px solid #f0ede8;
  cursor: pointer;
  transition: border-color 0.15s;
}

.result-item:hover {
  border-color: #B8860B;
}

.result-item.failed {
  border-left: 3px solid #c0392b;
}

.result-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
}

.result-id {
  font-size: 10px;
  color: #B8860B;
  min-width: 40px;
  flex-shrink: 0;
}

.result-type-badge {
  font-size: 9px;
  padding: 2px 8px;
  letter-spacing: 0.1em;
  flex-shrink: 0;
}

.type-factual {
  background: #e8f5e9;
  color: #27ae60;
}

.type-temporal {
  background: #fff8e1;
  color: #B8860B;
}

.type-conflict {
  background: #fce4ec;
  color: #c0392b;
}

.type-out_of_domain {
  background: #f3e5f5;
  color: #7b1fa2;
}

.result-question {
  flex: 1;
  font-size: 12px;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.result-scores {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

.score-pill {
  font-size: 10px;
  padding: 2px 8px;
  background: #f5f5f5;
}

.verdict-pill {
  font-size: 10px;
  padding: 2px 8px;
  font-weight: 600;
}

.verdict-pass {
  background: #e8f5e9;
  color: #27ae60;
}

.verdict-fail {
  background: #ffebee;
  color: #c0392b;
}

/* Expanded detail */
.result-detail {
  padding: 16px 12px;
  border-top: 1px solid #f0ede8;
  background: #FAFAF8;
  display: grid;
  grid-template-columns: 1fr 1fr 2fr;
  gap: 16px;
}

.detail-col {}

.detail-label {
  font-size: 9px;
  letter-spacing: 0.15em;
  color: #999;
  margin: 0 0 6px;
}

.detail-text {
  font-size: 12px;
  color: #444;
  margin: 0;
  line-height: 1.6;
}

.ground-truth {
  color: #27ae60;
  font-weight: 500;
}

.generated {
  color: #1a1a1a;
}

.detail-scores {
  grid-column: 1 / -1;
  display: flex;
  gap: 24px;
  padding-top: 12px;
  border-top: 1px solid #eee;
  flex-wrap: wrap;
}

.dscore {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.dscore span {
  font-size: 10px;
  color: #999;
}

.dscore strong {
  font-size: 14px;
}

/* Empty state */
.empty-eval {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 40px;
  text-align: center;
  color: #999;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-title {
  font-family: 'Playfair Display', serif;
  font-size: 20px;
  color: #1a1a1a;
  margin: 0 0 8px;
}

.empty-sub {
  font-size: 12px;
  color: #999;
  margin: 0;
}
</style>
