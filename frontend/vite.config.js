import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";
import path from "path";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  // Override per machine via .env.local: FRAPPE_DEV_URL=http://localhost:8000
  const target = env.FRAPPE_DEV_URL || process.env.FRAPPE_DEV_URL || "https://admin.justyol.com";

  return {
    plugins: [vue()],
    resolve: {
      alias: { "@": path.resolve(__dirname, "./src") },
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
      // Different port from purchasing (8081) so both can run side-by-side.
      port: 8082,
      proxy: {
        "^/(api|login|app|assets|socket\\.io)": {
          target,
          changeOrigin: true,
          secure: false,
          cookieDomainRewrite: { "*": "" },
          followRedirects: true,
        },
      },
    },
  };
});
