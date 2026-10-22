import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { login, useSession } from "../../lib/session";
import { FormField } from "../../components/common/FormField";
import { ErrorState } from "../../components/common/ErrorState";

/** Login screen (SCREEN_SPECS: clean branded shell, no public registration). */
export function LoginPage() {
  const session = useSession();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  if (session.status === "SIGNED_IN" && session.user) {
    return <Navigate to="/" replace />;
  }
  if (session.status === "LOADING") {
    return (
      <div className="center-card" role="status">
        <span className="skeleton" style={{ width: "50%", display: "inline-block" }} />
        <p className="muted">Checking existing session…</p>
      </div>
    );
  }

  function validate(): string | null {
    if (!email.trim()) return "Enter your email address.";
    if (!/.+@.+\..+/.test(email.trim())) return "Enter a valid email address.";
    if (!password) return "Enter your password.";
    return null;
  }

  function submit(event: React.FormEvent) {
    event.preventDefault();
    const error = validate();
    setFieldError(error);
    if (error) return;
    setPending(true);
    setAuthError(null);
    void (async () => {
      try {
        await login(email.trim(), password);
        navigate("/", { replace: true });
      } catch {
        // Generic failure only: never reveal whether the account exists.
        setAuthError("Email or password is incorrect, or sign-in is temporarily unavailable.");
        setPending(false);
      }
    })();
  }

  return (
    <div className="center-card">
      <h1>Corn Distribution Tracker</h1>
      <p className="brand-line">Sign in with the account issued by your organization.</p>
      {authError ? <ErrorState error={new Error(authError)} title="Sign-in failed." /> : null}
      <form className="form-grid" onSubmit={submit} noValidate>
        <FormField
          id="login-email"
          label="Email"
          required
          error={fieldError && !email.trim() ? fieldError : null}
          helper="Use the address your invitation or admin account was issued to."
        >
          {(ids) => (
            <input
              id="login-email"
              type="email"
              autoComplete="email"
              value={email}
              aria-describedby={ids.describedBy}
              onChange={(event) => setEmail(event.target.value)}
              disabled={pending}
            />
          )}
        </FormField>
        <FormField id="login-password" label="Password" required>
          {(ids) => (
            <>
              <input
                id="login-password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                value={password}
                aria-describedby={ids.describedBy}
                onChange={(event) => setPassword(event.target.value)}
                disabled={pending}
              />
              <label className="helper" style={{ display: "inline-flex", gap: 4, alignItems: "center" }}>
                <input
                  type="checkbox"
                  checked={showPassword}
                  onChange={(event) => setShowPassword(event.target.checked)}
                  style={{ width: "auto" }}
                />
                Show password
              </label>
            </>
          )}
        </FormField>
        {fieldError ? <div className="form-field">{fieldError}</div> : null}
        <div className="form-actions">
          <button type="submit" className="btn" disabled={pending}>
            {pending ? "Signing in…" : "Sign in"}
          </button>
          <Link to="/reset-password" className="btn ghost">
            Forgot password?
          </Link>
          <Link to="/reset-password?mode=invite" className="btn ghost">
            Accept invitation
          </Link>
        </div>
      </form>
      {pending ? (
        <p role="status" className="small muted">
          Verifying credentials…
        </p>
      ) : null}
    </div>
  );
}
