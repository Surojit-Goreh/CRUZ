from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
import asyncio

router = APIRouter()

@router.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    await websocket.accept()

    dispatcher = websocket.app.state.dispatcher
    voice_manager = websocket.app.state.voice_manager

    queue = dispatcher.subscribe()

    async def forward_events():
        # Pure async — no cross-thread scheduling needed, since
        # dispatcher.publish() is always called from within this
        # same event loop (run_turn is awaited on it directly).
        while True:
            event = await queue.get()
            await websocket.send_json(event)

    forward_task = asyncio.create_task(forward_events())

    try:
        while True:
            msg = await websocket.receive_json()
            print("📩 RECEIVED:", msg)
            if msg.get("action") == "start_turn":
                result = await voice_manager.run_turn(duration_seconds=5, save_debug_audio=False)
                await websocket.send_json({"state": "result", **result})
                print("📤 SENDING RESULT")
    except WebSocketDisconnect:
        pass
    finally:
        forward_task.cancel()
        dispatcher.unsubscribe(queue)