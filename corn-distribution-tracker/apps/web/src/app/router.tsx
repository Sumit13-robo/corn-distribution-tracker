/**
 * Route registry with role guards. Server authorization is authoritative —
 * these guards only shape the UI and prevent wasted round-trips; every
 * endpoint still enforces role and record-ownership scope itself.
 */

import { Navigate, Outlet, RouterProvider, createBrowserRouter, useLocation } from "react-router-dom";
import { AppShell } from "../components/layout/AppShell";
import { LoginPage } from "../features/auth/LoginPage";
import { PasswordResetPage } from "../features/auth/PasswordResetPage";
import { AdminDashboardPage } from "../features/admin/dashboard/AdminDashboardPage";
import { DistributionMapPage } from "../features/admin/map/DistributionMapPage";
import { DistributorsPage } from "../features/admin/distributors/DistributorsPage";
import { SitesPage } from "../features/admin/sites/SitesPage";
import { CampaignsPage } from "../features/admin/campaigns/CampaignsPage";
import { InventoryPage } from "../features/admin/inventory/InventoryPage";
import { EvidenceReviewPage } from "../features/admin/evidence/EvidenceReviewPage";
import { AnalyticsPage } from "../features/admin/analytics/AnalyticsPage";
import { SettingsPage } from "../features/admin/settings/SettingsPage";
import { AuditTrailPage } from "../features/admin/audit/AuditTrailPage";
import { DistributorDashboardPage } from "../features/distributor/dashboard/DistributorDashboardPage";
import { AssignedSitesPage } from "../features/distributor/sites/AssignedSitesPage";
import { SiteDetailPage } from "../features/distributor/sites/SiteDetailPage";
import { DeliverySubmissionPage } from "../features/distributor/deliveries/DeliverySubmissionPage";
import { MySubmissionsPage } from "../features/distributor/deliveries/MySubmissionsPage";
import { EmptyState } from "../components/common/EmptyState";
import { useSession } from "../lib/session";
import type { Role } from "../types/domain";
import type { ReactNode } from "react";

function FullScreenLoading() {
  return (
    <div className="center-card" role="status">
      <span className="skeleton" style={{ width: "60%", display: "inline-block" }} />
      <p className="muted">Restoring session…</p>
    </div>
  );
}

function RequireAuth() {
  const session = useSession();
  const location = useLocation();
  if (session.status === "LOADING") return <FullScreenLoading />;
  if (session.status !== "SIGNED_IN") {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <AppShell />;
}

function RequireRole({ roles, children }: { roles: Role[]; children?: ReactNode }) {
  const session = useSession();
  if (session.status === "SIGNED_IN" && session.user && roles.includes(session.user.role)) {
    return children ?? <Outlet />;
  }
  return (
    <EmptyState
      title="You do not have access to this page."
      description="This section is limited to a different role. Use the navigation menu to return to your workspace."
    />
  );
}

function DashboardSelector() {
  const session = useSession();
  if (session.user?.role === "ADMIN") return <AdminDashboardPage />;
  return <DistributorDashboardPage />;
}

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  { path: "/reset-password", element: <PasswordResetPage /> },
  {
    path: "/",
    element: <RequireAuth />,
    children: [
      { index: true, element: <DashboardSelector /> },
      {
        element: <RequireRole roles={["ADMIN"]} />,
        children: [
          { path: "map", element: <DistributionMapPage /> },
          { path: "campaigns", element: <CampaignsPage /> },
          { path: "distributors", element: <DistributorsPage /> },
          { path: "sites", element: <SitesPage /> },
          { path: "inventory", element: <InventoryPage /> },
          { path: "evidence", element: <EvidenceReviewPage /> },
          { path: "analytics", element: <AnalyticsPage /> },
          { path: "settings", element: <SettingsPage /> },
          { path: "audit", element: <AuditTrailPage /> },
        ],
      },
      {
        element: <RequireRole roles={["DISTRIBUTOR"]} />,
        children: [
          { path: "my-sites", element: <AssignedSitesPage /> },
          { path: "my-sites/:siteId", element: <SiteDetailPage /> },
          { path: "deliver/new", element: <DeliverySubmissionPage /> },
          { path: "deliveries", element: <MySubmissionsPage /> },
        ],
      },
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
]);

export function AppRoutes() {
  return <RouterProvider router={router} />;
}
