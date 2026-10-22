/**
 * Added file (beyond the planned list): tests the shared API client's
 * 401 single-flight refresh + retry behavior and its error parsing. These
 * paths protect against token reuse storms and silent failures.
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, configureAuth, registerRefreshTokenSink, request } from "./api-client";

let holdingToken: string | null = null;
const authLost = vi.fn();

interface FetchCall {
  url: string;
  init: RequestInit;
}

describe("api-client request()", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    holdingToken = null;
    configureAuth({ getToken: () => null, onAuthLost: () => undefined });
    authLost.mockReset();
  });

  function stubFetch(callLog: FetchCall[], plan: (call: FetchCall, index: number) => Response): void {
    const fetchMock = vi.fn(async (input: URL | RequestInfo, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
      const call: FetchCall = { url, init: init ?? {} };
      const index = callLog.length;
      callLog.push(call);
      return plan(call, index);
    });
    vi.stubGlobal("fetch", fetchMock);
    return;
  }

  function json(status: number, body: unknown): Response {
    return new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    });
  }

  it("retries exactly once after a single-flight refresh and uses the rotated token", async () => {
    holdingToken = "stale-token";
    configureAuth({
      getToken: () => holdingToken,
      onAuthLost: authLost,
    });
    registerRefreshTokenSink((token) => {
      holdingToken = token;
    });

    const calls: FetchCall[] = [];
    stubFetch(calls, (call, index) => {
      if (call.url.includes("/auth/refresh")) {
        return json(200, { access_token: "fresh-token", user: {} });
      }
      if (index === 0) {
        return json(401, {
          error: { code: "AUTH_REQUIRED", message: "expired", request_id: "req-1", details: [] },
        });
      }
      return json(200, { ok: true });
    });

    const result = await request<{ ok: boolean }>("GET", "/deliveries");
    expect(result).toEqual({ ok: true });

    const refreshCalls = calls.filter((call) => call.url.includes("/auth/refresh"));
    expect(refreshCalls).toHaveLength(1);
    // Retry carries the rotated token from the in-memory sink.
    const retryHeaders = calls.at(-1)?.init.headers as Record<string, string>;
    expect(retryHeaders.Authorization).toBe("Bearer fresh-token");
    expect(authLost).not.toHaveBeenCalled();
  });

  it("shares a single refresh when two requests 401 concurrently", async () => {
    holdingToken = "stale-token";
    configureAuth({ getToken: () => holdingToken, onAuthLost: authLost });
    registerRefreshTokenSink((token) => {
      holdingToken = token;
    });

    const calls: FetchCall[] = [];
    stubFetch(calls, (call, index) => {
      if (call.url.includes("/auth/refresh")) {
        return json(200, { access_token: "fresh-token", user: {} });
      }
      if (index < 2) {
        return json(401, {
          error: { code: "AUTH_REQUIRED", message: "expired", request_id: "req-2", details: [] },
        });
      }
      return json(200, { ok: index });
    });

    const [first, second] = await Promise.all([
      request<{ ok: number }>("GET", "/deliveries"),
      request<{ ok: number }>("GET", "/settings"),
    ]);

    expect(first).toEqual({ ok: expect.any(Number) });
    expect(second).toEqual({ ok: expect.any(Number) });

    const refreshCalls = calls.filter((call) => call.url.includes("/auth/refresh"));
    expect(refreshCalls).toHaveLength(1);
    expect(authLost).not.toHaveBeenCalled();
  });

  it("invokes onAuthLost when the refresh rotation fails", async () => {
    holdingToken = "expired-token";
    configureAuth({ getToken: () => holdingToken, onAuthLost: authLost });

    const calls: FetchCall[] = [];
    stubFetch(calls, (call) => {
      if (call.url.includes("/auth/refresh")) {
        return json(401, {
          error: { code: "AUTH_REQUIRED", message: "no session", request_id: "req-3", details: [] },
        });
      }
      return json(401, {
        error: { code: "AUTH_REQUIRED", message: "expired", request_id: "req-3", details: [] },
      });
    });

    await expect(request("GET", "/deliveries")).rejects.toThrow("expired");
    expect(authLost).toHaveBeenCalledTimes(1);
    // No retry happened without a successful refresh.
    expect(calls).toHaveLength(2);
  });

  it("parses the error envelope into ApiError fields", async () => {
    configureAuth({ getToken: () => null, onAuthLost: authLost });
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
