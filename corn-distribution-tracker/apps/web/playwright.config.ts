import { randomBytes } from "node:crypto";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { defineConfig, devices } from "@playwright/test";

import { e2e } from "./e2e/support/config";

const webDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(webDir, "../..");
const apiDir = path.resolve(repoRoot, "apps/api");
const python = process.env.E2E_PYTHON ?? path.join(repoRoot, ".venv/bin/python");
const storageDir = path.resolve(process.env.E2E_LOCAL_STORAGE_DIR ?? "/tmp/corn-tracker-e2e-storage");
/** Per-run test secret; never a committed credential or reused signing key. */
const e2eSecretKey = randomBytes(32).toString("hex");

/**
 * Browser E2E: real Vite dev server + real Django/DRF/PostgreSQL, isolated E2E
 * database and private local evidence directory. Global setup recreates the
 * database, migrates it with Django and bootstraps the first admin; the setup
 * project then creates campaign/site/invitation/assignment/stock through the
 * public API so tests exercise the product's actual contracts.
 */
export default defineConfig({
  testDir: "./e2e",
  globalSetup: "./e2e/global-setup.ts",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: e2e.baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "off",
    geolocation: {
      latitude: Number(e2e.siteLatitude),
      longitude: Number(e2e.siteLongitude),
      accuracy: 10,
    },
    permissions: ["geolocation"],
  },
  projects: [
    { name: "setup", testMatch: /setup\.spec\.ts/ },
    {
      name: "chromium",
      testMatch: /.*\.spec\.ts/,
      testIgnore: /setup\.spec\.ts/,
      dependencies: ["setup"],
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [
    {
      command: `"${python}" manage.py runserver 127.0.0.1:8000 --noreload`,
      cwd: apiDir,
      url: "http://127.0.0.1:8000/health/live",
      reuseExistingServer: false,
      timeout: 120_000,
      stdout: "pipe",
      stderr: "pipe",
      env: {
        ...process.env,
        DJANGO_SETTINGS_MODULE: "config.settings",
        APP_ENV: "test",
        DATABASE_URL: e2e.databaseURL,
        SECRET_KEY: e2eSecretKey,
        CORS_ALLOWED_ORIGINS: e2e.baseURL,
        CSRF_TRUSTED_ORIGINS: e2e.baseURL,
        COOKIE_SECURE: "false",
        COOKIE_SAMESITE: "Lax",
        STORAGE_MODE: "local",
        LOCAL_STORAGE_DIR: storageDir,
        PUBLIC_BASE_URL: e2e.baseURL,
        LOG_LEVEL: "WARNING",
        DB_CONN_MAX_AGE: "0",
      },
    },
    {
      command: "npm run dev -- --host 127.0.0.1",
      cwd: webDir,
      url: e2e.baseURL,
      reuseExistingServer: false,
      timeout: 120_000,
      stdout: "pipe",
      stderr: "pipe",
      env: {
        ...process.env,
        VITE_API_BASE_URL: "/api/v1",
      },
    },
  ],
});
