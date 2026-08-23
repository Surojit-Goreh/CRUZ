import type { Skill, ToggleSkillResponse } from "../types/skills";

const API_BASE = "http://127.0.0.1:8000";

export async function fetchSkills(): Promise<Skill[]> {
  const res = await fetch(`${API_BASE}/skills`);
  if (!res.ok) {
    throw new Error(`Failed to load skills: ${res.statusText}`);
  }
  const data = await res.json();
  return data.skills || [];
}

export async function toggleSkill(name: string, enabled: boolean): Promise<ToggleSkillResponse> {
  const res = await fetch(`${API_BASE}/skills/${name}/toggle`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to toggle skill" }));
    throw new Error(err.detail || "Failed to toggle skill");
  }
  return res.json();
}

export async function enableSkill(name: string): Promise<ToggleSkillResponse> {
  const res = await fetch(`${API_BASE}/skills/${name}/enable`, {
    method: "POST",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to enable skill" }));
    throw new Error(err.detail || "Failed to enable skill");
  }
  return res.json();
}

export async function disableSkill(name: string): Promise<ToggleSkillResponse> {
  const res = await fetch(`${API_BASE}/skills/${name}/disable`, {
    method: "POST",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to disable skill" }));
    throw new Error(err.detail || "Failed to disable skill");
  }
  return res.json();
}

// ──────────────────────────────────────────
// 100-Specialist System API Services
// ──────────────────────────────────────────
import type { Specialist, DepartmentSummary, ExecutionPlan } from "../types/skills";

export async function fetchSpecialists(department?: string, search?: string): Promise<Specialist[]> {
  const params = new URLSearchParams();
  if (department && department !== "All") params.append("department", department);
  if (search && search.trim()) params.append("search", search.trim());

  const url = `${API_BASE}/specialists${params.toString() ? `?${params.toString()}` : ""}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to load specialists: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchDepartments(): Promise<DepartmentSummary[]> {
  const res = await fetch(`${API_BASE}/specialists/departments`);
  if (!res.ok) {
    throw new Error(`Failed to load departments: ${res.statusText}`);
  }
  return res.json();
}

export async function toggleSpecialist(id: string, enabled: boolean): Promise<any> {
  const res = await fetch(`${API_BASE}/specialists/${id}/toggle`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to toggle specialist" }));
    throw new Error(err.detail || "Failed to toggle specialist");
  }
  return res.json();
}

export async function previewExecutionPlan(message: string, agentMode: string = "auto"): Promise<ExecutionPlan> {
  const res = await fetch(`${API_BASE}/specialists/plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, agent_mode: agentMode }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to preview plan" }));
    throw new Error(err.detail || "Failed to preview plan");
  }
  return res.json();
}
