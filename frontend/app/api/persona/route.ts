import { NextRequest, NextResponse } from "next/server";
import { verifyRequest } from "@/lib/api-security";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function GET(req: NextRequest) {
    const rejection = verifyRequest(req);
    if (rejection) return rejection;

    try {
        const res = await fetch(`${BACKEND_URL}/api/persona`, {
            headers: {
                "X-API-Key": process.env.ECHOAI_API_KEY ?? "",
            },
        });

        if (!res.ok) {
            return NextResponse.json(
                { error: "Failed to fetch persona" },
                { status: res.status },
            );
        }

        const data = await res.json();
        return NextResponse.json(data);
    } catch (error) {
        console.error("Persona proxy error:", error);
        return NextResponse.json(
            { error: "Internal server error" },
            { status: 500 },
        );
    }
}
