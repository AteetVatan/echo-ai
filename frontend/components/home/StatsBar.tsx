"use client";

const stats = [
    {
        label: "RAG Accuracy",
        value: "94%",
        sublabel: "Grounded in real data",
        color: "var(--color-coral)",
        glowColor: "var(--glow-coral)",
        gradient: "var(--gradient-coral)",
        progress: 94,
        icon: (
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
            </svg>
        ),
    },
    {
        label: "Voice Latency",
        value: "<200ms",
        sublabel: "Edge-TTS neural synthesis",
        color: "var(--color-teal)",
        glowColor: "var(--glow-teal)",
        gradient: "var(--gradient-teal)",
        progress: 85,
        icon: (
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" />
            </svg>
        ),
    },
    {
        label: "Cache Speed",
        value: "<50ms",
        sublabel: "Multi-level LRU + semantic",
        color: "var(--color-amber)",
        glowColor: "var(--glow-amber)",
        gradient: "var(--gradient-amber)",
        progress: 96,
        icon: (
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
            </svg>
        ),
    },
    {
        label: "Knowledge Base",
        value: "2,005",
        sublabel: "Career facts indexed",
        color: "var(--color-violet)",
        glowColor: "var(--glow-violet)",
        gradient: "var(--gradient-violet)",
        progress: 78,
        icon: (
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125" />
            </svg>
        ),
    },
    {
        label: "LLM Uptime",
        value: "99.8%",
        sublabel: "DeepSeek + Mistral fallback",
        color: "var(--color-green)",
        glowColor: "var(--glow-green)",
        gradient: "var(--gradient-green)",
        progress: 99,
        icon: (
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.348 14.651a3.75 3.75 0 010-5.303m5.304 0a3.75 3.75 0 010 5.303m-7.425 2.122a6.75 6.75 0 010-9.546m9.546 0a6.75 6.75 0 010 9.546M5.106 18.894c-3.808-3.808-3.808-9.98 0-13.789m13.788 0c3.808 3.808 3.808 9.981 0 13.79M12 12h.008v.007H12V12zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
            </svg>
        ),
    },
    {
        label: "Persona Match",
        value: "97%",
        sublabel: "Tone & factual consistency",
        color: "var(--color-pink)",
        glowColor: "var(--glow-pink)",
        gradient: "var(--gradient-pink)",
        progress: 97,
        icon: (
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
            </svg>
        ),
    },
];

export function StatsBar() {
    return (
        <section className="mx-auto max-w-7xl px-6 py-16">
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
                {stats.map((s) => (
                    <div
                        key={s.label}
                        className="glass-card group relative overflow-hidden px-5 py-5"
                    >
                        {/* Icon */}
                        <div
                            className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl transition-transform group-hover:scale-110"
                            style={{
                                background: s.gradient,
                                boxShadow: `0 4px 15px ${s.glowColor}`,
                                color: "white",
                            }}
                        >
                            {s.icon}
                        </div>

                        {/* Metric */}
                        <div className="mb-1 text-2xl font-bold tracking-tight" style={{ color: s.color }}>
                            {s.value}
                        </div>
                        <div className="mb-1 text-sm font-medium text-[var(--color-text)]">
                            {s.label}
                        </div>
                        <div className="mb-4 text-xs text-[var(--color-text-muted)]">
                            {s.sublabel}
                        </div>

                        {/* Progress bar */}
                        <div className="h-1 w-full overflow-hidden rounded-full bg-white/5">
                            <div
                                className="h-full rounded-full transition-all duration-1000"
                                style={{
                                    width: `${s.progress}%`,
                                    background: s.gradient,
                                }}
                            />
                        </div>

                        {/* Hover glow */}
                        <div
                            className="pointer-events-none absolute -bottom-8 -right-8 h-24 w-24 rounded-full opacity-0 transition-opacity group-hover:opacity-100"
                            style={{ background: `radial-gradient(circle, ${s.glowColor}, transparent 70%)` }}
                        />
                    </div>
                ))}
            </div>
        </section>
    );
}
