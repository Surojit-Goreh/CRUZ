import "./ChatMessage.css";

import { Bot, User } from "lucide-react";

export interface Message {
  id: string;
  sender: "user" | "assistant";
  text: string;
  timestamp: string;
}

type Props = {
  message: Message;
};

export default function ChatMessage({ message }: Props) {
  const isUser = message.sender === "user";

  return (
    <div
      className={`message-row ${isUser ? "user-row" : "assistant-row"}`}
    >
      {!isUser && (
        <div className="message-avatar assistant-avatar">
          <Bot size={20} />
        </div>
      )}

      <div className="message-wrapper">
        <div
          className={`message-bubble ${
            isUser ? "user-bubble" : "assistant-bubble"
          }`}
        >
          {message.text}
        </div>

        <span className="message-time">
          {message.timestamp}
        </span>
      </div>

      {isUser && (
        <div className="message-avatar user-avatar">
          <User size={20} />
        </div>
      )}
    </div>
  );
}