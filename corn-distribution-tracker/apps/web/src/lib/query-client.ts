/**
 * TanStack Query client factory plus the single source of truth for query
 * keys. Screens read server state only through these keys so mutations can
 * invalidate precisely and consistently.
 */

import { QueryClient } from "@tanstack/react-query";
import { ApiError } from "./api-client";
import type { DeliveryListFilters } from "../types/domain";

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 20_000,
        gcTime: 5 * 60_000,
        refetchOnWindowFocus: false,
        // 4xx responses will not succeed on retry; only transient failures retry.
        retry: (failureCount, error) => {
          if (error instanceof ApiError && error.status >= 400 && error.status < 500) return false;
          return failureCount < 2;
        },
      },
      mutations: {
        retry: false,
      },
    },
  });
}

/** Every list/detail/mutation key used in the app. */
export const queryKeys = {
  campaigns: (status?: string) => ["campaigns", status ?? "any"] as const,
  distributors: (search: string) => ["distributors", search] as const,
  invitations: () => ["invitations"] as const,
  sites: (filters: { search?: string; active_only?: boolean; campaign_id?: string }) =>
    ["sites", filters.search ?? "", filters.campaign_id ?? "any", filters.active_only === true] as const,
  site: (id: string) => ["site", id] as const,
  siteProgress: (siteId: string, campaignId: string | null) =>
    ["site-progress", siteId, campaignId ?? "any"] as const,
  assignments: (campaignId: string | null) => ["assignments", campaignId ?? "any"] as const,
  myAssignments: () => ["my-assignments"] as const,
  inventorySummary: () => ["inventory-summary"] as const,
  accountLedger: (accountId: string) => ["account-ledger", accountId] as const,
  deliveries: (filters: DeliveryListFilters) => ["deliveries", filters] as const,
  delivery: (id: string) => ["delivery", id] as const,
  overview: (campaignId: string | null) => ["analytics-overview", campaignId ?? "any"] as const,
  distributorPerformance: (campaignId: string | null) =>
    ["analytics-distributors", campaignId ?? "any"] as const,
  sitePerformance: (campaignId: string | null) => ["analytics-sites", campaignId ?? "any"] as const,
  mapDeliveries: (campaignId: string | null, distributorId: string | null) =>
    ["analytics-map-deliveries", campaignId ?? "any", distributorId ?? "any"] as const,
  mapSites: (campaignId: string | null, distributorId: string | null) =>
    ["analytics-map-sites", campaignId ?? "any", distributorId ?? "any"] as const,
  auditEvents: (filters: Record<string, string>) => ["audit-events", filters] as const,
};
