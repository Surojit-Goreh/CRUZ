import "./WelcomeScreen.css";
import { Code2, Search, Mic, FileText } from "lucide-react";

interface Props {
  onSelectPrompt?: (text: string) => void;
}

export default function WelcomeScreen({ onSelectPrompt }: Props) {
  const suggestions = [
    {
      icon: <Code2 size={20} />,
      title: "Write Code",
      description: "Write code to solve problems, generate functions, or debug issues.",
      prompt: "Can you help me write a Python script?",
    },
    {
      icon: <Search size={20} />,
      title: "Research a Topic",
      description: "Explore complex concepts, technical docs, or historical topics.",
      prompt: "Explain how WebSockets work in real-time applications.",
    },
    {
      icon: <Mic size={20} />,
      title: "Voice Chat",
      description: "Speak directly with CRUZ for instant hands-free voice responses.",
      prompt: "Hello CRUZ! Tell me a quick fun fact.",
    },
    {
      icon: <FileText size={20} />,
      title: "Summarize & Analyze",
      description: "Paste articles or notes for instant summaries and key takeaways.",
      prompt: "How can I structure a React project efficiently?",
    },
  ];

  return (
    <div className="welcome-container">
      <div className="welcome-hero">
        <div className="welcome-orb">
          <div className="welcome-orb-inner" />
        </div>

        <h1 className="welcome-title">How can I help you today?</h1>
        <p className="welcome-subtitle">
          CRUZ is your personal AI assistant for coding, research, voice chat, and more.
        </p>
      </div>

      <div className="welcome-grid">
        {suggestions.map((item, idx) => (
          <button
            key={idx}
            className="suggestion-card"
            onClick={() => onSelectPrompt?.(item.prompt)}
            type="button"
          >
            <div className="card-icon">{item.icon}</div>
            <div className="card-content">
              <h3>{item.title}</h3>
              <p>{item.description}</p>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
