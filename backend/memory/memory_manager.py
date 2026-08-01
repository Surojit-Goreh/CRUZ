from typing import Dict, List, Optional

from config import MEMORY_WINDOW_SIZE
from memory.chat_memory import ChatMemory

DEFAULT_SESSION_ID = "default"


class MemoryManager:
    """
    Keeps one ChatMemory per session_id.

    Right now the frontend only ever runs one conversation at a time, so
    everything falls back to DEFAULT_SESSION_ID unless a session_id is
    explicitly passed in. This is here so wiring up multi-chat later
    (the Sidebar's "New Chat" / "History" buttons) is a frontend-only
    change — the backend already supports it.
    """

    def __init__(self):
        self._sessions: Dict[str, ChatMemory] = {}

    def _get_or_create(self, session_id: str) -> ChatMemory:
        if session_id not in self._sessions:
            self._sessions[session_id] = ChatMemory(max_messages=MEMORY_WINDOW_SIZE)
        return self._sessions[session_id]

    def add_message(self, session_id: str, role: str, content: str) -> None:
        self._get_or_create(session_id).add_message(role, content)

    def get_messages(self, session_id: str) -> List[Dict[str, str]]:
        return self._get_or_create(session_id).get_messages()

    def clear(self, session_id: str) -> None:
        if session_id in self._sessions:
            self._sessions[session_id].clear()

    def reset(self, session_id: Optional[str] = None) -> None:
        """
        Reset one session, or wipe every session if none is given.
        """
        if session_id is None:
            self._sessions.clear()
        elif session_id in self._sessions:
            self._sessions[session_id].reset()


# One instance shared across the whole backend process.
memory_manager = MemoryManager()
