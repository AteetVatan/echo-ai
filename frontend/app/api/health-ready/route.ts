import { NextResponse } from "next/server";

/**
 * Deep health-check endpoint used by Railway's healthcheck (via nginx).
 *
 * Returns 200 only when ALL of:
 *  - FastAPI backend is reachable AND reports `status: "healthy"` in its
 *    /health JSON body (backend /health always returns HTTP 200 with the
 *    real warmup state in the body, so we must parse, not just check ok)
 *  - Next.js can serve its own `/` root page (not just this API route)
 *
 * The root-page check matters because an API route handler can be ready
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

        // Backend /health always returns 200 (so direct probes don't fail)
        // and reports warmup state inside the JSON `status` field.
        // Gate Railway readiness on that field, not just HTTP status.
        const body = (await res.json()) as { status?: string };
        if (body?.status !== "healthy") {
            return NextResponse.json(
                { status: "starting", frontend: "ok", backend: body?.status ?? "warming_up" },
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
