import { useState, useRef, useCallback, useEffect } from "react";
import type { Message, ActivityEvent, ActivityState } from "../types/chat";
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
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [activityState, setActivityState] = useState<ActivityState | null>(null);
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
  const abortControllerRef = useRef<AbortController | null>(null);
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

  const stopGeneration = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsTyping(false);
    setIsGenerating(false);
    setActivityState(null);
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
      setIsGenerating(true);

      // Immediately show initial high-level thinking state
      const initialStepId = `step_${Date.now()}`;
      setActivityState({
        status: "processing",
        currentMessage: "Understanding request...",
        phase: "understanding",
        progress: 10,
        steps: [
          {
            id: initialStepId,
            message: "Understanding request...",
            phase: "understanding",
            completed: false,
            timestamp: Date.now(),
          },
        ],
      });

      const aiId = makeId();
      let streamStarted = false;
      const targetMode = explicitAgentMode || clientDetectedMode || agentModeRef.current || "auto";
      const targetModel = explicitModel || selectedModelRef.current || "auto";

      // Abort previous in-flight request if any
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      const controller = new AbortController();
      abortControllerRef.current = controller;

      try {
        const response = await fetch("http://127.0.0.1:8000/chat/stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          signal: controller.signal,
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
        let livePlan: any | undefined;
        let liveModelsUsed: any[] = [];

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

            if (eventType === "plan") {
              livePlan = parsed;
              setMessages((prev) =>
                prev.map((m) => (m.id === aiId ? { ...m, plan: livePlan } : m))
              );
            } else if (eventType === "activity") {
              const act = parsed as ActivityEvent;
              setActivityState((prev) => {
                const prevSteps = prev ? [...prev.steps] : [];
                // Mark previous step as completed if message or phase changed
                const updatedSteps = prevSteps.map((s, idx) =>
                  idx === prevSteps.length - 1 ? { ...s, completed: true } : s
                );
                const nextStepId = `step_${Date.now()}_${Math.random().toString(36).slice(2, 5)}`;
                const lastStep = updatedSteps[updatedSteps.length - 1];
                if (!lastStep || lastStep.message !== act.message) {
                  updatedSteps.push({
                    id: nextStepId,
                    message: act.message,
                    specialist: act.specialist,
                    phase: act.phase,
                    completed: false,
                    timestamp: Date.now(),
                  });
                }
                return {
                  execution_id: act.execution_id,
                  status: "processing",
                  currentMessage: act.message,
                  phase: act.phase,
                  specialist: act.specialist,
                  progress: act.progress,
                  steps: updatedSteps,
                };
              });
            } else if (eventType === "metadata") {
              liveProvider = parsed.provider_name || "";
              liveModel = parsed.model || "";
              if (parsed.models_used && Array.isArray(parsed.models_used)) {
                liveModelsUsed = parsed.models_used;
              }
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === aiId
                    ? {
                        ...m,
                        provider: liveProvider,
                        model: liveModel,
                        plan: livePlan,
                        models_used: liveModelsUsed.length > 0 ? liveModelsUsed : m.models_used,
                      }
                    : m
                )
              );
            } else if (eventType === "token") {
              const chunkText = parsed as string;
              if (!streamStarted) {
                streamStarted = true;
                setIsTyping(false);
                // As soon as the final response tokens begin streaming, clean up the temporary thinking UI
                setActivityState(null);
                setMessages((prev) => [
                  ...prev,
                  {
                    id: aiId,
                    sender: "assistant",
                    text: chunkText,
                    timestamp: nowTime(),
                    provider: liveProvider,
                    model: liveModel,
                    plan: livePlan,
                    models_used: liveModelsUsed,
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
                          plan: livePlan || m.plan,
                          models_used: liveModelsUsed.length > 0 ? liveModelsUsed : m.models_used,
                        }
                      : m
                  )
                );
              }
            } else if (eventType === "done") {
              setIsTyping(false);
              setIsGenerating(false);
              setActivityState(null);
            } else if (eventType === "error") {
              setIsTyping(false);
              setIsGenerating(false);
              setActivityState(null);
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
        setIsGenerating(false);
        setActivityState(null);
      } catch (error: any) {
        if (error?.name === "AbortError") {
          console.log("Chat generation was stopped by user.");
          setIsTyping(false);
          setIsGenerating(false);
          setActivityState(null);
          return;
        }

        console.error("Failed to stream AI response:", error);
        setIsTyping(false);
        setIsGenerating(false);
        setActivityState(null);
        setMessages((prev) => [
          ...prev,
          {
            id: aiId,
            sender: "assistant",
            text: error instanceof Error ? error.message : "Unable to complete request. Please try again.",
            timestamp: nowTime(),
          },
        ]);
      } finally {
        if (abortControllerRef.current === controller) {
          abortControllerRef.current = null;
        }
      }
    },
    [addUserMessage]
  );


  const startVoiceTurn = useCallback((prompt?: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      if (prompt && prompt.trim()) {
        console.log(`🎤 Immediate voice turn with prompt: "${prompt.trim()}"`);
        wsRef.current.send(
          JSON.stringify({
            action: "chat_voice",
            message: prompt.trim(),
            agent_mode: agentModeRef.current || "auto",
          })
        );
      } else {
        console.log("🎤 Starting live microphone listening turn...");
        wsRef.current.send(JSON.stringify({ action: "start_turn" }));
      }
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


  const voicePlanRef = useRef<any | null>(null);
  const voiceModelsUsedRef = useRef<any[]>([]);

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
      setActivityState(null);
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

      if (data.state === "plan" || (data.plan && !data.state)) {
        voicePlanRef.current = data.plan;
        if (voiceMsgIdRef.current) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === voiceMsgIdRef.current ? { ...m, plan: data.plan } : m
            )
          );
        }
        return;
      }

      if (data.state === "activity" || data.event_type) {
        const act = data;
        setActivityState((prev) => {
          const prevSteps = prev ? [...prev.steps] : [];
          const updatedSteps = prevSteps.map((s, idx) =>
            idx === prevSteps.length - 1 ? { ...s, completed: true } : s
          );
          const nextStepId = `step_${Date.now()}_${Math.random().toString(36).slice(2, 5)}`;
          const lastStep = updatedSteps[updatedSteps.length - 1];
          if (!lastStep || lastStep.message !== act.message) {
            updatedSteps.push({
              id: nextStepId,
              message: act.message,
              specialist: act.specialist,
              phase: act.phase,
              completed: false,
              timestamp: Date.now(),
            });
          }
          return {
            execution_id: act.execution_id,
            status: "processing",
            currentMessage: act.message,
            phase: act.phase,
            specialist: act.specialist,
            progress: act.progress,
            steps: updatedSteps,
          };
        });
        return;
      }

      if (data.state === "result") {
        const result = data as TurnResult & {
          agent_mode?: string;
          provider?: string;
          model?: string;
          plan?: any;
          models_used?: any[];
        };
        setVoiceState("idle");
        setIsTyping(false);
        setActivityState(null);

        if (result.agent_mode) {
          setAgentMode(result.agent_mode);
        }

        const resProvider = result.provider;
        const resModel = result.model;
        const resPlan = result.plan || voicePlanRef.current;
        const resModels = result.models_used || voiceModelsUsedRef.current;

        if (voiceMsgIdRef.current && result.reply) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === voiceMsgIdRef.current
                ? {
                    ...m,
                    text: result.reply,
                    provider: resProvider || m.provider,
                    model: resModel || m.model,
                    plan: resPlan || m.plan,
                    models_used: resModels.length > 0 ? resModels : m.models_used,
                  }
                : m
            )
          );
        } else if (!voiceMsgIdRef.current && result.reply && result.success) {
          const newId = makeId();
          setMessages((prev) => [
            ...prev,
            {
              id: newId,
              sender: "assistant",
              text: result.reply,
              timestamp: nowTime(),
              provider: resProvider,
              model: resModel,
              plan: resPlan,
              models_used: resModels,
            },
          ]);
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

      const event = data as VoiceEvent & {
        text?: string;
        audio?: string;
        sentence_index?: number;
        provider?: string;
        model?: string;
        agent_mode?: string;
        plan?: any;
        models_used?: any[];
      };
      setVoiceState(event.state);

      if (event.state === "thinking" || event.state === "transcribing") {
        voiceMsgIdRef.current = null;
        voicePlanRef.current = null;
        voiceModelsUsedRef.current = [];
        if (event.transcript) {
          addUserMessage(event.transcript);
        }
        setIsTyping(true);
      } else if (event.state === "speaking") {
        setIsTyping(false);
        setActivityState(null);
        if (event.plan) voicePlanRef.current = event.plan;
        if (event.models_used && Array.isArray(event.models_used)) {
          voiceModelsUsedRef.current = event.models_used;
        }

        const replyText = event.reply || event.text || "";
        const eventProvider = event.provider;
        const eventModel = event.model;
        const eventPlan = event.plan || voicePlanRef.current;
        const eventModels = (event.models_used && event.models_used.length > 0) ? event.models_used : voiceModelsUsedRef.current;

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
                plan: eventPlan,
                models_used: eventModels,
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
                      plan: eventPlan || m.plan,
                      models_used: eventModels.length > 0 ? eventModels : m.models_used,
                    }
                  : m
              )
            );
          }
        }
      } else if (event.state === "idle") {
        setIsTyping(false);
        setActivityState(null);
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
    isGenerating,
    activityState,
    stopGeneration,
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
