import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from config import MEMORY_DB_PATH

_DB_PATH = Path(MEMORY_DB_PATH)
_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Facts CRUZ is allowed to remember. Keeping this closed (rather than
# letting the extractor invent categories) is what keeps memory tidy —
# see extractor.py, which enforces the same list.
CATEGORIES = (
    "identity",
    "preferences",
    "projects",
    "goals",
    "devices",
    "coding_preferences",
)


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS facts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                category    TEXT NOT NULL,
                key         TEXT NOT NULL,
                value       TEXT NOT NULL,
                updated_at  TEXT NOT NULL,
                UNIQUE(category, key)
            )
            """
        )


_init_db()


class LongTermMemory:
    """
    Persistent fact storage backed by SQLite.

    Facts are stored as (category, key, value) triples, e.g.
    ("preferences", "favorite_language", "Python"). Saving a fact under
    a category+key that already exists overwrites the old value — CRUZ
    only ever keeps the latest version of a fact, not a history of it.

    Deliberately synchronous: sqlite3 calls against a small local file
    are effectively instant, and keeping this simple makes it easy to
    debug — same philosophy as ChatMemory/MemoryManager elsewhere.
    """

    def save_fact(self, category: str, key: str, value: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO facts (category, key, value, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(category, key)
                DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """,
                (category, key, value, now),
            )

    def get_fact(self, category: str, key: str) -> Optional[str]:
        with _connect() as conn:
            row = conn.execute(
                "SELECT value FROM facts WHERE category = ? AND key = ?",
                (category, key),
            ).fetchone()
        return row["value"] if row else None

    def get_all_facts(self) -> List[Dict[str, str]]:
        with _connect() as conn:
            rows = conn.execute(
                "SELECT category, key, value, updated_at FROM facts ORDER BY category, key"
            ).fetchall()
        return [dict(row) for row in rows]

    def get_facts_by_category(self, category: str) -> List[Dict[str, str]]:
        with _connect() as conn:
            rows = conn.execute(
                "SELECT category, key, value, updated_at FROM facts WHERE category = ? ORDER BY key",
                (category,),
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_fact(self, category: str, key: str) -> bool:
        with _connect() as conn:
            cur = conn.execute(
                "DELETE FROM facts WHERE category = ? AND key = ?",
                (category, key),
            )
        return cur.rowcount > 0

    def delete_all(self) -> None:
        with _connect() as conn:
            conn.execute("DELETE FROM facts")


# One instance shared across the whole backend process — same pattern
# as memory_manager in memory_manager.py.
long_term_memory = LongTermMemory()
