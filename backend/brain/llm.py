from brain.prompt_builder import build_prompt
from services.ollama import chat, stream_chat


async def generate_response(user_message: str):
    """
    Normal (non-streaming) response.
    """
    messages = build_prompt(user_message)

    return await chat(messages)


async def generate_stream(user_message: str):
    """
    Streaming response.
    """
    messages = build_prompt(user_message)

    async for chunk in stream_chat(messages):
        yield chunk