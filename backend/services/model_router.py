import asyncio
import json
import time
import httpx
from contextvars import ContextVar
from typing import List, Dict, Any, Optional, Tuple

from config import (
    MODEL_PROVIDER,
    GEMINI_API_KEY,
    GEMINI_BASE_URL,
    GEMINI_MODEL,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OLLAMA_MODEL,
)
from services import ollama
from services.providers.manager import provider_manager
from services.providers.classifier import classify_task
from services.providers.registry import PROVIDERS_CATALOG
from utils.logger import get_logger

logger = get_logger("services.model_router")


class CircuitBreaker:
    """
    In-memory circuit breaker that tracks recent failures per provider.
    Temporarily cools down failing providers to keep chat snappy without hanging on dead endpoints.
    """

    def __init__(self, failure_threshold: int = 3, cooldown_seconds: float = 60.0):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._failures: Dict[str, List[float]] = {}

    def record_failure(self, provider_id: str):
        now = time.monotonic()
        if provider_id not in self._failures:
            self._failures[provider_id] = []
        # Keep only recent failures within cooldown window
        self._failures[provider_id] = [t for t in self._failures[provider_id] if now - t < self.cooldown_seconds]
        self._failures[provider_id].append(now)
        logger.warning(f"CircuitBreaker: Recorded failure for '{provider_id}' (count: {len(self._failures[provider_id])})")

    def record_success(self, provider_id: str):
        if provider_id in self._failures:
            self._failures[provider_id] = []

    def is_available(self, provider_id: str) -> bool:
        if provider_id == "ollama":
            return True  # Ollama is always tried as final safeguard
        now = time.monotonic()
        recent = [t for t in self._failures.get(provider_id, []) if now - t < self.cooldown_seconds]
        self._failures[provider_id] = recent
        return len(recent) < self.failure_threshold


class ModelRouter:
    """
    Cloud Brain Multi-Provider Router with Task-Based Selection and Silent Fallback:
    1. Classifies the incoming prompt (coding, reasoning, writing, vision, general) or uses explicit agent mode.
    2. Dynamically resolves the best specialized free model for each connected provider.
    3. Dispatches prompt to the highest-priority connected provider for that task category.
    4. If the top provider fails, silently falls back to the next connected provider.
    5. Guarantees local Ollama as the final offline fallback.
    6. Tracks which provider/model answered for frontend display.
    """

    PREFERENCE_PIPELINES = {
        "coding": ["groq", "gemini", "opencode", "cloudflare", "nvidia", "openrouter", "ollama"],
        "reasoning": ["groq", "gemini", "opencode", "cloudflare", "nvidia", "openrouter", "ollama"],
        "writing": ["gemini", "groq", "opencode", "cloudflare", "nvidia", "openrouter", "ollama"],
        "vision": ["groq", "cloudflare", "gemini", "opencode", "nvidia", "openrouter", "ollama"],
        "general": ["groq", "gemini", "opencode", "cloudflare", "nvidia", "openrouter", "ollama"],
    }

    def __init__(self):
        self.circuit_breaker = CircuitBreaker()
        self._provider_info: ContextVar[Dict[str, str]] = ContextVar(
            "provider_info",
            default={
            "provider_id": "ollama",
            "provider_name": "Ollama",
            "model": OLLAMA_MODEL or "qwen2.5:3b",
            },
        )

    @property
    def last_provider_info(self) -> Dict[str, str]:
        """Provider data scoped to the current async request/task."""
        return self._provider_info.get()

    @last_provider_info.setter
    def last_provider_info(self, value: Dict[str, str]) -> None:
        self._provider_info.set(value)

    def get_candidate_providers(self, task_category: str, selected_model: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Returns an ordered list of currently connected provider configs for the given task category,
        filtering out providers currently in circuit-breaker cooldown (unless no others exist).
        Dynamically resolves the best task-specialized model for each provider when model is 'auto' or default.
        If selected_model is specified, elevates that provider and model to the highest priority candidate.
        Ollama is always guaranteed at the end of the list.
        """
        connected = provider_manager.get_connected_providers()
        pipeline = self.PREFERENCE_PIPELINES.get(task_category, self.PREFERENCE_PIPELINES["general"])

        candidates = []
        cooled_down = []

        for p_id in pipeline:
            if p_id in connected:
                raw_config = connected[p_id]
                config = dict(raw_config)

                # Dynamic task-based free model resolution
                if p_id in PROVIDERS_CATALOG:
                    info = PROVIDERS_CATALOG[p_id]
                    saved_model = config.get("model") or ""

                    # If model is set to 'auto', blank, or default catalog model, pick task-specialized model
                    if not saved_model or saved_model.lower() == "auto" or saved_model == info.default_model:
                        task_list = info.task_models.get(task_category, [])
                        config["model"] = task_list[0] if task_list else info.default_model

                if self.circuit_breaker.is_available(p_id):
                    candidates.append(config)
                else:
                    cooled_down.append(config)

        # If all cloud providers were cooled down, include cooled down ones before giving up
        if not candidates and cooled_down:
            candidates = cooled_down

        # Ensure Ollama is always appended as final fallback
        if not any(c["id"] == "ollama" for c in candidates):
            ollama_task_models = PROVIDERS_CATALOG["ollama"].task_models.get(task_category, ["qwen2.5:3b"])
            resolved_ollama_model = ollama_task_models[0] if ollama_task_models else (OLLAMA_MODEL or "qwen2.5:3b")

            if "ollama" in connected:
                ollama_cfg = dict(connected["ollama"])
                if not ollama_cfg.get("model") or ollama_cfg.get("model") in ("qwen2.5:3b", "auto"):
                    ollama_cfg["model"] = resolved_ollama_model
                candidates.append(ollama_cfg)
            else:
                candidates.append({
                    "id": "ollama",
                    "name": "Ollama",
                    "api_key": "",
                    "account_id": "",
                    "model": resolved_ollama_model,
                    "base_url": "http://localhost:11434",
                })

        # Manual / Explicit Model Selection Override
        if selected_model and selected_model.strip() and selected_model.lower() != "auto":
            target_pid = None
            target_m = None
            if ":" in selected_model:
                target_pid, target_m = selected_model.split(":", 1)
            else:
                for p_id, info in PROVIDERS_CATALOG.items():
                    if selected_model in info.available_models or selected_model == p_id:
                        target_pid = p_id
                        target_m = selected_model if selected_model in info.available_models else info.default_model
                        break

            if target_pid and target_pid in connected:
                manual_cfg = dict(connected[target_pid])
                manual_cfg["model"] = target_m or manual_cfg.get("model")
                candidates = [c for c in candidates if c["id"] != target_pid]
                candidates.insert(0, manual_cfg)
            elif target_pid == "ollama":
                ollama_cfg = {
                    "id": "ollama",
                    "name": "Ollama",
                    "api_key": "",
                    "account_id": "",
                    "model": target_m or OLLAMA_MODEL or "qwen2.5:3b",
                    "base_url": "http://localhost:11434",
                }
                candidates = [c for c in candidates if c["id"] != "ollama"]
                candidates.insert(0, ollama_cfg)

        return candidates

    async def _call_openai_compatible(
        self,
        url: str,
        api_key: str,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        timeout: float = 12.0,
    ) -> Dict[str, Any]:
        """Generic OpenAI-compatible chat completion helper with tools support."""
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        openai_tools = []
        if tools:
            for t in tools:
                if "type" in t and "function" in t:
                    openai_tools.append(t)
                else:
                    openai_tools.append({"type": "function", "function": t})

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        if openai_tools:
            payload["tools"] = openai_tools

        client_timeout = httpx.Timeout(timeout, connect=4.0)
        async with httpx.AsyncClient(timeout=client_timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
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
                        },
                    })

            res_msg = {
                "role": choice.get("role", "assistant"),
                "content": choice.get("content") or "",
            }
            if tool_calls:
                res_msg["tool_calls"] = tool_calls
            return res_msg

    async def _stream_openai_compatible(
        self,
        url: str,
        api_key: str,
        model: str,
        messages: List[Dict[str, Any]],
        timeout: float = 20.0,
    ):
        """Streams SSE tokens from an OpenAI-compatible endpoint."""
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {"model": model, "messages": messages, "stream": True}

        client_timeout = httpx.Timeout(timeout, connect=4.0)
        async with httpx.AsyncClient(timeout=client_timeout) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                if response.status_code >= 400:
                    body = await response.aread()
                    raise httpx.HTTPStatusError(
                        f"{response.status_code} from {url}: {body[:300]}",
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

    async def chat_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        task_category: Optional[str] = None,
        selected_model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes a tool-enabled chat completion with dynamic routing and silent multi-provider fallback.
        """
        if not task_category:
            task_category = classify_task(messages)
        candidates = self.get_candidate_providers(task_category, selected_model=selected_model)
        logger.info(f"Task category '{task_category}' (selected_model: {selected_model}). Candidate routing order: {[(c['id'], c['model']) for c in candidates]}")

        last_exception = None

        for config in candidates:
            p_id = config["id"]
            p_name = config["name"]
            model = config["model"]
            api_key = config.get("api_key", "")
            account_id = config.get("account_id", "")

            try:
                # 1. Local Ollama Fallback
                if p_id == "ollama":
                    logger.info(f"Attempting local Ollama completion (model: {model})")
                    msg = await ollama.chat_with_tools(messages, tools)
                    self.last_provider_info = {
                        "provider_id": "ollama",
                        "provider_name": "Ollama",
                        "model": model,
                    }
                    msg["_provider_info"] = self.last_provider_info
                    return msg

                # 2. OpenCode Zen
                elif p_id == "opencode":
                    url = "https://opencode.ai/zen/v1/chat/completions"
                    logger.info(f"Attempting OpenCode Zen (model: {model})")
                    msg = await self._call_openai_compatible(url, api_key, model, messages, tools, timeout=30.0)
                    self.circuit_breaker.record_success(p_id)
                    self.last_provider_info = {"provider_id": p_id, "provider_name": p_name, "model": model}
                    msg["_provider_info"] = self.last_provider_info
                    return msg

                # 3. Google Gemini (OpenAI compatible endpoint)
                elif p_id == "gemini":
                    url = f"{GEMINI_BASE_URL.rstrip('/')}/openai/chat/completions"
                    logger.info(f"Attempting Google Gemini (model: {model})")
                    msg = await self._call_openai_compatible(url, api_key, model, messages, tools, timeout=30.0)
                    self.circuit_breaker.record_success(p_id)
                    self.last_provider_info = {"provider_id": p_id, "provider_name": p_name, "model": model}
                    msg["_provider_info"] = self.last_provider_info
                    return msg

                # 4. Groq
                elif p_id == "groq":
                    url = "https://api.groq.com/openai/v1/chat/completions"
                    logger.info(f"Attempting Groq LPU (model: {model})")
                    msg = await self._call_openai_compatible(url, api_key, model, messages, tools, timeout=25.0)
                    self.circuit_breaker.record_success(p_id)
                    self.last_provider_info = {"provider_id": p_id, "provider_name": p_name, "model": model}
                    msg["_provider_info"] = self.last_provider_info
                    return msg

                # 5. OpenRouter
                elif p_id == "openrouter":
                    url = "https://openrouter.ai/api/v1/chat/completions"
                    logger.info(f"Attempting OpenRouter (model: {model})")
                    msg = await self._call_openai_compatible(url, api_key, model, messages, tools, timeout=30.0)
                    self.circuit_breaker.record_success(p_id)
                    self.last_provider_info = {"provider_id": p_id, "provider_name": p_name, "model": model}
                    msg["_provider_info"] = self.last_provider_info
                    return msg

                # 6. NVIDIA NIM
                elif p_id == "nvidia":
                    url = "https://integrate.api.nvidia.com/v1/chat/completions"
                    logger.info(f"Attempting NVIDIA NIM (model: {model})")
                    msg = await self._call_openai_compatible(url, api_key, model, messages, tools, timeout=30.0)
                    self.circuit_breaker.record_success(p_id)
                    self.last_provider_info = {"provider_id": p_id, "provider_name": p_name, "model": model}
                    msg["_provider_info"] = self.last_provider_info
                    return msg

                # 7. Cloudflare Workers AI
                elif p_id == "cloudflare":
                    if account_id:
                        url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1/chat/completions"
                        logger.info(f"Attempting Cloudflare Workers AI (model: {model})")
                        msg = await self._call_openai_compatible(url, api_key, model, messages, tools, timeout=30.0)
                        self.circuit_breaker.record_success(p_id)
                        self.last_provider_info = {"provider_id": p_id, "provider_name": p_name, "model": model}
                        msg["_provider_info"] = self.last_provider_info
                        return msg

            except Exception as e:
                logger.warning(f"Provider '{p_name}' ({p_id}) failed: {e}. Silently falling back to next provider...")
                self.circuit_breaker.record_failure(p_id)
                last_exception = e

        # Final guarantee fallback to local Ollama
        logger.info("All configured cloud providers failed; executing guaranteed local Ollama fallback")
        msg = await ollama.chat_with_tools(messages, tools)
        self.last_provider_info = {
            "provider_id": "ollama",
            "provider_name": "Ollama",
            "model": OLLAMA_MODEL or "qwen2.5:3b",
        }
        msg["_provider_info"] = self.last_provider_info
        return msg

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        task_category: Optional[str] = None,
        selected_model: Optional[str] = None,
    ) -> str:
        """Plain text completion with auto-routing and silent fallback."""
        msg = await self.chat_with_tools(
            messages,
            task_category=task_category,
            selected_model=selected_model,
        )
        return msg.get("content", "")

    async def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        task_category: Optional[str] = None,
        selected_model: Optional[str] = None,
    ):
        """
        Streams response tokens with automatic task classification, provider selection,
        and silent fallback if stream initiation fails.
        """
        if not task_category:
            task_category = classify_task(messages)
        candidates = self.get_candidate_providers(task_category, selected_model=selected_model)
        logger.info(f"Streaming: task '{task_category}' (selected_model: {selected_model}), candidates: {[(c['id'], c['model']) for c in candidates]}")

        for config in candidates:
            p_id = config["id"]
            p_name = config["name"]
            model = config["model"]
            api_key = config.get("api_key", "")
            account_id = config.get("account_id", "")

            stream_started = False
            try:
                if p_id == "ollama":
                    self.last_provider_info = {"provider_id": "ollama", "provider_name": "Ollama", "model": model}
                    async for chunk in ollama.stream_chat(messages):
                        yield chunk
                    return

                elif p_id == "opencode":
                    url = "https://opencode.ai/zen/v1/chat/completions"
                    async for chunk in self._stream_openai_compatible(url, api_key, model, messages):
                        stream_started = True
                        self.last_provider_info = {"provider_id": p_id, "provider_name": p_name, "model": model}
                        yield chunk
                    if stream_started:
                        self.circuit_breaker.record_success(p_id)
                        return

                elif p_id == "gemini":
                    url = f"{GEMINI_BASE_URL.rstrip('/')}/openai/chat/completions"
                    async for chunk in self._stream_openai_compatible(url, api_key, model, messages):
                        stream_started = True
                        self.last_provider_info = {"provider_id": p_id, "provider_name": p_name, "model": model}
                        yield chunk
                    if stream_started:
                        self.circuit_breaker.record_success(p_id)
                        return

                elif p_id == "groq":
                    url = "https://api.groq.com/openai/v1/chat/completions"
                    async for chunk in self._stream_openai_compatible(url, api_key, model, messages):
                        stream_started = True
                        self.last_provider_info = {"provider_id": p_id, "provider_name": p_name, "model": model}
                        yield chunk
                    if stream_started:
                        self.circuit_breaker.record_success(p_id)
                        return

                elif p_id == "openrouter":
                    url = "https://openrouter.ai/api/v1/chat/completions"
                    async for chunk in self._stream_openai_compatible(url, api_key, model, messages):
                        stream_started = True
                        self.last_provider_info = {"provider_id": p_id, "provider_name": p_name, "model": model}
                        yield chunk
                    if stream_started:
                        self.circuit_breaker.record_success(p_id)
                        return

                elif p_id == "nvidia":
                    url = "https://integrate.api.nvidia.com/v1/chat/completions"
                    async for chunk in self._stream_openai_compatible(url, api_key, model, messages):
                        stream_started = True
                        self.last_provider_info = {"provider_id": p_id, "provider_name": p_name, "model": model}
                        yield chunk
                    if stream_started:
                        self.circuit_breaker.record_success(p_id)
                        return

                elif p_id == "cloudflare" and account_id:
                    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1/chat/completions"
                    async for chunk in self._stream_openai_compatible(url, api_key, model, messages):
                        stream_started = True
                        self.last_provider_info = {"provider_id": p_id, "provider_name": p_name, "model": model}
                        yield chunk
                    if stream_started:
                        self.circuit_breaker.record_success(p_id)
                        return

            except Exception as e:
                if stream_started:
                    # Stream aborted mid-flight
                    logger.error(f"Stream aborted mid-flight from '{p_name}': {e}")
                    return
                logger.warning(f"Failed to start stream from '{p_name}': {e}. Falling back...")
                self.circuit_breaker.record_failure(p_id)

        # Fallback to Ollama stream
        logger.info("Falling back to local Ollama stream")
        self.last_provider_info = {
            "provider_id": "ollama",
            "provider_name": "Ollama",
            "model": OLLAMA_MODEL or "qwen2.5:3b",
        }
        async for chunk in ollama.stream_chat(messages):
            yield chunk


model_router = ModelRouter()
