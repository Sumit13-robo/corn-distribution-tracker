/**
 * Campaign setup contract: site names are added with the campaign (or from
 * the selected campaign panel), and a site location remains optional until an
 * admin explicitly supplies coordinates later.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { CampaignOut, Page, SiteOut } from "../../../types/domain";

vi.mock("../../../lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../../lib/api-client")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      listCampaigns: vi.fn(),
      listSites: vi.fn(),
      listDistributors: vi.fn(),
      inventorySummary: vi.fn(),
      listAllAssignments: vi.fn(),
      createCampaign: vi.fn(),
      createSite: vi.fn(),
      updateSite: vi.fn(),
    },
  };
});

import { api } from "../../../lib/api-client";
import { ToastProvider } from "../../../app/providers";
import { CampaignsPage } from "./CampaignsPage";

const campaign: CampaignOut = {
  id: "campaign-1",
  name: "Kolhapur",
  reference_code: "KOLHAPUR-1",
  starts_at: null,
  ends_at: null,
  status: "ACTIVE",
  timezone: "Asia/Kolkata",
  notes: null,
  created_at: "2026-01-01T00:00:00Z",
};

const site: SiteOut = {
  id: "site-1",
  name: "Gandhi Chowk",
  site_code: "GANDHI-CHOWK",
  campaign_id: campaign.id,
  address_text: null,
  region: null,
  latitude: null,
  longitude: null,
  geofence_radius_m: 200,
  max_acceptable_accuracy_m: null,
  is_active: true,
  notes: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: null,
};

function page<T>(items: T[]): Page<T> {
  return { items, total: items.length, limit: 100, offset: 0 };
}

function renderPage() {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <CampaignsPage />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

async function selectCampaign() {
  const buttons = await screen.findAllByRole("button", { name: "Kolhapur" });
  const button = buttons[0];
  if (!button) throw new Error("Campaign button not found");
  fireEvent.click(button);
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.listCampaigns).mockResolvedValue(page([campaign]));
  vi.mocked(api.listSites).mockResolvedValue(page([]));
  vi.mocked(api.listDistributors).mockResolvedValue(page([]));
  vi.mocked(api.inventorySummary).mockResolvedValue({ accounts: [], reconciliation: null });
  vi.mocked(api.listAllAssignments).mockResolvedValue(page([]));
  vi.mocked(api.createCampaign).mockResolvedValue(campaign);
  vi.mocked(api.createSite).mockResolvedValue(site);
  vi.mocked(api.updateSite).mockResolvedValue({
    ...site,
    latitude: "16.700000",
    longitude: "74.243300",
  });
});

afterEach(cleanup);

describe("CampaignsPage site setup", () => {
  it("creates name-only sites from the campaign dialog", async () => {
    renderPage();
    await screen.findAllByRole("button", { name: "Kolhapur" });

    fireEvent.click(screen.getByRole("button", { name: "New campaign" }));
    fireEvent.change(screen.getByLabelText(/^Name/), { target: { value: "New campaign" } });
    fireEvent.change(screen.getByLabelText(/^Reference code/), { target: { value: "NEW-1" } });
    fireEvent.change(screen.getByLabelText(/^Sites/), {
      target: { value: "Gandhi Chowk\nRukadi Market\ngandhi chowk" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save campaign" }));

    await waitFor(() =>
      expect(api.createCampaign).toHaveBeenCalledWith(
        expect.objectContaining({
          sites: ["Gandhi Chowk", "Rukadi Market"],
        }),
      ),
    );
  });

  it("adds a site inside the selected campaign with only its name", async () => {
    renderPage();
    await selectCampaign();
    await screen.findByTestId("campaign-sites");

    fireEvent.change(screen.getByLabelText(/^Add a site/), {
      target: { value: "Gandhi Chowk" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add site" }));

    await waitFor(() =>
      expect(api.createSite).toHaveBeenCalledWith({
        name: "Gandhi Chowk",
        campaign_id: campaign.id,
      }),
    );
  });

  it("adds an optional site location later", async () => {
    vi.mocked(api.listSites).mockResolvedValue(page([site]));
    renderPage();
    await selectCampaign();
    fireEvent.click(await screen.findByRole("button", { name: "Add location (optional)" }));

    fireEvent.change(screen.getByLabelText(/^Latitude/), { target: { value: "16.7" } });
    fireEvent.change(screen.getByLabelText(/^Longitude/), { target: { value: "74.2433" } });
    fireEvent.click(screen.getByRole("button", { name: "Save location" }));

    await waitFor(() =>
      expect(api.updateSite).toHaveBeenCalledWith(site.id, {
        latitude: "16.7",
        longitude: "74.2433",
      }),
    );
  });
});
