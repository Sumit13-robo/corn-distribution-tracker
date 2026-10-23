import { useState, type FormEvent } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { ApiError } from "../../lib/api-client";
import { login, useSession } from "../../lib/session";
import { FormField } from "../../components/common/FormField";
import { AuthLayout } from "./AuthLayout";

interface FieldErrors {
  email?: string;
  password?: string;
}

const GENERIC_LOGIN_ERROR =
  "Email or password is incorrect, or sign-in is temporarily unavailable.";

/**
 * Keeps credential failures deliberately generic (no account enumeration) but
 * tells the user what to do about throttling or an unreachable API instead of
 * blaming the password for an infrastructure problem.
 */
export function loginErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 429 || error.code === "RATE_LIMITED") {
      const detail = error.details.find((item) => typeof item.retry_after === "number");
      const seconds = typeof detail?.retry_after === "number" ? Math.ceil(detail.retry_after) : 0;
      if (seconds > 0) {
        const wait = seconds < 60 ? `${seconds} seconds` : `${Math.ceil(seconds / 60)} minutes`;
        return `Too many sign-in attempts. Try again in ${wait}.`;
      }
      return "Too many sign-in attempts. Try again in a few minutes.";
    }
    if (error.status >= 500) {
      return "The sign-in service is temporarily unavailable. Try again shortly.";
    }
    if (error.status === 403) {
      return "Your sign-in session expired. Reload the page and try again.";
    }
  }
  if (error instanceof TypeError) {
    return "We couldn't reach the sign-in service. Check your connection and try again.";
  }
  return GENERIC_LOGIN_ERROR;
}

/**
 * Sign-in (SCREEN_SPECS): branded, focused and free of public-registration
 * noise. Invitations arrive as direct links from an administrator.
 */
export function LoginPage() {
  const session = useSession();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [authError, setAuthError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const destination = destinationFromState(location.state);

  if (session.status === "SIGNED_IN" && session.user) {
    return <Navigate to={destination} replace />;
  }

  if (session.status === "LOADING") {
    return (
      <AuthLayout eyebrow="Secure access" title="Checking your session" intro="One moment while we restore your workspace.">
        <div className="auth-loading" role="status" aria-live="polite">
          <span className="spinner" aria-hidden="true" />
          <span>Restoring session…</span>
        </div>
      </AuthLayout>
    );
  }

  function validate(): FieldErrors {
    const errors: FieldErrors = {};
    const cleanEmail = email.trim();
    if (!cleanEmail) errors.email = "Enter your email address.";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(cleanEmail)) errors.email = "Enter a valid email address.";
    if (!password) errors.password = "Enter your password.";
    return errors;
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const errors = validate();
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;

    setPending(true);
    setAuthError(null);
    void (async () => {
      try {
        await login(email.trim(), password);
        navigate(destination, { replace: true });
      } catch (error) {
        // Never reveal whether the account exists; do explain throttling and
        // service outages, which are not credential failures.
        setAuthError(loginErrorMessage(error));
        setPending(false);
      }
    })();
  }

  return (
    <AuthLayout
      eyebrow="Welcome back"
      title="Sign in"
      intro="Use the account issued by your organization. There is no public sign-up."
    >
      {authError ? (
        <div className="auth-alert" role="alert">
          <strong>Sign-in failed</strong>
          <span>{authError}</span>
        </div>
      ) : null}

      <form className="auth-form" onSubmit={submit} noValidate>
        <FormField id="login-email" label="Email" required error={fieldErrors.email}>
          {(ids) => (
            <input
              id="login-email"
              type="email"
              inputMode="email"
              autoComplete="email"
              autoFocus
              value={email}
              aria-invalid={fieldErrors.email ? true : undefined}
              aria-describedby={ids.describedBy || undefined}
              onChange={(event) => {
                setEmail(event.target.value);
                if (fieldErrors.email) setFieldErrors((current) => ({ ...current, email: undefined }));
              }}
              disabled={pending}
            />
          )}
        </FormField>

        <FormField id="login-password" label="Password" required error={fieldErrors.password}>
          {(ids) => (
            <div className="password-control">
              <input
                id="login-password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                value={password}
                aria-invalid={fieldErrors.password ? true : undefined}
                aria-describedby={ids.describedBy || undefined}
                onChange={(event) => {
                  setPassword(event.target.value);
                  if (fieldErrors.password) setFieldErrors((current) => ({ ...current, password: undefined }));
                }}
                disabled={pending}
              />
              <button
                type="button"
                className="password-toggle"
                aria-controls="login-password"
                aria-pressed={showPassword}
                onClick={() => setShowPassword((visible) => !visible)}
                disabled={pending}
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
          )}
        </FormField>

        <div className="auth-form-meta">
          <Link to="/reset-password">Forgot password?</Link>
        </div>

        <button type="submit" className="btn auth-submit" disabled={pending}>
          {pending ? (
            <>
              <span className="spinner" aria-hidden="true" /> Signing in…
            </>
          ) : (
            "Sign in"
          )}
        </button>
      </form>

      <p className="auth-help">
        Received an invitation? Open the secure link in your invitation message.
        <br />
        Need access? Contact your distribution administrator.
      </p>

      {pending ? (
        <p role="status" className="sr-only">
          Signing in. Please wait.
        </p>
      ) : null}
    </AuthLayout>
  );
}

/** Only accept an in-app path so a forged history state cannot redirect off-site. */
function destinationFromState(state: unknown): string {
  const from = (state as { from?: unknown } | null)?.from;
  return typeof from === "string" && from.startsWith("/") && !from.startsWith("//") ? from : "/";
}
