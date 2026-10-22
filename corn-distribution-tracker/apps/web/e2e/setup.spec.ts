import { expect, test as setup } from "@playwright/test";
import type { APIResponse } from "@playwright/test";

import { e2e } from "./support/config";
import { credentials } from "./support/credentials";

interface CreatedInvitation {
  invite_token: string;
}

interface CreatedUser {
  id: string;
}

interface NamedRow {
  id: string;
}

async function body<T>(response: APIResponse, label: string): Promise<T> {
  if (!response.ok()) {
    throw new Error(`${label} failed: ${response.status()} ${await response.text()}`);
  }
  return (await response.json()) as T;
}

/**
 * Seed the E2E world through the public HTTP API (not direct database writes):
 * one active campaign/site, one accepted distributor invitation, one target,
 * and enough central stock to allocate 500 kg to that distributor.
 */
setup("seed campaign, site, distributor, assignment and stock", async ({ request }) => {
  const creds = credentials();
  const api = (route: string) => `/api/v1${route}`;

  const loginResponse = await request.post(api("/auth/login"), {
    data: { email: creds.adminEmail, password: creds.adminPassword },
  });
  const login = await body<{ access_token: string; user: CreatedUser }>(loginResponse, "admin login");
  const auth = { Authorization: `Bearer ${login.access_token}` };

  const campaign = await body<NamedRow>(
    await request.post(api("/campaigns"), {
      headers: auth,
      data: {
        name: "E2E Juba campaign",
        reference_code: e2e.campaignCode,
        status: "ACTIVE",
        timezone: "Africa/Juba",
      },
    }),
    "create campaign",
  );

  const site = await body<NamedRow>(
    await request.post(api("/sites"), {
      headers: auth,
      data: {
        name: "E2E Juba collection point",
        site_code: e2e.siteCode,
        address_text: "Juba, South Sudan (synthetic E2E location)",
        region: "Central Equatoria",
        latitude: e2e.siteLatitude,
        longitude: e2e.siteLongitude,
        geofence_radius_m: 500,
        max_acceptable_accuracy_m: 100,
        notes: "Synthetic site created by the browser E2E setup project.",
      },
    }),
    "create site",
  );

  const invitation = await body<CreatedInvitation>(
    await request.post(api("/admin/users/invitations"), {
      headers: auth,
      data: {
        email: creds.distributorEmail,
        display_name: "E2E Distributor",
        role: "DISTRIBUTOR",
      },
    }),
    "create distributor invitation",
  );

  const distributor = await body<CreatedUser>(
    await request.post(api("/auth/accept-invitation"), {
      data: {
        token: invitation.invite_token,
        password: creds.distributorPassword,
        display_name: "E2E Distributor",
      },
    }),
    "accept distributor invitation",
  );

  const assignment = await body<NamedRow>(
    await request.post(api("/assignments"), {
      headers: auth,
      data: {
        site_id: site.id,
        campaign_id: campaign.id,
        distributor_user_id: distributor.id,
        target_quantity: "500",
        unit: "KG",
        notes: "E2E target",
      },
    }),
    "create assignment",
  );

  await body<NamedRow>(
    await request.post(api("/inventory/receipts"), {
      headers: { ...auth, "Idempotency-Key": "e2e-receipt-2000" },
      data: {
        quantity: "2000",
        unit: "KG",
        source_reference: "E2E synthetic receipt",
        notes: "Synthetic stock for browser E2E.",
      },
    }),
    "receive stock",
  );

  await body<NamedRow>(
    await request.post(api("/inventory/allocations"), {
      headers: { ...auth, "Idempotency-Key": "e2e-allocation-500" },
      data: {
        distributor_user_id: distributor.id,
        quantity: "500",
        unit: "KG",
        campaign_id: campaign.id,
        notes: "Synthetic allocation for browser E2E.",
      },
    }),
    "allocate stock",
  );

  expect(campaign.id).toBeTruthy();
  expect(site.id).toBeTruthy();
  expect(assignment.id).toBeTruthy();
  expect(distributor.id).toBeTruthy();
  expect(login.user.id).toBeTruthy();
});

/**
 * A second setup step makes the failure obvious if the generated credentials do
 * not work through the UI-facing login endpoint.
 */
setup("verify seeded distributor credentials", async ({ request }) => {
  const creds = credentials();
  const response = await request.post("/api/v1/auth/login", {
    data: { email: creds.distributorEmail, password: creds.distributorPassword },
  });
  await expect(response).toBeOK();
  const payload = (await response.json()) as { user: { role: string } };
  expect(payload.user.role).toBe("DISTRIBUTOR");
});
