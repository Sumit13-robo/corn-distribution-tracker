/**
 * UI permission helpers. Mirrors the server-side authorization scopes in
 * apps/api/app/api/dependencies.py: UI permissions are supplementary — every
 * endpoint re-checks role and record ownership, so an incorrect client here can
 * never bypass server authorization.
 */

import type { Role } from "../types/domain";

export type Permission =
  | "campaigns.read"
  | "campaigns.write"
  | "distributors.read"
  | "distributors.write"
  | "sites.read"
  | "sites.write"
  | "assignments.read"
  | "assignments.readAll"
  | "assignments.write"
  | "inventory.read"
  | "inventory.write"
  | "deliveries.readOwn"
  | "deliveries.readAll"
  | "deliveries.submit"
  | "deliveries.review"
  | "evidence.upload"
  | "evidence.read"
  | "map.read"
  | "analytics.read"
  | "exports.read"
  | "settings.read"
  | "settings.write"
  | "audit.read";

const ADMIN_PERMISSIONS: Permission[] = [
  "campaigns.read",
  "campaigns.write",
  "distributors.read",
  "distributors.write",
  "sites.read",
  "sites.write",
  "assignments.read",
  "assignments.readAll",
  "assignments.write",
  "inventory.read",
  "inventory.write",
  "deliveries.readAll",
  "deliveries.review",
  "evidence.read",
  "map.read",
  "analytics.read",
  "exports.read",
  "settings.read",
  "settings.write",
  "audit.read",
];

const DISTRIBUTOR_PERMISSIONS: Permission[] = [
  "campaigns.read",
  "sites.read",
  "assignments.read",
  "inventory.read",
  "deliveries.readOwn",
  "deliveries.submit",
  "evidence.upload",
  "settings.read",
];

const ROLE_PERMISSIONS: Record<Role, Permission[]> = {
  ADMIN: ADMIN_PERMISSIONS,
  DISTRIBUTOR: DISTRIBUTOR_PERMISSIONS,
};

export function can(role: Role | null | undefined, permission: Permission): boolean {
  if (!role) return false;
  const granted = ROLE_PERMISSIONS[role];
  return granted.includes(permission);
}

/** Landing route per role (used after login and by guards). */
export function homePathFor(_role: Role | null | undefined): string {
  // Both roles land on "/" — the dashboard component is role-aware.
  return "/";
}
