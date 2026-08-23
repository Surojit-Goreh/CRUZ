from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid


@dataclass
class Specialist:
    """
    Standardized model for each of the 100 CRUZ Specialists (X001–X100).
    Encapsulates identity, role, department, capabilities, required tools,
    input/output contracts, dependencies, permissions, and prompt guidance.
    """
    id: str                                  # Unique ID (e.g. "X001", "X011", "X100")
    name: str                                # Human readable name (e.g. "Supreme Commander")
    department: str                          # Department (e.g. "Command", "Coding", "Research", ...)
    role: str                                # Primary responsibility
    description: str                         # Detailed description of specialist's function
    capabilities: List[str]                  # Capability keywords (e.g. ["python", "debugging", "fastapi"])
    relevant_tools: List[str] = field(default_factory=list) # Tools this specialist utilizes
    input_requirements: List[str] = field(default_factory=list) # Expected input fields or artifacts
    expected_output: str = ""                # Format/description of expected output
    dependencies: List[str] = field(default_factory=list) # Other specialist IDs typically required before this
    required_permissions: List[str] = field(default_factory=list) # Permissions needed (e.g. ["filesystem_read"])
    enabled: bool = True                     # Enabled state in UI
    is_core: bool = False                    # Core specialists cannot be disabled (e.g. X001, X100)
    version: str = "1.0.0"                   # Versioning
    prompt_guidelines: str = ""              # Specialized system prompt instruction

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "department": self.department,
            "role": self.role,
            "description": self.description,
            "capabilities": self.capabilities,
            "relevant_tools": self.relevant_tools,
            "input_requirements": self.input_requirements,
            "expected_output": self.expected_output,
            "dependencies": self.dependencies,
            "required_permissions": self.required_permissions,
            "enabled": self.enabled,
            "is_core": self.is_core,
            "version": self.version,
        }


@dataclass
class SpecialistResult:
    """
    Structured outcome produced by a single specialist execution.
    """
    specialist_id: str
    specialist_name: str
    status: str                              # "SUCCESS", "WARNING", "FAILED", "SKIPPED"
    output: str                              # Primary text output or response fragment
    artifacts: List[str] = field(default_factory=list) # Generated file paths or references
    warnings: List[str] = field(default_factory=list)  # Any non-fatal issues observed
    errors: List[str] = field(default_factory=list)    # Fatal errors if failed
    confidence: float = 1.0                  # Confidence score (0.0 - 1.0)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "specialist_id": self.specialist_id,
            "specialist_name": self.specialist_name,
            "status": self.status,
            "output": self.output,
            "artifacts": self.artifacts,
            "warnings": self.warnings,
            "errors": self.errors,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


@dataclass
class SubTask:
    """
    An individual subtask step within an execution plan assigned to a specialist.
    """
    id: str
    title: str
    description: str
    department: str
    specialist_id: str
    dependencies: List[str] = field(default_factory=list) # IDs of parent subtasks that must complete first
    input_data: Dict[str, Any] = field(default_factory=dict)
    status: str = "PENDING"                  # "PENDING", "RUNNING", "COMPLETED", "FAILED", "SKIPPED"
    result: Optional[SpecialistResult] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "department": self.department,
            "specialist_id": self.specialist_id,
            "dependencies": self.dependencies,
            "status": self.status,
            "result": self.result.to_dict() if self.result else None,
        }


@dataclass
class ExecutionPlan:
    """
    Dynamic execution plan constructed by Command specialists (X001-X007) for a user request.
    """
    plan_id: str = field(default_factory=lambda: f"plan_{uuid.uuid4().hex[:12]}")
    user_request: str = ""
    intent: str = "general"
    complexity: str = "simple"               # "simple", "moderate", "complex"
    departments: List[str] = field(default_factory=list)
    specialists: List[str] = field(default_factory=list)
    subtasks: List[SubTask] = field(default_factory=list)
    estimated_steps: int = 1
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "user_request": self.user_request,
            "intent": self.intent,
            "complexity": self.complexity,
            "departments": self.departments,
            "specialists": self.specialists,
            "subtasks": [st.to_dict() for st in self.subtasks],
            "estimated_steps": self.estimated_steps,
            "created_at": self.created_at,
        }


@dataclass
class QualityVerdict:
    """
    Evaluation produced by the Quality Department (X091-X100) led by X100 Supreme Judge.
    """
    verdict: str                             # "PASS", "PASS_WITH_WARNINGS", "RETRY", "ESCALATE", "FAIL"
    score: float                             # 0.0 - 100.0 score
    criticisms: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    safety_checked: bool = True
    grounding_checked: bool = True
    evaluator_id: str = "X100"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict,
            "score": self.score,
            "criticisms": self.criticisms,
            "recommendations": self.recommendations,
            "safety_checked": self.safety_checked,
            "grounding_checked": self.grounding_checked,
            "evaluator_id": self.evaluator_id,
            "timestamp": self.timestamp,
        }


@dataclass
class TaskContext:
    """
    Scoped shared execution context maintained across specialists during a task.
    """
    request_id: str = field(default_factory=lambda: f"req_{uuid.uuid4().hex[:12]}")
    user_message: str = ""
    detected_intent: str = ""
    requirements: List[str] = field(default_factory=list)
    active_plan: Optional[ExecutionPlan] = None
    specialist_results: Dict[str, SpecialistResult] = field(default_factory=dict)
    artifacts: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    tool_outputs: List[Dict[str, Any]] = field(default_factory=list)
    quality_verdict: Optional[QualityVerdict] = None
    final_output: str = ""

    def add_result(self, result: SpecialistResult):
        self.specialist_results[result.specialist_id] = result
        if result.artifacts:
            self.artifacts.extend(result.artifacts)
        if result.warnings:
            self.warnings.extend(result.warnings)

    def get_summary_context(self, max_chars: int = 4000) -> str:
        """Renders compact summary of previous specialist outputs for downstream specialists."""
        parts = []
        for sid, res in self.specialist_results.items():
            if res.output:
                snippet = res.output[:600] + ("..." if len(res.output) > 600 else "")
                parts.append(f"[{sid} {res.specialist_name} ({res.status})]:\n{snippet}")
        full = "\n\n".join(parts)
        return full[:max_chars]
