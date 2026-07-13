/**
 * Landing page — hero section with animated design.
 * Redirects to dashboard if already authenticated.
 */

import React, { useEffect } from "react";
import Head from "next/head";
import { useRouter } from "next/router";
import { useAuth } from "@/lib/auth-context";

export default function LandingPage() {
    const router = useRouter();
    const { user, loading } = useAuth();

    useEffect(() => {
        if (!loading && user) {
            router.push("/dashboard");
        }
    }, [user, loading, router]);

    return (
        <>
            <Head>
                <title>Exyst — AI-Powered Exam Intelligence Platform</title>
                <meta
                    name="description"
                    content="Analyze university syllabi and historical question papers to predict future exam questions with AI-powered confidence scoring."
                />
            </Head>

            <div
                style={{
                    minHeight: "100vh",
                    background: "var(--bg-primary)",
                    position: "relative",
                    overflow: "hidden",
                }}
            >
                {/* Animated Background Orbs */}
                <div
                    className="animate-float"
                    style={{
                        position: "absolute",
                        width: 600,
                        height: 600,
                        borderRadius: "50%",
                        background:
                            "radial-gradient(circle, rgba(99,102,241,0.12) 0%, transparent 70%)",
                        top: "-15%",
                        right: "-10%",
                        filter: "blur(40px)",
                    }}
                />
                <div
                    className="animate-float"
                    style={{
                        position: "absolute",
                        width: 500,
                        height: 500,
                        borderRadius: "50%",
                        background:
                            "radial-gradient(circle, rgba(139,92,246,0.1) 0%, transparent 70%)",
                        bottom: "-10%",
                        left: "-5%",
                        filter: "blur(40px)",
                        animationDelay: "2s",
                    }}
                />
                <div
                    style={{
                        position: "absolute",
                        width: 300,
                        height: 300,
                        borderRadius: "50%",
                        background:
                            "radial-gradient(circle, rgba(34,211,238,0.08) 0%, transparent 70%)",
                        top: "40%",
                        left: "30%",
                        filter: "blur(60px)",
                    }}
                />

                {/* Nav */}
                <nav
                    className="glass"
                    style={{
                        position: "fixed",
                        top: 0,
                        left: 0,
                        right: 0,
                        zIndex: 50,
                        padding: "16px 32px",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                    }}
                >
                    <h1
                        className="text-gradient"
                        style={{
                            fontSize: "1.3rem",
                            fontWeight: 900,
                            margin: 0,
                            letterSpacing: "-0.02em",
                        }}
                    >
                        EXYST
                    </h1>
                    <div style={{ display: "flex", gap: 12 }}>
                        <button
                            className="btn-secondary"
                            onClick={() => router.push("/login")}
                            style={{ padding: "8px 20px", fontSize: "0.8rem" }}
                        >
                            Sign In
                        </button>
                        <button
                            className="btn-primary"
                            onClick={() => router.push("/login")}
                            style={{ padding: "8px 20px", fontSize: "0.8rem" }}
                        >
                            Get Started
                        </button>
                    </div>
                </nav>

                {/* Hero Content */}
                <div
                    style={{
                        position: "relative",
                        zIndex: 10,
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        justifyContent: "center",
                        minHeight: "100vh",
                        textAlign: "center",
                        padding: "0 24px",
                    }}
                >
                    <div className="animate-fade-in" style={{ maxWidth: 720 }}>
                        {/* Badge */}
                        <div
                            className="badge badge-info animate-scale-in"
                            style={{
                                marginBottom: 24,
                                fontSize: "0.75rem",
                                padding: "6px 16px",
                            }}
                        >
                            ✨ AI-Powered Exam Intelligence
                        </div>

                        {/* Title */}
                        <h1
                            style={{
                                fontSize: "clamp(2.5rem, 5vw, 4rem)",
                                fontWeight: 900,
                                lineHeight: 1.1,
                                margin: "0 0 20px",
                                letterSpacing: "-0.03em",
                            }}
                        >
                            Predict Your Next{" "}
                            <span className="text-gradient">
                                Exam Questions
                            </span>{" "}
                            With AI
                        </h1>

                        {/* Subtitle */}
                        <p
                            className="animate-fade-in stagger-2"
                            style={{
                                fontSize: "1.1rem",
                                color: "var(--text-secondary)",
                                lineHeight: 1.6,
                                margin: "0 0 36px",
                                maxWidth: 560,
                                marginLeft: "auto",
                                marginRight: "auto",
                                opacity: 0,
                            }}
                        >
                            Upload your syllabus and past question papers. Our
                            AI analyzes topic frequency, detects trends, and
                            generates predicted papers with confidence scoring.
                        </p>

                        {/* CTA Buttons */}
                        <div
                            className="animate-fade-in stagger-3"
                            style={{
                                display: "flex",
                                gap: 16,
                                justifyContent: "center",
                                opacity: 0,
                            }}
                        >
                            <button
                                className="btn-primary"
                                onClick={() => router.push("/login")}
                                style={{
                                    padding: "14px 32px",
                                    fontSize: "0.95rem",
                                }}
                            >
                                🚀 Get Started — Free
                            </button>
                            <button
                                className="btn-secondary"
                                onClick={() => {
                                    const el =
                                        document.getElementById("features");
                                    el?.scrollIntoView({ behavior: "smooth" });
                                }}
                                style={{
                                    padding: "14px 32px",
                                    fontSize: "0.95rem",
                                }}
                            >
                                Learn More ↓
                            </button>
                        </div>
                    </div>
                </div>

                {/* Features Section */}
                <div
                    id="features"
                    style={{
                        position: "relative",
                        zIndex: 10,
                        padding: "80px 24px 100px",
                        maxWidth: 1000,
                        margin: "0 auto",
                    }}
                >
                    <h2
                        style={{
                            textAlign: "center",
                            fontSize: "2rem",
                            fontWeight: 800,
                            marginBottom: 12,
                            letterSpacing: "-0.02em",
                        }}
                    >
                        How It Works
                    </h2>
                    <p
                        style={{
                            textAlign: "center",
                            color: "var(--text-muted)",
                            fontSize: "0.95rem",
                            marginBottom: 48,
                        }}
                    >
                        Three steps to smarter exam preparation
                    </p>

                    <div
                        style={{
                            display: "grid",
                            gridTemplateColumns:
                                "repeat(auto-fit, minmax(280px, 1fr))",
                            gap: 24,
                        }}
                    >
                        <FeatureCard
                            icon="📤"
                            title="1. Upload"
                            description="Drop your combined PDF — syllabus and past question papers. Our AI automatically classifies each page."
                        />
                        <FeatureCard
                            icon="🧠"
                            title="2. Analyze"
                            description="LLM-powered analysis extracts topics, detects frequency patterns, and identifies rising trends across papers."
                        />
                        <FeatureCard
                            icon="🎯"
                            title="3. Predict"
                            description="Get a complete predicted question paper with per-question confidence scores and topic coverage analysis."
                        />
                    </div>
                </div>

                {/* Tech Banner */}
                <div
                    style={{
                        position: "relative",
                        zIndex: 10,
                        padding: "40px 24px 80px",
                        textAlign: "center",
                    }}
                >
                    <p
                        style={{
                            color: "var(--text-muted)",
                            fontSize: "0.8rem",
                            marginBottom: 16,
                            letterSpacing: "0.05em",
                        }}
                    >
                        BUILT WITH
                    </p>
                    <div
                        style={{
                            display: "flex",
                            justifyContent: "center",
                            gap: 32,
                            flexWrap: "wrap",
                            color: "var(--text-muted)",
                            fontSize: "0.85rem",
                            fontWeight: 500,
                        }}
                    >
                        <span>FastAPI</span>
                        <span>•</span>
                        <span>Next.js</span>
                        <span>•</span>
                        <span>Gemini</span>
                        <span>•</span>
                        <span>PostgreSQL</span>
                        <span>•</span>
                        <span>pgvector</span>
                    </div>
                </div>
            </div>
        </>
    );
}

function FeatureCard({
    icon,
    title,
    description,
}: {
    icon: string;
    title: string;
    description: string;
}) {
    return (
        <div className="glass-card" style={{ padding: 28 }}>
            <div
                style={{
                    width: 52,
                    height: 52,
                    borderRadius: "var(--radius-md)",
                    background: "var(--gradient-surface)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: "1.5rem",
                    marginBottom: 16,
                    border: "1px solid var(--border-subtle)",
                }}
            >
                {icon}
            </div>
            <h3
                style={{ fontSize: "1.1rem", fontWeight: 700, marginBottom: 8 }}
            >
                {title}
            </h3>
            <p
                style={{
                    color: "var(--text-secondary)",
                    fontSize: "0.85rem",
                    lineHeight: 1.6,
                    margin: 0,
                }}
            >
                {description}
            </p>
        </div>
    );
}
