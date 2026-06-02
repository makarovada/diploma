import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

const apiProxyTarget = process.env.VITE_API_PROXY_TARGET ?? "http://127.0.0.1:8080";
/** В Docker SPA монтируется под `/ui/` на FastAPI — задаётся через `VITE_BASE` при сборке образа. */
const baseRaw = process.env.VITE_BASE ?? "/";
const base = baseRaw === "/" ? "/" : baseRaw.endsWith("/") ? baseRaw : `${baseRaw}/`;

export default defineConfig({
  base,
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      "/api": {
        target: apiProxyTarget,
        changeOrigin: true,
      },
    },
  },
});
