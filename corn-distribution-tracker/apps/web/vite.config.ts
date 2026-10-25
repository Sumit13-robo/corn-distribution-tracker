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
    // Quick tunnels provide the HTTPS origin required by phone browsers for
    // geolocation. Add other dev hosts explicitly rather than allowing every
    // Host header.
    allowedHosts: [".trycloudflare.com"],
    // Same-origin dev API: keeps the HttpOnly session cookie first-party and
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
    include: ["src/**/*.test.{ts,tsx}"],
    css: false,
    restoreMocks: true,
  },
});
