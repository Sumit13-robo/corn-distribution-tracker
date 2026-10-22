import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../../lib/api-client";
import { queryKeys } from "../../../lib/query-client";
import { StatCard } from "../../../components/common/StatCard";
import { StatusBadge } from "../../../components/common/StatusBadge";
import { DataTable } from "../../../components/common/DataTable";
import { EmptyState } from "../../../components/common/EmptyState";
import { ErrorState } from "../../../components/common/ErrorState";
import { formatAge, formatDistance, formatKg } from "../../../lib/format";
import { distributionFlagSummary } from "../../../features/admin/shared/flags";

/**
 * Admin overview (SCREEN_SPECS "Overview"): KPI row with definitions, pending
 * review queue with flags, distributor performance list, and recent audit
 * events. Every metric links to the filtered view it comes from.
 */
export function AdminDashboardPage() {
  const overview = useQuery({
    queryKey: queryKeys.overview(null),
    queryFn: () => api.overview(),
  });
  const pendingQueue = useQuery({
    queryKey: queryKeys.deliveries({ status: "SUBMITTED", limit: 6, offset: 0 }),
    queryFn: () => api.listDeliveries({ status: "SUBMITTED", limit: 6, offset: 0 }),
  });
  const distributorStats = useQuery({
    queryKey: queryKeys.distributorPerformance(null),
    queryFn: () => api.distributorPerformance(),
  });
  const audit = useQuery({
    queryKey: queryKeys.auditEvents({ limit: "6" }),
    queryFn: () => api.auditEvents({ limit: 6, offset: 0 }),
  });

  const stock = overview.data?.stock;

  if (overview.isLoading) {
    return (
      <section aria-busy="true" aria-live="polite">
        <div className="skeleton" style={{ height: 120, marginBottom: "var(--space-4)" }} />
        <div className="skeleton" style={{ height: 240 }} />
      </section>
    );
  }

  if (overview.isError) {
    return <ErrorState error={overview.error} onRetry={() => void overview.refetch()} />;
  }

  if (!overview.data) return <EmptyState title="No overview yet." />;

  const data = overview.data;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Overview</h1>
          <p className="subtitle">Role-scoped metrics (docs/SCREEN_SPECS). All quantities are canonical kilograms.</p>
        </div>
        <Link className="btn ghost" to="/analytics">
          Open analytics →
        </Link>
      </div>

      <div className="metric-row">
        <StatCard
          label="Approved delivered"
          value={formatKg(data.approved_delivered_kg)}
          unit="kg"
          definition="Sum of approved submissions in the selected scope."
        />
        <StatCard
          label="Pending review"
          value={formatKg(data.submitted_pending_kg)}
          unit="kg"
          hint={`${data.open_review_count} record(s) awaiting review`}
          definition="Submitted records not yet approved or rejected."
        />
        <StatCard
          label="Remaining target"
          value={formatKg(data.remaining_target_kg)}
          unit="kg"
          definition="Assignment targets minus approved kilograms."
        />
        <StatCard
          label="Flagged records"
          value={data.flagged_record_count}
          definition="Records carrying validation or location flags."
        />
        <StatCard
          label="Central stock"
          value={formatKg(stock?.central_on_hand_kg)}
          unit="kg"
          definition="Posted balance of central stock accounts."
        />
        <StatCard
          label="Held by distributors"
          value={formatKg(stock?.distributor_held_kg)}
          unit="kg"
          definition="Allocated stock not yet delivered."
        />
      </div>

      <div className="section">
        <h2>Pending review queue</h2>
        <p className="muted small">Flagged records surface first; opening one goes to the review workspace.</p>
        {pendingQueue.isError ? (
          <ErrorState error={pendingQueue.error} onRetry={() => void pendingQueue.refetch()} />
        ) : pendingQueue.isLoading ? (
          <div className="skeleton" style={{ height: 80 }} />
        ) : (pendingQueue.data?.items.length ?? 0) === 0 ? (
          <EmptyState
            title="Nothing waiting for review."
            description="Submitted records will appear here as distributors sync their updates."
            action={
              <Link className="btn secondary" to="/evidence">
                Open review workspace
              </Link>
            }
          />
        ) : (
          <DataTable
            caption="Pending review queue"
            rowKey={(row) => row.id}
            emptyState={<EmptyState title="Nothing waiting for review." />}
            rows={pendingQueue.data?.items ?? []}
            columns={[
              {
                key: "site",
                header: "Site",
                sortValue: (row) => row.site_id,
                render: (row) => (
                  <Link to={`/evidence?site_id=${row.site_id}`}>Site {row.site_id.slice(0, 8)}…</Link>
                ),
              },
              {
                key: "distributor",
                header: "Distributor",
                sortValue: (row) => row.distributor_user_id,
                render: (row) => (
                  <Link to={`/evidence?distributor_user_id=${row.distributor_user_id}`}>
                    {row.distributor_user_id.slice(0, 8)}…
                  </Link>
                ),
              },
              {
                key: "quantity_kg",
                header: "Quantity (kg)",
                numeric: true,
                sortValue: (row) => Number(row.quantity_kg),
              },
              {
                key: "age",
                header: "Age",
                sortValue: (row) => row.submitted_at,
                render: (row) => formatAge(row.submitted_at),
              },
              {
                key: "geo",
                header: "Location",
                sortValue: (row) => row.geo_status,
                render: (row) => (
                  <span className="row">
                    <StatusBadge status={row.geo_status} />
                    <span className="small muted">{formatDistance(row.distance_to_site_m)}</span>
                  </span>
                ),
              },
              {
                key: "flags",
                header: "Flags",
                render: (row) => distributionFlagSummary(row),
              },
              {
                key: "open",
                header: "",
                render: (row) => (
                  <Link className="btn secondary" to={`/evidence?record_id=${row.id}`}>
                    Review
                  </Link>
                ),
              },
            ]}
          />
        )}
      </div>

      <div className="section">
        <h2>Distributor performance</h2>
        <p className="muted small">{distributorStats.data?.[0]?.denominator_note}</p>
        {distributorStats.isError ? (
          <ErrorState error={distributorStats.error} onRetry={() => void distributorStats.refetch()} />
        ) : distributorStats.isLoading ? (
          <div className="skeleton" style={{ height: 80 }} />
        ) : (distributorStats.data?.length ?? 0) === 0 ? (
          <EmptyState title="No distributors with targets yet." action={<Link className="btn secondary" to="/distributors">Manage distributors</Link>} />
        ) : (
          <DataTable
            caption="Distributor performance summary"
            rowKey={(row) => row.distributor_user_id}
            emptyState={null}
            rows={distributorStats.data ?? []}
            columns={[
              { key: "display_name", header: "Name", sortValue: (row) => row.display_name },
              {
                key: "approved_kg",
                header: "Approved (kg)",
                numeric: true,
                sortValue: (row) => Number(row.approved_kg),
              },
              {
                key: "pending_kg",
                header: "Pending (kg)",
                numeric: true,
                sortValue: (row) => Number(row.pending_kg),
              },
              {
                key: "remaining",
                header: "Remaining (kg)",
                numeric: true,
                sortValue: (row) => Number(row.remaining_target_kg),
              },
              {
                key: "flagged_submissions",
                header: "Flagged",
                numeric: true,
                sortValue: (row) => row.flagged_submissions,
              },
            ]}
          />
        )}
      </div>

      <div className="section">
        <h2>Recent audit events</h2>
        {audit.isError ? (
          <ErrorState error={audit.error} onRetry={() => void audit.refetch()} />
        ) : audit.isLoading ? (
          <div className="skeleton" style={{ height: 80 }} />
        ) : (audit.data?.items.length ?? 0) === 0 ? (
          <EmptyState title="No audit events yet." />
        ) : (
          <ul className="stack small" style={{ margin: 0, paddingLeft: 0, listStyle: "none" }}>
            {(audit.data?.items ?? []).map((event) => (
              <li key={event.id} className="row" style={{ gap: "var(--space-2)" }}>
                <code className="num">{event.action}</code>
                <span className="muted">
                  {event.target_type} {event.target_id ? `· ${event.target_id.slice(0, 8)}…` : ""}
                </span>
                <span className="grow" />
                <Link to="/audit" className="small">
                  details
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
