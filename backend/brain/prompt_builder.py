from typing import Dict, List, Optional

from brain.personality import SYSTEM_PROMPT


def build_prompt(
    user_message: str,
    history: Optional[List[Dict[str, str]]] = None,
):
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
    ]

    if history:
        messages.extend(history)

    messages.append({
        "role": "user",
        "content": user_message,
    })

    return messages
