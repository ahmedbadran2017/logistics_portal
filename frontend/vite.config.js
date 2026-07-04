import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";
import Icons from "unplugin-icons/vite";
import path from "path";

export default defineConfig(({ mode }) => {
  // Load ALL env vars (incl. non-VITE_) from .env.local so LP_BACKEND / LP_API_TOKEN
  // are available to the proxy below without ever reaching the client bundle.
  const env = loadEnv(mode, process.cwd(), "");
  return {
  plugins: [vue(), Icons()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    outDir: "../logistics_portal/public",
    emptyOutDir: false,
    target: "es2015",
    cssCodeSplit: false,
    rollupOptions: {
      input: path.resolve(__dirname, "src/main.js"),
      output: {
        entryFileNames: "logistics_portal.bundle.js",
        assetFileNames: "logistics_portal.bundle.css",
        inlineDynamicImports: true,
      },
    },
  },
  server: {
    port: 8080,
    proxy: {
      // Dev proxy. Point at a remote Frappe by setting LP_BACKEND (e.g. the live
      // site) and authenticate with LP_API_TOKEN="<api_key>:<api_secret>". These
      // are read here in the Node/proxy layer only — NOT the VITE_ prefix — so the
      // token never reaches the browser bundle. Token auth also bypasses CSRF.
      "^/(api|login|app|assets|files|private)": {
        target: env.LP_BACKEND || "http://localhost:8000",
        changeOrigin: true,
        secure: true,
        configure(proxy) {
          const token = env.LP_API_TOKEN;
          if (token) {
            proxy.on("proxyReq", (proxyReq) => {
              proxyReq.setHeader("Authorization", `token ${token}`);
            });
          }
        },
      },
    },
  },
  };
});
