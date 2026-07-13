/**
 * First-run guidance on the dashboard.
 *
 * The problem this solves: a brand-new user lands on a dashboard of zeroes and
 * has no idea what the product is or what to do first. Stat cards answer
 * "how much?" — they never answer "what is this?" or "what now?".
 *
 * So until someone has a prediction, the dashboard leads with a checklist that
 * *is* the product explanation: the three steps, in order, with the next one
 * highlighted and everything else muted. Once they've been through it, this
 * disappears for good and the dashboard becomes the stats view it should be.
 */

import React from "react";
import { useRouter } from "next/router";

interface GettingStartedProps {
    hasCourse: boolean;
    hasDocument: boolean;
    hasPrediction: boolean;
}

interface Step {
    title: string;
    body: string;
    cta: string;
    href: string;
    done: boolean;
}

export default function GettingStarted({
    hasCourse,
    hasDocument,
    hasPrediction,
}: GettingStartedProps) {
    const router = useRouter();

    const steps: Step[] = [
        {
            title: "Create a course",
            body: "A course is one subject. Papers filed under it build up into a single history — so every prediction gets smarter as you add more.",
            cta: "Create a course",
            href: "/courses",
            done: hasCourse,
        },
        {
            title: "Upload your papers",
            body: "One PDF with your syllabus and past question papers. Exyst reads every page and sorts out which is which itself.",
            cta: "Upload a PDF",
            href: "/upload",
            done: hasDocument,
        },
        {
            title: "Get your predicted paper",
            body: "Exyst finds the topics your examiners keep returning to, then writes a practice paper in your exam's exact format — with a confidence score on every question.",
            cta: "See your documents",
            href: "/documents",
            done: hasPrediction,
        },
    ];

    // The first unfinished step is the one we push; the rest stay quiet.
    const activeIndex = steps.findIndex((s) => !s.done);

    return (
        <div
            className="glass-card animate-fade-in"
            style={{ padding: 28, marginBottom: 32 }}
        >
            <h2
                style={{
                    margin: "0 0 6px",
                    fontSize: "1.15rem",
                    fontWeight: 800,
                    color: "var(--text-primary)",
                }}
            >
                Let&apos;s get your first prediction
            </h2>
            <p
                style={{
                    margin: "0 0 24px",
                    fontSize: "0.875rem",
                    color: "var(--text-secondary)",
                    lineHeight: 1.6,
                    maxWidth: 620,
                }}
            >
                Exyst studies your past exam papers to work out which topics keep
                coming up — then writes you a realistic practice paper in the same
                format as the real one. Three steps, about a minute.
            </p>

            <ol
                style={{
                    listStyle: "none",
                    margin: 0,
                    padding: 0,
                    display: "flex",
                    flexDirection: "column",
                    gap: 12,
                }}
            >
                {steps.map((step, i) => {
                    const isActive = i === activeIndex;
                    return (
                        <li
                            key={step.title}
                            style={{
                                display: "flex",
                                gap: 14,
                                alignItems: "flex-start",
                                padding: 16,
                                borderRadius: "var(--radius-md)",
                                border: `1px solid ${
                                    isActive
                                        ? "rgba(99, 102, 241, 0.35)"
                                        : "var(--border-subtle)"
                                }`,
                                background: isActive
                                    ? "rgba(99, 102, 241, 0.07)"
                                    : "transparent",
                                opacity: step.done ? 0.6 : 1,
                            }}
                        >
                            <span
                                aria-hidden="true"
                                style={{
                                    flexShrink: 0,
                                    width: 26,
                                    height: 26,
                                    borderRadius: "50%",
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                    fontSize: "0.75rem",
                                    fontWeight: 700,
                                    background: step.done
                                        ? "rgba(34, 197, 94, 0.15)"
                                        : isActive
                                          ? "var(--gradient-main)"
                                          : "rgba(255, 255, 255, 0.05)",
                                    color: step.done
                                        ? "#22c55e"
                                        : "var(--text-primary)",
                                }}
                            >
                                {step.done ? "✓" : i + 1}
                            </span>

                            <div style={{ flex: 1, minWidth: 0 }}>
                                <p
                                    style={{
                                        margin: 0,
                                        fontWeight: 700,
                                        fontSize: "0.9rem",
                                        color: "var(--text-primary)",
                                        textDecoration: step.done
                                            ? "line-through"
                                            : "none",
                                    }}
                                >
                                    {step.title}
                                </p>
                                <p
                                    style={{
                                        margin: "4px 0 0",
                                        fontSize: "0.8rem",
                                        color: "var(--text-muted)",
                                        lineHeight: 1.55,
                                    }}
                                >
                                    {step.body}
                                </p>
                            </div>

                            {isActive && (
                                <button
                                    className="btn-primary"
                                    onClick={() => router.push(step.href)}
                                    style={{
                                        flexShrink: 0,
                                        padding: "8px 16px",
                                        fontSize: "0.8rem",
                                        alignSelf: "center",
                                    }}
                                >
                                    {step.cta} →
                                </button>
                            )}
                        </li>
                    );
                })}
            </ol>
        </div>
    );
}
