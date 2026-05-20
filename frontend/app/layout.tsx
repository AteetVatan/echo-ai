import type { Metadata } from "next";
import "./globals.css";
import { Header } from "@/components/layout/Header";
import { LayoutShell } from "@/components/layout/LayoutShell";

export const metadata: Metadata = {
  title: "EchoAI — Talk to Ateet's AI Clone",
  description:
    "Chat with an AI-powered digital twin built on RAG, real-time voice synthesis, and grounded knowledge retrieval.",
  keywords: ["AI clone", "RAG", "voice AI", "digital twin", "Ateet Bahamani"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased" suppressHydrationWarning>
        <Header />
        <LayoutShell>{children}</LayoutShell>
      </body>
    </html>
  );
}
