import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import APP_NAME
from api.routes import router
from api.providers import router as providers_router
from api.websocket import router as voice_ws_router

from voice.event_dispatcher import EventDispatcher
from voice.voice_manager import VoiceManager

app = FastAPI(title=APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Provider", "X-Model"],
)

# -----------------------------
# Static files (Generated images, media)
# -----------------------------
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
os.makedirs(os.path.join(STATIC_DIR, "generated_images"), exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# -----------------------------
# REST APIs
# -----------------------------
app.include_router(router)
app.include_router(providers_router)


# -----------------------------
# Voice system (Singletons)
# -----------------------------
dispatcher = EventDispatcher()
app.state.dispatcher = dispatcher
# Voice models are large and unavailable in many API-only deployments. Create
# them only when a client actually opens the voice WebSocket.
app.state.voice_manager = None
app.state.voice_manager_lock = asyncio.Lock()

# -----------------------------
# Voice WebSocket
# -----------------------------
app.include_router(voice_ws_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.server:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_excludes=["data/*", "*.wav", "*.pyc", "*.bin"],
    )
