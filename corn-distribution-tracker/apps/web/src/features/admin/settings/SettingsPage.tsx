import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../../lib/api-client";
import { FormField } from "../../../components/common/FormField";
import { ErrorState } from "../../../components/common/ErrorState";
import { useToast } from "../../../app/providers";
import { formatDateTime } from "../../../lib/format";
import type { SettingsOut } from "../../../types/domain";

const DISPLAY_UNITS = ["KG", "QUINTAL", "TONNE", "BAG"] as const;

/**
 * Organization settings (SCREEN_SPECS): timezone, display unit with explicit
 * kg-per-bag, geolocation thresholds and geofence defaults. Every change is
 * audit-logged by the server; the form only edits allowlisted fields.
 */
export function SettingsPage() {
  const queryClient = useQueryClient();
  const toast = useToast();

  const settings = useQuery({ queryKey: ["settings"], queryFn: () => api.getSettings() });

  const [form, setForm] = useState<SettingsOut | null>(null);
  const [kgPerBagEnabled, setKgPerBagEnabled] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (settings.data && form === null) {
      setForm({ ...settings.data });
      setKgPerBagEnabled(settings.data.kg_per_bag !== null);
    }
  }, [settings.data, form]);

  const save = useMutation({
    mutationFn: () => {
      const payload: Record<string, unknown> = {};
      if (!form) return Promise.reject(new Error("Form not ready"));
      if (form.timezone !== settings.data?.timezone) payload.timezone = form.timezone;
      if (form.default_display_unit !== settings.data?.default_display_unit) {
        payload.default_display_unit = form.default_display_unit;
      }
      if (kgPerBagEnabled) {
        if (form.kg_per_bag !== settings.data?.kg_per_bag) payload.kg_per_bag = form.kg_per_bag;
      } else if (settings.data?.kg_per_bag !== null) {
        payload.kg_per_bag = null;
      }
      if (form.default_geofence_radius_m !== settings.data?.default_geofence_radius_m) {
        payload.default_geofence_radius_m = form.default_geofence_radius_m;
      }
      if (form.max_acceptable_gps_accuracy_m !== settings.data?.max_acceptable_gps_accuracy_m) {
        payload.max_acceptable_gps_accuracy_m = form.max_acceptable_gps_accuracy_m;
      }
      if (form.max_location_age_seconds !== settings.data?.max_location_age_seconds) {
        payload.max_location_age_seconds = form.max_location_age_seconds;
      }
      if (form.max_capture_time_drift_seconds !== settings.data?.max_capture_time_drift_seconds) {
        payload.max_capture_time_drift_seconds = form.max_capture_time_drift_seconds;
      }
      return api.patchSettings(payload);
    },
    onSuccess: () => {
      toast.notify("success", "Settings saved (audit event recorded).");
      void queryClient.invalidateQueries({ queryKey: ["settings"] });
      setError(null);
    },
  });

  if (settings.isError) {
    return <ErrorState error={settings.error} onRetry={() => void settings.refetch()} />;
  }
  if (settings.isLoading || !form) {
    return <div className="skeleton" style={{ height: 300 }} />;
  }

  function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!form) return;
    if (kgPerBagEnabled && (!form.kg_per_bag || Number(form.kg_per_bag) <= 0)) {
      setError("BAG display requires a positive kg-per-bag factor.");
      return;
    }
    setError(null);
    save.mutate();
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Organization settings</h1>
          <p className="subtitle">
            Allowlisted fields only; every change is audit-logged {form.updated_at ? `· last updated ${formatDateTime(form.updated_at)}` : ""}
          </p>
        </div>
        <Link className="btn ghost" to="/audit">
          Audit trail →
        </Link>
      </div>

      {save.error ? <ErrorState error={save.error} /> : null}
      {error ? <ErrorState error={new Error(error)} title="Check the form." /> : null}

      <form className="form-grid section" onSubmit={submit}>
        <div className="row">
          <FormField id="settings-timezone" label="Timezone" className="grow" helper="IANA timezone name (e.g. UTC).">
            {(ids) => (
              <input
                id="settings-timezone"
                value={form.timezone}
                aria-describedby={ids.describedBy}
                onChange={(event) => setForm({ ...form, timezone: event.target.value })}
              />
            )}
          </FormField>
          <FormField id="settings-unit" label="Default display unit" className="grow">
            {(ids) => (
              <select
                id="settings-unit"
                aria-describedby={ids.describedBy}
                value={form.default_display_unit}
                onChange={(event) => {
                  const unit = event.target.value;
                  setForm({ ...form, default_display_unit: unit });
                  if (unit === "BAG") setKgPerBagEnabled(true);
                }}
              >
                {DISPLAY_UNITS.map((unit) => (
                  <option key={unit} value={unit}>
                    {unit}
                  </option>
                ))}
              </select>
            )}
          </FormField>
        </div>

        <FormField
          id="settings-kgperbag"
          label="Kilograms per bag"
          helper="Needed only when BAG display is used. Canonical quantities stay in kilograms; this factor is only for display."
        >
          {(ids) => (
            <div className="kg-bag-control">
              <label className="checkbox-control">
                <input
                  type="checkbox"
                  checked={kgPerBagEnabled}
                  onChange={(event) => {
                    const enabled = event.target.checked;
                    setKgPerBagEnabled(enabled);
                    if (!enabled && form.default_display_unit === "BAG") {
                      setForm({ ...form, default_display_unit: "KG" });
                    }
                  }}
                />
                <span>Use a bag conversion factor</span>
              </label>
              <input
                id="settings-kgperbag"
                type="text"
                inputMode="decimal"
                className="num"
                value={form.kg_per_bag ?? ""}
                aria-describedby={ids.describedBy}
                disabled={!kgPerBagEnabled}
                onChange={(event) => setForm({ ...form, kg_per_bag: event.target.value })}
                placeholder="e.g. 50"
              />
            </div>
          )}
        </FormField>

        <div className="row">
          <FormField id="settings-geofence" label="Default geofence radius (m)" className="grow" helper="Site-created radius when not overridden (1–100000).">
            {(ids) => (
              <input
                id="settings-geofence"
                type="number"
                min={1}
                max={100000}
                className="num"
                value={form.default_geofence_radius_m}
                aria-describedby={ids.describedBy}
                onChange={(event) => setForm({ ...form, default_geofence_radius_m: Number(event.target.value) })}
              />
            )}
          </FormField>
          <FormField id="settings-accuracy" label="Max acceptable GPS accuracy (m)" className="grow" helper="Fixes less accurate than this are flagged (1–5000).">
            {(ids) => (
              <input
                id="settings-accuracy"
                type="number"
                min={1}
                max={5000}
                className="num"
                value={form.max_acceptable_gps_accuracy_m}
                aria-describedby={ids.describedBy}
                onChange={(event) => setForm({ ...form, max_acceptable_gps_accuracy_m: Number(event.target.value) })}
              />
            )}
          </FormField>
        </div>

        <div className="row">
          <FormField id="settings-age" label="Max location age (s)" className="grow" helper="Older fixes flag the record (1–86400).">
            {(ids) => (
              <input
                id="settings-age"
                type="number"
                min={1}
                max={86400}
                className="num"
                value={form.max_location_age_seconds}
                aria-describedby={ids.describedBy}
                onChange={(event) => setForm({ ...form, max_location_age_seconds: Number(event.target.value) })}
              />
            )}
          </FormField>
          <FormField id="settings-drift" label="Max capture-time drift (s)" className="grow" helper="EXIF vs. submission time drift tolerance (1–86400).">
            {(ids) => (
              <input
                id="settings-drift"
                type="number"
                min={1}
                max={86400}
                className="num"
                value={form.max_capture_time_drift_seconds}
                aria-describedby={ids.describedBy}
                onChange={(event) => setForm({ ...form, max_capture_time_drift_seconds: Number(event.target.value) })}
              />
            )}
          </FormField>
        </div>

        <div className="form-actions">
          <button type="submit" className="btn" disabled={save.isPending}>
            {save.isPending ? "Saving…" : "Save settings"}
          </button>
        </div>
        <p className="small muted">
          Storage and retention are deployment-level settings; they are not editable here by design.
        </p>
      </form>
    </div>
  );
}
