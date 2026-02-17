"use client";

import Link from "next/link";
import { NeuralBackground } from "./NeuralBackground";

export function HeroSection() {
    return (
        <section className="relative min-h-[92vh] overflow-hidden">
            {/* Neural background */}
            <div className="absolute inset-0">
                <NeuralBackground />
            </div>

            {/* Ambient glow orbs */}
            <div className="pointer-events-none absolute -top-32 left-1/6 h-80 w-80 rounded-full opacity-20 blur-[120px]"
                style={{ background: "var(--color-pink)" }} />
            <div className="pointer-events-none absolute -bottom-20 right-1/4 h-64 w-64 rounded-full opacity-15 blur-[100px]"
                style={{ background: "var(--color-teal)" }} />
            <div className="pointer-events-none absolute top-1/3 right-1/6 h-72 w-72 rounded-full opacity-10 blur-[100px]"
                style={{ background: "var(--color-coral)" }} />

            {/* Content */}
            <div className="relative z-10 mx-auto flex max-w-4xl flex-col items-center gap-8 px-6 pt-28 lg:pt-32">
                {/* Left side: text content */}
                <div className="text-center">
                    {/* Status badge */}
                    <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-xs backdrop-blur-sm">
                        <span className="relative flex h-2 w-2">
                            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[var(--color-green)] opacity-75" />
                            <span className="relative inline-flex h-2 w-2 rounded-full bg-[var(--color-green)]" />
                        </span>
                        <span className="text-[var(--color-text-muted)]">RAG-Powered AI Clone — Online</span>
                    </div>

                    <h1 className="mb-6 text-5xl font-bold leading-[1.1] tracking-tight sm:text-6xl lg:text-7xl">
                        <span className="block text-[var(--color-text)]">Talk to</span>
                        <span className="gradient-text-pink">
                            Ateet&apos;s AI Clone
                        </span>
                    </h1>

                    <p className="mx-auto mb-8 max-w-lg text-lg leading-relaxed text-[var(--color-text-muted)]">
                        A digital twin grounded in real career experience, projects, and expertise.
                        Powered by RAG retrieval, semantic search, and multi-LLM orchestration.
                    </p>

                    {/* CTA buttons */}
                    <div className="flex flex-col items-center justify-center gap-4 sm:flex-row">
                        <Link
                            href="/chat"
                            className="group relative inline-flex items-center gap-2 rounded-full px-8 py-3.5 text-base font-semibold text-white transition-all hover:scale-[1.03] hover:brightness-110"
                            style={{
                                background: "linear-gradient(135deg, #00cec9, #0984e3)",
                                boxShadow: "0 0 20px rgba(0, 206, 201, 0.3), 0 8px 32px rgba(0, 206, 201, 0.15), inset 0 1px 0 rgba(255,255,255,0.15)",
                            }}
                        >
                            Start a Conversation
                            <svg
                                className="h-4 w-4 transition-transform group-hover:translate-x-1"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                                strokeWidth={2}
                            >
                                <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                            </svg>
                        </Link>

                        <a
                            href="https://github.com/AteetVatan/echo-ai"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="glow-ring inline-flex items-center gap-2 rounded-full border border-white/10 px-6 py-3 text-sm text-[var(--color-text-muted)] backdrop-blur-sm transition-all hover:text-[var(--color-text)]"
                        >
                            <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
                                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
                            </svg>
                            View Source
                        </a>
                    </div>

                    {/* Social links */}
                    <div className="mt-6 flex items-center justify-center gap-5">
                        <a
                            href="https://ateetai.vercel.app/"
                            target="_blank"
                            rel="noopener noreferrer"
                            title="Portfolio"
                            className="glow-ring group flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-white/5 text-[var(--color-text-muted)] backdrop-blur-sm transition-all hover:border-white/20 hover:bg-white/10 hover:text-[var(--color-teal)]"
                        >
                            <svg className="h-[18px] w-[18px] transition-transform group-hover:scale-110" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5a17.92 17.92 0 01-8.716-2.247m0 0A8.966 8.966 0 013 12c0-1.04.176-2.04.5-2.97" />
                            </svg>
                        </a>
                        <a
                            href="https://github.com/AteetVatan"
                            target="_blank"
                            rel="noopener noreferrer"
                            title="GitHub"
                            className="glow-ring group flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-white/5 text-[var(--color-text-muted)] backdrop-blur-sm transition-all hover:border-white/20 hover:bg-white/10 hover:text-white"
                        >
                            <svg className="h-[18px] w-[18px] transition-transform group-hover:scale-110" fill="currentColor" viewBox="0 0 24 24">
                                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
                            </svg>
                        </a>
                        <a
                            href="https://www.linkedin.com/in/ateet-vatan-bahmani/"
                            target="_blank"
                            rel="noopener noreferrer"
                            title="LinkedIn"
                            className="glow-ring group flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-white/5 text-[var(--color-text-muted)] backdrop-blur-sm transition-all hover:border-white/20 hover:bg-white/10 hover:text-[#0a66c2]"
                        >
                            <svg className="h-[18px] w-[18px] transition-transform group-hover:scale-110" fill="currentColor" viewBox="0 0 24 24">
                                <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
                            </svg>
                        </a>
                    </div>

                    {/* Mini search indicator */}
                    <div className="mt-10 flex items-center justify-center gap-3">
                        <div className="h-1 flex-1 max-w-[200px] overflow-hidden rounded-full bg-white/5">
                            <div className="h-full w-2/3 rounded-full animate-shimmer"
                                style={{ background: "var(--gradient-green)" }} />
                        </div>
                        <span className="text-xs text-[var(--color-text-dim)]">Knowledge retrieval active</span>
                    </div>
                </div>

            </div>
        </section>
    );
}
