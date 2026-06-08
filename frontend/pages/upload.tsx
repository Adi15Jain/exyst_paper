/**
 * Upload page — drag & drop upload, triggers analysis + prediction pipeline
 * with real-time SSE streaming progress.
 */

import React, { useState, useCallback, useRef } from "react";
import Head from "next/head";
import { useRouter } from "next/router";
import AppLayout from "@/components/layout/AppLayout";
import { useAuth } from "@/lib/auth-context";
import {
    documents,
    pipeline,
    PipelineEvent,
} from "@/lib/api";

type PipelineStage =
    | "idle"
    | "uploading"
    | "streaming"
    | "complete"
    | "error";

interface StageLog {
    stage: string;
    detail: string;
    progress: number;
    timestamp: number;
    duration?: number;
}

const STAGE_LABELS: Record<string, string> = {
    starting: "🚀 Initializing pipeline",
    analysis_start: "🔬 Starting AI analysis",
    pdf_extraction: "📄 Extracting PDF text",
    classifying: "🏷️ Classifying pages",
    syllabus_analysis: "📚 Analyzing syllabus",
    pattern_analysis: "📊 Analyzing question patterns",
    rag_indexing: "🔗 Indexing into vector store",
    analysis_complete: "✅ Analysis complete",
    rag_retrieval: "🔍 Retrieving similar questions",
    predicting: "🧠 Generating prediction (Gemini)",
    evaluating: "📏 Scoring confidence",
};

export default function UploadPage() {
    const router = useRouter();
    const { user, loading: authLoading } = useAuth();
    const [file, setFile] = useState<File | null>(null);
    const [dragActive, setDragActive] = useState(false);
    const [stage, setStage] = useState<PipelineStage>("idle");
    const [error, setError] = useState("");
    const [progress, setProgress] = useState(0);
    const [currentDetail, setCurrentDetail] = useState("");
    const [currentStage, setCurrentStage] = useState("");
    const [stageLogs, setStageLogs] = useState<StageLog[]>([]);
    const [completionData, setCompletionData] = useState<any>(null);
    const startTimeRef = useRef<number>(0);

    const handleDrag = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover")
            setDragActive(true);
        else if (e.type === "dragleave") setDragActive(false);
    }, []);

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        if (e.dataTransfer.files?.[0]) {
            setFile(e.dataTransfer.files[0]);
            setError("");
        }
    }, []);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files?.[0]) {
            setFile(e.target.files[0]);
            setError("");
        }
    };

    const handleSubmit = async () => {
        if (!file) return;

        setError("");
        setProgress(0);
        setStageLogs([]);
        setCompletionData(null);
        startTimeRef.current = Date.now();

        try {
            // Stage 1: Upload
            setStage("uploading");
            setCurrentDetail("Uploading document...");
            setCurrentStage("uploading");
            setProgress(5);

            const doc = await documents.upload(file);

            // Stage 2: Stream analysis + prediction
            setStage("streaming");
            setProgress(8);

            let lastStageTime = Date.now();

            await pipeline.runStream(doc.id, (event: PipelineEvent) => {
                const now = Date.now();

                if (event.event === "stage") {
                    const stageName = event.data.stage || "";
                    const detail = event.data.detail || "";
                    const prog = event.data.progress || 0;

                    // Update current state
                    setCurrentStage(stageName);
                    setCurrentDetail(detail);
                    setProgress(prog);

                    // Add to log with duration of previous stage
                    setStageLogs((prev) => {
                        const updated = [...prev];
                        if (updated.length > 0) {
                            updated[updated.length - 1].duration =
                                now - lastStageTime;
                        }
                        updated.push({
                            stage: stageName,
                            detail,
                            progress: prog,
                            timestamp: now,
                        });
                        return updated;
                    });

                    lastStageTime = now;
                } else if (event.event === "complete") {
                    setCompletionData(event.data);
                    setStage("complete");
                    setProgress(100);
                    setCurrentDetail("Pipeline complete!");
                    setCurrentStage("complete");

                    // Navigate to results
                    setTimeout(() => {
                        router.push(`/documents/${doc.id}`);
                    }, 2000);
                } else if (event.event === "error") {
                    setStage("error");
                    setError(event.data.error || "Pipeline failed");
                }
            });

            // If stream ended without complete event
            if (stage !== "complete" && stage !== "error") {
                setStage("complete");
                setProgress(100);
                setTimeout(() => {
                    router.push(`/documents/${doc.id}`);
                }, 2000);
            }
        } catch (err) {
            setStage("error");
            setError(err instanceof Error ? err.message : "Pipeline failed");
        }
    };

    if (authLoading || !user) {
        if (!authLoading && !user) router.push("/login");
        return null;
    }

    const isProcessing = ["uploading", "streaming"].includes(stage);
    const elapsed = startTimeRef.current
        ? ((Date.now() - startTimeRef.current) / 1000).toFixed(1)
        : "0";

    return (
        <>
            <Head>
                <title>Upload — Exyst</title>
                <meta
                    name="description"
                    content="Upload exam documents for AI analysis and prediction"
                />
            </Head>

            <AppLayout title="Upload Document">
                <div style={{ maxWidth: 640, margin: "0 auto" }}>
                    {/* Upload Card */}
                    <div
                        className="glass-card animate-scale-in"
                        style={{ padding: 32, marginBottom: 24 }}
                    >
                        <h2
                            style={{
                                fontSize: "1.1rem",
                                fontWeight: 700,
                                marginBottom: 8,
                            }}
                        >
                            Upload Exam Document
                        </h2>
                        <p
                            style={{
                                color: "var(--text-muted)",
                                fontSize: "0.85rem",
                                marginBottom: 24,
                            }}
                        >
                            Upload a PDF containing your syllabus and previous
                            year question papers. The AI will classify, analyze,
                            and predict future questions.
                        </p>

                        {/* Drop Zone */}
                        <div
                            onDragEnter={handleDrag}
                            onDragLeave={handleDrag}
                            onDragOver={handleDrag}
                            onDrop={handleDrop}
                            onClick={() =>
                                document.getElementById("file-input")?.click()
                            }
                            style={{
                                border: `2px dashed ${
                                    dragActive
                                        ? "var(--accent-indigo)"
                                        : file
                                          ? "var(--accent-emerald)"
                                          : "var(--border-subtle)"
                                }`,
                                borderRadius: "var(--radius-lg)",
                                padding: "48px 24px",
                                textAlign: "center",
                                cursor: isProcessing ? "default" : "pointer",
                                transition: "all 0.3s ease",
                                background: dragActive
                                    ? "rgba(99, 102, 241, 0.05)"
                                    : file
                                      ? "rgba(34, 197, 94, 0.03)"
                                      : "transparent",
                                pointerEvents: isProcessing ? "none" : "auto",
                            }}
                        >
                            <input
                                id="file-input"
                                type="file"
                                accept=".pdf"
                                onChange={handleFileChange}
                                style={{ display: "none" }}
                            />

                            <div style={{ fontSize: "3rem", marginBottom: 16 }}>
                                {file ? "✅" : dragActive ? "📥" : "📄"}
                            </div>

                            {file ? (
                                <div>
                                    <p
                                        style={{
                                            fontWeight: 600,
                                            color: "var(--text-primary)",
                                            margin: 0,
                                        }}
                                    >
                                        {file.name}
                                    </p>
                                    <p
                                        style={{
                                            color: "var(--text-muted)",
                                            fontSize: "0.8rem",
                                            marginTop: 4,
                                        }}
                                    >
                                        {(file.size / 1024 / 1024).toFixed(2)}{" "}
                                        MB
                                    </p>
                                </div>
                            ) : (
                                <div>
                                    <p
                                        style={{
                                            fontWeight: 600,
                                            color: "var(--text-primary)",
                                            margin: 0,
                                        }}
                                    >
                                        Drop your PDF here or click to browse
                                    </p>
                                    <p
                                        style={{
                                            color: "var(--text-muted)",
                                            fontSize: "0.8rem",
                                            marginTop: 4,
                                        }}
                                    >
                                        Max 50MB • PDF files only
                                    </p>
                                </div>
                            )}
                        </div>

                        {/* Error */}
                        {error && (
                            <div
                                style={{
                                    marginTop: 16,
                                    padding: "12px 16px",
                                    borderRadius: "var(--radius-sm)",
                                    background: "rgba(239, 68, 68, 0.1)",
                                    border: "1px solid rgba(239, 68, 68, 0.2)",
                                    color: "#ef4444",
                                    fontSize: "0.85rem",
                                }}
                            >
                                {error}
                            </div>
                        )}

                        {/* Submit Button */}
                        <button
                            className="btn-primary"
                            onClick={handleSubmit}
                            disabled={!file || isProcessing}
                            style={{
                                width: "100%",
                                marginTop: 20,
                                padding: "14px",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                gap: 10,
                                fontSize: "0.9rem",
                            }}
                        >
                            {isProcessing && <span className="spinner" />}
                            {isProcessing
                                ? currentDetail || "Processing..."
                                : "🚀 Analyze & Predict"}
                        </button>
                    </div>

                    {/* Live Pipeline Progress */}
                    {stage !== "idle" && (
                        <div
                            className="glass-card animate-fade-in"
                            style={{ padding: 24 }}
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
                                        fontSize: "0.95rem",
                                        fontWeight: 700,
                                        margin: 0,
                                    }}
                                >
                                    AI Pipeline Progress
                                </h3>
                                {isProcessing && (
                                    <span
                                        style={{
                                            fontSize: "0.75rem",
                                            color: "var(--text-muted)",
                                            fontFamily: "monospace",
                                        }}
                                    >
                                        {elapsed}s elapsed
                                    </span>
                                )}
                            </div>

                            {/* Progress Bar */}
                            <div
                                style={{
                                    width: "100%",
                                    height: 6,
                                    background: "rgba(255, 255, 255, 0.05)",
                                    borderRadius: 3,
                                    marginBottom: 20,
                                    overflow: "hidden",
                                }}
                            >
                                <div
                                    style={{
                                        width: `${progress}%`,
                                        height: "100%",
                                        background:
                                            stage === "error"
                                                ? "#ef4444"
                                                : stage === "complete"
                                                  ? "var(--accent-emerald)"
                                                  : "var(--gradient-main)",
                                        borderRadius: 3,
                                        transition: "width 0.5s ease",
                                    }}
                                />
                            </div>

                            {/* Current Stage */}
                            {isProcessing && currentStage && (
                                <div
                                    style={{
                                        display: "flex",
                                        alignItems: "center",
                                        gap: 10,
                                        marginBottom: 16,
                                        padding: "10px 14px",
                                        borderRadius: "var(--radius-sm)",
                                        background: "rgba(99, 102, 241, 0.06)",
                                        border: "1px solid rgba(99, 102, 241, 0.15)",
                                    }}
                                >
                                    <span
                                        className="spinner"
                                        style={{
                                            width: 16,
                                            height: 16,
                                            borderWidth: 2,
                                            flexShrink: 0,
                                        }}
                                    />
                                    <span
                                        style={{
                                            fontSize: "0.85rem",
                                            fontWeight: 600,
                                            color: "var(--accent-indigo)",
                                        }}
                                    >
                                        {STAGE_LABELS[currentStage] ||
                                            currentStage}
                                    </span>
                                    <span
                                        style={{
                                            fontSize: "0.75rem",
                                            color: "var(--text-muted)",
                                            marginLeft: "auto",
                                        }}
                                    >
                                        {progress}%
                                    </span>
                                </div>
                            )}

                            {/* Completion info */}
                            {stage === "complete" && completionData && (
                                <div
                                    style={{
                                        padding: "14px 16px",
                                        borderRadius: "var(--radius-sm)",
                                        background: "rgba(34, 197, 94, 0.06)",
                                        border: "1px solid rgba(34, 197, 94, 0.2)",
                                        marginBottom: 16,
                                        display: "flex",
                                        alignItems: "center",
                                        gap: 10,
                                    }}
                                >
                                    <span style={{ fontSize: "1.2rem" }}>
                                        ✅
                                    </span>
                                    <div>
                                        <p
                                            style={{
                                                margin: 0,
                                                fontWeight: 600,
                                                fontSize: "0.9rem",
                                                color: "var(--accent-emerald)",
                                            }}
                                        >
                                            Pipeline Complete!
                                        </p>
                                        <p
                                            style={{
                                                margin: "4px 0 0",
                                                fontSize: "0.8rem",
                                                color: "var(--text-muted)",
                                            }}
                                        >
                                            Confidence:{" "}
                                            {(
                                                (completionData.overall_confidence ||
                                                    0) * 100
                                            ).toFixed(0)}
                                            % • Generated in{" "}
                                            {completionData.generation_time_seconds?.toFixed(
                                                1,
                                            )}
                                            s • Redirecting...
                                        </p>
                                    </div>
                                </div>
                            )}

                            {/* Stage Timeline */}
                            <div
                                style={{
                                    display: "flex",
                                    flexDirection: "column",
                                    gap: 6,
                                }}
                            >
                                {stageLogs.map((log, i) => {
                                    const isLast = i === stageLogs.length - 1;
                                    const isCurrent = isLast && isProcessing;
                                    return (
                                        <div
                                            key={i}
                                            style={{
                                                display: "flex",
                                                alignItems: "center",
                                                gap: 10,
                                                opacity: isCurrent ? 1 : 0.7,
                                            }}
                                        >
                                            <span
                                                style={{
                                                    fontSize: "0.75rem",
                                                    width: 16,
                                                    textAlign: "center",
                                                }}
                                            >
                                                {isCurrent ? "🔄" : "✅"}
                                            </span>
                                            <span
                                                style={{
                                                    flex: 1,
                                                    fontSize: "0.8rem",
                                                    color: isCurrent
                                                        ? "var(--text-primary)"
                                                        : "var(--text-muted)",
                                                    fontWeight: isCurrent
                                                        ? 600
                                                        : 400,
                                                }}
                                            >
                                                {STAGE_LABELS[log.stage] ||
                                                    log.detail}
                                            </span>
                                            {log.duration !== undefined && (
                                                <span
                                                    style={{
                                                        fontSize: "0.7rem",
                                                        color: "var(--text-muted)",
                                                        fontFamily: "monospace",
                                                    }}
                                                >
                                                    {(
                                                        log.duration / 1000
                                                    ).toFixed(1)}
                                                    s
                                                </span>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}
                </div>
            </AppLayout>
        </>
    );
}
