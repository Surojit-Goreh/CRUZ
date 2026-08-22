from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
import asyncio

from utils.logger import get_logger

logger = get_logger("api.websocket")

router = APIRouter()

from brain.llm import generate_stream
from voice.voice_manager import VoiceManager
from services.model_router import model_router
from services.providers.classifier import detect_agent_mode_intent
import re

@router.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    await websocket.accept()

    dispatcher = websocket.app.state.dispatcher
    async def get_voice_manager() -> VoiceManager:
        voice_manager = websocket.app.state.voice_manager
        if voice_manager is not None:
            return voice_manager
        async with websocket.app.state.voice_manager_lock:
            voice_manager = websocket.app.state.voice_manager
            if voice_manager is None:
                voice_manager = VoiceManager(on_event=dispatcher.publish)
                websocket.app.state.voice_manager = voice_manager
            return voice_manager

    queue = dispatcher.subscribe()

    async def forward_events():
        # Pure async — forwards dispatcher events to WebSocket client in real-time
        while True:
            event = await queue.get()
            await websocket.send_json(event)

    forward_task = asyncio.create_task(forward_events())

    try:
        while True:
            msg = await websocket.receive_json()
            logger.info(f"received: {msg}")
            action = msg.get("action")
            if action == "start_turn":
                voice_manager = await get_voice_manager()
                duration_seconds = msg.get("duration_seconds", None)
                result = await voice_manager.run_turn(
                    duration_seconds=duration_seconds, save_debug_audio=False
                )
                await websocket.send_json({"state": "result", **result})
                logger.info("sent result")
            elif action == "chat_voice":
                voice_manager = await get_voice_manager()
                user_msg = msg.get("message", "")
                intent_mode = detect_agent_mode_intent(user_msg)
                agent_mode = intent_mode or msg.get("agent_mode", "auto")

                if intent_mode:
                    dispatcher.publish({"state": "agent_mode_changed", "agent_mode": intent_mode})

                dispatcher.publish({"state": "thinking", "transcript": user_msg})
                token_stream = generate_stream(user_msg, agent_mode=agent_mode)
                reply = await voice_manager.stream_reply_tts(token_stream)

                agent_mode_match = re.search(r"AGENT_MODE_SWITCH:(\w+):", reply)
                detected_mode = agent_mode_match.group(1) if agent_mode_match else intent_mode or detect_agent_mode_intent(reply)
                cleaned_reply = re.sub(r"AGENT_MODE_SWITCH:\w+:\s*", "", reply).strip() if agent_mode_match else reply

                if detected_mode:
                    dispatcher.publish({"state": "agent_mode_changed", "agent_mode": detected_mode})

                dispatcher.publish({"state": "idle"})
                await websocket.send_json({
                    "state": "result",
                    "success": True,
                    "reply": cleaned_reply,
                    "transcript": user_msg,
                    "error": None,
                    "provider": model_router.last_provider_info.get("provider_name"),
                    "model": model_router.last_provider_info.get("model"),
                    "agent_mode": detected_mode,
                })
    except WebSocketDisconnect:
        pass
    finally:
        forward_task.cancel()
        dispatcher.unsubscribe(queue)
