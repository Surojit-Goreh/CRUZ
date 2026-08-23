import { lazy, Suspense, useState } from "react";
import { PanelLeftOpen } from "lucide-react";
import "./MainLayout.css";

import Sidebar from "../Sidebar/Sidebar";
import ChatWindow from "../Chat/ChatWindow";
import ChatInput from "../Chat/ChatInput";
import CloudBrain from "../Settings/CloudBrain";
import SkillsHub from "../Settings/SkillsHub";

import useChat from "../../hooks/useChat";

// Three.js and the VRM runtime are large; keep first chat paint lightweight.
const VrmAvatar = lazy(() => import("../Voice/VrmAvatar"));

export default function MainLayout() {
  const {
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
    wakeWordActive,
    agentMode,
    setAgentMode,
    selectedModel,
    setSelectedModel,
  } = useChat();

  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeTab, setActiveTab] = useState<string>("chats");
  const orbStageOpen = true;

  return (
    <div className={`app ${sidebarOpen ? "with-sidebar" : "sidebar-collapsed"}`}>
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
        {/* Floating Sidebar Expand Button (visible when sidebar is collapsed) */}
        {!sidebarOpen && (
          <button
            className="sidebar-expand-floating-btn glass"
            onClick={() => setSidebarOpen(true)}
            title="Expand Sidebar"
            type="button"
            aria-label="Expand Sidebar"
          >
            <PanelLeftOpen size={18} />
          </button>
        )}

        {/* ── Content Stage ── */}
        {activeTab === "cloud-brain" ? (
          <div className="tab-pane glass">
            <CloudBrain />
          </div>
        ) : activeTab === "skills" ? (
          <div className="tab-pane glass">
            <SkillsHub activeAgentMode={agentMode} />
          </div>
        ) : (
          <>
            <div className="content-row">
              {/* Left Side: 3D VRM Anime Avatar Stage in Liquid Glass */}
              {orbStageOpen && (
                <div className="stage-wrap glass">
                  <Suspense
                    fallback={
                      <div className="vrm-loading">
                        <div className="vrm-loading-orb" />
                        <p>Loading avatar…</p>
                      </div>
                    }
                  >
                    <VrmAvatar
                      voiceState={voiceState}
                      connected={connected}
                      onStartVoice={startVoiceTurn}
                      onStopVoice={stopVoiceTurn}
                    />
                  </Suspense>
                </div>
              )}

              {/* Right Side: Chat Window in Liquid Glass */}
              <div className="chat-panel glass">
                <ChatWindow
                  messages={messages}
                  isTyping={isTyping}
                  activityState={activityState}
                  onSend={sendMessage}
                  onStop={stopGeneration}
                />
              </div>
            </div>

            {/* Bottom Liquid Glass Control Bar */}
            <ChatInput
              onSend={sendMessage}
              connected={connected}
              voiceState={voiceState}
              onStartVoiceTurn={startVoiceTurn}
              agentMode={agentMode}
              onAgentModeChange={setAgentMode}
              selectedModel={selectedModel}
              onSelectedModelChange={setSelectedModel}
              isGenerating={isGenerating}
              onStopGeneration={stopGeneration}
            />
          </>
        )}
      </main>
    </div>
  );
}
