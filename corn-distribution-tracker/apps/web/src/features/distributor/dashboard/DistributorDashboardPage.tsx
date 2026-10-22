import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../../lib/api-client";
import { queryKeys } from "../../../lib/query-client";
import { StatCard } from "../../../components/common/StatCard";
import { StatusBadge } from "../../../components/common/StatusBadge";
import { EmptyState } from "../../../components/common/EmptyState";
import { ErrorState } from "../../../components/common/ErrorState";
import { getCurrentUserId, useSession } from "../../../lib/session";
import { loadDrafts } from "../offline/offlineQueue";
import { formatDateTime, formatKg } from "../../../lib/format";
/**
 * Distributor home (SCREEN_SPECS "Overview"): cards for available stock,
 * remaining target, pending/approved quantities and the local draft queue,
 * plus the primary action and assigned sites with clear progress.
 */
export function DistributorDashboardPage() {
  const session = useSession();
  const overview = useQuery({ queryKey: queryKeys.overview(null), queryFn: () => api.overview() });
  const assignments = useQuery({ queryKey: queryKeys.myAssignments(), queryFn: () => api.myAssignments() });
  const stock = useQuery({ queryKey: queryKeys.inventorySummary(), queryFn: () => api.inventorySummary() });

  const userId = getCurrentUserId();
  const drafts = userId ? loadDrafts(userId) : [];

  const myAvailable = (stock.data?.accounts ?? [])
    .filter((account) => account.account_type === "DISTRIBUTOR")
    .reduce((acc, account) => acc + Number(account.available_kg), 0);

  const approvedTotal = (assignments.data ?? []).reduce((acc, item) => acc + Number(item.approved_kg), 0);
  const pendingTotal = (assignments.data ?? []).reduce((acc, item) => acc + Number(item.pending_kg), 0);
  const remainingTotal = (assignments.data ?? []).reduce((acc, item) => acc + Number(item.remaining_target_kg), 0);

  if (overview.isError) {
    return <ErrorState error={overview.error} onRetry={() => void overview.refetch()} />;
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>My workspace</h1>
          <p className="subtitle">
            Welcome{session.user ? `, ${session.user.display_name}` : ""}. Update a site to submit a delivery with
            photo and location evidence.
          </p>
        </div>
        <Link className="btn" to="/my-sites" data-testid="primary-action">
          Update a site
        </Link>
      </div>

      <div className="metric-row">
        <StatCard label="Available stock" value={formatKg(String(myAvailable))} unit="kg" definition="Allocated to you and not yet reserved by a pending submission." />
        <StatCard label="Remaining target" value={formatKg(String(remainingTotal))} unit="kg" definition="Assignment targets minus approved kilograms." />
        <StatCard label="Pending review" value={formatKg(String(pendingTotal))} unit="kg" hint={`${overview.data?.open_review_count ?? 0} record(s)`} definition="Submitted and awaiting reviewer decision." />
        <StatCard label="Approved" value={formatKg(String(approvedTotal))} unit="kg" definition="Approved by a reviewer and posted to the site account." />
        <StatCard
          label="Local drafts / queue"
          value={drafts.filter((draft) => draft.state !== "SUBMITTED").length}
          hint={drafts.length > 0 ? `Last saved ${formatDateTime(drafts[drafts.length - 1]?.updatedAt)}` : "No drafts on this device"}
          definition="Stored only in this browser for your account; queued drafts sync automatically."
        />
      </div>

      <div className="section">
        <h2>Assigned sites</h2>
        {assignments.isError ? (
          <ErrorState error={assignments.error} onRetry={() => void assignments.refetch()} />
        ) : assignments.isLoading ? (
          <div className="skeleton" style={{ height: 120 }} />
        ) : (assignments.data?.length ?? 0) === 0 ? (
          <EmptyState
            title="No assignments yet."
            description="Your coordinator assigns sites and targets through the campaign planner."
          />
        ) : (
          <ul className="stack" style={{ margin: 0, paddingLeft: 0, listStyle: "none" }}>
            {(assignments.data ?? []).map((item) => {
              const progress = Number(item.target_kg) > 0 ? Math.min(100, (Number(item.approved_kg) / Number(item.target_kg)) * 100) : 0;
              return (
                <li key={item.assignment_id} className="section" style={{ marginBottom: 0 }}>
                  <div className="row">
                    <strong>{item.site?.site_code ?? "Site"}</strong>
                    <span>{item.site?.name}</span>
                    <StatusBadge status={item.status} />
                    <span className="grow" />
                    <Link className="btn secondary small" to={`/my-sites/${item.site?.id ?? ""}`}>
                      Open site
                    </Link>
                  </div>
                  <div className="small muted" style={{ margin: "var(--space-1) 0" }}>
                    target {formatKg(item.target_kg)} kg · approved {formatKg(item.approved_kg)} kg · pending{" "}
                    {formatKg(item.pending_kg)} kg · remaining {formatKg(item.remaining_target_kg)} kg
                    {item.over_target_kg !== "0" ? ` · over target ${formatKg(item.over_target_kg)} kg` : ""}
                    {item.due_at ? ` · due ${formatDateTime(item.due_at)}` : ""}
                  </div>
                  <div
                    role="progressbar"
                    aria-valuenow={Math.round(progress)}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-label={`Site ${item.site?.site_code ?? ""} progress: approved of target`}
                    style={{
                      height: 8,
                      borderRadius: 4,
                      background: "var(--color-surface-alt)",
                      overflow: "hidden",
                    }}
                  >
                    <div style={{ height: "100%", width: `${progress}%`, background: "var(--color-brand-600)" }} />
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {overview.data && overview.data.flagged_record_count > 0 ? (
        <div className="notice warning" role="status">
          {overview.data.flagged_record_count} of your records carry validation flags that reviewers are working
          through. Re-check photo/location guidance before the next submission.
        </div>
      ) : null}
    </div>
  );
}
