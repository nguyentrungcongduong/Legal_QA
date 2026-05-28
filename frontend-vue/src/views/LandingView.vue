<template>
  <div class="landing">

    <!-- NAV -->
    <nav class="nav">
      <div class="nav-brand">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#C9A84C" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
        <span>LegalAI RAG</span>
      </div>
      <div class="nav-links">
        <a href="#features">Tính năng</a>
        <a href="#domains">Lĩnh vực</a>
        <a href="#stats">Hiệu suất</a>
        <router-link to="/login" class="btn-nav">Đăng nhập</router-link>
      </div>
    </nav>

    <!-- HERO -->
    <section class="hero">
      <div class="hero-bg">
        <div class="hero-orb orb1"></div>
        <div class="hero-orb orb2"></div>
        <div class="hero-orb orb3"></div>
      </div>
      <div class="hero-content">
        <div class="hero-badge">
          <span class="badge-dot"></span>
          Hệ thống RAG 7 tầng — Đang hoạt động
        </div>
        <h1 class="hero-title">
          Tư Vấn Pháp Luật<br />
          <span class="highlight">Việt Nam</span> Thông Minh
        </h1>
        <p class="hero-desc">
          Hệ thống hỏi đáp pháp luật ứng dụng kỹ thuật RAG (Retrieval-Augmented Generation),
          kết hợp tìm kiếm văn bản pháp luật chính xác và mô hình ngôn ngữ lớn để cho câu trả lời
          <strong>có trích dẫn nguồn cụ thể</strong>, đáng tin cậy.
        </p>
        <div class="hero-actions">
          <router-link to="/login" class="btn-primary">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><path d="M12 8v4l3 3"/></svg>
            Bắt đầu tư vấn
          </router-link>
          <router-link to="/register" class="btn-secondary">Tạo tài khoản miễn phí</router-link>
        </div>
        <div class="hero-trust">
          <span>✓ Trích dẫn nguồn văn bản pháp luật</span>
          <span>✓ Không hallucination</span>
          <span>✓ Miễn phí</span>
        </div>
      </div>
      <div class="hero-visual">
        <div class="chat-demo">
          <div class="chat-header">
            <div class="chat-dot red"></div><div class="chat-dot yellow"></div><div class="chat-dot green"></div>
            <span>Hệ Thống Luật Sư AI · Luật Giao Thông</span>
          </div>
          <div class="chat-body">
            <div class="chat-msg user-msg">Nồng độ cồn mức 3 bị phạt bao nhiêu?</div>
            <div class="chat-msg ai-msg">
              <div class="ai-icon">⚖️</div>
              <div class="ai-text">
                Theo NĐ 168/2024/NĐ-CP, người điều khiển xe mô tô với nồng độ cồn vượt 80mg/100ml máu sẽ bị
                phạt tiền từ <strong>6.000.000 – 8.000.000 đồng</strong>
                <span class="cite-tag">[1]</span> và tước quyền sử dụng GPLX từ
                <strong>22 – 24 tháng</strong> <span class="cite-tag">[1]</span>.
              </div>
            </div>
            <div class="cite-bar">
              <span class="cite-label">CĂN CỨ PHÁP LÝ</span>
              <div class="cite-chip">[1] NĐ 168/2024/NĐ-CP · Điều 10</div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- FEATURES -->
    <section id="features" class="features">
      <div class="section-header">
        <p class="section-sub">Công nghệ</p>
        <h2>RAG Pipeline 7 Tầng</h2>
        <p class="section-desc">Từ câu hỏi đến câu trả lời có trích dẫn — qua 7 lớp xử lý thông minh</p>
      </div>
      <div class="pipeline">
        <div v-for="(step, i) in pipeline" :key="i" class="pipeline-step">
          <div class="step-icon" v-html="step.svg"></div>
          <div class="step-name">{{ step.name }}</div>
          <div class="step-desc">{{ step.desc }}</div>
        </div>
      </div>
    </section>

    <!-- DOMAINS -->
    <section id="domains" class="domains">
      <div class="section-header">
        <p class="section-sub">Phạm vi</p>
        <h2>5 Lĩnh Vực Pháp Luật</h2>
      </div>
      <div class="domain-grid">
        <div v-for="d in domains" :key="d.key" class="domain-card">
          <div class="domain-icon">{{ d.icon }}</div>
          <div class="domain-name">{{ d.name }}</div>
          <div class="domain-example">{{ d.example }}</div>
        </div>
      </div>
    </section>

    <!-- STATS -->
    <section id="stats" class="stats-section">
      <div class="stats-grid">
        <div v-for="s in stats" :key="s.label" class="stat-card">
          <div class="stat-value">{{ s.value }}</div>
          <div class="stat-label">{{ s.label }}</div>
        </div>
      </div>
    </section>

    <!-- CTA -->
    <section class="cta-section">
      <h2>Sẵn sàng tra cứu pháp luật?</h2>
      <p>Đặt câu hỏi bằng ngôn ngữ tự nhiên — nhận câu trả lời có căn cứ pháp lý ngay.</p>
      <router-link to="/register" class="btn-primary btn-large">
        Tạo tài khoản miễn phí
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
      </router-link>
    </section>

    <!-- FOOTER -->
    <footer class="footer">
      <div class="footer-brand">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#C9A84C" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
        LegalAI RAG — Hệ thống Hỏi Đáp Pháp Luật Việt Nam
      </div>
      <p class="footer-note">Thông tin chỉ mang tính tham khảo, không thay thế tư vấn pháp lý chuyên nghiệp.</p>
    </footer>

  </div>
</template>

<script setup>
const pipeline = [
  {
    name: 'Guard',
    desc: 'Lọc câu hỏi ngoài domain',
    svg: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>`
  },
  {
    name: 'Rewrite',
    desc: 'Chuẩn hóa câu hỏi',
    svg: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>`
  },
  {
    name: 'Hybrid Search',
    desc: 'Dense + Sparse search',
    svg: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/><path d="M11 8v6M8 11h6"/></svg>`
  },
  {
    name: 'Rerank',
    desc: 'Xếp hạng kết quả',
    svg: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18M7 12h10M11 18h2"/></svg>`
  },
  {
    name: 'Conflict',
    desc: 'Phát hiện xung đột',
    svg: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`
  },
  {
    name: 'Generate',
    desc: 'LLM sinh câu trả lời',
    svg: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><path d="M8 10h8M8 14h5"/></svg>`
  },
  {
    name: 'Citation',
    desc: 'Gán trích dẫn [1][2]',
    svg: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="9" y1="13" x2="15" y2="13"/><line x1="9" y1="17" x2="13" y2="17"/></svg>`
  },
]

const domains = [
  { key: 'giao_thong', icon: '🚗', name: 'Giao thông', example: 'Phạt nồng độ cồn, vượt đèn đỏ...' },
  { key: 'hinh_su', icon: '⚖️', name: 'Hình sự', example: 'Tội phạm, hình phạt, tố tụng...' },
  { key: 'dan_su', icon: '📜', name: 'Dân sự', example: 'Hợp đồng, tài sản, thừa kế...' },
  { key: 'lao_dong', icon: '👷', name: 'Lao động', example: 'Hợp đồng lao động, sa thải...' },
  { key: 'hon_nhan', icon: '💍', name: 'Hôn nhân & Gia đình', example: 'Ly hôn, nuôi con, tài sản...' },
]

const stats = [
  { value: '7', label: 'Tầng xử lý RAG' },
  { value: '5', label: 'Lĩnh vực pháp luật' },
  { value: '86.7%', label: 'Faithfulness Score' },
  { value: '< 3s', label: 'Thời gian phản hồi' },
]
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Playfair+Display:wght@700;800&display=swap');

* { box-sizing: border-box; margin: 0; padding: 0; }

.landing {
  background: #0a0c10;
  color: #e8e4d9;
  font-family: 'Inter', sans-serif;
  min-height: 100vh;
  overflow-x: hidden;
}

/* ── NAV ── */
.nav {
  position: fixed; top: 0; left: 0; right: 0; z-index: 100;
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 60px;
  background: rgba(10,12,16,0.85);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(201,168,76,0.15);
}
.nav-brand {
  display: flex; align-items: center; gap: 10px;
  font-size: 18px; font-weight: 700; color: #C9A84C;
}
.nav-links { display: flex; align-items: center; gap: 32px; }
.nav-links a { color: #a09880; font-size: 14px; text-decoration: none; transition: color 0.2s; }
.nav-links a:hover { color: #C9A84C; }
.btn-nav {
  padding: 8px 20px;
  background: rgba(201,168,76,0.15);
  border: 1px solid rgba(201,168,76,0.4);
  border-radius: 8px; color: #C9A84C !important;
  font-weight: 600; transition: all 0.2s;
}
.btn-nav:hover { background: rgba(201,168,76,0.25) !important; }

/* ── HERO ── */
.hero {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 1fr 1fr;
  align-items: center;
  gap: 60px;
  padding: 120px 60px 80px;
  position: relative;
  overflow: hidden;
}
.hero-bg { position: absolute; inset: 0; pointer-events: none; }
.hero-orb {
  position: absolute; border-radius: 50%;
  filter: blur(100px); opacity: 0.12;
  animation: float 8s ease-in-out infinite;
}
.orb1 { width: 500px; height: 500px; background: #C9A84C; top: -100px; left: -100px; }
.orb2 { width: 400px; height: 400px; background: #4a7c59; bottom: -100px; right: 100px; animation-delay: 3s; }
.orb3 { width: 300px; height: 300px; background: #7a5c2e; top: 40%; left: 40%; animation-delay: 6s; }
@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(30px, -20px) scale(1.05); }
  66% { transform: translate(-20px, 30px) scale(0.95); }
}

.hero-content { position: relative; z-index: 1; }
.hero-badge {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 6px 16px;
  background: rgba(201,168,76,0.12);
  border: 1px solid rgba(201,168,76,0.3);
  border-radius: 100px;
  font-size: 13px; color: #C9A84C; font-weight: 500;
  margin-bottom: 28px;
}
.badge-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #4ade80;
  animation: pulse-dot 2s ease-in-out infinite;
}
@keyframes pulse-dot {
  0%, 100% { box-shadow: 0 0 0 0 rgba(74,222,128,0.4); }
  50% { box-shadow: 0 0 0 6px rgba(74,222,128,0); }
}

.hero-title {
  font-family: 'Playfair Display', serif;
  font-size: clamp(36px, 4vw, 56px);
  font-weight: 800;
  line-height: 1.15;
  margin-bottom: 24px;
  color: #f0ece0;
}
.highlight {
  background: linear-gradient(135deg, #C9A84C, #f0c060);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.hero-desc {
  font-size: 16px; line-height: 1.75;
  color: #8a8070; max-width: 520px;
  margin-bottom: 36px;
}
.hero-actions { display: flex; gap: 16px; align-items: center; margin-bottom: 28px; flex-wrap: wrap; }
.btn-primary {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 14px 28px;
  background: linear-gradient(135deg, #C9A84C, #a07830);
  color: #0a0c10; font-weight: 700; font-size: 15px;
  border-radius: 10px; text-decoration: none;
  transition: all 0.25s; box-shadow: 0 4px 24px rgba(201,168,76,0.3);
}
.btn-primary:hover { transform: translateY(-2px); box-shadow: 0 8px 32px rgba(201,168,76,0.4); }
.btn-secondary {
  color: #C9A84C; font-weight: 600; font-size: 15px;
  text-decoration: none; border-bottom: 1px dashed rgba(201,168,76,0.5);
  transition: border-color 0.2s;
}
.btn-secondary:hover { border-color: #C9A84C; }
.btn-large { font-size: 17px; padding: 16px 36px; }

.hero-trust { display: flex; gap: 20px; flex-wrap: wrap; }
.hero-trust span { font-size: 13px; color: #6a6558; }
.hero-trust span::before { margin-right: 4px; }

/* ── CHAT DEMO ── */
.hero-visual { position: relative; z-index: 1; }
.chat-demo {
  background: #12141a;
  border: 1px solid rgba(201,168,76,0.2);
  border-radius: 16px; overflow: hidden;
  box-shadow: 0 20px 80px rgba(0,0,0,0.5);
  animation: float-card 6s ease-in-out infinite;
}
@keyframes float-card {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}
.chat-header {
  display: flex; align-items: center; gap: 8px;
  padding: 14px 20px;
  background: #0e1016;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  font-size: 12px; color: #6a6558;
}
.chat-dot { width: 10px; height: 10px; border-radius: 50%; }
.chat-dot.red { background: #ff5f57; }
.chat-dot.yellow { background: #febc2e; }
.chat-dot.green { background: #28c840; }
.chat-header span { margin-left: 6px; }

.chat-body { padding: 24px; display: flex; flex-direction: column; gap: 16px; }
.chat-msg { border-radius: 12px; font-size: 14px; line-height: 1.6; }
.user-msg {
  align-self: flex-end;
  background: rgba(201,168,76,0.15);
  border: 1px solid rgba(201,168,76,0.25);
  padding: 12px 16px; max-width: 80%;
  color: #e8dfc0;
}
.ai-msg {
  display: flex; gap: 12px; align-items: flex-start;
}
.ai-icon { font-size: 20px; flex-shrink: 0; margin-top: 2px; }
.ai-text {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  padding: 14px 16px; border-radius: 12px;
  font-size: 14px; line-height: 1.7; color: #c8c0b0;
}
.cite-tag {
  display: inline-block; font-size: 11px; font-weight: 700;
  color: #C9A84C; vertical-align: super; margin: 0 1px;
  cursor: pointer;
}
.cite-bar {
  border-top: 1px solid rgba(255,255,255,0.06);
  padding-top: 14px;
  display: flex; align-items: center; gap: 12px;
}
.cite-label { font-size: 10px; color: #6a6558; font-weight: 700; letter-spacing: 1px; }
.cite-chip {
  font-size: 12px; color: #C9A84C;
  background: rgba(201,168,76,0.1);
  border: 1px solid rgba(201,168,76,0.25);
  padding: 4px 12px; border-radius: 6px;
}

/* ── SECTIONS ── */
.section-header { text-align: center; margin-bottom: 60px; }
.section-sub { font-size: 13px; color: #C9A84C; font-weight: 600; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 12px; }
.section-header h2 {
  font-family: 'Playfair Display', serif;
  font-size: clamp(28px, 3vw, 40px);
  color: #f0ece0; margin-bottom: 16px;
}
.section-desc { color: #6a6558; font-size: 16px; max-width: 500px; margin: 0 auto; }

/* ── PIPELINE ── */
.features { padding: 100px 60px; background: #0c0e13; }
.pipeline {
  display: flex; align-items: stretch;
  gap: 0; overflow-x: auto;
  justify-content: center; flex-wrap: wrap; gap: 20px;
}
.pipeline-step {
  position: relative;
  background: #12141a;
  border: 1px solid rgba(201,168,76,0.15);
  border-radius: 14px;
  padding: 24px 20px;
  text-align: center;
  min-width: 130px;
  transition: all 0.25s;
}
.pipeline-step:hover {
  border-color: rgba(201,168,76,0.4);
  transform: translateY(-4px);
  box-shadow: 0 8px 32px rgba(201,168,76,0.1);
}
.step-icon {
  width: 40px; height: 40px;
  margin: 0 auto 12px;
  color: #C9A84C;
}
.step-icon :deep(svg) {
  width: 100%; height: 100%;
  stroke: #C9A84C;
}
.step-name { font-size: 13px; font-weight: 700; color: #e0d8c0; margin-bottom: 6px; }
.step-desc { font-size: 11px; color: #6a6558; line-height: 1.4; }

/* ── DOMAINS ── */
.domains { padding: 100px 60px; }
.domain-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 20px; max-width: 900px; margin: 0 auto;
}
.domain-card {
  background: #12141a;
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 14px; padding: 28px 20px; text-align: center;
  transition: all 0.25s; cursor: default;
}
.domain-card:hover {
  border-color: rgba(201,168,76,0.3);
  transform: translateY(-4px);
}
.domain-icon { font-size: 32px; margin-bottom: 12px; }
.domain-name { font-size: 14px; font-weight: 700; color: #e0d8c0; margin-bottom: 8px; }
.domain-example { font-size: 12px; color: #5a5548; line-height: 1.4; }

/* ── STATS ── */
.stats-section {
  padding: 80px 60px;
  background: linear-gradient(135deg, rgba(201,168,76,0.08), rgba(74,124,89,0.06));
  border-top: 1px solid rgba(201,168,76,0.1);
  border-bottom: 1px solid rgba(201,168,76,0.1);
}
.stats-grid {
  display: grid; grid-template-columns: repeat(4, 1fr);
  gap: 40px; max-width: 800px; margin: 0 auto; text-align: center;
}
.stat-value {
  font-family: 'Playfair Display', serif;
  font-size: 48px; font-weight: 800;
  color: #C9A84C; line-height: 1;
  margin-bottom: 8px;
}
.stat-label { font-size: 14px; color: #6a6558; }

/* ── CTA ── */
.cta-section {
  padding: 120px 60px; text-align: center;
}
.cta-section h2 {
  font-family: 'Playfair Display', serif;
  font-size: 40px; color: #f0ece0; margin-bottom: 16px;
}
.cta-section p { color: #6a6558; font-size: 16px; margin-bottom: 40px; }

/* ── FOOTER ── */
.footer {
  padding: 40px 60px;
  border-top: 1px solid rgba(255,255,255,0.06);
  text-align: center;
}
.footer-brand {
  display: inline-flex; align-items: center; gap: 10px;
  font-size: 15px; color: #6a6558; margin-bottom: 8px;
}
.footer-note { font-size: 12px; color: #3a3830; }

/* ── RESPONSIVE ── */
@media (max-width: 900px) {
  .hero { grid-template-columns: 1fr; padding: 100px 24px 60px; }
  .hero-visual { display: none; }
  .nav { padding: 16px 24px; }
  .nav-links a:not(.btn-nav) { display: none; }
  .features, .domains, .stats-section, .cta-section { padding: 60px 24px; }
  .domain-grid { grid-template-columns: repeat(2, 1fr); }
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
