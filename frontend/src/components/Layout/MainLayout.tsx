import { lazy, Suspense, useState } from "react";
import "./MainLayout.css";

import Sidebar from "../Sidebar/Sidebar";
import Header from "./Header";
import ChatWindow from "../Chat/ChatWindow";
import ChatInput from "../Chat/ChatInput";
import CloudBrain from "../Settings/CloudBrain";

import useChat from "../../hooks/useChat";

// Three.js and the VRM runtime are large; keep first chat paint lightweight.
const VrmAvatar = lazy(() => import("../Voice/VrmAvatar"));

export default function MainLayout() {
  const {
    messages,
    sendMessage,
    isTyping,
    connected,
    voiceState,
    startVoiceTurn,
    stopVoiceTurn,
    wakeWordActive,
    agentMode,
    setAgentMode,
    selectedModel,
    setSelectedModel,
  } = useChat();

  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [orbStageOpen, setOrbStageOpen] = useState(true);
  const [activeTab, setActiveTab] = useState<string>("chats");

  return (
    <div className="app">
      {/* Collapsible Left Sidebar */}
      <Sidebar
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
        activeTab={activeTab}
        onSelectTab={(tab) => setActiveTab(tab)}
        onNewChat={() => setActiveTab("chats")}
        voiceState={voiceState}
        connected={connected}
        onStartVoice={startVoiceTurn}
        onStopVoice={stopVoiceTurn}
        wakeWordActive={wakeWordActive}
      />

      <main className="main">
        <Header
          sidebarOpen={sidebarOpen}
          onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
          orbStageOpen={orbStageOpen}
          onToggleOrbStage={() => setOrbStageOpen(!orbStageOpen)}
        />

        {/* ── Content Stage ── */}
        {activeTab === "cloud-brain" ? (
          <CloudBrain />
        ) : (
          <div className="content-split">
            {/* Left Side: 3D VRM Anime Avatar Stage (Collapsible) */}
            {orbStageOpen && (
              <section className="orb-column">
                <Suspense fallback={<div className="vrm-loading">Loading avatar…</div>}>
                  <VrmAvatar
                    voiceState={voiceState}
                    connected={connected}
                    onStartVoice={startVoiceTurn}
                    onStopVoice={stopVoiceTurn}
                  />
                </Suspense>
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
                agentMode={agentMode}
                onAgentModeChange={setAgentMode}
                selectedModel={selectedModel}
                onSelectedModelChange={setSelectedModel}
              />
            </section>
          </div>
        )}
      </main>
    </div>
  );
}
