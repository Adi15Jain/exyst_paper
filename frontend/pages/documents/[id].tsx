/**
 * Document detail page — analysis results, predicted paper, confidence scores.
 */

import React, { useEffect, useState } from "react";
import Head from "next/head";
import { useRouter } from "next/router";
import AppLayout from "@/components/layout/AppLayout";
import { useAuth } from "@/lib/auth-context";
import {
    documents as documentsApi,
    analysis as analysisApi,
    predictions as predictionsApi,
    analytics as analyticsApi,
    DocumentData,
    AnalysisResult,
    PredictionData,
} from "@/lib/api";

export default function DocumentDetailPage() {
    const router = useRouter();
    const { id } = router.query;
    const { user, loading: authLoading } = useAuth();

    const [doc, setDoc] = useState<DocumentData | null>(null);
    const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(
        null,
    );
    const [prediction, setPrediction] = useState<PredictionData | null>(null);
    const [topicData, setTopicData] = useState<any>(null);
    const [activeTab, setActiveTab] = useState<
        "prediction" | "analysis" | "confidence"
    >("prediction");
    const [loading, setLoading] = useState(true);
    const [regenerating, setRegenerating] = useState(false);
    const [actionError, setActionError] = useState("");

    const handleRegenerate = async () => {
        if (!id) return;
        setRegenerating(true);
        setActionError("");
        try {
            const docId = id as string;
            const newPred = await predictionsApi.generate(docId);
            setPrediction(newPred);
            const topicFreq = await analyticsApi
                .topicFrequency(docId)
                .catch(() => null);
            if (topicFreq) setTopicData(topicFreq);
        } catch (err) {
            setActionError(
                err instanceof Error
                    ? err.message
                    : "Failed to generate prediction",
            );
        } finally {
            setRegenerating(false);
        }
    };

    useEffect(() => {
        if (authLoading || !user || !id) return;

        const docId = id as string;

        Promise.all([
            documentsApi.get(docId).catch(() => null),
            analysisApi.result(docId).catch(() => null),
            predictionsApi.get(docId).catch(() => null),
            analyticsApi.topicFrequency(docId).catch(() => null),
        ]).then(([docData, analysisData, predData, topicFreq]) => {
            if (docData) setDoc(docData);
            if (analysisData) setAnalysisResult(analysisData);
            if (predData) setPrediction(predData);
            if (topicFreq) setTopicData(topicFreq);
            setLoading(false);
        });
    }, [user, authLoading, id]);

    if (authLoading || !user) {
        if (!authLoading && !user) router.push("/login");
        return null;
    }

    if (loading) {
        return (
            <AppLayout title="Loading...">
                <div style={{ textAlign: "center", padding: "80px 0" }}>
                    <span
                        className="spinner"
                        style={{
                            width: 40,
                            height: 40,
                            margin: "0 auto",
                            display: "block",
                        }}
                    />
                </div>
            </AppLayout>
        );
    }

    const paper = prediction?.predicted_paper;
    const confidence = prediction?.confidence;

    return (
        <>
            <Head>
                <title>{doc?.original_filename || "Document"} — Exyst</title>
            </Head>

            <AppLayout title={doc?.original_filename || "Document Detail"}>
                {actionError && (
                    <div
                        role="alert"
                        style={{
                            marginBottom: 20,
                            padding: "12px 16px",
                            borderRadius: "var(--radius-sm)",
                            background: "rgba(239, 68, 68, 0.1)",
                            border: "1px solid rgba(239, 68, 68, 0.2)",
                            color: "#ef4444",
                            fontSize: "0.85rem",
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                            gap: 12,
                        }}
                    >
                        <span>{actionError}</span>
                        <button
                            onClick={() => setActionError("")}
                            style={{
                                background: "none",
                                border: "none",
                                color: "#ef4444",
                                cursor: "pointer",
                                fontSize: "1rem",
                                lineHeight: 1,
                            }}
                            aria-label="Dismiss error"
                        >
                            ✕
                        </button>
                    </div>
                )}

                {/* Summary Bar */}
                <div
                    style={{
                        display: "grid",
                        gridTemplateColumns:
                            "repeat(auto-fit, minmax(160px, 1fr))",
                        gap: 16,
                        marginBottom: 28,
                    }}
                >
                    <MiniStat label="Status" value={doc?.status || "—"} />
                    <MiniStat
                        label="Pages"
                        value={
                            analysisResult?.num_pages_processed?.toString() ||
                            "—"
                        }
                    />
                    <MiniStat
                        label="Papers Found"
                        value={
                            analysisResult?.num_papers_found?.toString() || "—"
                        }
                    />
                    <MiniStat
                        label="Confidence"
                        value={
                            prediction?.overall_confidence
                                ? `${(prediction.overall_confidence * 100).toFixed(0)}%`
                                : "—"
                        }
                        highlight
                    />
                </div>

                {/* Tabs */}
                <div
                    style={{
                        display: "flex",
                        gap: 4,
                        marginBottom: 24,
                        borderBottom: "1px solid var(--border-subtle)",
                        paddingBottom: 0,
                    }}
                >
                    {(["prediction", "analysis", "confidence"] as const).map(
                        (tab) => (
                            <button
                                key={tab}
                                onClick={() => setActiveTab(tab)}
                                style={{
                                    padding: "10px 20px",
                                    background: "transparent",
                                    border: "none",
                                    borderBottom:
                                        activeTab === tab
                                            ? "2px solid var(--accent-indigo)"
                                            : "2px solid transparent",
                                    color:
                                        activeTab === tab
                                            ? "var(--text-primary)"
                                            : "var(--text-muted)",
                                    fontWeight: activeTab === tab ? 600 : 400,
                                    fontSize: "0.85rem",
                                    cursor: "pointer",
                                    transition: "all 0.2s ease",
                                    textTransform: "capitalize",
                                }}
                            >
                                {tab === "prediction"
                                    ? "📝 Predicted Paper"
                                    : tab === "analysis"
                                      ? "🔬 Analysis"
                                      : "📊 Confidence"}
                            </button>
                        ),
                    )}
                </div>

                {/* Tab Content */}
                {activeTab === "prediction" && paper && (
                    <div className="animate-fade-in">
                        {paper.is_fallback ? (
                            <div
                                className="glass-card"
                                style={{
                                    padding: 40,
                                    textAlign: "center",
                                    marginBottom: 20,
                                    border: "1px solid rgba(239, 68, 68, 0.2)",
                                    background: "rgba(239, 68, 68, 0.02)",
                                }}
                            >
                                <span
                                    style={{
                                        fontSize: "3rem",
                                        display: "block",
                                        marginBottom: 16,
                                    }}
                                >
                                    ⚠️
                                </span>
                                <h3
                                    style={{
                                        fontSize: "1.2rem",
                                        fontWeight: 700,
                                        marginBottom: 10,
                                        color: "var(--text-primary)",
                                    }}
                                >
                                    Prediction Generation Failed
                                </h3>
                                <p
                                    style={{
                                        color: "var(--text-muted)",
                                        fontSize: "0.85rem",
                                        lineHeight: 1.6,
                                        marginBottom: 28,
                                        maxWidth: 580,
                                        margin: "0 auto 28px",
                                    }}
                                >
                                    {paper.error_message ||
                                        "An unexpected error occurred during prediction generation."}
                                </p>
                                <button
                                    className="btn-primary"
                                    onClick={handleRegenerate}
                                    disabled={regenerating}
                                    style={{
                                        padding: "10px 24px",
                                        display: "inline-flex",
                                        alignItems: "center",
                                        gap: 8,
                                        fontSize: "0.85rem",
                                    }}
                                >
                                    {regenerating && (
                                        <span
                                            className="spinner"
                                            style={{ width: 14, height: 14 }}
                                        />
                                    )}
                                    {regenerating
                                        ? "Regenerating..."
                                        : "Regenerate Prediction"}
                                </button>
                            </div>
                        ) : (
                            <>
                                {/* Paper Header */}
                                <div
                                    className="glass-card"
                                    style={{
                                        padding: 24,
                                        marginBottom: 20,
                                    }}
                                >
                                    <div
                                        style={{
                                            display: "flex",
                                            justifyContent: "space-between",
                                            alignItems: "center",
                                            marginBottom: 12,
                                            flexWrap: "wrap",
                                            gap: 12,
                                        }}
                                    >
                                        <h2
                                            style={{
                                                fontSize: "1.2rem",
                                                fontWeight: 800,
                                                margin: 0,
                                            }}
                                        >
                                            {paper.paper_info?.title ||
                                                "Predicted Question Paper"}
                                        </h2>
                                        <button
                                            className="btn-secondary"
                                            onClick={handleRegenerate}
                                            disabled={regenerating}
                                            style={{
                                                padding: "6px 12px",
                                                fontSize: "0.8rem",
                                                display: "inline-flex",
                                                alignItems: "center",
                                                gap: 6,
                                                margin: 0,
                                            }}
                                        >
                                            {regenerating && (
                                                <span
                                                    className="spinner"
                                                    style={{
                                                        width: 12,
                                                        height: 12,
                                                    }}
                                                />
                                            )}
                                            {regenerating
                                                ? "Regenerating..."
                                                : "🔄 Regenerate"}
                                        </button>
                                    </div>
                                    <p
                                        style={{
                                            color: "var(--accent-violet)",
                                            fontSize: "1rem",
                                            margin: "4px 0 12px",
                                            textAlign: "left",
                                        }}
                                    >
                                        {paper.paper_info?.subject || ""}
                                    </p>
                                    <div
                                        style={{
                                            display: "flex",
                                            justifyContent: "flex-start",
                                            gap: 24,
                                            color: "var(--text-muted)",
                                            fontSize: "0.8rem",
                                        }}
                                    >
                                        <span>
                                            📅{" "}
                                            {paper.paper_info?.academic_year ||
                                                ""}
                                        </span>
                                        <span>
                                            ⏱ {paper.paper_info?.duration || ""}
                                        </span>
                                        <span>
                                            📊 Max Marks:{" "}
                                            {paper.paper_info?.max_marks || ""}
                                        </span>
                                    </div>
                                </div>

                                {/* Sections */}
                                {paper.sections?.map(
                                    (section: any, sIdx: number) => (
                                        <div
                                            key={sIdx}
                                            className="glass-card"
                                            style={{
                                                padding: 24,
                                                marginBottom: 16,
                                            }}
                                        >
                                            <div
                                                style={{
                                                    display: "flex",
                                                    justifyContent:
                                                        "space-between",
                                                    alignItems: "center",
                                                    marginBottom: 16,
                                                }}
                                            >
                                                <div>
                                                    <h3
                                                        style={{
                                                            fontSize: "1rem",
                                                            fontWeight: 700,
                                                            margin: 0,
                                                        }}
                                                    >
                                                        {section.section_name}:{" "}
                                                        {section.title}
                                                    </h3>
                                                    <p
                                                        style={{
                                                            color: "var(--text-muted)",
                                                            fontSize: "0.8rem",
                                                            margin: "4px 0 0",
                                                        }}
                                                    >
                                                        {section.description}
                                                    </p>
                                                </div>
                                                <span className="badge badge-info">
                                                    {section.total_marks} marks
                                                </span>
                                            </div>

                                            <div
                                                style={{
                                                    display: "flex",
                                                    flexDirection: "column",
                                                    gap: 12,
                                                }}
                                            >
                                                {section.questions?.map(
                                                    (q: any, qIdx: number) => (
                                                        <div
                                                            key={qIdx}
                                                            style={{
                                                                padding:
                                                                    "14px 16px",
                                                                borderRadius:
                                                                    "var(--radius-md)",
                                                                background:
                                                                    "rgba(255, 255, 255, 0.02)",
                                                                borderLeft: `3px solid ${getConfidenceColor(q.confidence || 0.5)}`,
                                                            }}
                                                        >
                                                            <div
                                                                style={{
                                                                    display:
                                                                        "flex",
                                                                    justifyContent:
                                                                        "space-between",
                                                                    alignItems:
                                                                        "flex-start",
                                                                }}
                                                            >
                                                                <div
                                                                    style={{
                                                                        flex: 1,
                                                                        paddingRight: 16,
                                                                    }}
                                                                >
                                                                    <p
                                                                        style={{
                                                                            margin: 0,
                                                                            fontSize:
                                                                                "0.85rem",
                                                                            lineHeight: 1.5,
                                                                        }}
                                                                    >
                                                                        <strong>
                                                                            Q
                                                                            {
                                                                                q.question_number
                                                                            }
                                                                            .
                                                                        </strong>{" "}
                                                                        {
                                                                            q.question_text
                                                                        }
                                                                    </p>
                                                                    {q.topic && (
                                                                        <span
                                                                            style={{
                                                                                display:
                                                                                    "inline-block",
                                                                                marginTop: 6,
                                                                                fontSize:
                                                                                    "0.7rem",
                                                                                padding:
                                                                                    "2px 8px",
                                                                                borderRadius: 999,
                                                                                background:
                                                                                    "rgba(99, 102, 241, 0.1)",
                                                                                color: "var(--accent-indigo)",
                                                                            }}
                                                                        >
                                                                            {
                                                                                q.topic
                                                                            }
                                                                        </span>
                                                                    )}
                                                                    {q.parts &&
                                                                        q.parts
                                                                            .length >
                                                                            0 && (
                                                                            <QuestionParts
                                                                                parts={
                                                                                    q.parts
                                                                                }
                                                                            />
                                                                        )}
                                                                    {q.or_choice &&
                                                                        (q.or_choice
                                                                            .question_text ||
                                                                            (q
                                                                                .or_choice
                                                                                .parts &&
                                                                                q
                                                                                    .or_choice
                                                                                    .parts
                                                                                    .length >
                                                                                    0)) && (
                                                                            <div
                                                                                style={{
                                                                                    marginTop: 8,
                                                                                }}
                                                                            >
                                                                                <span
                                                                                    style={{
                                                                                        fontSize:
                                                                                            "0.7rem",
                                                                                        fontWeight: 700,
                                                                                        color: "var(--text-muted)",
                                                                                        letterSpacing:
                                                                                            "0.05em",
                                                                                    }}
                                                                                >
                                                                                    — OR —
                                                                                </span>
                                                                                {q
                                                                                    .or_choice
                                                                                    .question_text && (
                                                                                    <p
                                                                                        style={{
                                                                                            margin: "4px 0 0",
                                                                                            fontSize:
                                                                                                "0.85rem",
                                                                                            lineHeight: 1.5,
                                                                                        }}
                                                                                    >
                                                                                        {
                                                                                            q
                                                                                                .or_choice
                                                                                                .question_text
                                                                                        }
                                                                                    </p>
                                                                                )}
                                                                                {q
                                                                                    .or_choice
                                                                                    .parts &&
                                                                                    q
                                                                                        .or_choice
                                                                                        .parts
                                                                                        .length >
                                                                                        0 && (
                                                                                        <QuestionParts
                                                                                            parts={
                                                                                                q
                                                                                                    .or_choice
                                                                                                    .parts
                                                                                            }
                                                                                        />
                                                                                    )}
                                                                            </div>
                                                                        )}
                                                                </div>
                                                                <div
                                                                    style={{
                                                                        textAlign:
                                                                            "right",
                                                                        flexShrink: 0,
                                                                    }}
                                                                >
                                                                    <span
                                                                        style={{
                                                                            fontSize:
                                                                                "0.75rem",
                                                                            fontWeight: 700,
                                                                            color: "var(--text-secondary)",
                                                                            background:
                                                                                "rgba(255,255,255,0.05)",
                                                                            padding:
                                                                                "4px 10px",
                                                                            borderRadius:
                                                                                "var(--radius-sm)",
                                                                        }}
                                                                    >
                                                                        {
                                                                            q.marks
                                                                        }{" "}
                                                                        marks
                                                                    </span>
                                                                    {q.confidence !==
                                                                        undefined && (
                                                                        <p
                                                                            style={{
                                                                                margin: "4px 0 0",
                                                                                fontSize:
                                                                                    "0.7rem",
                                                                                color: getConfidenceColor(
                                                                                    q.confidence,
                                                                                ),
                                                                            }}
                                                                        >
                                                                            {(
                                                                                q.confidence *
                                                                                100
                                                                            ).toFixed(
                                                                                0,
                                                                            )}
                                                                            %
                                                                            conf
                                                                        </p>
                                                                    )}
                                                                </div>
                                                            </div>
                                                        </div>
                                                    ),
                                                )}
                                            </div>
                                        </div>
                                    ),
                                )}
                            </>
                        )}
                    </div>
                )}

                {activeTab === "analysis" && (
                    <div className="animate-fade-in">
                        {/* Topic Frequency Chart */}
                        {topicData?.chart_data?.labels?.length > 0 && (
                            <div
                                className="glass-card"
                                style={{ padding: 24, marginBottom: 20 }}
                            >
                                <h3
                                    style={{
                                        fontSize: "1rem",
                                        fontWeight: 700,
                                        marginBottom: 20,
                                    }}
                                >
                                    📊 Topic Frequency
                                </h3>
                                <div
                                    style={{
                                        display: "flex",
                                        flexDirection: "column",
                                        gap: 10,
                                    }}
                                >
                                    {topicData.chart_data.labels.map(
                                        (label: string, i: number) => (
                                            <div
                                                key={i}
                                                style={{
                                                    display: "flex",
                                                    alignItems: "center",
                                                    gap: 12,
                                                }}
                                            >
                                                <span
                                                    style={{
                                                        width: 140,
                                                        fontSize: "0.8rem",
                                                        color: "var(--text-secondary)",
                                                        flexShrink: 0,
                                                        textOverflow:
                                                            "ellipsis",
                                                        overflow: "hidden",
                                                        whiteSpace: "nowrap",
                                                    }}
                                                >
                                                    {label}
                                                </span>
                                                <div
                                                    style={{
                                                        flex: 1,
                                                        position: "relative",
                                                    }}
                                                >
                                                    <div
                                                        className="bar-chart-bar"
                                                        style={{
                                                            width: `${Math.max(
                                                                (topicData
                                                                    .chart_data
                                                                    .values[i] /
                                                                    Math.max(
                                                                        ...topicData
                                                                            .chart_data
                                                                            .values,
                                                                    )) *
                                                                    100,
                                                                4,
                                                            )}%`,
                                                            background:
                                                                topicData
                                                                    .chart_data
                                                                    .colors[i],
                                                        }}
                                                    />
                                                </div>
                                                <span
                                                    style={{
                                                        width: 60,
                                                        textAlign: "right",
                                                        fontSize: "0.75rem",
                                                        color: "var(--text-muted)",
                                                        flexShrink: 0,
                                                    }}
                                                >
                                                    {
                                                        topicData.chart_data
                                                            .values[i]
                                                    }
                                                    x (
                                                    {
                                                        topicData.chart_data
                                                            .percentages[i]
                                                    }
                                                    %)
                                                </span>
                                                <TrendBadge
                                                    trend={
                                                        topicData.chart_data
                                                            .trends[i]
                                                    }
                                                />
                                            </div>
                                        ),
                                    )}
                                </div>
                            </div>
                        )}

                        {/* Analysis Metadata */}
                        <div className="glass-card" style={{ padding: 24 }}>
                            <h3
                                style={{
                                    fontSize: "1rem",
                                    fontWeight: 700,
                                    marginBottom: 16,
                                }}
                            >
                                Analysis Details
                            </h3>
                            <div
                                style={{
                                    display: "grid",
                                    gridTemplateColumns:
                                        "repeat(auto-fit, minmax(200px, 1fr))",
                                    gap: 12,
                                }}
                            >
                                <MetaItem
                                    label="Model Used"
                                    value={analysisResult?.model_used || "—"}
                                />
                                <MetaItem
                                    label="Processing Time"
                                    value={
                                        analysisResult?.processing_time_seconds
                                            ? `${analysisResult.processing_time_seconds.toFixed(1)}s`
                                            : "—"
                                    }
                                />
                                <MetaItem
                                    label="Completed"
                                    value={
                                        analysisResult?.completed_at
                                            ? new Date(
                                                  analysisResult.completed_at,
                                              ).toLocaleString()
                                            : "—"
                                    }
                                />
                            </div>
                        </div>
                    </div>
                )}

                {activeTab === "confidence" && confidence && (
                    <div className="animate-fade-in">
                        {/* Overall Confidence Ring */}
                        <div
                            className="glass-card"
                            style={{
                                padding: 32,
                                textAlign: "center",
                                marginBottom: 20,
                            }}
                        >
                            <ConfidenceRing
                                value={
                                    confidence.overall_confidence ||
                                    prediction?.overall_confidence ||
                                    0
                                }
                            />
                            <p
                                style={{
                                    color: "var(--text-muted)",
                                    fontSize: "0.85rem",
                                    marginTop: 12,
                                }}
                            >
                                Overall Prediction Confidence
                            </p>
                        </div>

                        {/* Factor Breakdown */}
                        <div
                            className="glass-card"
                            style={{ padding: 24, marginBottom: 20 }}
                        >
                            <h3
                                style={{
                                    fontSize: "1rem",
                                    fontWeight: 700,
                                    marginBottom: 20,
                                }}
                            >
                                Confidence Factors
                            </h3>
                            <div
                                style={{
                                    display: "flex",
                                    flexDirection: "column",
                                    gap: 16,
                                }}
                            >
                                <ConfidenceBar
                                    label="Topic Coverage"
                                    value={confidence.topic_coverage_score || 0}
                                    description="How many syllabus topics are represented"
                                />
                                <ConfidenceBar
                                    label="Historical Alignment"
                                    value={
                                        confidence.historical_alignment_score ||
                                        0
                                    }
                                    description="Match with past exam patterns"
                                />
                                <ConfidenceBar
                                    label="Question Quality"
                                    value={
                                        confidence.question_quality_score || 0
                                    }
                                    description="Well-formedness and completeness"
                                />
                                <ConfidenceBar
                                    label="Marks Distribution"
                                    value={
                                        confidence.marks_distribution_score || 0
                                    }
                                    description="Alignment of marks pattern with historical papers"
                                />
                            </div>
                        </div>

                        {/* Per-question confidence */}
                        {confidence.per_question_confidence?.length > 0 && (
                            <div className="glass-card" style={{ padding: 24 }}>
                                <h3
                                    style={{
                                        fontSize: "1rem",
                                        fontWeight: 700,
                                        marginBottom: 16,
                                    }}
                                >
                                    Per-Question Confidence
                                </h3>
                                <div
                                    style={{
                                        display: "flex",
                                        flexDirection: "column",
                                        gap: 8,
                                    }}
                                >
                                    {confidence.per_question_confidence.map(
                                        (q: any, i: number) => (
                                            <div
                                                key={i}
                                                style={{
                                                    display: "flex",
                                                    alignItems: "center",
                                                    justifyContent:
                                                        "space-between",
                                                    padding: "8px 12px",
                                                    borderRadius:
                                                        "var(--radius-sm)",
                                                    background:
                                                        "rgba(255,255,255,0.02)",
                                                }}
                                            >
                                                <span
                                                    style={{
                                                        fontSize: "0.8rem",
                                                        color: "var(--text-secondary)",
                                                    }}
                                                >
                                                    Q{q.question_number} —{" "}
                                                    {q.topic}
                                                </span>
                                                <span
                                                    style={{
                                                        fontSize: "0.8rem",
                                                        fontWeight: 700,
                                                        color: getConfidenceColor(
                                                            q.confidence,
                                                        ),
                                                    }}
                                                >
                                                    {(
                                                        q.confidence * 100
                                                    ).toFixed(0)}
                                                    %
                                                </span>
                                            </div>
                                        ),
                                    )}
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {/* No prediction yet */}
                {!prediction && !loading && (
                    <div
                        className="glass-card"
                        style={{ padding: "60px 24px", textAlign: "center" }}
                    >
                        <p style={{ fontSize: "2.5rem", marginBottom: 12 }}>
                            🔮
                        </p>
                        <p style={{ fontSize: "1.1rem", fontWeight: 600 }}>
                            No prediction generated yet
                        </p>
                        <p
                            style={{
                                color: "var(--text-muted)",
                                marginBottom: 20,
                            }}
                        >
                            Generate a predicted question paper using AI based on the syllabus and past papers.
                        </p>
                        <button
                            className="btn-primary"
                            onClick={handleRegenerate}
                            disabled={regenerating}
                            style={{
                                padding: "10px 24px",
                                display: "inline-flex",
                                alignItems: "center",
                                gap: 8,
                                fontSize: "0.85rem",
                                margin: "0 auto",
                            }}
                        >
                            {regenerating && <span className="spinner" style={{ width: 14, height: 14 }} />}
                            {regenerating ? "Generating..." : "Generate Prediction"}
                        </button>
                    </div>
                )}
            </AppLayout>
        </>
    );
}

// --- Helper Components ---

function QuestionParts({ parts }: { parts: any[] }) {
    return (
        <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 4 }}>
            {parts.map((pt: any, i: number) => (
                <div
                    key={i}
                    style={{
                        display: "flex",
                        gap: 8,
                        fontSize: "0.82rem",
                        lineHeight: 1.5,
                        color: "var(--text-secondary)",
                    }}
                >
                    {pt.label && (
                        <span style={{ fontWeight: 600, flexShrink: 0 }}>
                            {pt.label})
                        </span>
                    )}
                    <span style={{ flex: 1 }}>{pt.question_text}</span>
                    {pt.marks ? (
                        <span
                            style={{
                                flexShrink: 0,
                                fontSize: "0.7rem",
                                color: "var(--text-muted)",
                                fontFamily: "monospace",
                            }}
                        >
                            [{pt.marks}]
                        </span>
                    ) : null}
                </div>
            ))}
        </div>
    );
}

function MiniStat({
    label,
    value,
    highlight,
}: {
    label: string;
    value: string;
    highlight?: boolean;
}) {
    return (
        <div className="stat-card">
            <div className="stat-label">{label}</div>
            <div
                className={`stat-value ${highlight ? "text-gradient" : ""}`}
                style={{ fontSize: "1.5rem" }}
            >
                {value}
            </div>
        </div>
    );
}

function MetaItem({ label, value }: { label: string; value: string }) {
    return (
        <div>
            <p
                style={{
                    color: "var(--text-muted)",
                    fontSize: "0.75rem",
                    margin: "0 0 2px",
                }}
            >
                {label}
            </p>
            <p
                style={{
                    color: "var(--text-primary)",
                    fontSize: "0.85rem",
                    margin: 0,
                    fontWeight: 500,
                }}
            >
                {value}
            </p>
        </div>
    );
}

function TrendBadge({ trend }: { trend: string }) {
    const config = {
        rising: { label: "↑", color: "#22c55e" },
        falling: { label: "↓", color: "#ef4444" },
        stable: { label: "→", color: "#6366f1" },
    };
    const c = config[trend as keyof typeof config] || config.stable;
    return (
        <span
            style={{
                color: c.color,
                fontSize: "0.8rem",
                fontWeight: 700,
                width: 20,
                textAlign: "center",
            }}
        >
            {c.label}
        </span>
    );
}

function ConfidenceRing({ value }: { value: number }) {
    const pct = Math.round(value * 100);
    const radius = 52;
    const circumference = 2 * Math.PI * radius;
    const strokeDashoffset = circumference - value * circumference;

    return (
        <div style={{ display: "inline-block", position: "relative" }}>
            <svg
                width="128"
                height="128"
                style={{ transform: "rotate(-90deg)" }}
            >
                <circle
                    cx="64"
                    cy="64"
                    r={radius}
                    stroke="rgba(255,255,255,0.05)"
                    strokeWidth="8"
                    fill="none"
                />
                <circle
                    cx="64"
                    cy="64"
                    r={radius}
                    stroke={getConfidenceColor(value)}
                    strokeWidth="8"
                    fill="none"
                    strokeLinecap="round"
                    strokeDasharray={circumference}
                    strokeDashoffset={strokeDashoffset}
                    style={{ transition: "stroke-dashoffset 1.5s ease" }}
                />
            </svg>
            <div
                style={{
                    position: "absolute",
                    top: "50%",
                    left: "50%",
                    transform: "translate(-50%, -50%)",
                    textAlign: "center",
                }}
            >
                <span
                    style={{
                        fontSize: "1.75rem",
                        fontWeight: 800,
                        color: getConfidenceColor(value),
                    }}
                >
                    {pct}%
                </span>
            </div>
        </div>
    );
}

function ConfidenceBar({
    label,
    value,
    description,
}: {
    label: string;
    value: number;
    description: string;
}) {
    return (
        <div>
            <div
                style={{
                    display: "flex",
                    justifyContent: "space-between",
                    marginBottom: 4,
                }}
            >
                <span
                    style={{
                        fontSize: "0.85rem",
                        fontWeight: 600,
                        color: "var(--text-primary)",
                    }}
                >
                    {label}
                </span>
                <span
                    style={{
                        fontSize: "0.85rem",
                        fontWeight: 700,
                        color: getConfidenceColor(value),
                    }}
                >
                    {(value * 100).toFixed(0)}%
                </span>
            </div>
            <div
                style={{
                    width: "100%",
                    height: 8,
                    background: "rgba(255,255,255,0.05)",
                    borderRadius: 4,
                    overflow: "hidden",
                }}
            >
                <div
                    style={{
                        width: `${value * 100}%`,
                        height: "100%",
                        background: getConfidenceColor(value),
                        borderRadius: 4,
                        transition: "width 1s ease",
                    }}
                />
            </div>
            <p
                style={{
                    color: "var(--text-muted)",
                    fontSize: "0.7rem",
                    marginTop: 4,
                }}
            >
                {description}
            </p>
        </div>
    );
}

function getConfidenceColor(value: number): string {
    if (value >= 0.7) return "#22c55e";
    if (value >= 0.4) return "#f59e0b";
    return "#ef4444";
}
