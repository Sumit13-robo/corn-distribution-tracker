import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ConfirmDialog } from "../../../components/common/ConfirmDialog";
import { EmptyState } from "../../../components/common/EmptyState";
import { StatusBadge } from "../../../components/common/StatusBadge";
import { useToast } from "../../../app/providers";
import { formatDateTime } from "../../../lib/format";
import { getCurrentUserId } from "../../../lib/session";
import {
  loadDrafts,
  queueAndSync,
  removeDraft,
  subscribeToDraftChanges,
  syncDrafts,
  type LocalDraft,
} from "./offlineQueue";

/**
 * Drafts & Sync (SCREEN_SPECS): every record here is local to this browser and
 * this signed-in user. Nothing is labelled submitted until the server accepts
 * it, and failed uploads stay queued with the server's message attached.
 */
export function DraftsSyncPage() {
  const userId = getCurrentUserId();
  const toast = useToast();
  const [drafts, setDrafts] = useState<LocalDraft[]>(() => (userId ? loadDrafts(userId) : []));
  const [online, setOnline] = useState(() => (typeof navigator === "undefined" ? true : navigator.onLine));
  const [busy, setBusy] = useState(false);
  const [activeDraftId, setActiveDraftId] = useState<string | null>(null);
  const [discardTarget, setDiscardTarget] = useState<LocalDraft | null>(null);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!userId) return;
    const refresh = () => setDrafts(loadDrafts(userId));
    refresh();
    return subscribeToDraftChanges(refresh);
  }, [userId]);

  useEffect(() => {
    const markOnline = () => setOnline(true);
    const markOffline = () => setOnline(false);
    window.addEventListener("online", markOnline);
    window.addEventListener("offline", markOffline);
    return () => {
      window.removeEventListener("online", markOnline);
      window.removeEventListener("offline", markOffline);
    };
  }, []);

  if (!userId) {
    return <EmptyState title="Sign in to view local drafts." description="Drafts are stored per signed-in account." />;
  }

  const scopeUserId = userId;
  const queued = drafts.filter((draft) => draft.state === "QUEUED");
  const unsynced = drafts.filter((draft) => draft.state !== "SUBMITTED");

  async function syncAll(): Promise<void> {
    if (!online) return;
    setBusy(true);
    setSyncMessage(null);
    try {
      const outcome = await syncDrafts(scopeUserId);
      setSyncMessage(
        outcome.syncedDraftIds.length > 0
          ? `${outcome.syncedDraftIds.length} draft(s) accepted by the server.`
          : "No queued drafts were waiting to sync.",
      );
      if (outcome.syncedDraftIds.length > 0) {
        toast.notify("success", `${outcome.syncedDraftIds.length} draft(s) submitted.`);
      }
    } finally {
      setBusy(false);
    }
  }

  async function retry(draft: LocalDraft): Promise<void> {
    if (!online || busy) return;
    setBusy(true);
    setActiveDraftId(draft.id);
    try {
      const result = await queueAndSync(scopeUserId, draft.id);
      if (result?.state === "SUBMITTED") {
        toast.notify("success", "Draft accepted by the server.");
      } else {
        toast.notify("warning", result?.lastError ?? "Still queued — try again when connectivity is stable.");
      }
    } finally {
      setActiveDraftId(null);
      setBusy(false);
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Drafts &amp; sync</h1>
          <p className="subtitle">
            Local-only records are stored in this browser for your account. Nothing here counts as submitted until the
            server accepts it.
          </p>
        </div>
        <div className="row">
          <Link className="btn ghost" to="/my-sites">
            Start an update
          </Link>
          <button
            type="button"
            className="btn"
            onClick={() => void syncAll()}
            disabled={!online || busy || queued.length === 0}
          >
            {busy ? "Syncing…" : `Sync ${queued.length > 0 ? `${queued.length} queued` : "queue"}`}
          </button>
        </div>
      </div>

      {!online ? (
        <div className="notice warning" role="status">
          This device appears offline. Queued drafts stay in this browser and retry automatically when the connection
          returns. Do not clear browser storage while drafts are waiting.
        </div>
      ) : null}

      {syncMessage ? (
        <p className="notice success" role="status">
          {syncMessage}
        </p>
      ) : null}

      <div className="section">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <div>
            <h2>On this device</h2>
            <p className="muted small">
              {drafts.length === 0
                ? "No local drafts."
                : `${unsynced.length} waiting · ${drafts.length - unsynced.length} submitted copy(ies)`}
            </p>
          </div>
          <StatusBadge status={online ? "ACTIVE" : "PAUSED"} label={online ? "Online" : "Offline"} />
        </div>

        {drafts.length === 0 ? (
          <EmptyState
            title="Nothing waiting on this device."
            description="Draft updates are saved here automatically while you work, even before you have a connection."
            action={
              <Link className="btn secondary" to="/my-sites">
                Choose a site
              </Link>
            }
          />
        ) : (
          <ul className="draft-list">
            {drafts.map((draft) => {
              const isSyncing = busy && activeDraftId === draft.id;
              return (
                <li key={draft.id} className="draft-row" data-testid="draft-row">
                  <div className="draft-main">
                    <div className="draft-title">
                      <strong>{draft.siteCode ?? draft.siteName ?? "Unassigned draft"}</strong>
                      <StatusBadge status={draft.state} />
                    </div>
                    <p className="draft-meta">
                      {draft.siteName && draft.siteName !== draft.siteCode ? `${draft.siteName} · ` : ""}
                      {draft.quantity ? `${draft.quantity} ${draft.unit}` : "quantity not entered"} ·{" "}
                      {draft.photoIds.length} photo(s)
                    </p>
                    <p className="draft-meta">
                      Saved {formatDateTime(draft.updatedAt)}
                      {draft.attempts > 0 ? ` · ${draft.attempts} failed sync attempt(s)` : ""}
                      {draft.submittedRecordId ? ` · server record ${draft.submittedRecordId.slice(0, 8)}…` : ""}
                    </p>
                    {draft.lastError ? (
                      <p className="notice danger small" role="status">
                        {draft.lastError}
                      </p>
                    ) : null}
                  </div>
                  <div className="draft-actions">
                    {draft.state === "SUBMITTED" ? (
                      <Link className="btn secondary small" to="/deliveries">
                        View submissions
                      </Link>
                    ) : (
                      <Link
                        className="btn secondary small"
                        to={
                          draft.assignmentId
                            ? `/deliver/new?assignment=${encodeURIComponent(draft.assignmentId)}`
                            : "/deliver/new"
                        }
                      >
                        Continue editing
                      </Link>
                    )}
                    {draft.state === "QUEUED" ? (
                      <button
                        type="button"
                        className="btn small"
                        onClick={() => void retry(draft)}
                        disabled={!online || busy}
                        aria-busy={isSyncing}
                      >
                        {isSyncing ? "Retrying…" : "Retry now"}
                      </button>
                    ) : null}
                    <button
                      type="button"
                      className="btn ghost small"
                      onClick={() => setDiscardTarget(draft)}
                      disabled={draft.state === "UPLOADING"}
                    >
                      {draft.state === "SUBMITTED" ? "Remove local copy" : "Discard…"}
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <p className="muted small">
        Photos in unsynced drafts are kept in this browser&rsquo;s private storage. Signing out keeps drafts for this
        account; clearing browser data removes them permanently.
      </p>

      <ConfirmDialog
        open={discardTarget !== null}
        title={discardTarget?.state === "SUBMITTED" ? "Remove this submitted copy?" : "Discard this local draft?"}
        message={
          discardTarget?.state === "SUBMITTED"
            ? "This only removes the local record. The server submission and its review history are not affected."
            : "The draft and its locally stored photos are deleted from this device. Server records are unaffected."
        }
        confirmLabel={discardTarget?.state === "SUBMITTED" ? "Remove copy" : "Discard draft"}
        destructive
        onConfirm={() => {
          if (!discardTarget) return;
          removeDraft(scopeUserId, discardTarget.id);
          setDiscardTarget(null);
          toast.notify("info", "Local record removed.");
        }}
        onCancel={() => setDiscardTarget(null)}
      />
    </div>
  );
}
