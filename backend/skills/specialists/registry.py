"""
Central Specialist Registry for CRUZ (X001–X100).
Manages discovery, capability-based lookups, department aggregation,
and SQLite state persistence for all 100 specialists.
"""
import sqlite3
from typing import List, Dict, Any, Optional
from utils.logger import get_logger
from config import MEMORY_DB_PATH

from .models import Specialist
from .command import COMMAND_SPECIALISTS
from .coding import CODING_SPECIALISTS
from .research import RESEARCH_SPECIALISTS
from .writing import WRITING_SPECIALISTS
from .visual import VISUAL_SPECIALISTS
from .data import DATA_SPECIALISTS
from .media import MEDIA_SPECIALISTS
from .productivity import PRODUCTIVITY_SPECIALISTS
from .strategy import STRATEGY_SPECIALISTS
from .quality import QUALITY_SPECIALISTS

logger = get_logger("skills.specialists.registry")

ALL_DEPARTMENTS = [
    "Command",
    "Coding",
    "Research",
    "Writing",
    "Visual",
    "Data",
    "Media",
    "Productivity",
    "Strategy",
    "Quality",
]


class SpecialistRegistry:
    """
    Central singleton registry managing the complete 100-specialist catalog.
    """

    def __init__(self, db_path: str = MEMORY_DB_PATH):
        self.db_path = db_path
        self._specialists: Dict[str, Specialist] = {}
        self._department_map: Dict[str, List[Specialist]] = {dept: [] for dept in ALL_DEPARTMENTS}

        self._load_all_specialists()
        self._init_db()
        self._load_saved_states()

    def _load_all_specialists(self):
        """Loads and indexes all 100 specialists from department definitions."""
        all_specs: List[Specialist] = (
            COMMAND_SPECIALISTS
            + CODING_SPECIALISTS
            + RESEARCH_SPECIALISTS
            + WRITING_SPECIALISTS
            + VISUAL_SPECIALISTS
            + DATA_SPECIALISTS
            + MEDIA_SPECIALISTS
            + PRODUCTIVITY_SPECIALISTS
            + STRATEGY_SPECIALISTS
            + QUALITY_SPECIALISTS
        )

        for spec in all_specs:
            self._specialists[spec.id] = spec
            if spec.department in self._department_map:
                self._department_map[spec.department].append(spec)

        logger.info(f"SpecialistRegistry initialized with {len(self._specialists)} specialists across {len(self._department_map)} departments.")

    def _init_db(self):
        """Creates the specialist state persistence table if not exists."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS specialist_states (
                        specialist_id TEXT PRIMARY KEY,
                        enabled INTEGER NOT NULL DEFAULT 1,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                conn.commit()
        except Exception as e:
            logger.warning(f"Failed to initialize specialist_states table: {e}")

    def _load_saved_states(self):
        """Loads persisted toggle states from SQLite."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT specialist_id, enabled FROM specialist_states")
                rows = cursor.fetchall()
                for sid, enabled in rows:
                    if sid in self._specialists:
                        spec = self._specialists[sid]
                        if not spec.is_core:
                            spec.enabled = bool(enabled)
        except Exception as e:
            logger.warning(f"Failed to load specialist toggle states: {e}")

    def get_specialist(self, specialist_id: str) -> Optional[Specialist]:
        """Returns a specialist by ID (e.g. 'X001')."""
        return self._specialists.get(specialist_id.upper())

    def get_all_specialists(self, department: Optional[str] = None, enabled_only: bool = False) -> List[Specialist]:
        """Returns all specialists, optionally filtered by department or enabled status."""
        specs = list(self._specialists.values())
        if department:
            dept_normalized = department.strip().capitalize()
            specs = [s for s in specs if s.department.lower() == dept_normalized.lower()]
        if enabled_only:
            specs = [s for s in specs if s.enabled]
        return specs

    def get_departments(self) -> List[Dict[str, Any]]:
        """Returns summary statistics for all 10 departments."""
        result = []
        for dept in ALL_DEPARTMENTS:
            dept_specs = self._department_map.get(dept, [])
            enabled_count = sum(1 for s in dept_specs if s.enabled)
            result.append({
                "name": dept,
                "total_specialists": len(dept_specs),
                "enabled_specialists": enabled_count,
                "specialist_ids": [s.id for s in dept_specs],
            })
        return result

    def set_specialist_enabled(self, specialist_id: str, enabled: bool) -> bool:
        """Toggles a specialist on or off and persists state to SQLite."""
        spec = self.get_specialist(specialist_id)
        if not spec:
            return False
        if spec.is_core:
            logger.warning(f"Specialist '{spec.id}' ({spec.name}) is core and cannot be disabled.")
            return False

        spec.enabled = enabled
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO specialist_states (specialist_id, enabled, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(specialist_id) DO UPDATE SET
                        enabled=excluded.enabled,
                        updated_at=CURRENT_TIMESTAMP
                    """,
                    (spec.id, 1 if enabled else 0)
                )
                conn.commit()
            logger.info(f"Specialist '{spec.id}' ({spec.name}) state changed to enabled={enabled}")
            return True
        except Exception as e:
            logger.error(f"Failed to persist specialist state for {spec.id}: {e}")
            return False

    def find_specialists_by_capabilities(
        self,
        required_capabilities: List[str],
        department: Optional[str] = None,
        top_k: int = 5
    ) -> List[Specialist]:
        """
        Finds and ranks specialists based on matching capability keywords.
        """
        candidates = self.get_all_specialists(department=department, enabled_only=True)
        scored: List[tuple[int, Specialist]] = []

        req_set = {c.lower().strip() for c in required_capabilities if c.strip()}

        for spec in candidates:
            score = 0
            spec_caps = {c.lower().strip() for c in spec.capabilities}
            # Direct overlap
            overlap = req_set.intersection(spec_caps)
            score += len(overlap) * 3

            # Substring matching
            for req in req_set:
                for cap in spec_caps:
                    if req in cap or cap in req:
                        score += 1
                if req in spec.name.lower() or req in spec.role.lower():
                    score += 2

            if score > 0:
                scored.append((score, spec))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:top_k]]

    def search_specialists(self, query: str) -> List[Specialist]:
        """Performs a full-text search across specialist names, IDs, departments, and roles."""
        clean_q = query.lower().strip()
        if not clean_q:
            return list(self._specialists.values())

        matched = []
        for s in self._specialists.values():
            if (
                clean_q in s.id.lower()
                or clean_q in s.name.lower()
                or clean_q in s.role.lower()
                or clean_q in s.department.lower()
                or any(clean_q in cap.lower() for cap in s.capabilities)
            ):
                matched.append(s)
        return matched


specialist_registry = SpecialistRegistry()
