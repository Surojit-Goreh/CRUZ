import { useState, useRef, useCallback, useEffect } from "react";
import type { Message } from "../types/chat";
import useWakeWord from "./useWakeWord";

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

function detectClientAgentMode(text: string): string | null {
  const lower = text.toLowerCase().trim();
  if (/\b(image|vision)\s*(mode|agent|node)?\b/i.test(lower) && /\b(change|switch|set|turn|enable|activate|on|to|use)\b/i.test(lower)) {
    return "image";
  }
  if (/\b(reasoning|resoning|plan|planning)\s*(mode|agent|node)?\b/i.test(lower) && /\b(change|switch|set|turn|enable|activate|on|to|use)\b/i.test(lower)) {
    return "plan";
  }
  if (/\b(build|coding|code|developer)\s*(mode|agent|node)?\b/i.test(lower) && /\b(change|switch|set|turn|enable|activate|on|to|use)\b/i.test(lower)) {
    return "build";
  }
  if (/\b(writing|writer)\s*(mode|agent|node)?\b/i.test(lower) && /\b(change|switch|set|turn|enable|activate|on|to|use)\b/i.test(lower)) {
    return "writing";
  }
  if (/\b(chat|fast chat|speed)\s*(mode|agent|node)?\b/i.test(lower) && /\b(change|switch|set|turn|enable|activate|on|to|use)\b/i.test(lower)) {
    return "chat";
  }
  if (/\b(auto|automatic|dispatcher)\s*(mode|agent|node)?\b/i.test(lower) && /\b(change|switch|set|turn|enable|activate|on|to|use)\b/i.test(lower)) {
    return "auto";
  }
  return null;
}

export default function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState<boolean>(false);
  const [agentMode, setAgentMode] = useState<string>("auto");
  const [selectedModel, setSelectedModel] = useState<string>("auto");

  // --- Voice State ---
  const [connected, setConnected] = useState(false);
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [wakeWordEnabled, setWakeWordEnabled] = useState(true);
  const [continuousMode, setContinuousMode] = useState(true);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const continuousTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);
  const connectRef = useRef<() => void>(() => undefined);
  const continuousModeRef = useRef(continuousMode);
  const agentModeRef = useRef(agentMode);
  const selectedModelRef = useRef(selectedModel);

  useEffect(() => {
    continuousModeRef.current = continuousMode;
  }, [continuousMode]);

  useEffect(() => {
    agentModeRef.current = agentMode;
  }, [agentMode]);

  useEffect(() => {
    selectedModelRef.current = selectedModel;
  }, [selectedModel]);

  const addUserMessage = useCallback((text: string) => {
    if (!text || !text.trim()) return;
    setMessages((prev) => [
      ...prev,
      { id: makeId(), sender: "user", text: text.trim(), timestamp: nowTime() },
    ]);
  }, []);

  const addAssistantMessage = useCallback((text: string, provider?: string, model?: string) => {
    if (!text || !text.trim()) return;
    setMessages((prev) => [
      ...prev,
      { id: makeId(), sender: "assistant", text: text.trim(), timestamp: nowTime(), provider, model },
    ]);
  }, []);

  // --- Typed Chat Streaming ---
  const sendMessage = useCallback(
    async (text: string, explicitAgentMode?: string, explicitModel?: string) => {
      if (!text.trim()) return;

      const clientDetectedMode = detectClientAgentMode(text);
      if (clientDetectedMode) {
        setAgentMode(clientDetectedMode);
      }

      addUserMessage(text);
      setIsTyping(true);

      const aiId = makeId();
      let streamStarted = false;
      const targetMode = explicitAgentMode || clientDetectedMode || agentModeRef.current || "auto";
      const targetModel = explicitModel || selectedModelRef.current || "auto";

      try {
        const response = await fetch("http://127.0.0.1:8000/chat/stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: text,
            agent_mode: targetMode,
            model: targetModel !== "auto" ? targetModel : undefined,
          }),
        });

        if (!response.ok || !response.body) {
          throw new Error("Network response was not ok or readable stream missing");
        }

        const agentModeHeader = response.headers.get("X-Agent-Mode");

        if (agentModeHeader) {
          setAgentMode(agentModeHeader);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let done = false;
        let eventBuffer = "";
        let liveProvider: string | undefined;
        let liveModel: string | undefined;

        const handleSseEvent = (rawEvent: string) => {
          const lines = rawEvent.split("\n");
          const eventLine = lines.find((l) => l.startsWith("event:"));
          const eventType = eventLine ? eventLine.slice(6).trim() : "token";
          const dataLines = lines
            .filter((l) => l.startsWith("data:"))
            .map((l) => l.slice(5).trim());
          const dataStr = dataLines.join("\n");
          if (!dataStr) return;

          try {
            const parsed = JSON.parse(dataStr);
            if (eventType === "metadata") {
              liveProvider = parsed.provider_name || "";
              liveModel = parsed.model || "";
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === aiId
                    ? { ...m, provider: liveProvider, model: liveModel }
                    : m
                )
              );
            } else if (eventType === "token") {
              const chunkText = parsed as string;
              if (!streamStarted) {
                streamStarted = true;
                setIsTyping(false);
                setMessages((prev) => [
                  ...prev,
                  {
                    id: aiId,
                    sender: "assistant",
                    text: chunkText,
                    timestamp: nowTime(),
                    provider: liveProvider,
                    model: liveModel,
                  },
                ]);
              } else {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === aiId
                      ? {
                          ...m,
                          text: m.text + chunkText,
                          provider: liveProvider || m.provider,
                          model: liveModel || m.model,
                        }
                      : m
                  )
                );
              }
            } else if (eventType === "error") {
              throw new Error(parsed as string);
            }
          } catch (err) {
            console.error("SSE parsing error:", err);
          }
        };

        while (!done) {
          const { value, done: readerDone } = await reader.read();
          done = readerDone;

          if (value) {
            eventBuffer += decoder.decode(value, { stream: true });
            let sepIdx = eventBuffer.indexOf("\n\n");
            while (sepIdx >= 0) {
              const rawEvent = eventBuffer.slice(0, sepIdx);
              eventBuffer = eventBuffer.slice(sepIdx + 2);
              handleSseEvent(rawEvent);
              sepIdx = eventBuffer.indexOf("\n\n");
            }
          }
        }

        setIsTyping(false);
      } catch (error) {
        console.error("Failed to stream AI response:", error);
        setIsTyping(false);
        setMessages((prev) => [
          ...prev,
          {
            id: aiId,
            sender: "assistant",
            text: error instanceof Error ? error.message : "Backend connection failed.",
            timestamp: nowTime(),
          },
        ]);
      }
    },
    [addUserMessage]
  );


  const startVoiceTurn = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: "start_turn" }));
    } else {
      console.warn("Voice WebSocket not connected");
    }
  }, []);

  const stopVoiceTurn = useCallback(() => {
    if (continuousTimerRef.current) {
      clearTimeout(continuousTimerRef.current);
      continuousTimerRef.current = null;
    }
  }, []);

  const voiceMsgIdRef = useRef<string | null>(null);

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
      voiceMsgIdRef.current = null;
      if (mountedRef.current) {
        reconnectTimerRef.current = setTimeout(() => connectRef.current(), RECONNECT_DELAY_MS);
      }
    };

    ws.onerror = (err) => {
      if (!isCurrent()) return;
      console.error("Voice WebSocket error:", err);
    };

    ws.onmessage = (msg) => {
      if (!isCurrent()) return;

      const data = JSON.parse(msg.data);

      if (data.state === "agent_mode_changed" && data.agent_mode) {
        setAgentMode(data.agent_mode);
        return;
      }

      if (data.state === "result") {
        const result = data as TurnResult & { agent_mode?: string; provider?: string; model?: string };
        setVoiceState("idle");
        setIsTyping(false);

        if (result.agent_mode) {
          setAgentMode(result.agent_mode);
        }

        const resProvider = result.provider;
        const resModel = result.model;

        if (voiceMsgIdRef.current && result.reply) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === voiceMsgIdRef.current
                ? {
                    ...m,
                    text: result.reply,
                    provider: resProvider || m.provider,
                    model: resModel || m.model,
                  }
                : m
            )
          );
        } else if (!voiceMsgIdRef.current && result.reply && result.success) {
          addAssistantMessage(result.reply, resProvider, resModel);
        }
        voiceMsgIdRef.current = null;

        if (!result.success) {
          if (result.error && result.error !== "No speech detected") {
            addAssistantMessage(`Voice error: ${result.error}`);
          }
          return;
        }

        // Check if user said goodbye to end conversation
        const isExit = /\b(bye|goodbye|stop conversation|stop talking|exit|see you later)\b/i.test(
          result.transcript || ""
        );
        if (isExit) {
          return;
        }

        // --- Continuous Conversation Loop ---
        if (continuousModeRef.current && mountedRef.current) {
          if (continuousTimerRef.current) clearTimeout(continuousTimerRef.current);
          continuousTimerRef.current = setTimeout(() => {
            if (mountedRef.current && wsRef.current?.readyState === WebSocket.OPEN) {
              console.log("🔄 Continuous voice mode: listening for next user response...");
              wsRef.current.send(JSON.stringify({ action: "start_turn" }));
            }
          }, 500);
        }

        return;
      }

      const event = data as VoiceEvent & { text?: string; audio?: string; sentence_index?: number; provider?: string; model?: string; agent_mode?: string };
      setVoiceState(event.state);

      if (event.state === "thinking" || event.state === "transcribing") {
        voiceMsgIdRef.current = null;
        if (event.transcript) {
          addUserMessage(event.transcript);
        }
        setIsTyping(true);
      } else if (event.state === "speaking") {
        setIsTyping(false);
        const replyText = event.reply || event.text || "";
        const eventProvider = event.provider;
        const eventModel = event.model;

        if (replyText) {
          if (!voiceMsgIdRef.current) {
            const newId = makeId();
            voiceMsgIdRef.current = newId;
            setMessages((prev) => [
              ...prev,
              {
                id: newId,
                sender: "assistant",
                text: replyText,
                timestamp: nowTime(),
                provider: eventProvider,
                model: eventModel,
              },
            ]);
          } else {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === voiceMsgIdRef.current
                  ? {
                      ...m,
                      text: replyText,
                      provider: eventProvider || m.provider,
                      model: eventModel || m.model,
                    }
                  : m
              )
            );
          }
        }
      } else if (event.state === "idle") {
        setIsTyping(false);
        voiceMsgIdRef.current = null;
      }
    };

    wsRef.current = ws;
  }, [addUserMessage, addAssistantMessage]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);


  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      if (continuousTimerRef.current) clearTimeout(continuousTimerRef.current);

      const ws = wsRef.current;
      wsRef.current = null;
      ws?.close();
    };
  }, [connect]);

  // --- Background Wake Word Listener ---
  const { isSupported: wakeWordSupported, isActive: wakeWordActive } = useWakeWord({
    enabled: wakeWordEnabled,
    voiceState,
    connected,
    onWakeWord: startVoiceTurn,
  });

  const toggleWakeWord = useCallback(() => {
    setWakeWordEnabled((prev) => !prev);
  }, []);

  const toggleContinuousMode = useCallback(() => {
    setContinuousMode((prev) => !prev);
  }, []);

  return {
    messages,
    sendMessage,
    isTyping,
    connected,
    voiceState,
    startVoiceTurn,
    stopVoiceTurn,
    wakeWordEnabled,
    wakeWordActive,
    wakeWordSupported,
    toggleWakeWord,
    continuousMode,
    toggleContinuousMode,
    agentMode,
    setAgentMode,
    selectedModel,
    setSelectedModel,
  };
}
