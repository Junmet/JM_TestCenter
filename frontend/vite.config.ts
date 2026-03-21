import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// 开发环境反向代理：把 /api 转发到后端，避免前端跨域配置
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8080",
        changeOrigin: true
      }
    }
  }
});

