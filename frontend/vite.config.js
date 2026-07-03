import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import Icons from "unplugin-icons/vite";
import path from "path";

export default defineConfig({
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
      "^/(api|login|app|assets|files|private)": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  // frappe-ui is no longer imported (we use a tiny fetch-based RPC client), so
  // no special dep-optimization handling is needed.
});
