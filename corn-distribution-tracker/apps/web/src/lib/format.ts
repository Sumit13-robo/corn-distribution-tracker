/**
 * Formatting helpers shared across screens. Quantities arrive as canonical
 * decimal-kg strings (NUMERIC(14,3)); they are rendered as submitted and are
 * never re-rounded in the client.
 */

export function cx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

/** Groups thousands and keeps the full canonical precision of the kg string. */
export function formatKg(value: string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 3 }).format(Number(value));
}

/** Formats a raw Number that is already display-scaled. */
export function formatNumber(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
}

/**
 * UTC timestamp rendering with an explicit "UTC" suffix: server timestamps are
 * ISO-8601 UTC and the UI never silently converts them.
 */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  const formatted = new Intl.DateTimeFormat("en-GB", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    timeZone: "UTC",
    hour12: false,
  }).format(date);
  return `${formatted} UTC`;
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("en-GB", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    timeZone: "UTC",
  }).format(date);
}

/** Coarse "time since" for review-queue ageing; falls back to absolute time. */
export function formatAge(iso: string | null | undefined, now: Date = new Date()): string {
  if (!iso) return "—";
  const then = new Date(iso);
  if (Number.isNaN(then.getTime())) return "—";
  const seconds = Math.max(0, Math.floor((now.getTime() - then.getTime()) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

/** Distances: metres under 1 km, otherwise kilometres with one decimal. */
export function formatDistance(meters: string | number | null | undefined): string {
  if (meters === null || meters === undefined || meters === "") return "—";
  const value = Number(meters);
  if (Number.isNaN(value)) return "—";
  if (value < 1000) return `${Math.round(value)} m`;
  return `${(value / 1000).toFixed(1)} km`;
}

export function formatBytes(bytes: number | null | undefined): string {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} kB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** Human label for machine status enums (kept in one place for consistency). */
export function humanizeStatus(status: string | null | undefined): string {
  if (!status) return "—";
  const map: Record<string, string> = {
    LOCAL_DRAFT: "Local draft",
    QUEUED: "Queued to sync",
    UPLOADING: "Uploading",
    SUBMITTED: "Submitted",
    APPROVED: "Approved",
    REJECTED: "Rejected",
    CANCELLED: "Cancelled",
    DRAFT: "Draft",
    ACTIVE: "Active",
    PAUSED: "Paused",
    CLOSED: "Closed",
    PASS: "Location captured",
    WARNING: "Location captured",
    EXCEPTION: "Location captured",
    UNAVAILABLE: "No location",
    RECEIPT: "Receipt",
    TRANSFER: "Allocation",
    DELIVERY: "Delivery",
    RETURN: "Return",
    LOSS: "Loss",
    ADJUSTMENT: "Adjustment",
    REVERSAL: "Reversal",
    COMPLETE: "Complete",
    PENDING: "Pending",
    EMPTY: "No stock",
  };
  const mapped = map[status];
  if (mapped) return mapped;
  return status.replace(/_/g, " ").toLowerCase();
}
