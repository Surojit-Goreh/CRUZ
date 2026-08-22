import re
from typing import List, Dict, Any, Optional

# Coding keywords & indicators
CODE_PATTERNS = [
    r"```",                                      # Code fences
    r"\b(def|class|function|const|let|var)\b",    # Language definitions
    r"\b(import|from|require|package)\b",         # Imports
    r"\b(return|yield|async|await)\b",           # Async / control
    r"\b(traceback|stacktrace|exception|syntaxerror|typeerror|nullpointer)\b", # Errors
    r"\b(sql|select|insert|update|delete|from|where|join)\b",                   # Database
    r"\b(html|css|javascript|typescript|python|rust|golang|c\+\+|java)\b",    # Languages
    r"\.(py|ts|tsx|js|jsx|html|css|json|rs|go|cpp|c|java|sh|bat|md)\b",       # File extensions
    r"\b(bug|fix this code|refactor|optimize this|debug|algorithm|api endpoint)\b",
]

# Deep Reasoning, Math & Logic keywords
REASONING_PATTERNS = [
    r"\b(solve|math|calculate|step[- ]by[- ]step|prove|proof|puzzle|riddle|logic|derive|deduce)\b",
    r"\b(think deeply|analyze this problem|complex problem|probability|algebra|calculus|theorem)\b",
    r"\b(compare and contrast|pros and cons|architectural trade-offs|root cause analysis)\b",
    r"\b(plan the architecture|system design|break this down into steps|stepwise)\b",
]

# Creative & writing keywords
WRITING_PATTERNS = [
    r"\b(write an essay|write a blog|write a story|write a poem|write a script)\b",
    r"\b(creative writing|draft an email|draft a letter|rewrite this|rephrase)\b",
    r"\b(summarize this article|novel|character|narrative|dialogue|draft a post)\b",
]

# Vision keywords (when image is present or user asks to analyze/describe visual input)
VISION_PATTERNS = [
    r"\b(look at this image|describe this image|what is in this picture|photo|screenshot)\b",
    r"\b(read this diagram|ocr|analyze this visual|chart in the image)\b",
]


def classify_task(messages: List[Dict[str, Any]]) -> str:
    """
    Fast rule-based task classifier for dynamic multi-provider routing.
    Categories: 'vision', 'coding', 'reasoning', 'writing', 'general'
    """
    if not messages:
        return "general"

    # 1. Check for vision / image attachments in the latest message or history
    for msg in reversed(messages):
        content = msg.get("content")
        # Check for OpenAI-style multimodal parts list: [{"type": "image_url", ...}]
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") in ("image_url", "image"):
                    return "vision"

    # Extract raw text from the latest user message
    user_text = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            content = msg.get("content")
            if isinstance(content, str):
                user_text = content
                break
            elif isinstance(content, list):
                # Extract text parts
                text_parts = [p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text"]
                user_text = " ".join(text_parts)
                break

    if not user_text:
        return "general"

    lower_text = user_text.lower()

    # 2. Check for explicit vision requests
    for pattern in VISION_PATTERNS:
        if re.search(pattern, lower_text, re.IGNORECASE):
            return "vision"

    # 3. Check for coding tasks
    code_matches = sum(1 for pattern in CODE_PATTERNS if re.search(pattern, lower_text, re.IGNORECASE))
    if code_matches >= 2 or "```" in user_text:
        return "coding"

    # 4. Check for deep reasoning / math / logic / planning
    for pattern in REASONING_PATTERNS:
        if re.search(pattern, lower_text, re.IGNORECASE):
            return "reasoning"

    # 5. Check for writing / creative drafting
    for pattern in WRITING_PATTERNS:
        if re.search(pattern, lower_text, re.IGNORECASE):
            return "writing"

    # 6. Default category
    return "general"


AGENT_MODE_INTENT_PATTERNS = {
    "image": [
        r"\b(image|vision)\s*(mode|agent|node)?\b",
        r"\b(change|switch|set|turn)\s*(your\s*)?(mode|node|agent)?\s*(to|on)?\s*(image|vision)\b",
        r"\bimage\s+mode\s+on\b",
    ],
    "plan": [
        r"\b(reasoning|resoning|plan|planning|deep reasoning)\s*(mode|agent|node)?\b",
        r"\b(change|switch|set|turn)\s*(your\s*)?(mode|node|agent)?\s*(to|on)?\s*(reasoning|resoning|plan|planning)\b",
        r"\breasoning\s+mode\s+on\b",
    ],
    "build": [
        r"\b(build|coding|code|developer|programmer)\s*(mode|agent|node)?\b",
        r"\b(change|switch|set|turn)\s*(your\s*)?(mode|node|agent)?\s*(to|on)?\s*(build|coding|code|developer)\b",
        r"\bcoding\s+mode\s+on\b",
    ],
    "writing": [
        r"\b(writing|writer|essay|blog)\s*(mode|agent|node)?\b",
        r"\b(change|switch|set|turn)\s*(your\s*)?(mode|node|agent)?\s*(to|on)?\s*(writing|writer)\b",
    ],
    "chat": [
        r"\b(chat|fast chat|speed|quick chat)\s*(mode|agent|node)?\b",
        r"\b(change|switch|set|turn)\s*(your\s*)?(mode|node|agent)?\s*(to|on)?\s*(chat|fast chat|speed)\b",
    ],
    "auto": [
        r"\b(auto|automatic|dispatcher)\s*(mode|agent|node)?\b",
        r"\b(change|switch|set|turn)\s*(your\s*)?(mode|node|agent)?\s*(to|on)?\s*(auto|automatic|default)\b",
    ],
}


def detect_agent_mode_intent(text: str) -> Optional[str]:
    """
    Detects if user is asking to change/switch their active agent mode.
    Returns the canonical mode name ('image', 'plan', 'build', 'writing', 'chat', 'auto') or None.
    """
    if not text:
        return None
    lower = text.strip().lower()

    # Must contain a switch indicator or explicit mode command
    is_switch_command = bool(
        re.search(r"\b(change|switch|set|turn|activate|enable|use)\b", lower)
        or re.search(r"\b(mode|node|agent)\b", lower)
    )
    if not is_switch_command:
        return None

    for mode, patterns in AGENT_MODE_INTENT_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, lower):
                return mode
    return None
