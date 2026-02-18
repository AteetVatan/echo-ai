"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import type { ChatMessage, VoiceState, WSIncomingMessage } from "@/lib/types";

/* ── helpers ─────────────────────────────────────────────────────────── */

function generateId() {
    return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

const GREETING: ChatMessage = {
    id: "greeting",
    role: "assistant",
    content:
        "Hey there! I'm Ateet's AI clone : a digital twin powered by RAG and grounded in his real experience. Ask me anything about his work, projects, or skills.",
    timestamp: Date.now(),
};

const TALK_TIMEOUT_MS = 5 * 60 * 1000; // 5 minutes
const VAD_THRESHOLD_IDLE = 0.01;
const VAD_THRESHOLD_SPEAKING = 0.04;
const SILENCE_DURATION_MS = 1500;
const MIN_SPEECH_MS = 500;
const MAX_SEND_RETRIES = 30; // 3 seconds max wait for WS open
const PING_INTERVAL_MS = 25_000; // FIX R7: keepalive every 25s
const ERROR_DISMISS_MS = 6000; // FIX R10: auto-dismiss errors

/**
 * WebSocket URL — connects directly to the FastAPI backend.
 * Next.js rewrites do NOT proxy WebSocket upgrade requests,
 * so we bypass Next.js and connect to the backend directly.
 */
function getWsUrl(): string {
    if (typeof window === "undefined") return "";
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const isDev = window.location.port === "3000";
    const host = isDev ? `${window.location.hostname}:8000` : window.location.host;
    return `${proto}//${host}/ws/voice`;
}

/* ── hook ─────────────────────────────────────────────────────────────── */

export function useChat() {
    // FIX U3: Fresh timestamp per mount (not stale module-load time)
    const [messages, setMessages] = useState<ChatMessage[]>(() => [
        { ...GREETING, timestamp: Date.now() },
    ]);
    const [voiceState, setVoiceState] = useState<VoiceState>("chatMode");
    const [isConnected, setIsConnected] = useState(false);
    const [isTalkMode, setIsTalkMode] = useState(false);
    const [talkTimeRemaining, setTalkTimeRemaining] = useState(TALK_TIMEOUT_MS);
    const [error, setError] = useState<string | null>(null);

    // Refs for mutable state (avoid stale closures)
    const wsRef = useRef<WebSocket | null>(null);
    const sessionIdRef = useRef<string | null>(null);
    const mediaStreamRef = useRef<MediaStream | null>(null);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const audioContextRef = useRef<AudioContext | null>(null);
    const analyserRef = useRef<AnalyserNode | null>(null);
    const vadFrameRef = useRef<number>(0);
    const audioPlayerRef = useRef<HTMLAudioElement | null>(null);
    const talkTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const talkStartRef = useRef<number>(0);
    const talkElapsedPausedRef = useRef<number>(0);
    const silenceStartRef = useRef<number>(0);
    const speechStartRef = useRef<number>(0);
    const voiceStateRef = useRef<VoiceState>("chatMode");
    const isTalkModeRef = useRef(false);
    const isConnectingRef = useRef(false); // FIX R8: prevent double connect
    const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null); // FIX V1
    const pingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null); // FIX R7
    const errorTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null); // FIX R10
    const blobUrlsRef = useRef<string[]>([]); // FIX R4: track blob URLs for cleanup

    // FIX R1/R3 callback refs (break stale closure chains)
    const playAudioRef = useRef<(url: string) => void>(() => { });
    const startRecordingRef = useRef<() => void>(() => { });
    const stopRecordingAndSendRef = useRef<() => void>(() => { });
    const stopAudioPlaybackRef = useRef<() => void>(() => { });
    const doSendRef = useRef<(text: string) => void>(() => { }); // FIX R1

    // Keep refs in sync with state
    useEffect(() => { voiceStateRef.current = voiceState; }, [voiceState]);
    useEffect(() => { isTalkModeRef.current = isTalkMode; }, [isTalkMode]);

    /* ── Error with auto-dismiss (FIX R10) ────────────────────────── */

    const setErrorWithDismiss = useCallback((msg: string) => {
        setError(msg);
        if (errorTimerRef.current) clearTimeout(errorTimerRef.current);
        errorTimerRef.current = setTimeout(() => {
            setError(null);
            errorTimerRef.current = null;
        }, ERROR_DISMISS_MS);
    }, []);

    /* ── WebSocket ────────────────────────────────────────────────── */

    const connectWs = useCallback(() => {
        // FIX R8: prevent double connections
        if (isConnectingRef.current) return;
        if (wsRef.current?.readyState === WebSocket.OPEN) return;

        const url = getWsUrl();
        if (!url) return;

        isConnectingRef.current = true;
        const ws = new WebSocket(url);
        wsRef.current = ws;

        ws.onopen = () => {
            isConnectingRef.current = false;
            setIsConnected(true);
            setError(null);

            // FIX R7: Start heartbeat
            if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
            pingIntervalRef.current = setInterval(() => {
                if (wsRef.current?.readyState === WebSocket.OPEN) {
                    wsRef.current.send(JSON.stringify({ type: "ping" }));
                }
            }, PING_INTERVAL_MS);
        };

        ws.onmessage = (event) => {
            try {
                const msg: WSIncomingMessage = JSON.parse(event.data);
                handleWsMessage(msg);
            } catch {
                console.error("Failed to parse WS message");
            }
        };

        ws.onclose = () => {
            isConnectingRef.current = false;
            setIsConnected(false);
            wsRef.current = null;

            // Stop heartbeat
            if (pingIntervalRef.current) {
                clearInterval(pingIntervalRef.current);
                pingIntervalRef.current = null;
            }

            // Auto-reconnect after 2s if still in talk mode
            // FIX V1: Track timer so it can be cancelled on unmount
            reconnectTimerRef.current = setTimeout(() => {
                reconnectTimerRef.current = null;
                if (isTalkModeRef.current) connectWs();
            }, 2000);
        };

        ws.onerror = () => {
            isConnectingRef.current = false;
            setErrorWithDismiss("WebSocket connection failed");
            ws.close();
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps -- uses refs to avoid stale closures
    }, []);

    const sendWs = useCallback((data: Record<string, unknown>) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify(data));
        }
    }, []);

    /* ── WS message handler ──────────────────────────────────────── */

    const handleWsMessage = useCallback((msg: WSIncomingMessage) => {
        switch (msg.type) {
            case "connection":
                sessionIdRef.current = msg.session_id || null;
                break;

            case "processing":
                setVoiceState("processing");
                break;

            case "response":
            case "text_response":
            case "streaming_response": {
                // FIX R4: Convert base64 to Blob URL (small string in state)
                let audioUrl: string | undefined;
                if (msg.audio) {
                    try {
                        const binaryStr = atob(msg.audio);
                        const bytes = new Uint8Array(binaryStr.length);
                        for (let i = 0; i < binaryStr.length; i++) {
                            bytes[i] = binaryStr.charCodeAt(i);
                        }
                        const blob = new Blob([bytes], { type: "audio/mpeg" });
                        audioUrl = URL.createObjectURL(blob);
                        blobUrlsRef.current.push(audioUrl);
                    } catch {
                        console.error("Failed to decode audio");
                    }
                }

                // FIX R5: Add transcription as user message ONLY for voice responses
                // (text_response is for typed text — user message was already added by doSend)
                if (msg.transcription && msg.type !== "text_response") {
                    setMessages((prev) => [
                        ...prev,
                        {
                            id: generateId(),
                            role: "user",
                            content: msg.transcription!,
                            timestamp: Date.now(),
                            transcription: msg.transcription,
                        },
                    ]);
                }

                // Add AI response message
                // Only attach audioUrl when in voice mode so chat mode stays text-only
                const attachAudio = isTalkModeRef.current ? audioUrl : undefined;
                if (msg.response_text) {
                    setMessages((prev) => [
                        ...prev,
                        {
                            id: generateId(),
                            role: "assistant",
                            content: msg.response_text!,
                            timestamp: Date.now(),
                            audioUrl: attachAudio,
                        },
                    ]);
                }

                // Play audio only in voice mode
                if (attachAudio) {
                    playAudioRef.current(attachAudio);
                } else {
                    setVoiceState(isTalkModeRef.current ? "idle" : "chatMode");
                }
                break;
            }

            case "error":
                setErrorWithDismiss(msg.message || "Unknown error");
                setVoiceState(isTalkModeRef.current ? "idle" : "chatMode");
                break;

            case "pong":
                break;
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps -- uses refs intentionally
    }, []);

    /* ── Audio playback ──────────────────────────────────────────── */

    const playAudio = useCallback((audioUrl: string) => {
        setVoiceState("speaking");
        const audio = new Audio(audioUrl);
        audioPlayerRef.current = audio;

        audio.onended = () => {
            audioPlayerRef.current = null;
            setVoiceState(isTalkModeRef.current ? "idle" : "chatMode");
        };

        audio.onerror = () => {
            audioPlayerRef.current = null;
            setVoiceState(isTalkModeRef.current ? "idle" : "chatMode");
        };

        audio.play().catch(() => {
            audioPlayerRef.current = null;
            setVoiceState(isTalkModeRef.current ? "idle" : "chatMode");
        });
    }, []);

    useEffect(() => { playAudioRef.current = playAudio; }, [playAudio]);

    /* ── VAD (Voice Activity Detection) ──────────────────────────── */

    const startVAD = useCallback(() => {
        if (!analyserRef.current) return;

        const analyser = analyserRef.current;
        const buffer = new Uint8Array(analyser.fftSize);

        const check = () => {
            if (!isTalkModeRef.current) return;

            analyser.getByteTimeDomainData(buffer);

            // RMS calculation
            let sum = 0;
            for (let i = 0; i < buffer.length; i++) {
                const v = (buffer[i] - 128) / 128;
                sum += v * v;
            }
            const rms = Math.sqrt(sum / buffer.length);

            const currentState = voiceStateRef.current;
            const threshold =
                currentState === "speaking"
                    ? VAD_THRESHOLD_SPEAKING
                    : VAD_THRESHOLD_IDLE;

            const now = Date.now();

            if (rms > threshold) {
                if (currentState === "idle") {
                    speechStartRef.current = now;
                    silenceStartRef.current = 0;
                    setVoiceState("listening");
                    startRecordingRef.current();
                } else if (currentState === "listening") {
                    silenceStartRef.current = 0;
                } else if (currentState === "speaking") {
                    if (!speechStartRef.current) {
                        speechStartRef.current = now;
                    } else if (now - speechStartRef.current > MIN_SPEECH_MS) {
                        stopAudioPlaybackRef.current();
                        setVoiceState("interrupted");
                        setTimeout(() => {
                            setVoiceState("listening");
                            startRecordingRef.current();
                        }, 100);
                        speechStartRef.current = 0;
                    }
                }
            } else {
                if (currentState === "listening") {
                    if (!silenceStartRef.current) {
                        silenceStartRef.current = now;
                    } else if (now - silenceStartRef.current > SILENCE_DURATION_MS) {
                        stopRecordingAndSendRef.current();
                        silenceStartRef.current = 0;
                        speechStartRef.current = 0;
                    }
                } else if (currentState === "speaking") {
                    speechStartRef.current = 0;
                }
            }

            vadFrameRef.current = requestAnimationFrame(check);
        };

        vadFrameRef.current = requestAnimationFrame(check);
        // eslint-disable-next-line react-hooks/exhaustive-deps -- all mutable via refs
    }, []);

    /* ── MediaRecorder ────────────────────────────────────────────── */

    const startRecording = useCallback(() => {
        if (!mediaStreamRef.current) return;
        if (
            mediaRecorderRef.current &&
            mediaRecorderRef.current.state === "recording"
        )
            return;

        // Safari doesn't support webm — graceful fallback
        let options: MediaRecorderOptions | undefined;
        if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) {
            options = { mimeType: "audio/webm;codecs=opus" };
        } else if (MediaRecorder.isTypeSupported("audio/mp4")) {
            options = { mimeType: "audio/mp4" };
        }

        const recorder = options
            ? new MediaRecorder(mediaStreamRef.current, options)
            : new MediaRecorder(mediaStreamRef.current);

        const chunks: Blob[] = [];
        recorder.ondataavailable = (e) => {
            if (e.data.size > 0) chunks.push(e.data);
        };

        recorder.onstop = () => {
            if (chunks.length === 0) return;
            const blob = new Blob(chunks, { type: recorder.mimeType });
            sendAudioBlob(blob);
        };

        recorder.start();
        mediaRecorderRef.current = recorder;
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    useEffect(() => { startRecordingRef.current = startRecording; }, [startRecording]);

    const stopRecordingAndSend = useCallback(() => {
        if (
            mediaRecorderRef.current &&
            mediaRecorderRef.current.state === "recording"
        ) {
            mediaRecorderRef.current.stop();
            mediaRecorderRef.current = null;
            setVoiceState("processing");
        }
    }, []);

    useEffect(() => { stopRecordingAndSendRef.current = stopRecordingAndSend; }, [stopRecordingAndSend]);

    const sendAudioBlob = useCallback(async (blob: Blob) => {
        const buffer = await blob.arrayBuffer();
        const base64 = btoa(
            new Uint8Array(buffer).reduce(
                (data, byte) => data + String.fromCharCode(byte),
                ""
            )
        );
        sendWs({ type: "audio", audio: base64 });
    }, [sendWs]);

    /* ── Audio playback control ───────────────────────────────────── */

    const stopAudioPlayback = useCallback(() => {
        if (audioPlayerRef.current) {
            audioPlayerRef.current.pause();
            audioPlayerRef.current.currentTime = 0;
            audioPlayerRef.current = null;
        }
    }, []);

    useEffect(() => { stopAudioPlaybackRef.current = stopAudioPlayback; }, [stopAudioPlayback]);

    /* ── Talk mode lifecycle ──────────────────────────────────────── */

    const startTalkMode = useCallback(async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                },
            });
            mediaStreamRef.current = stream;

            const audioCtx = new AudioContext();
            const source = audioCtx.createMediaStreamSource(stream);
            const analyser = audioCtx.createAnalyser();
            analyser.fftSize = 2048;
            source.connect(analyser);
            audioContextRef.current = audioCtx;
            analyserRef.current = analyser;

            // Connect WS if not already
            if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
                connectWs();
            }

            // Timer — pauses during processing/speaking
            talkStartRef.current = Date.now();
            talkElapsedPausedRef.current = 0;
            setTalkTimeRemaining(TALK_TIMEOUT_MS);
            talkTimerRef.current = setInterval(() => {
                const state = voiceStateRef.current;
                if (state === "processing" || state === "speaking") {
                    talkElapsedPausedRef.current += 1000;
                }
                const realElapsed = Date.now() - talkStartRef.current;
                const activeElapsed = realElapsed - talkElapsedPausedRef.current;
                const remaining = Math.max(0, TALK_TIMEOUT_MS - activeElapsed);
                setTalkTimeRemaining(remaining);
                if (remaining <= 0) {
                    stopTalkMode();
                }
            }, 1000);

            setIsTalkMode(true);
            setVoiceState("idle");
            isTalkModeRef.current = true;

            startVAD();
        } catch (err) {
            const msg =
                err instanceof DOMException && err.name === "NotAllowedError"
                    ? "Microphone access denied. Please allow microphone access."
                    : "Failed to start talk mode";
            setErrorWithDismiss(msg);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [connectWs, startVAD]);

    // V2: Intentionally keeps WS open so text chat can reuse the connection
    const stopTalkMode = useCallback(() => {
        if (vadFrameRef.current) {
            cancelAnimationFrame(vadFrameRef.current);
            vadFrameRef.current = 0;
        }

        if (
            mediaRecorderRef.current &&
            mediaRecorderRef.current.state === "recording"
        ) {
            mediaRecorderRef.current.stop();
            mediaRecorderRef.current = null;
        }

        stopAudioPlayback();

        if (talkTimerRef.current) {
            clearInterval(talkTimerRef.current);
            talkTimerRef.current = null;
        }

        if (mediaStreamRef.current) {
            mediaStreamRef.current.getTracks().forEach((t) => t.stop());
            mediaStreamRef.current = null;
        }
        if (audioContextRef.current) {
            audioContextRef.current.close();
            audioContextRef.current = null;
        }
        analyserRef.current = null;

        setIsTalkMode(false);
        isTalkModeRef.current = false;
        setVoiceState("chatMode");
    }, [stopAudioPlayback]);

    /* ── Text chat (over WS) ──────────────────────────────────────── */

    const doSend = useCallback(
        (text: string) => {
            setMessages((prev) => [
                ...prev,
                {
                    id: generateId(),
                    role: "user",
                    content: text,
                    timestamp: Date.now(),
                },
            ]);

            setVoiceState("processing");
            sendWs({ type: "text", text, voice_mode: isTalkModeRef.current });
        },
        [sendWs]
    );

    // FIX R1: keep doSend ref in sync so `send` never has a stale closure
    useEffect(() => { doSendRef.current = doSend; }, [doSend]);

    const send = useCallback(
        (text: string) => {
            const trimmed = text.trim();
            if (!trimmed) return;

            if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
                connectWs();
                let attempts = 0;
                const checkAndSend = () => {
                    if (wsRef.current?.readyState === WebSocket.OPEN) {
                        doSendRef.current(trimmed); // FIX R1: use ref
                    } else if (attempts < MAX_SEND_RETRIES) {
                        attempts++;
                        setTimeout(checkAndSend, 100);
                    } else {
                        setErrorWithDismiss("Could not connect to server. Please try again.");
                        setVoiceState(isTalkModeRef.current ? "idle" : "chatMode");
                    }
                };
                setTimeout(checkAndSend, 200);
                return;
            }

            doSendRef.current(trimmed); // FIX R1: use ref
        },
        [connectWs, setErrorWithDismiss]
    );

    /* ── Clear ────────────────────────────────────────────────────── */

    const clearChat = useCallback(() => {
        setMessages([{ ...GREETING, timestamp: Date.now() }]);
        setError(null);
        sendWs({ type: "clear_history" });
        // FIX T5: Revoke blob URLs to free memory
        blobUrlsRef.current.forEach((url) => URL.revokeObjectURL(url));
        blobUrlsRef.current = [];
    }, [sendWs]);

    /* ── Cleanup on unmount ───────────────────────────────────────── */

    useEffect(() => {
        return () => {
            if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current); // FIX V1
            if (wsRef.current) wsRef.current.close();
            if (vadFrameRef.current) cancelAnimationFrame(vadFrameRef.current);
            if (talkTimerRef.current) clearInterval(talkTimerRef.current);
            if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
            if (errorTimerRef.current) clearTimeout(errorTimerRef.current);
            if (mediaStreamRef.current)
                mediaStreamRef.current.getTracks().forEach((t) => t.stop());
            if (audioContextRef.current) audioContextRef.current.close();
            // FIX R4: Revoke all created blob URLs
            blobUrlsRef.current.forEach((url) => URL.revokeObjectURL(url));
        };
    }, []);

    const isLoading = voiceState === "processing";

    // Convenience toggle for the voice-mode button
    const toggleVoiceMode = useCallback(() => {
        if (isTalkModeRef.current) {
            stopTalkMode();
        } else {
            startTalkMode();
        }
    }, [startTalkMode, stopTalkMode]);

    return {
        messages,
        isLoading,
        voiceState,
        isConnected,
        isTalkMode,
        talkTimeRemaining,
        error,
        send,
        clearChat,
        startTalkMode,
        stopTalkMode,
        toggleVoiceMode,
        playAudio,
    };
}
