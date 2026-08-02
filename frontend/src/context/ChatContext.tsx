import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  useCallback,
} from "react";
import type { ReactNode } from "react";

export type VoiceState =
  | "listening"
  | "transcribing"
  | "thinking"
  | "speaking"
  | "idle";

interface VoiceEvent {
  state: VoiceState;
  transcript?: string;
  reply?: string;
  timestamp?: number;
}

interface TurnResult {
  state: "result";
  success: boolean;
  transcript: string;
  reply: string;
  error: string | null;
  latency_ms: number;
}

interface ChatContextValue {
  connected: boolean;
  voiceState: VoiceState;
  voiceTranscript: string;
  voiceReply: string;
  lastResult: TurnResult | null;
  triggerTurn: () => void;
}

const ChatContext = createContext<ChatContextValue | undefined>(undefined);

function getWebSocketUrl(): string {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  // Backend runs on 8000 regardless of what port the frontend is served on
  return `${protocol}://${window.location.hostname}:8000/ws/voice`;
}

const RECONNECT_DELAY_MS = 2000;

export function ChatProvider({ children }: { children: ReactNode }) {
  const [connected, setConnected] = useState(false);
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [voiceTranscript, setVoiceTranscript] = useState("");
  const [voiceReply, setVoiceReply] = useState("");
  const [lastResult, setLastResult] = useState<TurnResult | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);

  const connect = useCallback(() => {
    const ws = new WebSocket(getWebSocketUrl());

    ws.onopen = () => {
      setConnected(true);
    };

    ws.onclose = () => {
      setConnected(false);
      // Only attempt reconnect if the component is still mounted
      // (avoids reconnect loops firing after unmount in dev StrictMode)
      if (mountedRef.current) {
        reconnectTimerRef.current = setTimeout(connect, RECONNECT_DELAY_MS);
      }
    };

    ws.onerror = (err) => {
      console.error("Voice WebSocket error:", err);
      // onclose fires right after onerror for a failed connection,
      // so reconnect scheduling happens there — nothing to do here.
    };

    ws.onmessage = (msg) => {
      const data = JSON.parse(msg.data);

      if (data.state === "result") {
        setLastResult(data as TurnResult);
        setVoiceState("idle");
        return;
      }

      const event = data as VoiceEvent;
      setVoiceState(event.state);
      if (event.transcript) setVoiceTranscript(event.transcript);
      if (event.reply) setVoiceReply(event.reply);
    };

    wsRef.current = ws;
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [connect]);

  const triggerTurn = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      setVoiceTranscript("");
      setVoiceReply("");
      setLastResult(null);
      wsRef.current.send(JSON.stringify({ action: "start_turn" }));
    } else {
      console.warn("Voice WebSocket not connected");
    }
  }, []);

  return (
    <ChatContext.Provider
      value={{
        connected,
        voiceState,
        voiceTranscript,
        voiceReply,
        lastResult,
        triggerTurn,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}

export function useChat() {
  const ctx = useContext(ChatContext);
  if (!ctx) {
    throw new Error("useChat must be used within a ChatProvider");
  }
  return ctx;
}