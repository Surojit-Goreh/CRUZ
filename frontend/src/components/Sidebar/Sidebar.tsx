import "./Sidebar.css";

import {
  MessageSquare,
  Star,
  History,
  Settings,
  Cloud,
  Puzzle,
  ChevronDown,
  PanelLeftClose,
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
    <aside className={`sidebar glass ${isOpen ? "open" : "collapsed"}`}>
      {/* Brand Header */}
      <div className="brand">
        <div className="brand-orb" />
        <div className="brand-text">
          <h1>CRUZ</h1>
          <p>Your Personal AI</p>
        </div>
        <button
          className="sidebar-toggle-btn"
          onClick={onToggle}
          title="Collapse Sidebar"
          type="button"
        >
          <PanelLeftClose size={16} />
        </button>
      </div>

      {/* New Chat Button */}
      <div
        className="new-chat"
        onClick={() => {
          if (onNewChat) onNewChat();
          handleTabClick("chats");
        }}
      >
        + New chat
      </div>

      {/* Navigation */}
      <nav className="nav">
        <div
          className={`nav-item ${activeTab === "chats" ? "active" : ""}`}
          onClick={() => handleTabClick("chats")}
        >
          <span className="nav-dot" />
          <MessageSquare size={16} className="nav-icon" />
          <span>Chats</span>
        </div>

        <div
          className={`nav-item ${activeTab === "starred" ? "active" : ""}`}
          onClick={() => handleTabClick("starred")}
        >
          <span className="nav-dot" />
          <Star size={16} className="nav-icon" />
          <span>Starred</span>
        </div>

        <div
          className={`nav-item ${activeTab === "history" ? "active" : ""}`}
          onClick={() => handleTabClick("history")}
        >
          <span className="nav-dot" />
          <History size={16} className="nav-icon" />
          <span>History</span>
        </div>

        <div
          className={`nav-item ${activeTab === "skills" ? "active" : ""}`}
          onClick={() => handleTabClick("skills")}
        >
          <span className="nav-dot" />
          <Puzzle size={16} className="nav-icon" />
          <span>Skills</span>
        </div>

        <div
          className={`nav-item ${activeTab === "settings" ? "active" : ""}`}
          onClick={() => handleTabClick("settings")}
        >
          <span className="nav-dot" />
          <Settings size={16} className="nav-icon" />
          <span>Settings</span>
        </div>

        <div
          className={`nav-item ${activeTab === "cloud-brain" ? "active" : ""}`}
          onClick={() => handleTabClick("cloud-brain")}
        >
          <span className="nav-dot" />
          <Cloud size={16} className="nav-icon" />
          <span>Cloud brain</span>
        </div>
      </nav>

      {/* ── Bottom Group (Mic Card + User Profile) ── */}
      <div className="sidebar-bottom-group">
        {/* Voice Assistant Mic Card */}
        <div
          className="mic-card"
          onClick={() => {
            if (!connected) return;
            if (voiceState === "idle" && onStartVoice) {
              onStartVoice();
            } else if (onStopVoice) {
              onStopVoice();
            }
          }}
          title={
            !connected
              ? "Voice server offline"
              : voiceState === "speaking"
              ? "CRUZ speaking (click to interrupt)"
              : voiceState === "listening"
              ? "Listening (click to cancel)"
              : "Say 'Hey Cruz' or click to talk"
          }
        >
          <span
            className={`mic-pulse ${voiceState !== "idle" ? voiceState : wakeWordActive ? "wake-active" : ""}`}
          />
          <div className="mic-card-text">
            <p className="t1">
              {voiceState === "speaking"
                ? "CRUZ Speaking…"
                : voiceState === "listening"
                ? "Listening…"
                : voiceState === "thinking"
                ? "Thinking…"
                : "Say \"Hey Cruz\""}
            </p>
            <p className="t2">
              {voiceState === "idle"
                ? wakeWordActive
                  ? "Listening for wake word"
                  : "Click to talk"
                : "Live conversation"}
            </p>
          </div>
        </div>

        {/* User Profile */}
        <div className="profile">
          <div className="profile-avatar">SG</div>
          <div className="profile-text">
            <p className="t1">Surojit Goreh</p>
            <p className="t2">Free plan</p>
          </div>
          <span className="chev">
            <ChevronDown size={14} />
          </span>
        </div>
      </div>
    </aside>
  );
}