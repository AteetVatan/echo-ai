import { NextRequest, NextResponse } from "next/server";

/**
 * Shared API route security utilities.
 *
 * - CSRF: rejects cross-origin requests based on Origin/Referer header
 * - Browser-only: requires X-Requested-With header (blocks curl/Postman)
 */

const ALLOWED_ORIGINS = (process.env.ALLOWED_ORIGINS || "http://localhost:3000")
    .split(",")
    .map((o) => o.trim().replace(/\/$/, ""));

export function isOriginAllowed(origin: string | null): boolean {
    if (!origin) return false;
    return ALLOWED_ORIGINS.some(
        (allowed) => origin.replace(/\/$/, "") === allowed,
    );
}

/**
 * Verify that the request comes from a browser on our site.
 *
 * Checks:
 * 1. If Origin header is present, it must be in ALLOWED_ORIGINS
 *    (same-origin requests may omit Origin — that's OK)
 * 2. X-Requested-With header must be present (browsers send it via
 *    fetch headers, curl/Postman don't by default)
 *
 * @param requireCustomHeader  If true, require X-Requested-With.
 *                             Set to false for endpoints called without it
 *                             (e.g., ws-token, which is fetched from onopen).
 */
export function verifyRequest(
    req: NextRequest,
    { requireCustomHeader = true } = {},
): NextResponse | null {
    const origin = req.headers.get("origin") || req.headers.get("referer");
    const originHost = origin ? new URL(origin).origin : null;

    // CSRF: reject known cross-origin requests
    if (origin && !isOriginAllowed(originHost)) {
        return NextResponse.json({ error: "Forbidden" }, { status: 403 });
    }

    // Browser-only: block curl/Postman
    if (requireCustomHeader && !req.headers.get("x-requested-with")) {
        return NextResponse.json({ error: "Forbidden" }, { status: 403 });
    }

    return null; // request is valid
}
