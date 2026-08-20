import { useEffect, useRef } from "react";
import "./ChatWindow.css";

import ChatMessage from "./ChatMessage";
import WelcomeScreen from "./WelcomeScreen";
import TypingIndicator from "./TypingIndicator";

import type { Message } from "../../types/chat";

interface Props {
  messages: Message[];
  isTyping: boolean;
  onSend?: (text: string) => void;
}

export default function ChatWindow({ messages, isTyping, onSend }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  if (messages.length === 0 && !isTyping) {
    return (
      <div className="chat-window empty">
        <WelcomeScreen onSelectPrompt={onSend} />
      </div>
    );
  }

  const visibleMessages = messages.filter((m) => m.text.trim() !== "");

  return (
    <div className="chat-window">
      <div className="chat-messages-container">
        {visibleMessages.map((message) => (
          <ChatMessage key={message.id} message={message} />
        ))}
        {isTyping && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}