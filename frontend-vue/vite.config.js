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
    // Bắt buộc dùng polling khi chạy trong Docker trên Windows host
    watch: {
      usePolling: true,
      interval: 500,
    },
    proxy: {
      // Admin routes → FastAPI trực tiếp (port 8000) — FastAPI tự xác thực JWT
      "/api/admin": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
      // Tất cả /api còn lại → Spring Boot (port 8081)
      "/api": {
        target: "http://localhost:8081",
        changeOrigin: true,
      },
    },
  },
});
