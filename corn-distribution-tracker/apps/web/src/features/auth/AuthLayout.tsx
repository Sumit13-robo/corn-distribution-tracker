import type { ReactNode } from "react";

/**
 * Shared public-auth frame (login, invitation, reset and password-change).
 *
 * The left panel explains the product without marketing theatre; the right
 * panel stays a focused form. On narrow screens the panel collapses to a slim
 * wordmark so the form remains above the fold at 360 px.
 */
export function AuthLayout({
  eyebrow,
  title,
  intro,
  children,
}: {
  eyebrow: string;
  title: string;
  intro?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="auth-shell">
      <aside className="auth-brand" aria-label="About Corn Distribution Tracker">
        <div className="auth-wordmark">
          <BrandMark />
          <div>
            <strong>Corn Distribution Tracker</strong>
            <small>Field-to-ledger accountability</small>
          </div>
        </div>

        <div className="auth-message">
          <p className="auth-kicker">Agricultural operations</p>
          <h2>Every kilogram accounted for, from field to store.</h2>
          <p>
            Plan targets, record stock movements and review deliveries with private evidence — all against one
            append-only ledger.
          </p>
          <ul className="auth-points">
            <li>Private photo evidence with short-lived access</li>
            <li>Clear approval steps and immutable stock history</li>
            <li>Field-ready drafts that sync when connectivity returns</li>
          </ul>
        </div>

        <p className="auth-brand-note">Authorized accounts only. No public registration.</p>
      </aside>

      <main className="auth-form-panel">
        <div className="auth-card">
          <div className="auth-mobile-mark">
            <BrandMark />
            <span>Corn Distribution Tracker</span>
          </div>
          <p className="auth-eyebrow">{eyebrow}</p>
          <h1>{title}</h1>
          {intro ? <p className="auth-intro">{intro}</p> : null}
          {children}
        </div>
        <p className="auth-privacy">Sessions are protected with an HttpOnly cookie. Photos stay private.</p>
      </main>
    </div>
  );
}

export function BrandMark() {
  return (
    <span className="brand-mark" aria-hidden="true">
      <svg viewBox="0 0 32 32" focusable="false">
        <path d="M16 3c3.2 4.1 4.9 7.3 4.9 10.4 0 3.1-2 5.4-4.9 7.1-2.9-1.7-4.9-4-4.9-7.1C11.1 10.3 12.8 7.1 16 3Z" />
        <path d="M8.6 14.7c1.5 4.9 4.3 8.3 8.4 10.3-5.1 1.1-9.1-1-11.1-4.2.9-2.2 1.8-4.2 2.7-6.1Z" opacity=".82" />
        <path d="M23.4 14.7c-1.5 4.9-4.3 8.3-8.4 10.3 5.1 1.1 9.1-1 11.1-4.2-.9-2.2-1.8-4.2-2.7-6.1Z" opacity=".62" />
      </svg>
    </span>
  );
}
