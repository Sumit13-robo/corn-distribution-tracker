import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../../lib/api-client";
import { queryKeys } from "../../../lib/query-client";
import { DataTable } from "../../../components/common/DataTable";
import { EmptyState } from "../../../components/common/EmptyState";
import { ErrorState } from "../../../components/common/ErrorState";
import { FormField } from "../../../components/common/FormField";
import { StatusBadge } from "../../../components/common/StatusBadge";
import { StatCard } from "../../../components/common/StatCard";
import { useToast } from "../../../app/providers";
import { formatKg, humanizeStatus } from "../../../lib/format";
import type { SiteOut } from "../../../types/domain";

interface SiteFormValues {
  name: string;
  site_code: string;
  address_text: string;
  region: string;
  latitude: string;
  longitude: string;
  geofence_radius_m: string;
  max_acceptable_accuracy_m: string;
  notes: string;
}

const EMPTY_FORM: SiteFormValues = {
  name: "",
  site_code: "",
  address_text: "",
  region: "",
  latitude: "",
  longitude: "",
  geofence_radius_m: "200",
  max_acceptable_accuracy_m: "",
  notes: "",
};

function toForm(site: SiteOut | null): SiteFormValues {
  if (!site) return { ...EMPTY_FORM };
  return {
    name: site.name,
    site_code: site.site_code,
    address_text: site.address_text ?? "",
    region: site.region ?? "",
    latitude: site.latitude,
    longitude: site.longitude,
    geofence_radius_m: String(site.geofence_radius_m),
    max_acceptable_accuracy_m: site.max_acceptable_accuracy_m === null ? "" : String(site.max_acceptable_accuracy_m),
    notes: site.notes ?? "",
  };
}

/**
 * Site management (SCREEN_SPECS "Sites"): coordinate entry with per-site
 * geofence/accuracy settings, deactivation, and a detail panel with site
 * progress plus its delivery history. Coordinate edits are audit-logged by the
 * server (site.updated audit actions), never silently rewritten here.
 */
export function SitesPage() {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingSite, setEditingSite] = useState<SiteOut | null>(null);
  const [form, setForm] = useState<SiteFormValues>({ ...EMPTY_FORM });
  const [formError, setFormError] = useState<string | null>(null);
  const [detailSite, setDetailSite] = useState<SiteOut | null>(null);
  const queryClient = useQueryClient();
  const toast = useToast();

  const sites = useQuery({
    queryKey: queryKeys.sites({}),
    queryFn: () => api.listSites({ active_only: false, limit: 100 }),
  });

  const progress = useQuery({
    queryKey: queryKeys.siteProgress(detailSite?.id ?? "none", null),
    queryFn: () => api.siteProgress(detailSite?.id as string),
    enabled: detailSite !== null,
  });

  const history = useQuery({
    queryKey: queryKeys.deliveries({ site_id: detailSite?.id ?? "", limit: 10, offset: 0 }),
    queryFn: () => api.listDeliveries({ site_id: detailSite?.id as string, limit: 10, offset: 0 }),
    enabled: detailSite !== null,
  });

  const save = useMutation({
    mutationFn: () => {
      if (editingSite) {
        const patch: Record<string, unknown> = {};
        const original = editingSite;
        if (form.name !== original.name) patch.name = form.name;
        if (form.site_code !== original.site_code) patch.site_code = form.site_code;
        if (form.latitude !== original.latitude) patch.latitude = form.latitude;
        if (form.longitude !== original.longitude) patch.longitude = form.longitude;
        if (form.address_text !== (original.address_text ?? "")) patch.address_text = form.address_text || null;
        if (form.region !== (original.region ?? "")) patch.region = form.region || null;
        if (form.geofence_radius_m !== String(original.geofence_radius_m)) patch.geofence_radius_m = Number(form.geofence_radius_m);
        if (form.max_acceptable_accuracy_m !== String(original.max_acceptable_accuracy_m ?? "")) {
          patch.max_acceptable_accuracy_m = form.max_acceptable_accuracy_m === "" ? null : Number(form.max_acceptable_accuracy_m);
        }
        if (form.notes !== (original.notes ?? "")) patch.notes = form.notes || null;
        return api.updateSite(original.id, patch);
      }
      return api.createSite({
        name: form.name,
        site_code: form.site_code,
        address_text: form.address_text || null,
        region: form.region || null,
        latitude: form.latitude,
        longitude: form.longitude,
        geofence_radius_m: Number(form.geofence_radius_m || 200),
        max_acceptable_accuracy_m: form.max_acceptable_accuracy_m === "" ? null : Number(form.max_acceptable_accuracy_m),
        notes: form.notes || null,
      });
    },
    onSuccess: () => {
      toast.notify("success", editingSite ? "Site updated (coordinate edits are audit-logged)." : "Site created.");
      setDialogOpen(false);
      setFormError(null);
      void queryClient.invalidateQueries({ queryKey: ["sites"] });
    },
  });

  const deactivate = useMutation({
    mutationFn: (site: SiteOut) => api.deactivateSite(site.id),
    onSuccess: () => {
      toast.notify("success", "Site deactivated.");
      void queryClient.invalidateQueries({ queryKey: ["sites"] });
    },
  });

  function openCreate(): void {
    setEditingSite(null);
    setForm({ ...EMPTY_FORM });
    setFormError(null);
    setDialogOpen(true);
  }

  function openEdit(site: SiteOut): void {
    setEditingSite(site);
    setForm(toForm(site));
    setFormError(null);
    setDialogOpen(true);
  }

  function submitForm(event: React.FormEvent) {
    event.preventDefault();
    const errors: string[] = [];
    if (!form.name.trim()) errors.push("Name is required.");
    if (!/^[A-Za-z0-9_-]+$/.test(form.site_code)) errors.push("Site code uses letters, digits, dash or underscore only.");
    const lat = Number(form.latitude);
    const lng = Number(form.longitude);
    if (Number.isNaN(lat) || lat < -90 || lat > 90) errors.push("Latitude must be between -90 and 90.");
    if (Number.isNaN(lng) || lng < -180 || lng > 180) errors.push("Longitude must be between -180 and 180.");
    const radius = Number(form.geofence_radius_m);
    if (Number.isNaN(radius) || radius <= 0 || radius > 100_000) errors.push("Geofence radius must be 1–100000 m.");
    if (form.max_acceptable_accuracy_m) {
      const accuracy = Number(form.max_acceptable_accuracy_m);
      if (Number.isNaN(accuracy) || accuracy <= 0 || accuracy > 5000) errors.push("Max accuracy must be 1–5000 m.");
    }
    if (errors.length > 0) {
      setFormError(errors.join(" "));
      return;
    }
    setFormError(null);
    save.mutate();
  }

  const columns: Array<{
    key: string;
    header: string;
    sortValue?: (row: SiteOut) => string | number;
    numeric?: boolean;
    render?: (row: SiteOut) => React.ReactNode;
  }> = [
    {
      key: "site_code",
      header: "Code",
      sortValue: (row) => row.site_code,
      render: (row) => (
        <button
          type="button"
          className="btn ghost"
          style={{ padding: 0 }}
          onClick={() => setDetailSite(row)}
          aria-label={`Open detail for site ${row.site_code}`}
        >
          {row.site_code}
        </button>
      ),
    },
    { key: "name", header: "Name", sortValue: (row) => row.name },
    {
      key: "region",
      header: "Region",
      sortValue: (row) => row.region ?? "",
      render: (row) => row.region ?? "—",
    },
    {
      key: "coords",
      header: "Coordinates",
      render: (row) => (
        <span className="num">
          {row.latitude}, {row.longitude}
        </span>
      ),
    },
    {
      key: "geofence",
      header: "Geofence (m)",
      numeric: true,
      sortValue: (row) => row.geofence_radius_m,
    },
    {
      key: "status",
      header: "Status",
      sortValue: (row) => (row.is_active ? "ACTIVE" : "OFF"),
      render: (row) => (row.is_active ? <StatusBadge status="ACTIVE" /> : <StatusBadge status="CLOSED" label="Inactive" />),
    },
    {
      key: "actions",
      header: "",
      render: (row) => (
        <span className="row">
          <button type="button" className="btn ghost small" onClick={() => openEdit(row)}>
            Edit
          </button>
          {row.is_active ? (
            <button type="button" className="btn ghost small" onClick={() => deactivate.mutate(row)}>
              Deactivate
            </button>
          ) : null}
        </span>
      ),
    },
  ];

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Sites</h1>
          <p className="subtitle">Coordinate entry, geofence settings and delivery history per site.</p>
        </div>
        <button type="button" className="btn" onClick={openCreate}>
          New site
        </button>
      </div>

      {sites.isError ? (
        <ErrorState error={sites.error} onRetry={() => void sites.refetch()} />
      ) : sites.isLoading ? (
        <div className="skeleton" style={{ height: 200 }} />
      ) : (sites.data?.items.length ?? 0) === 0 ? (
        <EmptyState title="No sites yet." description="Create the first distribution site to plan assignments." action={<button type="button" className="btn" onClick={openCreate}>New site</button>} />
      ) : (
        <div className="section">
          <DataTable
            caption="Distribution sites"
            rowKey={(row) => row.id}
            emptyState={<EmptyState title="No sites yet." />}
            rows={sites.data?.items ?? []}
            columns={columns}
          />
        </div>
      )}

      {detailSite ? (
        <div className="section" data-testid="site-detail">
          <div className="row">
            <h2 className="grow">
              {detailSite.site_code} — {detailSite.name}
            </h2>
            <button type="button" className="btn ghost" onClick={() => setDetailSite(null)}>
              Close
            </button>
          </div>
          <p className="small muted">
            {detailSite.address_text ?? "No address recorded"} · geofence {detailSite.geofence_radius_m} m ·
            {detailSite.max_acceptable_accuracy_m ? ` max accuracy ${detailSite.max_acceptable_accuracy_m} m` : " org default accuracy"}
          </p>
          {progress.isError ? (
            <ErrorState error={progress.error} onRetry={() => void progress.refetch()} />
          ) : progress.isLoading ? (
            <div className="skeleton" style={{ height: 80 }} />
          ) : progress.data ? (
            <div className="metric-row">
              <StatCard label="Target" value={formatKg(progress.data.target_kg)} unit="kg" />
              <StatCard label="Approved" value={formatKg(progress.data.approved_kg)} unit="kg" />
              <StatCard label="Pending" value={formatKg(progress.data.pending_kg)} unit="kg" />
              <StatCard label="Rejected" value={formatKg(progress.data.rejected_kg)} unit="kg" />
              <StatCard
                label="Evidence"
                value={humanizeStatus(progress.data.evidence_status)}
                definition={progress.data.has_flagged_evidence ? "This site has flagged submissions requiring attention." : undefined}
              />
            </div>
          ) : null}
          <h3 style={{ marginTop: "var(--space-3)" }}>Delivery history</h3>
          {history.isError ? (
            <ErrorState error={history.error} onRetry={() => void history.refetch()} />
          ) : history.isLoading ? (
            <div className="skeleton" style={{ height: 80 }} />
          ) : (history.data?.items.length ?? 0) === 0 ? (
            <EmptyState title="No deliveries recorded for this site yet." />
          ) : (
            <ul className="stack small" style={{ margin: 0, paddingLeft: 0, listStyle: "none" }}>
              {(history.data?.items ?? []).map((record) => (
                <li key={record.id} className="row">
                  <StatusBadge status={record.status} />
                  <span className="num">{formatKg(record.quantity_kg)} kg</span>
                  <code className="num">{record.id.slice(0, 8)}…</code>
                  <span className="muted">distributor {record.distributor_name}</span>
                  <span className="grow" />
                  <span className="muted small">{new Date(record.submitted_at).toISOString()}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}

      {dialogOpen ? (
        <div className="dialog-backdrop" role="dialog" aria-modal="true" aria-labelledby="site-dialog-title" onClick={() => setDialogOpen(false)}>
          <div className="dialog" onClick={(event) => event.stopPropagation()} style={{ width: "min(560px, 94vw)" }}>
            <h2 id="site-dialog-title">{editingSite ? `Edit site ${editingSite.site_code}` : "Create site"}</h2>
            {save.error ? <ErrorState error={save.error} /> : null}
            {formError ? <ErrorState error={new Error(formError)} title="Check the form." /> : null}
            <form className="form-grid" onSubmit={submitForm}>
              <div className="row">
                <FormField id="site-name" label="Name" required className="grow">
                  {(ids) => <input id="site-name" value={form.name} aria-describedby={ids.describedBy} onChange={(e) => setForm({ ...form, name: e.target.value })} />}
                </FormField>
                <FormField id="site-code" label="Site code" required helper="Letters, digits, dash or underscore. Duplicates are rejected." className="grow">
                  {(ids) => (
                    <input
                      id="site-code"
                      value={form.site_code}
                      aria-describedby={ids.describedBy}
                      onChange={(e) => setForm({ ...form, site_code: e.target.value })}
                      disabled={editingSite !== null}
                    />
                  )}
                </FormField>
              </div>
              <div className="row">
                <FormField id="site-lat" label="Latitude" required helper="-90 to 90 decimal degrees." className="grow">
                  {(ids) => (
                    <input
                      id="site-lat"
                      type="text"
                      inputMode="decimal"
                      className="num"
                      value={form.latitude}
                      aria-describedby={ids.describedBy}
                      onChange={(e) => setForm({ ...form, latitude: e.target.value })}
                    />
                  )}
                </FormField>
                <FormField id="site-lng" label="Longitude" required helper="-180 to 180 decimal degrees." className="grow">
                  {(ids) => (
                    <input
                      id="site-lng"
                      type="text"
                      inputMode="decimal"
                      className="num"
                      value={form.longitude}
                      aria-describedby={ids.describedBy}
                      onChange={(e) => setForm({ ...form, longitude: e.target.value })}
                    />
                  )}
                </FormField>
              </div>
              <div className="row">
                <FormField id="site-radius" label="Geofence radius (m)" required className="grow">
                  {(ids) => <input id="site-radius" type="number" min={1} max={100000} value={form.geofence_radius_m} aria-describedby={ids.describedBy} onChange={(e) => setForm({ ...form, geofence_radius_m: e.target.value })} />}
                </FormField>
                <FormField id="site-accuracy" label="Max GPS accuracy (m)" helper="Blank: use the organization default." className="grow">
                  {(ids) => <input id="site-accuracy" type="number" min={1} max={5000} value={form.max_acceptable_accuracy_m} aria-describedby={ids.describedBy} onChange={(e) => setForm({ ...form, max_acceptable_accuracy_m: e.target.value })} />}
                </FormField>
              </div>
              <FormField id="site-address" label="Address" helper="Optional human-readable location description.">
                {(ids) => <input id="site-address" value={form.address_text} aria-describedby={ids.describedBy} onChange={(e) => setForm({ ...form, address_text: e.target.value })} />}
              </FormField>
              <div className="row">
                <FormField id="site-region" label="Region" className="grow">
                  {(ids) => <input id="site-region" value={form.region} aria-describedby={ids.describedBy} onChange={(e) => setForm({ ...form, region: e.target.value })} />}
                </FormField>
              </div>
              <FormField id="site-notes" label="Admin notes" helper="Internal only; distributors never see these.">
                {(ids) => <textarea id="site-notes" rows={2} value={form.notes} aria-describedby={ids.describedBy} onChange={(e) => setForm({ ...form, notes: e.target.value })} />}
              </FormField>
              <div className="dialog-actions">
                <button type="button" className="btn secondary" onClick={() => setDialogOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn" disabled={save.isPending}>
                  {save.isPending ? "Saving…" : editingSite ? "Save changes" : "Create site"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}
