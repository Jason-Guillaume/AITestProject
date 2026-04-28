import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import path from "path";

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  // 依赖预构建阶段由 esbuild 生成的 *.map 在部分版本下会出现 sources 为空，
  // Firefox 会报「No sources are declared in this source map」。关闭预构建 sourcemap 可消除该噪音。
  optimizeDeps: {
    esbuildOptions: {
      sourcemap: false,
    },
  },
  server: {
    port: 5173,
    open: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        // 长连接 SSE：避免 dev server 代理过早断开；流式 body 仍逐段转发
        timeout: 600_000,
        proxyTimeout: 600_000,
      },
      "/media": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/ws": {
        target: "http://127.0.0.1:8000",
        ws: true,
        changeOrigin: true,
      },
      // AI API Proxy - Bypass CORS for direct AI model testing
      "/ai-api": {
        target: "https://api.iamhc.cn",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/ai-api/, ""),
        secure: true,
        timeout: 30_000,
      },
    },
  },
});
