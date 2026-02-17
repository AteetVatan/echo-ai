"use client";

import { useEffect, useRef } from "react";
import Image from "next/image";
import { useChat } from "@/hooks/useChat";
import { MessageBubble } from "./MessageBubble";
import { ChatInput } from "./ChatInput";
import { TypingIndicator } from "./TypingIndicator";

export function ChatContainer() {
    const { messages, isLoading, error, send, clearChat } = useChat();
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        scrollRef.current?.scrollTo({
            top: scrollRef.current.scrollHeight,
            behavior: "smooth",
        });
    }, [messages, isLoading]);

    return (
        <div className="flex h-[calc(100vh-4rem)] flex-col">
            {/* Top bar */}
            <div className="glass-panel flex items-center justify-between px-4 py-3 sm:px-6">
                <div className="flex items-center gap-3">
                    <div className="relative h-9 w-9 overflow-hidden rounded-xl"
                        style={{ boxShadow: "0 2px 12px var(--glow-pink)" }}>
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
                                <span className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-75"
                                    style={{ background: isLoading ? "var(--color-amber)" : "var(--color-green)" }} />
                                <span className="relative inline-flex h-1.5 w-1.5 rounded-full"
                                    style={{ background: isLoading ? "var(--color-amber)" : "var(--color-green)" }} />
                            </span>
                            <p className="text-xs text-[var(--color-text-muted)]">
                                {isLoading ? "Thinking..." : "Online"}
                            </p>
                        </div>
                    </div>
                </div>
                <button
                    onClick={clearChat}
                    className="rounded-lg border border-white/6 bg-white/3 px-3 py-1.5 text-xs text-[var(--color-text-muted)] transition-all hover:border-[var(--color-coral)]/30 hover:bg-[var(--color-coral)]/10 hover:text-[var(--color-coral)]"
                >
                    Clear
                </button>
            </div>

            {/* Messages */}
            <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto px-4 py-6 sm:px-6">
                {messages.map((msg) => (
                    <MessageBubble key={msg.id} message={msg} />
                ))}
                {isLoading && <TypingIndicator />}
                {error && (
                    <div className="mx-auto max-w-sm rounded-xl border border-[var(--color-coral)]/20 bg-[var(--color-coral)]/10 px-4 py-3 text-center text-sm"
                        style={{ color: "var(--color-coral)" }}>
                        {error}
                    </div>
                )}
            </div>

            {/* Input */}
            <ChatInput onSend={send} disabled={isLoading} />
        </div>
    );
}
