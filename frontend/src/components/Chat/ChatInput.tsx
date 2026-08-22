import { useRef, useState, useEffect } from "react";
import {
  Paperclip,
  Mic,
  SendHorizontal,
  Sparkles,
  Hammer,
  Brain,
  Image as ImageIcon,
  PenTool,
  Zap,
  ChevronDown,
  Check,
  Cpu,
  Search,
} from "lucide-react";

import "./ChatInput.css";

type VoiceState = "listening" | "transcribing" | "thinking" | "speaking" | "idle";

interface Props {
  onSend: (text: string, agentMode?: string, model?: string) => void;
  connected: boolean;
  voiceState: VoiceState;
  onStartVoiceTurn: () => void;
  agentMode?: string;
  onAgentModeChange?: (mode: string) => void;
  selectedModel?: string;
  onSelectedModelChange?: (model: string) => void;
}

const VOICE_LABELS: Record<VoiceState, string> = {
  listening: "Listening…",
  transcribing: "Transcribing…",
  thinking: "Thinking…",
  speaking: "Speaking…",
  idle: "Say 'Hey Cruz' or click to talk",
};

interface AgentOption {
  id: string;
  name: string;
  badge: string;
  description: string;
  icon: React.ReactNode;
  color: string;
}

const AGENT_OPTIONS: AgentOption[] = [
  {
    id: "auto",
    name: "Auto Dispatcher",
    badge: "DYNAMIC",
    description: "Classifies task & auto-selects best free model across providers",
    icon: <Sparkles size={14} />,
    color: "#a78bfa",
  },
  {
    id: "build",
    name: "Build Agent",
    badge: "CODING",
    description: "Full-stack code, refactoring, algorithms & debugging",
    icon: <Hammer size={14} />,
    color: "#38bdf8",
  },
  {
    id: "plan",
    name: "Plan Agent",
    badge: "REASONING",
    description: "Deep reasoning, architecture design & multi-step logic",
    icon: <Brain size={14} />,
    color: "#ec4899",
  },
  {
    id: "image",
    name: "Image / Vision",
    badge: "VISION",
    description: "Image analysis, visual inspection & image generation",
    icon: <ImageIcon size={14} />,
    color: "#f59e0b",
  },
  {
    id: "writing",
    name: "Writer Agent",
    badge: "WRITING",
    description: "Long-form drafting, essays, blogs, emails & summaries",
    icon: <PenTool size={14} />,
    color: "#10b981",
  },
  {
    id: "chat",
    name: "Fast Chat",
    badge: "SPEED",
    description: "Ultra-fast low-latency conversational assistant",
    icon: <Zap size={14} />,
    color: "#eab308",
  },
];

export interface ModelItem {
  provider_id: string;
  provider_name: string;
  model_id: string;
  raw_model: string;
  model_name: string;
  badge: string;
  is_connected: boolean;
  is_default?: boolean;
  description?: string;
}

const DEFAULT_PRESET_MODELS: ModelItem[] = [
  {
    provider_id: "auto",
    provider_name: "Dynamic Router",
    model_id: "auto",
    raw_model: "auto",
    model_name: "Auto (Dynamic Router)",
    badge: "DYNAMIC",
    is_connected: true,
    is_default: true,
    description: "Auto-selects best specialized free model for the current task",
  },
  {
    provider_id: "groq",
    provider_name: "Groq",
    model_id: "groq:llama-3.3-70b-versatile",
    raw_model: "llama-3.3-70b-versatile",
    model_name: "Llama 3.3 70B Versatile",
    badge: "FREE",
    is_connected: true,
  },
  {
    provider_id: "groq",
    provider_name: "Groq",
    model_id: "groq:llama-3.1-8b-instant",
    raw_model: "llama-3.1-8b-instant",
    model_name: "Llama 3.1 8B Instant",
    badge: "FAST",
    is_connected: true,
  },
  {
    provider_id: "opencode",
    provider_name: "OpenCode Zen",
    model_id: "opencode:deepseek-v4-flash-free",
    raw_model: "deepseek-v4-flash-free",
    model_name: "DeepSeek V4 Flash Free",
    badge: "FREE",
    is_connected: true,
  },
  {
    provider_id: "opencode",
    provider_name: "OpenCode Zen",
    model_id: "opencode:nemotron-3.5-lightning-free",
    raw_model: "nemotron-3.5-lightning-free",
    model_name: "Nemotron 3.5 Lightning Free",
    badge: "REASONING",
    is_connected: true,
  },
  {
    provider_id: "gemini",
    provider_name: "Google Gemini",
    model_id: "gemini:gemini-2.5-flash",
    raw_model: "gemini-2.5-flash",
    model_name: "Gemini 2.5 Flash",
    badge: "FREE",
    is_connected: true,
  },
  {
    provider_id: "openrouter",
    provider_name: "OpenRouter",
    model_id: "openrouter:openrouter/free",
    raw_model: "openrouter/free",
    model_name: "OpenRouter Free Aggregator",
    badge: "FREE",
    is_connected: true,
  },
  {
    provider_id: "ollama",
    provider_name: "Ollama",
    model_id: "ollama:qwen2.5:3b",
    raw_model: "qwen2.5:3b",
    model_name: "Qwen 2.5 3B (Local)",
    badge: "LOCAL",
    is_connected: true,
  },
];

export default function ChatInput({
  onSend,
  connected,
  voiceState,
  onStartVoiceTurn,
  agentMode: controlledAgentMode,
  onAgentModeChange,
  selectedModel: controlledSelectedModel,
  onSelectedModelChange,
}: Props) {
  const [text, setText] = useState("");
  const [internalAgentMode, setInternalAgentMode] = useState<string>("auto");
  const [internalSelectedModel, setInternalSelectedModel] = useState<string>("auto");
  const [agentDropdownOpen, setAgentDropdownOpen] = useState(false);
  const [modelDropdownOpen, setModelDropdownOpen] = useState(false);
  const [modelSearchQuery, setModelSearchQuery] = useState("");
  const [availableModels, setAvailableModels] = useState<ModelItem[]>(DEFAULT_PRESET_MODELS);

  const activeAgentMode = controlledAgentMode !== undefined ? controlledAgentMode : internalAgentMode;
  const activeSelectedModel = controlledSelectedModel !== undefined ? controlledSelectedModel : internalSelectedModel;

  const setEffectiveAgentMode = (newMode: string) => {
    if (onAgentModeChange) {
      onAgentModeChange(newMode);
    } else {
      setInternalAgentMode(newMode);
    }
  };

  const setEffectiveSelectedModel = (newModel: string) => {
    if (onSelectedModelChange) {
      onSelectedModelChange(newModel);
    } else {
      setInternalSelectedModel(newModel);
    }
  };

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const agentDropdownRef = useRef<HTMLDivElement>(null);
  const modelDropdownRef = useRef<HTMLDivElement>(null);

  const currentAgent = AGENT_OPTIONS.find((a) => a.id === activeAgentMode) || AGENT_OPTIONS[0];

  // Fetch available models from backend
  useEffect(() => {
    const fetchModels = async () => {
      try {
        const res = await fetch("http://127.0.0.1:8000/providers/available-models");
        if (res.ok) {
          const data = await res.json();
          if (data.models && data.models.length > 0) {
            setAvailableModels(data.models);
          }
        }
      } catch {
        // Fall back to preset models
      }
    };
    fetchModels();
  }, []);

  // Find active model details
  const currentModelItem =
    availableModels.find((m) => m.model_id === activeSelectedModel || m.raw_model === activeSelectedModel) ||
    availableModels[0];

  // Close dropdowns on outside click
  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (agentDropdownRef.current && !agentDropdownRef.current.contains(e.target as Node)) {
        setAgentDropdownOpen(false);
      }
      if (modelDropdownRef.current && !modelDropdownRef.current.contains(e.target as Node)) {
        setModelDropdownOpen(false);
      }
    };
    if (agentDropdownOpen || modelDropdownOpen) {
      document.addEventListener("mousedown", handleOutsideClick);
    }
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, [agentDropdownOpen, modelDropdownOpen]);

  const handleSend = () => {
    if (!text.trim()) return;

    onSend(text, activeAgentMode, activeSelectedModel);
    setText("");

    if (textareaRef.current) {
      textareaRef.current.style.height = "26px";
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);

    const area = textareaRef.current;
    if (!area) return;

    area.style.height = "26px";
    area.style.height = area.scrollHeight + "px";
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const isBusy = voiceState !== "idle";

  // Filter models based on search query
  const filteredModels = availableModels.filter((m) => {
    if (!modelSearchQuery.trim()) return true;
    const q = modelSearchQuery.toLowerCase();
    return (
      m.model_name.toLowerCase().includes(q) ||
      m.provider_name.toLowerCase().includes(q) ||
      m.model_id.toLowerCase().includes(q)
    );
  });

  return (
    <div className="chat-input-wrapper">
      {/* ── Top Bar Controls: Agent Mode & Model Selector ── */}
      <div className="chat-input-top-bar">
        {/* ── 1. Agent Mode Selector ── */}
        <div className="agent-selector-wrapper" ref={agentDropdownRef}>
          <button
            type="button"
            className="agent-pill-btn"
            onClick={() => {
              setAgentDropdownOpen((prev) => !prev);
              setModelDropdownOpen(false);
            }}
            title={`Active Agent: ${currentAgent.name}`}
            style={{ "--agent-accent": currentAgent.color } as React.CSSProperties}
          >
            <span className="agent-pill-icon">{currentAgent.icon}</span>
            <span className="agent-pill-name">{currentAgent.name}</span>
            <ChevronDown
              size={12}
              className={`agent-chevron ${agentDropdownOpen ? "open" : ""}`}
            />
          </button>

          {agentDropdownOpen && (
            <div className="agent-dropdown-menu">
              <div className="agent-dropdown-header">
                <span>Select Agent Mode</span>
                <span className="agent-header-hint">Auto-dispatches best free model</span>
              </div>
              <div className="agent-dropdown-list">
                {AGENT_OPTIONS.map((opt) => {
                  const isSelected = opt.id === activeAgentMode;
                  return (
                    <button
                      key={opt.id}
                      type="button"
                      className={`agent-dropdown-item ${isSelected ? "selected" : ""}`}
                      onClick={() => {
                        setEffectiveAgentMode(opt.id);
                        setAgentDropdownOpen(false);
                      }}
                    >
                      <div
                        className="agent-item-icon"
                        style={{ color: opt.color, backgroundColor: `${opt.color}1a` }}
                      >
                        {opt.icon}
                      </div>
                      <div className="agent-item-info">
                        <div className="agent-item-top">
                          <span className="agent-item-name">{opt.name}</span>
                          <span
                            className="agent-item-badge"
                            style={{ color: opt.color, borderColor: `${opt.color}40` }}
                          >
                            {opt.badge}
                          </span>
                        </div>
                        <span className="agent-item-desc">{opt.description}</span>
                      </div>
                      {isSelected && (
                        <div className="agent-item-check" style={{ color: opt.color }}>
                          <Check size={14} />
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* ── 2. Free Model Selector Dropdown ── */}
        <div className="model-selector-wrapper" ref={modelDropdownRef}>
          <button
            type="button"
            className="model-pill-btn"
            onClick={() => {
              setModelDropdownOpen((prev) => !prev);
              setAgentDropdownOpen(false);
            }}
            title={`Selected Model: ${currentModelItem.provider_name} • ${currentModelItem.model_name}`}
          >
            <Cpu size={13} className="model-pill-icon" />
            <span className="model-pill-name">
              {currentModelItem.model_id === "auto"
                ? "Auto (Dynamic)"
                : `${currentModelItem.provider_name.split(" ")[0]}: ${currentModelItem.raw_model.split(":")[0].replace("meta/", "").replace("@cf/", "").substring(0, 16)}`}
            </span>
            <ChevronDown
              size={12}
              className={`agent-chevron ${modelDropdownOpen ? "open" : ""}`}
            />
          </button>

          {modelDropdownOpen && (
            <div className="model-dropdown-menu">
              <div className="model-dropdown-header">
                <div className="model-header-title">
                  <span>Free Models & Providers</span>
                  <span className="model-header-count">{filteredModels.length} models</span>
                </div>
                <div className="model-search-box">
                  <Search size={13} />
                  <input
                    type="text"
                    placeholder="Search free models or providers..."
                    value={modelSearchQuery}
                    onChange={(e) => setModelSearchQuery(e.target.value)}
                    onClick={(e) => e.stopPropagation()}
                    autoFocus
                  />
                </div>
              </div>

              <div className="model-dropdown-list">
                {filteredModels.map((m) => {
                  const isSelected =
                    m.model_id === activeSelectedModel ||
                    (activeSelectedModel === "auto" && m.model_id === "auto");

                  return (
                    <button
                      key={m.model_id}
                      type="button"
                      className={`model-dropdown-item ${isSelected ? "selected" : ""} ${!m.is_connected ? "unavailable" : ""}`}
                      onClick={() => {
                        if (!m.is_connected) return;
                        setEffectiveSelectedModel(m.model_id);
                        setModelDropdownOpen(false);
                      }}
                    >
                      <div className="model-item-left">
                        <span
                          className={`model-conn-dot ${m.is_connected ? "online" : "offline"}`}
                          title={m.is_connected ? "Connected & Ready" : "Unconnected"}
                        />
                        <div className="model-item-details">
                          <div className="model-item-line1">
                            <span className="model-item-title">{m.model_name}</span>
                            <span className={`model-badge ${m.badge.toLowerCase()}`}>{m.badge}</span>
                          </div>
                          <span className="model-item-provider">{m.provider_name}</span>
                        </div>
                      </div>

                      {isSelected && (
                        <div className="model-item-check">
                          <Check size={14} />
                        </div>
                      )}
                    </button>
                  );
                })}

                {filteredModels.length === 0 && (
                  <div className="model-dropdown-empty">
                    <span>No models matching "{modelSearchQuery}"</span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Main Spacious Input Bar ── */}
      <div className="chat-input-container">
        <button className="input-icon" type="button" title="Attach file">
          <Paperclip size={20} />
        </button>

        <textarea
          ref={textareaRef}
          rows={1}
          value={text}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={`Ask Cruz anything (${currentAgent.name})...`}
          className="chat-textarea"
        />

        <button
          className={`input-icon ${isBusy ? "mic-active" : ""}`}
          type="button"
          onClick={onStartVoiceTurn}
          disabled={!connected || isBusy}
          title={
            !connected ? "Voice server not connected" : VOICE_LABELS[voiceState]
          }
        >
          <Mic size={20} />
        </button>

        <button
          className={`send-btn ${text.trim() ? "active" : ""}`}
          onClick={handleSend}
          disabled={!text.trim()}
          type="button"
          title="Send message"
        >
          <SendHorizontal size={18} />
        </button>
      </div>

      {isBusy && <div className="voice-status">{VOICE_LABELS[voiceState]}</div>}
    </div>
  );
}
