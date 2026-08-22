import asyncio
import json
import uuid
from typing import Optional

from brain.prompt_builder import build_prompt
from memory.extractor import extract_facts
from memory.long_term_memory import long_term_memory
from memory.memory_manager import memory_manager, DEFAULT_SESSION_ID
from services.model_router import model_router
from executor.executor import run_tool_calls
from tools.registry import ALL_TOOL_SCHEMAS
from utils.logger import get_logger

logger = get_logger("brain.llm")

# Keeps references to fire-and-forget extraction tasks so asyncio
# doesn't garbage-collect them mid-flight; each task removes itself
# once done.
_background_tasks: set = set()

# Guards against infinite tool loops. Set high enough for multi-file project creation.
MAX_TOOL_ITERATIONS = 12


def _remember_in_background(user_message: str) -> None:
    """
    Kick off fact extraction without making the user wait for it.

    Extraction is itself an LLM call, so doing it inline would roughly
    double response time on a local 3B model. Firing it after the reply
    is already on its way keeps the chat feeling snappy.
    """
    task = asyncio.create_task(_remember(user_message))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def _remember(user_message: str) -> None:
    try:
        facts = await extract_facts(user_message)
        for fact in facts:
            long_term_memory.save_fact(fact["category"], fact["key"], fact["value"])
    except Exception:
        # A failed extraction should never crash anything — it just
        # means nothing new got saved this turn.
        pass
AGENT_MODE_TASK_MAP = {
    "build": "coding",
    "coding": "coding",
    "plan": "reasoning",
    "reasoning": "reasoning",
    "image": "vision",
    "vision": "vision",
    "writing": "writing",
    "writer": "writing",
    "chat": "general",
    "general": "general",
    "auto": None,
}


async def run_tool_pipeline(
    messages: list,
    task_category: Optional[str] = None,
    selected_model: Optional[str] = None,
) -> Optional[str]:
    """
    Executes the tool-calling loop. If the model asks to call a tool, runs it
    locally through the executor and appends both the tool call and tool result
    to `messages` — repeating until the model makes no more tool calls, or
    MAX_TOOL_ITERATIONS is hit.

    Returns:
      - The response content string if the model answered directly on round 0 (no tools called).
      - None if tool calls were executed, indicating `messages` now contains tool results.
    """
    for round_num in range(MAX_TOOL_ITERATIONS):
        message = await model_router.chat_with_tools(
            messages,
            tools=ALL_TOOL_SCHEMAS,
            task_category=task_category,
            selected_model=selected_model,
        )
        tool_calls = message.get("tool_calls")

        if not tool_calls:
            if round_num == 0:
                logger.info("model answered without calling any tool")
                return message.get("content", "")
            return None

        tool_names = [c.get("function", {}).get("name") for c in tool_calls]
        logger.info(f"round {round_num}: model called tool(s) {tool_names}")

        # Some providers (older Ollama versions especially) don't include
        # an `id` on each tool call at all. Synthesize one here, in the
        # single place every downstream consumer (history + executor)
        # reads from, so id and tool_call_id always agree no matter which
        # provider answered this round.
        for tc in tool_calls:
            if not tc.get("id"):
                tc["id"] = f"call_{uuid.uuid4().hex[:24]}"
            tc.setdefault("type", "function")

        history_message = dict(message)
        history_message["tool_calls"] = [
            {
                **tc,
                "function": {
                    **tc["function"],
                    "arguments": json.dumps(tc["function"].get("arguments", {})),
                },
            }
            for tc in tool_calls
        ]

        messages.append(history_message)
        messages.extend(await run_tool_calls(tool_calls))

    logger.warning(f"hit MAX_TOOL_ITERATIONS ({MAX_TOOL_ITERATIONS})")
    return None


async def generate_response(
    user_message: str,
    session_id: str = DEFAULT_SESSION_ID,
    agent_mode: Optional[str] = "auto",
    selected_model: Optional[str] = None,
) -> str:
    """
    Normal (non-streaming) response, with short-term + long-term memory
    and file-operation tool calling.
    """
    task_category = AGENT_MODE_TASK_MAP.get((agent_mode or "auto").lower())
    history = memory_manager.get_messages(session_id)
    facts = long_term_memory.get_all_facts()
    messages = build_prompt(user_message, history, facts)

    initial_reply = await run_tool_pipeline(messages, task_category=task_category, selected_model=selected_model)
    if initial_reply is not None:
        reply = initial_reply
    else:
        # Preserve the user's explicit model choice after tool execution too.
        reply = await model_router.chat(
            messages,
            task_category=task_category,
            selected_model=selected_model,
        )

    memory_manager.add_message(session_id, "user", user_message)
    memory_manager.add_message(session_id, "assistant", reply)

    _remember_in_background(user_message)

    return reply


async def generate_stream(
    user_message: str,
    session_id: str = DEFAULT_SESSION_ID,
    agent_mode: Optional[str] = "auto",
    selected_model: Optional[str] = None,
):
    """
    Streaming response, with short-term + long-term memory and file-operation
    tool calling. Fast-paths non-tool responses to avoid duplicate LLM calls.
    """
    task_category = AGENT_MODE_TASK_MAP.get((agent_mode or "auto").lower())
    history = memory_manager.get_messages(session_id)
    facts = long_term_memory.get_all_facts()
    messages = build_prompt(user_message, history, facts)

    initial_reply = await run_tool_pipeline(messages, task_category=task_category, selected_model=selected_model)

    full_reply = ""

    if initial_reply is not None:
        full_reply = initial_reply
        yield initial_reply
    else:
        async for chunk in model_router.stream_chat(messages, task_category=task_category, selected_model=selected_model):
            full_reply += chunk
            yield chunk

    memory_manager.add_message(session_id, "user", user_message)
    memory_manager.add_message(session_id, "assistant", full_reply)

    _remember_in_background(user_message)
