/**
 * Offline draft queue (docs/architecture/OFFLINE_SYNC.md).
 *
 * Contract points implemented here:
 *  - Client states: LOCAL_DRAFT -> QUEUED -> UPLOADING -> SUBMITTED. Terminal
 *    server states (APPROVED / REJECTED) live on the server and are fetched
 *    through the deliveries API; the local queue never fakes them.
 *  - An idempotency key is generated and persisted when a draft is created and
 *    is reused across every retry and reload.
 *  - Drafts are keyed per signed-in user; on logout the UI asks whether to
 *    discard unsynced drafts and this module removes them when asked to.
 *  - Failed syncs return the draft to QUEUED with the server message attached;
 *    nothing is silently rewritten to "submitted".
 *  - Photos taken offline are stored in IndexedDB (browser storage, device
 *    only) and uploaded on sync; without IndexedDB (e.g. test shells) an
 *    in-memory fallback keeps them for the running page only.
 */

import type { DeliveryCreateIn, EvidenceSpecIn, LocationIn } from "../../../types/domain";
import { api, ApiError, newId, uploadBlob } from "../../../lib/api-client";

export type DraftState = "LOCAL_DRAFT" | "QUEUED" | "UPLOADING" | "SUBMITTED";

export type DraftUnit = "KG" | "QUINTAL" | "TONNE" | "BAG" | string;

export interface DraftLocationSnapshot extends LocationIn {
  accuracy_m?: string | null;
}

export interface DraftPhoto {
  id: string;
  fileName: string;
  content_type: string;
  size_bytes: number;
  capture_source: "CAMERA" | "FILE_PICKER" | "OFFLINE_CAMERA";
  client_captured_at: string | null;
}

export interface LocalDraft {
  id: string;
  userId: string;
  idempotencyKey: string;
  state: DraftState;
  assignmentId: string | null;
  siteId: string | null;
  siteCode: string | null;
  siteName: string | null;
  quantity: string;
  unit: DraftUnit;
  notes: string | null;
  location: DraftLocationSnapshot | null;
  photoIds: string[];
  createdAt: string;
  updatedAt: string;
  attempts: number;
  lastError: string | null;
  /** Present only when a draft has synced and the server returned the record. */
  submittedRecordId: string | null;
  submittedAt: string | null;
}

interface StoredPhoto {
  draftId: string;
  blob: Blob;
  meta: DraftPhoto;
}

const DRAFTS_KEY_PREFIX = "corn-tracker:drafts:v1:";
const PHOTO_DB_NAME = "corn-tracker-evidence";
const PHOTO_DB_VERSION = 1;

const memoryPhotoStore = new Map<string, StoredPhoto>();

const randomId = newId;

/* -------------------------------------------------------------- Persistence */

function draftsKey(userId: string): string {
  return `${DRAFTS_KEY_PREFIX}${userId}`;
}

function readDraftsForUser(userId: string): LocalDraft[] {
  try {
    const raw = window.localStorage.getItem(draftsKey(userId));
    if (!raw) return [];
    const parsed = JSON.parse(raw) as LocalDraft[];
    if (!Array.isArray(parsed)) return [];
    return parsed;
  } catch {
    return [];
  }
}

function writeDraftsForUser(userId: string, drafts: LocalDraft[]): void {
  window.localStorage.setItem(draftsKey(userId), JSON.stringify(drafts));
  for (const listener of changeListeners) listener();
}

const changeListeners = new Set<() => void>();

export function subscribeToDraftChanges(listener: () => void): () => void {
  changeListeners.add(listener);
  if (typeof window !== "undefined") {
    // Cross-tab awareness: another tab may requeue or sync drafts.
    window.addEventListener("storage", listener);
    return () => {
      changeListeners.delete(listener);
      window.removeEventListener("storage", listener);
    };
  }
  return () => changeListeners.delete(listener);
}

/* ---------------------------------------------------------- Public draft API */

export function loadDrafts(userId: string): LocalDraft[] {
  return readDraftsForUser(userId).sort((a, b) => a.createdAt.localeCompare(b.createdAt));
}

export function unsyncedDraftCount(userId: string): number {
  return loadDrafts(userId).filter((draft) => draft.state === "LOCAL_DRAFT" || draft.state === "QUEUED").length;
}

export function hasUnsyncedDrafts(userId: string): boolean {
  return unsyncedDraftCount(userId) > 0;
}

export interface DraftSeed {
  assignmentId?: string | null;
  siteId?: string | null;
  siteCode?: string | null;
  siteName?: string | null;
  quantity?: string;
  unit?: DraftUnit;
  notes?: string | null;
}

/**
 * Creates a draft and immediately persists its idempotency key: retries and
 * reloads reuse the same key so the server can deduplicate submissions.
 */
export function createDraft(userId: string, seed: DraftSeed = {}): LocalDraft {
  const now = new Date().toISOString();
  const draft: LocalDraft = {
    id: randomId(),
    userId,
    idempotencyKey: randomId(),
    state: "LOCAL_DRAFT",
    assignmentId: seed.assignmentId ?? null,
    siteId: seed.siteId ?? null,
    siteCode: seed.siteCode ?? null,
    siteName: seed.siteName ?? null,
    quantity: seed.quantity ?? "",
    unit: seed.unit ?? "KG",
    notes: seed.notes ?? null,
    location: null,
    photoIds: [],
    createdAt: now,
    updatedAt: now,
    attempts: 0,
    lastError: null,
    submittedRecordId: null,
    submittedAt: null,
  };
  writeDraftsForUser(userId, [...readDraftsForUser(userId), draft]);
  return draft;
}

export function getDraft(userId: string, draftId: string | null): LocalDraft | null {
  if (!draftId) return null;
  return readDraftsForUser(userId).find((draft) => draft.id === draftId) ?? null;
}

export interface DraftPatch {
  quantity?: string;
  unit?: DraftUnit;
  notes?: string | null;
  assignmentId?: string | null;
  siteId?: string | null;
  siteCode?: string | null;
  siteName?: string | null;
  location?: DraftLocationSnapshot | null;
}

export function updateDraft(userId: string, draftId: string, patch: DraftPatch): LocalDraft | null {
  const drafts = readDraftsForUser(userId);
  const index = drafts.findIndex((draft) => draft.id === draftId);
  if (index < 0) return null;
  const current = drafts[index];
  if (!current) return null;
  const updated: LocalDraft = {
    ...current,
    ...patch,
    quantity: patch.quantity ?? current.quantity,
    unit: patch.unit ?? current.unit,
    location: patch.location === undefined ? current.location : patch.location,
    /** Only local-context fields are mutable; state flows are explicit below. */
    state: current.state === "LOCAL_DRAFT" ? "LOCAL_DRAFT" : current.state,
    updatedAt: new Date().toISOString(),
  };
  if (updated.state === "LOCAL_DRAFT") updated.lastError = null;
  const nextDrafts = [...drafts.slice(0, index), updated, ...drafts.slice(index + 1)];
  writeDraftsForUser(userId, nextDrafts);
  return updated;
}

export function requeueDraft(userId: string, draftId: string, error?: string): LocalDraft | null {
  return withDraft(userId, draftId, (draft) => ({
    ...draft,
    state: "QUEUED",
    lastError: error ?? draft.lastError,
    updatedAt: new Date().toISOString(),
  }));
}

export function removeDraft(userId: string, draftId: string): void {
  const drafts = readDraftsForUser(userId);
  const removed = drafts.filter((draft) => draft.id !== draftId);
  writeDraftsForUser(userId, removed);
  void deleteDraftPhotos(draftId);
}

/** Removes every draft for a user (used when a user opts to discard on logout). */
export function removeAllDrafts(userId: string): void {
  for (const draft of readDraftsForUser(userId)) {
    void deleteDraftPhotos(draft.id);
  }
  writeDraftsForUser(userId, []);
}

export function clearSubmittedDrafts(userId: string): void {
  const drafts = readDraftsForUser(userId);
  for (const draft of drafts) {
    if (draft.state === "SUBMITTED") void deleteDraftPhotos(draft.id);
  }
  writeDraftsForUser(
    userId,
    drafts.filter((draft) => draft.state !== "SUBMITTED"),
  );
}

/* ------------------------------------------------------------- Photo storage */

let photoDbPromise: Promise<IDBDatabase | null> | null = null;

interface PhotoDatabase {
  get(photoId: string): Promise<StoredPhoto | null>;
  put(record: StoredPhoto): Promise<void>;
  delete(photoId: string): Promise<void>;
  listByDraft(draftId: string): Promise<StoredPhoto[]>;
}

function openPhotoDatabase(): Promise<IDBDatabase | null> {
  if (typeof indexedDB === "undefined") return Promise.resolve(null);
  if (photoDbPromise) return photoDbPromise;
  photoDbPromise = new Promise((resolve) => {
    try {
      const request = indexedDB.open(PHOTO_DB_NAME, PHOTO_DB_VERSION);
      request.onupgradeneeded = () => {
        const db = request.result;
        if (!db.objectStoreNames.contains("photos")) {
          const store = db.createObjectStore("photos", { keyPath: "meta.id" });
          store.createIndex("draftId", "draftId", { unique: false });
        }
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => resolve(null);
    } catch {
      resolve(null);
    }
  });
  return photoDbPromise;
}

function databaseApi(db: IDBDatabase): PhotoDatabase {
  const run = <T>(mode: IDBTransactionMode, work: (store: IDBObjectStore) => IDBRequest<T>): Promise<T> =>
    new Promise((resolve, rejectFn) => {
      const tx = db.transaction("photos", mode);
      const request = work(tx.objectStore("photos"));
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => rejectFn(request.error ?? new Error("IndexedDB failure"));
    });

  return {
    get: (photoId) => run("readonly", (store) => store.get(photoId) as IDBRequest<StoredPhoto>).then((v) => v ?? null),
    put: (record) => run("readwrite", (store) => store.put(record)).then(() => undefined),
    delete: (photoId) => run("readwrite", (store) => store.delete(photoId)).then(() => undefined),
    listByDraft: (draftId) => {
      const all = run(
        "readonly",
        (store) =>
          store.index("draftId").getAll(draftId) as IDBRequest<StoredPhoto[]>,
      );
      return all;
    },
  };
}

function fallbackPhotoApi(): PhotoDatabase {
  return {
    get: async (photoId) => memoryPhotoStore.get(photoId) ?? null,
    put: async (record) => {
      memoryPhotoStore.set(record.meta.id, record);
    },
    delete: async (photoId) => {
      memoryPhotoStore.delete(photoId);
    },
    listByDraft: async (draftId) => [...memoryPhotoStore.values()].filter((photo) => photo.draftId === draftId),
  };
}

async function withPhotoStore<T>(work: (store: PhotoDatabase) => Promise<T>): Promise<T> {
  const db = await openPhotoDatabase();
  return work(db ? databaseApi(db) : fallbackPhotoApi());
}

export async function attachPhoto(
  userId: string,
  draftId: string,
  file: File,
  captureSource: DraftPhoto["capture_source"],
): Promise<DraftPhoto | null> {
  if (!file.type || !file.type.startsWith("image/")) return null;
  const meta: DraftPhoto = {
    id: randomId(),
    fileName: file.name || `${captureSource.toLowerCase()}-capture`,
    content_type: file.type,
    size_bytes: file.size,
    capture_source: captureSource,
    client_captured_at: new Date().toISOString(),
  };
  await withPhotoStore((store) => store.put({ draftId, blob: file, meta }));
  withDraft(userId, draftId, (draft) => ({
    ...draft,
    photoIds: [...draft.photoIds, meta.id],
    updatedAt: new Date().toISOString(),
  }));
  return meta;
}

export async function detachPhoto(userId: string, draftId: string, photoId: string): Promise<void> {
  await withPhotoStore((store) => store.delete(photoId));
  withDraft(userId, draftId, (draft) => ({
    ...draft,
    photoIds: draft.photoIds.filter((id) => id !== photoId),
    updatedAt: new Date().toISOString(),
  }));
}

async function deleteDraftPhotos(draftId: string): Promise<void> {
  await withPhotoStore(async (store) => {
    const photos = await store.listByDraft(draftId);
    for (const photo of photos) await store.delete(photo.meta.id);
  });
}

export async function getPhotoObjectUrl(photoId: string): Promise<string | null> {
  if (typeof URL === "undefined" || !URL.createObjectURL) return null;
  const photo = await withPhotoStore((store) => store.get(photoId));
  if (!photo) return null;
  return URL.createObjectURL(photo.blob);
}

/** Draft photo metadata for the submission UI (previews fetch separately). */
export async function listDraftPhotos(draftId: string): Promise<DraftPhoto[]> {
  const photos = await withPhotoStore((store) => store.listByDraft(draftId));
  return photos.map((photo) => photo.meta);
}

/* ------------------------------------------------------------ Sync machinery */

export interface SyncOutcome {
  syncedDraftIds: string[];
  failedDraftIds: string[];
}

function withDraft(userId: string, draftId: string | null, transform: (draft: LocalDraft) => LocalDraft): LocalDraft | null {
  if (!draftId) return null;
  const drafts = readDraftsForUser(userId);
  const index = drafts.findIndex((draft) => draft.id === draftId);
  if (index < 0) return null;
  const current = drafts[index];
  if (!current) return null;
  const transformed = transform(current);
  const nextDrafts = [...drafts.slice(0, index), transformed, ...drafts.slice(index + 1)];
  writeDraftsForUser(userId, nextDrafts);
  return transformed;
}

/** Age-ordered queue snapshot; dependencies (photos first) are handled inline. */
function queuedDrafts(userId: string): LocalDraft[] {
  return loadDrafts(userId)
    .filter((draft) => draft.state === "QUEUED")
    .sort((a, b) => a.createdAt.localeCompare(b.createdAt));
}

export function flushDrafts(userId: string): void {
  for (const draft of loadDrafts(userId)) {
    if (draft.state === "UPLOADING") {
      // Restarting the page mid-upload must never fake a submission.
      withDraft(userId, draft.id, (current) => ({ ...current, state: "QUEUED", updatedAt: new Date().toISOString() }));
    }
  }
}

async function syncOneDraft(userId: string, draft: LocalDraft): Promise<boolean> {
  withDraft(userId, draft.id, (current) => ({
    ...current,
    state: "UPLOADING",
    updatedAt: new Date().toISOString(),
  }));

  try {
    const photos = await withPhotoStore((store) => store.listByDraft(draft.id));
    const evidence: EvidenceSpecIn[] = [];
    for (const photo of photos) {
      const intent = await api.createUploadIntent(photo.meta.content_type);
      await uploadBlob(intent, photo.blob);
      evidence.push({
        intent_id: intent.intent_id,
        capture_source: photo.meta.capture_source,
        client_captured_at: photo.meta.client_captured_at,
      });
    }

    const payload: DeliveryCreateIn = {
      assignment_id: draft.assignmentId ?? "",
      quantity: draft.quantity,
      unit: draft.unit,
      notes: draft.notes,
      evidence,
      location: draft.location,
    };
    const record = await api.submitDelivery(payload, draft.idempotencyKey);
    withDraft(userId, draft.id, (current) => ({
      ...current,
      state: "SUBMITTED",
      submittedRecordId: record.id,
      submittedAt: record.submitted_at,
      lastError: null,
      updatedAt: new Date().toISOString(),
    }));
    await deleteDraftPhotos(draft.id);
    return true;
  } catch (error) {
    let message = "Sync failed — the draft stays queued for retry.";
    if (error instanceof ApiError) {
      message = friendlyApiError(error);
    } else if (error instanceof TypeError) {
      message = "Network unreachable — the draft stays queued until connectivity returns.";
    }
    withDraft(userId, draft.id, (current) => ({
      ...current,
      state: "QUEUED",
      attempts: current.attempts + 1,
      lastError: message,
      updatedAt: new Date().toISOString(),
    }));
    return false;
  }
}

/** Map known server conflicts to honest, actionable wording (never a fake OK). */
function friendlyApiError(error: ApiError): string {
  switch (error.code) {
    case "VALIDATION_ERROR":
      return `The server rejected this draft: ${error.message}`;
    case "INSUFFICIENT_STOCK":
      return "Stock became insufficient on the server since this draft was saved. Review the quantity and resubmit.";
    default:
      return `Server error (${error.code}): ${error.message}`;
  }
}

/**
 * Syncs all QUEUED drafts in age order. Failures never interrupt the loop for
 * remaining drafts.
 */
export async function syncDrafts(userId: string): Promise<SyncOutcome> {
  const outcome: SyncOutcome = { syncedDraftIds: [], failedDraftIds: [] };
  for (const draft of queuedDrafts(userId)) {
    const success = await syncOneDraft(userId, draft);
    if (success) outcome.syncedDraftIds.push(draft.id);
    else outcome.failedDraftIds.push(draft.id);
  }
  return outcome;
}

export interface SubmitDraftInput {
  userId: string;
  draft: LocalDraft;
}

/**
 * Called by the submission screen: queues the draft then attempts an immediate
 * sync. Online users see LOCAL_DRAFT -> QUEUED -> UPLOADING -> SUBMITTED
 * (server record id); offline users see the draft truthfully parked in QUEUED.
 */
export async function queueAndSync(userId: string, draftId: string): Promise<LocalDraft | null> {
  withDraft(userId, draftId, (current) => ({
    ...current,
    state: "QUEUED",
    updatedAt: new Date().toISOString(),
  }));
  if (typeof navigator !== "undefined" && navigator.onLine === false) {
    return getDraft(userId, draftId);
  }
  const draft = getDraft(userId, draftId);
  if (!draft) return null;
  await syncOneDraft(userId, draft);
  return getDraft(userId, draftId);
}
