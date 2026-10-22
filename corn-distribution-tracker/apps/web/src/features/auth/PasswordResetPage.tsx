import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../../lib/api-client";
import { FormField } from "../../components/common/FormField";
import { ErrorState } from "../../components/common/ErrorState";

export type ResetMode = "forgot" | "reset" | "invite" | "change";

/**
 * Password flows in a single screen:
 *  - `forgot`: request a reset token through the configured channel,
 *  - `reset`: set a new password using the one-time token,
 *  - `invite`: set the initial password from an invitation token,
 *  - `change`: signed-in password change (must-reset-password flag flow).
 * The forgot flow always answers generically — the UI cannot reveal whether an
 * account exists.
 */
export function PasswordResetPage() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const mode = (params.get("mode") as ResetMode | null) ?? "forgot";
  const [email, setEmail] = useState("");
  const [token, setToken] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  function setMode(next: ResetMode) {
    setParams({ mode: next });
    setError(null);
    setNotice(null);
  }

  function validate(mode: ResetMode): string | null {
    if (mode === "forgot") {
      if (!/.+@.+\..+/.test(email.trim())) return "Enter a valid email address.";
      return null;
    }
    if (token.trim().length < 10) return "Paste the full token you received.";
    if (password.length < 12) return "Use at least 12 characters.";
    if (mode === "invite" && !displayName.trim()) return "Enter your name as it should appear to admins.";
    if (mode === "change" && !currentPassword) return "Enter your current password.";
    return null;
  }

  function submit(event: React.FormEvent) {
    event.preventDefault();
    const validation = validate(mode);
    if (validation) {
      setError(validation);
      return;
    }
    setError(null);
    setPending(true);
    void (async () => {
      try {
        if (mode === "forgot") {
          const ack = await api.forgotPassword(email.trim());
          setNotice(ack.message);
        } else if (mode === "reset") {
          const ack = await api.resetPassword(token.trim(), password);
          setNotice(ack.message);
        } else if (mode === "invite") {
          await api.acceptInvitation(token.trim(), password, displayName.trim());
          setNotice("Invitation accepted. You can now sign in with your new password.");
        } else {
          const ack = await api.changePassword(currentPassword, password);
          setNotice(ack.message);
        }
        setPending(false);
      } catch (err) {
        setError(err instanceof Error ? err.message : "The request could not be completed.");
        setPending(false);
      }
    })();
  }

  const heading: Record<ResetMode, string> = {
    forgot: "Request a password reset",
    reset: "Set a new password",
    invite: "Accept invitation",
    change: "Change your password",
  };

  return (
    <div className="center-card">
      <h1>{heading[mode]}</h1>
      {mode === "forgot" ? (
        <p className="brand-line">
          Enter your account email. If it exists, a one-time reset token is delivered through your organization's
          configured channel — the response gives no indication whether an account exists.
        </p>
      ) : (
        <p className="brand-line">
          Tokens are single-use and expire. {mode === "change" ? "All sessions may be revoked after a change." : ""}
        </p>
      )}
      {notice ? (
        <div className="notice success" role="status">
          {notice}
        </div>
      ) : null}
      {error ? <ErrorState error={new Error(error)} title="Could not continue." /> : null}
      <form className="form-grid" onSubmit={submit} noValidate>
        {mode === "forgot" ? (
          <FormField id="reset-email" label="Email" required>
            {(ids) => (
              <input
                id="reset-email"
                type="email"
                autoComplete="email"
                value={email}
                aria-describedby={ids.describedBy}
                onChange={(event) => setEmail(event.target.value)}
                disabled={pending}
              />
            )}
          </FormField>
        ) : (
          <>
            {mode === "change" ? (
              <FormField id="current-password" label="Current password" required>
                {(ids) => (
                  <input
                    id="current-password"
                    type="password"
                    autoComplete="current-password"
                    value={currentPassword}
                    aria-describedby={ids.describedBy}
                    onChange={(event) => setCurrentPassword(event.target.value)}
                    disabled={pending}
                  />
                )}
              </FormField>
            ) : null}
            <FormField
              id="reset-token"
              label="One-time token"
              required
              helper="Paste the token exactly as delivered (visible in the message from your organization)."
            >
              {(ids) => (
                <input
                  id="reset-token"
                  type="text"
                  value={token}
                  aria-describedby={ids.describedBy}
                  onChange={(event) => setToken(event.target.value)}
                  disabled={pending}
                />
              )}
            </FormField>
            {mode === "invite" ? (
              <FormField id="display-name" label="Display name" required>
                {(ids) => (
                  <input
                    id="display-name"
                    type="text"
                    value={displayName}
                    aria-describedby={ids.describedBy}
                    onChange={(event) => setDisplayName(event.target.value)}
                    disabled={pending}
                  />
                )}
              </FormField>
            ) : null}
            <FormField id="new-password" label="New password" required helper="At least 12 characters.">
              {(ids) => (
                <input
                  id="new-password"
                  type="password"
                  autoComplete="new-password"
                  value={password}
                  aria-describedby={ids.describedBy}
                  onChange={(event) => setPassword(event.target.value)}
                  disabled={pending}
                />
              )}
            </FormField>
          </>
        )}
        <div className="form-actions">
          <button type="submit" className="btn" disabled={pending}>
            {pending ? "Working…" : mode === "forgot" ? "Send request" : "Continue"}
          </button>
          <Link to="/login" className="btn ghost">
            Back to sign in
          </Link>
        </div>
      </form>
      <div className="row" style={{ marginTop: "var(--space-3)" }}>
        {(["forgot", "reset", "invite"] as const).map((candidate) => (
          <button
            key={candidate}
            type="button"
            className="btn ghost"
            onClick={() => setMode(candidate)}
            aria-pressed={mode === candidate}
          >
            {candidate === "forgot" ? "Request reset" : candidate === "reset" ? "Reset password" : "Invitation"}
          </button>
        ))}
        {mode === "change" ? (
          <button type="button" className="btn ghost" onClick={() => navigate("/")}>
            Return to workspace
          </button>
        ) : null}
      </div>
    </div>
  );
}
