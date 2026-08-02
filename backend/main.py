from fastapi import FastAPI
from voice.event_dispatcher import EventDispatcher
from voice.voice_manager import VoiceManager

app = FastAPI()

dispatcher = EventDispatcher()
voice_manager = VoiceManager(on_event=dispatcher.publish)

# Make both available to routers without re-instantiating anything
app.state.dispatcher = dispatcher
app.state.voice_manager = voice_manager

from api.websocket import router as voice_ws_router
app.include_router(voice_ws_router)