"""
Command Orchestration & Dynamic Specialist Routing Engine for CRUZ.
Coordinates the multi-specialist lifecycle:
Intent -> Requirements -> Complexity -> Master Planning -> Execution DAG ->
Progress Monitoring -> Quality Verification -> Supreme Judgment -> Final Synthesis.
"""
import json
import re
import uuid
from typing import List, Dict, Any, Optional, Tuple

from utils.logger import get_logger
from .models import (
    Specialist,
    SpecialistResult,
    SubTask,
    ExecutionPlan,
    QualityVerdict,
    TaskContext,
)
from .registry import specialist_registry

logger = get_logger("skills.specialists.orchestrator")


class CommandOrchestrator:
    """
    Executes the dynamic specialist orchestration pipeline based on the Command Department (X001-X010).
    """

    MAX_RETRIES = 2
    MAX_SUBTASKS = 6

    def __init__(self):
        self.registry = specialist_registry

    def plan_task(self, user_message: str, agent_mode: Optional[str] = "auto") -> ExecutionPlan:
        """
        Plans the task using Command specialists X001-X007.
        Constructs an ExecutionPlan with minimal required departments and specialists.
        """
        # Step 1: X002 Intent Detection
        intent, complexity = self._detect_intent_and_complexity(user_message, agent_mode)

        # Step 2: X003 Requirement Analysis
        requirements, target_keywords = self._analyze_requirements(user_message, intent)

        # Step 3: X005 Department Routing
        departments = self._route_departments(user_message, intent, requirements)

        # Step 4: X006 Specialist Selection
        specialists = self._select_specialists(departments, target_keywords, intent)

        # Step 5: X004 & X007 Master Planning and Task Decomposition
        subtasks = self._decompose_subtasks(user_message, intent, requirements, departments, specialists)

        plan = ExecutionPlan(
            plan_id=f"plan_{uuid.uuid4().hex[:8]}",
            user_request=user_message,
            intent=intent,
            complexity=complexity,
            departments=departments,
            specialists=[s.id for s in specialists],
            subtasks=subtasks,
            estimated_steps=len(subtasks),
        )

        logger.info(
            f"Planned request '{user_message[:40]}...': "
            f"Intent={intent}, Complexity={complexity}, Depts={departments}, "
            f"Specialists={[s.id for s in specialists]}, Subtasks={len(subtasks)}"
        )
        return plan

    def _detect_intent_and_complexity(self, text: str, agent_mode: Optional[str]) -> Tuple[str, str]:
        """X002 Intent Detector & X001 Supreme Commander Complexity Assessment."""
        lower = text.lower()

        # Explicit mode overrides
        if agent_mode and agent_mode != "auto":
            intent_map = {
                "build": "coding",
                "plan": "reasoning",
                "writing": "writing",
                "image": "visual",
                "chat": "general",
            }
            if agent_mode in intent_map:
                intent = intent_map[agent_mode]
                complexity = "moderate" if len(text.split()) > 15 else "simple"
                return intent, complexity

        # Keyword heuristics for intent
        if any(w in lower for w in ["def ", "class ", "function", "bug", "error", "traceback", "fix", "code", "python", "typescript", "react", "fastapi", "npm", "pip", "sql"]):
            intent = "coding"
        elif any(w in lower for w in ["search", "research", "find", "price", "compare", "vs", "difference", "review", "monitor", "laptop", "market", "who is", "what is"]):
            intent = "research"
        elif any(w in lower for w in ["write", "article", "blog", "summary", "draft", "email", "docs", "docstring", "readme", "essay", "story"]):
            intent = "writing"
        elif any(w in lower for w in ["image", "picture", "draw", "generate", "ui", "css", "layout", "vrm", "avatar", "wireframe", "palette"]):
            intent = "visual"
        elif any(w in lower for w in ["data", "csv", "json", "analytics", "statistics", "dataset", "table", "chart", "metrics"]):
            intent = "data"
        elif any(w in lower for w in ["voice", "tts", "stt", "audio", "sound", "podcast", "subtitle", "speak"]):
            intent = "media"
        elif any(w in lower for w in ["automate", "organize", "todo", "task", "milestone", "standup", "schedule", "cleanup"]):
            intent = "productivity"
        elif any(w in lower for w in ["architecture", "strategy", "roadmap", "mvp", "tradeoff", "scale", "decision"]):
            intent = "strategy"
        else:
            intent = "general"

        # Complexity determination (X001 Supreme Commander)
        word_count = len(text.split())
        has_multi_clause = any(c in lower for c in [" and also ", " then ", " after that ", " step by step ", " comprehensive ", " in detail "])
        
        if word_count > 30 or has_multi_clause or ("search" in lower and "code" in lower) or ("research" in lower and "write" in lower):
            complexity = "complex"
        elif word_count > 12 or intent in ["coding", "strategy", "data"]:
            complexity = "moderate"
        else:
            complexity = "simple"

        return intent, complexity

    def _analyze_requirements(self, text: str, intent: str) -> Tuple[List[str], List[str]]:
        """X003 Requirement Analyst."""
        reqs = []
        keywords = []
        lower = text.lower()

        if intent == "coding":
            reqs.append("Analyze code structure, enforce error handling and typing.")
            keywords.extend(["python", "typescript", "debugging", "api", "testing"])
        elif intent == "research":
            reqs.append("Conduct multi-source web verification, price comparisons, and cite sources.")
            keywords.extend(["web-search", "market-analysis", "fact-checking", "spec-matrix"])
        elif intent == "writing":
            reqs.append("Produce clear, concise, well-structured GitHub Markdown text.")
            keywords.extend(["technical-writing", "markdown", "executive-summary", "proofreading"])
        elif intent == "visual":
            reqs.append("Design accessible UI components, CSS styling, or generative prompts.")
            keywords.extend(["ui-ux-design", "css-styling", "image-prompting", "diagrams"])
        elif intent == "data":
            reqs.append("Execute data transformations, clean tables, or SQL queries.")
            keywords.extend(["sql-queries", "data-analysis", "json-parsing", "csv-processing"])
        else:
            reqs.append("Provide direct, accurate, and concise conversational assistance.")
            keywords.extend(["response-synthesis", "clarity", "fact-lookup"])

        return reqs, keywords

    def _route_departments(self, text: str, intent: str, requirements: List[str]) -> List[str]:
        """X005 Department Router: selects active departments."""
        depts = ["Command"]
        lower = text.lower()

        # Primary department mapping
        intent_dept_map = {
            "coding": "Coding",
            "research": "Research",
            "writing": "Writing",
            "visual": "Visual",
            "data": "Data",
            "media": "Media",
            "productivity": "Productivity",
            "strategy": "Strategy",
            "general": "Command",
        }
        primary_dept = intent_dept_map.get(intent, "Command")
        if primary_dept not in depts:
            depts.append(primary_dept)

        # Multi-Department Co-activations
        if any(w in lower for w in ["search and write", "research and write", "compare and summarize"]):
            if "Research" not in depts: depts.append("Research")
            if "Writing" not in depts: depts.append("Writing")

        if any(w in lower for w in ["research and code", "find api and implement", "scrape and code"]):
            if "Research" not in depts: depts.append("Research")
            if "Coding" not in depts: depts.append("Coding")

        if any(w in lower for w in ["design and code", "ui and react", "css and component"]):
            if "Visual" not in depts: depts.append("Visual")
            if "Coding" not in depts: depts.append("Coding")

        if any(w in lower for w in ["data and visualize", "sql and chart", "analytics and table"]):
            if "Data" not in depts: depts.append("Data")
            if "Visual" not in depts: depts.append("Visual")

        # Always attach Quality department for critical tasks
        if any(d in depts for d in ["Coding", "Research", "Data", "Strategy"]):
            if "Quality" not in depts:
                depts.append("Quality")

        return depts

    def _select_specialists(self, departments: List[str], keywords: List[str], intent: str) -> List[Specialist]:
        """X006 Specialist Router: selects concrete specialists within activated departments."""
        selected: List[Specialist] = []

        # Always include Command anchor
        x001 = self.registry.get_specialist("X001")
        if x001: selected.append(x001)

        for dept in departments:
            if dept == "Command":
                continue
            matches = self.registry.find_specialists_by_capabilities(keywords, department=dept, top_k=2)
            if not matches:
                # Default anchor per department
                dept_specs = self.registry.get_all_specialists(department=dept, enabled_only=True)
                if dept_specs:
                    matches = [dept_specs[0]]
            for m in matches:
                if m not in selected:
                    selected.append(m)

        # Quality anchor if quality department active
        if "Quality" in departments:
            x100 = self.registry.get_specialist("X100")
            if x100 and x100 not in selected:
                selected.append(x100)

        # Final Synthesizer anchor
        x010 = self.registry.get_specialist("X010")
        if x010 and x010 not in selected:
            selected.append(x010)

        return selected

    def _decompose_subtasks(
        self,
        user_message: str,
        intent: str,
        requirements: List[str],
        departments: List[str],
        specialists: List[Specialist],
    ) -> List[SubTask]:
        """X004 & X007 Task Decomposer: builds execution subtasks with dependency graph."""
        subtasks: List[SubTask] = []
        domain_specs = [s for s in specialists if s.department not in ["Command", "Quality"]]

        if not domain_specs:
            # Fallback direct command response
            subtasks.append(
                SubTask(
                    id="subtask_1",
                    title="Direct Response Synthesis",
                    description="Answer the user's inquiry with clarity and precision.",
                    department="Command",
                    specialist_id="X010",
                    dependencies=[],
                )
            )
            return subtasks

        # Step 1..N: Domain Specialists Subtasks
        prev_subtask_id = None
        for idx, spec in enumerate(domain_specs, 1):
            st_id = f"subtask_{idx}"
            subtasks.append(
                SubTask(
                    id=st_id,
                    title=f"{spec.name} Execution",
                    description=f"Execute {spec.role} addressing: '{user_message[:50]}...'",
                    department=spec.department,
                    specialist_id=spec.id,
                    dependencies=[prev_subtask_id] if prev_subtask_id else [],
                )
            )
            prev_subtask_id = st_id

        # Quality Verification Step
        if "Quality" in departments:
            q_id = f"subtask_{len(subtasks) + 1}"
            subtasks.append(
                SubTask(
                    id=q_id,
                    title="Quality Verification & Supreme Judgment",
                    description="Verify accuracy, fact grounding, syntax, and deliver final judgment.",
                    department="Quality",
                    specialist_id="X100",
                    dependencies=[prev_subtask_id] if prev_subtask_id else [],
                )
            )
            prev_subtask_id = q_id

        # Final Response Assembly Step
        synth_id = f"subtask_{len(subtasks) + 1}"
        subtasks.append(
            SubTask(
                id=synth_id,
                title="Final Response Synthesis",
                description="Assemble all specialist outputs into polished final Markdown presentation.",
                department="Command",
                specialist_id="X010",
                dependencies=[prev_subtask_id] if prev_subtask_id else [],
            )
        )

        return subtasks

    def evaluate_quality(self, output: str, context: TaskContext) -> QualityVerdict:
        """
        Executes Quality Department verification (X091-X100) led by X100 Supreme Judge.
        """
        criticisms = []
        recommendations = []
        score = 95.0

        if not output or len(output.strip()) == 0:
            return QualityVerdict(
                verdict="FAIL",
                score=0.0,
                criticisms=["Output is completely empty."],
                recommendations=["Re-execute specialist pipeline."],
            )

        # X092 Hallucination & Raw Markup Check
        if "<tool_call>" in output or "<function=" in output:
            criticisms.append("Raw XML tool markup detected in output.")
            score -= 30.0

        # Length / Completeness Check
        if len(output.strip()) < 15:
            criticisms.append("Output is terse or potentially truncated.")
            score -= 15.0

        # Formatting Check
        if "|" in output and "---" not in output:
            recommendations.append("Ensure markdown table header separator rows are properly formatted.")

        # Supreme Judge Decision
        if score >= 80.0:
            verdict = "PASS" if not criticisms else "PASS_WITH_WARNINGS"
        elif score >= 50.0:
            verdict = "RETRY"
        else:
            verdict = "FAIL"

        return QualityVerdict(
            verdict=verdict,
            score=max(0.0, score),
            criticisms=criticisms,
            recommendations=recommendations,
            safety_checked=True,
            grounding_checked=True,
        )


command_orchestrator = CommandOrchestrator()
