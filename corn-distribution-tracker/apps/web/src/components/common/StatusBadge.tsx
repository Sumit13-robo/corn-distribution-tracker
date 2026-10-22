import { humanizeStatus } from "../../lib/format";

type Tone = "neutral" | "success" | "pending" | "warning" | "danger" | "info";

/** Status -> tone. Tones pair with a text label; color is never the only cue. */
const TONE_BY_STATUS: Record<string, Tone> = {
  APPROVED: "success",
  ACTIVE: "success",
  PASS: "success",
  SUBMITTED: "pending",
  QUEUED: "pending",
  UPLOADING: "pending",
  PENDING: "pending",
  DRAFT: "info",
  LOCAL_DRAFT: "info",
  WARNING: "warning",
  PAUSED: "warning",
  EXCEPTION: "danger",
  REJECTED: "danger",
  LOSS: "danger",
  CANCELLED: "neutral",
  CLOSED: "neutral",
  EMPTY: "neutral",
  REVERSAL: "info",
  UNAVAILABLE: "neutral",
};

export function statusTone(status: string): Tone {
  return TONE_BY_STATUS[status.toUpperCase()] ?? "neutral";
}

export function StatusBadge({
  status,
  label,
  tone,
}: {
  status: string;
  label?: string;
  tone?: Tone;
}) {
  return (
    <span className="status-badge" data-tone={tone ?? statusTone(status)}>
      <span aria-hidden="true" /> {label ?? humanizeStatus(status)}
    </span>
  );
}
