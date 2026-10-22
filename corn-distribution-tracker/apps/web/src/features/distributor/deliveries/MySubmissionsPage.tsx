import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../../lib/api-client";
import { queryKeys } from "../../../lib/query-client";
import { DataTable } from "../../../components/common/DataTable";
import { EmptyState } from "../../../components/common/EmptyState";
import { ErrorState } from "../../../components/common/ErrorState";
import { StatusBadge } from "../../../components/common/StatusBadge";
import { FormField } from "../../../components/common/FormField";
import { formatDateTime, formatDistance, formatKg, humanizeStatus } from "../../../lib/format";
import type { DistributionOut } from "../../../types/domain";

const STATUS_OPTIONS = ["SUBMITTED", "APPROVED", "REJECTED", "CANCELLED"] as const;

/**
 * My submissions (SCREEN_SPECS): only the signed-in distributor's records with
 * quantity, state, evidence status and review reason; the expanding detail row
 * carries the full submission history information.
 */
export function MySubmissionsPage() {
  const [status, setStatus] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const deliveries = useQuery({
    queryKey: queryKeys.deliveries({ status: status || undefined, limit: 25, offset: 0 }),
    queryFn: () => api.listDeliveries({ status: status || undefined, limit: 25, offset: 0 }),
    placeholderData: (previous) => previous,
  });

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>My submissions</h1>
          <p className="subtitle">Your records only (server-scoped). Rejected items are kept as context for new updates.</p>
        </div>
        <Link className="btn" to="/my-sites">
          New delivery update
        </Link>
      </div>

      <div className="section">
        <FormField id="status-filter" label="Status filter" helper="States come from the server; local drafts live in the submission form.">
          {(ids) => (
            <select
              id="status-filter"
              aria-describedby={ids.describedBy}
              value={status}
              onChange={(event) => setStatus(event.target.value)}
            >
              <option value="">All states</option>
              {STATUS_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {humanizeStatus(option)}
                </option>
              ))}
            </select>
          )}
        </FormField>
      </div>

      {deliveries.isError ? (
        <ErrorState error={deliveries.error} onRetry={() => void deliveries.refetch()} />
      ) : deliveries.isLoading ? (
        <div className="skeleton" style={{ height: 200 }} />
      ) : (deliveries.data?.items.length ?? 0) === 0 ? (
        <EmptyState
          title={status ? "No records with that state." : "No submissions yet."}
          description={status ? "Clear the filter to see your full history." : "Start from “My sites” to create your first delivery update."}
        />
      ) : (
        <div className="section">
          <DataTable
            caption="My submission history"
            rowKey={(row) => row.id}
            emptyState={<EmptyState title="No submissions." />}
            rows={deliveries.data?.items ?? []}
            rowExpandDetail={(row) => (
              <button
                type="button"
                className="btn ghost small"
                aria-expanded={expandedId === row.id}
                onClick={() => setExpandedId(expandedId === row.id ? null : row.id)}
              >
                {expandedId === row.id ? "Hide detail" : "Detail"}
              </button>
            )}
            columns={[
              {
                key: "site",
                header: "Site",
                sortValue: (row) => row.site_code,
                render: (row) => (
                  <span>
                    <strong>{row.site_code}</strong>
                    <span className="muted small" style={{ display: "block" }}>
                      {row.site_name}
                    </span>
                  </span>
                ),
              },
              { key: "submitted_at", header: "Submitted", sortValue: (row) => row.submitted_at, render: (row) => formatDateTime(row.submitted_at) },
              { key: "quantity_kg", header: "Quantity (kg)", numeric: true, sortValue: (row) => Number(row.quantity_kg), render: (row) => formatKg(row.quantity_kg) },
              { key: "status", header: "State", sortValue: (row) => row.status, render: (row) => <StatusBadge status={row.status} /> },
              {
                key: "evidence",
                header: "Evidence",
                numeric: true,
                sortValue: (row) => row.evidence.length,
                render: (row) =>
                  row.evidence.length > 0 ? (
                    `${row.evidence.length} ${row.evidence.length === 1 ? "image" : "images"}`
                  ) : (
                    <StatusBadge status="EXCEPTION" label="Missing" />
                  ),
              },
              {
                key: "review_reason",
                header: "Review reason",
                render: (row) => row.review_reason ?? (row.review_exception_reason ? `exception: ${row.review_exception_reason}` : "—"),
              },
            ]}
          />

          {(deliveries.data?.items ?? [])
            .filter((row) => row.id === expandedId)
            .map((record) => (
              <SubmissionDetail key={record.id} record={record} />
            ))}
        </div>
      )}
    </div>
  );
}

function SubmissionDetail({ record }: { record: DistributionOut }) {
  const firstEvidence = record.evidence[0];
  const viewUrl = useQuery({
    queryKey: ["evidence-view-url", firstEvidence?.id ?? "none"],
    queryFn: () => api.evidenceViewUrl(firstEvidence?.id ?? ""),
    enabled: Boolean(firstEvidence),
  });

  return (
    <div className="section" style={{ marginTop: "var(--space-3)" }} data-testid="submission-detail">
      <h3>
        Record <code className="num">{record.id}</code>
      </h3>
      <dl className="dl-grid">
        <dt>Site</dt>
        <dd>
          {record.site_code} — {record.site_name}
        </dd>
        <dt>State</dt>
        <dd>
          <StatusBadge status={record.status} />
        </dd>
        <dt>Submitted</dt>
        <dd>{formatDateTime(record.submitted_at)}</dd>
        <dt>Client created</dt>
        <dd>{record.client_created_at ? formatDateTime(record.client_created_at) : "—"}</dd>
        <dt>Reviewed</dt>
        <dd>{record.reviewed_at ? formatDateTime(record.reviewed_at) : "not reviewed yet"}</dd>
        <dt>Quantity</dt>
        <dd className="num">{formatKg(record.quantity_kg)} kg</dd>
        <dt>Location</dt>
        <dd>
          {record.location_latitude && record.location_longitude
            ? `${record.location_latitude}, ${record.location_longitude} · ±${record.location_accuracy_m ?? "?"} m`
            : "not provided"}
        </dd>
        <dt>Geodesic distance</dt>
        <dd>{formatDistance(record.distance_to_site_m)}</dd>
        <dt>Fix quality</dt>
        <dd>
          <StatusBadge status={record.geo_status} />
          {record.geo_flags.length > 0 ? ` · ${record.geo_flags.join(", ").toLowerCase()}` : ""}
        </dd>
        <dt>Notes</dt>
        <dd>{record.notes ?? "—"}</dd>
        {record.status === "APPROVED" && record.stock_movement_id ? (
          <>
            <dt>Ledger movement</dt>
            <dd>
              <code className="num">{record.stock_movement_id}</code> (site stock credited)
            </dd>
          </>
        ) : null}
        {record.status === "APPROVED" && !record.stock_movement_id ? (
          <>
            <dt>Ledger movement</dt>
            <dd>pending posting</dd>
          </>
        ) : null}
      </dl>

      {record.evidence.length > 0 ? (
        <div className="row" style={{ marginTop: "var(--space-2)" }}>
          {record.evidence.map((evidence) => (
            <figure key={evidence.id} className="evidence-card" style={{ width: 220, margin: 0 }}>
              {viewUrl.data && firstEvidence?.id === evidence.id ? (
                <img src={viewUrl.data.url} alt={`Evidence ${evidence.id.slice(0, 8)} (${evidence.content_type})`} />
              ) : (
                <div className="skeleton" style={{ height: 120 }} />
              )}
              <figcaption className="meta">
                <span>
                  {evidence.content_type} · capture {evidence.client_captured_at ? formatDateTime(evidence.client_captured_at) : "—"}
                </span>
                <StatusBadge status={evidence.lifecycle_status} label={humanizeStatus(evidence.lifecycle_status)} tone="info" />
              </figcaption>
            </figure>
          ))}
        </div>
      ) : (
        <p className="muted small">No evidence images on this record.</p>
      )}
    </div>
  );
}
