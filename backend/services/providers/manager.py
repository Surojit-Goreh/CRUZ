import os
import sqlite3
import json
import httpx
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from config import (
    MEMORY_DB_PATH,
    GEMINI_API_KEY,
    OPENROUTER_API_KEY,
    OPENCODE_API_KEY,
    OLLAMA_MODEL,
    get_env,
)
from utils.logger import get_logger
from .registry import PROVIDERS_CATALOG, ProviderInfo

logger = get_logger("services.providers.manager")

_DB_PATH = Path(MEMORY_DB_PATH)
_DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _connect_db() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_providers_table():
    with _connect_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS provider_connections (
                id              TEXT PRIMARY KEY,
                api_key         TEXT,
                account_id      TEXT,
                model           TEXT,
                connected       INTEGER NOT NULL DEFAULT 0,
                last_tested_at  TEXT,
                error_message   TEXT,
                extra_config    TEXT
            )
            """
        )


_init_providers_table()


def mask_api_key(key: Optional[str]) -> str:
    """Masks an API key for safe display in UI (e.g. ••••••••••••abcd)."""
    if not key:
        return ""
    key = key.strip()
    if len(key) <= 8:
        return "••••••••"
    return "•" * (len(key) - 4) + key[-4:]


class ProviderManager:
    """
    Manages LLM provider credentials, connection tests, and live status.
    Stores data in SQLite so changes take effect immediately without backend restart.
    """

    def __init__(self):
        self._sync_env_keys()

    def _sync_env_keys(self):
        """Initial sync of any environment variable keys into the database and auto-healing of obsolete model selections."""
        try:
            with _connect_db() as conn:
                for provider_id, info in PROVIDERS_CATALOG.items():
                    row = conn.execute("SELECT id, api_key, model FROM provider_connections WHERE id = ?", (provider_id,)).fetchone()
                    if not row:
                        if provider_id == "ollama":
                            conn.execute(
                                """
                                INSERT INTO provider_connections (id, api_key, model, connected, last_tested_at)
                                VALUES (?, '', ?, 1, ?)
                                """,
                                (provider_id, info.default_model, datetime.now(timezone.utc).isoformat())
                            )
                        else:
                            env_val = get_env(info.api_key_env_var, "") if info.api_key_env_var else ""
                            if env_val:
                                conn.execute(
                                    """
                                    INSERT INTO provider_connections (id, api_key, model, connected, last_tested_at)
                                    VALUES (?, ?, ?, 1, ?)
                                    """,
                                    (provider_id, env_val, info.default_model, datetime.now(timezone.utc).isoformat())
                                )
                    else:
                        saved_model = row["model"] or ""
                        # Auto-heal deprecated or sunset models to active catalog default
                        if saved_model and saved_model not in info.available_models and saved_model != info.default_model:
                            conn.execute(
                                "UPDATE provider_connections SET model = ? WHERE id = ?",
                                (info.default_model, provider_id)
                            )
                        env_val = get_env(info.api_key_env_var, "") if info.api_key_env_var else ""
                        if env_val and not row["api_key"]:
                            conn.execute(
                                """
                                UPDATE provider_connections
                                SET api_key = ?, connected = 1, last_tested_at = ?
                                WHERE id = ?
                                """,
                                (env_val, datetime.now(timezone.utc).isoformat(), provider_id)
                            )
        except Exception as e:
            logger.warning(f"Error syncing environment keys to DB: {e}")

    def get_all_providers(self) -> List[Dict[str, Any]]:
        """
        Returns all catalog providers merged with their live connection status.
        API keys are always masked to protect sensitive credentials.
        """
        db_records: Dict[str, Dict[str, Any]] = {}
        with _connect_db() as conn:
            rows = conn.execute("SELECT * FROM provider_connections").fetchall()
            for r in rows:
                db_records[r["id"]] = dict(r)

        result = []
        for provider_id, info in PROVIDERS_CATALOG.items():
            db_entry = db_records.get(provider_id, {})
            raw_key = db_entry.get("api_key") or ""
            is_connected = bool(db_entry.get("connected", 0))

            # Special case for Ollama: always show as local provider
            if provider_id == "ollama":
                is_connected = True

            result.append({
                "id": info.id,
                "name": info.name,
                "tier_label": info.tier_label,
                "description": info.description,
                "tags": info.tags,
                "docs_url": info.docs_url,
                "get_key_url": info.get_key_url,
                "default_model": info.default_model,
                "available_models": info.available_models,
                "selected_model": db_entry.get("model") or info.default_model,
                "requires_account_id": info.requires_account_id,
                "account_id_label": info.account_id_label,
                "account_id": db_entry.get("account_id") or "",
                "how_to_create_guide": info.how_to_create_guide,
                "icon_type": info.icon_type,
                "has_key": bool(raw_key) or provider_id == "ollama",
                "masked_key": mask_api_key(raw_key) if raw_key else "",
                "connected": is_connected,
                "last_tested_at": db_entry.get("last_tested_at"),
                "error_message": db_entry.get("error_message"),
            })

        return result

    def get_connected_providers(self) -> Dict[str, Dict[str, Any]]:
        """
        Returns unmasked credentials for all currently connected providers.
        Used directly by the ModelRouter at inference time.
        """
        connected = {}
        with _connect_db() as conn:
            rows = conn.execute("SELECT * FROM provider_connections WHERE connected = 1").fetchall()
            for r in rows:
                p_id = r["id"]
                if p_id in PROVIDERS_CATALOG:
                    info = PROVIDERS_CATALOG[p_id]
                    connected[p_id] = {
                        "id": p_id,
                        "name": info.name,
                        "api_key": r["api_key"] or "",
                        "account_id": r["account_id"] or "",
                        "model": r["model"] or info.default_model,
                        "base_url": info.base_url,
                    }

        # Ollama is always available locally
        if "ollama" not in connected and "ollama" in PROVIDERS_CATALOG:
            connected["ollama"] = {
                "id": "ollama",
                "name": "Ollama",
                "api_key": "",
                "account_id": "",
                "model": OLLAMA_MODEL or "qwen2.5:3b",
                "base_url": "http://localhost:11434",
            }

        return connected

    async def test_connection(
        self,
        provider_id: str,
        api_key: Optional[str] = None,
        account_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Tests connection to the specified provider endpoint with a fast ~5.0s timeout.
        Returns: (success: bool, message: str)
        """
        if provider_id not in PROVIDERS_CATALOG:
            return False, f"Unknown provider: {provider_id}"

        info = PROVIDERS_CATALOG[provider_id]
        key_to_test = api_key
        acc_to_test = account_id
        model_to_test = model or info.default_model

        # If key is not provided in args, lookup from existing saved connection
        if not key_to_test and provider_id != "ollama":
            with _connect_db() as conn:
                row = conn.execute("SELECT api_key, account_id, model FROM provider_connections WHERE id = ?", (provider_id,)).fetchone()
                if row:
                    key_to_test = row["api_key"]
                    acc_to_test = acc_to_test or row["account_id"]
                    model_to_test = model or row["model"] or info.default_model

        if provider_id == "ollama":
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    res = await client.get("http://localhost:11434/api/tags")
                    if res.status_code == 200:
                        models_data = res.json().get("models", [])
                        model_names = [m.get("name") for m in models_data]
                        return True, f"Ollama online with {len(models_data)} local models ({', '.join(model_names[:3]) or 'none pulled'})"
                    return False, f"Ollama returned HTTP {res.status_code}"
            except Exception as e:
                return False, f"Cannot reach Ollama at localhost:11434: {e}"

        if not key_to_test or not key_to_test.strip():
            return False, "API key is required"

        key_to_test = key_to_test.strip()

        # 1. Google Gemini
        if provider_id == "gemini":
            try:
                url = f"{info.base_url}/models?key={key_to_test}"
                async with httpx.AsyncClient(timeout=10.0) as client:
                    res = await client.get(url)
                    if res.status_code == 200:
                        return True, "Successfully connected to Google AI Studio"
                    err_msg = res.text[:200]
                    return False, f"Gemini auth error ({res.status_code}): {err_msg}"
            except httpx.TimeoutException:
                return False, "Gemini connection timed out. Please check your internet connection."
            except Exception as e:
                err_detail = str(e).strip() or type(e).__name__
                return False, f"Gemini connection failed: {err_detail}"

        # 2. Groq
        elif provider_id == "groq":
            try:
                headers = {
                    "Authorization": f"Bearer {key_to_test}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "model": model_to_test,
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 2,
                }
                async with httpx.AsyncClient(timeout=10.0) as client:
                    res = await client.post(f"{info.base_url}/chat/completions", json=payload, headers=headers)
                    if res.status_code == 200:
                        return True, "Successfully connected to Groq LPU"
                    err_msg = res.text[:200]
                    return False, f"Groq error ({res.status_code}): {err_msg}"
            except httpx.TimeoutException:
                return False, "Groq connection timed out. Please check your internet connection."
            except Exception as e:
                err_detail = str(e).strip() or type(e).__name__
                return False, f"Groq connection failed: {err_detail}"

        # 3. OpenRouter
        elif provider_id == "openrouter":
            try:
                headers = {
                    "Authorization": f"Bearer {key_to_test}",
                    "Content-Type": "application/json",
                }
                async with httpx.AsyncClient(timeout=10.0) as client:
                    res = await client.get("https://openrouter.ai/api/v1/auth/key", headers=headers)
                    if res.status_code == 200:
                        data = res.json().get("data", {})
                        label = data.get("label") or "Valid Key"
                        limit = data.get("limit") or "unlimited"
                        return True, f"OpenRouter verified ({label}, limit: {limit})"
                    return False, f"OpenRouter auth failed ({res.status_code})"
            except httpx.TimeoutException:
                return False, "OpenRouter connection timed out. Please check your internet connection."
            except Exception as e:
                err_detail = str(e).strip() or type(e).__name__
                return False, f"OpenRouter connection failed: {err_detail}"

        # 4. Cloudflare Workers AI
        elif provider_id == "cloudflare":
            if not acc_to_test or not acc_to_test.strip():
                return False, "Cloudflare Account ID is required"
            acc_clean = acc_to_test.strip()
            key_clean = key_to_test.strip()
            try:
                headers = {
                    "Authorization": f"Bearer {key_clean}",
                    "Content-Type": "application/json",
                }
                async with httpx.AsyncClient(timeout=10.0) as client:
                    # Step 1: Verify token status
                    verify_res = await client.get("https://api.cloudflare.com/client/v4/user/tokens/verify", headers=headers)
                    if verify_res.status_code == 200 and verify_res.json().get("success"):
                        return True, "Successfully connected to Cloudflare Workers AI"
                    elif verify_res.status_code in (401, 403):
                        return False, f"Cloudflare auth failed ({verify_res.status_code}): Invalid or inactive API token"

                    # Step 2: Fallback to v1 chat completions endpoint
                    v1_url = f"https://api.cloudflare.com/client/v4/accounts/{acc_clean}/ai/v1/chat/completions"
                    payload = {"model": model_to_test, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 2}
                    res = await client.post(v1_url, json=payload, headers=headers)
                    if res.status_code == 200:
                        return True, "Successfully connected to Cloudflare Workers AI"
                    return False, f"Cloudflare error ({res.status_code}): {res.text[:200]}"
            except httpx.TimeoutException:
                return False, "Cloudflare connection timed out. Please check your internet connection."
            except Exception as e:
                err_detail = str(e).strip() or type(e).__name__
                return False, f"Cloudflare connection failed: {err_detail}"

        # 5. NVIDIA NIM
        elif provider_id == "nvidia":
            try:
                headers = {
                    "Authorization": f"Bearer {key_to_test}",
                    "Content-Type": "application/json",
                }
                # Fast auth validation via /models endpoint (completes in ~0.4s)
                async with httpx.AsyncClient(timeout=10.0) as client:
                    res = await client.get(f"{info.base_url}/models", headers=headers)
                    if res.status_code == 200:
                        return True, f"Successfully connected to NVIDIA NIM"
                    if res.status_code in (401, 403):
                        return False, f"NVIDIA NIM auth failed ({res.status_code}): Invalid API key"
                    return False, f"NVIDIA NIM error ({res.status_code}): {res.text[:200]}"
            except httpx.TimeoutException:
                return False, "NVIDIA NIM connection timed out. Please check your internet connection."
            except Exception as e:
                err_detail = str(e).strip() or type(e).__name__
                return False, f"NVIDIA NIM connection failed: {err_detail}"

        # 6. OpenCode Zen
        elif provider_id == "opencode":
            try:
                headers = {
                    "Authorization": f"Bearer {key_to_test}",
                    "Content-Type": "application/json",
                }
                async with httpx.AsyncClient(timeout=10.0) as client:
                    # Quick auth test against /models endpoint
                    res = await client.get(f"{info.base_url}/models", headers=headers)
                    if res.status_code == 200:
                        return True, "Successfully connected to OpenCode Zen"
                    if res.status_code in (401, 403):
                        return False, f"OpenCode auth failed ({res.status_code}): Invalid API key"

                    # Fallback to chat completions probe
                    payload = {
                        "model": model_to_test if model_to_test and model_to_test != "auto" else info.default_model,
                        "messages": [{"role": "user", "content": "hi"}],
                        "max_tokens": 2,
                    }
                    res_chat = await client.post(f"{info.base_url}/chat/completions", json=payload, headers=headers)
                    if res_chat.status_code == 200:
                        return True, "Successfully connected to OpenCode Zen"
                    err_msg = res_chat.text[:200]
                    return False, f"OpenCode error ({res_chat.status_code}): {err_msg}"
            except httpx.TimeoutException:
                return False, "OpenCode connection timed out. Please check your internet connection."
            except Exception as e:
                err_detail = str(e).strip() or type(e).__name__
                return False, f"OpenCode connection failed: {err_detail}"

        # 7. CRUZ Node
        elif provider_id == "cruz_node":
            return True, "CRUZ Node endpoint ready for pairing"

        return False, "Provider test routine not implemented"

    async def fetch_available_models(
        self,
        provider_id: str,
        api_key: Optional[str] = None,
        account_id: Optional[str] = None,
    ) -> List[str]:
        """
        Dynamically queries provider API for live accessible models (filtering to free tier/active models).
        Falls back to catalog defaults if key is missing or endpoint fails.
        """
        if provider_id not in PROVIDERS_CATALOG:
            return []

        info = PROVIDERS_CATALOG[provider_id]
        key = api_key
        acc = account_id

        # Lookup from database if key not passed
        if not key and provider_id != "ollama":
            with _connect_db() as conn:
                row = conn.execute("SELECT api_key, account_id FROM provider_connections WHERE id = ?", (provider_id,)).fetchone()
                if row:
                    key = row["api_key"]
                    acc = acc or row["account_id"]

        # 1. Google Gemini
        if provider_id == "gemini":
            if key and key.strip():
                try:
                    url = f"{info.base_url}/models?key={key.strip()}"
                    async with httpx.AsyncClient(timeout=8.0) as client:
                        res = await client.get(url)
                        if res.status_code == 200:
                            data = res.json()
                            raw_models = data.get("models", [])
                            gemini_models = []
                            for m in raw_models:
                                name = m.get("name", "")
                                methods = m.get("supportedGenerationMethods", [])
                                if "generateContent" in methods and "gemini" in name:
                                    clean_name = name.replace("models/", "")
                                    gemini_models.append(clean_name)
                            if gemini_models:
                                gemini_models.sort(key=lambda x: (not ("flash" in x), not ("2.5" in x or "2.0" in x), x))
                                return gemini_models
                except Exception as e:
                    logger.debug(f"Failed to fetch Gemini dynamic models: {e}")
            return info.available_models

        # 2. Groq
        elif provider_id == "groq":
            if key and key.strip():
                try:
                    headers = {"Authorization": f"Bearer {key.strip()}"}
                    async with httpx.AsyncClient(timeout=8.0) as client:
                        res = await client.get(f"{info.base_url}/models", headers=headers)
                        if res.status_code == 200:
                            data = res.json()
                            models_data = data.get("data", [])
                            groq_models = []
                            for m in models_data:
                                mid = m.get("id", "")
                                if mid and not any(mid.startswith(prefix) for prefix in ["whisper", "distil-whisper", "tts"]):
                                    groq_models.append(mid)
                            if groq_models:
                                def _groq_sort(m_name: str):
                                    if "llama-3.3" in m_name: return (0, m_name)
                                    if "deepseek" in m_name: return (1, m_name)
                                    if "qwen" in m_name: return (2, m_name)
                                    if "llama-3.1" in m_name: return (3, m_name)
                                    if "gemma" in m_name: return (4, m_name)
                                    return (5, m_name)
                                groq_models.sort(key=_groq_sort)
                                return groq_models
                except Exception as e:
                    logger.debug(f"Failed to fetch Groq dynamic models: {e}")
            return info.available_models

        # 3. OpenRouter
        elif provider_id == "openrouter":
            try:
                headers = {}
                if key and key.strip():
                    headers["Authorization"] = f"Bearer {key.strip()}"
                async with httpx.AsyncClient(timeout=8.0) as client:
                    res = await client.get("https://openrouter.ai/api/v1/models", headers=headers)
                    if res.status_code == 200:
                        data = res.json()
                        raw_models = data.get("data", [])
                        free_models = ["openrouter/free"]
                        for m in raw_models:
                            mid = m.get("id", "")
                            pricing = m.get("pricing", {})
                            is_free = (
                                mid.endswith(":free")
                                or (pricing.get("prompt") == "0" and pricing.get("completion") == "0")
                            )
                            if is_free and mid not in free_models:
                                free_models.append(mid)
                        if len(free_models) > 1:
                            return free_models
            except Exception as e:
                logger.debug(f"Failed to fetch OpenRouter dynamic models: {e}")
            return info.available_models

        # 4. NVIDIA NIM
        elif provider_id == "nvidia":
            if key and key.strip():
                try:
                    headers = {"Authorization": f"Bearer {key.strip()}"}
                    async with httpx.AsyncClient(timeout=8.0) as client:
                        res = await client.get(f"{info.base_url}/models", headers=headers)
                        if res.status_code == 200:
                            data = res.json()
                            raw_models = data.get("data", [])
                            nvidia_models = []
                            # Exclude non-chat / embeddings / biology / vision-only models
                            excluded_keywords = [
                                "embed", "rerank", "diffusion", "whisper", "audio", "tts", "asr",
                                "riva", "guard", "clip", "vit", "bge", "arctic", "biology",
                                "genomics", "molmim", "diffdock", "esmfold", "ocr", "sdxl", "flux",
                                "stable-diffusion", "kosmos", "fuyu", "cuopt", "megamolbart"
                            ]
                            for m in raw_models:
                                mid = m.get("id", "")
                                if mid:
                                    mid_lower = mid.lower()
                                    if not any(k in mid_lower for k in excluded_keywords):
                                        if any(k in mid_lower for k in ["instruct", "chat", "nemotron", "deepseek", "llama", "mistral", "qwen", "gemma", "phi"]):
                                            nvidia_models.append(mid)

                            if nvidia_models:
                                def _nvidia_sort(m_name: str):
                                    m_lower = m_name.lower()
                                    if "llama-3.3-70b" in m_lower: return (0, m_name)
                                    if "llama-3.1-8b" in m_lower: return (1, m_name)
                                    if "nemotron-70b" in m_lower: return (2, m_name)
                                    if "deepseek-r1" in m_lower: return (3, m_name)
                                    if "llama-3.1-70b" in m_lower: return (4, m_name)
                                    if "mistral-large" in m_lower: return (5, m_name)
                                    if "qwen2.5-coder" in m_lower: return (6, m_name)
                                    if "qwen2.5-72b" in m_lower: return (7, m_name)
                                    if "gemma-2-27b" in m_lower: return (8, m_name)
                                    if "gemma-2-9b" in m_lower: return (9, m_name)
                                    return (10, m_name)

                                nvidia_models.sort(key=_nvidia_sort)
                                return nvidia_models
                except Exception as e:
                    logger.debug(f"Failed to fetch NVIDIA dynamic models: {e}")
            return info.available_models

        # 5. Ollama
        elif provider_id == "ollama":
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    res = await client.get("http://localhost:11434/api/tags")
                    if res.status_code == 200:
                        models_data = res.json().get("models", [])
                        names = [m.get("name") for m in models_data if m.get("name")]
                        if names:
                            return names
            except Exception as e:
                logger.debug(f"Failed to reach Ollama models: {e}")
            return info.available_models

        # 6. Cloudflare
        elif provider_id == "cloudflare":
            if key and acc and key.strip() and acc.strip():
                try:
                    headers = {"Authorization": f"Bearer {key.strip()}"}
                    async with httpx.AsyncClient(timeout=8.0) as client:
                        url = f"https://api.cloudflare.com/client/v4/accounts/{acc.strip()}/ai/models/search?task=Text%20Generation"
                        res = await client.get(url, headers=headers)
                        if res.status_code == 200:
                            data = res.json()
                            raw_models = data.get("result", [])
                            cf_models = []
                            for m in raw_models:
                                name = m.get("name", "")
                                if name and name.startswith("@cf/"):
                                    cf_models.append(name)
                            if cf_models:
                                def _cf_sort(m_name: str):
                                    m_lower = m_name.lower()
                                    if "llama-3.3-70b" in m_lower: return (0, m_name)
                                    if "deepseek" in m_lower: return (1, m_name)
                                    if "llama-3.1-8b" in m_lower: return (2, m_name)
                                    if "qwen" in m_lower: return (3, m_name)
                                    return (4, m_name)
                                cf_models.sort(key=_cf_sort)
                                return cf_models
                except Exception as e:
                    logger.debug(f"Failed to fetch Cloudflare dynamic models: {e}")
            return info.available_models

        # 7. OpenCode Zen
        elif provider_id == "opencode":
            try:
                headers = {}
                if key and key.strip():
                    headers["Authorization"] = f"Bearer {key.strip()}"
                async with httpx.AsyncClient(timeout=8.0) as client:
                    res = await client.get(f"{info.base_url}/models", headers=headers)
                    if res.status_code == 200:
                        data = res.json()
                        raw_models = data.get("data", [])
                        opencode_models = []
                        for m in raw_models:
                            mid = m.get("id", "")
                            if mid and mid not in opencode_models:
                                opencode_models.append(mid)
                        if opencode_models:
                            def _opencode_sort(m_name: str):
                                m_lower = m_name.lower()
                                if "-free" in m_lower or "free" in m_lower: return (0, m_name)
                                if "claude-sonnet" in m_lower: return (1, m_name)
                                if "gpt-5" in m_lower: return (2, m_name)
                                if "gemini" in m_lower: return (3, m_name)
                                if "deepseek" in m_lower: return (4, m_name)
                                if "qwen" in m_lower: return (5, m_name)
                                if "nemotron" in m_lower: return (6, m_name)
                                return (7, m_name)
                            opencode_models.sort(key=_opencode_sort)
                            return opencode_models
            except Exception as e:
                logger.debug(f"Failed to fetch OpenCode dynamic models: {e}")
            return info.available_models

        # 8. CRUZ Node
        elif provider_id == "cruz_node":
            return ["cruz-default"]

        return info.available_models

    async def connect_provider(
        self,
        provider_id: str,
        api_key: str,
        account_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Tests the API key and persists the result in the SQLite database.
        Retains previously saved credentials if new fields are left empty.
        """
        if provider_id not in PROVIDERS_CATALOG:
            return False, f"Unknown provider: {provider_id}"

        success, message = await self.test_connection(
            provider_id=provider_id,
            api_key=api_key,
            account_id=account_id,
            model=model,
        )

        now = datetime.now(timezone.utc).isoformat()
        info = PROVIDERS_CATALOG[provider_id]
        selected_model = model or info.default_model

        with _connect_db() as conn:
            existing = conn.execute("SELECT api_key, account_id, model FROM provider_connections WHERE id = ?", (provider_id,)).fetchone()
            key_to_save = api_key.strip() if api_key and api_key.strip() else (existing["api_key"] if existing and existing["api_key"] else "")
            acc_to_save = account_id.strip() if account_id and account_id.strip() else (existing["account_id"] if existing and existing["account_id"] else "")

            conn.execute(
                """
                INSERT INTO provider_connections (id, api_key, account_id, model, connected, last_tested_at, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    api_key = excluded.api_key,
                    account_id = excluded.account_id,
                    model = excluded.model,
                    connected = excluded.connected,
                    last_tested_at = excluded.last_tested_at,
                    error_message = excluded.error_message
                """,
                (
                    provider_id,
                    key_to_save,
                    acc_to_save,
                    selected_model,
                    1 if success else 0,
                    now,
                    None if success else message,
                ),
            )

        return success, message

    def disconnect_provider(self, provider_id: str) -> bool:
        """Removes saved key and marks provider disconnected."""
        if provider_id == "ollama":
            # Ollama stays available locally
            return True

        with _connect_db() as conn:
            conn.execute(
                """
                UPDATE provider_connections
                SET api_key = '', account_id = '', connected = 0, error_message = 'Disconnected by user'
                WHERE id = ?
                """,
                (provider_id,),
            )
        return True


provider_manager = ProviderManager()
