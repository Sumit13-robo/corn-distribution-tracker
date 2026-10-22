import { execFileSync } from "node:child_process";
import { randomBytes } from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { e2e } from "./support/config";

const webDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = path.resolve(webDir, "../..");
const apiDir = path.resolve(repoRoot, "apps/api");
const python = process.env.E2E_PYTHON ?? path.join(repoRoot, ".venv/bin/python");
const storageDir = path.resolve(process.env.E2E_LOCAL_STORAGE_DIR ?? "/tmp/corn-tracker-e2e-storage");
const stateDir = path.join(webDir, "e2e/.state");
const credentialsPath = path.join(stateDir, "credentials.json");
const e2eSecretKey = randomBytes(48).toString("hex");

/**
 * Playwright starts its web servers, then runs this setup, then the setup
 * project. `e2e/support/run-e2e.mjs` recreates and migrates the isolated E2E
 * database before the servers start; this file bootstraps per-run credentials
 * and the first administrator before any HTTP seed calls.
 */
export default function globalSetup(): void {
  if (!fs.existsSync(python)) {
    throw new Error(
      `E2E requires the repository virtualenv at ${python}. ` +
        "Run `make api-install`, or set E2E_PYTHON to a Python with the API requirements installed.",
    );
  }

  fs.mkdirSync(storageDir, { recursive: true });
  fs.rmSync(stateDir, { recursive: true, force: true });
  fs.mkdirSync(stateDir, { recursive: true, mode: 0o700 });

  const adminPassword = randomBytes(24).toString("base64url");
  const distributorPassword = randomBytes(24).toString("base64url");
  fs.writeFileSync(
    credentialsPath,
    JSON.stringify(
      {
        adminEmail: e2e.adminEmail,
        adminPassword,
        distributorEmail: e2e.distributorEmail,
        distributorPassword,
      },
      null,
      2,
    ),
    { mode: 0o600 },
  );

  const baseEnv = {
    ...process.env,
    DJANGO_SETTINGS_MODULE: "config.settings",
    APP_ENV: "test",
    DATABASE_URL: e2e.databaseURL,
    SECRET_KEY: e2eSecretKey,
    COOKIE_SECURE: "false",
    COOKIE_SAMESITE: "Lax",
    STORAGE_MODE: "local",
    LOCAL_STORAGE_DIR: storageDir,
    PUBLIC_BASE_URL: e2e.baseURL,
    CORS_ALLOWED_ORIGINS: e2e.baseURL,
    CSRF_TRUSTED_ORIGINS: e2e.baseURL,
    LOG_LEVEL: "WARNING",
    // Do not retain PostgreSQL connections between requests in E2E.
    DB_CONN_MAX_AGE: "0",
  };

  execFileSync(python, ["manage.py", "migrate", "--noinput"], {
    cwd: apiDir,
    env: baseEnv,
    stdio: "inherit",
  });

  execFileSync(
    python,
    [
      "manage.py",
      "create_admin",
      "--email",
      e2e.adminEmail,
      "--display-name",
      "E2E Administrator",
      "--password-env",
      "E2E_ADMIN_PASSWORD",
    ],
    {
      cwd: apiDir,
      env: { ...baseEnv, E2E_ADMIN_PASSWORD: adminPassword },
      stdio: "inherit",
    },
  );
}
