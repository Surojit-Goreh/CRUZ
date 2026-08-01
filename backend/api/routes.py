from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from brain.llm import (
    generate_response,
    generate_stream,
)
from memory.memory_manager import memory_manager, DEFAULT_SESSION_ID

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


@router.get("/")
def home():
    return {
        "message": "Welcome to CRUZ Backend"
    }


@router.get("/health")
def health():
    return {
        "status": "OK"
    }


@router.post("/chat")
async def chat(request: ChatRequest):
    try:
        session_id = request.session_id or DEFAULT_SESSION_ID
        reply = await generate_response(request.message, session_id)

        return {
            "reply": reply
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    session_id = request.session_id or DEFAULT_SESSION_ID

    async def event_generator():
        async for chunk in generate_stream(request.message, session_id):
            yield chunk

    return StreamingResponse(
        event_generator(),
        media_type="text/plain",
    )


@router.post("/chat/reset")
def chat_reset(session_id: Optional[str] = None):
    memory_manager.reset(session_id or DEFAULT_SESSION_ID)

    return {
        "status": "cleared",
        "session_id": session_id or DEFAULT_SESSION_ID,
    }
