import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../../lib/api-client";
import { queryKeys } from "../../../lib/query-client";
import { DataTable } from "../../../components/common/DataTable";
import { EmptyState } from "../../../components/common/EmptyState";
import { ErrorState } from "../../../components/common/ErrorState";
import { FormField } from "../../../components/common/FormField";
import { StatusBadge } from "../../../components/common/StatusBadge";
import { useToast } from "../../../app/providers";
import { formatDateTime, formatKg } from "../../../lib/format";
import type { AssignmentOut, CampaignOut, DistributorDetailOut, SiteOut } from "../../../types/domain";

const CAMPAIGN_STATUSES = ["DRAFT", "ACTIVE", "PAUSED", "CLOSED"] as const;

/**
 * Campaigns and targets (SCREEN_SPECS): campaign create/edit plus the
 * assignment planner. Proposed targets are compared against available stock
 * honestly — warnings here are advisory. Assignment creation validates fields
 * and duplicates but does not reserve stock; allocations and delivery
 * submissions are where ledger balances are enforced.
 */
export function CampaignsPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [selectedCampaignId, setSelectedCampaignId] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<CampaignOut | null>(null);
  const [form, setForm] = useState({ name: "", reference_code: "", starts_at: "", ends_at: "", status: "DRAFT", timezone: "UTC", notes: "", sitesText: "" });
  const [formError, setFormError] = useState<string | null>(null);
  const [newSiteName, setNewSiteName] = useState("");
  const [siteFormError, setSiteFormError] = useState<string | null>(null);
  const [locationSite, setLocationSite] = useState<SiteOut | null>(null);
  const [locationLat, setLocationLat] = useState("");
  const [locationLng, setLocationLng] = useState("");
  const [locationError, setLocationError] = useState<string | null>(null);
  const [assignmentSite, setAssignmentSite] = useState("");
  const [assignmentDistributor, setAssignmentDistributor] = useState("");
  const [assignmentQuantity, setAssignmentQuantity] = useState("");
  const [assignmentUnit, setAssignmentUnit] = useState("KG");
  const [assignmentDue, setAssignmentDue] = useState("");
  const queryClient = useQueryClient();
  const toast = useToast();

  const campaigns = useQuery({
    queryKey: queryKeys.campaigns(statusFilter || undefined),
    queryFn: () => api.listCampaigns(statusFilter || undefined),
  });

  const sites = useQuery({
    queryKey: queryKeys.sites({
      active_only: true,
      campaign_id: selectedCampaignId ?? undefined,
    }),
    queryFn: () =>
      api.listSites({
        active_only: true,
        campaign_id: selectedCampaignId ?? undefined,
        limit: 100,
      }),
    enabled: selectedCampaignId !== null,
  });
  const distributors = useQuery({ queryKey: queryKeys.distributors(""), queryFn: () => api.listDistributors() });
  const summary = useQuery({ queryKey: queryKeys.inventorySummary(), queryFn: () => api.inventorySummary() });

  const assignments = useQuery({
    queryKey: queryKeys.assignments(selectedCampaignId),
    queryFn: () => api.listAllAssignments(selectedCampaignId ?? undefined),
    enabled: selectedCampaignId !== null,
  });

  const selectedCampaign = useMemo(
    () => (campaigns.data?.items ?? []).find((campaign) => campaign.id === selectedCampaignId) ?? null,
    [campaigns.data, selectedCampaignId],
  );

  const saveCampaign = useMutation({
    mutationFn: () => {
      if (editing) {
        return api.updateCampaign(editing.id, {
          name: form.name,
          status: form.status as (typeof CAMPAIGN_STATUSES)[number],
          starts_at: form.starts_at || null,
          ends_at: form.ends_at || null,
          timezone: form.timezone,
          notes: form.notes || null,
        });
      }
      return api.createCampaign({
        name: form.name,
        reference_code: form.reference_code,
        starts_at: form.starts_at || null,
        ends_at: form.ends_at || null,
        status: form.status as (typeof CAMPAIGN_STATUSES)[number],
        timezone: form.timezone,
        notes: form.notes || null,
        sites: parseSiteNames(form.sitesText),
      });
    },
    onSuccess: (saved) => {
      toast.notify("success", "Campaign saved.");
      setDialogOpen(false);
      setFormError(null);
      // Clear the status filter so the saved campaign and its site panel
      // remain visible even if its status no longer matches the filter.
      setStatusFilter("");
      setSelectedCampaignId(saved.id);
      setAssignmentSite("");
      setNewSiteName("");
      setSiteFormError(null);
      void queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      void queryClient.invalidateQueries({ queryKey: ["sites"] });
    },
  });

  const addSite = useMutation({
    mutationFn: () =>
      api.createSite({
        name: newSiteName.trim(),
        campaign_id: selectedCampaignId,
      }),
    onSuccess: (site) => {
      toast.notify("success", "Site added.");
      setNewSiteName("");
      setSiteFormError(null);
      setAssignmentSite(site.id);
      void queryClient.invalidateQueries({ queryKey: ["sites"] });
      void queryClient.invalidateQueries({ queryKey: ["analytics-overview"] });
    },
  });

  const saveLocation = useMutation({
    mutationFn: () => {
      if (!locationSite) throw new Error("Choose a site first.");
      return api.updateSite(locationSite.id, {
        latitude: locationLat.trim(),
        longitude: locationLng.trim(),
      });
    },
    onSuccess: (site) => {
      toast.notify("success", "Site location saved.");
      setLocationSite(null);
      setLocationError(null);
      void queryClient.invalidateQueries({ queryKey: ["sites"] });
      void queryClient.invalidateQueries({ queryKey: queryKeys.site(site.id) });
      void queryClient.invalidateQueries({ queryKey: ["map-sites"] });
      void queryClient.invalidateQueries({ queryKey: ["analytics-overview"] });
    },
  });

  const createAssignment = useMutation({
    mutationFn: () =>
      api.createAssignment({
        site_id: assignmentSite,
        campaign_id: selectedCampaignId,
        distributor_user_id: assignmentDistributor,
        target_quantity: assignmentQuantity,
        unit: assignmentUnit,
        due_at: assignmentDue ? new Date(assignmentDue).toISOString() : null,
      }),
    onSuccess: () => {
      toast.notify("success", "Assignment created.");
      setAssignmentQuantity("");
      void queryClient.invalidateQueries({ queryKey: ["assignments"] });
      void queryClient.invalidateQueries({ queryKey: ["analytics-overview"] });
    },
  });

  function openCreate() {
    saveCampaign.reset();
    setEditing(null);
    setForm({ name: "", reference_code: "", starts_at: "", ends_at: "", status: "DRAFT", timezone: "UTC", notes: "", sitesText: "" });
    setFormError(null);
    setDialogOpen(true);
  }

  function openEdit(campaign: CampaignOut) {
    saveCampaign.reset();
    setEditing(campaign);
    setForm({
      name: campaign.name,
      reference_code: campaign.reference_code,
      starts_at: campaign.starts_at ? campaign.starts_at.slice(0, 10) : "",
      ends_at: campaign.ends_at ? campaign.ends_at.slice(0, 10) : "",
      status: campaign.status,
      timezone: campaign.timezone,
      notes: campaign.notes ?? "",
      sitesText: "",
    });
    setFormError(null);
    setDialogOpen(true);
  }

  function selectCampaign(campaignId: string | null) {
    if (!addSite.isPending) addSite.reset();
    if (!createAssignment.isPending) createAssignment.reset();
    setSelectedCampaignId(campaignId);
    setAssignmentSite("");
    setNewSiteName("");
    setSiteFormError(null);
  }

  function openLocation(site: SiteOut) {
    saveLocation.reset();
    setLocationSite(site);
    setLocationLat(site.latitude ?? "");
    setLocationLng(site.longitude ?? "");
    setLocationError(null);
  }

  function closeLocation() {
    saveLocation.reset();
    setLocationSite(null);
    setLocationLat("");
    setLocationLng("");
    setLocationError(null);
  }

  function submitSite(event: React.FormEvent) {
    event.preventDefault();
    if (!selectedCampaignId) return;
    const name = newSiteName.trim();
    if (!name) {
      setSiteFormError("Site name is required.");
      return;
    }
    const duplicate = (sites.data?.items ?? []).some(
      (site) => site.name.toLocaleLowerCase() === name.toLocaleLowerCase(),
    );
    if (duplicate) {
      setSiteFormError("A site with this name already exists in this campaign.");
      return;
    }
    setSiteFormError(null);
    addSite.mutate();
  }

  function submitLocation(event: React.FormEvent) {
    event.preventDefault();
    if (!locationSite) return;
    if (!locationLat.trim() || !locationLng.trim()) {
      setLocationError("Enter both latitude and longitude, or leave both blank.");
      return;
    }
    const latitude = Number(locationLat);
    const longitude = Number(locationLng);
    if (!Number.isFinite(latitude) || latitude < -90 || latitude > 90) {
      setLocationError("Latitude must be a number between -90 and 90.");
      return;
    }
    if (!Number.isFinite(longitude) || longitude < -180 || longitude > 180) {
      setLocationError("Longitude must be a number between -180 and 180.");
      return;
    }
    setLocationError(null);
    saveLocation.mutate();
  }

  function submitCampaign(event: React.FormEvent) {
    event.preventDefault();
    if (!form.name.trim()) {
      setFormError("Campaign name is required.");
      return;
    }
    if (!editing && !/^[A-Za-z0-9_-]+$/.test(form.reference_code)) {
      setFormError("Reference code uses letters, digits, dash or underscore only.");
      return;
    }
    setFormError(null);
    saveCampaign.mutate();
  }

  function submitAssignment(event: React.FormEvent) {
    event.preventDefault();
    if (!assignmentSite || !assignmentDistributor) {
      toast.notify("warning", "Choose a site and a distributor first.");
      return;
    }
    if (!Number.isFinite(Number(assignmentQuantity)) || Number(assignmentQuantity) <= 0) {
      toast.notify("warning", "Enter a target quantity greater than 0.");
      return;
    }
    createAssignment.mutate();
  }

  /* Honest advisory warning: proposed target vs. metadata from scope data. */
  const stockWarning = useMemo(() => {
    if (!createAssignment.isPending && Number(assignmentQuantity) > 0 && assignmentDistributor) {
      const distributor = distributors.data?.items.find((item) => item.id === assignmentDistributor);
      const quantity = Number(assignmentQuantity);
      const available = distributor ? Number(distributor.available_kg) : 0;
      const central = (summary.data?.accounts ?? [])
        .filter((account) => account.account_type === "CENTRAL")
        .reduce((acc, account) => acc + Number(account.available_kg), 0);
      const messages: string[] = [];
      if (!editing && available < quantity) messages.push(`Distributor currently holds only ${available} kg available.`);
      if (central < quantity) messages.push(`Central stock shows only ${central} kg available.`);
      return messages.length > 0 ? messages.join(" ") : null;
    }
    return null;
  }, [assignmentDistributor, assignmentQuantity, distributors.data, summary.data, createAssignment.isPending, editing]);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Campaigns and targets</h1>
          <p className="subtitle">Campaign lifecycle plus distributor/site assignment planning in canonical kg.</p>
        </div>
        <button type="button" className="btn" onClick={openCreate}>
          New campaign
        </button>
      </div>

      <div className="section">
        <div className="row">
          <FormField id="campaign-status-filter" label="Status filter" className="grow" helper="Server-side filter.">
            {(ids) => (
              <select id="campaign-status-filter" aria-describedby={ids.describedBy} value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
                <option value="">All statuses</option>
                {CAMPAIGN_STATUSES.map((status) => (
                  <option key={status} value={status}>
                    {humanStatus(status)}
                  </option>
                ))}
              </select>
            )}
          </FormField>
        </div>
        {campaigns.isError ? (
          <ErrorState error={campaigns.error} onRetry={() => void campaigns.refetch()} />
        ) : campaigns.isLoading ? (
          <div className="skeleton" style={{ height: 120 }} />
        ) : (campaigns.data?.items.length ?? 0) === 0 ? (
          <EmptyState title="No campaigns yet." action={<button type="button" className="btn" onClick={openCreate}>New campaign</button>} />
        ) : (
          <DataTable
            caption="Campaigns"
            rowKey={(row) => row.id}
            emptyState={<EmptyState title="No campaigns yet." />}
            rows={campaigns.data?.items ?? []}
            columns={[
              {
                key: "name",
                header: "Name",
                sortValue: (row) => row.name,
                render: (row) => (
                  <button
                    type="button"
                    className="btn ghost"
                    style={{
                      padding: 0,
                      fontWeight: selectedCampaignId === row.id ? "var(--weight-strong)" : undefined,
                    }}
                    onClick={() => selectCampaign(row.id === selectedCampaignId ? null : row.id)}
                  >
                    {row.name}
                  </button>
                ),
              },
              { key: "reference_code", header: "Reference", sortValue: (row) => row.reference_code },
              { key: "status", header: "Status", sortValue: (row) => row.status, render: (row) => <StatusBadge status={row.status} /> },
              { key: "starts_at", header: "Starts", sortValue: (row) => row.starts_at ?? "", render: (row) => formatDateTime(row.starts_at) },
              { key: "ends_at", header: "Ends", sortValue: (row) => row.ends_at ?? "", render: (row) => formatDateTime(row.ends_at) },
              { key: "timezone", header: "Timezone" },
              {
                key: "edit",
                header: "",
                render: (row) => (
                  <button type="button" className="btn ghost small" onClick={() => openEdit(row)}>
                    Edit
                  </button>
                ),
              },
            ]}
          />
        )}
      </div>

      {selectedCampaign ? (
        <>
          <div className="section" data-testid="campaign-sites">
            <div className="row">
              <div className="grow">
                <h2>Sites for {selectedCampaign.name}</h2>
                <p className="small muted">
                  Add place names only. A site location is optional and can be added later; it is used for map context
                  only and never blocks approval.
                </p>
              </div>
              <button type="button" className="btn ghost" onClick={() => selectCampaign(null)}>
                Close
              </button>
            </div>

            {sites.isError ? (
              <ErrorState error={sites.error} onRetry={() => void sites.refetch()} />
            ) : sites.isLoading ? (
              <div className="skeleton" style={{ height: 80 }} />
            ) : (sites.data?.items.length ?? 0) === 0 ? (
              <EmptyState
                title="No sites in this campaign yet."
                description="Add a place name below, then plan a distributor assignment."
              />
            ) : (
              <ul className="stack" style={{ margin: 0, paddingLeft: 0, listStyle: "none" }}>
                {(sites.data?.items ?? []).map((site) => (
                  <li
                    key={site.id}
                    className="row"
                    style={{ padding: "var(--space-2) 0", borderBottom: "1px solid var(--color-border)" }}
                  >
                    <div className="grow">
                      <strong>{site.name}</strong>
                      <div className="small muted">
                        {site.latitude !== null && site.longitude !== null
                          ? `Site location ${site.latitude}, ${site.longitude}`
                          : "Site location not set. A captured device fix is still stored with submissions."}
                      </div>
                    </div>
                    <button type="button" className="btn secondary small" onClick={() => openLocation(site)}>
                      {site.latitude !== null && site.longitude !== null ? "Edit location" : "Add location (optional)"}
                    </button>
                  </li>
                ))}
              </ul>
            )}

            <form className="row" onSubmit={submitSite} style={{ alignItems: "flex-end", marginTop: "var(--space-3)" }}>
              <FormField
                id="new-site-name"
                label="Add a site"
                required
                className="grow"
                helper="Place name only; no coordinates required."
              >
                {(ids) => (
                  <input
                    id="new-site-name"
                    value={newSiteName}
                    aria-describedby={ids.describedBy}
                    onChange={(event) => setNewSiteName(event.target.value)}
                  />
                )}
              </FormField>
              <button type="submit" className="btn" disabled={addSite.isPending || !selectedCampaignId}>
                {addSite.isPending ? "Adding…" : "Add site"}
              </button>
            </form>
            {siteFormError ? <ErrorState error={new Error(siteFormError)} title="Check the site name." /> : null}
            {addSite.error ? <ErrorState error={addSite.error} /> : null}
          </div>

          <div className="section" data-testid="assignment-planner">
            <div className="row">
              <h2 className="grow">Assignments for {selectedCampaign.name}</h2>
            </div>
          {assignments.isError ? (
            <ErrorState error={assignments.error} onRetry={() => void assignments.refetch()} />
          ) : assignments.isLoading ? (
            <div className="skeleton" style={{ height: 80 }} />
          ) : (assignments.data?.items.length ?? 0) === 0 ? (
            <EmptyState title="No assignments for this campaign yet." description="Use the planner below to add distributor targets." />
          ) : (
            <DataTable
              caption="Campaign assignments"
              rowKey={(row) => row.id}
              emptyState={null}
              rows={assignments.data?.items ?? []}
              columns={[
                {
                  key: "site",
                  header: "Site",
                  render: (row) =>
                    (sites.data?.items ?? []).find((site) => site.id === row.site_id)?.name ??
                    row.site_id.slice(0, 8) + "…",
                },
                {
                  key: "distributor",
                  header: "Distributor",
                  render: (row) => (distributors.data?.items ?? []).find((item) => item.id === row.distributor_user_id)?.display_name ?? row.distributor_user_id.slice(0, 8) + "…",
                },
                { key: "target", header: "Target (kg)", numeric: true, sortValue: (row: AssignmentOut) => Number(row.target_quantity_kg), render: (row) => formatKg(row.target_quantity_kg) },
                { key: "due", header: "Due", render: (row) => formatDateTime(row.due_at) },
                { key: "status", header: "Status", render: (row) => <StatusBadge status={row.status} /> },
              ]}
            />
          )}

          <h3 style={{ marginTop: "var(--space-3)" }}>Plan a new assignment</h3>
          {createAssignment.error ? <ErrorState error={createAssignment.error} /> : null}
          {stockWarning ? (
            <div className="notice warning" role="status">
              Stock warning: {stockWarning} This is advisory; assignments do not reserve stock. Allocate stock separately in Inventory.
            </div>
          ) : null}
          {assignmentUnit !== "KG" ? (
            <p className="small muted" role="status">
              Estimated canonical target: {formatKg(previewTargetKg(assignmentQuantity, assignmentUnit))} kg (final conversions are computed server-side).
            </p>
          ) : null}
          <form className="form-grid" onSubmit={submitAssignment} style={{ maxWidth: 520 }}>
            <div className="row">
              <FormField
                id="assign-site"
                label="Site"
                required
                className="grow"
                helper={
                  (sites.data?.items.length ?? 0) === 0
                    ? "Add a site in this campaign first."
                    : undefined
                }
              >
                {(ids) => (
                  <select
                    id="assign-site"
                    aria-describedby={ids.describedBy}
                    value={assignmentSite}
                    onChange={(e) => setAssignmentSite(e.target.value)}
                    disabled={sites.isLoading}
                  >
                    <option value="">Choose site…</option>
                    {(sites.data?.items ?? []).map((site: SiteOut) => (
                      <option key={site.id} value={site.id}>
                        {site.name}
                      </option>
                    ))}
                  </select>
                )}
              </FormField>
              <FormField id="assign-distributor" label="Distributor" required className="grow">
                {(ids) => (
                  <select id="assign-distributor" aria-describedby={ids.describedBy} value={assignmentDistributor} onChange={(e) => setAssignmentDistributor(e.target.value)}>
                    <option value="">Choose distributor…</option>
                    {(distributors.data?.items ?? []).map((item: DistributorDetailOut) => (
                      <option key={item.id} value={item.id}>
                        {item.display_name} ({formatKg(item.available_kg)} kg available)
                      </option>
                    ))}
                  </select>
                )}
              </FormField>
            </div>
            <div className="row">
              <FormField id="assign-quantity" label="Target quantity" required className="grow" helper="Positive decimal; canonical kilograms.">
                {(ids) => (
                  <input
                    id="assign-quantity"
                    type="text"
                    inputMode="decimal"
                    className="num"
                    value={assignmentQuantity}
                    aria-describedby={ids.describedBy}
                    onChange={(e) => setAssignmentQuantity(e.target.value)}
                  />
                )}
              </FormField>
              <FormField id="assign-unit" label="Unit" className="grow">
                {(ids) => (
                  <select id="assign-unit" aria-describedby={ids.describedBy} value={assignmentUnit} onChange={(e) => setAssignmentUnit(e.target.value)}>
                    <option value="KG">kg</option>
                    <option value="QUINTAL">quintal (100 kg)</option>
                    <option value="TONNE">tonne (1000 kg)</option>
                  </select>
                )}
              </FormField>
              <FormField id="assign-due" label="Due date" className="grow">
                {(ids) => (
                  <input
                    id="assign-due"
                    type="date"
                    value={assignmentDue}
                    aria-describedby={ids.describedBy}
                    onChange={(e) => setAssignmentDue(e.target.value)}
                  />
                )}
              </FormField>
            </div>
            <div className="form-actions">
              <button type="submit" className="btn" disabled={createAssignment.isPending || !selectedCampaignId}>
                {createAssignment.isPending ? "Saving…" : "Create assignment"}
              </button>
            </div>
          </form>
          </div>
        </>
      ) : null}

      {dialogOpen ? (
        <div className="dialog-backdrop" role="dialog" aria-modal="true" aria-labelledby="campaign-dialog-title" onClick={() => setDialogOpen(false)}>
          <div className="dialog" onClick={(e) => e.stopPropagation()} style={{ width: "min(560px, 94vw)" }}>
            <h2 id="campaign-dialog-title">{editing ? `Edit ${editing.name}` : "Create campaign"}</h2>
            {saveCampaign.error ? <ErrorState error={saveCampaign.error} /> : null}
            {formError ? <ErrorState error={new Error(formError)} title="Check the form." /> : null}
            <form className="form-grid" onSubmit={submitCampaign}>
              <FormField id="campaign-name" label="Name" required>
                {(ids) => <input id="campaign-name" value={form.name} aria-describedby={ids.describedBy} onChange={(e) => setForm({ ...form, name: e.target.value })} />}
              </FormField>
              <FormField
                id="campaign-ref"
                label="Reference code"
                required
                helper="Letters, digits, dash or underscore. Immutable after creation."
              >
                {(ids) => <input id="campaign-ref" value={form.reference_code} aria-describedby={ids.describedBy} onChange={(e) => setForm({ ...form, reference_code: e.target.value })} disabled={editing !== null} />}
              </FormField>
              <div className="row">
                <FormField id="campaign-start" label="Starts at" className="grow">
                  {(ids) => (
                    <input id="campaign-start" type="date" value={form.starts_at} aria-describedby={ids.describedBy} onChange={(e) => setForm({ ...form, starts_at: e.target.value })} />
                  )}
                </FormField>
                <FormField id="campaign-end" label="Ends at" className="grow">
                  {(ids) => (
                    <input id="campaign-end" type="date" value={form.ends_at} aria-describedby={ids.describedBy} onChange={(e) => setForm({ ...form, ends_at: e.target.value })} />
                  )}
                </FormField>
              </div>
              <div className="row">
                <FormField id="campaign-status" label="Status" className="grow">
                  {(ids) => (
                    <select id="campaign-status" aria-describedby={ids.describedBy} value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
                      {CAMPAIGN_STATUSES.map((status) => (
                        <option key={status} value={status}>
                          {humanStatus(status)}
                        </option>
                      ))}
                    </select>
                  )}
                </FormField>
                <FormField id="campaign-tz" label="Timezone" className="grow" helper="IANA timezone, e.g. UTC.">
                  {(ids) => <input id="campaign-tz" value={form.timezone} aria-describedby={ids.describedBy} onChange={(e) => setForm({ ...form, timezone: e.target.value })} />}
                </FormField>
              </div>
              <FormField id="campaign-notes" label="Notes" helper="Optional context for reviewers.">
                {(ids) => <textarea id="campaign-notes" rows={2} value={form.notes} aria-describedby={ids.describedBy} onChange={(e) => setForm({ ...form, notes: e.target.value })} />}
              </FormField>
              {!editing ? (
                <FormField
                  id="campaign-sites"
                  label="Sites"
                  helper="Optional. One place name per line. Coordinates are not required and can be added later."
                >
                  {(ids) => (
                    <textarea
                      id="campaign-sites"
                      rows={3}
                      value={form.sitesText}
                      placeholder={"For example:\nGandhi Chowk\nRukadi Market"}
                      aria-describedby={ids.describedBy}
                      onChange={(e) => setForm({ ...form, sitesText: e.target.value })}
                    />
                  )}
                </FormField>
              ) : (
                <p className="small muted">Sites are managed in the campaign panel after saving.</p>
              )}
              <div className="dialog-actions">
                <button type="button" className="btn secondary" onClick={() => setDialogOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn" disabled={saveCampaign.isPending}>
                  {saveCampaign.isPending ? "Saving…" : "Save campaign"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      {locationSite ? (
        <div
          className="dialog-backdrop"
          role="dialog"
          aria-modal="true"
          aria-labelledby="site-location-dialog-title"
          onClick={closeLocation}
        >
          <div className="dialog" onClick={(event) => event.stopPropagation()} style={{ width: "min(520px, 94vw)" }}>
            <h2 id="site-location-dialog-title">Site location — {locationSite.name}</h2>
            <p className="small muted">
              Optional map reference for this site. Existing submissions and captured locations are not changed.
            </p>
            {saveLocation.error ? <ErrorState error={saveLocation.error} /> : null}
            {locationError ? <ErrorState error={new Error(locationError)} title="Check the location." /> : null}
            <form className="form-grid" onSubmit={submitLocation}>
              <div className="row">
                <FormField id="site-latitude" label="Latitude" required className="grow" helper="Decimal degrees, -90 to 90.">
                  {(ids) => (
                    <input
                      id="site-latitude"
                      className="num"
                      inputMode="decimal"
                      value={locationLat}
                      aria-describedby={ids.describedBy}
                      onChange={(event) => setLocationLat(event.target.value)}
                    />
                  )}
                </FormField>
                <FormField id="site-longitude" label="Longitude" required className="grow" helper="Decimal degrees, -180 to 180.">
                  {(ids) => (
                    <input
                      id="site-longitude"
                      className="num"
                      inputMode="decimal"
                      value={locationLng}
                      aria-describedby={ids.describedBy}
                      onChange={(event) => setLocationLng(event.target.value)}
                    />
                  )}
                </FormField>
              </div>
              <div className="dialog-actions">
                <button type="button" className="btn secondary" onClick={closeLocation}>
                  Cancel
                </button>
                <button type="submit" className="btn" disabled={saveLocation.isPending}>
                  {saveLocation.isPending ? "Saving…" : "Save location"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}

/** Optional site names are entered one per line during campaign setup. */
function parseSiteNames(text: string): string[] {
  const names: string[] = [];
  const seen = new Set<string>();
  for (const raw of text.split(/\r?\n/)) {
    const name = raw.trim();
    const key = name.toLocaleLowerCase();
    if (name && !seen.has(key)) {
      names.push(name);
      seen.add(key);
    }
  }
  return names;
}

/** Advisory preview only; the server converts and validates the canonical kg. */
function previewTargetKg(quantityText: string, unit: string): string {
  const quantity = Number(quantityText);
  if (!Number.isFinite(quantity) || quantity <= 0) return "0";
  const factor = unit === "QUINTAL" ? 100 : unit === "TONNE" ? 1000 : 1;
  return String(quantity * factor);
}

function humanStatus(status: string): string {
  switch (status) {
    case "DRAFT":
      return "Draft (not started)";
    case "ACTIVE":
      return "Active";
    case "PAUSED":
      return "Paused";
    default:
      return "Closed";
  }
}
