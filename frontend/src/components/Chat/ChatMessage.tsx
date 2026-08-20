import "./ChatMessage.css";

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

  if (!message.text || message.text.trim() === "") {
    return null;
  }

  return (
    <div
      className={`message-row ${isUser ? "user-row" : "assistant-row"}`}
    >
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
    </div>
  );
}