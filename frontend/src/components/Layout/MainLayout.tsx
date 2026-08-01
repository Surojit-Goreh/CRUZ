import "./MainLayout.css";

import Sidebar from "../Sidebar/Sidebar";
import Header from "./Header";
import ChatWindow from "../Chat/ChatWindow";
import ChatInput from "../Chat/ChatInput";

import useChat from "../../hooks/useChat";

export default function MainLayout() {
  const {
    messages,
    sendMessage,
    isTyping,
  } = useChat();

  return (
    <div className="app">
      <Sidebar />

      <main className="main">
        <Header />

        <div className="chat-area">
          <ChatWindow
            messages={messages}
            isTyping={isTyping}
          />
        </div>

        <ChatInput
          onSend={sendMessage}
        />
      </main>
    </div>
  );
}