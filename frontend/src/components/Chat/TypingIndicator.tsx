import "./TypingIndicator.css";
import { Bot } from "lucide-react";

export default function TypingIndicator() {
  return (
    <div className="typing-row">
      <div className="message-avatar assistant-avatar">
        <Bot size={20} />
      </div>

      <div className="typing-bubble">
        <span className="dot"></span>
        <span className="dot"></span>
        <span className="dot"></span>
      </div>
    </div>
  );
}