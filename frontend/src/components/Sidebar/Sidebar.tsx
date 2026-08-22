import "./Sidebar.css";

import {
  MessageSquare,
  Star,
  History,
  Settings,
  Cloud,
  Plus,
  ChevronDown,
  PanelLeftClose,
  Mic,
} from "lucide-react";

interface Props {
  isOpen: boolean;
  onToggle: () => void;
  activeTab?: string;
  onSelectTab?: (tab: string) => void;
  onNewChat?: () => void;
  voiceState?: "listening" | "transcribing" | "thinking" | "speaking" | "idle";
  connected?: boolean;
  onStartVoice?: () => void;
  onStopVoice?: () => void;
  wakeWordActive?: boolean;
}

export default function Sidebar({
  isOpen,
  onToggle,
  activeTab = "chats",
  onSelectTab,
  onNewChat,
  voiceState = "idle",
  connected = true,
  onStartVoice,
  onStopVoice,
  wakeWordActive = false,
}: Props) {
  const handleTabClick = (tab: string) => {
    if (onSelectTab) {
      onSelectTab(tab);
    }
  };

  return (
    <aside className={`sidebar ${isOpen ? "open" : "collapsed"}`}>

      {/* Logo & Toggle Header */}
      <div className="sidebar-logo">
        <div className="logo-orb">
          <div className="orb-inner" />
        </div>

        <div className="logo-text">
          <h2>CRUZ</h2>
          <p>Your Personal AI</p>
        </div>

        <button
          className="sidebar-toggle-btn"
          onClick={onToggle}
          title="Collapse Sidebar"
          type="button"
        >
          <PanelLeftClose size={18} />
        </button>
      </div>

      {/* New Chat */}
      <button
        className="new-chat"
        onClick={() => {
          if (onNewChat) onNewChat();
          handleTabClick("chats");
        }}
        type="button"
      >
        <Plus size={18} />
        <span>New Chat</span>
      </button>

      {/* Menu */}
      <nav className="sidebar-menu">

        <button
          className={`menu-item ${activeTab === "chats" ? "active" : ""}`}
          onClick={() => handleTabClick("chats")}
          type="button"
        >
          <MessageSquare size={18} />
          <span>Chats</span>
        </button>

        <button
          className={`menu-item ${activeTab === "starred" ? "active" : ""}`}
          onClick={() => handleTabClick("starred")}
          type="button"
        >
          <Star size={18} />
          <span>Starred</span>
        </button>

        <button
          className={`menu-item ${activeTab === "history" ? "active" : ""}`}
          onClick={() => handleTabClick("history")}
          type="button"
        >
          <History size={18} />
          <span>History</span>
        </button>

        <button
          className={`menu-item ${activeTab === "settings" ? "active" : ""}`}
          onClick={() => handleTabClick("settings")}
          type="button"
        >
          <Settings size={18} />
          <span>Settings</span>
        </button>

        <button
          className={`menu-item ${activeTab === "cloud-brain" ? "active" : ""}`}
          onClick={() => handleTabClick("cloud-brain")}
          type="button"
        >
          <Cloud size={18} />
          <span>Cloud Brain</span>
        </button>

      </nav>


      {/* ── Voice Assistant Status & Trigger (Bottom-Left) ── */}
      <div className="sidebar-voice-card">
        <button
          type="button"
          className={`sidebar-voice-btn ${voiceState || "idle"}`}
          onClick={() => {
            if (!connected) return;
            if (voiceState === "idle" && onStartVoice) {
              onStartVoice();
            } else if (onStopVoice) {
              onStopVoice();
            }
          }}
          disabled={!connected}
          title={
            !connected
              ? "Voice server offline"
              : voiceState === "speaking"
              ? "CRUZ is speaking (click to interrupt)"
              : voiceState === "listening"
              ? "Listening (click to cancel)"
              : wakeWordActive
              ? "Say 'Hey Cruz' or click to talk"
              : "Click to talk"
          }
        >
          <div className="voice-btn-indicator">
            {voiceState === "speaking" ? (
              <div className="sidebar-voice-waves">
                <span className="wave-bar bar-1" />
                <span className="wave-bar bar-2" />
                <span className="wave-bar bar-3" />
              </div>
            ) : (
              <span className={`sidebar-voice-dot ${voiceState || "idle"} ${wakeWordActive ? "wake-active" : ""}`} />
            )}
          </div>

          <div className="sidebar-voice-info">
            <span className="voice-status-title">
              {voiceState === "speaking"
                ? "CRUZ Speaking…"
                : voiceState === "listening"
                ? "Listening…"
                : voiceState === "thinking"
                ? "Thinking…"
                : wakeWordActive
                ? "Say 'Hey Cruz'"
                : "Voice Assistant"}
            </span>
            <span className="voice-status-sub">
              {voiceState === "idle" ? (wakeWordActive ? "Listening for wake word" : "Click to talk") : "Live conversation"}
            </span>
          </div>

          <div className="sidebar-voice-mic-icon">
            <Mic size={15} />
          </div>
        </button>
      </div>

      {/* User */}
      <div className="sidebar-user">

        <div className="avatar">
          SG
        </div>

        <div className="user-info">
          <strong>Surojit Goreh</strong>
          <span>Free Plan</span>
        </div>

        <ChevronDown size={16} />

      </div>

    </aside>
  );
}