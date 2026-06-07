/**
 * Upload page — drag & drop upload, triggers analysis + prediction pipeline.
 */

import React, { useState, useCallback } from "react";
import Head from "next/head";
import { useRouter } from "next/router";
import AppLayout from "@/components/layout/AppLayout";
import { useAuth } from "@/lib/auth-context";
import { documents, analysis, predictions } from "@/lib/api";

type PipelineStage = "idle" | "uploading" | "analyzing" | "predicting" | "complete" | "error";

const stageLabels: Record<PipelineStage, string> = {
  idle: "Ready to upload",
  uploading: "Uploading document...",
  analyzing: "Running AI analysis pipeline...",
  predicting: "Generating prediction...",
  complete: "Complete!",
  error: "An error occurred",
};

export default function UploadPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [stage, setStage] = useState<PipelineStage>("idle");
  const [error, setError] = useState("");
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") setDragActive(true);
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

    try {
      // Stage 1: Upload
      setStage("uploading");
      setProgress(20);
      const doc = await documents.upload(file);
      setDocumentId(doc.id);

      // Stage 2: Analysis
      setStage("analyzing");
      setProgress(50);
      await analysis.run(doc.id);

      // Stage 3: Prediction
      setStage("predicting");
      setProgress(80);
      await predictions.generate(doc.id);

      // Complete
      setStage("complete");
      setProgress(100);

      // Navigate to results after a brief moment
      setTimeout(() => {
        router.push(`/documents/${doc.id}`);
      }, 1500);
    } catch (err) {
      setStage("error");
      setError(err instanceof Error ? err.message : "Pipeline failed");
    }
  };

  if (authLoading || !user) {
    if (!authLoading && !user) router.push("/login");
    return null;
  }

  const isProcessing = ["uploading", "analyzing", "predicting"].includes(stage);

  return (
    <>
      <Head>
        <title>Upload — Exyst</title>
        <meta name="description" content="Upload exam documents for AI analysis and prediction" />
      </Head>

      <AppLayout title="Upload Document">
        <div style={{ maxWidth: 640, margin: "0 auto" }}>
          {/* Upload Card */}
          <div
            className="glass-card animate-scale-in"
            style={{ padding: 32, marginBottom: 24 }}
          >
            <h2 style={{ fontSize: "1.1rem", fontWeight: 700, marginBottom: 8 }}>
              Upload Exam Document
            </h2>
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginBottom: 24 }}>
              Upload a PDF containing your syllabus and previous year question papers.
              The AI will classify, analyze, and predict future questions.
            </p>

            {/* Drop Zone */}
            <div
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => document.getElementById("file-input")?.click()}
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
                    {(file.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
              ) : (
                <div>
                  <p style={{ fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>
                    Drop your PDF here or click to browse
                  </p>
                  <p style={{ color: "var(--text-muted)", fontSize: "0.8rem", marginTop: 4 }}>
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
              {isProcessing ? stageLabels[stage] : "🚀 Analyze & Predict"}
            </button>
          </div>

          {/* Progress Pipeline */}
          {stage !== "idle" && (
            <div className="glass-card animate-fade-in" style={{ padding: 24 }}>
              <h3 style={{ fontSize: "0.95rem", fontWeight: 700, marginBottom: 16 }}>
                AI Pipeline Progress
              </h3>

              {/* Progress Bar */}
              <div
                style={{
                  width: "100%",
                  height: 6,
                  background: "rgba(255, 255, 255, 0.05)",
                  borderRadius: 3,
                  marginBottom: 24,
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    width: `${progress}%`,
                    height: "100%",
                    background: stage === "error" ? "#ef4444" : "var(--gradient-main)",
                    borderRadius: 3,
                    transition: "width 0.6s ease",
                  }}
                />
              </div>

              {/* Pipeline Steps */}
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <PipelineStep
                  label="Upload Document"
                  status={
                    stage === "uploading"
                      ? "active"
                      : progress >= 20
                      ? "complete"
                      : "pending"
                  }
                />
                <PipelineStep
                  label="AI Analysis (classify → extract → analyze)"
                  status={
                    stage === "analyzing"
                      ? "active"
                      : progress >= 50
                      ? "complete"
                      : "pending"
                  }
                />
                <PipelineStep
                  label="Generate Prediction & Score"
                  status={
                    stage === "predicting"
                      ? "active"
                      : progress >= 80
                      ? "complete"
                      : "pending"
                  }
                />
                <PipelineStep
                  label="Complete"
                  status={stage === "complete" ? "complete" : "pending"}
                />
              </div>
            </div>
          )}
        </div>
      </AppLayout>
    </>
  );
}

function PipelineStep({
  label,
  status,
}: {
  label: string;
  status: "pending" | "active" | "complete";
}) {
  const icons = {
    pending: "⬜",
    active: "🔄",
    complete: "✅",
  };
  const colors = {
    pending: "var(--text-muted)",
    active: "var(--accent-indigo)",
    complete: "var(--accent-emerald)",
  };

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
      <span style={{ fontSize: "1rem" }}>{icons[status]}</span>
      <span
        style={{
          color: colors[status],
          fontSize: "0.85rem",
          fontWeight: status === "active" ? 600 : 400,
        }}
      >
        {label}
      </span>
      {status === "active" && (
        <span className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />
      )}
    </div>
  );
}
