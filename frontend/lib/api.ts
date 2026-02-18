import type { PersonaData } from "./types";

const API_BASE = "/api";

export async function fetchPersona(): Promise<PersonaData> {
    const res = await fetch(`${API_BASE}/persona`, {
        headers: {
            "X-API-Key": process.env.NEXT_PUBLIC_ECHOAI_API_KEY ?? "",
        },
    });
    if (!res.ok) throw new Error("Failed to load persona data");
    return res.json();
}

