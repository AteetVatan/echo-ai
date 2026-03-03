import { NextResponse } from "next/server";

/**
 * Deep health-check endpoint used by Railway's healthcheck (via nginx).
 *
 * Returns 200 only when BOTH:
 *  - Next.js is serving (implicit — we're handling the request)
 *  - FastAPI backend is reachable
 *
 * If the backend isn't ready, this returns 503, so nginx returns 502/503
 * to Railway, and Railway keeps the service in "starting" state — no
 * traffic is routed until everything is warm.
 */

const BACKEND_PORT = process.env.BACKEND_PORT || "8000";
const BACKEND_URL =
    process.env.INTERNAL_BACKEND_URL || `http://127.0.0.1:${BACKEND_PORT}`;

export async function GET() {
    try {
        const res = await fetch(`${BACKEND_URL}/health`, {
            signal: AbortSignal.timeout(3000),
        });

        if (!res.ok) {
            return NextResponse.json(
                { status: "degraded", frontend: "ok", backend: "unhealthy" },
                { status: 503 },
            );
        }

        return NextResponse.json(
            { status: "ok", frontend: "ok", backend: "ok" },
            { status: 200 },
        );
    } catch {
        return NextResponse.json(
            { status: "starting", frontend: "ok", backend: "unreachable" },
            { status: 503 },
        );
    }
}
