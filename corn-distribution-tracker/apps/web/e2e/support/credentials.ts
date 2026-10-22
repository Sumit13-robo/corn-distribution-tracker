import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { e2e } from "./config";

export interface E2ECredentials {
  adminEmail: string;
  adminPassword: string;
  distributorEmail: string;
  distributorPassword: string;
}

const credentialsPath = path.join(
  path.dirname(fileURLToPath(import.meta.url)),
  "../.state/credentials.json",
);

let cached: E2ECredentials | null = null;

/** Read the per-run credentials written by global setup. Call inside tests. */
export function credentials(): E2ECredentials {
  if (cached) return cached;
  if (!fs.existsSync(credentialsPath)) {
    throw new Error(
      `E2E credentials not found at ${credentialsPath}; run via \`npm run test:e2e\` so global setup can create them.`,
    );
  }
  cached = JSON.parse(fs.readFileSync(credentialsPath, "utf8")) as E2ECredentials;
  if (cached.adminEmail !== e2e.adminEmail || cached.distributorEmail !== e2e.distributorEmail) {
    throw new Error("E2E credentials file does not match the configured test identities.");
  }
  return cached;
}
