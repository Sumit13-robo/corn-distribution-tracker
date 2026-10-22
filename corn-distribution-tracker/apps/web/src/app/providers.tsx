/**
 * Application providers: typed query cache, toast notifications, offline
 * queue sync management, and the global session-clearing behaviour on logout.
 */

import { QueryClientProvider } from "@tanstack/react-query";
import type { QueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { createQueryClient } from "../lib/query-client";
import { getCurrentUserId, sessionSnapshot, subscribeToSession, useSession } from "../lib/session";
import {
  flushDrafts,
  subscribeToDraftChanges,
  syncDrafts,
  unsyncedDraftCount,
} from "../features/distributor/offline/offlineQueue";

/* -------------------------------------------------------------------- Toasts */

export type ToastTone = "info" | "success" | "danger" | "warning";

export interface ToastMessage {
  id: number;
  tone: ToastTone;
  text: string;
}

interface ToastContextValue {
  notify: (tone: ToastTone, text: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast(): ToastContextValue {
  const value = useContext(ToastContext);
  if (value === null) throw new Error("useToast must be used inside AppProviders");
  return value;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const notify = useCallback((tone: ToastTone, text: string) => {
    const id = Date.now() + Math.random();
    setToasts((current) => [...current, { id, tone, text }]);
    window.setTimeout(() => {
      setToasts((current) => current.filter((toast) => toast.id !== id));
    }, 6_000);
  }, []);

  const contextValue = useMemo(() => ({ notify }), [notify]);

  return (
    <ToastContext.Provider value={contextValue}>
      {children}
      <div className="toast-stack" role="status" aria-live="polite" data-testid="toast-stack">
        {toasts.map((toast) => (
          <div key={toast.id} className="toast" data-tone={toast.tone}>
            {toast.text}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

/* ------------------------------------------------------- Offline sync manager */

const SYNC_INTERVAL_MS = 30_000;

/**
 * Runs the offline draft sync loop for the signed-in distributor. Triggers:
 * boot, connectivity, interval while signed in, and cross-tab draft-storage
 * changes (draftLibraryVersion). Local writes drive their own immediate sync
 * in the screen to avoid duplicate in-flight submissions.
 */
function OfflineSyncManager({ draftLibraryVersion }: { draftLibraryVersion: number }) {
  const session = useSession();
  const userId = session.status === "SIGNED_IN" ? session.user?.id ?? null : null;

  useEffect(() => {
    if (!userId) return;
    flushDrafts(userId); // never trust an interrupted UPLOADING state on boot
    let cancelled = false;

    const run = () => {
      if (cancelled || (typeof navigator !== "undefined" && navigator.onLine === false)) return;
      void syncDrafts(userId);
    };
    run();
    const interval = window.setInterval(run, SYNC_INTERVAL_MS);
    window.addEventListener("online", run);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
      window.removeEventListener("online", run);
    };
  }, [userId, draftLibraryVersion]);

  return null;
}

/* ------------------------------------------------------------------ Providers */

interface QueueCountContextValue {
  count: number;
}

const QueueCountContext = createContext<QueueCountContextValue>({ count: 0 });

/** Gives the layout a live count of unsynced distributor drafts. */
export function useUnsyncedDraftCount(): number {
  return useContext(QueueCountContext).count;
}

export function AppProviders({ children }: { children: ReactNode }) {
  const queryClient: QueryClient = useMemo(() => createQueryClient(), []);

  // Draft library revision: increments whenever any tab requeues/syncs drafts.
  const [draftLibraryVersion, setDraftLibraryVersion] = useState(0);
  const [queueCount, setQueueCount] = useState(0);

  useEffect(() => {
    return subscribeToSession(() => {
      if (sessionSnapshot().status === "SIGNED_OUT") queryClient.clear();
    });
  }, [queryClient]);

  useEffect(() => {
    const recount = () => {
      const userId = getCurrentUserId();
      if (userId) {
        setQueueCount(unsyncedDraftCount(userId));
      } else {
        setQueueCount(0);
      }
    };
    recount();
    const stopDrafts = subscribeToDraftChanges(() => {
      // Local writes drive their own sync (e.g. the submission screen); only
      // recount here. Cross-tab writes bump the version below so the manager
      // picks up drafts requeued/synced elsewhere without racing this tab.
      recount();
    });
    const stopSession = subscribeToSession(() => {
      // Login/logout switches the user scope: never show another account's queue count.
      recount();
    });
    const onStorage = () => {
      recount();
      setDraftLibraryVersion((version) => version + 1);
    };
    window.addEventListener("storage", onStorage);
    return () => {
      stopDrafts();
      stopSession();
      window.removeEventListener("storage", onStorage);
    };
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <OfflineSyncManager draftLibraryVersion={draftLibraryVersion} />
        <QueueCountContext.Provider value={{ count: queueCount }}>{children}</QueueCountContext.Provider>
      </ToastProvider>
    </QueryClientProvider>
  );
}
