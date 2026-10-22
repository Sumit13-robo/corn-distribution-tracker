/**
 * Session state backed by Django's HttpOnly session cookie.
 *
 * The browser never exposes credentials to JavaScript. On boot we ask
 * GET /auth/me whether the cookie is still valid; unsafe requests carry the
 * CSRF token managed by lib/api-client. No token is ever written to storage.
 */

import { useSyncExternalStore } from "react";

import type { LoginOut, UserOut } from "../types/domain";
import { configureAuth, request } from "./api-client";

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

/** Register this module as the api-client's session-loss observer. */
configureAuth({
  onAuthLost: () => {
    // Any 401 from a data endpoint means the server-side session is gone.
    clearSession("SIGNED_OUT");
  },
});

function clearSession(status: SessionStatus): void {
  publish({ status, user: null });
}

export async function login(email: string, password: string): Promise<UserOut> {
  const result = await request<LoginOut>("POST", "/auth/login", {
    body: { email, password },
  });
  publish({ status: "SIGNED_IN", user: result.user });
  return result.user;
}

/** Restores the signed-in user from the HttpOnly session cookie. */
export async function restoreSession(): Promise<SessionStatus> {
  try {
    const user = await request<UserOut>("GET", "/auth/me");
    publish({ status: "SIGNED_IN", user });
    return "SIGNED_IN";
  } catch {
    clearSession("SIGNED_OUT");
    return "SIGNED_OUT";
  }
}

/**
 * Revokes the server session (best effort) and drops the local identity.
 * Local unsynced drafts are handled by the caller, which must ask the user
 * what to keep before calling this (docs/architecture/OFFLINE_SYNC.md).
 */
export async function logout(): Promise<void> {
  try {
    await request<{ message: string }>("POST", "/auth/logout");
  } catch {
    // Server unreachable: clear locally anyway; the cookie expires server-side.
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
