import { NextResponse } from "next/server";

/**
 * Deep health-check endpoint used by Railway's healthcheck (via nginx).
 *
 * Returns 200 only when ALL of:
 *  - FastAPI backend is reachable
 *  - Next.js can serve its own `/` root page (not just this API route)
 *
 * The second check matters because an API route handler can be ready
 * before Next.js has compiled/warmed the root page bundle. Without it,
 * Railway routes traffic too early and first-time visitors see a raw
 * 404 until they refresh.
 */

const BACKEND_PORT = process.env.BACKEND_PORT || "8000";
const BACKEND_URL =
    process.env.INTERNAL_BACKEND_URL || `http://127.0.0.1:${BACKEND_PORT}`;
const FRONTEND_PORT = process.env.PORT || "3000";
const FRONTEND_SELF_URL =
    process.env.INTERNAL_FRONTEND_URL || `http://127.0.0.1:${FRONTEND_PORT}`;

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
    } catch {
        return NextResponse.json(
            { status: "starting", frontend: "ok", backend: "unreachable" },
            { status: 503 },
        );
    }

    try {
        const rootRes = await fetch(`${FRONTEND_SELF_URL}/`, {
            method: "HEAD",
            signal: AbortSignal.timeout(3000),
        });
        if (!rootRes.ok) {
            return NextResponse.json(
                { status: "starting", frontend: "compiling", backend: "ok" },
                { status: 503 },
            );
        }
    } catch {
        return NextResponse.json(
            { status: "starting", frontend: "compiling", backend: "ok" },
            { status: 503 },
        );
    }

    return NextResponse.json(
        { status: "ok", frontend: "ok", backend: "ok" },
        { status: 200 },
    );
}
