import { useState, useEffect } from "react";
import {
  Maximize2,
  Download,
  ExternalLink,
  X,
  Loader2,
  Sparkles,
  Image as ImageIcon,
} from "lucide-react";
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

function parseMessageContent(text: string): ParsedSegment[] {
  const segments: ParsedSegment[] = [];
  if (!text) return segments;

  // Regex to match Markdown images with optional newlines/spaces:
  // ![alt text](https://...) or ![alt text](/static/generated_images/...)
  const imgRegex = /!\[([\s\S]*?)\]\s*\(\s*([^\s)]+)\s*\)/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = imgRegex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      const preceding = text.substring(lastIndex, match.index);
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

  if (lastIndex < text.length) {
    const remaining = text.substring(lastIndex);
    pushTextOrRawImageSegments(segments, remaining);
  }

  return segments;
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

  const segments = parseMessageContent(message.text);

  return (
    <>
      <div className={`message-row ${isUser ? "user-row" : "assistant-row"}`}>
        <div className="message-wrapper">
          <div className={`message-bubble ${isUser ? "user-bubble" : "assistant-bubble"}`}>
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
                <span key={idx} className="message-text-segment">
                  {seg.content}
                </span>
              );
            })}
          </div>

          <div className="message-meta-row">
            <span className="message-time">{message.timestamp}</span>

            {!isUser && (
              <span className="message-provider-tag" title={`Model: ${message.model || "Default"}`}>
                <span className="provider-dot" />
                Used: {message.provider || "CRUZ AI"}
                {message.model ? ` · ${message.model}` : ""}
              </span>
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