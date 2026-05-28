import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import tailwindcss from "@tailwindcss/vite";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    // Polling chỉ cần khi chạy Vite trong Docker (volume mount trên Windows)
    watch:
      process.env.VITE_DOCKER === "1"
        ? { usePolling: true, interval: 500 }
        : undefined,
    proxy: {
      // ── FastAPI :8000 routes (phải đặt TRƯỚC rule /api chung) ──────────────
      // Admin routes → FastAPI (strip /api prefix)
      "/api/admin": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
      // RAGAS GET status polling — must come BEFORE /api/ai catch-all
      "/api/ai/evaluate/ragas/status": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
        proxyTimeout: 10000,
        timeout: 10000,
      },
      // AI query/compare/evaluate → FastAPI (strip /api prefix)
      "/api/ai": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
        proxyTimeout: 300000, // 300s — Groq rate-limit retry + Gemini fallback cần đủ thời gian
        timeout: 300000,
      },
      // Health check → FastAPI
      "/api/health": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
      // ── Spring Boot :8081 routes ────────────────────────────────────────────
      // Tất cả /api còn lại (auth, users, history...) → Spring Boot
      "/api": {
        target: "http://127.0.0.1:8081",
        changeOrigin: true,
      },
    },
  },
});
