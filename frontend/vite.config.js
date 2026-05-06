import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";
import path from "path";

export default defineConfig(({ mode }) => {
  /** 与仓库根目录 `.env` 对齐（`VITE_*` 供前端与 dev 代理共用） */
  const envRoot = path.resolve(__dirname, "..");
  const env = loadEnv(mode, envRoot, "");
  /** 优先 `VITE_CICD_PROXY_TARGET`，否则与 `VITE_CICD_API_BASE` 一致，最后回退本机 :8001 */
  const cicdProxyTarget =
    env.VITE_CICD_PROXY_TARGET || env.VITE_CICD_API_BASE || "http://127.0.0.1:8001";

  return {
    envDir: envRoot,
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
    build: {
      rollupOptions: {
        output: {
          manualChunks(id) {
            const norm = id.split(path.sep).join("/");
            // monaco 内部 vs/editor ↔ vs/language 等存在循环依赖，细拆 manualChunks 会触发 Rollup circular chunk，
            // 反而可能劣化加载。这里保持单一 monaco chunk；运行时配合 ScriptHub 的 defineAsyncComponent + 延迟挂载降低瞬时 CPU。
            if (norm.includes("node_modules/monaco-editor")) {
              return "monaco";
            }
            if (norm.includes("node_modules/echarts")) {
              return "echarts";
            }
            if (norm.includes("node_modules/element-plus")) {
              return "element-plus";
            }
          },
        },
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
        // CI/CD 编排服务（前端 axios base `/cicd-api` →  Strip 前缀后转发至远端端口）
        "/cicd-api": {
          target: cicdProxyTarget,
          changeOrigin: true,
          rewrite: (p) => p.replace(/^\/cicd-api/, ""),
          timeout: 120_000,
          proxyTimeout: 120_000,
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
  };
});
