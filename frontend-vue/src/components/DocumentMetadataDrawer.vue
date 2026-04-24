<template>
  <Teleport to="body">
    <!-- Backdrop -->
    <Transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="isOpen"
        class="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
        @click="close"
      />
    </Transition>

    <!-- Console Panel -->
    <Transition
      enter-active-class="transition duration-350 ease-out"
      enter-from-class="translate-x-full"
      enter-to-class="translate-x-0"
      leave-active-class="transition duration-250 ease-in"
      leave-from-class="translate-x-0"
      leave-to-class="translate-x-full"
    >
      <div
        v-if="isOpen && data"
        class="fixed right-0 top-0 h-full z-50 flex flex-col bg-white border-l border-rule shadow-[-24px_0_60px_rgba(0,0,0,0.12)]"
        style="width: min(85vw, 1280px); position: fixed; right: 0; top: 0; height: 100dvh; z-index: 50;"
      >
        <!-- ── Header ── -->
        <div class="flex items-center justify-between px-8 py-5 border-b border-rule bg-paper shrink-0">
          <div class="flex items-center gap-4">
            <!-- Badge loại văn bản -->
            <span class="font-meta text-[9px] uppercase tracking-[0.22em] text-gold font-bold border border-gold/30 bg-gold/5 px-2.5 py-1 rounded-full">
              {{ data.law_type || 'Văn bản pháp luật' }}
            </span>
            <div class="w-px h-4 bg-rule" />
            <span class="font-meta text-[9px] uppercase tracking-[0.2em] text-gray-400">
              Legal Document Console
            </span>
          </div>

          <button
            @click="close"
            class="w-8 h-8 flex items-center justify-center rounded-full text-gray-400 hover:text-ink hover:bg-gray-100 transition-all"
            aria-label="Đóng"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24"
              fill="none" stroke="currentColor" stroke-width="2"
              stroke-linecap="round" stroke-linejoin="round">
              <path d="M18 6 6 18"/><path d="m6 6 12 12"/>
            </svg>
          </button>
        </div>

        <!-- ── Document Title Bar ── -->
        <div class="px-8 py-6 border-b border-rule bg-white shrink-0">
          <p class="font-meta text-[10px] uppercase tracking-widest text-gold font-bold mb-1">Văn bản được trích dẫn</p>
          <h2 class="font-display text-2xl font-bold italic text-ink leading-snug">
            {{ data.law_name || 'Không rõ tên văn bản' }}
          </h2>
          <div class="flex items-center gap-3 mt-2">
            <span class="font-meta text-xs text-gray-500">{{ data.document_code }}</span>
            <span v-if="data.article" class="text-gray-300">·</span>
            <span v-if="data.article" class="font-meta text-xs text-gray-500">
              {{ data.article }}{{ data.clause ? ` – ${data.clause}` : '' }}
            </span>
          </div>
        </div>

        <!-- ── Body: 2-Column Console ── -->
        <div class="flex flex-1 min-h-0">

          <!-- LEFT: Metadata Panel -->
          <div class="w-[380px] shrink-0 flex flex-col border-r border-rule overflow-y-auto">

            <!-- Metadata fields -->
            <div class="p-8 space-y-5 flex-1">
              <div
                v-for="(item, idx) in displayFields"
                :key="idx"
                class="group"
              >
                <div class="font-meta text-[9px] uppercase tracking-[0.18em] text-gray-400 mb-1.5 group-hover:text-gold transition-colors">
                  {{ item.label }}
                </div>
                <div
                  class="font-sans text-sm text-ink pl-3 border-l-2 border-rule group-hover:border-gold transition-all py-0.5"
                  :class="item.mono ? 'font-mono text-gold font-bold' : 'font-medium'"
                >
                  <span v-if="item.value">{{ item.value }}</span>
                  <span v-else class="text-gray-400 italic text-xs">N/A</span>
                </div>
              </div>

              <!-- Status -->
              <div class="pt-3 border-t border-rule">
                <div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-50 border border-emerald-200">
                  <div class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  <span class="font-meta text-[9px] uppercase font-bold text-emerald-700 tracking-wider">Đang áp dụng</span>
                </div>
              </div>

              <!-- Excerpt: "Bằng chứng đã được bóc tách" -->
              <div v-if="data.content" class="mt-4">
                <div class="font-meta text-[10px] uppercase tracking-[0.15em] text-gold font-bold mb-2 flex items-center gap-2">
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="text-gold">
                    <path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"/>
                    <path d="m9 12 2 2 4-4"/>
                  </svg>
                  Bằng chứng đã được bóc tách
                </div>
                <div class="bg-[#FFFBEB] border-l-[6px] border-[#F59E0B] rounded-r-lg p-5 shadow-sm relative overflow-hidden">
                  <div class="absolute -top-6 -right-6 w-24 h-24 bg-[#FCD34D] rounded-full blur-2xl opacity-40"></div>
                  <div class="font-meta text-[9px] uppercase tracking-widest text-amber-700 mb-2 font-bold relative z-10">
                    Trích xuất từ trang {{ data.page_number || '?' }} · Phân tích bởi AI
                  </div>
                  <p class="font-serif italic text-base leading-relaxed text-amber-950 relative z-10 font-bold mix-blend-multiply">
                    <mark class="bg-[#FEF08A] text-amber-950 px-1 rounded-sm leading-8">"{{ data.content }}"</mark>
                  </p>
                </div>
              </div>
            </div>

            <!-- Footer -->
            <div class="p-6 border-t border-rule bg-paper shrink-0">
              <button
                @click="close"
                class="w-full py-3 bg-ink text-white font-sans text-sm font-semibold hover:bg-gold transition-all duration-300 rounded-sm"
              >
                Hoàn tất đối chiếu
              </button>
            </div>
          </div>

          <!-- RIGHT: PDF Viewer -->
          <div class="flex-1 min-w-0 flex flex-col bg-neutral-800">
            <!-- PDF toolbar -->
            <div class="flex items-center justify-between px-5 py-3 bg-neutral-900 shrink-0">
              <div class="flex items-center gap-2">
                <div class="w-3 h-3 rounded-full bg-red-500/70" />
                <div class="w-3 h-3 rounded-full bg-yellow-500/70" />
                <div class="w-3 h-3 rounded-full bg-emerald-500/70" />
                <span class="ml-3 font-meta text-[11px] text-neutral-300 uppercase tracking-widest font-bold">
                  Bối cảnh gốc <span class="text-neutral-500 normal-case tracking-normal font-normal ml-1">(Văn bản PDF)</span>
                </span>
              </div>
              <div v-if="data.page_number" class="flex items-center gap-1.5">
                <div class="w-1.5 h-1.5 rounded-full bg-gold animate-pulse" />
                <span class="font-meta text-[9px] text-gold uppercase tracking-widest">
                  Trang {{ data.page_number }}
                </span>
              </div>
            </div>

            <!-- iframe or placeholder -->
            <div class="flex-1 min-h-0 relative bg-neutral-800">
              <iframe
                v-if="pdfUrl"
                :src="pdfUrl"
                class="w-full h-full border-none"
                title="Văn bản gốc PDF"
              ></iframe>
              <div v-else class="absolute inset-0 flex flex-col items-center justify-center gap-4 text-neutral-500">
                <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24"
                  fill="none" stroke="currentColor" stroke-width="1"
                  stroke-linecap="round" stroke-linejoin="round" class="opacity-30">
                  <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>
                  <path d="M14 2v4a2 2 0 0 0 2 2h4"/>
                  <path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>
                </svg>
                <div class="text-center">
                  <p class="font-meta text-[11px] uppercase tracking-[0.2em] text-neutral-400 mb-1">PDF CHƯA CÓ SẴN TRÊN SERVER</p>
                  <p class="font-sans text-xs text-neutral-500">
                    Cần ingest PDF và trả về <code class="text-gold/80 bg-neutral-700 px-1 rounded">file_name</code> hoặc <code class="text-gold/80 bg-neutral-700 px-1 rounded">pdf_url</code> từ backend
                  </p>
                </div>
              </div>
            </div>
          </div>

        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  isOpen: { type: Boolean, default: false },
  data: { type: Object, default: null }
})

const emit = defineEmits(['close'])
const close = () => emit('close')

const pdfUrl = computed(() => {
  if (!props.data) return null;
  
  const baseUrl = "http://localhost:8000"; // URL của FastAPI
  const page = props.data.page_number || 1;
  
  // Dùng pdf_url từ backend nếu có (backend đã xử lý path)
  if (props.data.pdf_url) {
    return `${baseUrl}${props.data.pdf_url}#page=${page}&view=FitH`;
  }
  
  // Hoặc dùng file_name như hướng dẫn của Teach Lead
  if (props.data.file_name) {
    return `${baseUrl}/pdf-files/${props.data.file_name}#page=${page}&view=FitH`;
  }
  
  return null;
});

const displayFields = computed(() => {
  if (!props.data) return []
  return [
    { label: 'Mã hiệu văn bản', value: props.data.document_code, mono: true },
    { label: 'Loại văn bản', value: props.data.law_type, mono: false },
    { label: 'Điều / Khoản trích dẫn',
      value: props.data.article
        ? props.data.article + (props.data.clause ? ` – ${props.data.clause}` : '')
        : null,
      mono: false },
    { label: 'Ngày có hiệu lực', value: props.data.effective_date, mono: false },
    { label: 'Vị trí trang PDF',
      value: props.data.page_number ? `Trang ${props.data.page_number}` : null,
      mono: false },
  ]
})
</script>
