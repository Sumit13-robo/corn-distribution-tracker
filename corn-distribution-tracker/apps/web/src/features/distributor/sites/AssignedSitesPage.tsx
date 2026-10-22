import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../../lib/api-client";
import { queryKeys } from "../../../lib/query-client";
import { EmptyState } from "../../../components/common/EmptyState";
import { ErrorState } from "../../../components/common/ErrorState";
import { FormField } from "../../../components/common/FormField";
import { StatusBadge } from "../../../components/common/StatusBadge";
import { formatDateTime, formatKg } from "../../../lib/format";

/**
 * Assigned sites (SCREEN_SPECS): search/filter the signed-in distributor's own
 * sites; each item shows code/name, target, submitted/pending/approved,
 * remaining target and due date when set. Scope comes from
 * GET /distributors/me/assignments (server-enforced).
 */
export function AssignedSitesPage() {
  const [search, setSearch] = useState("");
  const assignments = useQuery({ queryKey: queryKeys.myAssignments(), queryFn: () => api.myAssignments() });

  const filtered = (assignments.data ?? []).filter((item) => {
    if (!search.trim()) return true;
    const needle = search.trim().toLowerCase();
    return (
      (item.site?.site_code ?? "").toLowerCase().includes(needle) ||
      (item.site?.name ?? "").toLowerCase().includes(needle) ||
      (item.site?.region ?? "").toLowerCase().includes(needle)
    );
  });

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>My sites</h1>
          <p className="subtitle">Sites with your assignments; the list never contains other distributors' records.</p>
        </div>
      </div>

      <div className="section">
        <FormField id="site-search" label="Search my sites" helper="Code, name or region." className="grow">
          {(ids) => (
            <input
              id="site-search"
              type="search"
              value={search}
              aria-describedby={ids.describedBy}
              onChange={(event) => setSearch(event.target.value)}
            />
          )}
        </FormField>
      </div>

      {assignments.isError ? (
        <ErrorState error={assignments.error} onRetry={() => void assignments.refetch()} />
      ) : assignments.isLoading ? (
        <div className="skeleton" style={{ height: 200 }} />
      ) : filtered.length === 0 ? (
        <EmptyState
          title={search ? "No sites match that search." : "No assigned sites yet."}
          description={search ? "Try a different term." : "New assignments appear as soon as a coordinator plans them."}
        />
      ) : (
        <ul className="stack" style={{ margin: 0, paddingLeft: 0, listStyle: "none" }}>
          {filtered.map((item) => (
            <li key={item.assignment_id} className="section" style={{ marginBottom: 0 }}>
              <div className="row">
                <strong>{item.site?.site_code ?? "Site"}</strong>
                <span className="grow">{item.site?.name}</span>
                <StatusBadge status={item.status} />
              </div>
              <dl className="dl-grid" style={{ margin: "var(--space-2) 0" }}>
                <dt>Target</dt>
                <dd className="num">{formatKg(item.target_kg)} kg</dd>
                <dt>Approved</dt>
                <dd className="num">{formatKg(item.approved_kg)} kg</dd>
                <dt>Pending</dt>
                <dd className="num">{formatKg(item.pending_kg)} kg</dd>
                <dt>Remaining</dt>
                <dd className="num">{formatKg(item.remaining_target_kg)} kg</dd>
                <dt>Site address</dt>
                <dd>{item.site?.address_text ?? "—"}</dd>
                <dt>Due</dt>
                <dd>{item.due_at ? formatDateTime(item.due_at) : "No due date set"}</dd>
              </dl>
              <div className="form-actions">
                <Link className="btn secondary small" to={`/my-sites/${item.site?.id ?? ""}`}>
                  Site detail
                </Link>
                <Link className="btn small" to={`/deliver/new?assignment=${item.assignment_id}`}>
                  New delivery update
                </Link>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
