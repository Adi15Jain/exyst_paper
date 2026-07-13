/**
 * Tests for the API client: auth token storage, header injection,
 * 401 -> cookie refresh -> retry, session restore, and error normalization.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { auth, clearAccessToken, getAccessToken, setAccessToken } from "./api";

function jsonResponse(body: unknown, status = 200) {
    return {
        ok: status >= 200 && status < 300,
        status,
        json: async () => body,
    } as Response;
}

describe("api client", () => {
    beforeEach(() => {
        clearAccessToken();
        vi.restoreAllMocks();
    });

    afterEach(() => {
        clearAccessToken();
    });

    it("login stores the access token in memory and sends credentials", async () => {
        const fetchMock = vi.fn().mockResolvedValue(
            jsonResponse({
                access_token: "acc-1",
                refresh_token: null,
                token_type: "bearer",
            }),
        );
        vi.stubGlobal("fetch", fetchMock);

        const data = await auth.login("a@b.com", "password123");
        expect(data.access_token).toBe("acc-1");
        expect(getAccessToken()).toBe("acc-1");

        // The refresh cookie is set by the server; the request must opt in.
        const [, init] = fetchMock.mock.calls[0];
        expect(init.credentials).toBe("include");
    });

    it("attaches the Authorization header when a token is set", async () => {
        setAccessToken("acc-1");
        const fetchMock = vi
            .fn()
            .mockResolvedValue(jsonResponse({ id: "u1", email: "a@b.com", name: "A" }));
        vi.stubGlobal("fetch", fetchMock);

        await auth.me();

        const [, init] = fetchMock.mock.calls[0];
        expect(init.headers["Authorization"]).toBe("Bearer acc-1");
    });

    it("normalizes error responses into a thrown Error message", async () => {
        setAccessToken("acc-1");
        const fetchMock = vi
            .fn()
            .mockResolvedValue(jsonResponse({ message: "Boom happened" }, 422));
        vi.stubGlobal("fetch", fetchMock);

        await expect(auth.me()).rejects.toThrow("Boom happened");
    });

    it("refreshes via cookie and retries once on 401", async () => {
        setAccessToken("stale-access");

        const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
            if (String(url).endsWith("/auth/refresh")) {
                // Cookie-based refresh: no body, credentials included.
                expect(init?.credentials).toBe("include");
                return jsonResponse({
                    access_token: "fresh-access",
                    refresh_token: null,
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

    it("restore returns the user when the refresh cookie is valid", async () => {
        const fetchMock = vi.fn(async (url: string) => {
            if (String(url).endsWith("/auth/refresh")) {
                return jsonResponse({ access_token: "acc-2", refresh_token: null });
            }
            return jsonResponse({ id: "u1", email: "a@b.com", name: "A" });
        });
        vi.stubGlobal("fetch", fetchMock);

        const user = await auth.restore();
        expect(user?.email).toBe("a@b.com");
        expect(getAccessToken()).toBe("acc-2");
    });

    it("restore resolves null when there is no valid session", async () => {
        const fetchMock = vi
            .fn()
            .mockResolvedValue(jsonResponse({ message: "no session" }, 401));
        vi.stubGlobal("fetch", fetchMock);

        const user = await auth.restore();
        expect(user).toBeNull();
        expect(getAccessToken()).toBeNull();
    });

    it("logout calls the revocation endpoint and clears the access token", async () => {
        setAccessToken("acc-1");
        const fetchMock = vi.fn().mockResolvedValue(jsonResponse(null, 204));
        vi.stubGlobal("fetch", fetchMock);

        await auth.logout();

        expect(getAccessToken()).toBeNull();
        const [url, init] = fetchMock.mock.calls[0];
        expect(String(url).endsWith("/auth/logout")).toBe(true);
        expect(init.credentials).toBe("include");
    });

    it("logout clears the access token even if the request fails", async () => {
        setAccessToken("acc-1");
        vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));

        await auth.logout();
        expect(getAccessToken()).toBeNull();
    });
});
