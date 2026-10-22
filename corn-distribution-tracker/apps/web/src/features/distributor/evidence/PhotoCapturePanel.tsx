/**
 * Photo capture panel: camera-first capture with an explicit file-picker
 * fallback. Photos are attached to the local draft's evidence store and are
 * only uploaded when the draft syncs; nothing is presented as uploaded before
 * the server accepts it.
 */

import { useEffect, useRef, useState } from "react";
import type { DraftPhoto } from "../offline/offlineQueue";
import { attachPhoto, detachPhoto, getPhotoObjectUrl } from "../offline/offlineQueue";
import { formatBytes, formatDateTime } from "../../../lib/format";

interface PhotoCapturePanelProps {
  userId: string;
  draftId: string | null;
  photos: DraftPhoto[];
  /** Present when the browser was offline at draft creation. */
  offlineMode?: boolean;
  onChange?(photos: DraftPhoto[]): void;
}

const ACCEPTED_TYPES = "image/jpeg,image/png,image/webp";

export function PhotoCapturePanel({ userId, draftId, photos, offlineMode = false, onChange }: PhotoCapturePanelProps) {
  const cameraInputRef = useRef<HTMLInputElement | null>(null);
  const pickerInputRef = useRef<HTMLInputElement | null>(null);
  const [previewUrls, setPreviewUrls] = useState<Record<string, string>>({});
  const createdUrlsRef = useRef<Record<string, string>>({});
  const [captureError, setCaptureError] = useState<string | null>(null);

  useEffect(() => {
    const active = new Set(photos.map((photo) => photo.id));
    const createdUrls = createdUrlsRef.current;
    let cancelled = false;
    for (const photo of photos) {
      void getPhotoObjectUrl(photo.id).then((url) => {
        if (cancelled || url === null) return;
        createdUrls[photo.id] = url;
        setPreviewUrls((current) => ({ ...current, [photo.id]: url }));
      });
    }
    return () => {
      cancelled = true;
      for (const [id, url] of Object.entries(createdUrls)) {
        if (!active.has(id)) {
          if (typeof URL.revokeObjectURL === "function") URL.revokeObjectURL(url);
          delete createdUrls[id];
        }
      }
    };
  }, [photos]);

  async function handleFiles(target: HTMLInputElement, source: DraftPhoto["capture_source"]): Promise<void> {
    const files = target.files;
    if (!files || !draftId) {
      setCaptureError(draftId === null ? "Save a draft before attaching photos." : null);
      return;
    }
    setCaptureError(null);
    const next: DraftPhoto[] = [...photos];
    for (const file of Array.from(files)) {
      if (!file.type.startsWith("image/")) {
        setCaptureError("Only JPEG, PNG or WebP images are accepted as evidence.");
        continue;
      }
      if (file.size > 10 * 1024 * 1024) {
        setCaptureError(`${file.name} exceeds the 10 MB evidence limit.`);
        continue;
      }
      const attached = await attachPhoto(userId, draftId, file, source);
      if (attached) next.push(attached);
    }
    target.value = "";
    onChange?.(next);
  }

  async function handleRemove(photoId: string): Promise<void> {
    if (!draftId) return;
    await detachPhoto(userId, draftId, photoId);
    onChange?.(photos.filter((photo) => photo.id !== photoId));
  }

  return (
    <div className="section" data-testid="photo-capture-panel">
      <h2>Evidence photos</h2>
      <p className="muted small">
        At least one photo is required for a submission. Use the camera when available; the file picker covers devices
        without camera capture. Nothing is uploaded until the draft syncs.
      </p>
      {offlineMode ? (
        <p className="notice warning" role="status">
          Offline: photos stay encrypted-at-rest in browser storage on this device and upload when connectivity returns.
        </p>
      ) : null}
      <div className="row" style={{ marginTop: "var(--space-2)" }}>
        <button
          type="button"
          className="btn secondary"
          onClick={(event) => {
            event.preventDefault();
            cameraInputRef.current?.click();
          }}
        >
          Capture photo
        </button>
        <button
          type="button"
          className="btn ghost"
          onClick={(event) => {
            event.preventDefault();
            pickerInputRef.current?.click();
          }}
        >
          Choose file (fallback)
        </button>
      </div>
      <input
        ref={cameraInputRef}
        type="file"
        accept={ACCEPTED_TYPES}
        capture="environment"
        className="sr-only"
        data-testid="camera-input"
        onChange={(event) => void handleFiles(event.currentTarget, offlineMode ? "OFFLINE_CAMERA" : "CAMERA")}
      />
      <input
        ref={pickerInputRef}
        type="file"
        accept={ACCEPTED_TYPES}
        multiple
        className="sr-only"
        data-testid="file-input"
        onChange={(event) => void handleFiles(event.currentTarget, "FILE_PICKER")}
      />
      {captureError ? (
        <p className="form-field" role="alert" style={{ color: "var(--color-danger-text)" }}>
          {captureError}
        </p>
      ) : null}
      <div className="row" data-testid="photo-thumbs" style={{ marginTop: "var(--space-3)" }}>
        {photos.length === 0 ? (
          <p className="small muted">No photos attached yet.</p>
        ) : (
          photos.map((photo) => (
            <figure
              key={photo.id}
              className="evidence-card"
              style={{ width: 180, margin: 0 }}
              data-testid={`photo-thumb-${photo.id}`}
            >
              {previewUrls[photo.id] ? <img src={previewUrls[photo.id]} alt={`Attached photo: ${photo.fileName}`} /> : <div className="skeleton" style={{ height: 110 }} />}
              <figcaption className="meta">
                <span className="flag-chips">
                  {photo.capture_source} · {formatBytes(photo.size_bytes)}
                </span>
                {photo.client_captured_at ? <span>{formatDateTime(photo.client_captured_at)}</span> : null}
                <button type="button" className="btn ghost small" onClick={() => void handleRemove(photo.id)}>
                  Remove
                </button>
              </figcaption>
            </figure>
          ))
        )}
      </div>
    </div>
  );
}
