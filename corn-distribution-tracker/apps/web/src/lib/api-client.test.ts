/**
 * Tests for the session/CSRF-aware API client.
 *
 * The client must never attach bearer tokens: authentication lives in the
 * Django HttpOnly session cookie, while unsafe requests carry X-CSRFToken.
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  ApiError,
  configureAuth,
  request,
  setCsrfToken,
  uploadBlob,
} from "./api-client";

interface FetchCall {
  url: string;
  init: RequestInit;
}

const authLost = vi.fn();

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function stubFetch(callLog: FetchCall[], plan: (call: FetchCall, index: number) => Response): void {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: URL | RequestInfo, init?: RequestInit) => {
      const url =
        typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
      const call: FetchCall = { url, init: init ?? {} };
      const index = callLog.length;
      callLog.push(call);
      return plan(call, index);
    }),
  );
}

function clearCookies(): void {
  for (const part of document.cookie.split(";")) {
    const name = part.split("=")[0]?.trim();
    if (name) document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`;
  }
}

function setCookie(name: string, value: string): void {
  document.cookie = `${name}=${encodeURIComponent(value)}; path=/`;
}

describe("api-client request()", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    clearCookies();
    setCsrfToken(null);
    authLost.mockReset();
    configureAuth({ onAuthLost: () => undefined });
  });

  it("sends the session cookie and no bearer token", async () => {
    const calls: FetchCall[] = [];
    stubFetch(calls, () => json(200, { ok: true }));
    await request("GET", "/inventory/summary");
    expect(calls).toHaveLength(1);
    expect(calls[0]?.init.credentials).toBe("include");
    const headers = calls[0]?.init.headers as Record<string, string>;
    expect(headers.Authorization).toBeUndefined();
    expect(headers["X-CSRFToken"]).toBeUndefined();
  });

  it("attaches X-CSRFToken on unsafe methods from the Django cookie", async () => {
    setCookie("csrftoken", "csrf-value-1");
    const calls: FetchCall[] = [];
    stubFetch(calls, () => json(201, { id: "record-1" }));
    await request("POST", "/deliveries", { body: { quantity: "10" } });
    const headers = calls[0]?.init.headers as Record<string, string>;
    expect(headers["X-CSRFToken"]).toBe("csrf-value-1");
    expect(headers["Content-Type"]).toBe("application/json");
    expect(headers.Authorization).toBeUndefined();
  });

  it("fetches a CSRF token from /auth/csrf when the cookie is unreadable", async () => {
    const calls: FetchCall[] = [];
    stubFetch(calls, (call) => {
      if (call.url.includes("/auth/csrf")) {
        return json(200, { csrf_token: "cross-origin-token" });
      }
      return json(200, { ok: true });
    });
    await request("PATCH", "/settings", { body: { timezone: "UTC" } });
    expect(calls).toHaveLength(2);
    expect(calls[0]?.url).toContain("/auth/csrf");
    const headers = calls[1]?.init.headers as Record<string, string>;
    expect(headers["X-CSRFToken"]).toBe("cross-origin-token");
    expect(calls[0]?.init.credentials).toBe("include");
  });

  it("clears the session once on a 401 without retrying or refreshing", async () => {
    configureAuth({ onAuthLost: authLost });
    const calls: FetchCall[] = [];
    stubFetch(calls, () =>
      json(401, {
        error: {
          code: "UNAUTHENTICATED",
          message: "Authentication required.",
          request_id: "req-1",
          details: [],
        },
      }),
    );
    await expect(request("GET", "/deliveries")).rejects.toThrow("Authentication required.");
    expect(authLost).toHaveBeenCalledTimes(1);
    expect(calls).toHaveLength(1);
  });

  it("does not call onAuthLost for a login failure", async () => {
    configureAuth({ onAuthLost: authLost });
    const calls: FetchCall[] = [];
    stubFetch(calls, () =>
      json(401, {
        error: { code: "UNAUTHENTICATED", message: "Invalid credentials.", request_id: "r", details: [] },
      }),
    );
    await expect(request("POST", "/auth/login", { body: { email: "x@example.org", password: "nope" } })).rejects.toThrow(
      "Invalid credentials.",
    );
    expect(authLost).not.toHaveBeenCalled();
  });

  it("parses the error envelope into ApiError fields", async () => {
    const calls: FetchCall[] = [];
    stubFetch(calls, () =>
      json(409, {
        error: {
          code: "INSUFFICIENT_STOCK",
          message: "Not enough central stock.",
          request_id: "req-4",
          details: [{ field: "quantity_kg" }],
        },
      }),
    );

    const error = await request("GET", "/inventory/summary").catch((caught: unknown) => caught);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 409,
      code: "INSUFFICIENT_STOCK",
      message: "Not enough central stock.",
      requestId: "req-4",
      details: [{ field: "quantity_kg" }],
    });
  });
});

describe("uploadBlob()", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    clearCookies();
    setCsrfToken(null);
  });

  it("uses credentials plus CSRF for the local API upload endpoint", async () => {
    setCookie("csrftoken", "upload-csrf");
    const calls: FetchCall[] = [];
    stubFetch(calls, () => new Response(null, { status: 204 }));
    await uploadBlob(
      { upload_url: "/api/v1/evidence/objects/00000000-0000-0000-0000-000000000000", headers: {} },
      new Blob([new Uint8Array([1, 2, 3])], { type: "image/png" }),
    );
    expect(calls).toHaveLength(1);
    expect(calls[0]?.init.credentials).toBe("include");
    const headers = calls[0]?.init.headers as Record<string, string>;
    expect(headers["X-CSRFToken"]).toBe("upload-csrf");
  });

  it("does not send cookies or CSRF to a presigned object-storage URL", async () => {
    setCookie("csrftoken", "upload-csrf");
    const calls: FetchCall[] = [];
    stubFetch(calls, () => new Response(null, { status: 200 }));
    await uploadBlob(
      {
        upload_url: "https://objects.example.test/private/evidence?X-Amz-Signature=abc",
        headers: { "Content-Type": "image/png" },
      },
      new Blob([new Uint8Array([1, 2, 3])], { type: "image/png" }),
    );
    expect(calls).toHaveLength(1);
    expect(calls[0]?.init.credentials).toBe("omit");
    const headers = calls[0]?.init.headers as Record<string, string>;
    expect(headers["X-CSRFToken"]).toBeUndefined();
    expect(headers.Authorization).toBeUndefined();
  });
});
