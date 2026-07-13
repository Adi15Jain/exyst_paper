/**
 * Centered loading spinner with an optional caption.
 */

import React from "react";

interface SpinnerProps {
    size?: number;
    caption?: string;
    padding?: number | string;
}

export default function Spinner({
    size = 32,
    caption,
    padding = "60px 0",
}: SpinnerProps) {
    return (
        <div style={{ textAlign: "center", padding }} role="status" aria-live="polite">
            <span
                className="spinner"
                style={{
                    width: size,
                    height: size,
                    margin: "0 auto",
                    display: "block",
                }}
            />
            {caption && (
                <p
                    style={{
                        color: "var(--text-muted)",
                        marginTop: 12,
                        fontSize: "0.85rem",
                    }}
                >
                    {caption}
                </p>
            )}
        </div>
    );
}
