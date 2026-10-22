/**
 * Prepare the disposable E2E database *before* Playwright starts its web
 * servers. Playwright launches `webServer` processes before `globalSetup`, so a
 * fresh checkout would otherwise start Django against a missing database.
 */
import { spawnSync } from "node:child_process";
import { randomBytes } from "node:crypto";
import path from "node:path";
import { fileURLToPath } from "node:url";

const supportDir = path.dirname(fileURLToPath(import.meta.url));
const webDir = path.resolve(supportDir, "../..");
const repoRoot = path.resolve(webDir, "../..");
const python = process.env.E2E_PYTHON ?? path.join(repoRoot, ".venv/bin/python");
const databaseURL =
  process.env.E2E_DATABASE_URL ??
  "postgresql+psycopg://corn:corn@localhost:5432/corn_tracker_e2e";

const baseEnv = {
  ...process.env,
  DJANGO_SETTINGS_MODULE: "config.settings",
  APP_ENV: "test",
  DATABASE_URL: databaseURL,
  SECRET_KEY: randomBytes(48).toString("hex"),
  COOKIE_SECURE: "false",
  COOKIE_SAMESITE: "Lax",
  STORAGE_MODE: "local",
  LOCAL_STORAGE_DIR:
    process.env.E2E_LOCAL_STORAGE_DIR ?? "/tmp/corn-tracker-e2e-storage",
  DB_CONN_MAX_AGE: "0",
};

function run(command, args, cwd) {
  const result = spawnSync(command, args, {
    cwd,
    env: baseEnv,
    stdio: "inherit",
  });
  if (result.error) throw result.error;
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

run(python, [path.join(webDir, "e2e/support/prepare_db.py")], repoRoot);
run(python, ["manage.py", "migrate", "--noinput"], path.join(repoRoot, "apps/api"));

const playwright = path.join(webDir, "node_modules/.bin/playwright");
const result = spawnSync(playwright, ["test", ...process.argv.slice(2)], {
  cwd: webDir,
  env: { ...process.env, E2E_DATABASE_URL: databaseURL },
  stdio: "inherit",
});
if (result.error) throw result.error;
process.exit(result.status ?? 1);
