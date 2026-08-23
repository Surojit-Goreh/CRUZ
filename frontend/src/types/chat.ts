import type { ExecutionPlan } from "./skills";

export interface ModelAttribution {
  provider_name: string;
  model: string;
  role?: string;
  provider_id?: string;
}

export interface Message {
  id: string;
  sender: "user" | "assistant";
  text: string;
  timestamp: string;
  provider?: string;
  model?: string;
  plan?: ExecutionPlan;
  models_used?: ModelAttribution[];
}

export interface ActivityEvent {
  type?: "activity";
  execution_id?: string;
  event_type: string;
  message: string;
  phase:
    | "understanding"
    | "planning"
    | "executing"
    | "researching"
    | "analyzing"
    | "verifying"
    | "synthesizing"
    | "completed"
    | "error"
    | string;
  specialist?: string;
  progress?: number;
  timestamp?: number;
}

export interface ActivityStep {
  id: string;
  message: string;
  specialist?: string;
  phase: string;
  completed: boolean;
  timestamp: number;
}

export interface ActivityState {
  execution_id?: string;
  status: "idle" | "processing" | "receiving" | "completed" | "error" | "cancelled";
  currentMessage: string;
  phase: string;
  specialist?: string;
  progress?: number;
  steps: ActivityStep[];
  errorMessage?: string;
}