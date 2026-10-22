import { NavLink } from "react-router-dom";
import { useSession } from "../../lib/session";
import { can, type Permission } from "../../lib/permissions";
import { useUnsyncedDraftCount } from "../../app/providers";
import type { Role } from "../../types/domain";

interface NavItem {
  to: string;
  label: string;
  guard: Permission;
  /** The distributor drafts badge surfaces offline work honestly. */
  showDraftBadge?: boolean;
}

const ADMIN_NAV: NavItem[] = [
  { to: "/", label: "Overview", guard: "analytics.read" },
  { to: "/map", label: "Distribution map", guard: "map.read" },
  { to: "/campaigns", label: "Campaigns", guard: "campaigns.write" },
  { to: "/distributors", label: "Distributors", guard: "distributors.read" },
  { to: "/sites", label: "Sites", guard: "sites.write" },
  { to: "/inventory", label: "Inventory", guard: "inventory.write" },
  { to: "/evidence", label: "Evidence review", guard: "deliveries.review" },
  { to: "/analytics", label: "Analytics", guard: "analytics.read" },
  { to: "/settings", label: "Settings", guard: "settings.write" },
  { to: "/audit", label: "Audit trail", guard: "audit.read" },
];

const DISTRIBUTOR_NAV: NavItem[] = [
  { to: "/", label: "Overview", guard: "deliveries.readOwn" },
  { to: "/my-sites", label: "My sites", guard: "deliveries.submit", showDraftBadge: true },
  { to: "/deliveries", label: "My submissions", guard: "deliveries.readOwn" },
];

/**
 * Navigation sidebar. Links render per granted permission; the distributor's
 * unsynced-draft count shows in the nav so queued work is never a surprise.
 */
export function Sidebar() {
  const session = useSession();
  const role: Role | null = session.user?.role ?? null;
  const draftCount = useUnsyncedDraftCount();

  const items = role === "ADMIN" ? ADMIN_NAV : DISTRIBUTOR_NAV;
  const visible = items.filter((item) => can(role, item.guard));

  return (
    <aside className="sidebar">
      <div className="brand">
        Corn Distribution Tracker
        <small>Accountable stock allocation</small>
      </div>
      <nav aria-label="Primary">
        {visible.map((item) => (
          <NavLink key={item.to} to={item.to} end={item.to === "/"}>
            {item.label}
            {item.showDraftBadge && draftCount > 0 ? (
              <span className="status-badge" data-tone="pending" style={{ marginLeft: "var(--space-2)" }}>
                {draftCount} queued
              </span>
            ) : null}
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-footer">
        <span>API v1 · offline-capable drafts</span>
      </div>
    </aside>
  );
}
