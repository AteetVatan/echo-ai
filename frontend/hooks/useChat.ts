"use client";

import { useState, useCallback, useRef } from "react";
import { sendChatMessage } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";

function generateId() {
    return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function getSessionId(): string {
    const key = "echoai_session_id";
    let id = sessionStorage.getItem(key);
    if (!id) {
        id = crypto.randomUUID();
        sessionStorage.setItem(key, id);
    }
    return id;
}

const GREETING: ChatMessage = {
    id: "greeting",
    role: "assistant",
    content:
        "Hey there! I'm Ateet's AI clone : a digital twin powered by RAG and grounded in his real experience. Ask me anything about his work, projects, or skills.",
    timestamp: Date.now(),
};

export function useChat() {
    const [messages, setMessages] = useState<ChatMessage[]>([GREETING]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const sessionRef = useRef<string | null>(null);

    const send = useCallback(async (text: string) => {
        const trimmed = text.trim();
        if (!trimmed || isLoading) return;

        if (!sessionRef.current) {
            sessionRef.current = getSessionId();
        }

        const userMsg: ChatMessage = {
            id: generateId(),
            role: "user",
            content: trimmed,
            timestamp: Date.now(),
        };

        setMessages((prev) => [...prev, userMsg]);
        setIsLoading(true);
        setError(null);

        try {
            const data = await sendChatMessage(trimmed, sessionRef.current);
            sessionRef.current = data.session_id;

            const aiMsg: ChatMessage = {
                id: generateId(),
                role: "assistant",
                content: data.response,
                timestamp: Date.now(),
            };

            setMessages((prev) => [...prev, aiMsg]);
        } catch (err) {
            const msg = err instanceof Error ? err.message : "Something went wrong";
            setError(msg);
        } finally {
            setIsLoading(false);
        }
    }, [isLoading]);

    const clearChat = useCallback(() => {
        setMessages([GREETING]);
        setError(null);
        sessionRef.current = null;
        sessionStorage.removeItem("echoai_session_id");
    }, []);

    return { messages, isLoading, error, send, clearChat };
}
