import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import APP_NAME
from api.routes import router
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
)

# -----------------------------
# Existing REST API
# -----------------------------
app.include_router(router)

# -----------------------------
# Voice system (Singletons)
# -----------------------------
dispatcher = EventDispatcher()
voice_manager = VoiceManager(on_event=dispatcher.publish)

app.state.dispatcher = dispatcher
app.state.voice_manager = voice_manager

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