import { useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { logout, useSession } from "../../lib/session";
import { ConfirmDialog } from "../common/ConfirmDialog";
import { hasUnsyncedDrafts, removeAllDrafts } from "../../features/distributor/offline/offlineQueue";
import { useToast } from "../../app/providers";

const PATH_LABELS: Record<string, string> = {
  "/": "Overview",
  "/map": "Distribution map",
  "/campaigns": "Campaigns",
  "/distributors": "Distributors",
  "/sites": "Sites",
  "/inventory": "Inventory and ledger",
  "/evidence": "Evidence review",
  "/analytics": "Analytics and exports",
  "/settings": "Organization settings",
  "/audit": "Audit trail",
  "/my-sites": "My sites",
  "/deliver/new": "New delivery update",
  "/deliveries": "My submissions",
};

/** Top bar: page context, signed-in identity, and a draft-safe logout flow. */
export function TopBar() {
  const session = useSession();
  const navigate = useNavigate();
  const location = useLocation();
  const toast = useToast();
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [discardDrafts, setDiscardDrafts] = useState(false);
  const [busy, setBusy] = useState(false);

  const pageLabel = useMemo(() => {
    if (location.pathname.startsWith("/my-sites/")) return "Site detail";
    if (location.pathname.startsWith("/my-sites")) return PATH_LABELS["/my-sites"];
    return PATH_LABELS[location.pathname] ?? "Corn Distribution Tracker";
  }, [location.pathname]);

  const user = session.user;
  const mustResetPassword = user?.must_reset_password === true;

  function signOut(): void {
    void (async () => {
      setBusy(true);
      if (discardDrafts && user) removeAllDrafts(user.id);
      await logout();
      setBusy(false);
      setConfirmOpen(false);
      toast.notify("info", "Signed out.");
      navigate("/login", { replace: true });
    })();
  }

  function requestSignOut(): void {
    if (user && hasUnsyncedDrafts(user.id)) {
      // OFFLINE_SYNC contract: disclose what stays on-device, then decide.
      setDiscardDrafts(false);
      setConfirmOpen(true);
      return;
    }
    signOut();
  }

  return (
    <>
      <header className="topbar">
        <div className="page-context">{pageLabel}</div>
        <div className="who">
          {mustResetPassword ? (
            <span className="notice warning" role="status">
              Password reset required by an administrator.
            </span>
          ) : null}
          {user ? (
            <>
              <span>
                {user.display_name} · {user.email}
              </span>
              <span className="status-badge" data-tone="info">
                {user.role}
              </span>
              <button type="button" className="btn secondary" onClick={requestSignOut} disabled={busy}>
                Sign out
              </button>
            </>
          ) : null}
        </div>
      </header>
      <ConfirmDialog
        open={confirmOpen}
        title="Discard unsynced drafts?"
        message={
          <>
            <p>
              Unsynced drafts are stored only in this browser for the currently signed-in user. Leaving them in place
              keeps them recoverable the next time this same user signs in; discarding deletes them from the device.
            </p>
            <label className="form-field">
              <span className="label" style={{ fontWeight: "var(--weight-strong)" }}>
                <input type="checkbox" checked={discardDrafts} onChange={(event) => setDiscardDrafts(event.target.checked)} style={{ width: "auto" }} />
                {" "}
                Discard local drafts on this device
              </span>
            </label>
          </>
        }
        confirmLabel={discardDrafts ? "Sign out and discard" : "Sign out and keep drafts"}
        busy={busy}
        onConfirm={signOut}
        onCancel={() => setConfirmOpen(false)}
      />
    </>
  );
}
