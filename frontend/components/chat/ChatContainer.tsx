"use client";

import { useEffect, useRef } from "react";
import Image from "next/image";
import { useChat } from "@/hooks/useChat";
import { MessageBubble } from "./MessageBubble";
import { ChatInput } from "./ChatInput";
import { TypingIndicator } from "./TypingIndicator";
import type { VoiceState } from "@/lib/types";

/* ── top-bar config per voice state ────────────────────────────────── */

const STATE_CONFIG: Record<
    VoiceState | "disconnected",
    { label: string; color: string; ping: boolean }
> = {
    chatMode: { label: "Online", color: "var(--color-green)", ping: true },
    idle: { label: "Listening...", color: "var(--color-teal)", ping: true },
    listening: { label: "Hearing you...", color: "var(--color-coral)", ping: true },
    processing: { label: "Thinking...", color: "var(--color-amber)", ping: true },
    speaking: { label: "Speaking...", color: "var(--color-green)", ping: false },
    interrupted: { label: "Interrupted", color: "var(--color-coral)", ping: false },
    disconnected: { label: "Reconnecting...", color: "var(--color-coral)", ping: false },
};

/* ── format timer ─────────────────────────────────────────────────── */

function formatTime(ms: number): string {
    const totalSec = Math.ceil(ms / 1000);
    const min = Math.floor(totalSec / 60);
    const sec = totalSec % 60;
    return `${min}:${sec.toString().padStart(2, "0")}`;
}

export function ChatContainer() {
    const {
        messages,
        voiceState,
        isConnected,
        isTalkMode,
        talkTimeRemaining,
        error,
        send,
        clearChat,
        startTalkMode,
        stopTalkMode,
        toggleVoiceMode,
        playAudio,
    } = useChat();

    const scrollRef = useRef<HTMLDivElement>(null);

    // Derive which visual config to show
    const stateKey = !isConnected && isTalkMode ? "disconnected" : voiceState;
    const cfg = STATE_CONFIG[stateKey];

    // Show indicator for processing, listening, speaking
    const showIndicator =
        voiceState === "processing" ||
        voiceState === "listening" ||
        voiceState === "speaking";

    useEffect(() => {
        scrollRef.current?.scrollTo({
            top: scrollRef.current.scrollHeight,
            behavior: "smooth",
        });
    }, [messages, showIndicator]);

    return (
        <div className="flex h-[calc(100vh-3.5rem)] flex-col sm:h-[calc(100vh-4rem)]">
            {/* Top bar */}
            <div className="glass-panel flex items-center justify-between px-3 py-2.5 sm:px-6 sm:py-3">
                <div className="flex items-center gap-3">
                    <div
                        className="relative h-8 w-8 overflow-hidden rounded-xl sm:h-9 sm:w-9"
                        style={{ boxShadow: `0 2px 12px ${cfg.color}40` }}
                    >
                        <Image
                            src="/profile.jpg"
                            alt="Ateet's AI Clone"
                            fill
                            className="object-cover"
                        />
                    </div>
                    <div>
                        <p className="text-sm font-semibold">Ateet&apos;s AI Clone</p>
                        <div className="flex items-center gap-1.5">
                            <span className="relative flex h-1.5 w-1.5">
                                {cfg.ping && (
                                    <span
                                        className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-75"
                                        style={{ background: cfg.color }}
                                    />
                                )}
                                <span
                                    className="relative inline-flex h-1.5 w-1.5 rounded-full"
                                    style={{ background: cfg.color }}
                                />
                            </span>
                            <p className="text-xs text-[var(--color-text-muted)]">
                                {cfg.label}
                                {isTalkMode && (
                                    <span className="ml-2 font-mono text-[var(--color-text-dim)]">
                                        {formatTime(talkTimeRemaining)}
                                    </span>
                                )}
                            </p>
                        </div>
                    </div>
                </div>
                <div className="flex items-center gap-1.5 sm:gap-2">
                    <button
                        onClick={toggleVoiceMode}
                        className={`flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs font-medium transition-all hover:scale-[1.03] sm:px-3 ${isTalkMode
                            ? "border border-[var(--color-coral)]/30 bg-[var(--color-coral)]/10 text-[var(--color-coral)] hover:bg-[var(--color-coral)]/20"
                            : "border border-[var(--color-teal)]/30 bg-[var(--color-teal)]/10 text-[var(--color-teal)] hover:bg-[var(--color-teal)]/20"
                            }`}
                    >
                        {isTalkMode ? (
                            <>
                                <svg className="h-3.5 w-3.5" fill="currentColor" viewBox="0 0 24 24">
                                    <rect x="6" y="6" width="12" height="12" rx="2" />
                                </svg>
                                <span className="hidden sm:inline">End Talk</span>
                            </>
                        ) : (
                            <>
                                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z" />
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 10v2a7 7 0 01-14 0v-2" />
                                    <line x1="12" y1="19" x2="12" y2="23" strokeLinecap="round" />
                                </svg>
                                <span className="hidden sm:inline">Talk to Me</span>
                            </>
                        )}
                    </button>
                    <button
                        onClick={clearChat}
                        className="rounded-lg border border-white/6 bg-white/3 px-3 py-1.5 text-xs text-[var(--color-text-muted)] transition-all hover:border-[var(--color-coral)]/30 hover:bg-[var(--color-coral)]/10 hover:text-[var(--color-coral)]"
                    >
                        Clear
                    </button>
                </div>
            </div>

            {/* Messages */}
            <div
                ref={scrollRef}
                className="flex-1 space-y-4 overflow-y-auto px-3 py-4 sm:px-6 sm:py-6"
            >
                {messages.map((msg) => (
                    <MessageBubble key={msg.id} message={msg} onPlayAudio={playAudio} />
                ))}
                {showIndicator && <TypingIndicator voiceState={voiceState} />}
                {error && (
                    <div
                        className="mx-auto max-w-sm rounded-xl border border-[var(--color-coral)]/20 bg-[var(--color-coral)]/10 px-4 py-3 text-center text-sm"
                        style={{ color: "var(--color-coral)" }}
                    >
                        {error}
                    </div>
                )}
            </div>

            {/* Input */}
            <ChatInput
                onSend={send}
                disabled={voiceState === "processing"}
                isTalkMode={isTalkMode}
                voiceState={voiceState}
            />
        </div>
    );
}
