import Link from "next/link";
import Image from "next/image";

export function Header() {
    return (
        <header className="fixed top-0 left-0 right-0 z-50 glass-panel">
            <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:h-16 sm:px-6">
                <Link
                    href="/"
                    className="flex items-center gap-2.5 text-lg font-semibold tracking-tight"
                >
                    {/* MASX AI Logo */}
                    <Image
                        src="/logo.png"
                        alt="MASX AI Logo"
                        width={28}
                        height={28}
                        className="rounded-lg"
                        style={{
                            filter: "drop-shadow(0 2px 8px var(--glow-teal))",
                        }}
                    />
                    <span className="gradient-text-teal">EchoAI</span>
                </Link>

                <nav className="flex items-center gap-5">
                    <Link
                        href="/"
                        className="text-sm text-[var(--color-text-muted)] transition-colors hover:text-[var(--color-text)]"
                    >
                        Home
                    </Link>

                    {/* Notification bell */}
                    <button className="relative hidden h-9 w-9 items-center justify-center rounded-lg border border-white/6 bg-white/3 text-[var(--color-text-muted)] transition-all hover:bg-white/8 hover:text-[var(--color-text)] sm:flex">
                        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
                        </svg>
                        <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full" style={{ background: "var(--color-coral)" }} />
                    </button>

                    {/* Chat CTA */}
                    <Link
                        href="/chat"
                        className="flex items-center gap-1 rounded-lg border border-[var(--color-teal)]/30 bg-[var(--color-teal)]/10 px-2 py-1 text-[10px] font-medium text-[var(--color-teal)] transition-all hover:scale-[1.03] hover:bg-[var(--color-teal)]/20 sm:gap-1.5 sm:px-3 sm:py-1.5 sm:text-xs"
                    >
                        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                        </svg>
                        Chat Now
                    </Link>
                </nav>
            </div>
        </header>
    );
}
