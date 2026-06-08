/**
 * Analytics page — aggregate insights and visualizations.
 */

import React, { useEffect, useState } from "react";
import Head from "next/head";
import { useRouter } from "next/router";
import AppLayout from "@/components/layout/AppLayout";
import { useAuth } from "@/lib/auth-context";
import { analytics as analyticsApi, OverviewStats } from "@/lib/api";

export default function AnalyticsPage() {
    const router = useRouter();
    const { user, loading: authLoading } = useAuth();
    const [stats, setStats] = useState<OverviewStats | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (authLoading) return;
        if (!user) {
            router.push("/login");
            return;
        }

        analyticsApi
            .overview()
            .then(setStats)
            .catch(() => {})
            .finally(() => setLoading(false));
    }, [user, authLoading, router]);

    if (authLoading || !user) return null;

    return (
        <>
            <Head>
                <title>Analytics — Exyst</title>
                <meta
                    name="description"
                    content="View aggregate analytics and insights for your exam predictions"
                />
            </Head>

            <AppLayout title="Analytics">
                <div className="animate-fade-in">
                    <p
                        style={{
                            color: "var(--text-muted)",
                            marginBottom: 28,
                            fontSize: "0.9rem",
                        }}
                    >
                        Aggregate insights across all your uploaded documents
                        and predictions.
                    </p>

                    {loading ? (
                        <div style={{ textAlign: "center", padding: "80px 0" }}>
                            <span
                                className="spinner"
                                style={{
                                    width: 32,
                                    height: 32,
                                    margin: "0 auto",
                                    display: "block",
                                }}
                            />
                        </div>
                    ) : !stats ? (
                        <div
                            className="glass-card"
                            style={{
                                padding: "60px 24px",
                                textAlign: "center",
                            }}
                        >
                            <p style={{ fontSize: "2.5rem", marginBottom: 12 }}>
                                📈
                            </p>
                            <p style={{ fontSize: "1.1rem", fontWeight: 600 }}>
                                No data yet
                            </p>
                            <p
                                style={{
                                    color: "var(--text-muted)",
                                    marginBottom: 20,
                                }}
                            >
                                Upload and analyze documents to see analytics
                            </p>
                            <button
                                className="btn-primary"
                                onClick={() => router.push("/upload")}
                            >
                                Upload Your First Document
                            </button>
                        </div>
                    ) : (
                        <>
                            {/* Document & Analysis Stats */}
                            <div
                                style={{
                                    display: "grid",
                                    gridTemplateColumns:
                                        "repeat(auto-fit, minmax(220px, 1fr))",
                                    gap: 20,
                                    marginBottom: 28,
                                }}
                            >
                                <BigStatCard
                                    icon="📄"
                                    value={stats.documents.total}
                                    label="Documents Uploaded"
                                    color="var(--accent-indigo)"
                                />
                                <BigStatCard
                                    icon="🔬"
                                    value={stats.analyses.completed}
                                    label="Analyses Completed"
                                    sub={`${stats.analyses.total_pages_processed} pages • ${stats.analyses.total_papers_found} papers`}
                                    color="var(--accent-cyan)"
                                />
                                <BigStatCard
                                    icon="🎯"
                                    value={stats.predictions.total}
                                    label="Predictions Generated"
                                    sub={`Avg ${stats.predictions.avg_generation_time_seconds.toFixed(1)}s generation`}
                                    color="var(--accent-violet)"
                                />
                            </div>

                            {/* Confidence & Performance */}
                            <div
                                style={{
                                    display: "grid",
                                    gridTemplateColumns: "1fr 1fr",
                                    gap: 20,
                                    marginBottom: 28,
                                }}
                            >
                                {/* Confidence Summary */}
                                <div
                                    className="glass-card"
                                    style={{ padding: 28 }}
                                >
                                    <h3
                                        style={{
                                            fontSize: "1rem",
                                            fontWeight: 700,
                                            marginBottom: 20,
                                        }}
                                    >
                                        🎯 Prediction Confidence
                                    </h3>
                                    <div
                                        style={{
                                            display: "flex",
                                            gap: 32,
                                            alignItems: "center",
                                        }}
                                    >
                                        <div style={{ textAlign: "center" }}>
                                            <div
                                                className="text-gradient"
                                                style={{
                                                    fontSize: "2.5rem",
                                                    fontWeight: 900,
                                                    lineHeight: 1,
                                                }}
                                            >
                                                {stats.predictions
                                                    .avg_confidence
                                                    ? `${(stats.predictions.avg_confidence * 100).toFixed(0)}%`
                                                    : "—"}
                                            </div>
                                            <p
                                                style={{
                                                    color: "var(--text-muted)",
                                                    fontSize: "0.75rem",
                                                    marginTop: 4,
                                                }}
                                            >
                                                Average
                                            </p>
                                        </div>
                                        <div style={{ textAlign: "center" }}>
                                            <div
                                                style={{
                                                    fontSize: "2.5rem",
                                                    fontWeight: 900,
                                                    lineHeight: 1,
                                                    color: "var(--accent-emerald)",
                                                }}
                                            >
                                                {stats.predictions
                                                    .max_confidence
                                                    ? `${(stats.predictions.max_confidence * 100).toFixed(0)}%`
                                                    : "—"}
                                            </div>
                                            <p
                                                style={{
                                                    color: "var(--text-muted)",
                                                    fontSize: "0.75rem",
                                                    marginTop: 4,
                                                }}
                                            >
                                                Best
                                            </p>
                                        </div>
                                    </div>
                                </div>

                                {/* Processing Performance */}
                                <div
                                    className="glass-card"
                                    style={{ padding: 28 }}
                                >
                                    <h3
                                        style={{
                                            fontSize: "1rem",
                                            fontWeight: 700,
                                            marginBottom: 20,
                                        }}
                                    >
                                        ⚡ Processing Performance
                                    </h3>
                                    <div
                                        style={{
                                            display: "flex",
                                            flexDirection: "column",
                                            gap: 16,
                                        }}
                                    >
                                        <div>
                                            <div
                                                style={{
                                                    display: "flex",
                                                    justifyContent:
                                                        "space-between",
                                                }}
                                            >
                                                <span
                                                    style={{
                                                        fontSize: "0.8rem",
                                                        color: "var(--text-secondary)",
                                                    }}
                                                >
                                                    Avg Analysis Time
                                                </span>
                                                <span
                                                    style={{
                                                        fontSize: "0.85rem",
                                                        fontWeight: 700,
                                                    }}
                                                >
                                                    {stats.analyses.avg_processing_time_seconds.toFixed(
                                                        1,
                                                    )}
                                                    s
                                                </span>
                                            </div>
                                            <div
                                                style={{
                                                    width: "100%",
                                                    height: 6,
                                                    background:
                                                        "rgba(255,255,255,0.05)",
                                                    borderRadius: 3,
                                                    marginTop: 6,
                                                    overflow: "hidden",
                                                }}
                                            >
                                                <div
                                                    style={{
                                                        width: `${Math.min((stats.analyses.avg_processing_time_seconds / 60) * 100, 100)}%`,
                                                        height: "100%",
                                                        background:
                                                            "var(--accent-cyan)",
                                                        borderRadius: 3,
                                                    }}
                                                />
                                            </div>
                                        </div>
                                        <div>
                                            <div
                                                style={{
                                                    display: "flex",
                                                    justifyContent:
                                                        "space-between",
                                                }}
                                            >
                                                <span
                                                    style={{
                                                        fontSize: "0.8rem",
                                                        color: "var(--text-secondary)",
                                                    }}
                                                >
                                                    Avg Prediction Time
                                                </span>
                                                <span
                                                    style={{
                                                        fontSize: "0.85rem",
                                                        fontWeight: 700,
                                                    }}
                                                >
                                                    {stats.predictions.avg_generation_time_seconds.toFixed(
                                                        1,
                                                    )}
                                                    s
                                                </span>
                                            </div>
                                            <div
                                                style={{
                                                    width: "100%",
                                                    height: 6,
                                                    background:
                                                        "rgba(255,255,255,0.05)",
                                                    borderRadius: 3,
                                                    marginTop: 6,
                                                    overflow: "hidden",
                                                }}
                                            >
                                                <div
                                                    style={{
                                                        width: `${Math.min((stats.predictions.avg_generation_time_seconds / 60) * 100, 100)}%`,
                                                        height: "100%",
                                                        background:
                                                            "var(--accent-violet)",
                                                        borderRadius: 3,
                                                    }}
                                                />
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Info Banner */}
                            <div
                                className="glass-card"
                                style={{
                                    padding: 20,
                                    display: "flex",
                                    alignItems: "center",
                                    gap: 16,
                                    borderLeft:
                                        "3px solid var(--accent-indigo)",
                                }}
                            >
                                <span style={{ fontSize: "1.5rem" }}>💡</span>
                                <div>
                                    <p
                                        style={{
                                            margin: 0,
                                            fontSize: "0.85rem",
                                            fontWeight: 600,
                                        }}
                                    >
                                        Tip: Upload more documents for better
                                        predictions
                                    </p>
                                    <p
                                        style={{
                                            margin: "4px 0 0",
                                            fontSize: "0.8rem",
                                            color: "var(--text-muted)",
                                        }}
                                    >
                                        The AI learns patterns from historical
                                        papers. More data = higher confidence.
                                    </p>
                                </div>
                            </div>
                        </>
                    )}
                </div>
            </AppLayout>
        </>
    );
}

function BigStatCard({
    icon,
    value,
    label,
    sub,
    color,
}: {
    icon: string;
    value: number;
    label: string;
    sub?: string;
    color: string;
}) {
    return (
        <div className="stat-card">
            <div
                style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                    marginBottom: 16,
                }}
            >
                <div
                    style={{
                        width: 44,
                        height: 44,
                        borderRadius: "var(--radius-md)",
                        background: `${color}15`,
                        border: `1px solid ${color}30`,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: "1.3rem",
                    }}
                >
                    {icon}
                </div>
            </div>
            <div
                style={{
                    fontSize: "2.25rem",
                    fontWeight: 900,
                    lineHeight: 1.1,
                    color,
                }}
            >
                {value}
            </div>
            <div className="stat-label">{label}</div>
            {sub && (
                <p
                    style={{
                        color: "var(--text-muted)",
                        fontSize: "0.7rem",
                        marginTop: 6,
                    }}
                >
                    {sub}
                </p>
            )}
        </div>
    );
}
