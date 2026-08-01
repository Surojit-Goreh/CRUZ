from brain.prompt_builder import build_prompt
from memory.memory_manager import memory_manager, DEFAULT_SESSION_ID
from services.ollama import chat, stream_chat


async def generate_response(user_message: str, session_id: str = DEFAULT_SESSION_ID):
    """
    Normal (non-streaming) response, with short-term memory.
    """
    history = memory_manager.get_messages(session_id)
    messages = build_prompt(user_message, history)

    reply = await chat(messages)

    memory_manager.add_message(session_id, "user", user_message)
    memory_manager.add_message(session_id, "assistant", reply)

    return reply


async def generate_stream(user_message: str, session_id: str = DEFAULT_SESSION_ID):
    """
    Streaming response, with short-term memory.

    The full reply has to be buffered as it streams out, because we only
    know what CRUZ actually said once the last chunk arrives — that's
    what gets saved to memory, not the individual chunks.
    """
    history = memory_manager.get_messages(session_id)
    messages = build_prompt(user_message, history)

    full_reply = ""

    async for chunk in stream_chat(messages):
        full_reply += chunk
        yield chunk

    memory_manager.add_message(session_id, "user", user_message)
    memory_manager.add_message(session_id, "assistant", full_reply)
