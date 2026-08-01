import httpx
import json

from config import OLLAMA_MODEL

OLLAMA_URL = "http://localhost:11434/api/chat"


async def chat(messages):
    """
    Normal (non-streaming) response.
    Used by REST endpoint.
    """

    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=120) as client:

        response = await client.post(
            OLLAMA_URL,
            json=payload,
        )

        response.raise_for_status()

        data = response.json()

        return data["message"]["content"]


async def stream_chat(messages):
    """
    Streaming response.
    Used by SSE endpoint.
    """

    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": True,
    }

    async with httpx.AsyncClient(timeout=None) as client:

        async with client.stream(
            "POST",
            OLLAMA_URL,
            json=payload,
        ) as response:

            async for line in response.aiter_lines():

                if not line:
                    continue

                data = json.loads(line)

                if "message" in data:
                    yield data["message"]["content"]