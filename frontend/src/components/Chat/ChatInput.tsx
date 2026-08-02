import { useRef, useState } from "react";
import { Paperclip, Mic, SendHorizontal } from "lucide-react";

import "./ChatInput.css";

type VoiceState = "listening" | "transcribing" | "thinking" | "speaking" | "idle";

interface Props {
  onSend: (text: string) => void;
  connected: boolean;
  voiceState: VoiceState;
  onStartVoiceTurn: () => void;
}

const VOICE_LABELS: Record<VoiceState, string> = {
  listening: "Listening…",
  transcribing: "Transcribing…",
  thinking: "Thinking…",
  speaking: "Speaking…",
  idle: "Start voice conversation",
};

export default function ChatInput({
  onSend,
  connected,
  voiceState,
  onStartVoiceTurn,
}: Props) {
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

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);

    const area = textareaRef.current;
    if (!area) return;

    area.style.height = "26px";
    area.style.height = area.scrollHeight + "px";
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const isBusy = voiceState !== "idle";

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

        <button
          className={`input-icon ${isBusy ? "mic-active" : ""}`}
          type="button"
          onClick={onStartVoiceTurn}
          disabled={!connected || isBusy}
          title={
            !connected ? "Voice server not connected" : VOICE_LABELS[voiceState]
          }
        >
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

      {isBusy && <div className="voice-status">{VOICE_LABELS[voiceState]}</div>}
    </div>
  );
}
