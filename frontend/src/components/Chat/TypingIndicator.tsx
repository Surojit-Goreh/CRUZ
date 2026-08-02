import { useEffect, useState } from "react";
import "./TypingIndicator.css";
import { Bot } from "lucide-react";

// CRUZ doesn't expose real reasoning tokens (the local model just streams
// plain text), so instead of faking "thoughts" we cycle a small set of
// in-character phrases while waiting for the first token to arrive.
const PHRASES = [
  "Thinking…",
  "Cooking something up…",
  "Crunching that…",
  "One sec…",
  "Loading brainpower…",
  "Piecing it together…",
];

const PHRASE_INTERVAL_MS = 2200;

export default function TypingIndicator() {
  const [phraseIndex, setPhraseIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setPhraseIndex((prev) => {
        if (PHRASES.length <= 1) return prev;

        let next = Math.floor(Math.random() * PHRASES.length);
        while (next === prev) {
          next = Math.floor(Math.random() * PHRASES.length);
        }
        return next;
      });
    }, PHRASE_INTERVAL_MS);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="typing-row">
      <div className="message-avatar assistant-avatar">
        <Bot size={20} />
      </div>

      <div className="typing-bubble">
        {/* key forces a remount on phrase change so the fade-in animation replays */}
        <span className="typing-shimmer-text" key={phraseIndex}>
          {PHRASES[phraseIndex]}
        </span>

        <span className="typing-dots">
          <span className="dot"></span>
          <span className="dot"></span>
          <span className="dot"></span>
        </span>
      </div>
    </div>
  );
}