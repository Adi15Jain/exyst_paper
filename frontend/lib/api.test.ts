/**
 * Tests for the API client: auth token storage, header injection,
 * 401 -> refresh -> retry, and error normalization.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { auth, clearTokens, getAccessToken, setTokens } from "./api";

function jsonResponse(body: unknown, status = 200) {
    return {
        ok: status >= 200 && status < 300,
        status,
        json: async () => body,
    } as Response;
}

describe("api client", () => {
    beforeEach(() => {
        clearTokens();
        vi.restoreAllMocks();
    });

    afterEach(() => {
        clearTokens();
    });

    it("login stores the returned tokens", async () => {
        const fetchMock = vi
            .fn()
            .mockResolvedValue(
                jsonResponse({
                    access_token: "acc-1",
                    refresh_token: "ref-1",
                    token_type: "bearer",
                }),
            );
        vi.stubGlobal("fetch", fetchMock);

        const data = await auth.login("a@b.com", "password123");
        expect(data.access_token).toBe("acc-1");
        expect(getAccessToken()).toBe("acc-1");
    });

    it("attaches the Authorization header when a token is set", async () => {
        setTokens("acc-1", "ref-1");
        const fetchMock = vi
            .fn()
            .mockResolvedValue(jsonResponse({ id: "u1", email: "a@b.com", name: "A" }));
        vi.stubGlobal("fetch", fetchMock);

        await auth.me();

        const [, init] = fetchMock.mock.calls[0];
        expect(init.headers["Authorization"]).toBe("Bearer acc-1");
    });

    it("normalizes error responses into a thrown Error message", async () => {
        setTokens("acc-1", "ref-1");
        const fetchMock = vi
            .fn()
            .mockResolvedValue(jsonResponse({ message: "Boom happened" }, 422));
        vi.stubGlobal("fetch", fetchMock);

        await expect(auth.me()).rejects.toThrow("Boom happened");
    });

    it("refreshes and retries once on 401, using the rotated token", async () => {
        setTokens("stale-access", "ref-1");

        const fetchMock = vi.fn(async (url: string) => {
            if (url.endsWith("/auth/refresh")) {
                return jsonResponse({
                    access_token: "fresh-access",
                    refresh_token: "ref-2",
                });
            }
            // First /auth/me uses the stale token -> 401; second uses fresh -> 200.
            if (getAccessToken() === "stale-access") {
                return jsonResponse({ message: "expired" }, 401);
            }
            return jsonResponse({ id: "u1", email: "a@b.com", name: "A" });
        });
        vi.stubGlobal("fetch", fetchMock);

        const me = await auth.me();
        expect(me.email).toBe("a@b.com");
        expect(getAccessToken()).toBe("fresh-access");

        // refresh endpoint was called exactly once
        const refreshCalls = fetchMock.mock.calls.filter((c) =>
            String(c[0]).endsWith("/auth/refresh"),
        );
        expect(refreshCalls).toHaveLength(1);
    });
});
