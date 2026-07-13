/**
 * Inline status banner (error / success), with an optional action button.
 *
 * Replaces ten hand-rolled copies of the same red box that were scattered
 * across the pages.
 */

import React from "react";

type BannerKind = "error" | "success";

interface BannerProps {
    kind?: BannerKind;
    children: React.ReactNode;
    /** Optional action, e.g. a Retry button. */
    actionLabel?: string;
    onAction?: () => void;
    /** Optional dismiss (✕) affordance. */
    onDismiss?: () => void;
    style?: React.CSSProperties;
}

const PALETTE: Record<BannerKind, { fg: string; bg: string; border: string }> = {
    error: {
        fg: "#ef4444",
        bg: "rgba(239, 68, 68, 0.1)",
        border: "rgba(239, 68, 68, 0.2)",
    },
    success: {
        fg: "#22c55e",
        bg: "rgba(34, 197, 94, 0.1)",
        border: "rgba(34, 197, 94, 0.2)",
    },
};

export default function Banner({
    kind = "error",
    children,
    actionLabel,
    onAction,
    onDismiss,
    style,
}: BannerProps) {
    const c = PALETTE[kind];

    return (
        <div
            role={kind === "error" ? "alert" : "status"}
            style={{
                padding: "12px 16px",
                borderRadius: "var(--radius-sm)",
                background: c.bg,
                border: `1px solid ${c.border}`,
                color: c.fg,
                fontSize: "0.85rem",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: 12,
                ...style,
            }}
        >
            <span>{children}</span>

            {(actionLabel || onDismiss) && (
                <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    {actionLabel && onAction && (
                        <button
                            onClick={onAction}
                            style={{
                                background: c.bg,
                                border: `1px solid ${c.border}`,
                                color: c.fg,
                                cursor: "pointer",
                                fontSize: "0.8rem",
                                padding: "4px 12px",
                                borderRadius: "var(--radius-sm)",
                                whiteSpace: "nowrap",
                            }}
                        >
                            {actionLabel}
                        </button>
                    )}
                    {onDismiss && (
                        <button
                            onClick={onDismiss}
                            aria-label="Dismiss"
                            style={{
                                background: "transparent",
                                border: "none",
                                color: c.fg,
                                cursor: "pointer",
                                fontSize: "1rem",
                                lineHeight: 1,
                                padding: 0,
                            }}
                        >
                            ✕
                        </button>
                    )}
                </span>
            )}
        </div>
    );
}
