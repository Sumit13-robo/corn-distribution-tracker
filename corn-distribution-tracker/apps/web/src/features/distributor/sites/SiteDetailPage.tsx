import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../../lib/api-client";
import { queryKeys } from "../../../lib/query-client";
import { EmptyState } from "../../../components/common/EmptyState";
import { ErrorState } from "../../../components/common/ErrorState";
import { StatCard } from "../../../components/common/StatCard";
import { StatusBadge } from "../../../components/common/StatusBadge";
import { formatDateTime, formatKg } from "../../../lib/format";

/**
 * Site detail for the signed-in distributor (SCREEN_SPECS): site address and
 * expected pin context, assignment target/progress, previous own submissions,
 * and the CTA for a new update. Other distributors' records are never shown —
 * server scoping enforces ownership, this page only renders own rows.
 */
export function SiteDetailPage() {
  const { siteId = "" } = useParams();
  const assignments = useQuery({ queryKey: queryKeys.myAssignments(), queryFn: () => api.myAssignments() });
  const site = useQuery({
    queryKey: ["sites", "detail", siteId],
    queryFn: () => api.getSite(siteId),
    enabled: siteId !== "",
  });
  const progress = useQuery({
    queryKey: queryKeys.siteProgress(siteId, null),
    queryFn: () => api.siteProgress(siteId),
    enabled: siteId !== "",
  });
  const history = useQuery({
    queryKey: queryKeys.deliveries({ site_id: siteId, limit: 25, offset: 0 }),
    queryFn: () => api.listDeliveries({ site_id: siteId, limit: 25, offset: 0 }),
    enabled: siteId !== "",
  });

  const myAssignment = (assignments.data ?? []).find((item) => item.site?.id === siteId) ?? null;

  if (siteId === "") {
    return <EmptyState title="No site selected." />;
  }

  if (site.isError) {
    return <ErrorState error={site.error} onRetry={() => void site.refetch()} />;
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>
            {site.data ? `${site.data.site_code} — ${site.data.name}` : "Site"}
          </h1>
          <p className="subtitle">{site.data?.address_text ?? "No address recorded on site."}</p>
        </div>
        {myAssignment ? (
          <Link className="btn" to={`/deliver/new?assignment=${myAssignment.assignment_id}`}>
            New delivery update
          </Link>
        ) : (
          <Link className="btn secondary" to="/my-sites">
            Back to my sites
          </Link>
        )}
      </div>

      {site.data ? (
        <div className="section">
          <SiteLocationPanel
            latitude={site.data.latitude}
            longitude={site.data.longitude}
          />
        </div>
      ) : site.isLoading ? (
        <div className="skeleton" style={{ height: 160 }} />
      ) : null}

      {myAssignment ? (
        <div className="section">
          <h2>Assignment</h2>
          <div className="metric-row">
            <StatCard label="Target" value={formatKg(myAssignment.target_kg)} unit="kg" />
            <StatCard label="Approved" value={formatKg(myAssignment.approved_kg)} unit="kg" />
            <StatCard label="Pending" value={formatKg(myAssignment.pending_kg)} unit="kg" />
            <StatCard label="Remaining" value={formatKg(myAssignment.remaining_target_kg)} unit="kg" />
          </div>
          <p className="small muted">
            Status <StatusBadge status={myAssignment.status} />
            {myAssignment.due_at ? ` · due ${formatDateTime(myAssignment.due_at)}` : ""}
          </p>
        </div>
      ) : (
        <EmptyState title="No assignment here yet." description="This site has no active assignment for your account." />
      )}

      <div className="section">
        <h2>My previous submissions for this site</h2>
        {history.isError ? (
          <ErrorState error={history.error} onRetry={() => void history.refetch()} />
        ) : history.isLoading ? (
          <div className="skeleton" style={{ height: 100 }} />
        ) : (history.data?.items.length ?? 0) === 0 ? (
          <EmptyState title="No submissions for this site yet." description="Your first update will appear here after it syncs." />
        ) : (
          <ul className="stack small" style={{ margin: 0, paddingLeft: 0, listStyle: "none" }}>
            {(history.data?.items ?? []).map((record) => (
              <li key={record.id} className="row">
                <StatusBadge status={record.status} />
                <span className="num">{formatKg(record.quantity_kg)} kg</span>
                <span className="muted">
                  {record.location_latitude != null && record.location_longitude != null
                    ? "location captured"
                    : "no location"}
                </span>
                {record.review_reason ? <span className="muted">review: {record.review_reason}</span> : null}
                <span className="grow" />
                <span className="muted small">{formatDateTime(record.submitted_at)}</span>
              </li>
            ))}
          </ul>
        )}
        {progress.data?.last_visit_at ? (
          <p className="muted small">Last recorded visit: {formatDateTime(progress.data.last_visit_at)}</p>
        ) : null}
      </div>
    </div>
  );
}

/**
 * Site reference point, when one exists. It is shown for context only; the
 * captured device fix is stored separately and approval is allowed from any
 * recorded location. No tile service is required and none is faked.
 */
function SiteLocationPanel({
  latitude,
  longitude,
}: {
  latitude: string | null;
  longitude: string | null;
}) {
  if (latitude === null || longitude === null) {
    return (
      <div>
        <h2>Site location</h2>
        <p className="notice" role="status">
          No site reference location has been set. Your device fix is still captured and stored with each submission.
        </p>
      </div>
    );
  }
  return (
    <div>
      <h2>Site location</h2>
      <dl className="dl-grid">
        <dt>Coordinates</dt>
        <dd className="num">{latitude}, {longitude}</dd>
        <dt>Coordinate reference</dt>
        <dd>WGS 84 decimal degrees (server-stored canonical values)</dd>
      </dl>
      <p className="muted small">
        This reference point is for context only. The captured device fix is stored with each submission and is not
        proof against spoofing.
      </p>
    </div>
  );
}
