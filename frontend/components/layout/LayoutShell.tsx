"use client";

import { usePathname } from "next/navigation";
import { Footer } from "@/components/layout/Footer";

export function LayoutShell({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const isChatPage = pathname.startsWith("/chat");

    return (
        <>
            <main className={isChatPage ? "pt-14 sm:pt-16" : "min-h-screen"}>
                {children}
            </main>
            {!isChatPage && <Footer />}
        </>
    );
}
