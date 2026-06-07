/**
 * Login / Register page with animated design.
 */

import React, { useState } from "react";
import Head from "next/head";
import { useRouter } from "next/router";
import { useAuth } from "@/lib/auth-context";

export default function LoginPage() {
  const router = useRouter();
  const { login, register } = useAuth();
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (isRegister) {
        await register(email, password, name);
      } else {
        await login(email, password);
      }
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Head>
        <title>{isRegister ? "Register" : "Login"} — Exyst</title>
        <meta name="description" content="Sign in to Exyst AI-powered exam intelligence platform" />
      </Head>

      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "var(--bg-primary)",
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* Background decoration */}
        <div
          style={{
            position: "absolute",
            width: 500,
            height: 500,
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(99,102,241,0.15) 0%, transparent 70%)",
            top: "-10%",
            right: "-10%",
          }}
        />
        <div
          style={{
            position: "absolute",
            width: 400,
            height: 400,
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(139,92,246,0.1) 0%, transparent 70%)",
            bottom: "-10%",
            left: "-5%",
          }}
        />

        <div className="animate-scale-in" style={{ width: "100%", maxWidth: 420, padding: 24, position: "relative", zIndex: 10 }}>
          {/* Logo */}
          <div style={{ textAlign: "center", marginBottom: 48 }}>
            <h1
              className="text-gradient"
              style={{
                fontSize: "3rem",
                fontWeight: 900,
                letterSpacing: "-0.03em",
                margin: 0,
              }}
            >
              EXYST
            </h1>
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginTop: 8 }}>
              AI-Powered Exam Intelligence
            </p>
          </div>

          {/* Card */}
          <div
            className="glass-card"
            style={{ padding: 32 }}
          >
            <h2
              style={{
                fontSize: "1.25rem",
                fontWeight: 700,
                marginBottom: 4,
                color: "var(--text-primary)",
              }}
            >
              {isRegister ? "Create Account" : "Welcome Back"}
            </h2>
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginBottom: 28 }}>
              {isRegister
                ? "Start predicting exam questions with AI"
                : "Sign in to your account"}
            </p>

            <form onSubmit={handleSubmit}>
              {isRegister && (
                <div style={{ marginBottom: 16 }}>
                  <label
                    style={{
                      display: "block",
                      color: "var(--text-secondary)",
                      fontSize: "0.8rem",
                      fontWeight: 500,
                      marginBottom: 6,
                    }}
                  >
                    Name
                  </label>
                  <input
                    className="input-field"
                    type="text"
                    placeholder="Your name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                  />
                </div>
              )}

              <div style={{ marginBottom: 16 }}>
                <label
                  style={{
                    display: "block",
                    color: "var(--text-secondary)",
                    fontSize: "0.8rem",
                    fontWeight: 500,
                    marginBottom: 6,
                  }}
                >
                  Email
                </label>
                <input
                  className="input-field"
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>

              <div style={{ marginBottom: 24 }}>
                <label
                  style={{
                    display: "block",
                    color: "var(--text-secondary)",
                    fontSize: "0.8rem",
                    fontWeight: 500,
                    marginBottom: 6,
                  }}
                >
                  Password
                </label>
                <input
                  className="input-field"
                  type="password"
                  placeholder="Minimum 8 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  minLength={8}
                  required
                />
              </div>

              {error && (
                <div
                  style={{
                    padding: "10px 14px",
                    borderRadius: "var(--radius-sm)",
                    background: "rgba(239, 68, 68, 0.1)",
                    border: "1px solid rgba(239, 68, 68, 0.2)",
                    color: "#ef4444",
                    fontSize: "0.8rem",
                    marginBottom: 16,
                  }}
                >
                  {error}
                </div>
              )}

              <button
                type="submit"
                className="btn-primary"
                disabled={loading}
                style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}
              >
                {loading && <span className="spinner" style={{ width: 18, height: 18 }} />}
                {isRegister ? "Create Account" : "Sign In"}
              </button>
            </form>

            <div style={{ textAlign: "center", marginTop: 24 }}>
              <button
                onClick={() => {
                  setIsRegister(!isRegister);
                  setError("");
                }}
                style={{
                  background: "none",
                  border: "none",
                  color: "var(--accent-indigo)",
                  cursor: "pointer",
                  fontSize: "0.85rem",
                  fontWeight: 500,
                }}
              >
                {isRegister
                  ? "Already have an account? Sign in"
                  : "Don't have an account? Register"}
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
