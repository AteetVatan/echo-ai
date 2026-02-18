"use client";

const features = [
    {
        icon: (
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z" />
            </svg>
        ),
        title: "RAG-Powered Memory",
        desc: "Dual-index vector search over career facts and project documentation. Every answer is grounded in real data.",
        color: "var(--color-coral)",
        gradient: "var(--gradient-coral)",
        glowColor: "var(--glow-coral)",
        metric: "94%",
        metricLabel: "Accuracy",
    },
    {
        icon: (
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" />
            </svg>
        ),
        title: "Real-Time Voice",
        desc: "WebSocket-streamed STT→LLM→TTS pipeline with Edge-TTS neural voices and sub-second latency.",
        color: "var(--color-teal)",
        gradient: "var(--gradient-teal)",
        glowColor: "var(--glow-teal)",
        metric: "<200ms",
        metricLabel: "Latency",
    },
    {
        icon: (
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.087.16 2.185.283 3.293.369V21l4.076-4.076a1.526 1.526 0 011.037-.443 48.282 48.282 0 005.68-.494c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
            </svg>
        ),
        title: "Intelligent Chat",
        desc: "Text-based conversations with semantic caching, multi-turn context, and persona-consistent responses.",
        color: "var(--color-pink)",
        gradient: "var(--gradient-pink)",
        glowColor: "var(--glow-pink)",
        metric: "∞",
        metricLabel: "Context",
    },
    {
        icon: (
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
            </svg>
        ),
        title: "Grounded Answers",
        desc: "Temperature locked to zero. Never invents facts — refuses gracefully when knowledge is insufficient.",
        color: "var(--color-green)",
        gradient: "var(--gradient-green)",
        glowColor: "var(--glow-green)",
        metric: "0°",
        metricLabel: "Temp",
    },
    {
        icon: (
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
            </svg>
        ),
        title: "Multi-Level Caching",
        desc: "In-memory LRU → SQLite hash match → ChromaDB semantic similarity. Sub-50ms for cached queries.",
        color: "var(--color-amber)",
        gradient: "var(--gradient-amber)",
        glowColor: "var(--glow-amber)",
        metric: "<50ms",
        metricLabel: "Speed",
    },
    {
        icon: (
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25z" />
            </svg>
        ),
        title: "Multi-LLM Fallback",
        desc: "DeepSeek primary, Mistral fallback. Automatic failover with LangChain RAG chain orchestration.",
        color: "var(--color-violet)",
        gradient: "var(--gradient-violet)",
        glowColor: "var(--glow-violet)",
        metric: "2+",
        metricLabel: "Models",
    },
];

export function FeaturesSection() {
    return (
        <section className="relative mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-24">
            {/* Ambient glow */}
            <div className="pointer-events-none absolute left-1/2 top-0 h-64 w-96 -translate-x-1/2 rounded-full opacity-10 blur-[120px]"
                style={{ background: "var(--color-violet)" }} />

            <div className="relative z-10">
                <div className="mb-14 text-center">
                    <h2 className="mb-3 text-2xl font-bold tracking-tight sm:text-3xl lg:text-4xl">
                        <span className="gradient-text-pink">How It Works</span>
                    </h2>
                    <p className="text-[var(--color-text-muted)]">
                        The engine behind the AI clone
                    </p>
                </div>

                <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
                    {features.map((f) => (
                        <div
                            key={f.title}
                            className="glass-card group relative overflow-hidden p-4 sm:p-6"
                        >
                            {/* Top row: icon + metric */}
                            <div className="mb-4 flex items-start justify-between">
                                <div
                                    className="flex h-12 w-12 items-center justify-center rounded-xl transition-all group-hover:scale-110"
                                    style={{
                                        background: f.gradient,
                                        boxShadow: `0 4px 20px ${f.glowColor}`,
                                        color: "white",
                                    }}
                                >
                                    {f.icon}
                                </div>
                                <div className="text-right">
                                    <div className="text-xl font-bold" style={{ color: f.color }}>{f.metric}</div>
                                    <div className="text-[10px] uppercase tracking-wider text-[var(--color-text-dim)]">{f.metricLabel}</div>
                                </div>
                            </div>

                            <h3 className="mb-2 text-lg font-semibold">{f.title}</h3>
                            <p className="text-sm leading-relaxed text-[var(--color-text-muted)]">{f.desc}</p>

                            {/* Bottom accent line */}
                            <div className="mt-5 h-0.5 w-full overflow-hidden rounded-full bg-white/5">
                                <div
                                    className="h-full w-0 rounded-full transition-all duration-500 group-hover:w-full"
                                    style={{ background: f.gradient }}
                                />
                            </div>

                            {/* Hover corner glow */}
                            <div
                                className="pointer-events-none absolute -right-6 -top-6 h-20 w-20 rounded-full opacity-0 transition-opacity duration-500 group-hover:opacity-100"
                                style={{ background: `radial-gradient(circle, ${f.glowColor}, transparent 70%)` }}
                            />
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
}
