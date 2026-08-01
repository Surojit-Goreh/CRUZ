from collections import deque
from typing import Dict, List


class ChatMemory:
    """
    Holds the message history for a single conversation.

    Uses a sliding window: once max_messages is reached, the oldest
    message is dropped as a new one comes in. Roles are "user" and
    "assistant" — the system prompt is NOT stored here, prompt_builder
    adds that separately.
    """

    def __init__(self, max_messages: int = 20):
        self.max_messages = max_messages
        self._messages: deque[Dict[str, str]] = deque(maxlen=max_messages)

    def add_message(self, role: str, content: str) -> None:
        self._messages.append({
            "role": role,
            "content": content,
        })

    def get_messages(self) -> List[Dict[str, str]]:
        return list(self._messages)

    def clear(self) -> None:
        self._messages.clear()

    def reset(self) -> None:
        self.clear()
