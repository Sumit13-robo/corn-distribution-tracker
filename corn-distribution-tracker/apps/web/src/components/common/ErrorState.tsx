import type { ReactNode } from "react";
import { ApiError } from "../../lib/api-client";

interface ErrorStateProps {
  error?: unknown;
  title?: string;
  description?: ReactNode;
  onRetry?: () => void;
}

/** Friendly error block; surfaces request_id for support without leaking internals. */
export function ErrorState({ error, title = "Something went wrong.", description, onRetry }: ErrorStateProps) {
  let message = typeof description === "string" ? description : "Please try again.";
  let requestId: string | null = null;
  if (error instanceof ApiError) {
    message = error.message;
    requestId = error.requestId;
  } else if (error instanceof Error) {
    message = error.message;
  }
  return (
    <div className="state-block error" role="alert" data-testid="error-state">
      <span className="title">{title}</span>
      <div>{message}</div>
      {requestId ? (
        <div className="small" style={{ marginTop: "var(--space-2)" }}>
          Request ID: <code>{requestId}</code>
        </div>
      ) : null}
      {onRetry ? (
        <div className="actions">
          <button type="button" className="btn secondary" onClick={onRetry}>
            Retry
          </button>
        </div>
      ) : null}
    </div>
  );
}
