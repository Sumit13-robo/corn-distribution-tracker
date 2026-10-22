/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Public configuration only. Vite variables (VITE_*) are compiled into browser
// code; keys/secrets must never be placed here (docs/ops/ENVIRONMENT_VARIABLES.md).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    // Same-origin dev API: keeps the HttpOnly refresh cookie first-party and
    // matches the relative /api/v1 base used in development.
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: false,
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: false,
    setupFiles: ["./vitest.setup.ts"],
    css: false,
    restoreMocks: true,
  },
});
