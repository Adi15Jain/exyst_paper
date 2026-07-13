/**
 * Documents list page.
 */

import React, { useEffect, useState } from "react";
import Head from "next/head";
import { useRouter } from "next/router";
import AppLayout from "@/components/layout/AppLayout";
import Banner from "@/components/ui/Banner";
import EmptyState from "@/components/ui/EmptyState";
import Spinner from "@/components/ui/Spinner";
import { useAuth } from "@/lib/auth-context";
import {
    documents as documentsApi,
    courses as coursesApi,
    DocumentData,
} from "@/lib/api";

export default function DocumentsPage() {
    const router = useRouter();
    const { user, loading: authLoading } = useAuth();
    const [docs, setDocs] = useState<DocumentData[]>([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    // Set when arriving from a course card ("View papers →").
    const courseId =
        typeof router.query.course === "string" ? router.query.course : undefined;
    const [courseName, setCourseName] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState(false);
    const [reloadKey, setReloadKey] = useState(0);
    const [deletingId, setDeletingId] = useState<string | null>(null);
    const [actionError, setActionError] = useState<string | null>(null);

    const handleRename = async (doc: DocumentData) => {
        const current = doc.original_filename || doc.filename;
        const next = window.prompt("Rename document", current);
        if (!next || !next.trim() || next === current) return;

        setActionError(null);
        try {
            await documentsApi.rename(doc.id, next.trim());
            setReloadKey((k) => k + 1);
        } catch (e) {
            setActionError(e instanceof Error ? e.message : "Rename failed");
        }
    };

    const handleDelete = async (doc: DocumentData) => {
        const name = doc.original_filename || doc.filename;
        if (
            !window.confirm(
                `Delete "${name}"? Its analyses and predictions will be deleted too. This cannot be undone.`,
            )
        ) {
            return;
        }
        setActionError(null);
        setDeletingId(doc.id);
        try {
            await documentsApi.delete(doc.id);
            // If this was the last row on the page, step back a page.
            if (docs.length === 1 && page > 1) {
                setPage(page - 1);
            } else {
                setReloadKey((k) => k + 1);
            }
        } catch (e) {
            setActionError(e instanceof Error ? e.message : "Delete failed");
        } finally {
            setDeletingId(null);
        }
    };

    useEffect(() => {
        if (authLoading) return;
        if (!user) {
            router.push("/login");
            return;
        }

        setLoading(true);
        setLoadError(false);

        documentsApi
            .list(page, 10, courseId)
            .then((data) => {
                setDocs(data.documents);
                setTotal(data.total);
            })
            .catch(() => setLoadError(true))
            .finally(() => setLoading(false));
    }, [user, authLoading, page, router, reloadKey, courseId]);

    // Show which course is being filtered, so the view isn't silently narrowed.
    useEffect(() => {
        if (!courseId) {
            setCourseName(null);
            return;
        }
        coursesApi
            .get(courseId)
            .then((c) => setCourseName(c.name))
            .catch(() => setCourseName(null));
    }, [courseId]);

    if (authLoading || !user) return null;

    return (
        <>
            <Head>
                <title>Documents — Exyst</title>
                <meta
                    name="description"
                    content="Manage your uploaded exam documents"
                />
            </Head>

            <AppLayout title="Documents">
                <div className="animate-fade-in">
                    {loadError && (
                        <Banner
                            actionLabel="Retry"
                            onAction={() => setReloadKey((k) => k + 1)}
                            style={{ marginBottom: 20 }}
                        >
                            Couldn&apos;t load your documents. The server may be
                            unavailable.
                        </Banner>
                    )}

                    {actionError && (
                        <Banner
                            onDismiss={() => setActionError(null)}
                            style={{ marginBottom: 20 }}
                        >
                            {actionError}
                        </Banner>
                    )}

                    {/* Header */}
                    <div
                        style={{
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                            marginBottom: 24,
                        }}
                    >
                        <div>
                            <p
                                style={{
                                    color: "var(--text-muted)",
                                    fontSize: "0.85rem",
                                    margin: 0,
                                }}
                            >
                                {total} document{total !== 1 ? "s" : ""}
                                {courseId ? " in this course" : " total"}
                            </p>
                            {courseId && (
                                <p
                                    style={{
                                        margin: "4px 0 0",
                                        fontSize: "0.8rem",
                                        color: "var(--text-secondary)",
                                    }}
                                >
                                    🎓 {courseName || "Course"} ·{" "}
                                    <button
                                        onClick={() => router.push("/documents")}
                                        style={{
                                            background: "none",
                                            border: "none",
                                            color: "var(--accent-indigo)",
                                            cursor: "pointer",
                                            fontSize: "0.8rem",
                                            padding: 0,
                                        }}
                                    >
                                        show all
                                    </button>
                                </p>
                            )}
                        </div>
                        <button
                            className="btn-primary"
                            onClick={() => router.push("/upload")}
                            style={{
                                display: "flex",
                                alignItems: "center",
                                gap: 8,
                            }}
                        >
                            <span>📤</span> Upload New
                        </button>
                    </div>

                    {/* Document List */}
                    {loading ? (
                        <Spinner caption="Loading documents..." />
                    ) : docs.length === 0 ? (
                        <EmptyState
                            icon="📭"
                            title="No documents yet"
                            hint="Upload your first exam document to get started"
                            actionLabel="Upload Document"
                            onAction={() => router.push("/upload")}
                        />
                    ) : (
                        <div
                            style={{
                                display: "flex",
                                flexDirection: "column",
                                gap: 12,
                            }}
                        >
                            {docs.map((doc, i) => (
                                <div
                                    key={doc.id}
                                    className={`glass-card animate-fade-in stagger-${Math.min(i + 1, 5)}`}
                                    style={{
                                        padding: "16px 20px",
                                        cursor: "pointer",
                                        display: "flex",
                                        alignItems: "center",
                                        justifyContent: "space-between",
                                        opacity: 0,
                                    }}
                                    onClick={() =>
                                        router.push(`/documents/${doc.id}`)
                                    }
                                >
                                    <div
                                        style={{
                                            display: "flex",
                                            alignItems: "center",
                                            gap: 16,
                                        }}
                                    >
                                        <div
                                            style={{
                                                width: 44,
                                                height: 44,
                                                borderRadius:
                                                    "var(--radius-md)",
                                                background:
                                                    "var(--gradient-surface)",
                                                display: "flex",
                                                alignItems: "center",
                                                justifyContent: "center",
                                                fontSize: "1.3rem",
                                                border: "1px solid var(--border-subtle)",
                                            }}
                                        >
                                            📄
                                        </div>
                                        <div>
                                            <p
                                                style={{
                                                    margin: 0,
                                                    fontWeight: 600,
                                                    color: "var(--text-primary)",
                                                    fontSize: "0.9rem",
                                                }}
                                            >
                                                {doc.original_filename ||
                                                    doc.filename}
                                            </p>
                                            <p
                                                style={{
                                                    margin: "2px 0 0",
                                                    color: "var(--text-muted)",
                                                    fontSize: "0.75rem",
                                                }}
                                            >
                                                Uploaded{" "}
                                                {new Date(
                                                    doc.uploaded_at,
                                                ).toLocaleDateString("en-US", {
                                                    year: "numeric",
                                                    month: "short",
                                                    day: "numeric",
                                                })}{" "}
                                                •{" "}
                                                {(
                                                    doc.file_size_bytes / 1024
                                                ).toFixed(0)}{" "}
                                                KB
                                            </p>
                                        </div>
                                    </div>

                                    <div
                                        style={{
                                            display: "flex",
                                            alignItems: "center",
                                            gap: 12,
                                        }}
                                    >
                                        <span
                                            className={`badge badge-${
                                                doc.status === "completed"
                                                    ? "success"
                                                    : doc.status === "failed"
                                                      ? "error"
                                                      : "info"
                                            }`}
                                        >
                                            {doc.status}
                                        </span>
                                        <button
                                            aria-label={`Rename ${doc.original_filename || doc.filename}`}
                                            title="Rename document"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                handleRename(doc);
                                            }}
                                            style={{
                                                background: "transparent",
                                                border: "1px solid var(--border-subtle)",
                                                color: "var(--text-secondary)",
                                                cursor: "pointer",
                                                fontSize: "0.75rem",
                                                padding: "6px 12px",
                                                borderRadius:
                                                    "var(--radius-sm)",
                                            }}
                                        >
                                            Rename
                                        </button>
                                        <button
                                            aria-label={`Delete ${doc.original_filename || doc.filename}`}
                                            title="Delete document"
                                            disabled={deletingId === doc.id}
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                handleDelete(doc);
                                            }}
                                            style={{
                                                background:
                                                    "rgba(239, 68, 68, 0.1)",
                                                border: "1px solid rgba(239, 68, 68, 0.2)",
                                                color: "#ef4444",
                                                cursor:
                                                    deletingId === doc.id
                                                        ? "wait"
                                                        : "pointer",
                                                fontSize: "0.75rem",
                                                padding: "6px 12px",
                                                borderRadius:
                                                    "var(--radius-sm)",
                                            }}
                                        >
                                            {deletingId === doc.id
                                                ? "Deleting…"
                                                : "Delete"}
                                        </button>
                                        <span
                                            style={{
                                                color: "var(--text-muted)",
                                                fontSize: "1.2rem",
                                            }}
                                        >
                                            →
                                        </span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Pagination */}
                    {total > 10 && (
                        <div
                            style={{
                                display: "flex",
                                justifyContent: "center",
                                gap: 8,
                                marginTop: 24,
                            }}
                        >
                            <button
                                className="btn-secondary"
                                disabled={page <= 1}
                                onClick={() => setPage(page - 1)}
                                style={{
                                    padding: "8px 16px",
                                    fontSize: "0.8rem",
                                }}
                            >
                                ← Previous
                            </button>
                            <span
                                style={{
                                    display: "flex",
                                    alignItems: "center",
                                    color: "var(--text-muted)",
                                    fontSize: "0.85rem",
                                    padding: "0 16px",
                                }}
                            >
                                Page {page} of {Math.ceil(total / 10)}
                            </span>
                            <button
                                className="btn-secondary"
                                disabled={page * 10 >= total}
                                onClick={() => setPage(page + 1)}
                                style={{
                                    padding: "8px 16px",
                                    fontSize: "0.8rem",
                                }}
                            >
                                Next →
                            </button>
                        </div>
                    )}
                </div>
            </AppLayout>
        </>
    );
}
