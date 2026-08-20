import httpx
import json

from config import OLLAMA_MODEL

OLLAMA_URL = "http://localhost:11434/api/chat"


def _clean_messages_for_ollama(messages):
    """
    Ollama requires tool_calls[].function.arguments to be a dictionary/object,
    not a stringified JSON string (which OpenRouter requires). This helper
    ensures all tool_call arguments are properly parsed into dicts for Ollama.
    """
    cleaned = []
    for msg in messages:
        m = dict(msg)
        if "tool_calls" in m and m["tool_calls"]:
            cleaned_tc = []
            for tc in m["tool_calls"]:
                tc_copy = dict(tc)
                if "function" in tc_copy:
                    fn = dict(tc_copy["function"])
                    if isinstance(fn.get("arguments"), str):
                        try:
                            fn["arguments"] = json.loads(fn["arguments"])
                        except Exception:
                            fn["arguments"] = {}
                    tc_copy["function"] = fn
                cleaned_tc.append(tc_copy)
            m["tool_calls"] = cleaned_tc
        cleaned.append(m)
    return cleaned


async def chat(messages):
    """
    Normal (non-streaming) response — plain text content only.
    Used by REST endpoint and by memory/extractor.py. Unchanged from
    before: existing callers that expect a string back keep working.
    """

    payload = {
        "model": OLLAMA_MODEL,
        "messages": _clean_messages_for_ollama(messages),
        "stream": False,
        "keep_alive": "30m",
    }

    async with httpx.AsyncClient(timeout=120) as client:

        response = await client.post(
            OLLAMA_URL,
            json=payload,
        )

        response.raise_for_status()

        data = response.json()

        return data["message"]["content"]


async def chat_with_tools(messages, tools=None):
    """
    Same as chat(), but returns the full message dict instead of just
    the content string, and can advertise tool schemas to the model.

    The full message matters here because a tool-calling response has
    message["tool_calls"] instead of (or alongside) message["content"] —
    the caller (brain/llm.py) needs to see that to decide whether to run
    a tool or treat the reply as final.
    """

    payload = {
        "model": OLLAMA_MODEL,
        "messages": _clean_messages_for_ollama(messages),
        "stream": False,
        "keep_alive": "30m",
    }
    if tools:
        payload["tools"] = tools

    async with httpx.AsyncClient(timeout=120) as client:

        response = await client.post(
            OLLAMA_URL,
            json=payload,
        )

        response.raise_for_status()

        data = response.json()

        return data["message"]


async def stream_chat(messages):
    """
    Streaming response.
    Used by SSE endpoint.
    """

    payload = {
        "model": OLLAMA_MODEL,
        "messages": _clean_messages_for_ollama(messages),
        "stream": True,
        "keep_alive": "30m",
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
