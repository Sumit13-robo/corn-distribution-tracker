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

/**
 * Runs after Playwright starts the web/API processes and before the setup
 * project. The API does not open a database connection at import time, so it
 * is safe to recreate the database here. Credentials are generated per run and
 * kept only in the gitignored state directory.
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

  const baseEnv = { ...process.env, DATABASE_URL: e2e.databaseURL };

  execFileSync(python, [path.join(webDir, "e2e/support/prepare_db.py")], {
    cwd: repoRoot,
    env: { ...process.env, E2E_DATABASE_URL: e2e.databaseURL },
    stdio: "inherit",
  });

  execFileSync(python, ["-m", "alembic", "upgrade", "head"], {
    cwd: apiDir,
    env: baseEnv,
    stdio: "inherit",
  });

  execFileSync(
    python,
    ["-m", "app.cli.create_admin", "--email", e2e.adminEmail, "--display-name", "E2E Administrator"],
    {
      cwd: apiDir,
      env: {
        ...baseEnv,
        INITIAL_ADMIN_PASSWORD_ENV: "E2E_ADMIN_PASSWORD",
        E2E_ADMIN_PASSWORD: adminPassword,
      },
      stdio: "inherit",
    },
  );
}
