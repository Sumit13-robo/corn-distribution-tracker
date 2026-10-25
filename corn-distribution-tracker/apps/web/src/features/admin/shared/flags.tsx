import { StatusBadge } from "../../../components/common/StatusBadge";
import type { DistributionOut } from "../../../types/domain";

/**
 * Location flags retained on historical rows are informational only and must
 * never be presented as warnings. Approval is allowed from any captured place.
 */
const LOCATION_FLAGS = new Set([
  "GPS_MISSING",
  "GPS_STALE",
  "GPS_LOW_ACCURACY",
  "OUTSIDE_GEOFENCE",
  "EXIF_GPS_MISMATCH",
  "LOCATION_EXCEPTION",
]);

export function integrityFlagList(flags: string[]): string[] {
  return flags.filter((flag) => !LOCATION_FLAGS.has(flag));
}

export function integrityFlags(record: DistributionOut): string[] {
  return integrityFlagList(record.geo_flags);
}

/**
 * Compact evidence-integrity chips shared by the pending queue and review
 * workspace. Location quality is not a warning anymore.
 */
export function distributionFlagSummary(record: DistributionOut) {
  const flags = integrityFlags(record);
  if (flags.length === 0) {
    return <span className="muted small">None</span>;
  }
  return (
    <span className="flag-chips">
      {flags.map((flag) => (
        <span key={flag} className="status-badge" data-tone="warning">
          {flag.replace(/_/g, " ").toLowerCase()}
        </span>
      ))}
    </span>
  );
}

/** Explain a non-location evidence integrity flag in plain language. */
export function distributionFlagExplanation(record: DistributionOut): string | null {
  const flags = new Set(integrityFlags(record));
  const messages: string[] = [];
  if (flags.has("CAPTURE_TIME_MISMATCH")) {
    messages.push("The device/photo capture time differs from the reported location time.");
  }
  if (flags.has("DUPLICATE_IMAGE_HASH")) {
    messages.push("This image matches another submitted image hash.");
  }
  if (flags.has("UNEXPECTED_FILE_TYPE")) {
    messages.push("The uploaded file type was not the expected image type.");
  }
  return messages.length > 0 ? messages.join(" ") : null;
}

/** A location is informational; this label never blocks approval. */
export function locationCaptureLabel(record: DistributionOut): string {
  return record.location_latitude != null && record.location_longitude != null
    ? "Captured"
    : "Missing";
}

export function LocationCaptureBadge({ record }: { record: DistributionOut }) {
  const captured = record.location_latitude != null && record.location_longitude != null;
  return (
    <span className="small">
      <StatusBadge status={captured ? "PASS" : "UNAVAILABLE"} label={captured ? "Captured" : "Missing"} tone={captured ? "success" : "info"} />
    </span>
  );
}
