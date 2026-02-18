export type VoiceState =
    | "chatMode"
    | "idle"
    | "listening"
    | "processing"
    | "speaking"
    | "interrupted";

export interface ChatMessage {
    id: string;
    role: "user" | "assistant";
    content: string;
    timestamp: number;
    audioUrl?: string;          // base64 data URL for replay
    transcription?: string;     // STT transcription (voice input)
}

export interface PersonaData {
    name: string;
    title: string;
    bio: string;
    location: string;
    links: {
        linkedin: string;
        github: string;
        portfolio: string;
        email: string;
    };
}

/* WebSocket message types (mirrors backend WSMessageType) */
export type WSIncomingType =
    | "connection"
    | "processing"
    | "response"
    | "text_response"
    | "streaming_response"
    | "error"
    | "pong"
    | "auth_success"
    | "auth_failed";

export interface WSIncomingMessage {
    type: WSIncomingType;
    session_id?: string;        // only present on "connection" messages
    message?: string;
    transcription?: string;
    response_text?: string;
    audio?: string | null;      // base64 MP3, or null/absent if TTS failed
    latency?: Record<string, number>;
    models_used?: Record<string, string>;
}
