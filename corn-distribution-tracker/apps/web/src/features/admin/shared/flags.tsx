import { StatusBadge } from "../../../components/common/StatusBadge";
import type { DistributionOut } from "../../../types/domain";

/**
 * Compact flag chips for a distribution record (shared by the overview queue
 * and the review workspace). Validation and location flags are shown with
 * words, never color alone.
 */
export function distributionFlagSummary(record: DistributionOut) {
  if (record.geo_flags.length === 0 && record.geo_status === "PASS") {
    return <span className="muted small">None</span>;
  }
  return (
    <span className="flag-chips">
      <StatusBadge status={record.geo_status} />
      {record.geo_flags.map((flag) => (
        <span key={flag} className="status-badge" data-tone="warning">
          {flag.replace(/_/g, " ").toLowerCase()}
        </span>
      ))}
    </span>
  );
}
