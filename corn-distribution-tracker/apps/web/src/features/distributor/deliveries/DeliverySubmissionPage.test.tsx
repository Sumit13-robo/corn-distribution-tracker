/**
 * Planned-file test: delivery submission draft handling (SCREEN_SPECS
 * "Delivery update", OFFLINE_SYNC draft-state machine).
 *
 * Covers the contract-critical behaviours:
 *  - the draft (and its idempotency key) persists across a remount instead of
 *    spawning a duplicate draft,
 *  - offline submission stays honestly QUEUED, never a fake SUBMITTED,
 *  - a successful sync calls the server once even under a double click,
 *  - the payload is built from the draft fields and local evidence intents.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { DistributionOut, DistributorAssignmentItemOut, SettingsOut } from "../../../types/domain";
import { pruneSubmittedDrafts, type LocalDraft } from "../offline/offlineQueue";

const TEST_USER_ID = "user-test-1";
const DRAFTS_KEY = `corn-tracker:drafts:v1:${TEST_USER_ID}`;

vi.mock("../../../lib/session", () => {
  const user = {
    id: "user-test-1",
    email: "distributor@example.test",
    display_name: "Test Distributor",
    role: "DISTRIBUTOR",
    is_active: true,
  };
  return {
    getCurrentUserId: () => "user-test-1",
    useSession: () => ({ status: "SIGNED_IN", user }),
    sessionSnapshot: () => ({ status: "SIGNED_IN", user }),
    subscribeToSession: () => () => undefined,
  };
});

vi.mock("../../../lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../../lib/api-client")>();
  return {
    ...actual,
    uploadBlob: vi.fn(async () => undefined),
    api: {
      ...actual.api,
      myAssignments: vi.fn(),
      getSettings: vi.fn(),
      createUploadIntent: vi.fn(),
      completeUploadIntent: vi.fn(async () => ({
        intent_id: "intent-1",
        completed: true,
        newly_verified: true,
        size_bytes: 3,
        sha256_hex: "a".repeat(64),
        content_type: "image/jpeg",
      })),
      submitDelivery: vi.fn(),
    },
  };
});

import { api } from "../../../lib/api-client";
import { ToastProvider } from "../../../app/providers";
import { DeliverySubmissionPage } from "./DeliverySubmissionPage";

const assignment: DistributorAssignmentItemOut = {
  assignment_id: "asg-1",
  campaign_id: null,
  due_at: null,
  status: "ACTIVE",
  target_kg: "1000",
  approved_kg: "100",
  pending_kg: "0",
  remaining_target_kg: "900",
  over_target_kg: "0",
  site: {
    id: "site-1",
    name: "Central School",
    site_code: "SITE-001",
    campaign_id: null,
    address_text: "1 Example Road",
    region: "North",
    latitude: "12.3456789",
    longitude: "-1.2345678",
    geofence_radius_m: 250,
    max_acceptable_accuracy_m: null,
    is_active: true,
    notes: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: null,
  },
};

const settings: SettingsOut = {
  timezone: "UTC",
  default_display_unit: "KG",
  kg_per_bag: null,
  default_geofence_radius_m: 250,
  max_acceptable_gps_accuracy_m: 50,
  max_location_age_seconds: 300,
  max_capture_time_drift_seconds: 900,
  updated_at: null,
};

const serverRecord: DistributionOut = {
  id: "record-1",
  campaign_id: null,
  assignment_id: "asg-1",
  site_id: "site-1",
  site_code: "TEST-01",
  site_name: "Test Site",
  distributor_user_id: TEST_USER_ID,
  distributor_name: "Test Distributor",
  quantity_kg: "250.000",
  status: "SUBMITTED",
  client_created_at: "2026-01-01T01:00:00Z",
  submitted_at: "2026-01-01T01:00:05Z",
  reviewed_at: null,
  reviewed_by: null,
  review_reason: null,
  review_exception_reason: null,
  reversed_at: null,
  reversed_by: null,
  reversal_reason: null,
  stock_movement_id: null,
  notes: null,
  location_latitude: null,
  location_longitude: null,
  location_accuracy_m: null,
  location_timestamp: null,
  device_reported_location_time: null,
  distance_to_site_m: null,
  geo_status: "UNAVAILABLE",
  geo_flags: [],
  evidence: [],
  created_at: "2026-01-01T01:00:05Z",
  updated_at: null,
};

function deferred<T>() {
  let resolve!: (value: T | PromiseLike<T>) => void;
  const promise = new Promise<T>((res) => {
    resolve = res;
  });
  return { promise, resolve };
}

function readDrafts(): LocalDraft[] {
  const raw = window.localStorage.getItem(DRAFTS_KEY);
  return raw ? (JSON.parse(raw) as LocalDraft[]) : [];
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
        <MemoryRouter initialEntries={["/deliver/new?assignment=asg-1"]}>
          <DeliverySubmissionPage />
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  );
}

async function waitForDraft() {
  await waitFor(() => expect(screen.getByTestId("draft-state")).toBeInTheDocument());
}

async function attachPhoto() {
  const input = screen.getByTestId("file-input") as HTMLInputElement;
  const file = new File([new Uint8Array([1, 2, 3])], "evidence.jpg", { type: "image/jpeg" });
  Object.defineProperty(input, "files", { configurable: true, value: [file] });
  fireEvent.change(input);
  await screen.findByTestId(/^photo-thumb-/);
}

function setQuantity(value: string) {
  fireEvent.change(screen.getByLabelText(/Quantity/), { target: { value } });
}

/** Only the test sets a synthetic connectivity flag; the real getter returns. */
function setOnline(value: boolean): () => void {
  Object.defineProperty(window.navigator, "onLine", { configurable: true, value });
  return () => {
    delete (window.navigator as unknown as Record<string, unknown>).onLine;
  };
}

describe("DeliverySubmissionPage", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.mocked(api.myAssignments).mockResolvedValue([assignment]);
    vi.mocked(api.getSettings).mockResolvedValue(settings);
    vi.mocked(api.createUploadIntent).mockResolvedValue({
      intent_id: "intent-1",
      expires_at: "2026-01-01T02:00:00Z",
      upload_method: "PUT",
      upload_url: "/api/v1/uploads/intent-1",
      headers: {},
    });
    vi.mocked(api.submitDelivery).mockReset();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("persists the draft and its idempotency key across a remount", async () => {
    const first = renderPage();
    await waitForDraft();
    expect(screen.getByTestId("draft-state")).toHaveTextContent("Local draft");

    setQuantity("175");
    await waitFor(() => expect(readDrafts()[0]?.quantity).toBe("175"));
    const originalKey = readDrafts()[0]?.idempotencyKey;
    expect(originalKey).toBeTruthy();

    first.unmount();
    renderPage();
    await waitForDraft();

    expect(screen.getByLabelText(/Quantity/)).toHaveValue("175");
    const drafts = readDrafts();
    expect(drafts).toHaveLength(1);
    expect(drafts[0]?.idempotencyKey).toBe(originalKey);
  });

  it("persists a captured device fix into the draft before submission", async () => {
    const getCurrentPosition = vi.fn((success: PositionCallback) =>
      success({
        coords: {
          latitude: 12.3456789,
          longitude: -1.2345678,
          accuracy: 8,
          altitude: null,
          altitudeAccuracy: null,
          heading: null,
          speed: null,
        },
        timestamp: Date.now(),
      } as GeolocationPosition),
    );
    Object.defineProperty(window.navigator, "geolocation", {
      configurable: true,
      value: { getCurrentPosition },
    });
    try {
      renderPage();
      await waitForDraft();
      fireEvent.click(screen.getByRole("button", { name: "Capture location" }));
      await waitFor(() => expect(readDrafts()[0]?.location?.accuracy_m).toBe("8.0"));
      expect(screen.getByText("12.345679, -1.234568", { exact: false })).toBeInTheDocument();
    } finally {
      delete (window.navigator as unknown as Record<string, unknown>).geolocation;
    }
  });

  it("resumes a saved draft fix without warning that location is missing and submits it", async () => {
    const getCurrentPosition = vi.fn((success: PositionCallback) =>
      success({
        coords: {
          latitude: 12.3456789,
          longitude: -1.2345678,
          accuracy: 8,
          altitude: null,
          altitudeAccuracy: null,
          heading: null,
          speed: null,
        },
        timestamp: Date.now(),
      } as GeolocationPosition),
    );
    Object.defineProperty(window.navigator, "geolocation", {
      configurable: true,
      value: { getCurrentPosition },
    });
    try {
      const first = renderPage();
      await waitForDraft();
      fireEvent.click(screen.getByRole("button", { name: "Capture location" }));
      await waitFor(() => expect(readDrafts()[0]?.location?.accuracy_m).toBe("8.0"));
      first.unmount();

      vi.mocked(api.submitDelivery).mockResolvedValue(serverRecord);
      renderPage();
      await waitForDraft();
      expect(await screen.findByText("12.345679, -1.234568", { exact: false })).toBeInTheDocument();
      expect(screen.queryByText(/Location not captured/i)).toBeNull();

      setQuantity("100");
      await attachPhoto();
      fireEvent.click(screen.getByTestId("submit-delivery"));
      await screen.findByText("Submitted — record accepted by the server.");

      const [payload] = vi.mocked(api.submitDelivery).mock.calls[0] ?? [];
      expect(payload?.location).toMatchObject({
        latitude: "12.345679",
        longitude: "-1.234568",
        accuracy_m: "8.0",
      });
    } finally {
      delete (window.navigator as unknown as Record<string, unknown>).geolocation;
    }
  });

  it("explains that location capture needs HTTPS on an insecure origin", async () => {
    const secureContext = Object.getOwnPropertyDescriptor(window, "isSecureContext");
    Object.defineProperty(window, "isSecureContext", { configurable: true, value: false });
    try {
      renderPage();
      await waitForDraft();
      fireEvent.click(screen.getByRole("button", { name: "Capture location" }));
      expect(await screen.findByText(/Location needs HTTPS/i)).toBeInTheDocument();
    } finally {
      if (secureContext) {
        Object.defineProperty(window, "isSecureContext", secureContext);
      } else {
        delete (window as unknown as Record<string, unknown>).isSecureContext;
      }
    }
  });

  it("keeps an offline submission QUEUED and never claims it was submitted", async () => {
    const restoreOnline = setOnline(false);
    try {
      renderPage();
      await waitForDraft();
      setQuantity("90");
      await attachPhoto();

      fireEvent.click(screen.getByTestId("submit-delivery"));
      await screen.findByText("Draft parked in the queue until connectivity returns.");

      expect(screen.getByTestId("draft-state")).toHaveTextContent("Queued to sync");
      expect(api.submitDelivery).not.toHaveBeenCalled();
      expect(api.createUploadIntent).not.toHaveBeenCalled();
      expect(readDrafts()[0]).toMatchObject({ state: "QUEUED", submittedRecordId: null });
      expect(screen.queryByText("Submitted", { exact: true })).toBeNull();
    } finally {
      restoreOnline();
    }
  });

  it("submits once under a double click and records the server id", async () => {
    const pending = deferred<DistributionOut>();
    vi.mocked(api.submitDelivery).mockReturnValue(pending.promise);

    renderPage();
    await waitForDraft();
    setQuantity("250");
    await attachPhoto();

    const submitButton = screen.getByTestId("submit-delivery");
    expect(submitButton).toBeEnabled();
    fireEvent.click(submitButton);
    await waitFor(() => expect(api.submitDelivery).toHaveBeenCalledTimes(1));

    // The in-flight guard blocks a duplicate submission.
    expect(submitButton).toBeDisabled();
    fireEvent.click(submitButton);
    expect(api.submitDelivery).toHaveBeenCalledTimes(1);

    await act(async () => {
      pending.resolve(serverRecord);
    });
    await screen.findByText("Submitted — record accepted by the server.");

    const [payload, idempotencyKey] = vi.mocked(api.submitDelivery).mock.calls[0] ?? [];
    expect(payload).toMatchObject({
      assignment_id: "asg-1",
      quantity: "250",
      unit: "KG",
      evidence: [{ intent_id: "intent-1", capture_source: "FILE_PICKER" }],
    });

    const drafts = readDrafts();
    expect(drafts).toHaveLength(1);
    expect(drafts[0]).toMatchObject({
      state: "SUBMITTED",
      submittedRecordId: "record-1",
      location: null,
      notes: null,
      photoIds: [],
      siteCode: null,
      siteName: null,
      idempotencyKey: "",
    });
    expect(idempotencyKey).toBeTruthy();

    // Local receipts are convenience copies and can be pruned once retained.
    pruneSubmittedDrafts(TEST_USER_ID, 0);
    expect(readDrafts()).toHaveLength(0);
  });
});
