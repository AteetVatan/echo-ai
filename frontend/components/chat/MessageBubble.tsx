import type { ChatMessage } from "@/lib/types";

interface MessageBubbleProps {
    message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
    const isUser = message.role === "user";

    return (
        <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
            <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed sm:max-w-[70%] ${isUser
                        ? "rounded-br-md text-white"
                        : "rounded-bl-md border border-white/6 bg-white/4 text-[var(--color-text)]"
                    }`}
                style={
                    isUser
                        ? {
                            background: "var(--gradient-pink)",
                            boxShadow: "0 4px 16px var(--glow-pink)",
                        }
                        : { backdropFilter: "blur(8px)" }
                }
            >
                {message.content}
            </div>
        </div>
    );
}
