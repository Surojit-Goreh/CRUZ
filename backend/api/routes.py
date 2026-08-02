from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from brain.llm import (
    generate_response,
    generate_stream,
)
from memory.long_term_memory import CATEGORIES, long_term_memory
from memory.memory_manager import memory_manager, DEFAULT_SESSION_ID

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class FactUpsert(BaseModel):
    category: str
    key: str
    value: str


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


@router.get("/memory")
def list_memory():
    return {"facts": long_term_memory.get_all_facts()}


@router.get("/memory/{category}")
def list_memory_by_category(category: str):
    return {"facts": long_term_memory.get_facts_by_category(category)}


@router.post("/memory")
def upsert_memory(fact: FactUpsert):
    if fact.category not in CATEGORIES:
        raise HTTPException(
            status_code=422,
            detail=f"category must be one of: {', '.join(CATEGORIES)}",
        )

    long_term_memory.save_fact(fact.category, fact.key, fact.value)
    return {"status": "saved", "category": fact.category, "key": fact.key, "value": fact.value}


@router.delete("/memory/{category}/{key}")
def forget_memory(category: str, key: str):
    deleted = long_term_memory.delete_fact(category, key)
    if not deleted:
        raise HTTPException(status_code=404, detail="Fact not found")
    return {"status": "forgotten", "category": category, "key": key}


@router.delete("/memory")
def forget_all_memory():
    long_term_memory.delete_all()
    return {"status": "wiped"}
