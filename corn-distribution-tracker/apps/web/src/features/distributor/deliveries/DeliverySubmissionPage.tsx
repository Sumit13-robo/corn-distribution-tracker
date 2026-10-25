import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../../lib/api-client";
import { queryKeys } from "../../../lib/query-client";
import { FormField } from "../../../components/common/FormField";
import { ErrorState } from "../../../components/common/ErrorState";
import { EmptyState } from "../../../components/common/EmptyState";
import { StatusBadge } from "../../../components/common/StatusBadge";
import { ConfirmDialog } from "../../../components/common/ConfirmDialog";
import { useToast } from "../../../app/providers";
import { PhotoCapturePanel } from "../evidence/PhotoCapturePanel";
import { useDeviceLocation } from "../evidence/useDeviceLocation";
import {
  createDraft,
  getDraft,
  listDraftPhotos,
  loadDrafts,
  queueAndSync,
  removeDraft,
  subscribeToDraftChanges,
  updateDraft,
  type DraftPhoto,
  type DraftUnit,
} from "../offline/offlineQueue";
import type { LocalDraft } from "../offline/offlineQueue";
import { formatDateTime, formatKg, humanizeStatus } from "../../../lib/format";
import { getCurrentUserId } from "../../../lib/session";

type UnitOption = "KG" | "QUINTAL" | "TONNE" | "BAG";

const UNIT_FACTORS: Record<UnitOption, number | null> = { KG: 1, QUINTAL: 100, TONNE: 1000, BAG: null };

/**
 * Delivery update workflow (SCREEN_SPECS "Delivery update"):
 *  - site/assignment context is pinned server-side,
 *  - photos attach to the local draft evidence store (nothing uploaded yet),
 *  - the device fix is captured with its accuracy and clock metadata,
 *  - the draft is auto-saved with a persistent idempotency key,
 *  - submit moves LOCAL_DRAFT → QUEUED → UPLOADING → SUBMITTED with truthful
 *    states; offline drafts stay QUEUED and retry manually or on reconnection.
 */
export function DeliverySubmissionPage() {
  const [params] = useSearchParams();
  const toast = useToast();
  const userId = getCurrentUserId();
  const requestedAssignmentId = params.get("assignment");

  const assignments = useQuery({ queryKey: queryKeys.myAssignments(), queryFn: () => api.myAssignments() });
  const settings = useQuery({ queryKey: ["settings"], queryFn: () => api.getSettings() });

  /* Local draft state (single active draft on this page). */
  const [draftId, setDraftId] = useState<string | null>(null);
  const [draft, setDraft] = useState<LocalDraft | null>(null);
  const [photos, setPhotos] = useState<DraftPhoto[]>([]);
  const [quantityInput, setQuantityInput] = useState("");
  const [unit, setUnit] = useState<DraftUnit>("KG");
  const [notesInput, setNotesInput] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [discardTarget, setDiscardTarget] = useState<LocalDraft | null>(null);
  const createdForAssignmentRef = useRef<string | null>(null);

  const location = useDeviceLocation();

  const assignment = useMemo(
    () => (assignments.data ?? []).find((item) => item.assignment_id === requestedAssignmentId) ?? null,
    [assignments.data, requestedAssignmentId],
  );

  const refreshDrafts = useCallback(() => {
    if (!userId) return;
    const current = draftId ? getDraft(userId, draftId) : null;
    setDraft(current);
  }, [userId, draftId]);

  /* Draft creation: resume the unsent draft for this assignment (same
   * idempotency key), or create exactly one per assignment visit. */
  useEffect(() => {
    if (!userId || !assignment || draftId !== null || createdForAssignmentRef.current === assignment.assignment_id) return;
    createdForAssignmentRef.current = assignment.assignment_id;
    const resumable = loadDrafts(userId).find(
      (item) =>
        item.assignmentId === assignment.assignment_id &&
        (item.state === "LOCAL_DRAFT" || item.state === "QUEUED"),
    );
    const next =
      resumable ??
      createDraft(userId, {
        assignmentId: assignment.assignment_id,
        siteId: assignment.site?.id ?? null,
        siteCode: assignment.site?.site_code ?? null,
        siteName: assignment.site?.name ?? null,
        unit: "KG",
      });
    setDraftId(next.id);
    setDraft(next);
    setQuantityInput(next.quantity);
    setNotesInput(next.notes ?? "");
    setUnit(next.unit);
  }, [userId, assignment, draftId]);

  /* Keep the on-screen state honest while the queue works in the background. */
  useEffect(() => {
    if (!userId) return;
    return subscribeToDraftChanges(() => {
      refreshDrafts();
    });
  }, [userId, refreshDrafts]);

  /* A captured fix belongs to the draft immediately, not only at submit:
   * otherwise the UI says "no fix captured" and a reload would lose it. */
  useEffect(() => {
    if (location.status !== "CAPTURED" || !location.coordinates || !userId || !draftId) return;
    const coordinates = location.coordinates;
    const updated = updateDraft(userId, draftId, {
      location: {
        latitude: coordinates.latitude,
        longitude: coordinates.longitude,
        accuracy_m: coordinates.accuracy_m,
        timestamp: coordinates.timestamp,
        device_time: coordinates.device_time,
        client_created_at: new Date().toISOString(),
      },
    });
    if (updated) setDraft(updated);
  }, [location.status, location.coordinates, userId, draftId]);

  /* Load photo metadata when the draft id materializes. */
  useEffect(() => {
    if (!draftId) {
      setPhotos([]);
      return;
    }
    void listDraftPhotos(draftId).then(setPhotos);
  }, [draftId, photos.length]);

  useEffect(() => {
    if (!draft) return;
    setQuantityInput(draft.quantity);
    setNotesInput(draft.notes ?? "");
    if (draft.unit) setUnit(draft.unit);
    refreshDrafts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft?.id]);

  /* Auto-save on field change (kept cheap: local writes only). */
  function persistField(patch: { quantity?: string; unit?: DraftUnit; notes?: string | null }) {
    if (!userId || !draftId) return;
    const updated = updateDraft(userId, draftId, patch);
    if (updated) setDraft(updated);
  }

  function persistLocation() {
    if (!userId || !draftId || !location.coordinates) return;
    const updated = updateDraft(userId, draftId, {
      location: {
        latitude: location.coordinates.latitude,
        longitude: location.coordinates.longitude,
        accuracy_m: location.coordinates.accuracy_m,
        timestamp: location.coordinates.timestamp,
        device_time: location.coordinates.device_time,
        client_created_at: new Date().toISOString(),
      },
    });
    if (updated) setDraft(updated);
  }

  if (assignments.isError) {
    return <ErrorState error={assignments.error} onRetry={() => void assignments.refetch()} />;
  }

  if ((assignments.data?.length ?? 0) === 0) {
    return (
      <EmptyState
        title="No assignments to report against."
        description="Assignments appear here once a coordinator plans targets for your account."
        action={
          <Link className="btn secondary" to="/my-sites">
            Back to my sites
          </Link>
        }
      />
    );
  }

  if (!assignment) {
    return (
      <div>
        <div className="page-header">
          <h1>New delivery update</h1>
          <p className="subtitle">Choose which assignment you are reporting against.</p>
        </div>
        <div className="stack">
          {(assignments.data ?? []).map((item) => (
            <Link
              key={item.assignment_id}
              className="section"
              style={{ color: "inherit", textDecoration: "none" }}
              to={`/deliver/new?assignment=${item.assignment_id}`}
            >
              <div className="row">
                <strong>{item.site?.site_code ?? "Site"}</strong>
                <span>{item.site?.name}</span>
                <span className="grow" />
                <span className="muted small">
                  remaining {formatKg(item.remaining_target_kg)} kg of {formatKg(item.target_kg)} kg
                </span>
              </div>
            </Link>
          ))}
        </div>
      </div>
    );
  }

  const kgPerBag = settings.data?.kg_per_bag ? Number(settings.data.kg_per_bag) : null;
  const bagFactorMissing = unit === "BAG" && kgPerBag === null;
  const quantityNumber = Number(quantityInput);
  const quantityValid = quantityInput !== "" && Number.isFinite(quantityNumber) && quantityNumber > 0;
  const previewKg = quantityValid ? quantityNumber * (unit === "BAG" ? (kgPerBag ?? 0) : (UNIT_FACTORS[unit as UnitOption] ?? 1)) : null;

  /* Prefer the fresh in-memory fix, then the fix persisted with this draft.
   * A resumed draft must not look uncaptured just because the hook restarted. */
  const savedLocation =
    draft?.location?.latitude != null && draft.location.longitude != null ? draft.location : null;
  const capturedLocation = location.coordinates ?? savedLocation;

  /* Honest evidence warnings (the server revalidates on sync). */
  const warnings: string[] = [];
  if (photos.length === 0) warnings.push("No photos attached yet — the server requires at least one evidence image.");
  if (bagFactorMissing) warnings.push("BAG unit requires kg-per-bag configured; submit in kg or ask an admin to configure it.");
  const existingDrafts = loadDrafts(userId ?? "").filter((item) => item.id !== draftId);

  async function handleSubmit(): Promise<void> {
    if (!userId || !draftId) return;
    if (!quantityValid) {
      setSubmitError("Enter a quantity greater than 0.");
      return;
    }
    if (bagFactorMissing) {
      setSubmitError("BAG unit requires kg-per-bag configured; submit in kg instead.");
      return;
    }
    if (photos.length === 0) {
      setSubmitError("At least one evidence photo is required before submitting.");
      return;
    }
    setSubmitError(null);
    setSubmitting(true);
    persistLocation();
    try {
      await queueAndSync(userId, draftId);
      const outcome = getDraft(userId, draftId);
      if (outcome?.state === "SUBMITTED" && outcome.submittedRecordId) {
        toast.notify("success", "Submitted — record accepted by the server.");
        setDraftId(null);
        setDraft(null);
        setQuantityInput("");
        setNotesInput("");
        setPhotos([]);
      } else if (outcome?.state === "QUEUED") {
        toast.notify("warning", outcome.lastError ?? "Draft parked in the queue until connectivity returns.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>New delivery update</h1>
          <p className="subtitle">
            {draft?.siteCode ? `${draft.siteCode} — ${draft.siteName}` : "Site"} · remaining target{" "}
            {formatKg(assignment.remaining_target_kg)} kg
          </p>
        </div>
        <div className="row">
          {draft ? (
            <span data-testid="draft-state">
              <StatusBadge status={draft.state} />
            </span>
          ) : null}
          <Link className="btn ghost" to="/deliveries">
            My submissions
          </Link>
        </div>
      </div>

      {!navigator.onLine ? (
        <div className="notice warning" role="status">
          You appear offline. Fill everything now — the draft stays in this browser as QUEUED and syncs automatically
          when connectivity returns. Nothing is marked submitted until the server accepts it.
        </div>
      ) : null}

      <PhotoCapturePanel
        userId={userId ?? ""}
        draftId={draftId}
        photos={photos}
        offlineMode={!navigator.onLine}
        onChange={(next) => setPhotos(next)}
      />

      <div className="section">
        <h2>Location</h2>
        <p className="muted small">
          Captures your device fix once (accuracy + device clock included). It is supporting metadata, not proof
          against spoofing. A delivery can be approved from any recorded location.
        </p>
        <div className="row">
          <button type="button" className="btn secondary" onClick={location.request} disabled={location.status === "LOADING"}>
            {location.status === "LOADING" ? "Locating…" : capturedLocation ? "Re-capture location" : "Capture location"}
          </button>
          {capturedLocation ? (
            <span className="small num">
              {capturedLocation.latitude}, {capturedLocation.longitude} · ±{capturedLocation.accuracy_m ?? "?"} m
            </span>
          ) : (
            <span className="small muted">No fix captured yet.</span>
          )}
        </div>
        {location.message ? <p className="notice warning" role="status">{location.message}</p> : null}
      </div>

      <div className="section">
        <h2>Quantity and notes</h2>
        <div className="row">
          <FormField
            id="delivery-quantity"
            label="Quantity"
            required
            className="grow"
            error={!quantityValid && quantityInput !== "" ? "Enter a positive number." : null}
          >
            {(ids) => (
              <input
                id="delivery-quantity"
                type="text"
                inputMode="decimal"
                className="num"
                value={quantityInput}
                aria-describedby={ids.describedBy}
                onChange={(event) => {
                  setQuantityInput(event.target.value);
                  persistField({ quantity: event.target.value });
                }}
              />
            )}
          </FormField>
          <FormField id="delivery-unit" label="Unit" className="grow">
            {(ids) => (
              <select
                id="delivery-unit"
                aria-describedby={ids.describedBy}
                value={unit}
                onChange={(event) => {
                  setUnit(event.target.value);
                  persistField({ unit: event.target.value });
                }}
              >
                {(Object.keys(UNIT_FACTORS) as UnitOption[]).map((option) => (
                  <option key={option} value={option}>
                    {option === "KG" ? "kg" : option === "QUINTAL" ? "quintal (100 kg)" : option === "TONNE" ? "tonne (1000 kg)" : `bag (${kgPerBag ?? "?"} kg)`}
                  </option>
                ))}
              </select>
            )}
          </FormField>
        </div>
        {previewKg !== null ? (
          <p className="small muted" role="status">
            Canonical estimate: {formatKg(previewKg ? String(previewKg) : "0")} kg — the server converts and revalidates.
          </p>
        ) : null}
        <FormField id="delivery-notes" label="Notes" helper="Optional context for the reviewer.">
          {(ids) => (
            <textarea
              id="delivery-notes"
              rows={2}
              value={notesInput}
              aria-describedby={ids.describedBy}
              onChange={(event) => {
                setNotesInput(event.target.value);
                persistField({ notes: event.target.value });
              }}
            />
          )}
        </FormField>
      </div>

      <div className="section" data-testid="final-review">
        <h2>Review and submit</h2>
        {warnings.length > 0 ? (
          <ul className="notice warning" style={{ margin: "0 0 var(--space-3)" }}>
            {warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        ) : null}
        {submitError ? <ErrorState error={new Error(submitError)} title="Cannot submit yet." /> : null}
        <dl className="dl-grid">
          <dt>Assignment</dt>
          <dd>
            <code className="num">{assignment.assignment_id}</code>
          </dd>
          <dt>Site</dt>
          <dd>{assignment.site ? `${assignment.site.site_code} — ${assignment.site.name}` : "—"}</dd>
          <dt>Draft saved</dt>
          <dd>{draft ? formatDateTime(draft.updatedAt) : "—"}</dd>
        </dl>
        <div className="form-actions" style={{ marginTop: "var(--space-3)" }}>
          <button
            type="button"
            className="btn"
            onClick={() => void handleSubmit()}
            disabled={submitting || !quantityValid || photos.length === 0 || bagFactorMissing}
            data-testid="submit-delivery"
          >
            {submitting ? "Queuing submission…" : "Submit delivery"}
          </button>
          <span className="small muted">Duplicate clicks are blocked until the attempt resolves.</span>
        </div>
        {draft && draft.state !== "LOCAL_DRAFT" ? (
          <p className="small muted" style={{ marginTop: "var(--space-2)" }}>
            Draft state: <StatusBadge status={draft.state} />
            {draft.lastError ? ` · last error: ${draft.lastError}` : ""}
          </p>
        ) : null}
      </div>

      <div className="section">
        <h2>Drafts on this device ({existingDrafts.length})</h2>
        {existingDrafts.length === 0 ? (
          <p className="muted small">No other local drafts. Local drafts are unmistakably labelled and never fetched from the server.</p>
        ) : (
          <ul className="stack small" style={{ margin: 0, paddingLeft: 0, listStyle: "none" }}>
            {existingDrafts.map((item) => (
              <li key={item.id} className="row">
                <StatusBadge status={item.state} />
                <span>
                  {item.siteCode ?? "site"} — {item.quantity || "—"} {item.unit}
                </span>
                <span className="muted">{humanizeStatus(item.state)} · saved {formatDateTime(item.updatedAt)}</span>
                {item.lastError ? <span className="muted"> · {item.lastError}</span> : null}
                <span className="grow" />
                {item.state === "QUEUED" ? (
                  <button
                    type="button"
                    className="btn ghost small"
                    onClick={() => {
                      if (!userId) return;
                      void queueAndSync(userId, item.id).then(refreshDrafts);
                    }}
                  >
                    Retry now
                  </button>
                ) : null}
                <button type="button" className="btn ghost small" onClick={() => setDiscardTarget(item)}>
                  Discard…
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <ConfirmDialog
        open={discardTarget !== null}
        title="Discard this local draft?"
        message="The draft and its locally-stored photos are deleted from this device. Server records are unaffected."
        confirmLabel="Discard draft"
        destructive
        onConfirm={() => {
          if (!userId || !discardTarget) return;
          removeDraft(userId, discardTarget.id);
          if (discardTarget.id === draftId) {
            setDraftId(null);
            setDraft(null);
          }
          setDiscardTarget(null);
          refreshDrafts();
          toast.notify("info", "Draft discarded.");
        }}
        onCancel={() => setDiscardTarget(null)}
      />
    </div>
  );
}
