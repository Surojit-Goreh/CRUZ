import importlib
import inspect
import pkgutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable

from config import MEMORY_DB_PATH
from skills.base import BaseSkill
from utils.logger import get_logger

logger = get_logger("skills.manager")

_DB_PATH = Path(MEMORY_DB_PATH)
_DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _connect_db() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_skills_table():
    with _connect_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS skill_states (
                skill_name  TEXT PRIMARY KEY,
                enabled     INTEGER NOT NULL DEFAULT 1,
                updated_at  TEXT
            )
            """
        )


_init_skills_table()


class SkillManager:
    """
    Central Manager for CRUZ Skills:
    - Auto-discovers built-in and custom skills.
    - Persists user enable/disable preferences in SQLite.
    - Selects relevant skills dynamically based on task category & keyword triggers.
    - Provides merged tool schemas and tool registries to the LLM & Executor.
    """

    def __init__(self):
        self._skills: Dict[str, BaseSkill] = {}
        self._discover_skills()

    def _discover_skills(self):
        """
        Dynamically imports and instantiates all BaseSkill subclasses
        from skills.built_in and skills.custom packages.
        """
        import skills.built_in

        # 1. Discover Built-in Skills
        for _, module_name, _ in pkgutil.iter_modules(skills.built_in.__path__):
            try:
                full_module_name = f"skills.built_in.{module_name}"
                mod = importlib.import_module(full_module_name)
                for _, obj in inspect.getmembers(mod, inspect.isclass):
                    if issubclass(obj, BaseSkill) and obj is not BaseSkill:
                        instance = obj()
                        self.register_skill(instance)
            except Exception as e:
                logger.error(f"Failed to load built-in skill module '{module_name}': {e}")

        # 2. Discover Custom Skills (if skills/custom folder exists)
        custom_path = Path(__file__).resolve().parent / "custom"
        if custom_path.exists() and custom_path.is_dir():
            try:
                import skills.custom
                for _, module_name, _ in pkgutil.iter_modules(skills.custom.__path__):
                    try:
                        full_module_name = f"skills.custom.{module_name}"
                        mod = importlib.import_module(full_module_name)
                        for _, obj in inspect.getmembers(mod, inspect.isclass):
                            if issubclass(obj, BaseSkill) and obj is not BaseSkill:
                                instance = obj()
                                self.register_skill(instance)
                    except Exception as e:
                        logger.error(f"Failed to load custom skill module '{module_name}': {e}")
            except Exception as e:
                logger.debug(f"Custom skills package not configured: {e}")

        logger.info(f"SkillManager initialized with {len(self._skills)} skills: {list(self._skills.keys())}")

    def register_skill(self, skill: BaseSkill):
        """Registers a BaseSkill instance."""
        self._skills[skill.name] = skill
        logger.debug(f"Registered skill '{skill.name}' ({skill.display_name})")

    def get_skill(self, name: str) -> Optional[BaseSkill]:
        return self._skills.get(name)

    def is_skill_enabled(self, name: str) -> bool:
        skill = self.get_skill(name)
        if not skill:
            return False
        if skill.is_core:
            return True

        with _connect_db() as conn:
            row = conn.execute("SELECT enabled FROM skill_states WHERE skill_name = ?", (name,)).fetchone()
            if row is not None:
                return bool(row["enabled"])
            return skill.enabled_by_default

    def set_skill_enabled(self, name: str, enabled: bool) -> bool:
        skill = self.get_skill(name)
        if not skill:
            return False
        if skill.is_core:
            return True  # Core skills cannot be disabled

        now = datetime.now(timezone.utc).isoformat()
        with _connect_db() as conn:
            conn.execute(
                """
                INSERT INTO skill_states (skill_name, enabled, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(skill_name) DO UPDATE SET
                    enabled = excluded.enabled,
                    updated_at = excluded.updated_at
                """,
                (name, 1 if enabled else 0, now),
            )
        logger.info(f"Skill '{name}' state changed to enabled={enabled}")
        return True

    def get_all_skills(self) -> List[Dict[str, Any]]:
        """Returns list of all skills with their active metadata and enabled status."""
        result = []
        for name, skill in self._skills.items():
            enabled = self.is_skill_enabled(name)
            result.append(skill.to_dict(enabled=enabled))
        return result

    def get_active_skills(
        self,
        task_category: Optional[str] = None,
        user_message: Optional[str] = None,
    ) -> List[BaseSkill]:
        """
        Dynamically resolves active skills based on:
        1. User enable/disable preference in SQLite.
        2. Task category alignment (coding, reasoning, writing, vision, general).
        3. Trigger keyword matching in user message (fallback override).
        4. Core skills (always included).
        """
        active: List[BaseSkill] = []
        msg_lower = (user_message or "").lower()

        for name, skill in self._skills.items():
            if not self.is_skill_enabled(name):
                continue

            # Core skills are always active
            if skill.is_core:
                active.append(skill)
                continue

            # If no category is passed, include all enabled skills
            if not task_category:
                active.append(skill)
                continue

            # 1. Match by task category
            category_match = task_category in skill.task_categories

            # 2. Match by trigger keywords in user message
            keyword_match = False
            if msg_lower and skill.trigger_keywords:
                for kw in skill.trigger_keywords:
                    if kw in msg_lower:
                        keyword_match = True
                        break

            if category_match or keyword_match:
                active.append(skill)

        return active

    def get_active_tool_schemas(
        self,
        task_category: Optional[str] = None,
        user_message: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Returns merged OpenAI function schemas for all active skills without duplicates.
        """
        active_skills = self.get_active_skills(task_category=task_category, user_message=user_message)
        schemas = []
        seen_names = set()

        for skill in active_skills:
            for s in skill.get_tool_schemas():
                name = s.get("function", {}).get("name") if "function" in s else s.get("name")
                if name and name not in seen_names:
                    schemas.append(s)
                    seen_names.add(name)

        return schemas

    def get_active_tool_registry(
        self,
        task_category: Optional[str] = None,
        user_message: Optional[str] = None,
    ) -> Dict[str, Callable]:
        """
        Returns merged {tool_name: callable} mapping for all active skills.
        """
        active_skills = self.get_active_skills(task_category=task_category, user_message=user_message)
        registry: Dict[str, Callable] = {}
        for skill in active_skills:
            registry.update(skill.get_tool_registry())
        return registry

    def get_active_prompt_instructions(
        self,
        task_category: Optional[str] = None,
        user_message: Optional[str] = None,
    ) -> str:
        """
        Returns concatenated prompt guidelines from all active skills.
        """
        active_skills = self.get_active_skills(task_category=task_category, user_message=user_message)
        blocks = []
        for skill in active_skills:
            instr = skill.get_prompt_instructions()
            if instr and instr.strip():
                blocks.append(instr.strip())
        return "\n\n".join(blocks)

    def get_tool(self, tool_name: str) -> Optional[Callable]:
        """
        Resolves a tool function by name across all enabled skills.
        """
        for name, skill in self._skills.items():
            if self.is_skill_enabled(name):
                reg = skill.get_tool_registry()
                if tool_name in reg:
                    return reg[tool_name]
        return None

    @property
    def specialist_registry(self):
        """Returns the central 100-Specialist Registry."""
        from skills.specialists.registry import specialist_registry
        return specialist_registry

    @property
    def orchestrator(self):
        """Returns the Command Orchestrator engine."""
        from skills.specialists.orchestrator import command_orchestrator
        return command_orchestrator


skill_manager = SkillManager()
