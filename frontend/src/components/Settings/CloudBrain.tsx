import { useState, useEffect, useCallback, useRef } from "react";
import {
  RotateCw,
  Key,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  ExternalLink,
  HelpCircle,
  Eye,
  EyeOff,
  Clipboard,
  CheckCircle2,
  XCircle,
  Loader2,
  Cloud,
  Cpu,
  Zap,
  Server,
  Layers,
  Sparkles,
  Code2,
  X,
} from "lucide-react";
import type { Provider } from "../../types/providers";
import {
  fetchProviders,
  connectProvider,
  disconnectProvider,
  fetchProviderModels,
} from "../../services/providerService";
import "./CloudBrain.css";


export default function CloudBrain() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showBeginnerGuide, setShowBeginnerGuide] = useState(false);

  // Per-provider input states
  const [inputStates, setInputStates] = useState<
    Record<
      string,
      {
        apiKey: string;
        accountId: string;
        model: string;
        modelsList: string[];
        loadingModels: boolean;
        showKey: boolean;
        testing: boolean;
        feedback: { success: boolean; msg: string } | null;
      }
    >
  >({});

  // Modal for "How to create it"
  const [activeGuideModal, setActiveGuideModal] = useState<Provider | null>(null);
  const debounceTimers = useRef<Record<string, ReturnType<typeof setTimeout>>>({});

  const refreshModelsForProvider = useCallback(async (providerId: string, apiKey?: string, accountId?: string) => {
    setInputStates((prev) => {
      if (!prev[providerId]) return prev;
      return {
        ...prev,
        [providerId]: {
          ...prev[providerId],
          loadingModels: true,
        },
      };
    });

    try {
      const models = await fetchProviderModels(providerId, apiKey, accountId);
      if (models && models.length > 0) {
        setInputStates((prev) => {
          const current = prev[providerId];
          if (!current) return prev;
          const hasCurrentModel = models.includes(current.model);
          return {
            ...prev,
            [providerId]: {
              ...current,
              modelsList: models,
              model: hasCurrentModel ? current.model : models[0],
              loadingModels: false,
            },
          };
        });
      } else {
        setInputStates((prev) => {
          if (!prev[providerId]) return prev;
          return {
            ...prev,
            [providerId]: {
              ...prev[providerId],
              loadingModels: false,
            },
          };
        });
      }
    } catch {
      setInputStates((prev) => {
        if (!prev[providerId]) return prev;
        return {
          ...prev,
          [providerId]: {
            ...prev[providerId],
            loadingModels: false,
          },
        };
      });
    }
  }, []);

  const loadProviders = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);

    try {
      const data = await fetchProviders();
      setProviders(data);

      // Initialize inputs from data if not already edited
      setInputStates((prev) => {
        const next = { ...prev };
        for (const p of data) {
          if (!next[p.id]) {
            next[p.id] = {
              apiKey: "",
              accountId: p.account_id || "",
              model: p.selected_model || p.default_model,
              modelsList: p.available_models || [],
              loadingModels: false,
              showKey: false,
              testing: false,
              feedback: null,
            };
          } else {
            // Keep existing typed apiKey and modelsList
            next[p.id] = {
              ...next[p.id],
              accountId: next[p.id].accountId || p.account_id || "",
              modelsList: next[p.id].modelsList?.length ? next[p.id].modelsList : p.available_models || [],
            };
          }
        }
        return next;
      });

      // Auto-fetch dynamic models for connected providers
      for (const p of data) {
        if (p.has_key || p.connected) {
          refreshModelsForProvider(p.id, undefined, p.account_id);
        }
      }
    } catch (err) {
      console.error("Failed to load providers:", err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [refreshModelsForProvider]);

  useEffect(() => {
    loadProviders();
  }, [loadProviders]);

  const handleInputChange = (providerId: string, field: "apiKey" | "accountId" | "model", value: string) => {
    setInputStates((prev) => ({
      ...prev,
      [providerId]: {
        ...prev[providerId],
        [field]: value,
        feedback: null,
      },
    }));

    if (field === "apiKey" && value.trim().length > 6) {
      if (debounceTimers.current[providerId]) {
        clearTimeout(debounceTimers.current[providerId]);
      }
      debounceTimers.current[providerId] = setTimeout(() => {
        refreshModelsForProvider(providerId, value.trim(), inputStates[providerId]?.accountId);
      }, 700);
    }
  };

  const toggleShowKey = (providerId: string) => {
    setInputStates((prev) => ({
      ...prev,
      [providerId]: {
        ...prev[providerId],
        showKey: !prev[providerId]?.showKey,
      },
    }));
  };

  const handlePasteKey = async (providerId: string) => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        const clean = text.trim();
        handleInputChange(providerId, "apiKey", clean);
        refreshModelsForProvider(providerId, clean, inputStates[providerId]?.accountId);
      }
    } catch (err) {
      console.error("Failed to read clipboard:", err);
    }
  };

  const handleTestAndConnect = async (p: Provider) => {
    const state = inputStates[p.id];
    const keyToUse = state?.apiKey || "";
    const accToUse = state?.accountId || "";
    const modelToUse = state?.model || p.default_model;

    setInputStates((prev) => ({
      ...prev,
      [p.id]: { ...prev[p.id], testing: true, feedback: null },
    }));

    try {
      const res = await connectProvider(p.id, keyToUse, accToUse, modelToUse);
      setInputStates((prev) => ({
        ...prev,
        [p.id]: {
          ...prev[p.id],
          testing: false,
          // RETAIN the API key so the user can test other models without re-entering!
          feedback: {
            success: res.connected,
            msg: res.message || (res.connected ? "Connected successfully" : "Connection failed"),
          },
        },
      }));
      // If connected successfully and we didn't fetch dynamic models yet, fetch now
      if (res.connected) {
        refreshModelsForProvider(p.id, keyToUse, accToUse);
      }
      // Reload providers to get updated status & masked key
      await loadProviders(true);
    } catch (err: unknown) {
      setInputStates((prev) => ({
        ...prev,
        [p.id]: {
          ...prev[p.id],
          testing: false,
          feedback: {
            success: false,
            msg: err instanceof Error ? err.message : "Failed to connect",
          },
        },
      }));
    }
  };

  const handleDisconnect = async (providerId: string) => {
    try {
      await disconnectProvider(providerId);
      setInputStates((prev) => ({
        ...prev,
        [providerId]: {
          ...prev[providerId],
          apiKey: "",
          feedback: null,
        },
      }));
      await loadProviders(true);
    } catch (err) {
      console.error("Disconnect failed:", err);
    }
  };

  const isAnyProviderConnected = providers.some((p) => p.connected);

  const getProviderIcon = (type: string) => {
    switch (type) {
      case "google":
        return <Sparkles size={18} />;
      case "cloudflare":
        return <Cloud size={18} />;
      case "groq":
        return <Zap size={18} />;
      case "nvidia":
        return <Cpu size={18} />;
      case "openrouter":
        return <Layers size={18} />;
      case "opencode":
        return <Code2 size={18} />;
      case "cruz":
        return <Server size={18} />;
      case "ollama":
      default:
        return <Cpu size={18} />;
    }
  };

  return (
    <div className="cloud-brain-container">
      {/* ── Header ── */}
      <div className="cb-header-wrapper">
        <div>
          <div className="cb-subtitle-tag">Universal Compute</div>
          <h1 className="cb-title">Connect a Cloud Brain</h1>
          <p className="cb-description">
            Connect one provider to run CRUZ on this computer — no local model required.
          </p>
        </div>

        <div className="cb-header-actions">
          <button
            className="cb-refresh-btn"
            onClick={() => loadProviders(true)}
            disabled={refreshing}
            type="button"
          >
            <RotateCw size={14} className={refreshing ? "spin-animation" : ""} />
            <span>Refresh status</span>
          </button>

          <div className="cb-status-badge">
            <div className="cb-status-dot" />
            <span>{isAnyProviderConnected ? "Inference ready" : "Offline fallback"}</span>
          </div>
        </div>
      </div>

      {/* ── Beginner Setup Banner ── */}
      <div
        className="cb-beginner-card"
        onClick={() => setShowBeginnerGuide(!showBeginnerGuide)}
      >
        <div className="cb-beginner-header">
          <div className="cb-beginner-left">
            <div className="cb-beginner-icon">
              <Key size={20} />
            </div>
            <div>
              <div className="cb-beginner-title">I AM A BEGINNER — SET IT UP FOR ME</div>
              <div className="cb-beginner-sub">
                Fast guided steps: One valid Google Gemini key is enough to start chatting for free.
              </div>
            </div>
          </div>
          {showBeginnerGuide ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </div>

        {showBeginnerGuide && (
          <div className="cb-beginner-content" onClick={(e) => e.stopPropagation()}>
            <div className="cb-step-item">
              <div className="cb-step-num">STEP 1</div>
              <div className="cb-step-desc">
                Open <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noreferrer" style={{ color: "#a78bfa" }}>Google AI Studio</a> in a new tab.
              </div>
            </div>
            <div className="cb-step-item">
              <div className="cb-step-num">STEP 2</div>
              <div className="cb-step-desc">
                Sign in and click <strong>"Create API key"</strong>.
              </div>
            </div>
            <div className="cb-step-item">
              <div className="cb-step-num">STEP 3</div>
              <div className="cb-step-desc">
                Paste your key into the <strong>Google Gemini</strong> card below and click <strong>"Test connection"</strong>.
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── Policy & Limits Alert ── */}
      <div className="cb-limits-alert">
        <AlertTriangle size={18} style={{ flexShrink: 0 }} />
        <div>
          Free access can have request, token, or daily limits. Availability and limits can change. CRUZ respects provider terms honestly and never enables paid models by default.
        </div>
      </div>

      {/* ── Provider Cards Grid ── */}
      {loading ? (
        <div style={{ display: "flex", justifyContent: "center", padding: "60px 0" }}>
          <Loader2 size={32} className="spin-animation" style={{ color: "#7c5cfc" }} />
        </div>
      ) : (
        <div className="cb-grid">
          {providers.map((p) => {
            const pState = inputStates[p.id] || {
              apiKey: "",
              accountId: p.account_id || "",
              model: p.selected_model || p.default_model,
              showKey: false,
              testing: false,
              feedback: null,
            };

            const isConnected = p.connected;
            const hasExistingKey = p.has_key;

            return (
              <div key={p.id} className={`cb-card ${isConnected ? "connected" : ""}`}>
                {/* Tier Badge */}
                <div className="cb-card-badge">{p.tier_label}</div>

                {/* Header: Icon + Title + Status */}
                <div className="cb-card-header">
                  <div className="cb-card-title-group">
                    <div className="cb-provider-icon">{getProviderIcon(p.icon_type)}</div>
                    <h3 className="cb-card-title">{p.name}</h3>
                  </div>

                  <div className={`cb-card-status-pill ${isConnected ? "on" : "off"}`}>
                    <span
                      style={{
                        width: 6,
                        height: 6,
                        borderRadius: "50%",
                        background: isConnected ? "#10b981" : "#64748b",
                      }}
                    />
                    <span>{isConnected ? "Connected" : "Disconnected"}</span>
                  </div>
                </div>

                {/* Description */}
                <p className="cb-card-desc">{p.description}</p>

                {/* Good for Tags */}
                <div className="cb-card-tags">
                  Good for: {p.tags.join(" · ")}
                </div>

                {/* Action Links: Get Key / Guide */}
                <div className="cb-card-links">
                  {p.get_key_url && (
                    <a
                      href={p.get_key_url}
                      target="_blank"
                      rel="noreferrer"
                      className="cb-link-btn"
                    >
                      <span>Get API key</span>
                      <ExternalLink size={12} />
                    </a>
                  )}

                  {p.how_to_create_guide && p.how_to_create_guide.length > 0 && (
                    <button
                      className="cb-link-btn"
                      onClick={() => setActiveGuideModal(p)}
                      type="button"
                    >
                      <span>How to create it</span>
                      <HelpCircle size={12} />
                    </button>
                  )}
                </div>

                {/* Inputs */}
                {p.id !== "ollama" && (
                  <>
                    {/* Cloudflare Account ID if required */}
                    {p.requires_account_id && (
                      <div className="cb-input-group">
                        <label className="cb-input-label">{p.account_id_label || "Account ID"}</label>
                        <div className="cb-input-box">
                          <input
                            type="text"
                            placeholder="Enter Cloudflare Account ID"
                            value={pState.accountId}
                            onChange={(e) => handleInputChange(p.id, "accountId", e.target.value)}
                          />
                        </div>
                      </div>
                    )}

                    {/* API Key Input */}
                    <div className="cb-input-group">
                      <label className="cb-input-label">API Key</label>
                      <div className="cb-input-box">
                        <input
                          type={pState.showKey ? "text" : "password"}
                          placeholder={hasExistingKey ? p.masked_key : "Paste your API key"}
                          value={pState.apiKey}
                          onChange={(e) => handleInputChange(p.id, "apiKey", e.target.value)}
                        />
                        <div className="cb-input-actions">
                          <button
                            type="button"
                            className="cb-icon-btn"
                            onClick={() => toggleShowKey(p.id)}
                            title={pState.showKey ? "Hide API key" : "Show API key"}
                          >
                            {pState.showKey ? <EyeOff size={14} /> : <Eye size={14} />}
                          </button>
                          <button
                            type="button"
                            className="cb-paste-btn"
                            onClick={() => handlePasteKey(p.id)}
                            title="Paste from clipboard"
                          >
                            <Clipboard size={12} />
                            <span>Paste</span>
                          </button>
                        </div>
                      </div>
                    </div>

                    {/* Model selector dropdown */}
                    {(() => {
                      const displayModels = (pState.modelsList && pState.modelsList.length > 0) ? pState.modelsList : p.available_models;
                      if (!displayModels || displayModels.length === 0) return null;
                      return (
                        <div className="cb-input-group">
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                            <label className="cb-input-label" style={{ margin: 0 }}>Default Model</label>
                            {pState.loadingModels ? (
                              <span style={{ fontSize: 11, color: "#a78bfa", display: "flex", alignItems: "center", gap: 4 }}>
                                <Loader2 size={11} className="spin-animation" /> Checking live free models...
                              </span>
                            ) : (
                              <span style={{ fontSize: 11, color: "#94a3b8" }}>
                                {displayModels.length} available models
                              </span>
                            )}
                          </div>
                          <select
                            className="cb-model-select"
                            value={pState.model}
                            onChange={(e) => handleInputChange(p.id, "model", e.target.value)}
                          >
                            <option value="auto">✨ Auto — Dynamic Best Free Model for Task (Recommended)</option>
                            {displayModels.filter((m) => m !== "auto").map((m) => (
                              <option key={m} value={m}>
                                {m}
                              </option>
                            ))}
                          </select>
                        </div>
                      );
                    })()}

                    {/* Terms notice */}
                    <div className="cb-terms-note">
                      I understand provider limits and my provider account's billing terms may apply. Paid model selection stays disabled.
                    </div>
                  </>
                )}

                {/* Local Ollama Info */}
                {p.id === "ollama" && (
                  <div style={{ margin: "14px 0", fontSize: 13, color: "#cbd5e1", lineHeight: 1.4 }}>
                    Private inference on this device. Install Ollama from <a href="https://ollama.com" target="_blank" rel="noreferrer" style={{ color: "#a78bfa" }}>ollama.com</a>, then run: <code style={{ background: "rgba(0,0,0,0.3)", padding: "2px 6px", borderRadius: 4 }}>ollama pull qwen2.5:3b</code>
                  </div>
                )}

                {/* Card Action Footer */}
                <div className="cb-card-footer">
                  <button
                    className="cb-test-btn"
                    onClick={() => handleTestAndConnect(p)}
                    disabled={pState.testing}
                    type="button"
                  >
                    {pState.testing ? (
                      <>
                        <Loader2 size={14} className="spin-animation" />
                        <span>Testing...</span>
                      </>
                    ) : (
                      <span>Test connection</span>
                    )}
                  </button>

                  {isConnected && p.id !== "ollama" && (
                    <button
                      className="cb-disconnect-btn"
                      onClick={() => handleDisconnect(p.id)}
                      type="button"
                    >
                      Disconnect
                    </button>
                  )}
                </div>

                {/* Feedback Message */}
                {pState.feedback && (
                  <div
                    className={`cb-feedback-msg ${
                      pState.feedback.success ? "success" : "error"
                    }`}
                  >
                    {pState.feedback.success ? (
                      <CheckCircle2 size={14} style={{ flexShrink: 0 }} />
                    ) : (
                      <XCircle size={14} style={{ flexShrink: 0 }} />
                    )}
                    <span>{pState.feedback.msg}</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* ── Guide Modal ── */}
      {activeGuideModal && (
        <div className="cb-modal-overlay" onClick={() => setActiveGuideModal(null)}>
          <div className="cb-modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="cb-modal-header">
              <h3 className="cb-modal-title">How to get {activeGuideModal.name} API Key</h3>
              <button
                className="cb-icon-btn"
                onClick={() => setActiveGuideModal(null)}
                type="button"
              >
                <X size={18} />
              </button>
            </div>

            <div className="cb-modal-steps">
              {activeGuideModal.how_to_create_guide.map((step, idx) => (
                <div key={idx} className="cb-modal-step-row">
                  {step}
                </div>
              ))}
            </div>

            <div className="cb-modal-footer">
              {activeGuideModal.get_key_url && (
                <a
                  href={activeGuideModal.get_key_url}
                  target="_blank"
                  rel="noreferrer"
                  className="cb-test-btn"
                  style={{ textDecoration: "none", display: "inline-flex" }}
                >
                  <span>Open {activeGuideModal.name} Portal</span>
                  <ExternalLink size={14} />
                </a>
              )}
              <button
                className="cb-refresh-btn"
                onClick={() => setActiveGuideModal(null)}
                type="button"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
