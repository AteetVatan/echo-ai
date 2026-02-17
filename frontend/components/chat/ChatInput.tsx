"use client";

import { useState, type FormEvent, type KeyboardEvent } from "react";

interface ChatInputProps {
    onSend: (message: string) => void;
    disabled: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
    const [value, setValue] = useState("");

    function handleSubmit(e: FormEvent) {
        e.preventDefault();
        if (!value.trim() || disabled) return;
        onSend(value);
        setValue("");
    }

    function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSubmit(e);
        }
    }

    return (
        <form
            onSubmit={handleSubmit}
            className="flex items-end gap-3 border-t border-white/5 bg-[var(--color-bg)] px-4 py-4 sm:px-6"
        >
            <textarea
                value={value}
                onChange={(e) => setValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask me anything about Ateet..."
                disabled={disabled}
                rows={1}
                className="flex-1 resize-none rounded-xl border border-white/8 bg-white/4 px-4 py-3 text-sm text-[var(--color-text)] placeholder:text-[var(--color-text-dim)] transition-all focus:border-[var(--color-pink)]/50 focus:outline-none focus:ring-1 focus:ring-[var(--color-pink)]/30 focus:bg-white/6 disabled:opacity-50"
                style={{ backdropFilter: "blur(8px)" }}
            />
            <button
                type="submit"
                disabled={disabled || !value.trim()}
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-white transition-all hover:scale-105 disabled:opacity-40 disabled:hover:scale-100"
                style={{
                    background: "var(--gradient-pink)",
                    boxShadow: disabled || !value.trim() ? "none" : "0 4px 16px var(--glow-pink)",
                }}
            >
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
                </svg>
            </button>
        </form>
    );
}
