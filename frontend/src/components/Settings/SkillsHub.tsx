import { useState, useEffect, useCallback } from "react";
import {
  RotateCw,
  Sparkles,
  FolderOpen,
  Globe,
  Search,
  Laptop,
  Image as ImageIcon,
  Puzzle,
  CheckCircle2,
  XCircle,
  Loader2,
  ShieldCheck,
  Zap,
  Layers,
  ChevronDown,
  ChevronUp,
  Bot,
  FileCode,
  FileText,
  Palette,
  Database,
  Volume2,
  Calendar,
  Compass,
  CheckCheck,
  SearchCode,
  Play,
} from "lucide-react";
import type { Skill, Specialist, DepartmentSummary, ExecutionPlan } from "../../types/skills";
import {
  fetchSkills,
  toggleSkill,
  fetchSpecialists,
  fetchDepartments,
  toggleSpecialist,
  previewExecutionPlan,
} from "../../services/skillService";
import "./SkillsHub.css";

interface Props {
  activeAgentMode?: string;
}

const DEPARTMENT_ICONS: Record<string, any> = {
  All: Layers,
  Command: Bot,
  Coding: FileCode,
  Research: SearchCode,
  Writing: FileText,
  Visual: Palette,
  Data: Database,
  Media: Volume2,
  Productivity: Calendar,
  Strategy: Compass,
  Quality: CheckCheck,
};

export default function SkillsHub({ activeAgentMode = "auto" }: Props) {
  // Main view tabs: "specialists" (100 specialists) | "skills" (modular tools) | "planner" (DAG tester)
  const [activeTab, setActiveTab] = useState<"specialists" | "skills" | "planner">("specialists");

  // 100 Specialists State
  const [specialists, setSpecialists] = useState<Specialist[]>([]);
  const [departments, setDepartments] = useState<DepartmentSummary[]>([]);
  const [selectedDept, setSelectedDept] = useState<string>("All");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [togglingSpecialist, setTogglingSpecialist] = useState<string | null>(null);

  // Modular Skills State
  const [skills, setSkills] = useState<Skill[]>([]);
  const [togglingSkill, setTogglingSkill] = useState<string | null>(null);
  const [expandedTools, setExpandedTools] = useState<Record<string, boolean>>({});

  // DAG Plan Tester State
  const [testPrompt, setTestPrompt] = useState<string>("Research best monitors under 10000 and write a comparison table");
  const [previewPlan, setPreviewPlan] = useState<ExecutionPlan | null>(null);
  const [planningLoading, setPlanningLoading] = useState<boolean>(false);

  // General State
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [feedback, setFeedback] = useState<{ success: boolean; msg: string } | null>(null);
  const [showArchitectureGuide, setShowArchitectureGuide] = useState(false);

  const loadData = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);

    try {
      const [skillsData, specsData, deptsData] = await Promise.all([
        fetchSkills(),
        fetchSpecialists(),
        fetchDepartments(),
      ]);
      setSkills(skillsData);
      setSpecialists(specsData);
      setDepartments(deptsData);
    } catch (err) {
      console.error("Failed to load skills hub data:", err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Toggle Specialist
  const handleToggleSpecialist = async (spec: Specialist) => {
    if (spec.is_core) return;
    const targetState = !spec.enabled;
    setTogglingSpecialist(spec.id);
    setFeedback(null);

    try {
      await toggleSpecialist(spec.id, targetState);
      setSpecialists((prev) =>
        prev.map((s) => (s.id === spec.id ? { ...s, enabled: targetState } : s))
      );
      setFeedback({
        success: true,
        msg: `${spec.name} (${spec.id}) ${targetState ? "enabled" : "disabled"}`,
      });
      setTimeout(() => setFeedback(null), 3000);
    } catch (err: unknown) {
      setFeedback({
        success: false,
        msg: err instanceof Error ? err.message : "Failed to toggle specialist",
      });
    } finally {
      setTogglingSpecialist(null);
    }
  };

  // Toggle Modular Tool Skill
  const handleToggleSkill = async (skill: Skill) => {
    if (skill.is_core) return;
    const targetState = !skill.enabled;
    setTogglingSkill(skill.name);
    setFeedback(null);

    try {
      const res = await toggleSkill(skill.name, targetState);
      setSkills((prev) =>
        prev.map((s) => (s.name === skill.name ? { ...s, enabled: res.enabled } : s))
      );
      setFeedback({
        success: true,
        msg: `${skill.display_name} ${res.enabled ? "enabled" : "disabled"}`,
      });
      setTimeout(() => setFeedback(null), 3000);
    } catch (err: unknown) {
      setFeedback({
        success: false,
        msg: err instanceof Error ? err.message : "Failed to toggle skill",
      });
    } finally {
      setTogglingSkill(null);
    }
  };

  // Test Dynamic Plan
  const handleRunPlannerTest = async () => {
    if (!testPrompt.trim()) return;
    setPlanningLoading(true);
    try {
      const plan = await previewExecutionPlan(testPrompt, activeAgentMode);
      setPreviewPlan(plan);
    } catch (err) {
      console.error("Planner test error:", err);
    } finally {
      setPlanningLoading(false);
    }
  };

  // Filter Specialists
  const filteredSpecialists = specialists.filter((s) => {
    const matchesDept = selectedDept === "All" || s.department.toLowerCase() === selectedDept.toLowerCase();
    if (!matchesDept) return false;
    if (!searchQuery.trim()) return true;

    const q = searchQuery.toLowerCase();
    return (
      s.id.toLowerCase().includes(q) ||
      s.name.toLowerCase().includes(q) ||
      s.role.toLowerCase().includes(q) ||
      s.department.toLowerCase().includes(q) ||
      s.capabilities.some((c) => c.toLowerCase().includes(q))
    );
  });

  const totalSpecialistsEnabled = specialists.filter((s) => s.enabled || s.is_core).length;

  return (
    <div className="skills-hub-container">
      {/* ── Header ── */}
      <div className="sh-header-wrapper">
        <div>
          <div className="sh-subtitle-tag">Modular Intelligence & Orchestration</div>
          <h1 className="sh-title">100-Specialist Skills System</h1>
          <p className="sh-description">
            CRUZ orchestrates 100 specialized agents across 10 departments using dynamic capability-based routing,
            Command orchestration, and Quality verification.
          </p>
        </div>

        <div className="sh-header-actions">
          <button
            className="sh-refresh-btn"
            onClick={() => loadData(true)}
            disabled={refreshing}
            type="button"
          >
            <RotateCw size={14} className={refreshing ? "spin-animation" : ""} />
            <span>Refresh All</span>
          </button>

          <div className="sh-stats-pill">
            <div className="sh-stats-dot" />
            <span>{totalSpecialistsEnabled} of 100 Specialists Active</span>
          </div>
        </div>
      </div>

      {/* ── Architecture Guide Accordion ── */}
      <div className="sh-info-card" onClick={() => setShowArchitectureGuide(!showArchitectureGuide)}>
        <div className="sh-info-header">
          <div className="sh-info-left">
            <div className="sh-info-icon">
              <Zap size={20} />
            </div>
            <div>
              <div className="sh-info-title">HOW THE 100-SPECIALIST ENGINE WORKS</div>
              <div className="sh-info-sub">
                User Request → X002 Intent → X003 Requirements → X004 Master Planning → Multi-Department Execution → X100 Quality Judgment → X010 Final Synthesis.
              </div>
            </div>
          </div>
          {showArchitectureGuide ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </div>

        {showArchitectureGuide && (
          <div className="sh-info-content" onClick={(e) => e.stopPropagation()}>
            <div className="sh-guide-grid">
              <div className="sh-guide-item">
                <div className="sh-guide-num">1. Dynamic Orchestration</div>
                <p>Never runs all 100 specialists at once. Selects the minimal optimal set based on capability match.</p>
              </div>
              <div className="sh-guide-item">
                <div className="sh-guide-num">2. 10 Dedicated Departments</div>
                <p>Command (X001-X010), Coding, Research, Writing, Visual, Data, Media, Productivity, Strategy, and Quality.</p>
              </div>
              <div className="sh-guide-item">
                <div className="sh-guide-num">3. Quality Gate (X091–X100)</div>
                <p>Audits code, verifies facts, eliminates hallucinations, and X100 Supreme Judge gives final sign-off.</p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── Navigation Tabs ── */}
      <div className="sh-nav-tabs">
        <button
          className={`sh-nav-tab ${activeTab === "specialists" ? "active" : ""}`}
          onClick={() => setActiveTab("specialists")}
          type="button"
        >
          <Bot size={16} />
          <span>100 Specialists Catalog ({specialists.length})</span>
        </button>
        <button
          className={`sh-nav-tab ${activeTab === "planner" ? "active" : ""}`}
          onClick={() => setActiveTab("planner")}
          type="button"
        >
          <Compass size={16} />
          <span>Dynamic Plan Previewer</span>
        </button>
        <button
          className={`sh-nav-tab ${activeTab === "skills" ? "active" : ""}`}
          onClick={() => setActiveTab("skills")}
          type="button"
        >
          <Puzzle size={16} />
          <span>Core Tool Skills ({skills.length})</span>
        </button>
      </div>

      {/* ── Global Feedback Toast ── */}
      {feedback && (
        <div className={`sh-toast ${feedback.success ? "success" : "error"}`}>
          {feedback.success ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
          <span>{feedback.msg}</span>
        </div>
      )}

      {loading ? (
        <div className="sh-loading-container">
          <Loader2 size={36} className="spin-animation" style={{ color: "#7c5cfc" }} />
          <p>Loading 100-specialist catalog and department registries...</p>
        </div>
      ) : (
        <>
          {/* ══════════════════════════════════════════
              VIEW 1: 100 Specialists Catalog
             ══════════════════════════════════════════ */}
          {activeTab === "specialists" && (
            <div className="sh-specialists-view">
              {/* Department Filter Pills */}
              <div className="sh-dept-pills-bar">
                {["All", ...departments.map((d) => d.name)].map((deptName) => {
                  const Icon = DEPARTMENT_ICONS[deptName] || Layers;
                  const deptData = departments.find((d) => d.name === deptName);
                  const isSelected = selectedDept === deptName;

                  return (
                    <button
                      key={deptName}
                      className={`sh-dept-pill ${isSelected ? "active" : ""}`}
                      onClick={() => setSelectedDept(deptName)}
                      type="button"
                    >
                      <Icon size={14} />
                      <span>{deptName}</span>
                      <span className="sh-dept-count">
                        {deptName === "All" ? "100" : deptData ? `${deptData.enabled_specialists}/${deptData.total_specialists}` : "10"}
                      </span>
                    </button>
                  );
                })}
              </div>

              {/* Search Bar */}
              <div className="sh-search-row">
                <div className="sh-search-input-wrapper">
                  <Search size={16} className="sh-search-icon" />
                  <input
                    type="text"
                    className="sh-search-input"
                    placeholder="Search specialists by ID (e.g. X001, X011, X100), name, role, or capabilities..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                  {searchQuery && (
                    <button
                      type="button"
                      className="sh-search-clear"
                      onClick={() => setSearchQuery("")}
                    >
                      ✕
                    </button>
                  )}
                </div>
                <div className="sh-search-results-label">
                  Showing {filteredSpecialists.length} of {specialists.length} Specialists
                </div>
              </div>

              {/* Specialist Cards Grid */}
              <div className="sh-specialists-grid">
                {filteredSpecialists.map((spec) => {
                  const isEnabled = spec.enabled || spec.is_core;
                  const isToggling = togglingSpecialist === spec.id;

                  return (
                    <div
                      key={spec.id}
                      className={`sh-spec-card ${isEnabled ? "enabled" : "disabled"} ${spec.is_core ? "core" : ""}`}
                    >
                      <div className="sh-spec-card-header">
                        <div className="sh-spec-id-badge">
                          <span className="sh-spec-id">{spec.id}</span>
                          <span className="sh-spec-dept-tag">{spec.department}</span>
                        </div>

                        {spec.is_core ? (
                          <div className="sh-core-badge" title="Core Specialist (Always active)">
                            <ShieldCheck size={13} />
                            <span>CORE</span>
                          </div>
                        ) : (
                          <button
                            type="button"
                            className={`sh-toggle-switch ${isEnabled ? "on" : "off"}`}
                            onClick={() => handleToggleSpecialist(spec)}
                            disabled={isToggling}
                            title={isEnabled ? "Disable Specialist" : "Enable Specialist"}
                          >
                            {isToggling ? (
                              <Loader2 size={12} className="spin-animation" />
                            ) : (
                              <div className="sh-toggle-thumb" />
                            )}
                          </button>
                        )}
                      </div>

                      <div className="sh-spec-body">
                        <h3 className="sh-spec-name">{spec.name}</h3>
                        <div className="sh-spec-role">{spec.role}</div>
                        <p className="sh-spec-desc">{spec.description}</p>

                        {/* Capability Chips */}
                        <div className="sh-spec-caps-wrapper">
                          {spec.capabilities.slice(0, 4).map((cap, i) => (
                            <span key={i} className="sh-cap-chip">
                              {cap}
                            </span>
                          ))}
                          {spec.capabilities.length > 4 && (
                            <span className="sh-cap-chip more">
                              +{spec.capabilities.length - 4}
                            </span>
                          )}
                        </div>

                        {/* Tool Needs */}
                        {spec.relevant_tools && spec.relevant_tools.length > 0 && (
                          <div className="sh-spec-tools-row">
                            <span className="sh-tools-label">Tools:</span>
                            {spec.relevant_tools.map((t, idx) => (
                              <code key={idx} className="sh-tool-tag">
                                {t}
                              </code>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* ══════════════════════════════════════════
              VIEW 2: Dynamic Plan Previewer
             ══════════════════════════════════════════ */}
          {activeTab === "planner" && (
            <div className="sh-planner-view">
              <div className="sh-planner-hero">
                <h2>Dynamic Orchestration DAG Tester</h2>
                <p>
                  Enter any user request to see how Supreme Commander (X001), Intent Detector (X002), and Master Planner (X004)
                  dynamically construct the subtask execution plan.
                </p>

                <div className="sh-planner-input-box">
                  <input
                    type="text"
                    className="sh-planner-input"
                    value={testPrompt}
                    onChange={(e) => setTestPrompt(e.target.value)}
                    placeholder="Enter a request to simulate dynamic execution planning..."
                  />
                  <button
                    className="sh-planner-run-btn"
                    onClick={handleRunPlannerTest}
                    disabled={planningLoading}
                    type="button"
                  >
                    {planningLoading ? <Loader2 size={16} className="spin-animation" /> : <Play size={16} />}
                    <span>Generate DAG Plan</span>
                  </button>
                </div>
              </div>

              {previewPlan && (
                <div className="sh-plan-result-card">
                  <div className="sh-plan-meta-row">
                    <div className="sh-plan-meta-item">
                      <span className="label">Plan ID:</span>
                      <strong>{previewPlan.plan_id}</strong>
                    </div>
                    <div className="sh-plan-meta-item">
                      <span className="label">Detected Intent:</span>
                      <strong className="intent-badge">{previewPlan.intent.toUpperCase()}</strong>
                    </div>
                    <div className="sh-plan-meta-item">
                      <span className="label">Complexity:</span>
                      <strong className="complexity-badge">{previewPlan.complexity.toUpperCase()}</strong>
                    </div>
                    <div className="sh-plan-meta-item">
                      <span className="label">Active Departments:</span>
                      <strong>{previewPlan.departments.join(", ")}</strong>
                    </div>
                  </div>

                  <h3 className="sh-dag-title">Execution Subtasks DAG ({previewPlan.subtasks.length} Steps)</h3>
                  <div className="sh-subtasks-list">
                    {previewPlan.subtasks.map((st, i) => {
                      const spec = specialists.find((s) => s.id === st.specialist_id);
                      return (
                        <div key={st.id} className="sh-subtask-card">
                          <div className="sh-subtask-step-num">{i + 1}</div>
                          <div className="sh-subtask-main">
                            <div className="sh-subtask-header">
                              <span className="sh-subtask-title">{st.title}</span>
                              <span className="sh-subtask-spec-id">
                                {st.specialist_id} {spec ? `· ${spec.name}` : ""}
                              </span>
                            </div>
                            <p className="sh-subtask-desc">{st.description}</p>
                            {st.dependencies && st.dependencies.length > 0 && (
                              <div className="sh-subtask-dep">
                                Depends on: <code>{st.dependencies.join(", ")}</code>
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ══════════════════════════════════════════
              VIEW 3: Core Modular Tool Skills
             ══════════════════════════════════════════ */}
          {activeTab === "skills" && (
            <div className="sh-grid">
              {skills.map((skill) => {
                const isEnabled = skill.enabled || skill.is_core;
                const isToggling = togglingSkill === skill.name;
                const isExpanded = !!expandedTools[skill.name];

                return (
                  <div
                    key={skill.name}
                    className={`sh-card ${isEnabled ? "enabled" : "disabled"} ${skill.is_core ? "core" : ""}`}
                  >
                    <div className="sh-card-header">
                      <div className="sh-card-header-left">
                        <div className="sh-icon-box">{getSkillIcon(skill.icon)}</div>
                        <div>
                          <div className="sh-card-title-row">
                            <h3 className="sh-card-title">{skill.display_name}</h3>
                            <span className="sh-version-tag">v{skill.version}</span>
                          </div>
                          <span className="sh-identifier">skills.{skill.name}</span>
                        </div>
                      </div>

                      {skill.is_core ? (
                        <div className="sh-core-badge" title="Core skill cannot be disabled">
                          <ShieldCheck size={14} />
                          <span>CORE</span>
                        </div>
                      ) : (
                        <button
                          type="button"
                          className={`sh-toggle-switch ${isEnabled ? "on" : "off"}`}
                          onClick={() => handleToggleSkill(skill)}
                          disabled={isToggling}
                          title={isEnabled ? "Disable Skill" : "Enable Skill"}
                        >
                          {isToggling ? (
                            <Loader2 size={12} className="spin-animation" />
                          ) : (
                            <div className="sh-toggle-thumb" />
                          )}
                        </button>
                      )}
                    </div>

                    <p className="sh-card-desc">{skill.description}</p>

                    <div className="sh-tags-section">
                      <div className="sh-tags-label">Task Affinities</div>
                      <div className="sh-tags-row">
                        {skill.task_categories.map((cat) => (
                          <span key={cat} className="sh-task-tag">
                            {cat}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div className="sh-tools-accordion">
                      <button
                        type="button"
                        className="sh-tools-accordion-toggle"
                        onClick={() =>
                          setExpandedTools((prev) => ({
                            ...prev,
                            [skill.name]: !prev[skill.name],
                          }))
                        }
                      >
                        <span>
                          Registered Tools ({skill.tool_count})
                        </span>
                        {isExpanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
                      </button>

                      {isExpanded && (
                        <div className="sh-tools-list">
                          {skill.tools && skill.tools.length > 0 ? (
                            skill.tools.map((toolName) => (
                              <div key={toolName} className="sh-tool-item">
                                <span className="sh-tool-dot" />
                                <code>{toolName}</code>
                              </div>
                            ))
                          ) : (
                            <span className="sh-no-tools">No registered tool functions</span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function getSkillIcon(iconName: string) {
  switch (iconName?.toLowerCase()) {
    case "folderopen":
    case "folder":
      return <FolderOpen size={20} />;
    case "globe":
    case "browser":
      return <Globe size={20} />;
    case "search":
      return <Search size={20} />;
    case "laptop":
    case "desktop":
      return <Laptop size={20} />;
    case "image":
    case "imagegen":
      return <ImageIcon size={20} />;
    case "sparkles":
      return <Sparkles size={20} />;
    default:
      return <Puzzle size={20} />;
  }
}
