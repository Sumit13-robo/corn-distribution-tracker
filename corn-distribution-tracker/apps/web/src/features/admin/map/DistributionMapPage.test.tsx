/**
 * Admin map contract: only distributor-recorded delivery points are plotted;
 * site reference coordinates and sites without deliveries are not shown.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { CampaignOut, MapDeliveryOut } from "../../../types/domain";

vi.mock("../../../lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../../lib/api-client")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      listCampaigns: vi.fn(),
      mapDeliveries: vi.fn(),
    },
  };
});

vi.mock("../../../components/common/MapCanvas", () => ({
  MapCanvas: ({
    points,
    ariaLabel,
  }: {
    points: Array<{ id: string; label: string }>;
    ariaLabel: string;
  }) => (
    <div data-testid="map-canvas" aria-label={ariaLabel}>
      {points.map((point) => (
        <span key={point.id}>{point.label}</span>
      ))}
    </div>
  ),
}));

import { api } from "../../../lib/api-client";
import { DistributionMapPage } from "./DistributionMapPage";

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

const delivery: MapDeliveryOut = {
  id: "delivery-1",
  site_id: "site-1",
  site_code: "KOLHAPUR",
  site_name: "Kolhapur",
  campaign_id: campaign.id,
  distributor_user_id: "user-1",
  distributor_name: "Amina Peter",
  quantity_kg: "1.000",
  status: "APPROVED",
  submitted_at: "2026-10-25T17:05:22Z",
  location_latitude: "16.673600",
  location_longitude: "74.206139",
  location_accuracy_m: "16.20",
  location_timestamp: "2026-10-25T17:04:49Z",
};

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <MemoryRouter>
      <QueryClientProvider client={client}>
        <DistributionMapPage />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.listCampaigns).mockResolvedValue({
    items: [campaign],
    total: 1,
    limit: 100,
    offset: 0,
  });
  vi.mocked(api.mapDeliveries).mockResolvedValue([delivery]);
});

afterEach(cleanup);

describe("DistributionMapPage delivery markers", () => {
  it("shows only delivery locations and opens the selected delivery", async () => {
    renderPage();

    expect(await screen.findByTestId("delivery-list-item-delivery-1")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Delivery locations" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Sites in scope" })).not.toBeInTheDocument();
    expect(screen.getByTestId("map-canvas")).toHaveTextContent("Amina Peter delivered 1 kg to Kolhapur");

    fireEvent.click(screen.getByTestId("delivery-list-item-delivery-1"));
    expect(await screen.findByTestId("delivery-drawer")).toHaveTextContent("Amina Peter");
    expect(screen.getByRole("link", { name: "Open evidence review" })).toHaveAttribute(
      "href",
      "/evidence?record_id=delivery-1",
    );
  });

  it("explains when no delivery has a captured location", async () => {
    vi.mocked(api.mapDeliveries).mockResolvedValue([]);
    renderPage();

    expect(await screen.findByText("No recorded delivery locations yet.")).toBeInTheDocument();
    expect(screen.queryByTestId("map-canvas")).not.toBeInTheDocument();
  });
});
