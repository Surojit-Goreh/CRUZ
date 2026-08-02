import asyncio
import time

class EventDispatcher:
    """Sits between VoiceManager and any number of async consumers
    (WebSocket connections, loggers, etc). VoiceManager only knows
    about dispatcher.publish() — a plain sync method."""

    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        if q in self._subscribers:
            self._subscribers.remove(q)

    def publish(self, event: dict):
        """Sync method — safe to call from VoiceManager directly,
        since we're always running inside the FastAPI event loop thread
        (no cross-thread scheduling needed here)."""
        event = {**event, "timestamp": time.time()}
        for q in self._subscribers:
            q.put_nowait(event)