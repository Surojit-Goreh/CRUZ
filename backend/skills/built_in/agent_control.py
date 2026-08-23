from typing import List, Dict, Any, Callable, Optional
from skills.base import BaseSkill
from tools import system
from tools.schemas import AGENT_CONTROL_SCHEMAS


class AgentControlSkill(BaseSkill):
    name = "agent_control"
    display_name = "Agent Mode Controller"
    description = "Core system skill that allows dynamic switching between specialized agent modes (Auto, Coding, Reasoning, Vision, Writer, Fast Chat)."
    icon = "Sparkles"
    version = "1.0.0"
    is_core = True  # Core skill: always active, cannot be disabled
    enabled_by_default = True

    task_categories = ["coding", "reasoning", "writing", "vision", "general"]
    trigger_keywords = [
        "switch mode", "change mode", "agent mode", "coding mode",
        "reasoning mode", "vision mode", "writer mode", "fast chat", "auto mode"
    ]

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return AGENT_CONTROL_SCHEMAS

    def get_tool_registry(self) -> Dict[str, Callable]:
        return {
            "set_agent_mode": system.set_agent_mode,
        }

    def get_prompt_instructions(self) -> Optional[str]:
        return None
