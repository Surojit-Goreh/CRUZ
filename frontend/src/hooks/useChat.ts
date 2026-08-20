import { useState, useRef, useCallback, useEffect } from "react";
import type { Message } from "../types/chat";

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

function getWebSocketUrl(): string {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  return `${protocol}://${window.location.hostname}:8000/ws/voice`;
}

const RECONNECT_DELAY_MS = 2000;

function makeId(): string {
  return Date.now().toString() + Math.random().toString(36).slice(2, 7);
}

function nowTime(): string {
  return new Date().toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });
}

export default function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState<boolean>(false);

  // --- Voice State ---
  const [connected, setConnected] = useState(false);
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);

  const addUserMessage = useCallback((text: string) => {
    if (!text || !text.trim()) return;
    setMessages((prev) => [
      ...prev,
      { id: makeId(), sender: "user", text: text.trim(), timestamp: nowTime() },
    ]);
  }, []);

  const addAssistantMessage = useCallback((text: string) => {
    if (!text || !text.trim()) return;
    setMessages((prev) => [
      ...prev,
      { id: makeId(), sender: "assistant", text: text.trim(), timestamp: nowTime() },
    ]);
  }, []);

  // --- Typed Chat Streaming ---
  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim()) return;

      addUserMessage(text);
      setIsTyping(true);

      const aiId = makeId();
      let streamStarted = false;

      try {
        const response = await fetch("http://127.0.0.1:8000/chat/stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text }),
        });

        if (!response.ok || !response.body) {
          throw new Error("Network response was not ok or readable stream missing");
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let done = false;

        while (!done) {
          const { value, done: readerDone } = await reader.read();
          done = readerDone;

          if (value) {
            const chunkText = decoder.decode(value, { stream: true });
            if (!streamStarted) {
              streamStarted = true;
              setIsTyping(false);
              setMessages((prev) => [
                ...prev,
                { id: aiId, sender: "assistant", text: chunkText, timestamp: nowTime() },
              ]);
            } else {
              setMessages((prev) =>
                prev.map((m) => (m.id === aiId ? { ...m, text: m.text + chunkText } : m))
              );
            }
          }
        }

        setIsTyping(false);
      } catch (error) {
        console.error("Failed to stream AI response:", error);
        setIsTyping(false);
        setMessages((prev) => [
          ...prev,
          { id: aiId, sender: "assistant", text: "Backend connection failed.", timestamp: nowTime() },
        ]);
      }
    },
    [addUserMessage]
  );

  // --- Voice WebSocket ---
  const connect = useCallback(() => {
    const ws = new WebSocket(getWebSocketUrl());
    const isCurrent = () => wsRef.current === ws;

    ws.onopen = () => {
      if (!isCurrent()) {
        ws.close();
        return;
      }
      setConnected(true);
    };

    ws.onclose = () => {
      if (!isCurrent()) return;
      setConnected(false);
      setIsTyping(false);
      if (mountedRef.current) {
        reconnectTimerRef.current = setTimeout(connect, RECONNECT_DELAY_MS);
      }
    };

    ws.onerror = (err) => {
      if (!isCurrent()) return;
      console.error("Voice WebSocket error:", err);
    };

    ws.onmessage = (msg) => {
      if (!isCurrent()) return;

      const data = JSON.parse(msg.data);

      if (data.state === "result") {
        const result = data as TurnResult;
        setVoiceState("idle");
        setIsTyping(false);

        if (!result.success) {
          addAssistantMessage(
            result.error ? `Voice error: ${result.error}` : "Sorry, I didn't catch that."
          );
        }
        return;
      }

      const event = data as VoiceEvent;
      setVoiceState(event.state);

      if (event.state === "thinking" || event.state === "transcribing") {
        if (event.transcript) {
          addUserMessage(event.transcript);
        }
        setIsTyping(true);
      } else if (event.state === "speaking") {
        setIsTyping(false);
        if (event.reply) {
          addAssistantMessage(event.reply);
        }
      } else if (event.state === "idle") {
        setIsTyping(false);
      }
    };

    wsRef.current = ws;
  }, [addUserMessage, addAssistantMessage]);

  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);

      const ws = wsRef.current;
      wsRef.current = null;
      ws?.close();
    };
  }, [connect]);

  const startVoiceTurn = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: "start_turn" }));
    } else {
      console.warn("Voice WebSocket not connected");
    }
  }, []);

  return {
    messages,
    sendMessage,
    isTyping,
    connected,
    voiceState,
    startVoiceTurn,
  };
}
