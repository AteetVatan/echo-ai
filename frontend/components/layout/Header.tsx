import Link from "next/link";
import Image from "next/image";

export function Header() {
    return (
        <header className="fixed top-0 left-0 right-0 z-50 glass-panel">
            <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
                <Link
                    href="/"
                    className="flex items-center gap-2.5 text-lg font-semibold tracking-tight"
                >
                    {/* MASX AI Logo */}
                    <Image
                        src="/logo.png"
                        alt="MASX AI Logo"
                        width={36}
                        height={36}
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
                    <button className="relative flex h-9 w-9 items-center justify-center rounded-lg border border-white/6 bg-white/3 text-[var(--color-text-muted)] transition-all hover:bg-white/8 hover:text-[var(--color-text)]">
                        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
                        </svg>
                        <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full" style={{ background: "var(--color-coral)" }} />
                    </button>

                    {/* Chat CTA */}
                    <Link
                        href="/chat"
                        className="rounded-full px-5 py-2 text-sm font-medium text-white transition-all hover:scale-105 hover:brightness-110"
                        style={{
                            background: "linear-gradient(135deg, #00cec9, #0984e3)",
                            boxShadow: "0 0 12px rgba(0, 206, 201, 0.25), 0 4px 16px rgba(0, 206, 201, 0.15), inset 0 1px 0 rgba(255,255,255,0.12)",
                        }}
                    >
                        Chat Now
                    </Link>
                </nav>
            </div>
        </header>
    );
}
