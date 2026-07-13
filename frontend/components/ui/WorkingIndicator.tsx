/**
 * Feedback for genuinely slow work (an LLM call: 20–90 seconds).
 *
 * A bare spinner is not enough here. Past roughly ten seconds a user starts to
 * wonder whether the thing is broken, and there is nothing on screen to tell
 * them otherwise. So this shows three things a spinner can't:
 *
 *   1. **An elapsed counter** — proof that time is passing and the app knows it.
 *   2. **What it's doing right now** — the steps advance on a timeline calibrated
 *      to a real run, so the message keeps changing even though the server can't
 *      report progress on a single blocking request.
 *   3. **An honest expectation** — "usually 30–60 seconds", set before they start
 *      wondering.
 *
 * The steps are time-driven, not server-driven, and that's a deliberate
 * trade-off: this component is used where the backend gives us one blocking
 * POST and no progress events. It never claims a step is *finished* — only that
 * it's underway — so it can't tell the user something false. (The upload page,
 * which does have a real SSE progress stream, uses that instead.)
 */

import React, { useEffect, useState } from "react";

export interface WorkStep {
    /** Seconds into the run at which this message takes over. */
    at: number;
    label: string;
}

interface WorkingIndicatorProps {
    steps: WorkStep[];
    /** e.g. "usually 30–60 seconds" */
    expectation?: string;
    /** Past this many seconds, reassure the user it's still alive rather than stuck. */
    slowAfter?: number;
}

export default function WorkingIndicator({
    steps,
    expectation,
    slowAfter = 90,
}: WorkingIndicatorProps) {
    const [elapsed, setElapsed] = useState(0);

    useEffect(() => {
        const started = Date.now();
        const id = setInterval(() => {
            setElapsed(Math.floor((Date.now() - started) / 1000));
        }, 1000);
        return () => clearInterval(id);
    }, []);

    const active = [...steps].reverse().find((s) => elapsed >= s.at) ?? steps[0];
    const isSlow = elapsed >= slowAfter;

    return (
        <div
            className="glass-card animate-fade-in"
            style={{ padding: 20 }}
            role="status"
            aria-live="polite"
        >
            <div
                style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                    marginBottom: 14,
                }}
            >
                <span className="spinner" style={{ width: 18, height: 18 }} />
                <span
                    style={{
                        fontWeight: 600,
                        fontSize: "0.9rem",
                        color: "var(--text-primary)",
                    }}
                >
                    {active?.label}
                </span>
                <span
                    style={{
                        marginLeft: "auto",
                        fontVariantNumeric: "tabular-nums",
                        fontSize: "0.8rem",
                        color: "var(--text-muted)",
                    }}
                >
                    {elapsed}s
                </span>
            </div>

            {/* Indeterminate track: the work is real but unmeasurable, so the
                bar communicates "in motion" rather than a fake percentage. */}
            <div className="indeterminate-track" aria-hidden="true">
                <div className="indeterminate-fill" />
            </div>

            <p
                style={{
                    margin: "12px 0 0",
                    fontSize: "0.75rem",
                    color: isSlow ? "var(--accent-violet)" : "var(--text-muted)",
                    lineHeight: 1.5,
                }}
            >
                {isSlow
                    ? "Still working — a long or complex paper can take a while. Don't close this tab."
                    : expectation}
            </p>

            {/* The step list doubles as an explanation of what the system does. */}
            <ol
                style={{
                    listStyle: "none",
                    padding: 0,
                    margin: "14px 0 0",
                    display: "flex",
                    flexDirection: "column",
                    gap: 6,
                }}
            >
                {steps.map((s) => {
                    const done = elapsed > s.at && s !== active;
                    const current = s === active;
                    return (
                        <li
                            key={s.label}
                            style={{
                                display: "flex",
                                alignItems: "center",
                                gap: 8,
                                fontSize: "0.75rem",
                                color: current
                                    ? "var(--text-secondary)"
                                    : "var(--text-muted)",
                                opacity: done ? 0.55 : 1,
                            }}
                        >
                            <span aria-hidden="true">
                                {done ? "✓" : current ? "▸" : "·"}
                            </span>
                            {s.label}
                        </li>
                    );
                })}
            </ol>
        </div>
    );
}

/** The stages of a prediction run, timed against a typical Gemini call. */
export const PREDICTION_STEPS: WorkStep[] = [
    { at: 0, label: "Reading the analysed paper structure" },
    { at: 4, label: "Retrieving similar questions from your course history" },
    { at: 10, label: "Generating the predicted paper (Gemini)" },
    { at: 45, label: "Checking marks totals and section structure" },
    { at: 60, label: "Scoring confidence against historical patterns" },
];
