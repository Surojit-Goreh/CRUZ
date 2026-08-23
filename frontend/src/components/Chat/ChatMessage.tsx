import { useState, useEffect } from "react";
import {
  Maximize2,
  Download,
  ExternalLink,
  X,
  Loader2,
  Sparkles,
  Image as ImageIcon,
  ChevronDown,
  ChevronUp,
  Bot,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import "./ChatMessage.css";
import type { Message } from "../../types/chat";

type Props = {
  message: Message;
};

interface ParsedSegment {
  type: "text" | "image" | "code";
  content: string;
  alt?: string;
  url?: string;
  language?: string;
}

interface MessageParseOutput {
  thought?: string;
  segments: ParsedSegment[];
}

function extractThoughtAndSanitize(text: string): { thought?: string; cleanText: string } {
  if (!text) return { cleanText: "" };
  let clean = text;

  // 1. Extract closed <think>...</think>
  let thought: string | undefined;
  const thinkMatch = /<think>([\s\S]*?)<\/think>/i.exec(clean);
  if (thinkMatch) {
    thought = thinkMatch[1].trim();
    clean = clean.replace(/<think>[\s\S]*?<\/think>/gi, "");
  } else {
    // Unclosed <think>... during streaming
    const unclosedThink = /<think>([\s\S]*)$/i.exec(clean);
    if (unclosedThink) {
      thought = unclosedThink[1].trim();
      clean = clean.replace(/<think>[\s\S]*$/gi, "");
    }
  }

  // 2. Extract unprompted raw thought narration (e.g. "Okay, so the user wants me to...")
  if (!thought) {
    const rawMonologueMatch = /^(?:Okay,?\s+so\s+the\s+user|First,?\s+I\s+need\s+to\s+make\s+sure|Let's\s+figure\s+out\s+what\s+the\s+user)[\s\S]*?(?=\n\n(?:Here|Sure|I've|I'll|Alright|Playing|Now|\*|#|[A-Z])|$)/i.exec(clean);
    if (rawMonologueMatch && rawMonologueMatch[0].length < clean.length) {
      thought = rawMonologueMatch[0].trim();
      clean = clean.slice(rawMonologueMatch[0].length).trim();
    }
  }

  // Strip raw tool tags
  clean = clean.replace(/<tool_call>[\s\S]*?<\/tool_call>/gi, "");
  clean = clean.replace(/<function=[^>]+>[\s\S]*?<\/function>/gi, "");
  clean = clean.replace(/<\/?(?:tool_call|function|parameter|think)[^>]*>/gi, "");

  return { thought: thought || undefined, cleanText: clean.trim() };
}

function parseMessageContent(text: string): MessageParseOutput {
  const segments: ParsedSegment[] = [];
  const { thought, cleanText } = extractThoughtAndSanitize(text);
  if (!cleanText) return { thought, segments };

  // Regex to match Markdown images with optional newlines/spaces:
  // ![alt text](https://...) or ![alt text](/static/generated_images/...)
  const imgRegex = /!\[([\s\S]*?)\]\s*\(\s*([^\s)]+)\s*\)/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = imgRegex.exec(cleanText)) !== null) {
    if (match.index > lastIndex) {
      const preceding = cleanText.substring(lastIndex, match.index);
      pushTextOrRawImageSegments(segments, preceding);
    }

    const rawAlt = match[1].trim().replace(/\s+/g, " ") || "Generated Image";
    let rawUrl = match[2].trim();

    // Ensure relative /static/ URLs resolve against backend if needed
    if (rawUrl.startsWith("/static/")) {
      rawUrl = `http://127.0.0.1:8000${rawUrl}`;
    }

    segments.push({
      type: "image",
      content: match[0],
      alt: rawAlt,
      url: rawUrl,
    });

    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < cleanText.length) {
    const remaining = cleanText.substring(lastIndex);
    pushTextOrRawImageSegments(segments, remaining);
  }

  return { thought, segments };
}

function pushTextOrRawImageSegments(segments: ParsedSegment[], text: string) {
  if (!text) return;

  // Catch standalone image links (.png, .jpg, .webp, pollinations, static generated images)
  const rawUrlRegex = /(https?:\/\/(?:image\.pollinations\.ai\/prompt\/[^\s)]+|[^\s)]+\.(?:png|jpg|jpeg|webp|gif)(?:\?[^\s)]*)?)|\/static\/generated_images\/[^\s)]+\.(?:png|jpg|jpeg|webp))/gi;
  let last = 0;
  let m: RegExpExecArray | null;

  while ((m = rawUrlRegex.exec(text)) !== null) {
    if (m.index > last) {
      segments.push({
        type: "text",
        content: text.substring(last, m.index),
      });
    }

    let url = m[1].trim();
    if (url.startsWith("/static/")) {
      url = `http://127.0.0.1:8000${url}`;
    }

    segments.push({
      type: "image",
      content: url,
      alt: "Generated Image",
      url,
    });

    last = m.index + m[0].length;
  }

  if (last < text.length) {
    segments.push({
      type: "text",
      content: text.substring(last),
    });
  }
}

export default function ChatMessage({ message }: Props) {
  const isUser = message.sender === "user";
  const [lightboxImage, setLightboxImage] = useState<{ url: string; alt: string } | null>(null);
  const [showPlanDetails, setShowPlanDetails] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setLightboxImage(null);
      }
    };
    if (lightboxImage) {
      document.addEventListener("keydown", handleKeyDown);
    }
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [lightboxImage]);

  if (!message.text || message.text.trim() === "") {
    return null;
  }

  const { thought, segments } = parseMessageContent(message.text);
  const hasPlan = !isUser && Boolean(message.plan && message.plan.specialists && message.plan.specialists.length > 0);

  return (
    <>
      <div className={`message-row ${isUser ? "user-row" : "assistant-row"}`}>
        <div className="message-wrapper">
          <div className={`message-bubble ${isUser ? "user-bubble" : "assistant-bubble"}`}>
            {/* ── 100-Specialist Orchestration Plan Banner ── */}
            {hasPlan && message.plan && (
              <div className="message-plan-card">
                <button
                  type="button"
                  className="message-plan-toggle-btn"
                  onClick={() => setShowPlanDetails(!showPlanDetails)}
                  title="Click to expand/collapse multi-agent orchestration roadmap"
                >
                  <div className="message-plan-toggle-left">
                    <span className="message-plan-icon">
                      <Bot size={14} />
                    </span>
                    <span className="message-plan-label">
                      Orchestrated by {message.plan.specialists.length} Specialists ({message.plan.departments?.join(", ") || "Command"})
                    </span>
                  </div>
                  <div className="message-plan-toggle-right">
                    <span className="message-plan-intent-chip">{message.plan.intent?.toUpperCase()}</span>
                    {showPlanDetails ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </div>
                </button>

                {showPlanDetails && (
                  <div className="message-plan-dropdown">
                    <div className="message-plan-specs-row">
                      <span className="specs-row-label">Specialists:</span>
                      {message.plan.specialists.map((sid) => (
                        <span key={sid} className="plan-spec-badge">
                          <code>{sid}</code>
                        </span>
                      ))}
                    </div>

                    {message.plan.subtasks && message.plan.subtasks.length > 0 && (
                      <div className="message-plan-subtasks-list">
                        {message.plan.subtasks.map((st: any, i: number) => (
                          <div key={st.id || i} className="plan-subtask-item">
                            <span className="subtask-step-idx">{i + 1}</span>
                            <div className="subtask-details">
                              <span className="subtask-title-text">{st.title || st}</span>
                              {st.specialist_id && (
                                <span className="subtask-spec-id">{st.specialist_id}</span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* ── Internal Chain of Thought ── */}
            {!isUser && thought && (
              <details className="message-thought-card">
                <summary className="message-thought-summary">
                  <span>💭 View Internal Reasoning ({thought.length > 100 ? `${thought.slice(0, 80)}...` : "Thought Process"})</span>
                </summary>
                <div className="message-thought-content">
                  {thought}
                </div>
              </details>
            )}

            {segments.map((seg, idx) => {
              if (seg.type === "image" && seg.url) {
                return (
                  <ChatImageCard
                    key={idx}
                    url={seg.url}
                    alt={seg.alt || "Generated Image"}
                    onExpand={() => setLightboxImage({ url: seg.url!, alt: seg.alt || "Generated Image" })}
                  />
                );
              }
              return (
                <div key={idx} className="message-markdown-content">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {seg.content}
                  </ReactMarkdown>
                </div>
              );
            })}
          </div>

          <div className="message-meta-row">
            <span className="message-time">{message.timestamp}</span>

            {!isUser && (
              <div className="message-models-container">
                {message.models_used && message.models_used.length > 1 ? (
                  <div
                    className="message-multi-model-tag"
                    title={message.models_used
                      .map((m) => `${m.provider_name} (${m.model}) [${m.role || "Task"}]`)
                      .join(" ➔ ")}
                  >
                    <span className="provider-dot" />
                    <span className="multi-title">
                      Used: {message.models_used.map((m) => m.provider_name).join(" + ")}
                    </span>
                    <div className="multi-chips-list">
                      {message.models_used.map((m, idx) => (
                        <span key={idx} className="multi-chip">
                          {m.provider_name} · {m.model ? m.model.split("/").pop() : m.role}
                        </span>
                      ))}
                    </div>
                  </div>
                ) : (
                  <span className="message-provider-tag" title={`Model: ${message.model || "Default"}`}>
                    <span className="provider-dot" />
                    Used: {message.provider || "CRUZ AI"}
                    {message.model ? ` · ${message.model}` : ""}
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Full Resolution Lightbox Modal ── */}
      {lightboxImage && (
        <div className="lightbox-backdrop" onClick={() => setLightboxImage(null)}>
          <div className="lightbox-content" onClick={(e) => e.stopPropagation()}>
            <div className="lightbox-header">
              <div className="lightbox-title">
                <ImageIcon size={16} />
                <span>{lightboxImage.alt}</span>
              </div>
              <div className="lightbox-actions">
                <a
                  href={lightboxImage.url}
                  download="cruz_generated_image.jpg"
                  target="_blank"
                  rel="noreferrer"
                  className="lightbox-btn"
                  title="Download Image"
                >
                  <Download size={16} />
                  <span>Download</span>
                </a>
                <a
                  href={lightboxImage.url}
                  target="_blank"
                  rel="noreferrer"
                  className="lightbox-btn"
                  title="Open Original Link"
                >
                  <ExternalLink size={16} />
                  <span>Open Full</span>
                </a>
                <button
                  type="button"
                  className="lightbox-btn close"
                  onClick={() => setLightboxImage(null)}
                  title="Close (Esc)"
                >
                  <X size={18} />
                </button>
              </div>
            </div>
            <div className="lightbox-image-wrapper">
              <img
                src={lightboxImage.url}
                alt={lightboxImage.alt}
                className="lightbox-img"
              />
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function ChatImageCard({
  url,
  alt,
  onExpand,
}: {
  url: string;
  alt: string;
  onExpand: () => void;
}) {
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState(false);
  const [currentSrc, setCurrentSrc] = useState(url);

  const handleImageError = () => {
    if (currentSrc.includes("127.0.0.1:8000/static/")) {
      setCurrentSrc(currentSrc.replace("http://127.0.0.1:8000/static/", "/static/"));
    } else if (currentSrc.startsWith("/static/")) {
      setCurrentSrc(`http://127.0.0.1:8000${currentSrc}`);
    } else {
      setError(true);
    }
  };

  return (
    <div className="chat-image-card">
      <div className="chat-image-container" onClick={onExpand}>
        {!loaded && !error && (
          <div className="chat-image-skeleton">
            <Loader2 size={24} className="spin-animation" />
            <span>Rendering HD Image (Flux)...</span>
          </div>
        )}

        {error ? (
          <div className="chat-image-error">
            <span>Failed to load image</span>
            <a href={url} target="_blank" rel="noreferrer">
              Open link directly
            </a>
          </div>
        ) : (
          <img
            src={currentSrc}
            alt={alt}
            className={`chat-rendered-image ${loaded ? "loaded" : "loading"}`}
            onLoad={() => setLoaded(true)}
            onError={handleImageError}
            loading="lazy"
          />
        )}

        {loaded && (
          <div className="chat-image-overlay">
            <button
              type="button"
              className="chat-image-zoom-btn"
              onClick={(e) => {
                e.stopPropagation();
                onExpand();
              }}
              title="Click to view full screen"
            >
              <Maximize2 size={16} />
              <span>Zoom</span>
            </button>
          </div>
        )}
      </div>

      <div className="chat-image-footer">
        <span className="chat-image-badge">
          <Sparkles size={11} /> HD FLUX
        </span>
        <span className="chat-image-caption" title={alt}>
          {alt}
        </span>
      </div>
    </div>
  );
}