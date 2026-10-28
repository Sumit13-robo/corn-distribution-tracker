/**
 * Typed HTTP client for the API (docs/architecture/API_CONTRACT.md).
 *
 * Authentication is a Django HttpOnly session cookie. Unsafe requests also
 * send the double-submit CSRF token in X-CSRFToken. The SPA never stores
 * credentials in localStorage/sessionStorage. A 401 clears the local session;
 * there is no bearer token or refresh-token rotation.
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
  MapDeliveryOut,
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
  UploadCompletionOut,
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
  onAuthLost: () => void;
}

const auth: AuthHooks = {
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
  if (hooks.onAuthLost) auth.onAuthLost = hooks.onAuthLost;
}

/** Auth-flow requests handle their own failure; only data reads clear session. */
function isAuthFlowPath(path: string): boolean {
  return (
    path === "/auth/login" ||
    path === "/auth/me" ||
    path === "/auth/csrf" ||
    path === "/auth/logout" ||
    path === "/auth/forgot-password" ||
    path === "/auth/reset-password" ||
    path === "/auth/accept-invitation" ||
    path === "/auth/change-password"
  );
}

/* ------------------------------------------------------------------ CSRF */

const CSRF_COOKIE_NAME = "csrftoken";
let csrfToken: string | null = null;

function readCookie(name: string): string | null {
  if (typeof document === "undefined" || !document.cookie) return null;
  for (const part of document.cookie.split(";")) {
    const [rawName, ...rawValue] = part.trim().split("=");
    if (rawName === name) {
      try {
        return decodeURIComponent(rawValue.join("="));
      } catch {
        return rawValue.join("=");
      }
    }
  }
  return null;
}

/** Test/embedding hook; the normal path reads the Django csrftoken cookie. */
export function setCsrfToken(token: string | null): void {
  csrfToken = token;
}

/**
 * Returns the current CSRF token. Same-origin deployments read the Django
 * cookie; for a cross-origin API the cookie belongs to another origin, so the
 * client asks GET /auth/csrf for the paired value.
 */
async function ensureCsrfToken(): Promise<string | null> {
  const fromCookie = readCookie(CSRF_COOKIE_NAME);
  if (fromCookie) {
    csrfToken = fromCookie;
    return csrfToken;
  }
  if (csrfToken) return csrfToken;
  try {
    const response = await fetch(`${BASE_URL}/auth/csrf`, {
      method: "GET",
      credentials: "include",
      headers: { Accept: "application/json" },
    });
    if (!response.ok) return null;
    const body = (await response.json()) as { csrf_token?: string };
    csrfToken = body.csrf_token ?? null;
    return csrfToken;
  } catch {
    return null;
  }
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
  const headers: Record<string, string> = { Accept: "application/json" };
  if (method !== "GET") {
    const token = await ensureCsrfToken();
    if (token) headers["X-CSRFToken"] = token;
  }
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  if (options.idempotencyKey) headers["Idempotency-Key"] = options.idempotencyKey;

  const response = await fetch(buildUrl(path, options.query), {
    method,
    headers,
    credentials: "include",
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    signal: options.signal,
  });

  if (response.status === 401 && !isAuthFlowPath(path) && !options.signal?.aborted) {
    auth.onAuthLost();
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
 * a same-origin API endpoint (session cookie + CSRF header) or a presigned
 * object-storage URL (authorization is baked into the URL: only the
 * intent-provided headers may be sent, or the signature would break).
 */
export async function uploadBlob(
  intent: { upload_url: string; headers?: Record<string, string> },
  blob: Blob,
): Promise<void> {
  const absolute = new URL(intent.upload_url, window.location.origin);
  const isApiEndpoint =
    absolute.origin === window.location.origin && absolute.pathname.startsWith("/api/");
  const headers: Record<string, string> = { ...(intent.headers ?? {}) };
  if (isApiEndpoint) {
    const token = await ensureCsrfToken();
    if (token) headers["X-CSRFToken"] = token;
  }
  const response = await fetch(absolute.toString(), {
    method: "PUT",
    headers,
    credentials: isApiEndpoint ? "include" : "omit",
    body: blob,
  });
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
  const response = await fetch(buildUrl("/exports/distributions.csv", query as RequestOptions["query"]), {
    method: "GET",
    headers,
    credentials: "include",
    signal,
  });
  if (response.status === 401) auth.onAuthLost();
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
  completeUploadIntent: (intentId: string) =>
    post<UploadCompletionOut>(`/evidence/upload-intents/${intentId}/complete`),
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
  mapDeliveries: (filters: { bbox?: string; campaign_id?: string; distributor_user_id?: string } = {}) =>
    get<MapDeliveryOut[]>("/analytics/map-deliveries", filters),
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
