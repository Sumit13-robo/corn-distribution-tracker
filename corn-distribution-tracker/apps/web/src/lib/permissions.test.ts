import { describe, expect, it } from "vitest";
import { can, homePathFor, type Permission } from "./permissions";

/** These enforce the same scope split the server applies (RBAC in dependencies). */
const ADMIN_ONLY_PERMISSIONS: Permission[] = [
  "campaigns.write",
  "distributors.write",
  "sites.write",
  "inventory.write",
  "deliveries.readAll",
  "deliveries.review",
  "evidence.read",
  "map.read",
  "analytics.read",
  "exports.read",
  "settings.write",
  "audit.read",
];

const SHARED_PERMISSIONS: Permission[] = ["campaigns.read", "sites.read", "inventory.read", "settings.read"];

describe("permissions", () => {
  it("grants admins every administrative permission", () => {
    for (const permission of ADMIN_ONLY_PERMISSIONS) {
      expect(can("ADMIN", permission), `admin permission: ${permission}`).toBe(true);
    }
  });

  it("denies distributors administrative endpoints in the UI", () => {
    for (const permission of ADMIN_ONLY_PERMISSIONS) {
      expect(can("DISTRIBUTOR", permission), `distributor must lack: ${permission}`).toBe(false);
    }
  });

  it("grants distributors their submission workflow and shared reads", () => {
    expect(can("DISTRIBUTOR", "deliveries.submit")).toBe(true);
    expect(can("DISTRIBUTOR", "deliveries.readOwn")).toBe(true);
    expect(can("DISTRIBUTOR", "evidence.upload")).toBe(true);
    expect(can("DISTRIBUTOR", "assignments.read")).toBe(true);
    for (const permission of SHARED_PERMISSIONS) {
      expect(can("DISTRIBUTOR", permission), `shared permission: ${permission}`).toBe(true);
    }
  });

  it("denies admins the distributor-only submission action", () => {
    // Records are submitted by the assigned distributor; admins review.
    expect(can("ADMIN", "deliveries.submit")).toBe(false);
  });

  it("denies unknown or signed-out roles", () => {
    expect(can(null, "analytics.read")).toBe(false);
    expect(can(undefined, "deliveries.submit")).toBe(false);
  });

  it("lands every role on the dashboard route", () => {
    expect(homePathFor("ADMIN")).toBe("/");
    expect(homePathFor("DISTRIBUTOR")).toBe("/");
    expect(homePathFor(null)).toBe("/");
  });
});
