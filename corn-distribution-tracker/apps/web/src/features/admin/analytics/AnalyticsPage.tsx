import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, downloadBlob, fetchDistributionsCsv } from "../../../lib/api-client";
import { queryKeys } from "../../../lib/query-client";
import { DataTable } from "../../../components/common/DataTable";
import { EmptyState } from "../../../components/common/EmptyState";
import { ErrorState } from "../../../components/common/ErrorState";
import { FormField } from "../../../components/common/FormField";
import { StatusBadge } from "../../../components/common/StatusBadge";
import { StatCard } from "../../../components/common/StatCard";
import { useToast } from "../../../app/providers";
import { cx, formatDateTime, formatKg, formatNumber } from "../../../lib/format";
import type { SitePerfOut } from "../../../types/domain";

/**
 * Analytics and exports (SCREEN_SPECS): filters on top with a visible selected
 * scope, clear unit definitions, accessible bar/table rendering of the same
 * data, and a CSV export for the identical filter set. Charts are CSS bars
 * scaled from the real returned values only — nothing invented.
 */
export function AnalyticsPage() {
  const [campaignId, setCampaignId] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const toast = useToast();

  const filters = useMemo(
    () => ({
      campaign_id: campaignId || undefined,
      from: fromDate ? new Date(`${fromDate}T00:00:00Z`).toISOString() : undefined,
      to: toDate ? new Date(`${toDate}T23:59:59Z`).toISOString() : undefined,
    }),
    [campaignId, fromDate, toDate],
  );

  const campaigns = useQuery({ queryKey: queryKeys.campaigns(undefined), queryFn: () => api.listCampaigns(undefined) });
  const overview = useQuery({
    queryKey: queryKeys.overview(campaignId || null),
    queryFn: () => api.overview(fromDate || toDate ? filters : { campaign_id: campaignId || undefined }),
  });
  const distributors = useQuery({
    queryKey: queryKeys.distributorPerformance(campaignId || null),
    queryFn: () => api.distributorPerformance(filters),
  });
  const sites = useQuery({
    queryKey: queryKeys.sitePerformance(campaignId || null),
    queryFn: () => api.sitePerformance(filters),
  });

  const [exporting, setExporting] = useState(false);

  async function exportCsv() {
    setExporting(true);
    try {
      const blob = await fetchDistributionsCsv({
        campaign_id: campaignId || undefined,
        from: filters.from,
        to: filters.to,
      });
      downloadBlob(blob, "distributions.csv");
      // The server audits every export action.
      toast.notify("success", "Export downloaded (server audit event recorded).");
    } catch (error) {
      toast.notify("danger", error instanceof Error ? error.message : "Export failed.");
    } finally {
      setExporting(false);
    }
  }

  const distributorMax = Math.max(1, ...(distributors.data ?? []).map((row) => Number(row.approved_kg)));
  const siteMax = Math.max(1, ...(sites.data ?? []).map((row) => Number(row.approved_kg)));

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Analytics and exports</h1>
          <p className="subtitle">
            <span className={cx("num")}>{campaignNameOrScope(campaignId, campaigns.data?.items ?? [])}</span> · all
            quantities in canonical kilograms (kg)
          </p>
        </div>
        <button type="button" className="btn" onClick={() => void exportCsv()} disabled={exporting}>
          {exporting ? "Preparing…" : "Export distributions CSV"}
        </button>
      </div>

      <div className="section">
        <div className="row">
          <FormField id="analytics-campaign" label="Campaign" className="grow">
            {(ids) => (
              <select
                id="analytics-campaign"
                aria-describedby={ids.describedBy}
                value={campaignId}
                onChange={(event) => setCampaignId(event.target.value)}
              >
                <option value="">All campaigns (scope)</option>
                {(campaigns.data?.items ?? []).map((campaign) => (
                  <option key={campaign.id} value={campaign.id}>
                    {campaign.name}
                  </option>
                ))}
              </select>
            )}
          </FormField>
          <FormField id="analytics-from" label="From (UTC date)" className="grow">
            {(ids) => (
              <input
                id="analytics-from"
                type="date"
                value={fromDate}
                aria-describedby={ids.describedBy}
                onChange={(event) => setFromDate(event.target.value)}
              />
            )}
          </FormField>
          <FormField id="analytics-to" label="To (UTC date)" className="grow">
            {(ids) => (
              <input
                id="analytics-to"
                type="date"
                value={toDate}
                aria-describedby={ids.describedBy}
                onChange={(event) => setToDate(event.target.value)}
              />
            )}
          </FormField>
        </div>
      </div>

      {overview.isError ? (
        <ErrorState error={overview.error} onRetry={() => void overview.refetch()} />
      ) : overview.isLoading ? (
        <div className="skeleton" style={{ height: 160 }} />
      ) : !overview.data ? (
        <EmptyState title="No analytics for this scope yet." />
      ) : (
        <div className="section">
          <h2>Scope metrics</h2>
          <div className="metric-row">
            <StatCard label="Approved delivered" value={formatKg(overview.data.approved_delivered_kg)} unit="kg" />
            <StatCard label="Submitted pending" value={formatKg(overview.data.submitted_pending_kg)} unit="kg" />
            <StatCard label="Rejected" value={formatKg(overview.data.rejected_kg)} unit="kg" />
            <StatCard label="Remaining target" value={formatKg(overview.data.remaining_target_kg)} unit="kg" />
            <StatCard
              label="Evidence completeness"
              value={overview.data.evidence_completeness.ratio === null ? "—" : `${Math.round(overview.data.evidence_completeness.ratio * 100)}%`}
              definition={`${overview.data.evidence_completeness.approved_with_evidence} of ${overview.data.evidence_completeness.approved_total} approved records carry evidence.`}
            />
          </div>
        </div>
      )}

      <div className="section">
        <h2>Distributor breakdown</h2>
        <p className="muted small">{distributors.data?.[0]?.denominator_note ?? "Approved kilograms over total target."}</p>
        {distributors.isError ? (
          <ErrorState error={distributors.error} onRetry={() => void distributors.refetch()} />
        ) : distributors.isLoading ? (
          <div className="skeleton" style={{ height: 120 }} />
        ) : (distributors.data?.length ?? 0) === 0 ? (
          <EmptyState title="No distributor data in this scope." />
        ) : (
          <>
            <div className="stack" role="img" aria-label="Distributor approved kilograms bar chart" data-testid="distributor-bars">
              {(distributors.data ?? []).map((row) => (
                <div key={row.distributor_user_id} className="row" style={{ gap: "var(--space-2)" }}>
                  <span style={{ minWidth: 180 }}>{row.display_name}</span>
                  <div
                    style={{
                      height: 14,
                      background: "var(--color-brand-600)",
                      borderRadius: 7,
                      width: `${(Number(row.approved_kg) / distributorMax) * 70}%`,
                      minWidth: 4,
                    }}
                    aria-hidden="true"
                  />
                  <span className="num small">{formatKg(row.approved_kg)} kg</span>
                </div>
              ))}
            </div>
            <DataTable
              caption="Distributor performance table"
              rowKey={(row) => row.distributor_user_id}
              emptyState={<EmptyState title="No distributor data." />}
              rows={distributors.data ?? []}
              columns={[
                { key: "display_name", header: "Name", sortValue: (row) => row.display_name },
                { key: "target", header: "Target (kg)", numeric: true, sortValue: (row) => Number(row.target_kg), render: (row) => formatKg(row.target_kg) },
                { key: "approved", header: "Approved (kg)", numeric: true, sortValue: (row) => Number(row.approved_kg), render: (row) => formatKg(row.approved_kg) },
                { key: "pending", header: "Pending (kg)", numeric: true, sortValue: (row) => Number(row.pending_kg), render: (row) => formatKg(row.pending_kg) },
                { key: "rejected", header: "Rejected (kg)", numeric: true, sortValue: (row) => Number(row.rejected_kg), render: (row) => formatKg(row.rejected_kg) },
                { key: "remaining", header: "Remaining (kg)", numeric: true, sortValue: (row) => Number(row.remaining_target_kg), render: (row) => formatKg(row.remaining_target_kg) },
                { key: "flagged", header: "Flagged", numeric: true, sortValue: (row) => row.flagged_submissions, render: (row) => formatNumber(row.flagged_submissions) },
                { key: "exceptions", header: "Exception approvals", numeric: true, sortValue: (row) => row.approved_with_exception, render: (row) => formatNumber(row.approved_with_exception) },
              ]}
            />
          </>
        )}
      </div>

      <div className="section">
        <h2>Site breakdown</h2>
        {sites.isError ? (
          <ErrorState error={sites.error} onRetry={() => void sites.refetch()} />
        ) : sites.isLoading ? (
          <div className="skeleton" style={{ height: 120 }} />
        ) : (sites.data?.length ?? 0) === 0 ? (
          <EmptyState title="No site data in this scope." />
        ) : (
          <>
            <div className="stack" role="img" aria-label="Site approved kilograms bar chart">
              {(sites.data ?? []).map((row) => (
                <div key={row.site_id} className="row" style={{ gap: "var(--space-2)" }}>
                  <span style={{ minWidth: 180 }}>{row.site_code}</span>
                  <div
                    style={{
                      height: 14,
                      background: "var(--color-brand-700)",
                      borderRadius: 7,
                      width: `${(Number(row.approved_kg) / siteMax) * 70}%`,
                      minWidth: 4,
                    }}
                    aria-hidden="true"
                  />
                  <span className="num small">{formatKg(row.approved_kg)} kg</span>
                </div>
              ))}
            </div>
            <DataTable
              caption="Site performance table"
              rowKey={(row) => row.site_id}
              emptyState={<EmptyState title="No site data." />}
              rows={sites.data ?? []}
              columns={[
                { key: "site_code", header: "Code", sortValue: (row) => row.site_code },
                { key: "site_name", header: "Name", sortValue: (row) => row.site_name },
                {
                  key: "status",
                  header: "Evidence",
                  render: (row: SitePerfOut) => <StatusBadge status={row.evidence_status} />,
                },
                { key: "target", header: "Target (kg)", numeric: true, sortValue: (row) => Number(row.target_kg), render: (row) => formatKg(row.target_kg) },
                { key: "approved", header: "Approved (kg)", numeric: true, sortValue: (row) => Number(row.approved_kg), render: (row) => formatKg(row.approved_kg) },
                { key: "remaining", header: "Remaining (kg)", numeric: true, sortValue: (row) => Number(row.remaining_target_kg), render: (row) => formatKg(row.remaining_target_kg) },
                { key: "last_visit", header: "Last visit", sortValue: (row) => row.last_visit_at ?? "", render: (row) => formatDateTime(row.last_visit_at) },
              ]}
            />
          </>
        )}
      </div>
    </div>
  );
}

function campaignNameOrScope(campaignId: string, items: Array<{ id: string; name: string }>): string {
  if (!campaignId) return "Scope: whole organization";
  return `Scope: campaign ${items.find((item) => item.id === campaignId)?.name ?? ""}`;
}
