import { useState } from "react";
import "./MainLayout.css";

import Sidebar from "../Sidebar/Sidebar";
import Header from "./Header";
import ChatWindow from "../Chat/ChatWindow";
import ChatInput from "../Chat/ChatInput";
import AiBlob from "../Voice/AiBlob";

import useChat from "../../hooks/useChat";

export default function MainLayout() {
  const {
    messages,
    sendMessage,
    isTyping,
    connected,
    voiceState,
    startVoiceTurn,
  } = useChat();

  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [orbStageOpen, setOrbStageOpen] = useState(true);

  return (
    <div className="app">
      {/* Collapsible Left Sidebar */}
      <Sidebar
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
      />

      <main className="main">
        <Header
          sidebarOpen={sidebarOpen}
          onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
          orbStageOpen={orbStageOpen}
          onToggleOrbStage={() => setOrbStageOpen(!orbStageOpen)}
        />

        {/* ── Content Stage ── */}
        <div className="content-split">
          
          {/* Left Side: Interactive 3D AI Orb Stage (Collapsible) */}
          {orbStageOpen && (
            <section className="orb-column">
              <AiBlob
                voiceState={voiceState}
                connected={connected}
                onStartVoice={startVoiceTurn}
              />
            </section>
          )}

          {/* Right Side: Chat Window + Floating Input */}
          <section className="chat-column">
            <div className="chat-area">
              <ChatWindow
                messages={messages}
                isTyping={isTyping}
                onSend={sendMessage}
              />
            </div>

            <ChatInput
              onSend={sendMessage}
              connected={connected}
              voiceState={voiceState}
              onStartVoiceTurn={startVoiceTurn}
            />
          </section>

        </div>
      </main>
    </div>
  );
}
