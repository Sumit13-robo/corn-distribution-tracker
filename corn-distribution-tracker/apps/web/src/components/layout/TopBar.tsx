import { useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
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
  "/drafts": "Drafts and sync",
};

const ROLE_LABELS = { ADMIN: "Administrator", DISTRIBUTOR: "Distributor" } as const;

/** Top bar: mobile menu trigger, page context, identity, and draft-safe logout. */
export function TopBar({
  onOpenNavigation,
  navigationOpen,
}: {
  onOpenNavigation: () => void;
  navigationOpen: boolean;
}) {
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
        <div className="topbar-main">
          <button
            id="nav-menu-button"
            type="button"
            className="icon-button nav-menu-button"
            aria-label="Open navigation"
            aria-controls="primary-navigation"
            aria-expanded={navigationOpen}
            onClick={onOpenNavigation}
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              aria-hidden="true"
            >
              <path d="M4 7h16M4 12h16M4 17h16" />
            </svg>
          </button>
          <span className="page-context">{pageLabel}</span>
        </div>

        <div className="who">
          {user ? (
            <>
              <span className="who-identity" title={`${user.display_name} — ${user.email}`}>
                <span className="who-avatar" aria-hidden="true">
                  {initials(user.display_name)}
                </span>
                <span className="who-copy">
                  <strong>{user.display_name}</strong>
                  <small>{ROLE_LABELS[user.role]}</small>
                </span>
              </span>
              <button
                type="button"
                className="btn secondary small"
                onClick={requestSignOut}
                disabled={busy}
                aria-busy={busy}
              >
                {busy ? "Signing out…" : "Sign out"}
              </button>
            </>
          ) : null}
        </div>
      </header>

      {mustResetPassword ? (
        <div className="account-banner" role="status">
          <span>
            <strong>Password update required.</strong> An administrator requires you to choose a new password.
          </span>
          <Link to="/reset-password?mode=change" className="btn small">
            Update password
          </Link>
        </div>
      ) : null}

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
                <input
                  type="checkbox"
                  checked={discardDrafts}
                  onChange={(event) => setDiscardDrafts(event.target.checked)}
                  style={{ width: "auto" }}
                />{" "}
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

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  return `${parts[0]?.[0] ?? ""}${parts.length > 1 ? (parts[1]?.[0] ?? "") : ""}`.toUpperCase();
}
