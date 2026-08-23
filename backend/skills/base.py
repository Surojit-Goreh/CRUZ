from abc import ABC, abstractmethod
from typing import List, Dict, Any, Callable, Optional


class BaseSkill(ABC):
    """
    Abstract Base Class for all CRUZ Skills.
    A skill encapsulates a set of OpenAI-compatible tool schemas, their underlying
    Python execution functions, task category affinities, trigger keywords,
    and optional system prompt guidance.
    """
    name: str                          # Unique identifier (e.g. "filesystem", "browser")
    display_name: str                  # Human-readable title for UI (e.g. "File Operations")
    description: str                   # Detailed description of what this skill provides
    icon: str = "Puzzle"               # Lucide icon name for frontend rendering
    version: str = "1.0.0"
    is_core: bool = False              # If True, cannot be disabled (always active)
    enabled_by_default: bool = True    # Initial state if not yet saved in SQLite

    # Task categories where this skill should automatically be loaded:
    # "coding", "reasoning", "writing", "vision", "general"
    task_categories: List[str] = ["coding", "reasoning", "writing", "vision", "general"]

    # Keyword triggers that will dynamically activate this skill even if task category doesn't match
    trigger_keywords: List[str] = []

    @abstractmethod
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """
        Return the OpenAI function-calling schemas for all tools in this skill.
        """
        return []

    @abstractmethod
    def get_tool_registry(self) -> Dict[str, Callable]:
        """
        Return a dictionary mapping tool names (strings) to callable Python functions.
        """
        return {}

    def get_prompt_instructions(self) -> Optional[str]:
        """
        Optional system prompt guidelines or workflow rules injected when this skill is active.
        """
        return None

    def to_dict(self, enabled: bool = True) -> Dict[str, Any]:
        """
        Serialize skill metadata for the API and frontend UI.
        """
        schemas = self.get_tool_schemas()
        return {
            "name": self.name,
            "display_name": getattr(self, "display_name", self.name.title()),
            "description": getattr(self, "description", ""),
            "icon": getattr(self, "icon", "Puzzle"),
            "version": getattr(self, "version", "1.0.0"),
            "is_core": getattr(self, "is_core", False),
            "enabled": True if getattr(self, "is_core", False) else enabled,
            "task_categories": getattr(self, "task_categories", []),
            "trigger_keywords": getattr(self, "trigger_keywords", []),
            "tool_count": len(schemas),
            "tools": [s.get("function", {}).get("name") for s in schemas if "function" in s],
        }
