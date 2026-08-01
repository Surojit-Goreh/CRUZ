import { useRef, useState } from "react";
import { Paperclip, Mic, SendHorizontal } from "lucide-react";

import "./ChatInput.css";

interface Props {
  onSend: (text: string) => void;
}

export default function ChatInput({ onSend }: Props) {
  const [text, setText] = useState("");

  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    if (!text.trim()) return;

    onSend(text);

    setText("");

    if (textareaRef.current) {
      textareaRef.current.style.height = "26px";
    }
  };

  const handleChange = (
    e: React.ChangeEvent<HTMLTextAreaElement>
  ) => {
    setText(e.target.value);

    const area = textareaRef.current;

    if (!area) return;

    area.style.height = "26px";
    area.style.height = area.scrollHeight + "px";
  };

  const handleKeyDown = (
    e: React.KeyboardEvent<HTMLTextAreaElement>
  ) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-input-wrapper">
      <div className="chat-input-container">
        <button className="input-icon" type="button">
          <Paperclip size={22} />
        </button>

        <textarea
          ref={textareaRef}
          rows={1}
          value={text}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder="Type a message..."
          className="chat-textarea"
        />

        <button className="input-icon" type="button">
          <Mic size={22} />
        </button>

        <button
          className={`send-btn ${text.trim() ? "active" : ""}`}
          onClick={handleSend}
          disabled={!text.trim()}
          type="button"
        >
          <SendHorizontal size={20} />
        </button>
      </div>
    </div>
  );
}