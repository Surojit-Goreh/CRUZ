import httpx
import json
import asyncio
from typing import List, Dict, Any, Optional

from config import (
    MODEL_PROVIDER,
    OPENROUTER_BASE_URL,
    OPENROUTER_API_KEY,
    OLLAMA_MODEL,
    OPENROUTER_MODEL,
    ZEN_BASE_URL,
    ZEN_API_KEY,
    ZEN_MODEL,
    GEMINI_API_KEY,
    GEMINI_BASE_URL,
    GEMINI_MODEL,
)
from services import ollama
from utils.logger import get_logger

logger = get_logger("services.model_router")


class ModelRouter:
    """
    Unified Model Router supporting:
    1. Online Google AI Studio (Gemini) Mode (highest priority when online & configured)
    2. Online OpenCode Zen & OpenRouter Modes
    3. Local Offline Fallback: Ollama (Qwen 2.5) at http://localhost:11434
    4. Automatic Resilient Fallback: If online endpoints fail or time out,
       it seamlessly falls back to local Qwen 2.5 without interrupting the user turn.
    """

    def __init__(self):
        self.provider = MODEL_PROVIDER.lower()
        self.gemini_url = f"{GEMINI_BASE_URL.rstrip('/')}/openai/chat/completions"
        self.openrouter_url = f"{OPENROUTER_BASE_URL.rstrip('/')}/chat/completions"
        self.zen_url = f"{ZEN_BASE_URL.rstrip('/')}/chat/completions"

    GEMINI_MODELS = [
        GEMINI_MODEL,
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-flash-latest",
    ]

    # FIX: "openrouter/auto" is NOT a free-guaranteed model — it can route to
    # paid models and bill you. "openrouter/free" is the real free auto-router.
    # Also replaced dead/stale free IDs (qwen-2.5, gemma-2-9b, mistral-7b are
    # no longer offered free on OpenRouter) with currently-live ones.
    FREE_MODELS = [
        "openrouter/free",
        "nvidia/nemotron-3-ultra-550b-a55b:free",
        "google/gemma-4-31b-it:free",
        "openai/gpt-oss-20b:free",
        "nvidia/nemotron-3-nano-30b-a3b:free",
        "nvidia/nemotron-nano-9b-v2:free",
        "cohere/north-mini-code:free",
    ]

    async def _call_gemini_chat_with_tools(
        self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Calls Google AI Studio (Gemini) API via OpenAI-compatible endpoint.
        Includes automatic fallback across available Gemini models if rate-limited or unavailable.
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GEMINI_API_KEY}",
        }

        openai_tools = []
        if tools:
            for t in tools:
                if "type" in t and "function" in t:
                    openai_tools.append(t)
                else:
                    openai_tools.append({"type": "function", "function": t})

        candidate_models = list(dict.fromkeys(self.GEMINI_MODELS))
        last_exception = None

        for model_name in candidate_models:
            payload: Dict[str, Any] = {
                "model": model_name,
                "messages": messages,
                "stream": False,
            }
            if openai_tools:
                payload["tools"] = openai_tools

            try:
                logger.info(f"Attempting Google AI Studio (Gemini) model: {model_name}")
                async with httpx.AsyncClient(timeout=45) as client:
                    response = await client.post(
                        self.gemini_url,
                        json=payload,
                        headers=headers,
                    )
                    if response.status_code >= 400:
                        logger.warning(
                            f"Google AI Studio '{model_name}' returned {response.status_code}: {response.text[:1000]}"
                        )
                    response.raise_for_status()
                    data = response.json()
                    choice = data["choices"][0]["message"]

                    tool_calls = []
                    if "tool_calls" in choice and choice["tool_calls"]:
                        for tc in choice["tool_calls"]:
                            func = tc.get("function", {})
                            args = func.get("arguments", {})
                            if isinstance(args, str):
                                try:
                                    args = json.loads(args)
                                except Exception:
                                    args = {}
                            tc_item = {
                                "id": tc.get("id"),
                                "type": tc.get("type", "function"),
                                "function": {
                                    "name": func.get("name"),
                                    "arguments": args,
                                }
                            }
                            if "extra_content" in tc:
                                tc_item["extra_content"] = tc["extra_content"]
                            tool_calls.append(tc_item)

                    res_msg = {
                        "role": choice.get("role", "assistant"),
                        "content": choice.get("content") or "",
                    }
                    if tool_calls:
                        res_msg["tool_calls"] = tool_calls

                    logger.info(f"Successfully received response from Google AI Studio ({model_name})")
                    return res_msg
            except Exception as e:
                logger.warning(f"Google AI Studio model '{model_name}' failed ({e}). Trying next model...")
                last_exception = e

        raise last_exception or RuntimeError("All Google AI Studio Gemini models failed")

    async def _call_openrouter_chat_with_tools(
        self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        headers = {
            "Content-Type": "application/json",
        }
        if OPENROUTER_API_KEY:
            headers["Authorization"] = f"Bearer {OPENROUTER_API_KEY}"

        openai_tools = []
        if tools:
            for t in tools:
                if "type" in t and "function" in t:
                    openai_tools.append(t)
                else:
                    openai_tools.append({"type": "function", "function": t})

        # Deduplicate candidates while keeping order
        candidate_models = list(dict.fromkeys(self.FREE_MODELS))
        last_exception = None

        for model_name in candidate_models:
            payload: Dict[str, Any] = {
                "model": model_name,
                "messages": messages,
                "stream": False,
            }
            if openai_tools:
                payload["tools"] = openai_tools

            try:
                payload_size = len(json.dumps(payload))
                logger.info(f"Attempting OpenRouter free model: {model_name} (payload ~{payload_size} bytes)")
                async with httpx.AsyncClient(timeout=30) as client:
                    response = await client.post(
                        self.openrouter_url,
                        json=payload,
                        headers=headers,
                    )
                    if response.status_code >= 400:
                        logger.warning(
                            f"OpenRouter '{model_name}' returned {response.status_code}: {response.text[:1000]}"
                        )
                    response.raise_for_status()
                    data = response.json()
                    choice = data["choices"][0]["message"]

                    tool_calls = []
                    if "tool_calls" in choice and choice["tool_calls"]:
                        for tc in choice["tool_calls"]:
                            func = tc.get("function", {})
                            args = func.get("arguments", {})
                            if isinstance(args, str):
                                try:
                                    args = json.loads(args)
                                except Exception:
                                    args = {}
                            tool_calls.append({
                                "id": tc.get("id"),
                                "type": tc.get("type", "function"),
                                "function": {
                                    "name": func.get("name"),
                                    "arguments": args,
                                }
                            })

                    res_msg = {
                        "role": choice.get("role", "assistant"),
                        "content": choice.get("content") or "",
                    }
                    if tool_calls:
                        res_msg["tool_calls"] = tool_calls

                    logger.info(f"Successfully received response from OpenRouter ({model_name})")
                    return res_msg
            except Exception as e:
                logger.warning(f"OpenRouter model '{model_name}' failed or rate-limited ({e}). Trying next free model...")
                last_exception = e

        raise last_exception or RuntimeError("All free OpenRouter models failed")

    async def _stream_openai_compatible(
        self, url: str, model: str, api_key: str, messages: List[Dict[str, Any]]
    ):
        """
        Shared SSE streaming for any OpenAI-compatible /chat/completions
        endpoint (Google AI Studio, OpenRouter, OpenCode Zen).
        """
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {"model": model, "messages": messages, "stream": True}

        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                if response.status_code >= 400:
                    body = await response.aread()
                    raise httpx.HTTPStatusError(
                        f"{response.status_code} from {url}: {body[:500]}",
                        request=response.request,
                        response=response,
                    )

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data_str = line[len("data:"):].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield content

    async def _call_zen_chat_with_tools(
        self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        OpenCode Zen — hosted gateway with an OpenAI-compatible endpoint.
        """
        headers = {"Content-Type": "application/json"}
        if ZEN_API_KEY:
            headers["Authorization"] = f"Bearer {ZEN_API_KEY}"

        openai_tools = []
        if tools:
            for t in tools:
                if "type" in t and "function" in t:
                    openai_tools.append(t)
                else:
                    openai_tools.append({"type": "function", "function": t})

        payload: Dict[str, Any] = {
            "model": ZEN_MODEL,
            "messages": messages,
            "stream": False,
        }
        if openai_tools:
            payload["tools"] = openai_tools

        logger.info(f"Attempting OpenCode Zen model: {ZEN_MODEL}")
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(self.zen_url, json=payload, headers=headers)
            if response.status_code >= 400:
                logger.warning(f"OpenCode Zen '{ZEN_MODEL}' returned {response.status_code}: {response.text[:1000]}")
            response.raise_for_status()
            data = response.json()
            choice = data["choices"][0]["message"]

            tool_calls = []
            if "tool_calls" in choice and choice["tool_calls"]:
                for tc in choice["tool_calls"]:
                    func = tc.get("function", {})
                    args = func.get("arguments", {})
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except Exception:
                            args = {}
                    tool_calls.append({
                        "id": tc.get("id"),
                        "type": tc.get("type", "function"),
                        "function": {
                            "name": func.get("name"),
                            "arguments": args,
                        }
                    })

            res_msg = {
                "role": choice.get("role", "assistant"),
                "content": choice.get("content") or "",
            }
            if tool_calls:
                res_msg["tool_calls"] = tool_calls

            logger.info(f"Successfully received response from OpenCode Zen ({ZEN_MODEL})")
            return res_msg

    async def chat_with_tools(
        self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Routes tool-enabled chat requests according to provider strategy with automatic offline fallback to Qwen 2.5.
        Priority: Google AI Studio (Gemini) -> OpenCode Zen -> OpenRouter free models -> local Ollama.
        """
        if self.provider in ("gemini", "google", "auto") and GEMINI_API_KEY:
            try:
                logger.info(f"Attempting online model route to Google AI Studio ({self.gemini_url})")
                return await self._call_gemini_chat_with_tools(messages, tools)
            except Exception as e:
                logger.warning(f"Google AI Studio route failed ({type(e).__name__}: {e}). Falling back to next online provider...")

        if self.provider in ("zen", "auto") and ZEN_API_KEY:
            try:
                logger.info(f"Attempting online model route to {self.zen_url}")
                return await self._call_zen_chat_with_tools(messages, tools)
            except Exception as e:
                logger.warning(f"OpenCode Zen route failed ({type(e).__name__}: {e}). Falling back to OpenRouter free models...")

        if self.provider in ("openrouter", "omniroute", "auto", "zen", "gemini", "google"):
            try:
                logger.info(f"Attempting online model route to {self.openrouter_url}")
                return await self._call_openrouter_chat_with_tools(messages, tools)
            except Exception as e:
                logger.warning(
                    f"Online/OpenRouter model route failed ({type(e).__name__}: {e}). Falling back seamlessly to local Ollama ({OLLAMA_MODEL})"
                )

        # Local Offline Fallback / Default Route: Ollama Qwen 2.5
        return await ollama.chat_with_tools(messages, tools)

    async def chat(self, messages: List[Dict[str, Any]]) -> str:
        """
        Routes plain text completion with automatic fallback.
        """
        msg = await self.chat_with_tools(messages)
        return msg.get("content", "")

    async def stream_chat(self, messages: List[Dict[str, Any]]):
        """
        Routes streaming completion using provider priority: Google AI Studio -> OpenCode Zen -> OpenRouter free models -> local Ollama.
        """
        started = False

        if self.provider in ("gemini", "google", "auto") and GEMINI_API_KEY:
            candidate_models = list(dict.fromkeys(self.GEMINI_MODELS))
            for model_name in candidate_models:
                try:
                    async for chunk in self._stream_openai_compatible(
                        self.gemini_url, model_name, GEMINI_API_KEY, messages
                    ):
                        started = True
                        yield chunk
                    if started:
                        return
                except Exception as e:
                    if started:
                        raise
                    logger.warning(f"Google AI Studio stream '{model_name}' failed ({type(e).__name__}: {e}). Trying next...")

        if self.provider in ("zen", "auto") and ZEN_API_KEY:
            try:
                async for chunk in self._stream_openai_compatible(
                    self.zen_url, ZEN_MODEL, ZEN_API_KEY, messages
                ):
                    started = True
                    yield chunk
                if started:
                    return
            except Exception as e:
                if started:
                    raise
                logger.warning(f"OpenCode Zen stream failed ({type(e).__name__}: {e}). Falling back to OpenRouter...")

        if self.provider in ("openrouter", "omniroute", "auto", "zen", "gemini", "google"):
            for model_name in list(dict.fromkeys(self.FREE_MODELS)):
                try:
                    async for chunk in self._stream_openai_compatible(
                        self.openrouter_url, model_name, OPENROUTER_API_KEY, messages
                    ):
                        started = True
                        yield chunk
                    if started:
                        return
                except Exception as e:
                    if started:
                        raise
                    logger.warning(f"OpenRouter stream '{model_name}' failed ({type(e).__name__}: {e}). Trying next...")

        # Local Offline Fallback / Default Route: Ollama Qwen 2.5
        logger.info(f"Streaming via local Ollama ({OLLAMA_MODEL})")
        async for chunk in ollama.stream_chat(messages):
            yield chunk


model_router = ModelRouter()