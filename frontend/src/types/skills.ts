export interface Skill {
  name: string;
  display_name: string;
  description: string;
  icon: string;
  version: string;
  is_core: boolean;
  enabled: boolean;
  task_categories: string[];
  trigger_keywords: string[];
  tool_count: number;
  tools: string[];
}

export interface SkillsResponse {
  skills: Skill[];
}

export interface ToggleSkillResponse {
  name: string;
  enabled: boolean;
  status: string;
}

export interface Specialist {
  id: string;
  name: string;
  department: string;
  role: string;
  description: string;
  capabilities: string[];
  relevant_tools: string[];
  input_requirements: string[];
  expected_output: string;
  dependencies: string[];
  required_permissions: string[];
  enabled: boolean;
  is_core: boolean;
  version: string;
}

export interface DepartmentSummary {
  name: string;
  total_specialists: number;
  enabled_specialists: number;
  specialist_ids: string[];
}

export interface SubTask {
  id: string;
  title: string;
  description: string;
  department: string;
  specialist_id: string;
  dependencies: string[];
  status: string;
}

export interface ExecutionPlan {
  plan_id: string;
  user_request: string;
  intent: string;
  complexity: string;
  departments: string[];
  specialists: string[];
  subtasks: SubTask[];
  estimated_steps: number;
  created_at: string;
}
