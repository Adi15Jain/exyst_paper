/**
 * Courses page — the organizing unit for a student's papers.
 *
 * A course is a subject. Papers filed under it accumulate into one corpus, and
 * predictions for any paper in the course are grounded on that whole corpus.
 */

import React, { useEffect, useState } from "react";
import Head from "next/head";
import { useRouter } from "next/router";
import AppLayout from "@/components/layout/AppLayout";
import Banner from "@/components/ui/Banner";
import EmptyState from "@/components/ui/EmptyState";
import Spinner from "@/components/ui/Spinner";
import { useAuth } from "@/lib/auth-context";
import { courses as coursesApi, Course } from "@/lib/api";

const labelStyle: React.CSSProperties = {
    display: "block",
    fontSize: "0.8rem",
    fontWeight: 600,
    color: "var(--text-secondary)",
    marginBottom: 6,
};

export default function CoursesPage() {
    const router = useRouter();
    const { user, loading: authLoading } = useAuth();

    const [items, setItems] = useState<Course[]>([]);
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState(false);
    const [reloadKey, setReloadKey] = useState(0);
    const [actionError, setActionError] = useState<string | null>(null);
    const [deletingId, setDeletingId] = useState<string | null>(null);

    const [showForm, setShowForm] = useState(false);
    const [name, setName] = useState("");
    const [code, setCode] = useState("");
    const [semester, setSemester] = useState("");
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        if (authLoading) return;
        if (!user) {
            router.push("/login");
            return;
        }

        setLoading(true);
        setLoadError(false);
        coursesApi
            .list()
            .then((data) => setItems(data.courses))
            .catch(() => setLoadError(true))
            .finally(() => setLoading(false));
    }, [user, authLoading, router, reloadKey]);

    if (authLoading || !user) return null;

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        setActionError(null);
        setSaving(true);
        try {
            await coursesApi.create({
                name: name.trim(),
                code: code.trim() || null,
                semester: semester.trim() || null,
            });
            setName("");
            setCode("");
            setSemester("");
            setShowForm(false);
            setReloadKey((k) => k + 1);
        } catch (err) {
            setActionError(
                err instanceof Error
                    ? err.message
                    : "Couldn't create the course.",
            );
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async (course: Course) => {
        const papers = course.document_count;
        const note =
            papers > 0
                ? `\n\nIts ${papers} paper${papers === 1 ? "" : "s"} will NOT be deleted — they'll just become unfiled.`
                : "";
        if (!window.confirm(`Delete the course "${course.name}"?${note}`))
            return;

        setActionError(null);
        setDeletingId(course.id);
        try {
            await coursesApi.delete(course.id);
            setReloadKey((k) => k + 1);
        } catch (err) {
            setActionError(
                err instanceof Error
                    ? err.message
                    : "Couldn't delete the course.",
            );
        } finally {
            setDeletingId(null);
        }
    };

    return (
        <>
            <Head>
                <title>Courses — Exyst</title>
                <meta
                    name="description"
                    content="Group your exam papers by subject"
                />
            </Head>

            <AppLayout title="Courses">
                <div className="animate-fade-in">
                    {loadError && (
                        <Banner
                            actionLabel="Retry"
                            onAction={() => setReloadKey((k) => k + 1)}
                            style={{ marginBottom: 20 }}
                        >
                            Couldn&apos;t load your courses. The server may be
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

                    <div
                        style={{
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                            marginBottom: 24,
                            gap: 12,
                            flexWrap: "wrap",
                        }}
                    >
                        <p
                            style={{
                                color: "var(--text-muted)",
                                fontSize: "0.85rem",
                                margin: 0,
                            }}
                        >
                            Papers filed under a course are analysed together —
                            each prediction is grounded on that subject&apos;s
                            full history.
                        </p>
                        <button
                            className="btn-primary"
                            onClick={() => setShowForm((s) => !s)}
                        >
                            {showForm ? "Cancel" : "+ New Course"}
                        </button>
                    </div>

                    {showForm && (
                        <form
                            className="glass-card animate-fade-in"
                            style={{ padding: 24, marginBottom: 24 }}
                            onSubmit={handleCreate}
                        >
                            <label style={labelStyle} htmlFor="course-name">
                                Course name
                            </label>
                            <input
                                id="course-name"
                                className="input-field"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                placeholder="e.g. Machine Learning"
                                required
                                maxLength={255}
                                style={{ width: "100%", marginBottom: 16 }}
                            />

                            <div
                                className="grid-2"
                                style={{ marginBottom: 16 }}
                            >
                                <div>
                                    <label
                                        style={labelStyle}
                                        htmlFor="course-code"
                                    >
                                        Course code{" "}
                                        <span style={{ fontWeight: 400 }}>
                                            (optional)
                                        </span>
                                    </label>
                                    <input
                                        id="course-code"
                                        className="input-field"
                                        value={code}
                                        onChange={(e) =>
                                            setCode(e.target.value)
                                        }
                                        placeholder="e.g. EAI602"
                                        maxLength={50}
                                        style={{ width: "100%" }}
                                    />
                                </div>
                                <div>
                                    <label
                                        style={labelStyle}
                                        htmlFor="course-semester"
                                    >
                                        Semester{" "}
                                        <span style={{ fontWeight: 400 }}>
                                            (optional)
                                        </span>
                                    </label>
                                    <input
                                        id="course-semester"
                                        className="input-field"
                                        value={semester}
                                        onChange={(e) =>
                                            setSemester(e.target.value)
                                        }
                                        placeholder="e.g. 6th"
                                        maxLength={50}
                                        style={{ width: "100%" }}
                                    />
                                </div>
                            </div>

                            <button
                                type="submit"
                                className="btn-primary"
                                disabled={saving || !name.trim()}
                            >
                                {saving ? "Creating…" : "Create Course"}
                            </button>
                        </form>
                    )}

                    {loading ? (
                        <Spinner caption="Loading courses..." />
                    ) : items.length === 0 ? (
                        <EmptyState
                            icon="🎓"
                            title="No courses yet"
                            hint="Create a course, then file your past papers under it — they'll build up into one corpus per subject."
                            actionLabel="Create your first course"
                            onAction={() => setShowForm(true)}
                        />
                    ) : (
                        <div
                            style={{
                                display: "grid",
                                gridTemplateColumns:
                                    "repeat(auto-fill, minmax(260px, 1fr))",
                                gap: 16,
                            }}
                        >
                            {items.map((course, i) => (
                                <div
                                    key={course.id}
                                    className={`glass-card animate-fade-in stagger-${Math.min(i + 1, 5)}`}
                                    style={{ padding: 20, opacity: 0 }}
                                >
                                    <div
                                        style={{
                                            display: "flex",
                                            justifyContent: "space-between",
                                            alignItems: "flex-start",
                                            gap: 8,
                                        }}
                                    >
                                        <h3
                                            style={{
                                                margin: 0,
                                                fontSize: "1rem",
                                                fontWeight: 700,
                                                color: "var(--text-primary)",
                                            }}
                                        >
                                            {course.name}
                                        </h3>
                                        <button
                                            aria-label={`Delete ${course.name}`}
                                            title="Delete course (papers are kept)"
                                            onClick={() => handleDelete(course)}
                                            disabled={deletingId === course.id}
                                            style={{
                                                background: "transparent",
                                                border: "none",
                                                color: "var(--text-muted)",
                                                cursor:
                                                    deletingId === course.id
                                                        ? "wait"
                                                        : "pointer",
                                                fontSize: "0.9rem",
                                                padding: 0,
                                                lineHeight: 1,
                                            }}
                                        >
                                            {deletingId === course.id ? (
                                                <span
                                                    className="spinner"
                                                    style={{
                                                        width: 12,
                                                        height: 12,
                                                    }}
                                                />
                                            ) : (
                                                "✕"
                                            )}
                                        </button>
                                    </div>

                                    <p
                                        style={{
                                            margin: "4px 0 14px",
                                            fontSize: "0.75rem",
                                            color: "var(--text-muted)",
                                        }}
                                    >
                                        {[course.code, course.semester]
                                            .filter(Boolean)
                                            .join(" • ") || "—"}
                                    </p>

                                    <p
                                        style={{
                                            margin: "0 0 14px",
                                            fontSize: "0.85rem",
                                            color: "var(--text-secondary)",
                                        }}
                                    >
                                        {course.document_count} paper
                                        {course.document_count === 1 ? "" : "s"}
                                    </p>

                                    <button
                                        className="btn-secondary"
                                        onClick={() =>
                                            router.push(
                                                `/documents?course=${course.id}`,
                                            )
                                        }
                                        style={{
                                            width: "100%",
                                            fontSize: "0.8rem",
                                            padding: "8px 12px",
                                        }}
                                    >
                                        View papers →
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </AppLayout>
        </>
    );
}
