import { useEffect, useRef } from "react";
import "./ChatWindow.css";

import ChatMessage from "./ChatMessage";
import TypingIndicator from "./TypingIndicator";

import type { Message } from "../../types/chat";

interface Props {
  messages: Message[];
  isTyping: boolean;
}

export default function ChatWindow({ messages, isTyping }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  return (
    <div className="chat-window">
      {messages.map((message) => (
        <ChatMessage key={message.id} message={message} />
      ))}

      <div ref={bottomRef} />
    </div>
  );
}