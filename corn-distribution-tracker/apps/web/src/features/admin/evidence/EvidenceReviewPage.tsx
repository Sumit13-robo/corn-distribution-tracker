import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../../../lib/api-client";
import { queryKeys } from "../../../lib/query-client";
import { DataTable } from "../../../components/common/DataTable";
import { EmptyState } from "../../../components/common/EmptyState";
import { ErrorState } from "../../../components/common/ErrorState";
import { StatusBadge } from "../../../components/common/StatusBadge";
import { ConfirmDialog } from "../../../components/common/ConfirmDialog";
import { FormField } from "../../../components/common/FormField";
import { StatCard } from "../../../components/common/StatCard";
import { useToast } from "../../../app/providers";
import { distributionFlagSummary } from "../shared/flags";
import { formatAge, formatBytes, formatDateTime, formatDistance, formatKg, humanizeStatus } from "../../../lib/format";
import type { EvidenceOut } from "../../../types/domain";
import { newId } from "../../../lib/api-client";

/**
 * Evidence review workspace (SCREEN_SPECS "Evidence review"): pending queue
 * with site/distributor/quantity/age/flags, full detail with private evidence,
 * and approve / reject / cancel actions. Approval posts a stock movement on
 * the server — the UI states this before the admin confirms.
 */
export function EvidenceReviewPage() {
  const [params, setParams] = useSearchParams();
  const queryClient = useQueryClient();
  const toast = useToast();

  const siteFilter = params.get("site_id") ?? undefined;
  const distributorFilter = params.get("distributor_user_id") ?? undefined;
  const selectedId = params.get("record_id") ?? null;

  const queue = useQuery({
    queryKey: queryKeys.deliveries({ status: "SUBMITTED", site_id: siteFilter, distributor_user_id: distributorFilter, limit: 25, offset: 0 }),
    queryFn: () =>
      api.listDeliveries({
        status: "SUBMITTED",
        site_id: siteFilter,
        distributor_user_id: distributorFilter,
        limit: 25,
        offset: 0,
      }),
  });

  const selected = useQuery({
    queryKey: queryKeys.delivery(selectedId ?? "none"),
    queryFn: () => api.getDelivery(selectedId as string),
    enabled: selectedId !== null,
  });

  const [action, setAction] = useState<"approve" | "reject" | "cancel" | null>(null);
  const [approveException, setApproveException] = useState("");
  const [approveNote, setApproveNote] = useState("");
  const [rejectReason, setRejectReason] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);

  const approve = useMutation({
    mutationFn: (input: { id: string; exception_reason: string; review_note: string }) =>
      api.approveDelivery(
        input.id,
        {
          exception_reason: input.exception_reason || null,
          review_note: input.review_note || null,
        },
        newId(),
      ),
  });
  const reject = useMutation({
    mutationFn: (input: { id: string; reason: string }) => api.rejectDelivery(input.id, input.reason),
  });
  const cancelAction = useMutation({
    mutationFn: (input: { id: string; reason: string }) =>
      api.cancelDelivery(input.id, input.reason || undefined),
  });

  useEffect(() => {
    if (!selectedId && params.get("record_id")) setParams({}, { replace: true });
  }, [selectedId, params, setParams]);

  function afterMutation(message: string) {
    toast.notify("success", message);
    setAction(null);
    setActionError(null);
    setApproveException("");
    setApproveNote("");
    setRejectReason("");
    void queryClient.invalidateQueries({ queryKey: ["deliveries"] });
    void queryClient.invalidateQueries({ queryKey: ["analytics-overview"] });
    void queryClient.invalidateQueries({ queryKey: ["delivery"] });
  }

  function runAction(kind: "approve" | "reject" | "cancel") {
    if (!selectedId) return;
    setActionError(null);
    void (async () => {
      try {
        if (kind === "approve") {
          await approve.mutateAsync({ id: selectedId, exception_reason: approveException.trim(), review_note: approveNote.trim() });
          afterMutation("Approved — the stock movement was posted on the server.");
        } else if (kind === "reject") {
          await reject.mutateAsync({ id: selectedId, reason: rejectReason.trim() });
          afterMutation("Rejected with the reason recorded.");
        } else {
          await cancelAction.mutateAsync({ id: selectedId, reason: "" });
          afterMutation("Record cancelled.");
        }
      } catch (err) {
        setActionError(err instanceof ApiError ? err.message : "The action failed. Try again.");
      }
    })();
  }

  const record = selected.data ?? null;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Evidence review</h1>
          <p className="subtitle">Review pending submissions; approving posts stock movements on the server.</p>
        </div>
      </div>

      <div className="section">
        <div className="row">
          <h2 className="grow">Pending queue</h2>
          {siteFilter ? (
            <button type="button" className="btn ghost small" onClick={() => setParams({})}>
              Clear site filter
            </button>
          ) : null}
        </div>
        {queue.isError ? (
          <ErrorState error={queue.error} onRetry={() => void queue.refetch()} />
        ) : queue.isLoading ? (
          <div className="skeleton" style={{ height: 120 }} />
        ) : (queue.data?.items.length ?? 0) === 0 ? (
          <EmptyState
            title="Queue is clear."
            description="Approved and rejected records are available through analytics and the audit trail."
          />
        ) : (
          <DataTable
            caption="Pending submissions queue"
            rowKey={(row) => row.id}
            emptyState={<EmptyState title="Queue is clear." />}
            rows={queue.data?.items ?? []}
            columns={[
              {
                key: "site",
                header: "Site",
                sortValue: (row) => row.site_id,
                render: (row) => (
                  <button type="button" className="btn ghost" style={{ padding: 0 }} onClick={() => setParams({ site_id: row.site_id })}>
                    {row.site_id.slice(0, 8)}…
                  </button>
                ),
              },
              {
                key: "quantity",
                header: "Quantity (kg)",
                numeric: true,
                sortValue: (row) => Number(row.quantity_kg),
                render: (row) => formatKg(row.quantity_kg),
              },
              { key: "age", header: "Age", sortValue: (row) => row.submitted_at, render: (row) => formatAge(row.submitted_at) },
              { key: "geo", header: "Location", render: (row) => <StatusBadge status={row.geo_status} /> },
              { key: "flags", header: "Flags", render: (row) => distributionFlagSummary(row) },
              {
                key: "open",
                header: "",
                render: (row) => (
                  <button type="button" className="btn secondary" onClick={() => setParams({ record_id: row.id })}>
                    Review
                  </button>
                ),
              },
            ]}
          />
        )}
      </div>

      {selected.isLoading ? <div className="skeleton" style={{ height: 200 }} /> : null}
      {selected.isError ? <ErrorState error={selected.error} onRetry={() => void selected.refetch()} /> : null}

      {record ? (
        <div className="section" data-testid="review-detail">
          <div className="row">
            <h2>Record {record.id.slice(0, 8)}…</h2>
            <StatusBadge status={record.status} />
            <span className="grow" />
            <span className="small muted">submitted {formatAge(record.submitted_at)} ago</span>
          </div>

          <div className="metric-row">
            <StatCard label="Quantity" value={formatKg(record.quantity_kg)} unit="kg" />
            <StatCard label="Distance to site" value={formatDistance(record.distance_to_site_m)} definition="Server-computed geodesic distance (Vincenty WGS84)." />
            <StatCard label="Location fix" value={humanizeStatus(record.geo_status)} definition={record.location_accuracy_m ? `Accuracy ${record.location_accuracy_m} m` : "No accuracy reported"} />
            <StatCard label="Submitted at" value={formatDateTime(record.submitted_at)} definition={`Client created: ${formatDateTime(record.client_created_at)}`} />
          </div>

          <div className="row" style={{ alignItems: "flex-start", marginTop: "var(--space-3)" }}>
            <dl className="dl-grid grow">
              <dt>Assignment</dt>
              <dd>
                <code className="num">{record.assignment_id}</code>
              </dd>
              <dt>Campaign</dt>
              <dd>{record.campaign_id ? `campaign ${record.campaign_id.slice(0, 8)}…` : "—"}</dd>
              <dt>Site</dt>
              <dd>
                <code className="num">{record.site_id}</code>
              </dd>
              <dt>Distributor</dt>
              <dd>
                <code className="num">{record.distributor_user_id}</code>
              </dd>
              <dt>Coordinates</dt>
              <dd>
                {record.location_latitude && record.location_longitude
                  ? `${record.location_latitude}, ${record.location_longitude}`
                  : "not provided"}
              </dd>
              <dt>Device reported time</dt>
              <dd>{record.device_reported_location_time ? formatDateTime(record.device_reported_location_time) : "—"}</dd>
              <dt>Location timestamp</dt>
              <dd>{record.location_timestamp ? formatDateTime(record.location_timestamp) : "—"}</dd>
              <dt>Notes</dt>
              <dd>{record.notes ?? "—"}</dd>
              <dt>Flags</dt>
              <dd>
                <div className="flag-chips">
                  {record.geo_flags.length === 0 ? <StatusBadge status="PASS" /> : record.geo_flags.map((flag) => <StatusBadge key={flag} status={flag} />)}
                </div>
              </dd>
            </dl>
          </div>

          <h3 style={{ marginTop: "var(--space-4)" }}>Evidence ({record.evidence.length})</h3>
          {record.evidence.length === 0 ? (
            <EmptyState title="No evidence attached." description="This record cannot be approved without evidence." />
          ) : (
            <div className="row">
              {record.evidence.map((evidence) => (
                <EvidenceTile key={evidence.id} evidence={evidence} />
              ))}
            </div>
          )}

          {record.review_reason || record.review_exception_reason ? (
            <div className="notice" style={{ marginTop: "var(--space-3)" }}>
              Previous review: {humanizeStatus(record.status)}
              {record.review_reason ? ` · reason: ${record.review_reason}` : ""}
              {record.review_exception_reason ? ` · exception: ${record.review_exception_reason}` : ""}
            </div>
          ) : null}

          {record.status === "SUBMITTED" ? (
            <div className="form-actions" style={{ marginTop: "var(--space-4)" }}>
              <button type="button" className="btn" onClick={() => setAction("approve")} data-testid="approve-button">
                Approve…
              </button>
              <button type="button" className="btn destructive" onClick={() => setAction("reject")}>
                Reject…
              </button>
              <button type="button" className="btn secondary" onClick={() => setAction("cancel")}>
                Cancel record
              </button>
            </div>
          ) : null}
          {actionError ? <ErrorState error={new Error(actionError)} title="Action failed." /> : null}
        </div>
      ) : null}

      <ConfirmDialog
        open={action === "approve"}
        title="Approve this delivery?"
        message={
          <div className="stack">
            <p>
              Approving posts a stock movement to the immutable ledger (site account credited). This cannot be edited —
              a reversal is required afterwards.
            </p>
            <FormField id="approve-note" label="Review note (optional)">
              {(ids) => (
                <input
                  id="approve-note"
                  type="text"
                  value={approveNote}
                  aria-describedby={ids.describedBy}
                  onChange={(event) => setApproveNote(event.target.value)}
                />
              )}
            </FormField>
            <FormField
              id="approve-exception"
              label="Exception reason (only to override failed validations)"
              helper="Required when evidence or location checks have failed; recorded in the audit trail."
            >
              {(ids) => (
                <input
                  id="approve-exception"
                  type="text"
                  value={approveException}
                  aria-describedby={ids.describedBy}
                  onChange={(event) => setApproveException(event.target.value)}
                />
              )}
            </FormField>
          </div>
        }
        confirmLabel="Approve and post movement"
        busy={approve.isPending}
        onConfirm={() => runAction("approve")}
        onCancel={() => setAction(null)}
      />
      <ConfirmDialog
        open={action === "reject"}
        title="Reject this delivery?"
        message={
          <FormField id="reject-reason" label="Rejection reason" required helper="Required — the distributor sees this reason.">
            {(ids) => (
              <input
                id="reject-reason"
                type="text"
                value={rejectReason}
                aria-describedby={ids.describedBy}
                onChange={(event) => setRejectReason(event.target.value)}
              />
            )}
          </FormField>
        }
        confirmLabel="Reject"
        destructive
        busy={reject.isPending}
        onConfirm={() => {
          if (rejectReason.trim().length < 3) {
            setActionError("A rejection reason of at least 3 characters is required.");
            return;
          }
          runAction("reject");
        }}
        onCancel={() => setAction(null)}
      />
      <ConfirmDialog
        open={action === "cancel"}
        title="Cancel this submission?"
        message="Cancelling marks the record CANCELLED. Posted movements are never erased."
        confirmLabel="Cancel record"
        destructive
        busy={cancelAction.isPending}
        onConfirm={() => runAction("cancel")}
        onCancel={() => setAction(null)}
      />
    </div>
  );
}

function EvidenceTile({ evidence }: { evidence: EvidenceOut }) {
  const viewUrl = useQuery({
    queryKey: ["evidence-view-url", evidence.id],
    queryFn: () => api.evidenceViewUrl(evidence.id),
    staleTime: 60_000, // signed URLs are short-lived; do not hold them long
  });

  return (
    <figure className="evidence-card" style={{ width: 260, margin: 0 }} data-testid="evidence-tile">
      {viewUrl.isError ? (
        <div className="state-block small">
          <span className="title">Image unavailable</span>
          {viewUrl.error instanceof ApiError ? viewUrl.error.message : "The signed URL could not be fetched."}
        </div>
      ) : viewUrl.data ? (
        <img src={viewUrl.data.url} alt={`Evidence image ${evidence.id.slice(0, 8)} (content type ${evidence.content_type})`} />
      ) : (
        <div className="skeleton" style={{ height: 160 }} />
      )}
      <figcaption className="meta">
        <span>
          {evidence.content_type} · {formatBytes(evidence.size_bytes)}
        </span>
        <span>{evidence.capture_source}</span>
        {evidence.client_captured_at ? <span>Captured {formatDateTime(evidence.client_captured_at)}</span> : null}
        {evidence.server_received_at ? <span>Received {formatDateTime(evidence.server_received_at)}</span> : null}
        {evidence.exif_latitude && evidence.exif_longitude ? (
          <span>
            EXIF position: {evidence.exif_latitude}, {evidence.exif_longitude}
          </span>
        ) : null}
        {evidence.validation_flags.length > 0 ? (
          <span className="flag-chips">
            {evidence.validation_flags.map((flag) => (
              <StatusBadge key={flag} status={flag} />
            ))}
          </span>
        ) : null}
        <span className="muted">
          sha256 {evidence.sha256_hex.slice(0, 12)}… · {humanizeStatus(evidence.lifecycle_status)}
        </span>
      </figcaption>
    </figure>
  );
}
