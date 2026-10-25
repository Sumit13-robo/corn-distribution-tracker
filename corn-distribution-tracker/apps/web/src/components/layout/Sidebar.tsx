import { useEffect, useRef } from "react";
import { NavLink } from "react-router-dom";
import { useSession } from "../../lib/session";
import { can, type Permission } from "../../lib/permissions";
import { useUnsyncedDraftCount } from "../../app/providers";
import type { Role } from "../../types/domain";
import { BrandMark } from "../../features/auth/AuthLayout";

type NavIconName =
  | "overview"
  | "map"
  | "campaigns"
  | "distributors"
  | "sites"
  | "inventory"
  | "evidence"
  | "analytics"
  | "settings"
  | "audit"
  | "submissions"
  | "drafts";

interface NavItem {
  to: string;
  label: string;
  icon: NavIconName;
  guard: Permission;
  /** The distributor drafts badge surfaces offline work honestly. */
  showDraftBadge?: boolean;
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

const ADMIN_NAV: NavGroup[] = [
  {
    label: "Monitor",
    items: [
      { to: "/", label: "Overview", icon: "overview", guard: "analytics.read" },
      { to: "/map", label: "Distribution map", icon: "map", guard: "map.read" },
    ],
  },
  {
    label: "Plan",
    items: [
      { to: "/campaigns", label: "Campaigns", icon: "campaigns", guard: "campaigns.write" },
      { to: "/distributors", label: "Distributors", icon: "distributors", guard: "distributors.read" },
    ],
  },
  {
    label: "Operate",
    items: [
      { to: "/inventory", label: "Inventory & ledger", icon: "inventory", guard: "inventory.write" },
      { to: "/evidence", label: "Evidence review", icon: "evidence", guard: "deliveries.review" },
    ],
  },
  {
    label: "Oversee",
    items: [
      { to: "/analytics", label: "Analytics & exports", icon: "analytics", guard: "analytics.read" },
      { to: "/settings", label: "Settings", icon: "settings", guard: "settings.write" },
      { to: "/audit", label: "Audit trail", icon: "audit", guard: "audit.read" },
    ],
  },
];

const DISTRIBUTOR_NAV: NavGroup[] = [
  {
    label: "Field work",
    items: [
      { to: "/", label: "Overview", icon: "overview", guard: "deliveries.readOwn" },
      {
        to: "/my-sites",
        label: "My sites",
        icon: "sites",
        guard: "deliveries.submit",
        showDraftBadge: true,
      },
      { to: "/deliveries", label: "My submissions", icon: "submissions", guard: "deliveries.readOwn" },
      {
        to: "/drafts",
        label: "Drafts & sync",
        icon: "drafts",
        guard: "deliveries.submit",
        showDraftBadge: true,
      },
    ],
  },
];

/**
 * Role-aware navigation. On desktop it is a fixed-height rail; below 900 px it
 * becomes an off-canvas drawer opened from the top bar. Focus returns to the
 * menu trigger through the parent's state when the drawer closes.
 */
export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const session = useSession();
  const role: Role | null = session.user?.role ?? null;
  const draftCount = useUnsyncedDraftCount();
  const asideRef = useRef<HTMLElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  const groups = role === "ADMIN" ? ADMIN_NAV : DISTRIBUTOR_NAV;
  const visibleGroups = groups
    .map((group) => ({ ...group, items: group.items.filter((item) => can(role, item.guard)) }))
    .filter((group) => group.items.length > 0);

  useEffect(() => {
    if (!open) return;
    closeRef.current?.focus();
    const drawer = asideRef.current;

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== "Tab" || !drawer) return;
      const focusable = Array.from(
        drawer.querySelectorAll<HTMLElement>('a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])'),
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (!first || !last) return;
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  return (
    <>
      <div className={`sidebar-backdrop${open ? " is-open" : ""}`} onClick={onClose} aria-hidden="true" />
      <aside
        id="primary-navigation"
        ref={asideRef}
        className={`sidebar${open ? " is-open" : ""}`}
        aria-label="Workspace navigation"
      >
        <div className="sidebar-head">
          <NavLink to="/" className="brand" end onClick={onClose} aria-label="Corn Distribution Tracker — overview">
            <BrandMark />
            <span className="brand-copy">
              <strong>Corn Tracker</strong>
              <small>Distribution ledger</small>
            </span>
          </NavLink>
          <button ref={closeRef} type="button" className="sidebar-close" onClick={onClose} aria-label="Close navigation">
            <CloseIcon />
          </button>
        </div>

        <nav aria-label="Primary">
          {visibleGroups.map((group) => (
            <div className="nav-group" key={group.label}>
              <p className="nav-label">{group.label}</p>
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === "/"}
                  className="nav-link"
                  onClick={onClose}
                >
                  <NavIcon name={item.icon} />
                  <span className="nav-text">{item.label}</span>
                  {item.showDraftBadge && draftCount > 0 ? (
                    <span
                      className="nav-count"
                      aria-label={`${draftCount} unsynced ${draftCount === 1 ? "draft" : "drafts"}`}
                    >
                      {draftCount}
                    </span>
                  ) : null}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        <div className="sidebar-footer">
          <span className="sidebar-status-dot" aria-hidden="true" />
          <span>
            Private evidence
            <small>Append-only stock ledger</small>
          </span>
        </div>
      </aside>
    </>
  );
}

function NavIcon({ name }: { name: NavIconName }) {
  return (
    <svg
      className="nav-icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {name === "overview" ? (
        <>
          <rect x="3" y="3" width="7" height="7" rx="1.5" />
          <rect x="14" y="3" width="7" height="7" rx="1.5" />
          <rect x="3" y="14" width="7" height="7" rx="1.5" />
          <rect x="14" y="14" width="7" height="7" rx="1.5" />
        </>
      ) : null}
      {name === "map" ? (
        <>
          <path d="M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0Z" />
          <circle cx="12" cy="10" r="2.5" />
        </>
      ) : null}
      {name === "campaigns" ? (
        <>
          <path d="M5 21V4" />
          <path d="M5 5h11l-2 4 2 4H5" />
        </>
      ) : null}
      {name === "distributors" ? (
        <>
          <circle cx="9" cy="8" r="3" />
          <path d="M3 20a6 6 0 0 1 12 0" />
          <path d="M16 5.5a3 3 0 0 1 0 5.4" />
          <path d="M18 14a5 5 0 0 1 3 4.5" />
        </>
      ) : null}
      {name === "sites" ? (
        <>
          <path d="M3 21h18" />
          <path d="M5 21V9l7-5 7 5v12" />
          <path d="M9 21v-6h6v6" />
        </>
      ) : null}
      {name === "inventory" ? (
        <>
          <path d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Z" />
          <path d="m4 7.5 8 4.5 8-4.5M12 12v9" />
        </>
      ) : null}
      {name === "evidence" ? (
        <>
          <path d="M4 7h3l1.5-2h7L17 7h3a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1Z" />
          <circle cx="12" cy="13" r="3.5" />
        </>
      ) : null}
      {name === "analytics" ? (
        <>
          <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" />
        </>
      ) : null}
      {name === "settings" ? (
        <>
          <path d="M4 6h7M15 6h5M4 12h3M11 12h9M4 18h10M18 18h2" />
          <circle cx="13" cy="6" r="2" />
          <circle cx="8" cy="12" r="2" />
          <circle cx="16" cy="18" r="2" />
        </>
      ) : null}
      {name === "audit" ? (
        <>
          <circle cx="12" cy="12" r="8.5" />
          <path d="M12 7v5l3.5 2" />
        </>
      ) : null}
      {name === "submissions" ? (
        <>
          <path d="M6 2.5h8l4 4V21a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1Z" />
          <path d="M14 2.5V7h4M8.5 12h7M8.5 16h7" />
        </>
      ) : null}
      {name === "drafts" ? (
        <>
          <path d="M20 7a8 8 0 1 0 1 7" />
          <path d="M20 3v5h-5" />
          <path d="M12 8v5l3 2" />
        </>
      ) : null}
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
      <path d="m6 6 12 12M18 6 6 18" />
    </svg>
  );
}
