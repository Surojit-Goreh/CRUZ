import { useEffect, useRef } from "react";
import "./ChatWindow.css";

import ChatMessage from "./ChatMessage";
import WelcomeScreen from "./WelcomeScreen";
import TypingIndicator from "./TypingIndicator";
import ActivityIndicator from "./ActivityIndicator";

import type { Message, ActivityState } from "../../types/chat";

interface Props {
  messages: Message[];
  isTyping: boolean;
  activityState?: ActivityState | null;
  onSend?: (text: string) => void;
  onStop?: () => void;
}

export default function ChatWindow({
  messages,
  isTyping,
  activityState,
  onSend,
  onStop,
}: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping, activityState]);

  const hasActivity = Boolean(activityState && activityState.status === "processing");
  const isBusy = isTyping || hasActivity;

  if (messages.length === 0 && !isBusy) {
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

        {/* Temporary activity/thinking UI while backend processes request */}
        {hasActivity && activityState ? (
          <ActivityIndicator activityState={activityState} onStop={onStop} />
        ) : (
          isTyping && <TypingIndicator />
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}