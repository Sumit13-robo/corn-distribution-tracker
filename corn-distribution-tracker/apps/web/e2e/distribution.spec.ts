import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

import { e2e, EVIDENCE_PNG_BASE64 } from "./support/config";
import { credentials } from "./support/credentials";

/**
 * End-to-end proof of the critical distributor/reviewer loop against real
 * PostgreSQL, real Django/DRF, and the real SPA:
 *   1. session-cookie restore + role guard,
 *   2. photo/geo delivery submission,
 *   3. reviewer approval that posts the stock movement,
 *   4. admin delivery map shows the approved location (not sites),
 *   5. distributor sees the approved record,
 *   6. offline draft honestly QUEUED, then synced on reconnect.
 *
 * Tests are serial because they form one business workflow and share one
 * isolated database.
 */
test.describe.configure({ mode: "serial" });

interface StoredDraft {
  state: string;
  idempotencyKey: string;
  submittedRecordId: string | null;
}

async function readDrafts(page: Page): Promise<StoredDraft[]> {
  return page.evaluate(() => {
    const key = Object.keys(window.localStorage).find((candidate) =>
      candidate.startsWith("corn-tracker:drafts:v1:"),
    );
    if (!key) return [];
    try {
      return JSON.parse(window.localStorage.getItem(key) ?? "[]") as Array<{
        state: string;
        idempotencyKey: string;
        submittedRecordId: string | null;
      }>;
    } catch {
      return [];
    }
  });
}

async function signIn(page: Page, role: "admin" | "distributor"): Promise<void> {
  const creds = credentials();
  const email = role === "admin" ? creds.adminEmail : creds.distributorEmail;
  const password = role === "admin" ? creds.adminPassword : creds.distributorPassword;
  await page.goto("/login");
  await page.locator("#login-email").fill(email);
  await page.locator("#login-password").fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  // Do not race the login request with a subsequent navigation.
  await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible();
}

async function openFirstAssignment(page: Page): Promise<void> {
  await page.getByRole("link", { name: "Update a site" }).click();
  await expect(page).toHaveURL(/\/my-sites$/);
  await page.getByRole("link", { name: "New delivery update" }).first().click();
  await expect(page).toHaveURL(/\/deliver\/new\?assignment=/);
  await expect(page.getByRole("heading", { name: "New delivery update" })).toBeVisible();
  await expect(page.locator("#delivery-quantity")).toBeVisible();
}

async function attachEvidence(page: Page, name: string = e2e.evidenceName): Promise<void> {
  await page.getByTestId("file-input").setInputFiles({
    name,
    mimeType: e2e.evidenceMimeType,
    buffer: Buffer.from(EVIDENCE_PNG_BASE64, "base64"),
  });
  await expect(page.getByTestId("photo-thumbs").locator("figure")).toHaveCount(1);
}

test("distributor session survives reload without persisting auth tokens", async ({ page, context }) => {
  await signIn(page, "distributor");
  await expect(page.getByRole("heading", { name: "My workspace" })).toBeVisible();
  const identity = page.locator(".who-identity");
  await expect(identity).toContainText("E2E Distributor");
  await expect(identity).toHaveAttribute("title", `E2E Distributor — ${e2e.distributorEmail}`);

  const cookies = await context.cookies();
  const session = cookies.find((cookie) => cookie.name === "sessionid");
  expect(session, "session cookie must be set by login").toBeTruthy();
  expect(session?.httpOnly).toBe(true);
  expect(session?.secure).toBe(false); // local E2E runs over http; production requires secure.
  expect(cookies.filter((cookie) => /refresh|access|jwt/i.test(cookie.name))).toEqual([]);

  const storageKeys = await page.evaluate(() => Object.keys(window.localStorage));
  expect(storageKeys.filter((key) => /token|jwt|auth/i.test(key))).toEqual([]);

  // The HttpOnly session cookie survives reload and restores the server session.
  await page.reload();
  await expect(page.getByRole("heading", { name: "My workspace" })).toBeVisible();

  // Server-authoritative role guard: direct navigation still refuses admin screens.
  await page.goto("/inventory");
  await expect(page.getByText("You do not have access to this page.")).toBeVisible();
});

test("distributor submits a delivery with photo and location evidence", async ({ page }) => {
  await signIn(page, "distributor");
  await expect(page.getByRole("heading", { name: "My workspace" })).toBeVisible();
  await openFirstAssignment(page);

  await page.locator("#delivery-quantity").fill("25");
  await page.locator("#delivery-notes").fill("E2E delivery: 25 kg with device evidence.");
  await attachEvidence(page);

  await page.getByRole("button", { name: "Capture location" }).click();
  await expect(page.getByText("4.851000, 31.582000", { exact: false })).toBeVisible();

  const submit = page.getByTestId("submit-delivery");
  await expect(submit).toBeEnabled();
  await submit.click();

  await expect(page.getByTestId("toast-stack")).toContainText("Submitted — record accepted by the server.");
  await page.goto("/deliveries");
  await expect(page.getByRole("heading", { name: "My submissions" })).toBeVisible();
  const row = page.getByRole("row").filter({ hasText: "25" });
  await expect(row).toContainText("Submitted");
  await expect(row).toContainText("1 image");
});

test("admin reviews evidence and approves, posting the stock movement", async ({ page }) => {
  await signIn(page, "admin");
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  await page.goto("/evidence");
  await expect(page.getByRole("heading", { name: "Evidence review" })).toBeVisible();

  await page.getByRole("button", { name: "Review", exact: true }).first().click();
  await expect(page.getByTestId("review-detail")).toBeVisible();
  await expect(page.getByTestId("evidence-tile")).toHaveCount(1);

  const image = page.getByTestId("evidence-tile").locator("img");
  await expect(image).toBeVisible();
  await expect
    .poll(() => image.evaluate((element) => (element as HTMLImageElement).naturalWidth))
    .toBeGreaterThan(0);

  await page.getByTestId("approve-button").click();
  await page.locator("#approve-note").fill("E2E approval after evidence/location review.");
  await page.getByRole("button", { name: "Approve and post movement" }).click();

  await expect(page.getByTestId("toast-stack")).toContainText(
    "Approved — the stock movement was posted on the server.",
  );
  await expect(page.getByText("Queue is clear.")).toBeVisible();
});

test("admin map plots the approved delivery location, not a site list", async ({ page }) => {
  await signIn(page, "admin");
  await page.goto("/map");
  await expect(page.getByRole("heading", { name: "Distribution map" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Delivery locations" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Sites in scope" })).toHaveCount(0);

  const delivery = page.locator('[data-testid^="delivery-list-item-"]').first();
  await expect(delivery).toContainText("E2E Distributor");
  await expect(delivery).toContainText("25");
  await expect(delivery).toContainText("Approved");
  await expect(page.locator(".map-pin")).toHaveCount(1);

  await delivery.click();
  const drawer = page.getByTestId("delivery-drawer");
  await expect(drawer).toContainText("4.851000, 31.582000");
  await expect(drawer.getByRole("link", { name: "Open evidence review" })).toHaveAttribute(
    "href",
    /\/evidence\?record_id=/,
  );
});

test("distributor sees the approved record and its ledger movement", async ({ page }) => {
  await signIn(page, "distributor");
  await page.goto("/deliveries");
  const row = page
    .getByRole("row")
    .filter({ has: page.getByRole("cell", { name: "25", exact: true }) });
  await expect(row).toContainText("Approved");

  await row.getByRole("button", { name: "Detail", exact: true }).click();
  const detail = page.getByTestId("submission-detail");
  await expect(detail).toBeVisible();
  await expect(detail).toContainText("Ledger movement");
  await expect(detail).not.toContainText("pending posting");
});

test("offline submission stays QUEUED and syncs honestly when connectivity returns", async ({
  page,
  context,
}) => {
  await signIn(page, "distributor");
  await expect(page.getByRole("heading", { name: "My workspace" })).toBeVisible();
  await openFirstAssignment(page);

  await page.locator("#delivery-quantity").fill("7");
  await attachEvidence(page, "offline-e2e-evidence.png");

  const keyBefore = (await readDrafts(page))[0]?.idempotencyKey ?? null;
  expect(keyBefore).toBeTruthy();

  await context.setOffline(true);
  await page.getByTestId("submit-delivery").click();

  await expect(page.getByTestId("toast-stack")).toContainText("Draft parked in the queue until connectivity returns.");
  await expect(page.getByTestId("draft-state")).toContainText("Queued");

  const queued = (await readDrafts(page))[0];
  expect(queued?.state).toBe("QUEUED");
  expect(queued?.idempotencyKey).toBe(keyBefore);

  await context.setOffline(false);
  // The online event triggers the app's sync manager; no fake "submitted" state.
  await expect(page.getByTestId("draft-state")).toContainText("Submitted", { timeout: 30_000 });

  const synced = (await readDrafts(page))[0];
  expect(synced?.state).toBe("SUBMITTED");
  expect(synced?.idempotencyKey).toBe(keyBefore);
  expect(synced?.submittedRecordId).toBeTruthy();

  await page.goto("/deliveries");
  await expect(page.getByRole("cell", { name: "7", exact: true })).toBeVisible();
  const offlineRow = page
    .getByRole("row")
    .filter({ has: page.getByRole("cell", { name: "7", exact: true }) });
  await expect(offlineRow).toContainText("Submitted");
});

test("distributor workspace is usable at a 360 px mobile viewport", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 800 });
  await signIn(page, "distributor");
  await expect(page.getByRole("heading", { name: "My workspace" })).toBeVisible();
  await openFirstAssignment(page);

  await expect(page.locator("#delivery-quantity")).toBeVisible();
  await expect(page.getByTestId("submit-delivery")).toBeVisible();
  const horizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(horizontalOverflow).toBeLessThanOrEqual(1);
});
