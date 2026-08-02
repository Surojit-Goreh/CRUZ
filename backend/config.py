import os
from dotenv import load_dotenv

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "CRUZ")

HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", 8000))

DEBUG = os.getenv("DEBUG", "True").lower() == "true"

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "qwen2.5:3b",
)

# How many past messages (user + assistant combined) to keep per session
# for short-term conversation memory. 20 ≈ last 10 exchanges.
MEMORY_WINDOW_SIZE = int(os.getenv("MEMORY_WINDOW_SIZE", 20))

# Phase 4 — long-term memory database (facts that survive restarts).
MEMORY_DB_PATH = os.getenv(
    "MEMORY_DB_PATH",
    os.path.join(os.path.dirname(__file__), "data", "memory.db"),
)
