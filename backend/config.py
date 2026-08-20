import os
import sys
from dotenv import load_dotenv

load_dotenv()


def get_env(key: str, default: str = "") -> str:
    """
    Retrieves an environment variable from:
    1. Process environment (.env or active shell)
    2. Permanent Windows User Registry (HKEY_CURRENT_USER\Environment)
    """
    val = os.getenv(key)
    if val:
        return val
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as reg_key:
                reg_val, _ = winreg.QueryValueEx(reg_key, key)
                if reg_val:
                    return str(reg_val)
        except Exception:
            pass
    return default


APP_NAME = get_env("APP_NAME", "CRUZ")

HOST = get_env("HOST", "127.0.0.1")
PORT = int(get_env("PORT", "8000"))

DEBUG = get_env("DEBUG", "True").lower() == "true"

OLLAMA_MODEL = get_env("OLLAMA_MODEL", "qwen2.5:3b")

# How many past messages (user + assistant combined) to keep per session
# for short-term conversation memory. 20 ≈ last 10 exchanges.
MEMORY_WINDOW_SIZE = int(get_env("MEMORY_WINDOW_SIZE", "20"))

# Phase 4 — long-term memory database (facts that survive restarts).
MEMORY_DB_PATH = get_env(
    "MEMORY_DB_PATH",
    os.path.join(os.path.dirname(__file__), "data", "memory.db"),
)

# Browser automation settings
DEFAULT_SEARCH_ENGINE = get_env("DEFAULT_SEARCH_ENGINE", "google")
BROWSER_HEADLESS = get_env("BROWSER_HEADLESS", "False").lower() == "true"
DATA_ROOT = os.path.join(os.path.dirname(__file__), "data")
BROWSER_PROFILE_DIR = get_env("BROWSER_PROFILE_DIR", os.path.join(DATA_ROOT, "browser_profile"))
BROWSER_SCREENSHOTS_DIR = get_env("BROWSER_SCREENSHOTS_DIR", os.path.join(DATA_ROOT, "browser_screenshots"))

# Model Routing & Provider settings
MODEL_PROVIDER = get_env("MODEL_PROVIDER", "auto")  # 'auto', 'gemini', 'openrouter', 'zen', or 'ollama'
OPENROUTER_BASE_URL = get_env("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_API_KEY = get_env("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = get_env("OPENROUTER_MODEL", "openrouter/auto")

# OpenCode Zen — hosted gateway, OpenAI-compatible
ZEN_BASE_URL = get_env("ZEN_BASE_URL", "https://opencode.ai/zen/v1")
ZEN_API_KEY = get_env("ZEN_API_KEY", "")
ZEN_MODEL = get_env("ZEN_MODEL", "deepseek-v4-flash-free")

# Firecrawl Web Research settings
FIRECRAWL_API_KEY = get_env("FIRECRAWL_API_KEY", "")
FIRECRAWL_BASE_URL = get_env("FIRECRAWL_BASE_URL", "https://api.firecrawl.dev")

# Google AI Studio / Gemini settings
GEMINI_API_KEY = get_env("GEMINI_API_KEY", get_env("GOOGLE_API_KEY", ""))
GEMINI_BASE_URL = get_env("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta")
GEMINI_MODEL = get_env("GEMINI_MODEL", "gemini-3.6-flash")
GEMINI_STT_MODEL = get_env("GEMINI_STT_MODEL", "gemini-2.5-flash")
GEMINI_TTS_MODEL = get_env("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")
GEMINI_TTS_VOICE = get_env("GEMINI_TTS_VOICE", "Puck")  # Puck, Aoede, Fenrir, Kore, Charon
WHISPER_MODEL = get_env("WHISPER_MODEL", "small.en")    # Offline STT model: tiny.en, base.en, small.en, medium.en
VOICE_MODE = get_env("VOICE_MODE", "auto")  # 'auto' (online with offline fallback), 'local' (offline only), 'cloud' (cloud only)

# Dynamic Voice Activity Detection (VAD) timing settings
VOICE_SILENCE_DURATION = float(get_env("VOICE_SILENCE_DURATION", "1.2"))  # Snappy ~1.2s pause after speaking before responding
VOICE_INITIAL_TIMEOUT = float(get_env("VOICE_INITIAL_TIMEOUT", "10.0"))   # Wait time for user to begin speaking (first word)
VOICE_MAX_DURATION = float(get_env("VOICE_MAX_DURATION", "60.0"))         # Maximum continuous voice recording duration
