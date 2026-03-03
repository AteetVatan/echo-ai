import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // NOTE: /api/persona and /api/chat are handled by Next.js API routes
  // (server-side proxy with ECHOAI_API_KEY). No rewrite needed.
  // WebSocket (/ws/*) connects directly to the backend, bypassing Next.js.
};

export default nextConfig;
