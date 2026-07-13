/**
 * Top-of-page progress bar shown during client-side navigation.
 *
 * Without this, clicking a nav link does nothing visible until the next page's
 * data arrives — which reads as "the click didn't register". The bar appears
 * immediately, so the app always acknowledges the input.
 *
 * It's deliberately *indeterminate*: we can't know how long a route will take,
 * so it eases toward 90% and only completes when the route actually does.
 * Faking a percentage would be lying to the user.
 */

import React, { useEffect, useRef, useState } from "react";
import { useRouter } from "next/router";

// Navigations faster than this never show a bar — a flash of loading UI on an
// instant transition looks like a glitch, not like feedback.
const SHOW_AFTER_MS = 150;

export default function RouteProgress() {
    const router = useRouter();
    const [visible, setVisible] = useState(false);
    const [progress, setProgress] = useState(0);

    const showTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
    const tickTimer = useRef<ReturnType<typeof setInterval> | null>(null);
    const hideTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

    useEffect(() => {
        const clearTimers = () => {
            if (showTimer.current) clearTimeout(showTimer.current);
            if (tickTimer.current) clearInterval(tickTimer.current);
            if (hideTimer.current) clearTimeout(hideTimer.current);
        };

        const start = () => {
            clearTimers();
            showTimer.current = setTimeout(() => {
                setVisible(true);
                setProgress(8);

                // Ease toward 90% — decelerating, so it never stalls at a
                // number and never claims to be finished before it is.
                tickTimer.current = setInterval(() => {
                    setProgress((p) => (p >= 90 ? p : p + (90 - p) * 0.12));
                }, 200);
            }, SHOW_AFTER_MS);
        };

        const done = () => {
            clearTimers();
            setProgress(100);
            // Let the fill animate to 100% before fading out.
            hideTimer.current = setTimeout(() => {
                setVisible(false);
                setProgress(0);
            }, 250);
        };

        router.events.on("routeChangeStart", start);
        router.events.on("routeChangeComplete", done);
        router.events.on("routeChangeError", done);

        return () => {
            router.events.off("routeChangeStart", start);
            router.events.off("routeChangeComplete", done);
            router.events.off("routeChangeError", done);
            clearTimers();
        };
    }, [router]);

    if (!visible) return null;

    return (
        <div
            className="route-progress"
            role="progressbar"
            aria-busy="true"
            aria-label="Loading page"
        >
            <div
                className="route-progress-bar"
                style={{
                    width: `${progress}%`,
                    opacity: progress === 100 ? 0 : 1,
                }}
            />
        </div>
    );
}
