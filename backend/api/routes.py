from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from brain.llm import (
    generate_response,
    generate_stream,
)

router = APIRouter()


class ChatRequest(BaseModel):
    message: str


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
        reply = await generate_response(request.message)

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

    async def event_generator():
        async for chunk in generate_stream(request.message):
            yield chunk

    return StreamingResponse(
        event_generator(),
        media_type="text/plain",
    )