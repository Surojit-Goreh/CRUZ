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