/**
 * Forgot password — request a reset link by email.
 */

import React, { useState } from "react";
import Head from "next/head";
import Link from "next/link";
import { auth as authApi } from "@/lib/api";

export default function ForgotPasswordPage() {
    const [email, setEmail] = useState("");
    const [submitting, setSubmitting] = useState(false);
    const [sent, setSent] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setSubmitting(true);
        try {
            await authApi.forgotPassword(email);
            // The API deliberately doesn't say whether the address exists, so
            // the UI mustn't either.
            setSent(true);
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Couldn't send the reset link. Try again.",
            );
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <>
            <Head>
                <title>Forgot password — Exyst</title>
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
                                margin: "0 0 8px",
                                textAlign: "center",
                            }}
                        >
                            EXYST
                        </h1>
                    </Link>

                    {sent ? (
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
                                If <strong>{email}</strong> has an account, a reset link is on
                                its way. The link expires in an hour.
                            </p>
                            <Link
                                href="/login"
                                className="btn-primary"
                                style={{
                                    display: "block",
                                    textAlign: "center",
                                    marginTop: 24,
                                    textDecoration: "none",
                                }}
                            >
                                Back to sign in
                            </Link>
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
                                Enter your email and we&apos;ll send you a link to choose a new
                                password.
                            </p>

                            <label
                                htmlFor="email"
                                style={{
                                    display: "block",
                                    fontSize: "0.8rem",
                                    fontWeight: 600,
                                    color: "var(--text-secondary)",
                                    marginBottom: 6,
                                }}
                            >
                                Email
                            </label>
                            <input
                                id="email"
                                type="email"
                                className="input-field"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                required
                                autoComplete="email"
                                style={{ width: "100%" }}
                            />

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
                                    {error}
                                </div>
                            )}

                            <button
                                type="submit"
                                className="btn-primary"
                                disabled={submitting || !email}
                                style={{ width: "100%", marginTop: 20 }}
                            >
                                {submitting ? "Sending…" : "Send reset link"}
                            </button>

                            <p
                                style={{
                                    marginTop: 20,
                                    textAlign: "center",
                                    fontSize: "0.8rem",
                                    color: "var(--text-muted)",
                                }}
                            >
                                <Link
                                    href="/login"
                                    style={{ color: "var(--accent-indigo)" }}
                                >
                                    Back to sign in
                                </Link>
                            </p>
                        </form>
                    )}
                </div>
            </div>
        </>
    );
}
