import json
from typing import Dict, List

from memory.long_term_memory import CATEGORIES
from services.ollama import chat

_EXTRACTION_SYSTEM_PROMPT = f"""
You are a silent fact-extraction filter for CRUZ, a personal AI assistant.
You are NOT talking to the user — you are analyzing ONE message to decide
whether it contains a durable fact worth remembering long-term.

Save a fact ONLY if it fits one of these categories:
- identity: name, age, location, education
- preferences: favorite language, IDE, game, music, framework
- projects: something the user is building or working on
- goals: something the user wants to achieve
- devices: laptop, GPU, phone, microphone the user owns
- coding_preferences: languages/stacks/tools the user codes with

Do NOT extract facts from:
- Greetings, small talk, jokes, banter
- Temporary states ("I'm tired", "I'm drinking tea", "I'm bored")
- Questions the user is asking
- Anything not stated as a fact about the user themselves

Respond with ONLY raw JSON (no markdown fences, no commentary), in exactly
this shape:
{{"facts": [{{"category": "preferences", "key": "favorite_language", "value": "Python"}}]}}

If nothing is worth remembering, respond with exactly:
{{"facts": []}}

Rules for each fact:
- "category" must be one of: {", ".join(CATEGORIES)}
- "key" must be short snake_case, e.g. favorite_language, favorite_ide, location, current_project
- "value" must be the plain fact, not a full sentence
- A single message can contain multiple facts — extract all of them
"""


async def extract_facts(user_message: str) -> List[Dict[str, str]]:
    """
    Ask the LLM whether `user_message` contains anything worth
    remembering long-term, and if so, extract it as structured
    (category, key, value) triples.

    Returns an empty list for small talk, questions, temporary states,
    or anything else that isn't a durable fact about the user. Never
    raises — extraction failures should never take down the main chat
    flow, they should just mean "nothing got saved this turn".
    """
    messages = [
        {"role": "system", "content": _EXTRACTION_SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    try:
        raw = await chat(messages)
    except Exception:
        return []

    return _parse_facts(raw)


def _parse_facts(raw: str) -> List[Dict[str, str]]:
    raw = raw.strip()

    # Small local models sometimes wrap JSON in ```json fences despite
    # being told not to — strip those before parsing.
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return []

    facts = data.get("facts", []) if isinstance(data, dict) else data
    if not isinstance(facts, list):
        return []

    cleaned: List[Dict[str, str]] = []
    for fact in facts:
        if not isinstance(fact, dict):
            continue

        category = str(fact.get("category", "")).strip().lower()
        key = str(fact.get("key", "")).strip().lower().replace(" ", "_")
        value = str(fact.get("value", "")).strip()

        if category not in CATEGORIES or not key or not value:
            continue

        cleaned.append({"category": category, "key": key, "value": value})

    return cleaned
