from brain.personality import SYSTEM_PROMPT


def build_prompt(user_message: str):
    return [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": user_message,
        },
    ]