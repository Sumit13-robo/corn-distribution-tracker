/**
 * Session state. The access token lives in module memory only — it is never
 * written to localStorage/sessionStorage, so a stolen device storage dump
 * cannot yield a bearer token. On a reload the session is restored through the
 * HttpOnly refresh cookie via POST /auth/refresh (single rotation), which
 * returns a fresh access token and the current user.
 */

import { useSyncExternalStore } from "react";

import type { LoginOut, UserOut } from "../types/domain";
import { configureAuth, registerRefreshTokenSink, request } from "./api-client";

export type SessionStatus = "LOADING" | "SIGNED_IN" | "SIGNED_OUT";

export interface SessionState {
  status: SessionStatus;
  user: UserOut | null;
}

let state: SessionState = { status: "LOADING", user: null };

const listeners = new Set<() => void>();

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function getSnapshot(): SessionState {
  return state;
}

function publish(next: SessionState): void {
  state = next;
  for (const listener of listeners) listener();
}

let accessToken: string | null = null;

/** Register this module as the api-client's token source before any request. */
configureAuth({
  getToken: () => accessToken,
  onAuthLost: () => {
    // Refresh rotation failed (expired/revoked): the session is gone.
    clearSession("SIGNED_OUT");
  },
});

registerRefreshTokenSink((token) => {
  accessToken = token;
});

function clearSession(status: SessionStatus): void {
  accessToken = null;
  publish({ status, user: null });
}

export async function login(email: string, password: string): Promise<UserOut> {
  const result = await request<LoginOut>("POST", "/auth/login", {
    body: { email, password },
  });
  accessToken = result.access_token;
  publish({ status: "SIGNED_IN", user: result.user });
  return result.user;
}

/**
 * Restores the session after a page load. Only the HttpOnly cookie is needed;
 * failure to refresh simply means "not signed in". Lighthouse-frequent pattern;
 * returns the final status so the router can decide what to render.
 */
export async function restoreSession(): Promise<SessionStatus> {
  try {
    const result = await request<LoginOut>("POST", "/auth/refresh");
    accessToken = result.access_token;
    publish({ status: "SIGNED_IN", user: result.user });
    return "SIGNED_IN";
  } catch {
    clearSession("SIGNED_OUT");
    return "SIGNED_OUT";
  }
}

/**
 * Revokes the refresh session server-side (best effort) and drop the memory
 * token. Local unsynced drafts are handled by the caller, which must ask the
 * user what to keep before calling this (docs/architecture/OFFLINE_SYNC.md).
 */
export async function logout(): Promise<void> {
  try {
    await request<{ message: string }>("POST", "/auth/logout");
  } catch {
    // Signature: the server is unreachable — clear locally anyway.
  } finally {
    clearSession("SIGNED_OUT");
  }
}

/** Human-safe current user (used by layout + role guards). */
export function currentUser(): UserOut | null {
  return state.user;
}

/** User id of the signed-in session or null (offline queue scoping). */
export function getCurrentUserId(): string | null {
  return state.user?.id ?? null;
}

/** React hook for session state; safe across all route components. */
export function useSession(): SessionState {
  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
}

export { subscribe as subscribeToSession, getSnapshot as sessionSnapshot };
