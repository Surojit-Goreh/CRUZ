import asyncio

from brain.prompt_builder import build_prompt
from memory.extractor import extract_facts
from memory.long_term_memory import long_term_memory
from memory.memory_manager import memory_manager, DEFAULT_SESSION_ID
from services.ollama import chat, stream_chat

# Keeps references to fire-and-forget extraction tasks so asyncio
# doesn't garbage-collect them mid-flight; each task removes itself
# once done.
_background_tasks: set = set()


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


async def generate_response(user_message: str, session_id: str = DEFAULT_SESSION_ID):
    """
    Normal (non-streaming) response, with short-term + long-term memory.
    """
    history = memory_manager.get_messages(session_id)
    facts = long_term_memory.get_all_facts()
    messages = build_prompt(user_message, history, facts)

    reply = await chat(messages)

    memory_manager.add_message(session_id, "user", user_message)
    memory_manager.add_message(session_id, "assistant", reply)

    _remember_in_background(user_message)

    return reply


async def generate_stream(user_message: str, session_id: str = DEFAULT_SESSION_ID):
    """
    Streaming response, with short-term + long-term memory.

    The full reply has to be buffered as it streams out, because we only
    know what CRUZ actually said once the last chunk arrives — that's
    what gets saved to memory, not the individual chunks.
    """
    history = memory_manager.get_messages(session_id)
    facts = long_term_memory.get_all_facts()
    messages = build_prompt(user_message, history, facts)

    full_reply = ""

    async for chunk in stream_chat(messages):
        full_reply += chunk
        yield chunk

    memory_manager.add_message(session_id, "user", user_message)
    memory_manager.add_message(session_id, "assistant", full_reply)

    _remember_in_background(user_message)
