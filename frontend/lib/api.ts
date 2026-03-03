import type { PersonaData } from "./types";

const API_BASE = "/api";

export async function fetchPersona(): Promise<PersonaData> {
    const res = await fetch(`${API_BASE}/persona`, {
        headers: { "X-Requested-With": "EchoAI" },
    });
    if (!res.ok) throw new Error("Failed to load persona data");
    return res.json();
}

