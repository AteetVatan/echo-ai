import type { ChatMessage } from "@/lib/types";

interface MessageBubbleProps {
    message: ChatMessage;
    onPlayAudio?: (audioUrl: string) => void;
}

export function MessageBubble({ message, onPlayAudio }: MessageBubbleProps) {
    const isUser = message.role === "user";

    return (
        <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
            <div
                className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed sm:max-w-[70%] ${isUser
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
                <span style={{ whiteSpace: "pre-wrap" }}>{message.content}</span>

                {/* Audio replay button for assistant messages */}
                {!isUser && message.audioUrl && onPlayAudio && (
                    <button
                        onClick={() => onPlayAudio(message.audioUrl!)}
                        className="mt-2 flex items-center gap-1.5 rounded-lg border border-white/8 bg-white/4 px-2.5 py-1 text-xs text-[var(--color-text-muted)] transition-all hover:border-[var(--color-teal)]/30 hover:text-[var(--color-teal)]"
                    >
                        <svg
                            className="h-3.5 w-3.5"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            strokeWidth={2}
                        >
                            <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                d="M15.536 8.464a5 5 0 010 7.072M18.364 5.636a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z"
                            />
                        </svg>
                        Replay
                    </button>
                )}
            </div>
        </div>
    );
}
