/**
 * Dashboard page — overview stats, recent documents, quick actions.
 */

import React, { useEffect, useState } from "react";
import Head from "next/head";
import { useRouter } from "next/router";
import AppLayout from "@/components/layout/AppLayout";
import Banner from "@/components/ui/Banner";
import { useAuth } from "@/lib/auth-context";
import {
    analytics as analyticsApi,
    documents as documentsApi,
    OverviewStats,
    DocumentData,
} from "@/lib/api";

export default function DashboardPage() {
    const router = useRouter();
    const { user, loading: authLoading } = useAuth();
    const [stats, setStats] = useState<OverviewStats | null>(null);
    const [recentDocs, setRecentDocs] = useState<DocumentData[]>([]);
    const [loadError, setLoadError] = useState(false);
    const [reloadKey, setReloadKey] = useState(0);

    useEffect(() => {
        if (authLoading) return;
        if (!user) {
            router.push("/login");
            return;
        }

        setLoadError(false);

        Promise.all([
            analyticsApi.overview().catch(() => null),
            documentsApi.list(1, 5).catch(() => null),
        ]).then(([statsData, docsData]) => {
            if (statsData) setStats(statsData);
            if (docsData) setRecentDocs(docsData.documents);
            // Both failing means the backend is unreachable, not just empty data.
            if (!statsData && !docsData) setLoadError(true);
        });
    }, [user, authLoading, router, reloadKey]);

    if (authLoading || !user) return null;

    return (
        <>
            <Head>
                <title>Dashboard — Exyst</title>
                <meta
                    name="description"
                    content="Exyst AI dashboard — view analytics and manage exam predictions"
                />
            </Head>

            <AppLayout title="Dashboard">
                {loadError && (
                    <Banner
                        actionLabel="Retry"
                        onAction={() => setReloadKey((k) => k + 1)}
                        style={{ marginBottom: 24 }}
                    >
                        Couldn&apos;t load your dashboard data. The server may be
                        unavailable.
                    </Banner>
                )}

                {/* Welcome Section */}
                <div className="animate-fade-in" style={{ marginBottom: 32 }}>
                    <h1
                        style={{
                            fontSize: "1.75rem",
                            fontWeight: 800,
                            margin: 0,
                        }}
                    >
                        Welcome back,{" "}
                        <span className="text-gradient">
                            {user.name.split(" ")[0]}
                        </span>
                    </h1>
                    <p
                        style={{
                            color: "var(--text-muted)",
                            marginTop: 4,
                            fontSize: "0.9rem",
                        }}
                    >
                        Here&apos;s your exam intelligence overview
                    </p>
                </div>

                {/* Stats Grid */}
                <div
                    style={{
                        display: "grid",
                        gridTemplateColumns:
                            "repeat(auto-fit, minmax(200px, 1fr))",
                        gap: 20,
                        marginBottom: 32,
                    }}
                >
                    <StatCard
                        icon="📄"
                        value={stats?.documents.total ?? 0}
                        label="Documents"
                        delay={1}
                    />
                    <StatCard
                        icon="🔬"
                        value={stats?.analyses.completed ?? 0}
                        label="Analyses Complete"
                        delay={2}
                    />
                    <StatCard
                        icon="🎯"
                        value={stats?.predictions.total ?? 0}
                        label="Predictions"
                        delay={3}
                    />
                    <StatCard
                        icon="📊"
                        value={
                            stats?.predictions.avg_confidence
                                ? `${(stats.predictions.avg_confidence * 100).toFixed(0)}%`
                                : "—"
                        }
                        label="Avg Confidence"
                        gradient
                        delay={4}
                    />
                </div>

                {/* Quick Actions */}
                <div
                    className="glass-card animate-fade-in stagger-3"
                    style={{ padding: 24, marginBottom: 32, opacity: 0 }}
                >
                    <h3
                        style={{
                            fontSize: "1rem",
                            fontWeight: 700,
                            marginBottom: 16,
                            color: "var(--text-primary)",
                        }}
                    >
                        Quick Actions
                    </h3>
                    <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                        <button
                            className="btn-primary"
                            onClick={() => router.push("/upload")}
                            style={{
                                display: "flex",
                                alignItems: "center",
                                gap: 8,
                            }}
                        >
                            <span>📤</span> Upload Document
                        </button>
                        <button
                            className="btn-secondary"
                            onClick={() => router.push("/documents")}
                            style={{
                                display: "flex",
                                alignItems: "center",
                                gap: 8,
                            }}
                        >
                            <span>📁</span> View Documents
                        </button>
                        <button
                            className="btn-secondary"
                            onClick={() => router.push("/analytics")}
                            style={{
                                display: "flex",
                                alignItems: "center",
                                gap: 8,
                            }}
                        >
                            <span>📈</span> Analytics
                        </button>
                    </div>
                </div>

                {/* Recent Documents */}
                <div
                    className="glass-card animate-fade-in stagger-4"
                    style={{ padding: 24, opacity: 0 }}
                >
                    <div
                        style={{
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                            marginBottom: 16,
                        }}
                    >
                        <h3
                            style={{
                                fontSize: "1rem",
                                fontWeight: 700,
                                color: "var(--text-primary)",
                                margin: 0,
                            }}
                        >
                            Recent Documents
                        </h3>
                        <button
                            className="btn-secondary"
                            onClick={() => router.push("/documents")}
                            style={{ fontSize: "0.75rem", padding: "6px 12px" }}
                        >
                            View All →
                        </button>
                    </div>

                    {recentDocs.length === 0 ? (
                        <div
                            style={{
                                textAlign: "center",
                                padding: "40px 0",
                                color: "var(--text-muted)",
                            }}
                        >
                            <p style={{ fontSize: "2rem", marginBottom: 8 }}>
                                📄
                            </p>
                            <p style={{ fontSize: "0.9rem" }}>
                                No documents yet
                            </p>
                            <p style={{ fontSize: "0.8rem" }}>
                                Upload your first document to get started
                            </p>
                        </div>
                    ) : (
                        <div
                            style={{
                                display: "flex",
                                flexDirection: "column",
                                gap: 8,
                            }}
                        >
                            {recentDocs.map((doc) => (
                                <div
                                    key={doc.id}
                                    onClick={() =>
                                        router.push(`/documents/${doc.id}`)
                                    }
                                    style={{
                                        display: "flex",
                                        alignItems: "center",
                                        justifyContent: "space-between",
                                        padding: "12px 16px",
                                        borderRadius: "var(--radius-md)",
                                        background: "rgba(255, 255, 255, 0.02)",
                                        border: "1px solid var(--border-subtle)",
                                        cursor: "pointer",
                                        transition: "all 0.2s ease",
                                    }}
                                >
                                    <div
                                        style={{
                                            display: "flex",
                                            alignItems: "center",
                                            gap: 12,
                                        }}
                                    >
                                        <span style={{ fontSize: "1.2rem" }}>
                                            📄
                                        </span>
                                        <div>
                                            <p
                                                style={{
                                                    margin: 0,
                                                    fontSize: "0.85rem",
                                                    fontWeight: 600,
                                                    color: "var(--text-primary)",
                                                }}
                                            >
                                                {doc.original_filename ||
                                                    doc.filename}
                                            </p>
                                            <p
                                                style={{
                                                    margin: 0,
                                                    fontSize: "0.75rem",
                                                    color: "var(--text-muted)",
                                                }}
                                            >
                                                {new Date(
                                                    doc.uploaded_at,
                                                ).toLocaleDateString()}{" "}
                                                •{" "}
                                                {(
                                                    doc.file_size_bytes / 1024
                                                ).toFixed(0)}{" "}
                                                KB
                                            </p>
                                        </div>
                                    </div>
                                    <span
                                        className={`badge badge-${doc.status === "completed" ? "success" : doc.status === "failed" ? "error" : "info"}`}
                                    >
                                        {doc.status}
                                    </span>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </AppLayout>
        </>
    );
}

// --- Stat Card Component ---

function StatCard({
    icon,
    value,
    label,
    gradient,
    delay,
}: {
    icon: string;
    value: number | string;
    label: string;
    gradient?: boolean;
    delay: number;
}) {
    return (
        <div
            className={`stat-card animate-fade-in stagger-${delay}`}
            style={{ opacity: 0 }}
        >
            <div
                style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                    marginBottom: 12,
                }}
            >
                <span style={{ fontSize: "1.5rem" }}>{icon}</span>
            </div>
            <div
                className={gradient ? "text-gradient" : ""}
                style={{ fontSize: "2rem", fontWeight: 800, lineHeight: 1.1 }}
            >
                {value}
            </div>
            <div className="stat-label">{label}</div>
        </div>
    );
}
