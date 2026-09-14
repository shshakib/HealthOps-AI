import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  base: "/",
  server: {
    proxy: {
      "/api": "http://127.0.0.1:18000",
      "/health": "http://127.0.0.1:18000",
    },
  },
  build: { outDir: "../src/healthops/static", emptyOutDir: true },
});
