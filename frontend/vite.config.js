import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";
import Icons from "unplugin-icons/vite";
import path from "path";

export default defineConfig(({ mode }) => {
  // Load ALL env vars (incl. non-VITE_) from .env.local so LP_BACKEND / LP_API_TOKEN
  // are available to the proxy below without ever reaching the client bundle.
  const env = loadEnv(mode, process.cwd(), "");
  // Two SPAs from one source tree. The souk portal (/souk) is its own app —
  // own entry, shell, login and bundle — like the supplier portal, so the
  // buyer's phone never downloads the warehouse floor (2026-11-17). Rollup
  // cannot inline dynamic imports across two inputs, hence two passes:
  // `npm run build` runs this config once plain and once with LP_ENTRY=souk.
  const souk = process.env.LP_ENTRY === "souk";
  const NAME = souk ? "logistics_souk" : "logistics_portal";
  return {
  plugins: [vue(), Icons()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  // Chunk URLs must resolve against frappe's static mount, not the page URL.
  base: mode === "production" ? "/assets/logistics_portal/" : "/",
  build: {
    outDir: "../logistics_portal/public",
    emptyOutDir: false,
    target: "es2015",
    cssCodeSplit: false,
    rollupOptions: {
      input: path.resolve(__dirname, souk ? "src/souk/main.js" : "src/main.js"),
      output: {
        // ONE self-contained bundle. Route-level code splitting was reverted:
        // frappe serves static public/ files and busts the entry via
        // include_script(...?ver=<hash>), but hashed lazy chunks aren't
        // coordinated with that — a browser holding a stale entry requests a
        // deleted chunk hash and the route renders blank. A single bundle
        // (frappe ?ver-busted, then cached) is the robust trade for a
        // self-hosted team tool; the real load win was the DB indexes.
        entryFileNames: `${NAME}.bundle.js`,
        assetFileNames: `${NAME}.bundle.css`,
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
