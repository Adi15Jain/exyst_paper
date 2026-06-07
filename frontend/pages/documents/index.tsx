/**
 * Documents list page.
 */

import React, { useEffect, useState } from "react";
import Head from "next/head";
import { useRouter } from "next/router";
import AppLayout from "@/components/layout/AppLayout";
import { useAuth } from "@/lib/auth-context";
import { documents as documentsApi, DocumentData } from "@/lib/api";

export default function DocumentsPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [docs, setDocs] = useState<DocumentData[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      router.push("/login");
      return;
    }

    documentsApi
      .list(page, 10)
      .then((data) => {
        setDocs(data.documents);
        setTotal(data.total);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user, authLoading, page, router]);

  if (authLoading || !user) return null;

  return (
    <>
      <Head>
        <title>Documents — Exyst</title>
        <meta name="description" content="Manage your uploaded exam documents" />
      </Head>

      <AppLayout title="Documents">
        <div className="animate-fade-in">
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
              <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", margin: 0 }}>
                {total} document{total !== 1 ? "s" : ""} total
              </p>
            </div>
            <button
              className="btn-primary"
              onClick={() => router.push("/upload")}
              style={{ display: "flex", alignItems: "center", gap: 8 }}
            >
              <span>📤</span> Upload New
            </button>
          </div>

          {/* Document List */}
          {loading ? (
            <div style={{ textAlign: "center", padding: "60px 0" }}>
              <span className="spinner" style={{ width: 32, height: 32, margin: "0 auto", display: "block" }} />
              <p style={{ color: "var(--text-muted)", marginTop: 12, fontSize: "0.85rem" }}>
                Loading documents...
              </p>
            </div>
          ) : docs.length === 0 ? (
            <div
              className="glass-card"
              style={{ textAlign: "center", padding: "60px 24px" }}
            >
              <p style={{ fontSize: "3rem", marginBottom: 12 }}>📭</p>
              <p style={{ fontSize: "1.1rem", fontWeight: 600, color: "var(--text-primary)" }}>
                No documents yet
              </p>
              <p style={{ color: "var(--text-muted)", marginBottom: 20, fontSize: "0.9rem" }}>
                Upload your first exam document to get started
              </p>
              <button className="btn-primary" onClick={() => router.push("/upload")}>
                Upload Document
              </button>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
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
                  onClick={() => router.push(`/documents/${doc.id}`)}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                    <div
                      style={{
                        width: 44,
                        height: 44,
                        borderRadius: "var(--radius-md)",
                        background: "var(--gradient-surface)",
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
                        {doc.original_filename || doc.filename}
                      </p>
                      <p style={{ margin: "2px 0 0", color: "var(--text-muted)", fontSize: "0.75rem" }}>
                        Uploaded {new Date(doc.uploaded_at).toLocaleDateString("en-US", {
                          year: "numeric",
                          month: "short",
                          day: "numeric",
                        })}{" "}
                        • {(doc.file_size_bytes / 1024).toFixed(0)} KB
                      </p>
                    </div>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <span
                      className={`badge badge-${
                        doc.status === "completed" ? "success" : doc.status === "failed" ? "error" : "info"
                      }`}
                    >
                      {doc.status}
                    </span>
                    <span style={{ color: "var(--text-muted)", fontSize: "1.2rem" }}>→</span>
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
                style={{ padding: "8px 16px", fontSize: "0.8rem" }}
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
                style={{ padding: "8px 16px", fontSize: "0.8rem" }}
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
