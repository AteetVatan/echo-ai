import { NextRequest, NextResponse } from "next/server";
import crypto from "crypto";
import { verifyRequest } from "@/lib/api-security";

/**
 * Generates an HMAC-signed session token for WebSocket authentication.
 *
 * Flow:
 * 1. Browser calls GET /api/auth/ws-token (no API key needed)
 * 2. This route signs the current timestamp with ECHOAI_API_KEY (server-side only)
 * 3. Browser sends the token as WS first-message auth
 * 4. FastAPI backend verifies the HMAC signature + timestamp freshness
 *
 * Token format: "<unix_timestamp>.<hmac_sha256_hex>"
 * Tokens expire after 5 minutes.
 */

// Basic in-memory rate limiting: max 10 tokens per IP per minute
const tokenRequests = new Map<string, { count: number; resetAt: number }>();
const TOKEN_RATE_LIMIT = 10;
const TOKEN_RATE_WINDOW_MS = 60_000;

function checkTokenRateLimit(ip: string): boolean {
    const now = Date.now();
    const entry = tokenRequests.get(ip);

    if (!entry || now > entry.resetAt) {
        tokenRequests.set(ip, { count: 1, resetAt: now + TOKEN_RATE_WINDOW_MS });
        return true;
    }

    if (entry.count >= TOKEN_RATE_LIMIT) {
        return false;
    }

    entry.count++;
    return true;
}

// Periodic cleanup to prevent memory leak (every 5 minutes)
if (typeof setInterval !== "undefined") {
    setInterval(() => {
        const now = Date.now();
        for (const [ip, entry] of tokenRequests) {
            if (now > entry.resetAt) tokenRequests.delete(ip);
        }
    }, 5 * 60_000);
}

export async function GET(req: NextRequest) {
    // CSRF check (no X-Requested-With required — ws-token is fetched from onopen)
    const rejection = verifyRequest(req, { requireCustomHeader: false });
    if (rejection) return rejection;

    // Rate limiting
    const ip = req.headers.get("x-forwarded-for")?.split(",")[0]?.trim()
        || req.headers.get("x-real-ip")
        || "unknown";

    if (!checkTokenRateLimit(ip)) {
        return NextResponse.json(
            { error: "Rate limit exceeded" },
            { status: 429 },
        );
    }

    const key = process.env.ECHOAI_API_KEY;
    if (!key) {
        // No key configured — return empty token (backend will skip auth)
        return NextResponse.json({ token: "" });
    }

    const timestamp = Math.floor(Date.now() / 1000).toString();
    const hmac = crypto
        .createHmac("sha256", key)
        .update(timestamp)
        .digest("hex");

    return NextResponse.json({ token: `${timestamp}.${hmac}` });
}
