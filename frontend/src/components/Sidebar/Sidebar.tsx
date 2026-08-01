import "./Sidebar.css";

import {
  MessageSquare,
  Star,
  History,
  Settings,
  Plus,
  ChevronDown,
} from "lucide-react";

export default function Sidebar() {
  return (
    <aside className="sidebar">

      {/* Logo */}

      <div className="sidebar-logo">

        <div className="logo-box">
          🤖
        </div>

        <div>
          <h2>CRUZ</h2>
          <p>Your Personal AI Assistant</p>
        </div>

      </div>

      {/* New Chat */}

      <button className="new-chat">

        <Plus size={18} />

        <span>New Chat</span>

      </button>

      {/* Menu */}

      <nav className="sidebar-menu">

        <button className="menu-item active">

          <MessageSquare size={20} />

          Chats

        </button>

        <button className="menu-item">

          <Star size={20} />

          Starred

        </button>

        <button className="menu-item">

          <History size={20} />

          History

        </button>

        <button className="menu-item">

          <Settings size={20} />

          Settings

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

        <ChevronDown size={18} />

      </div>

    </aside>
  );
}