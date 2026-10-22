/**
 * Test-only identifiers and paths. Passwords are generated per run by
 * `global-setup.ts` and stored in the gitignored `.state/` directory, so no
 * credential is committed or reused between runs.
 *
 * The database defaults to a local PostgreSQL instance. Set E2E_DATABASE_URL
 * for a different host/user (for example CI service containers).
 */

export const e2e = {
  baseURL: "http://127.0.0.1:5173",
  databaseURL: process.env.E2E_DATABASE_URL ?? "postgresql+psycopg://localhost:5432/corn_tracker_e2e",
  adminEmail: "admin@e2e.example.org",
  distributorEmail: "distributor@e2e.example.org",
  campaignCode: "E2E-CAMPAIGN",
  siteCode: "E2E-SITE-1",
  siteLatitude: "4.8510000",
  siteLongitude: "31.5820000",
  evidenceName: "e2e-evidence.png",
  evidenceMimeType: "image/png",
} as const;

/** 32x24 PNG generated with Pillow; valid for server-side decoding/sniffing. */
export const EVIDENCE_PNG_BASE64 =
  "iVBORw0KGgoAAAANSUhEUgAAACAAAAAYCAIAAAAUMWhjAAAAJklEQVR4nGNU6lZioCVgoqnpoxaMWjBqwagFoxaMWjBqwagFVAMAPJoA/0rKqkoAAAAASUVORK5CYII=";
