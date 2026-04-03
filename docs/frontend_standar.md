1. Hiệu chỉnh Design Tokens (Legal DNA)
Chúng ta sẽ ánh xạ các token của phong cách "Serif" sang các thực thể pháp lý:
Token	Giá trị	Ý nghĩa trong Domain Legal
background	#FAFAF8	Ivory Paper: Tạo cảm giác như đọc văn bản trên giấy thật.
foreground	#1A1A1A	Ink Black: Màu mực in truyền thống, độ tương phản cao, dễ đọc.
accent	#B8860B	Seal Gold: Màu của con dấu và bìa da pháp lý, dùng cho các Điều luật.
border	#E8E4DF	Editorial Rules: Các đường kẻ phân cách chương, mục trong văn bản.
font-serif	Playfair Display	The Authority: Dùng cho tiêu đề "Điều 1", "Luật Đất Đai".
font-mono	IBM Plex Mono	The Reference: Dùng cho mã hiệu văn bản, số trang, ngày ban hành.
2. Cấu hình Tailwind CSS (Tối ưu cho Legal)
Tôi đã tinh chỉnh tailwind.config.js để tích hợp các pattern "Serif" nhưng vẫn đảm bảo tính ứng dụng cao cho việc tra cứu:
code
JavaScript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        paper: '#FAFAF8',
        ink: '#1A1A1A',
        gold: {
          DEFAULT: '#B8860B', // Burnished Gold
          soft: 'rgba(184, 134, 11, 0.1)', // Màu nền highlight
        },
        rule: '#E8E4DF',
      },
      fontFamily: {
        display: ['"Playfair Display"', 'serif'], // Heading pháp lý
        body: ['"Source Sans 3"', 'sans-serif'], // Nội dung tư vấn
        meta: ['"IBM Plex Mono"', 'monospace'], // Trích dẫn/Mã hiệu
      },
      letterSpacing: {
        'legal-meta': '0.15em', // Cho phong cách Small Caps
      },
      backgroundImage: {
        'legal-texture': "url('https://www.transparenttextures.com/patterns/natural-paper.png')",
      }
    },
  },
}
3. Thành phần Signature: "Hallucination-Fighting UI"
Để giảm ảo tưởng, giao diện phải làm cho người dùng phân biệt được đâu là "Lời AI nói" và đâu là "Luật thật nói".
A. Component: LegalSourceCard.vue (Bằng chứng trích dẫn)
Dùng phong cách Asymmetric Layout và Rule Lines để trình bày phần trích dẫn.
code
Vue
<template>
  <div class="border-t border-rule pt-4 pb-6 group">
    <!-- Meta info: Small Caps & Mono -->
    <div class="flex items-center gap-3 mb-2">
      <span class="font-meta text-[10px] uppercase tracking-legal-meta text-gold font-bold">
        [TRÍCH DẪN {{ index }}]
      </span>
      <span class="h-px flex-1 bg-rule/50"></span>
      <span class="font-meta text-[10px] text-muted-foreground italic">
        Trang {{ page }}
      </span>
    </div>

    <!-- Article Header: Playfair Serif -->
    <h4 class="font-display text-lg font-bold text-ink group-hover:text-gold transition-colors">
      {{ lawName }} — {{ article }}
    </h4>

    <!-- Content: High-contrast Sans -->
    <p class="mt-2 font-body text-sm leading-relaxed text-ink/80 italic border-l-2 border-gold/30 pl-4 py-1">
      "...{{ content }}..."
    </p>
  </div>
</template>
B. Component: AIConsultationBubble.vue (Nội dung tư vấn)
AI trả lời trên nền Ivory, sử dụng Typography tinh tế để tạo cảm giác uy tín.
code
Vue
<template>
  <div class="relative py-12 px-6 border-b border-rule bg-paper/50">
    <div class="max-w-3xl mx-auto">
      <!-- Label phong cách Editorial -->
      <div class="mb-8 flex items-center gap-4">
        <span class="font-meta text-xs font-medium uppercase tracking-legal-meta text-gold">
          Tư vấn từ hệ thống AI
        </span>
        <span class="h-px flex-1 bg-rule"></span>
      </div>

      <!-- AI Content -->
      <div class="font-body text-lg leading-[1.8] text-ink prose prose-neutral">
        <slot />
      </div>
      
      <!-- Citation Footer -->
      <div class="mt-8 flex gap-3 flex-wrap">
        <span class="font-meta text-[10px] text-muted-foreground mr-2">CĂN CỨ:</span>
        <button v-for="c in sources" :key="c.id" 
                class="px-2 py-1 border border-rule text-[10px] font-meta hover:border-gold transition-all">
          {{ c.article_code }}
        </button>
      </div>
    </div>
  </div>
</template>
4. Bố cục tổng thể (Asymmetric Split-View)
Theo triết lý Serif, chúng ta sẽ không dùng layout cân đối 50/50 mà dùng tỉ lệ Editorial (60/40).
code
Vue
<template>
  <div class="h-screen flex bg-paper bg-legal-texture overflow-hidden">
    <!-- Cột trái: Luồng Chat (Tư vấn) -->
    <main class="flex-1 overflow-y-auto border-r border-rule scroll-smooth">
      <nav class="sticky top-0 bg-paper/90 backdrop-blur-sm border-b border-rule z-10 px-8 py-4 flex justify-between items-center">
        <h1 class="font-display text-xl italic font-bold text-ink">Legal Assistant v1.0</h1>
        <div class="font-meta text-[10px] tracking-widest text-gold uppercase font-bold">Verified by RAG</div>
      </nav>
      
      <div class="chat-container">
        <!-- Các bubble chat ở đây -->
      </div>
    </main>

    <!-- Cột phải: Thư viện bằng chứng (The Truth) -->
    <aside class="w-[400px] bg-white p-8 overflow-y-auto">
      <header class="mb-12">
        <p class="font-meta text-[10px] uppercase tracking-widest text-gold mb-2">Evidence Viewer</p>
        <h2 class="font-display text-2xl border-b border-ink pb-4">Cơ sở pháp lý gốc</h2>
      </header>

      <div class="space-y-8">
        <!-- Hiển thị nội dung chi tiết của Điều luật AI vừa trích dẫn -->
        <LegalSourceCard 
          v-for="(source, i) in activeSources" 
          :key="i"
          :index="i+1"
          v-bind="source"
        />
      </div>
    </aside>
  </div>
</template>