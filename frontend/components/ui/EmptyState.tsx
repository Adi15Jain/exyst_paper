/**
 * "Nothing here yet" card with an optional call to action.
 */

import React from "react";

interface EmptyStateProps {
    icon: string;
    title: string;
    hint?: string;
    actionLabel?: string;
    onAction?: () => void;
}

export default function EmptyState({
    icon,
    title,
    hint,
    actionLabel,
    onAction,
}: EmptyStateProps) {
    return (
        <div
            className="glass-card"
            style={{ textAlign: "center", padding: "60px 24px" }}
        >
            <p style={{ fontSize: "3rem", marginBottom: 12 }} aria-hidden="true">
                {icon}
            </p>
            <p
                style={{
                    fontSize: "1.1rem",
                    fontWeight: 600,
                    color: "var(--text-primary)",
                }}
            >
                {title}
            </p>
            {hint && (
                <p
                    style={{
                        color: "var(--text-muted)",
                        marginBottom: 20,
                        fontSize: "0.9rem",
                    }}
                >
                    {hint}
                </p>
            )}
            {actionLabel && onAction && (
                <button className="btn-primary" onClick={onAction}>
                    {actionLabel}
                </button>
            )}
        </div>
    );
}
