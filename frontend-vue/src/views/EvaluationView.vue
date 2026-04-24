<template>
  <div class="eval-page">

    <!-- Header -->
    <div class="eval-header">
      <div>
        <h2 class="eval-title">Evaluation Dashboard</h2>
        <p class="eval-sub">Đánh giá định lượng khả năng chống hallucination</p>
      </div>
      <button class="run-btn" @click="runEvaluation" :disabled="loading">
        {{ loading ? 'ĐANG CHẠY...' : 'CHẠY ĐÁNH GIÁ' }}
      </button>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="loading-state">
      <div class="loading-bar">
        <div class="loading-fill" :style="{ width: progress + '%' }"></div>
      </div>
      <p class="loading-text">
        Đang chạy {{ currentTest }}/{{ totalTests }} test cases...
      </p>
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
            <div
              class="bar-fill"
              :style="{
                width: (data.avg_faithfulness * 100) + '%',
                background: barColor(data.avg_faithfulness)
              }"
            ></div>
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
          <button
            v-for="f in filters"
            :key="f.value"
            class="filter-btn"
            :class="{ active: activeFilter === f.value }"
            @click="activeFilter = f.value"
          >{{ f.label }}</button>
        </div>
      </div>

      <div class="result-list">
        <div
          v-for="r in filteredResults"
          :key="r.id"
          class="result-item"
          :class="{ failed: r.is_hallucinated }"
          @click="expandedId = expandedId === r.id ? null : r.id"
        >
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
      <p class="empty-sub">Nhấn "CHẠY ĐÁNH GIÁ" để bắt đầu kiểm tra 20 test cases</p>
    </div>

  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import api from '@/plugins/api'
const loading = ref(false)
const result = ref(null)
const expandedId = ref(null)
const activeFilter = ref('all')
const progress = ref(0)
const currentTest = ref(0)
const totalTests = ref(20)

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
  result.value = null
  progress.value = 0
  currentTest.value = 0

  // Simulate progress while waiting for backend
  const interval = setInterval(() => {
    if (currentTest.value < totalTests.value - 1) {
      currentTest.value++
      progress.value = Math.round((currentTest.value / totalTests.value) * 85)
    }
  }, 2500)

  try {
    const res = await api.post('/api/ai/evaluate', {})
    result.value = res.data
  } catch (e) {
    console.error('Evaluation failed:', e)
    alert('Lỗi khi chạy evaluation: ' + (e.response?.data?.detail || e.message))
  } finally {
    clearInterval(interval)
    progress.value = 100
    currentTest.value = totalTests.value
    loading.value = false
  }
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

.run-btn:hover:not(:disabled) { background: #B8860B; }
.run-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* Loading */
.loading-state {
  margin-bottom: 32px;
  padding: 24px;
  background: white;
  border: 1px solid #eee;
}

.loading-bar { height: 4px; background: #eee; margin-bottom: 12px; }
.loading-fill { height: 100%; background: #B8860B; transition: width 0.5s ease; }
.loading-text { font-size: 12px; color: #888; margin: 0; }

/* Summary grid */
.summary-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
  margin-bottom: 32px;
}

@media (max-width: 1200px) {
  .summary-grid { grid-template-columns: repeat(3, 1fr); }
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

.metric-desc { font-size: 10px; color: #bbb; margin: 0; line-height: 1.4; }

.text-success { color: #27ae60; }
.text-warning { color: #B8860B; }
.text-danger  { color: #c0392b; }

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

.bar-chart { display: flex; flex-direction: column; gap: 14px; }

.bar-row { display: flex; align-items: center; gap: 12px; }

.bar-label { width: 130px; font-size: 11px; color: #666; flex-shrink: 0; }

.bar-track { flex: 1; height: 8px; background: #f0ede8; border-radius: 2px; }

.bar-fill { height: 100%; border-radius: 2px; transition: width 0.8s ease; }

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

.filter-group { display: flex; gap: 6px; flex-wrap: wrap; }

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

.filter-btn:hover { border-color: #B8860B; color: #B8860B; }
.filter-btn.active { background: #1a1a1a; border-color: #1a1a1a; color: white; }

/* Result list */
.result-list { display: flex; flex-direction: column; gap: 4px; }

.result-item {
  border: 1px solid #f0ede8;
  cursor: pointer;
  transition: border-color 0.15s;
}

.result-item:hover { border-color: #B8860B; }
.result-item.failed { border-left: 3px solid #c0392b; }

.result-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
}

.result-id { font-size: 10px; color: #B8860B; min-width: 40px; flex-shrink: 0; }

.result-type-badge { font-size: 9px; padding: 2px 8px; letter-spacing: 0.1em; flex-shrink: 0; }
.type-factual    { background: #e8f5e9; color: #27ae60; }
.type-temporal   { background: #fff8e1; color: #B8860B; }
.type-conflict   { background: #fce4ec; color: #c0392b; }
.type-out_of_domain { background: #f3e5f5; color: #7b1fa2; }

.result-question {
  flex: 1;
  font-size: 12px;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.result-scores { display: flex; gap: 6px; flex-shrink: 0; }

.score-pill { font-size: 10px; padding: 2px 8px; background: #f5f5f5; }

.verdict-pill { font-size: 10px; padding: 2px 8px; font-weight: 600; }
.verdict-pass { background: #e8f5e9; color: #27ae60; }
.verdict-fail { background: #ffebee; color: #c0392b; }

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

.detail-label { font-size: 9px; letter-spacing: 0.15em; color: #999; margin: 0 0 6px; }

.detail-text { font-size: 12px; color: #444; margin: 0; line-height: 1.6; }
.ground-truth { color: #27ae60; font-weight: 500; }
.generated { color: #1a1a1a; }

.detail-scores {
  grid-column: 1 / -1;
  display: flex;
  gap: 24px;
  padding-top: 12px;
  border-top: 1px solid #eee;
  flex-wrap: wrap;
}

.dscore { display: flex; flex-direction: column; gap: 2px; }
.dscore span { font-size: 10px; color: #999; }
.dscore strong { font-size: 14px; }

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

.empty-icon { font-size: 48px; margin-bottom: 16px; }
.empty-title { font-family: 'Playfair Display', serif; font-size: 20px; color: #1a1a1a; margin: 0 0 8px; }
.empty-sub { font-size: 12px; color: #999; margin: 0; }
</style>
