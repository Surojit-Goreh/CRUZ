import json
from pathlib import Path
from typing import Dict, List, Optional

from brain.personality import SYSTEM_PROMPT

_DEBUG_DUMP_PATH = Path(__file__).resolve().parent.parent / "data" / "debug_last_prompt.json"


def build_prompt(
    user_message: str,
    history: Optional[List[Dict[str, str]]] = None,
    long_term_facts: Optional[List[Dict[str, str]]] = None,
):
    system_content = SYSTEM_PROMPT

    if long_term_facts:
        system_content += "\n\n" + _format_facts(long_term_facts)

    messages = [
        {
            "role": "system",
            "content": system_content,
        },
    ]

    if history:
        messages.extend(history)

    messages.append({
        "role": "user",
        "content": user_message,
    })

    _dump_debug(messages, long_term_facts)

    return messages


def _dump_debug(messages: List[Dict[str, str]], long_term_facts: Optional[List[Dict[str, str]]]) -> None:
    """
    Write the exact prompt just built to disk, overwriting the previous
    one. This exists so you can answer "did the facts actually make it
    into the prompt, or is the model just ignoring them?" by looking at
    a file instead of guessing — check backend/data/debug_last_prompt.json
    right after asking CRUZ something. If the fact you expect is missing
    from "system_prompt" there, it's a retrieval bug. If it IS there and
    CRUZ still got it wrong, it's a model/prompt-following issue, not a
    plumbing issue.
    """
    try:
        _DEBUG_DUMP_PATH.parent.mkdir(parents=True, exist_ok=True)
        _DEBUG_DUMP_PATH.write_text(
            json.dumps(
                {
                    "fact_count": len(long_term_facts) if long_term_facts else 0,
                    "facts": long_term_facts or [],
                    "full_messages_sent_to_ollama": messages,
                },
                indent=2,
            )
        )
    except Exception:
        # Debug output should never break the actual chat flow.
        pass


def _format_facts(facts: List[Dict[str, str]]) -> str:
    """
    Render stored facts as a block appended to the system prompt.

    Grouped by category so the model sees structure, not a flat dump.
    No embeddings/relevance ranking yet (Phase 4 doesn't have that) —
    every known fact goes in every time, since the total count is small
    for a single-user assistant.
    """
    by_category: Dict[str, List[str]] = {}
    for fact in facts:
        by_category.setdefault(fact["category"], []).append(
            f"- {fact['key']}: {fact['value']}"
        )

    lines = [
        "=====================================================",
        "WHAT YOU KNOW ABOUT SUROJIT (long-term memory) — TRUE FACTS",
        "=====================================================",
    ]
    for category, items in by_category.items():
        lines.append(f"\n{category.replace('_', ' ').title()}:")
        lines.extend(items)

    lines.append(
        "\nThese are confirmed facts, not guesses. If Surojit asks something "
        "a fact above already answers — his name, where he lives, what he's "
        "building, what he prefers — answer it directly and confidently using "
        "that fact. NEVER ask him to (re)state information already listed "
        "above; that makes it look like you forgot, which you didn't. Use "
        "these naturally, like a friend would, not like you're reading a "
        "profile page, and don't mention 'memory' or 'retrieving' out loud."
    )
    return "\n".join(lines)