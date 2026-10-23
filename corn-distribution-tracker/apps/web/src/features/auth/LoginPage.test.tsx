/**
 * Sign-in failure messaging.
 *
 * Credential failures stay deliberately generic (no account enumeration), but
 * throttling and API outages must tell the user what actually happened so a
 * correct password is not reported as wrong.
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { ApiError } from "../../lib/api-client";

const { loginMock } = vi.hoisted(() => ({ loginMock: vi.fn() }));

vi.mock("../../lib/session", () => ({
  login: loginMock,
  useSession: () => ({ status: "SIGNED_OUT", user: null }),
}));

import { LoginPage, loginErrorMessage } from "./LoginPage";

afterEach(() => {
  cleanup();
  loginMock.mockReset();
});

describe("loginErrorMessage", () => {
  it("keeps credential failures generic", () => {
    const message = loginErrorMessage(
      new ApiError(401, "UNAUTHENTICATED", "Invalid email or password.", "req-1"),
    );
    expect(message).toContain("Email or password is incorrect");
    expect(message).not.toContain("Invalid email or password.");
  });

  it("explains a rate limit with the server's retry window", () => {
    const message = loginErrorMessage(
      new ApiError(429, "RATE_LIMITED", "Too many attempts; try again later.", "req-2", [
        { retry_after: 237 },
      ]),
    );
    expect(message).toBe("Too many sign-in attempts. Try again in 4 minutes.");
  });

  it("explains a brief rate limit in seconds", () => {
    const message = loginErrorMessage(
      new ApiError(429, "RATE_LIMITED", "Too many attempts; try again later.", "req-3", [
        { retry_after: 42 },
      ]),
    );
    expect(message).toBe("Too many sign-in attempts. Try again in 42 seconds.");
  });

  it("distinguishes an unavailable API from a wrong password", () => {
    expect(loginErrorMessage(new TypeError("Failed to fetch"))).toContain(
      "couldn't reach the sign-in service",
    );
    expect(loginErrorMessage(new ApiError(503, "INTERNAL_ERROR", "Unavailable.", "req-4"))).toContain(
      "temporarily unavailable",
    );
  });
});

describe("LoginPage", () => {
  it("shows the rate-limit message instead of blaming the password", async () => {
    loginMock.mockRejectedValueOnce(
      new ApiError(429, "RATE_LIMITED", "Too many attempts; try again later.", "req-5", [
        { retry_after: 120 },
      ]),
    );

    render(
      <MemoryRouter initialEntries={["/login"]}>
        <LoginPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "admin@example.org" },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: "AdminLocal!2026" },
    });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Sign-in failed");
    expect(alert).toHaveTextContent("Too many sign-in attempts. Try again in 2 minutes.");
    expect(alert).not.toHaveTextContent("Email or password is incorrect");
  });
});
