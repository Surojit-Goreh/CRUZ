import "./Sidebar.css";

import {
  MessageSquare,
  Star,
  History,
  Settings,
  Plus,
  ChevronDown,
  PanelLeftClose,
} from "lucide-react";

interface Props {
  isOpen: boolean;
  onToggle: () => void;
}

export default function Sidebar({ isOpen, onToggle }: Props) {
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
      <button className="new-chat">
        <Plus size={18} />
        <span>New Chat</span>
      </button>

      {/* Menu */}
      <nav className="sidebar-menu">

        <button className="menu-item active">
          <MessageSquare size={18} />
          <span>Chats</span>
        </button>

        <button className="menu-item">
          <Star size={18} />
          <span>Starred</span>
        </button>

        <button className="menu-item">
          <History size={18} />
          <span>History</span>
        </button>

        <button className="menu-item">
          <Settings size={18} />
          <span>Settings</span>
        </button>

      </nav>

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