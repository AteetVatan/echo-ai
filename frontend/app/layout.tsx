import type { Metadata } from "next";
import { Inter, Outfit } from "next/font/google";
import "./globals.css";
import { Header } from "@/components/layout/Header";
import { LayoutShell } from "@/components/layout/LayoutShell";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

const outfit = Outfit({
  subsets: ["latin"],
  variable: "--font-outfit",
});

export const metadata: Metadata = {
  title: "EchoAI — Talk to Ateet's AI Clone",
  description:
    "Chat with an AI-powered digital twin built on RAG, real-time voice synthesis, and grounded knowledge retrieval.",
  keywords: ["AI clone", "RAG", "voice AI", "digital twin", "Ateet Vatan Bahmani"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} ${outfit.variable} antialiased`} suppressHydrationWarning>
        <Header />
        <LayoutShell>{children}</LayoutShell>
      </body>
    </html>
  );
}
