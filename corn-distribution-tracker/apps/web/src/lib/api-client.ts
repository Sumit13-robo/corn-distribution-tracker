/**
 * Typed HTTP client for the API (docs/architecture/API_CONTRACT.md).
 *
 * Every screen uses this module instead of hand-rolled fetch logic. It:
 *  - prefixes all paths with the public API base URL,
 *  - attaches the in-memory bearer token (never persisted to storage),
 *  - converts non-2xx responses into ApiError with the stable error envelope,
 *  - performs a single-flight POST /auth/refresh (cookie-based, HttpOnly)
 *    on 401 and retries the original request exactly once,
 *  - keeps the refresh cookie flow on same-origin relative requests through the
 *    dev proxy, or explicit credentials for cross-origin deployments.
 */

import type {
  AckOut,
  AdjustmentIn,
  AllocationIn,
  AssignmentIn,
  AssignmentOut,
  AssignmentPatchIn,
  AuditEventFilters,
  AuditEventOut,
  CampaignIn,
  CampaignOut,
  CampaignPatchIn,
  DeliveryApproveIn,
  DeliveryCreateIn,
  DeliveryListFilters,
  DistributionOut,
  DistributorAssignmentItemOut,
  DistributorDetailOut,
  DistributorListOut,
  InventorySummaryOut,
  InvitationCreatedOut,
  LoginOut,
  MapSiteOut,
  OverviewOut,
  Page,
  ReceiptIn,
  ReversalIn,
  SettingsOut,
  SettingsPatchIn,
  SiteIn,
  SiteOut,
  SitePatchIn,
  SitePerfOut,
  SiteProgressOut,
  StockMovementOut,
  UploadIntentOut,
  UserOut,
  ViewURLOut,
  DistributorPerfOut,
} from "../types/domain";

const BASE_URL: string = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "/api/v1";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId: string | null;
  readonly details: ReadonlyArray<Record<string, unknown>>;

  constructor(
    status: number,
    code: string,
    message: string,
    requestId: string | null,
    details: ReadonlyArray<Record<string, unknown>> = [],
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.requestId = requestId;
    this.details = details;
  }
}

interface AuthHooks {
  getToken: () => string | null;
  onAuthLost: () => void;
}

const auth: AuthHooks = {
  getToken: () => null,
  onAuthLost: () => undefined,
};

/** Collision-resistant unique id (crypto.randomUUID, then CSPRNG bytes). */
export function newId(): string {
  const cryptoRef = globalThis.crypto;
  if (cryptoRef && typeof cryptoRef.randomUUID === "function") return cryptoRef.randomUUID();
  if (cryptoRef && typeof cryptoRef.getRandomValues === "function") {
    const bytes = new Uint8Array(16);
    cryptoRef.getRandomValues(bytes);
    return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
  }
  return `id-${Date.now().toString(16)}-${Math.random().toString(16).slice(2, 10)}`;
}

/** Session hooks are registered once by lib/session.ts (avoids import cycle). */
export function configureAuth(hooks: Partial<AuthHooks>): void {
  if (hooks.getToken) auth.getToken = hooks.getToken;
  if (hooks.onAuthLost) auth.onAuthLost = hooks.onAuthLost;
}

let refreshInFlight: Promise<boolean> | null = null;

let onRefreshedToken: (token: string) => void = () => undefined;

/** session.ts installs the sink so rotated tokens reach the in-memory store. */
export function registerRefreshTokenSink(sink: (token: string) => void): void {
  onRefreshedToken = sink;
}

async function runRefresh(): Promise<boolean> {
  // Token rotation is cookie-based; POST /auth/refresh needs no bearer token.
  const response = await fetch(`${BASE_URL}/auth/refresh`, {
    method: "POST",
    credentials: "include",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) return false;
  const body = (await response.json()) as { access_token?: string };
  if (!body.access_token) return false;
  onRefreshedToken(body.access_token);
  return true;
}

async function refreshOnce(): Promise<boolean> {
  if (refreshInFlight === null) {
    // Single-flight: parallel 401s share one rotation, preventing token reuse.
    refreshInFlight = runRefresh().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

/** Auth endpoints are handled without the normal 401 retry ladder (no loops). */
function isAuthFlowPath(path: string): boolean {
  return (
    path === "/auth/login" ||
    path === "/auth/refresh" ||
    path === "/auth/logout" ||
    path === "/auth/forgot-password"
  );
}

async function parseErrorEnvelope(response: Response): Promise<ApiError> {
  try {
    const body = (await response.json()) as { error?: Record<string, unknown> };
    if (body && body.error) {
      const envelope = body.error as {
        code?: string;
        message?: string;
        request_id?: string;
        details?: Array<Record<string, unknown>>;
      };
      return new ApiError(
        response.status,
        envelope.code ?? "ERROR",
        envelope.message ?? "Request failed.",
        envelope.request_id ?? null,
        envelope.details ?? [],
      );
    }
  } catch {
    // fall through to the generic error below
  }
  return new ApiError(response.status, "ERROR", response.statusText || "Request failed.", null);
}

export interface RequestOptions {
  query?: Record<string, string | number | boolean | null | undefined>;
  body?: unknown;
  idempotencyKey?: string;
  signal?: AbortSignal;
}

function buildUrl(path: string, query?: RequestOptions["query"]): string {
  // `new URL` against the page origin keeps BASE_URL relative (dev proxy) or absolute.
  const url = new URL(`${BASE_URL}${path}`, window.location.origin);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== null && value !== undefined && value !== "") {
        url.searchParams.set(key, String(value));
      }
    }
  }
  return url.toString();
}

export async function request<T>(
  method: "GET" | "POST" | "PATCH" | "PUT" | "DELETE",
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const token = auth.getToken();
  const headers: Record<string, string> = { Accept: "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  if (options.idempotencyKey) headers["Idempotency-Key"] = options.idempotencyKey;

  let response = await fetch(buildUrl(path, options.query), {
    method,
    headers,
    credentials: "include",
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    signal: options.signal,
  });

  if (response.status === 401 && !isAuthFlowPath(path) && auth.getToken() !== null && !options.signal?.aborted) {
    const refreshed = await refreshOnce();
    if (refreshed) {
      const retryHeaders: Record<string, string> = { ...headers };
      const fresh = auth.getToken();
      if (fresh) retryHeaders.Authorization = `Bearer ${fresh}`;
      response = await fetch(buildUrl(path, options.query), {
        method,
        headers: retryHeaders,
        credentials: "include",
        body: options.body === undefined ? null : JSON.stringify(options.body),
        signal: options.signal,
      });
    } else {
      // Rotation failed: the refresh session is gone; drop the session state.
      auth.onAuthLost();
    }
  }

  if (response.status === 204) return undefined as T;
  if (!response.ok) {
    throw await parseErrorEnvelope(response);
  }
  return (await response.json()) as T;
}

/* ------------------------------------------------------------------ Uploads */

/**
 * Uploads media against short-lived upload instructions. The target is either
 * a same-origin API endpoint (authorized with our bearer token) or a presigned
 * object-storage URL (authorization is baked into the URL: only the
 * intent-provided headers may be sent, or the signature would break).
 */
export async function uploadBlob(
  intent: { upload_url: string; headers?: Record<string, string> },
  blob: Blob,
): Promise<void> {
  const isApiEndpoint = intent.upload_url.startsWith("/api/");
  const url = isApiEndpoint ? new URL(intent.upload_url, window.location.origin).toString() : intent.upload_url;
  const headers: Record<string, string> = { ...(intent.headers ?? {}) };
  if (isApiEndpoint) {
    const current = auth.getToken();
    if (current) headers.Authorization = `Bearer ${current}`;
  }
  const response = await fetch(url, { method: "PUT", headers, body: blob });
  if (!response.ok) {
    throw await parseErrorEnvelope(response);
  }
}

/* -------------------------------------------------------------------- CSV */

/** Fetches the authorized CSV export as a blob (the server audits the action). */
export async function fetchDistributionsCsv(
  query: DeliveryListFilters,
  signal?: AbortSignal,
): Promise<Blob> {
  const headers: Record<string, string> = { Accept: "text/csv" };
  const token = auth.getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(buildUrl("/exports/distributions.csv", query as RequestOptions["query"]), {
    method: "GET",
    headers,
    credentials: "include",
    signal,
  });
  if (!response.ok) throw await parseErrorEnvelope(response);
  return response.blob();
}

/** Triggers a browser download for a blob already fetched. */
export function downloadBlob(blob: Blob, filename: string): void {
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 5_000);
}

/* -------------------------------------- Endpoint functions used by screens */

export const api = {
  /* auth */
  login: (email: string, password: string) => post<LoginOut>("/auth/login", { email, password }),
  logout: () => post<AckOut>("/auth/logout"),
  me: () => get<UserOut>("/auth/me"),
  forgotPassword: (email: string) => post<AckOut>("/auth/forgot-password", { email }),
  resetPassword: (token: string, password: string) =>
    post<AckOut>("/auth/reset-password", { token, password }),
  acceptInvitation: (token: string, password: string, displayName?: string) =>
    post<UserOut>("/auth/accept-invitation", { token, password, display_name: displayName }),
  changePassword: (currentPassword: string, newPassword: string) =>
    post<AckOut>("/auth/change-password", {
      current_password: currentPassword,
      new_password: newPassword,
    }),

  /* campaigns */
  listCampaigns: (status?: string, limit = 50) => get<Page<CampaignOut>>("/campaigns", { status, limit }),
  createCampaign: (payload: CampaignIn) => post<CampaignOut>("/campaigns", payload),
  updateCampaign: (id: string, payload: CampaignPatchIn) =>
    request<CampaignOut>("PATCH", `/campaigns/${id}`, { body: payload }),

  /* distributors */
  listDistributors: (search?: string, limit = 50) =>
    get<DistributorListOut>("/admin/distributors", { search, limit }),
  updateDistributor: (id: string, displayName: string) =>
    request<DistributorDetailOut>("PATCH", `/admin/distributors/${id}`, { body: { display_name: displayName } }),
  deactivateDistributor: (id: string) => post<DistributorDetailOut>(`/admin/distributors/${id}/deactivate`),
  createInvitation: (payload: { email: string; display_name: string; role?: "ADMIN" | "DISTRIBUTOR" }) =>
    post<InvitationCreatedOut>("/admin/users/invitations", payload),
  listInvitations: () =>
    get<
      Array<{
        id: string;
        email: string;
        display_name: string;
        role: string;
        expires_at: string;
        accepted_at: string | null;
        revoked_at: string | null;
        created_at: string;
      }>
    >("/admin/users/invitations"),

  /* sites */
  listSites: (
    filters: { search?: string; campaign_id?: string; active_only?: boolean; limit?: number } = {},
  ) => get<Page<SiteOut>>("/sites", filters as RequestOptions["query"]),
  getSite: (id: string) => get<SiteOut>(`/sites/${id}`),
  createSite: (payload: SiteIn) => post<SiteOut>("/sites", payload),
  updateSite: (id: string, payload: SitePatchIn) =>
    request<SiteOut>("PATCH", `/sites/${id}`, { body: payload }),
  deactivateSite: (id: string) => post<SiteOut>(`/sites/${id}/deactivate`),
  siteProgress: (id: string, campaignId?: string) =>
    get<SiteProgressOut>(`/sites/${id}/progress`, campaignId ? { campaign_id: campaignId } : undefined),

  /* assignments */
  listAllAssignments: (campaignId?: string, limit = 100) =>
    get<Page<AssignmentOut>>("/assignments", { campaign_id: campaignId, limit }),
  getAssignment: (id: string) => get<AssignmentOut>(`/assignments/${id}`),
  createAssignment: (payload: AssignmentIn) => post<AssignmentOut>("/assignments", payload),
  updateAssignment: (id: string, payload: AssignmentPatchIn) =>
    request<AssignmentOut>("PATCH", `/assignments/${id}`, { body: payload }),
  myAssignments: () => get<DistributorAssignmentItemOut[]>("/distributors/me/assignments"),

  /* inventory */
  inventorySummary: () => get<InventorySummaryOut>("/inventory/summary"),
  accountLedger: (accountId: string, limit = 50, offset = 0) =>
    get<Page<StockMovementOut>>(`/inventory/accounts/${accountId}/ledger`, { limit, offset }),
  postReceipt: (payload: ReceiptIn, idempotencyKey: string) =>
    post<StockMovementOut>("/inventory/receipts", payload, { idempotencyKey }),
  postAllocation: (payload: AllocationIn, idempotencyKey: string) =>
    post<StockMovementOut>("/inventory/allocations", payload, { idempotencyKey }),
  postAdjustment: (payload: AdjustmentIn, idempotencyKey: string) =>
    post<StockMovementOut>("/inventory/adjustments", payload, { idempotencyKey }),
  reverseMovement: (movementId: string, payload: ReversalIn, idempotencyKey: string) =>
    post<StockMovementOut>(`/inventory/movements/${movementId}/reversal`, payload, { idempotencyKey }),

  /* evidence */
  createUploadIntent: (contentType: string, purpose?: string) =>
    post<UploadIntentOut>("/evidence/upload-intents", {
      content_type: contentType,
      purpose: purpose ?? "DISTRIBUTION_EVIDENCE",
    }),
  evidenceViewUrl: (evidenceId: string) => get<ViewURLOut>(`/evidence/${evidenceId}/view-url`),

  /* deliveries */
  submitDelivery: (payload: DeliveryCreateIn, idempotencyKey: string) =>
    post<DistributionOut>("/deliveries", payload, { idempotencyKey }),
  listDeliveries: (filters: DeliveryListFilters = {}, signal?: AbortSignal) =>
    get<Page<DistributionOut>>("/deliveries", filters as RequestOptions["query"], signal),
  getDelivery: (id: string) => get<DistributionOut>(`/deliveries/${id}`),
  approveDelivery: (id: string, payload: DeliveryApproveIn, idempotencyKey: string) =>
    post<DistributionOut>(`/deliveries/${id}/approve`, payload, { idempotencyKey }),
  rejectDelivery: (id: string, reason: string) => post<DistributionOut>(`/deliveries/${id}/reject`, { reason }),
  cancelDelivery: (id: string, reason?: string) =>
    post<DistributionOut>(`/deliveries/${id}/cancel`, reason ? { reason } : undefined),

  /* analytics */
  overview: (filters: { campaign_id?: string; from?: string; to?: string } = {}) =>
    get<OverviewOut>("/analytics/overview", filters),
  distributorPerformance: (filters: { campaign_id?: string; from?: string; to?: string } = {}) =>
    get<DistributorPerfOut[]>("/analytics/distributors", filters),
  sitePerformance: (filters: { campaign_id?: string; from?: string; to?: string } = {}) =>
    get<SitePerfOut[]>("/analytics/sites", filters),
  mapSites: (filters: { bbox?: string; campaign_id?: string; distributor_user_id?: string } = {}) =>
    get<MapSiteOut[]>("/analytics/map-sites", filters),

  /* settings + audit */
  getSettings: () => get<SettingsOut>("/settings"),
  patchSettings: (payload: SettingsPatchIn) => request<SettingsOut>("PATCH", "/settings", { body: payload }),
  auditEvents: (filters: AuditEventFilters = {}) =>
    get<Page<AuditEventOut>>("/audit/events", filters as RequestOptions["query"]),
};

function get<T>(path: string, query?: RequestOptions["query"], signal?: AbortSignal): Promise<T> {
  return request<T>("GET", path, { query, signal });
}

function post<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
  return request<T>("POST", path, { ...options, body });
}

export type { DistributionOut, Page };
