/**
 * Reset password — set a new password using the token from the emailed link.
 */

import React, { useState } from "react";
import Head from "next/head";
import Link from "next/link";
import { useRouter } from "next/router";
import { auth as authApi } from "@/lib/api";

export default function ResetPasswordPage() {
    const router = useRouter();
    const token = typeof router.query.token === "string" ? router.query.token : "";

    const [password, setPassword] = useState("");
    const [confirm, setConfirm] = useState("");
    const [submitting, setSubmitting] = useState(false);
    const [done, setDone] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const mismatch = confirm.length > 0 && password !== confirm;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (password !== confirm) {
            setError("The two passwords don't match.");
            return;
        }
        setError(null);
        setSubmitting(true);
        try {
            await authApi.resetPassword(token, password);
            setDone(true);
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "This reset link is invalid or has expired.",
            );
        } finally {
            setSubmitting(false);
        }
    };

    // router.query is empty on the first render; don't flash "invalid link".
    if (!router.isReady) return null;

    return (
        <>
            <Head>
                <title>Reset password — Exyst</title>
            </Head>

            <div
                style={{
                    minHeight: "100vh",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    padding: 20,
                    background: "var(--bg-primary)",
                }}
            >
                <div
                    className="glass-card animate-fade-in"
                    style={{ width: "100%", maxWidth: 400, padding: 32 }}
                >
                    <Link href="/" style={{ textDecoration: "none" }}>
                        <h1
                            className="text-gradient"
                            style={{
                                fontSize: "1.75rem",
                                fontWeight: 900,
                                margin: "0 0 20px",
                                textAlign: "center",
                            }}
                        >
                            EXYST
                        </h1>
                    </Link>

                    {!token ? (
                        <>
                            <p
                                role="alert"
                                style={{
                                    color: "var(--text-secondary)",
                                    fontSize: "0.9rem",
                                    textAlign: "center",
                                    lineHeight: 1.6,
                                }}
                            >
                                This reset link is missing its token. Request a new one.
                            </p>
                            <Link
                                href="/forgot-password"
                                className="btn-primary"
                                style={{
                                    display: "block",
                                    textAlign: "center",
                                    marginTop: 24,
                                    textDecoration: "none",
                                }}
                            >
                                Request a new link
                            </Link>
                        </>
                    ) : done ? (
                        <>
                            <p
                                role="status"
                                style={{
                                    color: "var(--text-secondary)",
                                    fontSize: "0.9rem",
                                    textAlign: "center",
                                    lineHeight: 1.6,
                                }}
                            >
                                Your password has been reset, and every device has been signed
                                out. Sign in with your new password.
                            </p>
                            <button
                                className="btn-primary"
                                onClick={() => router.push("/login")}
                                style={{ width: "100%", marginTop: 24 }}
                            >
                                Sign in
                            </button>
                        </>
                    ) : (
                        <form onSubmit={handleSubmit}>
                            <p
                                style={{
                                    color: "var(--text-muted)",
                                    fontSize: "0.85rem",
                                    textAlign: "center",
                                    margin: "0 0 24px",
                                }}
                            >
                                Choose a new password for your account.
                            </p>

                            <label
                                htmlFor="password"
                                style={{
                                    display: "block",
                                    fontSize: "0.8rem",
                                    fontWeight: 600,
                                    color: "var(--text-secondary)",
                                    marginBottom: 6,
                                }}
                            >
                                New password
                            </label>
                            <input
                                id="password"
                                type="password"
                                className="input-field"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
                                minLength={8}
                                autoComplete="new-password"
                                style={{ width: "100%", marginBottom: 16 }}
                            />

                            <label
                                htmlFor="confirm"
                                style={{
                                    display: "block",
                                    fontSize: "0.8rem",
                                    fontWeight: 600,
                                    color: "var(--text-secondary)",
                                    marginBottom: 6,
                                }}
                            >
                                Confirm new password
                            </label>
                            <input
                                id="confirm"
                                type="password"
                                className="input-field"
                                value={confirm}
                                onChange={(e) => setConfirm(e.target.value)}
                                required
                                minLength={8}
                                autoComplete="new-password"
                                aria-invalid={mismatch}
                                style={{ width: "100%" }}
                            />
                            {mismatch && (
                                <p
                                    style={{
                                        margin: "6px 0 0",
                                        fontSize: "0.7rem",
                                        color: "#ef4444",
                                    }}
                                >
                                    The two passwords don&apos;t match.
                                </p>
                            )}

                            {error && (
                                <div
                                    role="alert"
                                    style={{
                                        marginTop: 16,
                                        padding: "10px 14px",
                                        borderRadius: "var(--radius-sm)",
                                        background: "rgba(239, 68, 68, 0.1)",
                                        border: "1px solid rgba(239, 68, 68, 0.2)",
                                        color: "#ef4444",
                                        fontSize: "0.8rem",
                                    }}
                                >
                                    {error}{" "}
                                    <Link
                                        href="/forgot-password"
                                        style={{ color: "#ef4444", fontWeight: 600 }}
                                    >
                                        Request a new link
                                    </Link>
                                </div>
                            )}

                            <button
                                type="submit"
                                className="btn-primary"
                                disabled={submitting || password.length < 8 || mismatch}
                                style={{ width: "100%", marginTop: 20 }}
                            >
                                {submitting ? "Resetting…" : "Reset password"}
                            </button>
                        </form>
                    )}
                </div>
            </div>
        </>
    );
}
