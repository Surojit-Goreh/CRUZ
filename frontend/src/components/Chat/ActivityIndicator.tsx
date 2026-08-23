import { useState } from "react";
import {
  Bot,
  Square,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Layers,
  Search,
  FolderTree,
  Globe,
  Terminal,
  Cpu,
} from "lucide-react";
import "./ActivityIndicator.css";
import type { ActivityState } from "../../types/chat";

interface Props {
  activityState: ActivityState;
  onStop?: () => void;
}

function getSpecialistIcon(specialist?: string) {
  if (!specialist) return <Sparkles size={12} />;
  const lower = specialist.toLowerCase();
  if (lower.includes("search") || lower.includes("research")) return <Search size={12} />;
  if (lower.includes("file") || lower.includes("workspace")) return <FolderTree size={12} />;
  if (lower.includes("browser") || lower.includes("web")) return <Globe size={12} />;
  if (lower.includes("desktop") || lower.includes("system")) return <Terminal size={12} />;
  if (lower.includes("engineer") || lower.includes("developer") || lower.includes("coding")) return <Cpu size={12} />;
  return <Layers size={12} />;
}

export default function ActivityIndicator({ activityState, onStop }: Props) {
  const [expanded, setExpanded] = useState(false);
  const { currentMessage, specialist, steps, progress } = activityState;

  // Show previous completed steps if more than 1 step has occurred
  const completedSteps = steps.filter((s) => s.completed);
  const hasHistory = completedSteps.length > 0;

  return (
    <div className="activity-row" role="status" aria-live="polite">
      <div className="message-avatar assistant-avatar pulse-avatar">
        <Bot size={20} />
      </div>

      <div className="activity-container">
        <div className="activity-card">
          {/* Main Activity Header */}
          <div className="activity-header">
            <div className="activity-status-group">
              <span className="activity-spinner" aria-hidden="true">
                <span className="spinner-glyph">◌</span>
              </span>

              <div className="activity-text-wrapper">
                <span className="activity-shimmer-text" key={currentMessage}>
                  {currentMessage || "Processing request..."}
                </span>

                {specialist && (
                  <span className="activity-specialist-pill" title={`Active Specialist: ${specialist}`}>
                    {getSpecialistIcon(specialist)}
                    <span className="specialist-name">{specialist}</span>
                  </span>
                )}
              </div>
            </div>

            <div className="activity-actions">
              {hasHistory && (
                <button
                  type="button"
                  className="activity-expand-btn"
                  onClick={() => setExpanded(!expanded)}
                  title={expanded ? "Hide execution steps" : "View execution stages"}
                  aria-expanded={expanded}
                >
                  <span className="step-count-badge">{completedSteps.length + 1} steps</span>
                  {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                </button>
              )}

              {onStop && (
                <button
                  type="button"
                  className="activity-stop-btn"
                  onClick={onStop}
                  title="Stop generation (Esc)"
                  aria-label="Stop generation"
                >
                  <Square size={11} fill="currentColor" />
                  <span>Stop</span>
                </button>
              )}
            </div>
          </div>

          {/* Subtle Progress Bar */}
          {typeof progress === "number" && progress > 0 && progress <= 100 && (
            <div className="activity-progress-track">
              <div
                className="activity-progress-fill"
                style={{ width: `${Math.min(100, Math.max(5, progress))}%` }}
              />
            </div>
          )}

          {/* Collapsible Multi-Step Stage History */}
          {expanded && hasHistory && (
            <div className="activity-steps-list">
              {completedSteps.map((step) => (
                <div key={step.id} className="activity-step-item completed">
                  <CheckCircle2 size={13} className="step-check-icon" />
                  <span className="step-msg">{step.message}</span>
                  {step.specialist && (
                    <span className="step-specialist-tag">{step.specialist}</span>
                  )}
                </div>
              ))}

              <div className="activity-step-item current">
                <span className="step-dot-pulse" />
                <span className="step-msg current">{currentMessage}</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
