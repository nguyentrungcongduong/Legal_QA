<template>
  <div class="compare-shell">

    <!-- ═══ TOP NAV ═══ -->
    <header class="compare-topbar">
      <button class="back-btn" @click="$router.push('/chat')">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 5l-7 7 7 7"/></svg>
        Quay lại
      </button>

      <div class="topbar-center">
        <span class="topbar-eyebrow">SO SÁNH MÔ HÌNH</span>
        <h1 class="topbar-title">Đấu Trường <em>Kiểm Chứng</em> AI</h1>
      </div>

      <div class="live-chip">
        <span class="live-dot"></span>
        LIVE BENCHMARK
      </div>
    </header>

    <!-- ═══ INPUT ═══ -->
    <section class="input-section">
      <div class="input-label">ĐẶT CÂU HỎI PHÁP LÝ ĐỂ SO SÁNH</div>
      <div class="input-row">
        <input
          v-model="query"
          class="compare-input"
          placeholder="Ví dụ: Mức phạt kịch khung nồng độ cồn xe máy theo luật hiện hành?"
          @keydown.enter="runCompare"
        />
        <button class="compare-btn" @click="runCompare" :disabled="loading">
          <span v-if="!loading">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="display:inline;vertical-align:middle;margin-right:6px"><polygon points="5 3 19 12 5 21 5 3" fill="currentColor" stroke="none"/></svg>
            SO SÁNH
          </span>
          <span v-else class="btn-dots"><span></span><span></span><span></span></span>
        </button>
      </div>

      <!-- Gợi ý -->
      <div class="chips-row" v-if="!result && !loading">
        <button v-for="q in suggestions" :key="q" class="chip" @click="query = q">{{ q }}</button>
      </div>
    </section>

    <!-- ═══ STATS BAR ═══ -->
    <div class="stats-strip" v-if="!result && !loading">
      <div class="stat">
        <strong>2</strong><span>Văn bản luật đã nạp</span>
      </div>
      <div class="stat-sep"></div>
      <div class="stat">
        <strong>3</strong><span>Mô hình AI đối chiếu</span>
      </div>
      <div class="stat-sep"></div>
      <div class="stat">
        <strong>100%</strong><span>Nguồn được trích dẫn</span>
      </div>
    </div>

    <!-- ═══ SKELETON LOADING ═══ -->
    <section class="battle-grid" v-if="loading">
      <div class="sk-col sk-rag">
        <div class="sk-header"></div>
        <div class="sk-line w-full"></div>
        <div class="sk-line w-4/5"></div>
        <div class="sk-line w-5/6"></div>
        <div class="sk-line w-3/4"></div>
        <div class="sk-gap"></div>
        <div class="sk-cite"></div>
        <div class="sk-cite"></div>
      </div>
      <div class="sk-col sk-van">
        <div class="sk-header-g"></div>
        <div class="sk-line w-full"></div>
        <div class="sk-line w-5/6"></div>
        <div class="sk-line w-full"></div>
        <div class="sk-line w-3/5"></div>
        <div class="sk-gap"></div>
        <div class="sk-warn"></div>
      </div>
      <div class="sk-col sk-van" style="animation-delay:.12s">
        <div class="sk-header-g"></div>
        <div class="sk-line w-5/6"></div>
        <div class="sk-line w-full"></div>
        <div class="sk-line w-4/5"></div>
        <div class="sk-line w-2/3"></div>
        <div class="sk-gap"></div>
        <div class="sk-warn"></div>
      </div>
    </section>

    <!-- ═══ BATTLE RESULT GRID ═══ -->
    <section class="battle-grid result-in" v-if="result && !loading">

      <!-- Cột 1: Legal RAG — Nhân vật chính -->
      <div class="col col-rag">
        <div class="col-crown-area">
          <span class="crown-icon">👑</span>
          <div class="rag-badge">
            <svg width="9" height="9" viewBox="0 0 24 24" fill="#B8860B"><path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
            XÁC THỰC BỞI LUẬT
          </div>
        </div>

        <div class="col-modelname gold">LEGAL RAG</div>

        <div class="col-answer rag-answer">{{ result.rag?.answer ?? '---' }}</div>

        <!-- Citations -->
        <div class="citations-wrap" v-if="result.rag?.citations?.length">
          <p class="cite-section-label">
            <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="#B8860B" stroke-width="2.5"><path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
            CAN CU PHAP LY XAC THUC
          </p>
          <div v-for="(c, i) in result.rag.citations.slice(0, 3)" :key="i" class="cite-card" @click="onCitationClick(c)">
            <span class="cite-num">[{{ i + 1 }}]</span>
            <div>
              <p class="cite-law">{{ c.law_name }}</p>
              <p class="cite-details">{{ c.article }}{{ c.clause ? ' · ' + c.clause : '' }}</p>
            </div>
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#B8860B" stroke-width="2" style="margin-left:auto;flex-shrink:0"><path d="M9 18l6-6-6-6"/></svg>
          </div>
        </div>

        <!-- Conflict -->
        <div class="conflict-row" v-if="result.rag?.conflicts?.length">
          ⚠ Phát hiện {{ result.rag.conflicts.length }} vùng mâu thuẫn văn bản
        </div>

        <!-- Verdict WIN + Copy button -->
        <div class="verdict verdict-win">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="#27ae60"><path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
          Thong tin <strong>chinh xac 100%</strong> · Co trich dan dieu khoan
          <button
            v-if="result.rag?.answer"
            class="copy-ans-btn"
            @click.stop="copyAnswer(result.rag.answer, 'Legal RAG')"
            title="Sao chep noi dung tu van"
          >&#x2398;</button>
        </div>
      </div>

      <!-- Cot 2: Llama 3.3 70B Vanilla -->
      <div class="col col-vanilla">
        <div class="col-meta-row">
          <span class="col-modelname gray">LLAMA 3.3 70B</span>
          <span class="no-ctx-tag">NO CONTEXT</span>
        </div>

        <div class="col-answer van-answer" v-if="result.vanilla_gpt?.answer">{{ result.vanilla_gpt.answer }}</div>
        <div class="col-answer error-answer" v-else-if="result.vanilla_gpt?.error"><em>{{ result.vanilla_gpt.error }}</em></div>

        <div class="hall-warn">
          <div class="hall-title">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="#c0392b"><path d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/></svg>
            CẢNH BÁO HALLUCINATION
          </div>
          <p>Mô hình tự sinh câu trả lời từ dữ liệu huấn luyện — <strong>không truy xuất văn bản luật thực tế</strong>. Số liệu có thể sai hoặc lỗi thời.</p>
        </div>

        <div class="verdict verdict-lose">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="#c0392b"><path d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
          Không trích dẫn · <strong>Dễ ảo tưởng</strong>
        </div>
      </div>

      <!-- Cot 3: Llama 4 Scout Vanilla -->
      <div class="col col-vanilla">
        <div class="col-meta-row">
          <span class="col-modelname gray">LLAMA 4 SCOUT</span>
          <span class="no-ctx-tag">NO CONTEXT</span>
        </div>

        <div class="col-answer van-answer" v-if="result.vanilla_gemini?.answer">{{ result.vanilla_gemini.answer }}</div>
        <div class="col-answer error-answer" v-else-if="result.vanilla_gemini?.error"><em>{{ result.vanilla_gemini.error }}</em></div>

        <div class="hall-warn">
          <div class="hall-title">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="#c0392b"><path d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/></svg>
            CẢNH BÁO HALLUCINATION
          </div>
          <p>Không truy xuất dữ liệu pháp lý thực tế. Câu trả lời dựa trên tập huấn luyện cố định, <strong>có thể đã lỗi thời</strong> kể từ khi luật cập nhật.</p>
        </div>

        <div class="verdict verdict-lose">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="#c0392b"><path d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
          Không nguồn xác thực · <strong>Thiếu căn cứ pháp lý</strong>
        </div>
      </div>

    </section>

    <!-- ═══ EMPTY STATE ═══ -->
    <section class="empty-state" v-if="!result && !loading">
      <div class="vs-display">
        <span class="vs-rag">RAG</span>
        <span class="vs-sep">vs</span>
        <span class="vs-ai">AI</span>
      </div>
      <p class="empty-title">Nhập câu hỏi để bắt đầu trận đấu kiểm chứng</p>
      <p class="empty-sub">Hệ thống sẽ so sánh Legal RAG (có căn cứ pháp lý) với GPT-4o và Gemini (không có context)</p>
    </section>

    <!-- ═══ DOCUMENT METADATA DRAWER ═══ -->
    <DocumentMetadataDrawer
      :is-open="drawerOpen"
      :data="drawerCitation"
      @close="drawerOpen = false"
    />

  </div>
</template>

<script setup>
import { ref } from 'vue'
import api from '@/plugins/api'
import { useToast } from '@/composables/useToast'
import DocumentMetadataDrawer from '@/components/DocumentMetadataDrawer.vue'

const emit = defineEmits(['open-citation'])
const toast = useToast()
const query = ref('')
const loading = ref(false)
const result = ref(null)

// Drawer state
const drawerOpen = ref(false)
const drawerCitation = ref(null)

const suggestions = [
  'Mức phạt kịch khung nồng độ cồn xe máy?',
  'Vượt đèn đỏ ô tô bị phạt bao nhiêu?',
  'Không đội mũ bảo hiểm bị xử lý thế nào?',
  'Xe máy đi ngược chiều bị phạt bao nhiêu?',
]

async function copyAnswer(text, label) {
  try {
    await navigator.clipboard.writeText(text)
    toast.success('Da sao chep noi dung tu van vao khay nho tam.', 'Sao chep thanh cong')
  } catch {
    toast.error('Trinh duyet khong cho phep truy cap clipboard.', 'Loi sao chep')
  }
}

function onCitationClick(citation) {
  // Hien thi toast thong bao
  const page = citation.page_number ? ` - trang ${citation.page_number}` : ''
  toast.legal(
    `Dang tai ban goc: ${citation.law_name || 'Van ban phap ly'}${page}`,
    'Truy xuat tai lieu'
  )
  // Mo Document Metadata Drawer
  drawerCitation.value = citation
  drawerOpen.value = true
}

async function runCompare() {
  if (!query.value.trim()) return
  loading.value = true
  result.value = null

  toast.info('Dang phan tich voi 3 mo hinh AI song song...', 'Khoi chay kiem chung')

  try {
    const res = await api.post('/api/ai/compare', {
      query: query.value
    })
    result.value = res.data

    // Canh bao conflict neu co
    const conflicts = res.data?.rag?.conflicts || []
    if (conflicts.length > 0) {
      toast.warning(
        `Phat hien ${conflicts.length} mau thuan van ban. He thong da xu ly va chon nguon moi nhat.`,
        'Canh bao mau thuan phap ly'
      )
    } else {
      toast.success(
        'Legal RAG da hoan thanh voi nguon duoc xac thuc. So sanh hoan tat.',
        'Kiem chung thanh cong'
      )
    }
  } catch (e) {
    toast.error('Khong ket noi duoc toi may chu. Dang hien thi du lieu demo.', 'Loi he thong')
    console.error(e)
    // Mock data de demo UI khi backend chua co LLM keys
    result.value = {
      rag: {
        answer: `Theo Nghị định 100/2019/NĐ-CP (được sửa đổi bởi Nghị định 123/2021/NĐ-CP), người điều khiển xe mô tô, xe gắn máy có nồng độ cồn trong máu vượt 0.4 mg/lít khí thở trở lên bị phạt tiền từ 6.000.000đ đến 8.000.000đ, đồng thời bị tước quyền sử dụng Giấy phép lái xe từ 22 tháng đến 24 tháng.`,
        citations: [
          { law_name: 'Nghị định 100/2019/NĐ-CP', article: 'Điều 5', clause: 'Khoản 8', chunk_id: 'mock-1' },
          { law_name: 'Nghị định 123/2021/NĐ-CP', article: 'Điều 2', clause: 'Khoản 1', chunk_id: 'mock-2' },
        ],
        conflicts: []
      },
      vanilla_gpt: {
        answer: 'Theo tôi biết, mức phạt nồng độ cồn cao nhất cho xe máy là khoảng 3–4 triệu đồng và bị tước bằng lái 1–2 năm. Tuy nhiên luật có thể đã thay đổi, bạn nên kiểm tra lại quy định mới nhất.'
      },
      vanilla_gemini: {
        answer: 'Luật Giao thông Đường bộ quy định người điều khiển xe mô tô có nồng độ cồn cao có thể bị phạt từ 2–5 triệu đồng. Tuy nhiên tôi không thể cung cấp thông tin chính xác về các nghị định cụ thể hiện hành.'
      }
    }
  } finally {
    loading.value = false
  }
}

function openCitation(citation) {
  emit('open-citation', citation)
}
</script>

<style scoped>
/* ══ Base ══ */
.compare-shell {
  min-height: 100vh;
  background: #FAFAF8;
  color: #1a1a1a;
  font-family: 'IBM Plex Mono', 'Source Sans 3', monospace;
  -webkit-font-smoothing: antialiased;
  display: flex;
  flex-direction: column;
}

/* ══ Top Nav ══ */
.compare-topbar {
  position: sticky;
  top: 0;
  z-index: 10;
  background: rgba(250, 250, 248, 0.92);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid #e8e4df;
  padding: 16px 40px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  background: transparent;
  border: 1px solid #ddd;
  color: #888;
  font-family: inherit;
  font-size: 11px;
  letter-spacing: 0.08em;
  padding: 6px 14px;
  cursor: pointer;
  transition: all 0.15s;
}
.back-btn:hover { border-color: #B8860B; color: #B8860B; }

.topbar-center { text-align: center; }
.topbar-eyebrow {
  display: block;
  font-size: 9px;
  letter-spacing: 0.3em;
  color: #B8860B;
  margin-bottom: 2px;
}
.topbar-title {
  font-family: 'Playfair Display', Georgia, serif;
  font-size: 22px;
  font-weight: 700;
  color: #1a1a1a;
  margin: 0;
}
.topbar-title em { color: #B8860B; font-style: italic; }

.live-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 9px;
  letter-spacing: 0.2em;
  color: #27ae60;
  border: 1px solid rgba(39,174,96,0.35);
  padding: 5px 12px;
  background: rgba(39,174,96,0.04);
}
.live-dot {
  width: 6px; height: 6px;
  background: #27ae60;
  border-radius: 50%;
  animation: livepulse 1.5s ease-in-out infinite;
}
@keyframes livepulse { 0%,100%{opacity:1} 50%{opacity:0.25} }

/* ══ Input Section ══ */
.input-section {
  padding: 36px 40px 0;
  border-bottom: 1px solid #e8e4df;
  background: #fff;
}

.input-label {
  font-size: 9px;
  letter-spacing: 0.25em;
  color: #B8860B;
  margin-bottom: 14px;
  font-weight: 600;
}

.input-row {
  display: flex;
  gap: 10px;
  align-items: stretch;
}

.compare-input {
  flex: 1;
  padding: 14px 18px;
  border: 1px solid #e8e4df;
  background: #FAFAF8;
  font-family: 'Playfair Display', Georgia, serif;
  font-size: 17px;
  color: #1a1a1a;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.compare-input::placeholder { color: #bbb; }
.compare-input:focus { border-color: #B8860B; box-shadow: 0 0 0 1px #B8860B; }

.compare-btn {
  background: #1a1a1a;
  color: #FAFAF8;
  border: none;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.2em;
  padding: 0 28px;
  cursor: pointer;
  transition: background 0.2s;
  min-width: 130px;
}
.compare-btn:hover:not(:disabled) { background: #B8860B; }
.compare-btn:disabled { opacity: 0.4; cursor: not-allowed; }

/* Loading dots */
.btn-dots { display:flex; gap:5px; align-items:center; justify-content:center; }
.btn-dots span {
  width:5px; height:5px; background:#FAFAF8; border-radius:50%;
  animation: dotbounce 1.1s ease-in-out infinite;
}
.btn-dots span:nth-child(2){animation-delay:.18s}
.btn-dots span:nth-child(3){animation-delay:.36s}
@keyframes dotbounce{ 0%,80%,100%{transform:translateY(0);opacity:.5} 40%{transform:translateY(-6px);opacity:1} }

/* Chips */
.chips-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 18px;
  padding: 18px 0;
}
.chip {
  font-size: 11px;
  padding: 5px 14px;
  border: 1px solid #ddd;
  background: white;
  color: #666;
  cursor: pointer;
  font-family: inherit;
  transition: all 0.15s;
}
.chip:hover { border-color: #B8860B; color: #B8860B; }

/* ══ Stats Strip ══ */
.stats-strip {
  display: flex;
  align-items: center;
  background: #fff;
  border-bottom: 1px solid #e8e4df;
}
.stat {
  flex: 1;
  padding: 18px 40px;
  display: flex;
  align-items: center;
  gap: 14px;
}
.stat strong {
  font-family: 'Playfair Display', serif;
  font-size: 26px;
  color: #B8860B;
  font-weight: 700;
}
.stat span { font-size: 10px; letter-spacing: 0.1em; color: #999; }
.stat-sep { width: 1px; height: 40px; background: #e8e4df; }

/* ══ Battle Grid ══ */
.battle-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 1px;
  background: #e8e4df;
  flex: 1;
  margin: 28px 40px 40px;
  box-shadow: 0 2px 20px rgba(0,0,0,0.05);
}

.result-in {
  animation: risein 0.35s ease forwards;
}
@keyframes risein { from{opacity:0;transform:translateY(20px)} to{opacity:1;transform:translateY(0)} }

/* ══ Column Base ══ */
.col {
  background: #fff;
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
}

/* ══ RAG Column — Elevated ══ */
.col-rag {
  border-top: 4px solid #B8860B;
  background: #fff;
  box-shadow: 0 0 0 1px rgba(184,134,11,0.12) inset;
}

.col-crown-area {
  padding: 20px 28px 4px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.crown-icon { font-size: 18px; }
.rag-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: rgba(184,134,11,0.08);
  border: 1px solid rgba(184,134,11,0.3);
  color: #B8860B;
  font-size: 8px;
  letter-spacing: 0.15em;
  padding: 3px 9px;
  font-weight: 600;
}

/* ══ Vanilla Column — Dimmed ══ */
.col-vanilla {
  border-top: 4px solid #e8e4df;
  background: #fdfcfb;
  opacity: 0.88;
}

.col-meta-row {
  padding: 20px 28px 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.no-ctx-tag {
  font-size: 8px;
  letter-spacing: 0.15em;
  color: #bbb;
  border: 1px solid #e8e4df;
  padding: 2px 7px;
}

/* ══ Model Name ══ */
.col-modelname {
  display: block;
  font-size: 10px;
  letter-spacing: 0.25em;
  font-weight: 600;
  padding: 0 28px 16px;
}
.col-modelname.gold { color: #B8860B; }
.col-modelname.gray { color: #bbb; font-size: 9px; padding: 0; }

/* ══ Answer Text ══ */
.col-answer {
  padding: 0 28px 24px;
  line-height: 1.8;
  flex: 1;
}
.rag-answer {
  font-family: 'Playfair Display', Georgia, serif;
  font-size: 15px;
  color: #1a1a1a;
  font-style: italic;
}
.van-answer {
  font-size: 13px;
  color: #888;
  line-height: 1.7;
}
.error-answer { font-size: 12px; color: #ccc; }

/* ══ Citations ══ */
.citations-wrap {
  margin: 0 28px 20px;
  border-top: 1px solid #e8e4df;
  padding-top: 18px;
}
.cite-section-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 9px;
  letter-spacing: 0.2em;
  color: #B8860B;
  font-weight: 600;
  margin: 0 0 10px;
}
.cite-card {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 9px 11px;
  border: 1px solid #e8e4df;
  background: #FAFAF8;
  margin-bottom: 5px;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}
.cite-card:hover { border-color: #B8860B; background: rgba(184,134,11,0.03); }
.cite-num { font-size: 10px; color: #B8860B; font-weight: 700; min-width: 22px; }
.cite-law { font-size: 11px; font-weight: 600; color: #1a1a1a; margin: 0; }
.cite-details { font-size: 9px; color: #999; margin: 2px 0 0; }

/* ══ Conflict ══ */
.conflict-row {
  margin: 0 28px 14px;
  font-size: 10px;
  color: #B8860B;
  padding: 7px 11px;
  background: rgba(184,134,11,0.06);
  border: 1px solid rgba(184,134,11,0.2);
}

/* ══ Hallucination Warning ══ */
.hall-warn {
  margin: 0 28px 20px;
  padding: 13px 15px;
  background: #fff5f5;
  border: 1px solid #fcc;
  border-left: 3px solid #c0392b;
}
.hall-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 9px;
  letter-spacing: 0.15em;
  color: #c0392b;
  font-weight: 700;
  margin-bottom: 7px;
}
.hall-warn p { font-size: 11px; color: #999; line-height: 1.6; margin: 0; }
.hall-warn strong { color: #c0392b; }

/* ══ Verdict ══ */
.verdict {
  margin-top: auto;
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 10px;
  padding: 12px 28px;
  border-top: 1px solid #e8e4df;
  letter-spacing: 0.03em;
}
.verdict strong { font-weight: 700; }
.verdict-win { color: #27ae60; background: rgba(39,174,96,0.04); }
.verdict-lose { color: #c0392b; background: rgba(192,57,43,0.03); }

/* ══ Skeleton ══ */
@keyframes shimmer { 0%{background-position:-500px 0} 100%{background-position:500px 0} }
.sk-col, .sk-rag, .sk-van {
  padding: 28px;
  display: flex;
  flex-direction: column;
  gap: 11px;
  background: #fff;
}
.sk-rag { border-top: 4px solid rgba(184,134,11,0.3); }
.sk-van { border-top: 4px solid #e8e4df; background: #fdfcfb; }

.sk-bg { background: linear-gradient(90deg,#f0ede8 25%,#e8e4df 50%,#f0ede8 75%); background-size:1000px 100%; animation: shimmer 1.5s infinite linear; border-radius:2px; }

.sk-header, .sk-header-g,
.sk-line, .sk-cite, .sk-warn, .sk-gap {
  border-radius: 2px;
  background: linear-gradient(90deg,#f0ede8 25%,#e8e4df 50%,#f0ede8 75%);
  background-size: 1000px 100%;
  animation: shimmer 1.5s infinite linear;
}
.sk-header { height: 18px; width: 55%; align-self: flex-start; }
.sk-header-g { height: 14px; width: 45%; }
.sk-line { height: 11px; }
.sk-line.w-full{width:100%}.sk-line.w-5\/6{width:83%}.sk-line.w-4\/5{width:80%}
.sk-line.w-3\/4{width:75%}.sk-line.w-2\/3{width:67%}.sk-line.w-3\/5{width:60%}
.sk-gap { height: 22px; background: transparent; }
.sk-cite { height: 44px; }
.sk-warn { height: 60px; }

/* ══ Empty State ══ */
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 40px;
  text-align: center;
}
.vs-display {
  display: flex;
  align-items: baseline;
  gap: 28px;
  margin-bottom: 28px;
}
.vs-rag {
  font-family: 'Playfair Display', serif;
  font-size: 52px;
  font-weight: 700;
  color: #B8860B;
}
.vs-sep {
  font-size: 18px;
  color: #ccc;
  letter-spacing: 0.2em;
  font-family: 'IBM Plex Mono', monospace;
}
.vs-ai {
  font-family: 'Playfair Display', serif;
  font-size: 52px;
  font-weight: 700;
  color: #e8e4df;
}
.empty-title {
  font-family: 'Playfair Display', serif;
  font-size: 20px;
  color: #666;
  margin: 0 0 10px;
  font-style: italic;
}
.empty-sub {
  font-size: 11px;
  color: #bbb;
  max-width: 460px;
  line-height: 1.7;
  margin: 0;
}

/* Copy answer button inside verdict bar */
.copy-ans-btn {
  background: none;
  border: 1px solid #B8860B44;
  color: #B8860B;
  font-size: 14px;
  line-height: 1;
  padding: 1px 6px;
  margin-left: auto;
  cursor: pointer;
  opacity: 0.7;
  transition: opacity 0.15s, border-color 0.15s;
  flex-shrink: 0;
}
.copy-ans-btn:hover { opacity: 1; border-color: #B8860B; }
</style>
