import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../../lib/api-client";
import { queryKeys } from "../../../lib/query-client";
import { DataTable } from "../../../components/common/DataTable";
import { EmptyState } from "../../../components/common/EmptyState";
import { ErrorState } from "../../../components/common/ErrorState";
import { FormField } from "../../../components/common/FormField";
import { formatDateTime, formatNumber } from "../../../lib/format";

/**
 * Audit trail (SCREEN_SPECS): admin-only, server-side filtered history. There
 * is no edit or delete UI — audit records are immutable by contract.
 */
export function AuditTrailPage() {
  const [filters, setFilters] = useState({ action: "", from: "", to: "" });
  const [search, setSearch] = useState({ action: "", from: "", to: "" });

  const queryFilters = useMemo(
    () => ({
      action: search.action || undefined,
      from: search.from ? new Date(`${search.from}T00:00:00Z`).toISOString() : undefined,
      to: search.to ? new Date(`${search.to}T23:59:59Z`).toISOString() : undefined,
      limit: 25,
      offset: 0,
    }),
    [search],
  );

  const events = useQuery({
    queryKey: queryKeys.auditEvents({
      action: search.action,
      from: search.from,
      to: search.to,
      limit: "25",
      offset: "0",
    }),
    queryFn: () => api.auditEvents(queryFilters),
    placeholderData: (previous) => previous,
  });

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Audit trail</h1>
          <p className="subtitle">
            Immutable event history.{" "}
            {events.data
              ? `${formatNumber(events.data.total)} events in this scope.`
              : "Loading event count…"}
          </p>
        </div>
      </div>

      <div className="section">
        <form
          className="row"
          role="search"
          onSubmit={(event) => {
            event.preventDefault();
            setSearch({ ...filters });
          }}
        >
          <FormField id="audit-action" label="Action" className="grow" helper="e.g. site.updated, export.distributions">
            {(ids) => (
              <input
                id="audit-action"
                type="text"
                value={filters.action}
                aria-describedby={ids.describedBy}
                onChange={(event) => setFilters({ ...filters, action: event.target.value })}
              />
            )}
          </FormField>
          <FormField id="audit-from" label="From (UTC)" className="grow">
            {(ids) => (
              <input
                id="audit-from"
                type="date"
                value={filters.from}
                aria-describedby={ids.describedBy}
                onChange={(event) => setFilters({ ...filters, from: event.target.value })}
              />
            )}
          </FormField>
          <FormField id="audit-to" label="To (UTC)" className="grow">
            {(ids) => (
              <input
                id="audit-to"
                type="date"
                value={filters.to}
                aria-describedby={ids.describedBy}
                onChange={(event) => setFilters({ ...filters, to: event.target.value })}
              />
            )}
          </FormField>
          <div className="row">
            <button type="submit" className="btn secondary">
              Apply
            </button>
            <button
              type="button"
              className="btn ghost"
              onClick={() => {
                setFilters({ action: "", from: "", to: "" });
                setSearch({ action: "", from: "", to: "" });
              }}
            >
              Clear
            </button>
          </div>
        </form>
      </div>

      {events.isError ? (
        <ErrorState error={events.error} onRetry={() => void events.refetch()} />
      ) : events.isLoading ? (
        <div className="skeleton" style={{ height: 200 }} />
      ) : (events.data?.items.length ?? 0) === 0 ? (
        <EmptyState title="No audit events for the current filters." />
      ) : (
        <div className="section">
          <DataTable
            caption="Audit events"
            rowKey={(row) => row.id}
            emptyState={<EmptyState title="No audit events." />}
            rows={events.data?.items ?? []}
            columns={[
              { key: "occurred_at", header: "Occurred", sortValue: (row) => row.occurred_at, render: (row) => formatDateTime(row.occurred_at) },
              { key: "action", header: "Action", sortValue: (row) => row.action, render: (row) => <code className="num">{row.action}</code> },
              { key: "target_type", header: "Target", render: (row) => `${row.target_type}${row.target_id ? ` ${row.target_id.slice(0, 8)}…` : ""}` },
              { key: "actor", header: "Actor", render: (row) => (row.actor_user_id ? <code className="num">{row.actor_user_id.slice(0, 8)}…</code> : <span className="muted">system</span>) },
              { key: "reason", header: "Reason", render: (row) => row.reason ?? "—" },
              {
                key: "details",
                header: "Details",
                render: (row) =>
                  row.details ? (
                    <details>
                      <summary>View details</summary>
                      <pre className="small" style={{ whiteSpace: "pre-wrap" }}>
                        {JSON.stringify(row.details, null, 2)}
                      </pre>
                    </details>
                  ) : null,
              },
            ]}
          />
        </div>
      )}
    </div>
  );
}
