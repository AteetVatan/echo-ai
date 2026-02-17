export function TypingIndicator() {
    return (
        <div className="flex justify-start">
            <div className="flex items-center gap-1.5 rounded-2xl rounded-bl-md border border-white/6 bg-white/4 px-4 py-3"
                style={{ backdropFilter: "blur(8px)" }}>
                <span className="h-2 w-2 animate-bounce rounded-full [animation-delay:0ms]"
                    style={{ background: "var(--color-coral)" }} />
                <span className="h-2 w-2 animate-bounce rounded-full [animation-delay:150ms]"
                    style={{ background: "var(--color-teal)" }} />
                <span className="h-2 w-2 animate-bounce rounded-full [animation-delay:300ms]"
                    style={{ background: "var(--color-amber)" }} />
            </div>
        </div>
    );
}
