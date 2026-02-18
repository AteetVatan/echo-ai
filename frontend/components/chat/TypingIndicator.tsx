"use client";

import { useState, useEffect } from "react";
import type { VoiceState } from "@/lib/types";

interface TypingIndicatorProps {
    voiceState: VoiceState;
}

const PHASE_LABELS = [
    "Processing...",
    "Analyzing context...",
    "Thinking deeply...",
    "Almost there...",
];

export function TypingIndicator({ voiceState }: TypingIndicatorProps) {
    const [phase, setPhase] = useState(0);

    // Progressive phase for processing state
    useEffect(() => {
        if (voiceState !== "processing") {
            setPhase(0);
            return;
        }
        const t1 = setTimeout(() => setPhase(1), 500);
        const t2 = setTimeout(() => setPhase(2), 3000);
        const t3 = setTimeout(() => setPhase(3), 6000);
        return () => {
            clearTimeout(t1);
            clearTimeout(t2);
            clearTimeout(t3);
        };
    }, [voiceState]);

    return (
        <div className="flex justify-start">
            <div
                className="flex flex-col items-center gap-2 rounded-2xl rounded-bl-md border border-white/6 bg-white/4 px-5 py-3"
                style={{ backdropFilter: "blur(8px)" }}
            >
                {/* ── Listening: waveform bars ─────────────────── */}
                {voiceState === "listening" && (
                    <div className="flex items-end gap-1 h-6">
                        {[0, 1, 2, 3, 4].map((i) => (
                            <span
                                key={i}
                                className="w-1 rounded-full animate-wave-bar"
                                style={{
                                    background: "var(--color-coral)",
                                    animationDelay: `${i * 120}ms`,
                                }}
                            />
                        ))}
                    </div>
                )}

                {/* ── Processing: progressive animation ───────── */}
                {voiceState === "processing" && (
                    <>
                        {phase < 2 ? (
                            /* Phase 0-1: bouncing dots */
                            <div className="flex items-center gap-1.5">
                                <span
                                    className="h-2 w-2 animate-bounce rounded-full"
                                    style={{
                                        background: "var(--color-coral)",
                                        animationDelay: "0ms",
                                    }}
                                />
                                <span
                                    className="h-2 w-2 animate-bounce rounded-full"
                                    style={{
                                        background: "var(--color-teal)",
                                        animationDelay: "150ms",
                                    }}
                                />
                                <span
                                    className="h-2 w-2 animate-bounce rounded-full"
                                    style={{
                                        background: "var(--color-amber)",
                                        animationDelay: "300ms",
                                    }}
                                />
                            </div>
                        ) : (
                            /* Phase 2-3: pulsing ring with shimmer */
                            <div className="relative flex items-center justify-center h-6 w-6">
                                <span
                                    className="absolute h-6 w-6 rounded-full animate-think-progress"
                                    style={{
                                        border: "2px solid",
                                        borderColor:
                                            phase >= 3
                                                ? "var(--color-amber)"
                                                : "var(--color-violet)",
                                        boxShadow: `0 0 12px ${phase >= 3
                                            ? "var(--glow-amber)"
                                            : "var(--glow-violet)"
                                            }`,
                                    }}
                                />
                                <span
                                    className="h-2 w-2 rounded-full"
                                    style={{
                                        background:
                                            phase >= 3
                                                ? "var(--color-amber)"
                                                : "var(--color-violet)",
                                    }}
                                />
                            </div>
                        )}
                        <span className="text-[10px] text-[var(--color-text-muted)]">
                            {PHASE_LABELS[phase]}
                        </span>
                    </>
                )}

                {/* ── Speaking: equalizer bars ─────────────────── */}
                {voiceState === "speaking" && (
                    <div className="flex items-end gap-1 h-6">
                        {[0, 1, 2].map((i) => (
                            <span
                                key={i}
                                className="w-1.5 rounded-full animate-speak-bar"
                                style={{
                                    background: "var(--color-green)",
                                    animationDelay: `${i * 200}ms`,
                                }}
                            />
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
