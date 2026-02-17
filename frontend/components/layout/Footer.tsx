export function Footer() {
    const links = [
        { label: "LinkedIn", href: "https://www.linkedin.com/in/ateet-vatan-bahmani/" },
        { label: "GitHub", href: "https://github.com/AteetVatan" },
        { label: "Portfolio", href: "https://ateetai.vercel.app/" },
    ];

    return (
        <footer className="relative border-t border-white/5 bg-[var(--color-bg)]">
            {/* Subtle top glow */}
            <div className="pointer-events-none absolute -top-px left-1/2 h-px w-1/2 -translate-x-1/2"
                style={{ background: "linear-gradient(90deg, transparent, var(--color-pink), transparent)" }} />

            <div className="mx-auto flex max-w-7xl flex-col items-center gap-4 px-6 py-10 sm:flex-row sm:justify-between">
                <p className="text-sm text-[var(--color-text-dim)]">
                    © {new Date().getFullYear()} Ateet Vatan Bahmani. Built with{" "}
                    <span className="gradient-text-pink font-medium">EchoAI</span>.
                </p>
                <div className="flex gap-6">
                    {links.map((l) => (
                        <a
                            key={l.label}
                            href={l.href}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm text-[var(--color-text-muted)] transition-colors hover:text-[var(--color-pink-light)]"
                        >
                            {l.label}
                        </a>
                    ))}
                </div>
            </div>
        </footer>
    );
}
