import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  server: {
    host: true,
    port: 5173,
    // 端口被占用时自动换端口，避免 dev 直接退出导致“打不开”
    strictPort: false,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/uploads": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  // npm run preview 时同样需要把 /api 转到后端，否则页面能开但数据全失败
  preview: {
    host: true,
    port: 4173,
    strictPort: false,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/uploads": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
