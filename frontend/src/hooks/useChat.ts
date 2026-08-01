import { useState } from "react";
import type { Message } from "../types/chat";

export default function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState<boolean>(false);

  const sendMessage = async (text: string) => {
    if (!text.trim()) return;

    const userTime = new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    });

    const userMsg: Message = {
      id: Date.now().toString(),
      sender: "user",
      text: text,
      timestamp: userTime,
    };

    // 1. Add the user message immediately
    setMessages((prev) => [...prev, userMsg]);
    setIsTyping(true);

    // 2. Create a placeholder message for CRUZ's incoming streaming reply
    const aiId = (Date.now() + 1).toString();
    const aiTime = new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    });

    const initialAiMsg: Message = {
      id: aiId,
      sender: "assistant",
      text: "",
      timestamp: aiTime,
    };

    setMessages((prev) => [...prev, initialAiMsg]);

    try {
      const response = await fetch("http://127.0.0.1:8000/chat/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: text }),
      });

      if (!response.ok || !response.body) {
        throw new Error("Network response was not ok or readable stream missing");
      }

      // Turn off typing dots as soon as the stream begins
      setIsTyping(false);

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let done = false;

      // 3. Read chunks continuously from FastAPI -> Ollama
      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;

        if (value) {
          const chunkText = decoder.decode(value, { stream: true });

          // Append each incoming token dynamically to CRUZ's message bubble
          setMessages((prevMessages) =>
            prevMessages.map((msg) =>
              msg.id === aiId ? { ...msg, text: msg.text + chunkText } : msg
            )
          );
        }
      }

      // Flush any buffered multi-byte characters left in the decoder
      const finalChunk = decoder.decode();
      if (finalChunk) {
        setMessages((prevMessages) =>
          prevMessages.map((msg) =>
            msg.id === aiId ? { ...msg, text: msg.text + finalChunk } : msg
          )
        );
      }
    } catch (error) {
      console.error("Failed to stream AI response:", error);
      setIsTyping(false);

      setMessages((prevMessages) =>
        prevMessages.map((msg) =>
          msg.id === aiId
            ? { ...msg, text: "Backend connection failed." }
            : msg
        )
      );
    }
  };

  return {
    messages,
    sendMessage,
    isTyping,
  };
}