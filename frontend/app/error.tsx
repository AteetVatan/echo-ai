"use client";

export default function ErrorPage({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    return (
        <div className="flex min-h-screen flex-col items-center justify-center gap-6 px-6 text-center">
            <div className="glass-card flex flex-col items-center gap-5 px-10 py-10">
                <div className="flex h-16 w-16 items-center justify-center rounded-2xl"
                    style={{
                        background: "var(--gradient-coral)",
                        boxShadow: "0 8px 32px var(--glow-coral)",
                    }}>
                    <svg className="h-8 w-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                    </svg>
                </div>
                <h2 className="text-xl font-semibold">Something went wrong</h2>
                <p className="max-w-md text-sm text-[var(--color-text-muted)]">
                    {error.message || "An unexpected error occurred."}
                </p>
                <button
                    onClick={reset}
                    className="rounded-full px-6 py-2.5 text-sm font-medium text-white transition-all hover:scale-105"
                    style={{
                        background: "var(--gradient-pink)",
                        boxShadow: "0 4px 16px var(--glow-pink)",
                    }}
                >
                    Try Again
                </button>
            </div>
        </div>
    );
}
