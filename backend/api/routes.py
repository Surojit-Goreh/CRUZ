from typing import Optional
import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from brain.llm import (
    generate_response,
    generate_stream,
)
from memory.long_term_memory import CATEGORIES, long_term_memory
from memory.memory_manager import memory_manager, DEFAULT_SESSION_ID
from utils.logger import get_logger

logger = get_logger("api.routes")

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    agent_mode: Optional[str] = "auto"
    model: Optional[str] = None


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


from services.model_router import model_router
from services.providers.classifier import detect_agent_mode_intent

@router.post("/chat")
async def chat(request: ChatRequest):
    try:
        session_id = request.session_id or DEFAULT_SESSION_ID
        intent_mode = detect_agent_mode_intent(request.message)
        effective_mode = intent_mode or request.agent_mode

        raw_reply = await generate_response(
            request.message,
            session_id,
            agent_mode=effective_mode,
            selected_model=request.model,
        )
        clean_reply = re.sub(r"AGENT_MODE_SWITCH:\w+:\s*", "", raw_reply).strip()

        return {
            "reply": clean_reply,
            "provider": model_router.last_provider_info.get("provider_name"),
            "model": model_router.last_provider_info.get("model"),
            "agent_mode": intent_mode,
        }

    except Exception as e:
        logger.exception("chat request failed")
        raise HTTPException(
            status_code=500,
            detail="Something went wrong processing your message. Check server logs for details.",
        )


import json
from core.activity import ActivityEvent

@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    session_id = request.session_id or DEFAULT_SESSION_ID
    intent_mode = detect_agent_mode_intent(request.message)
    effective_mode = intent_mode or request.agent_mode

    async def event_generator():
        sent_metadata = False
        try:
            async for item in generate_stream(
                request.message,
                session_id,
                agent_mode=effective_mode,
                selected_model=request.model,
            ):
                if isinstance(item, ActivityEvent):
                    yield f"event: activity\ndata: {json.dumps(item.to_dict())}\n\n"
                elif isinstance(item, dict):
                    if item.get("type") == "plan":
                        yield f"event: plan\ndata: {json.dumps(item.get('plan', {}))}\n\n"
                    else:
                        yield f"event: activity\ndata: {json.dumps(item)}\n\n"
                elif isinstance(item, str):
                    clean_chunk = re.sub(r"AGENT_MODE_SWITCH:\w+:\s*", "", item)
                    if clean_chunk:
                        if not sent_metadata:
                            provider_info = model_router.last_provider_info
                            yield f"event: metadata\ndata: {json.dumps(provider_info)}\n\n"
                            sent_metadata = True
                        yield f"event: token\ndata: {json.dumps(clean_chunk)}\n\n"
            # Send latest provider and multi-model metadata before completion
            final_metadata = model_router.last_provider_info
            yield f"event: metadata\ndata: {json.dumps(final_metadata)}\n\n"
            yield f"event: done\ndata: {json.dumps({'done': True})}\n\n"
        except Exception as exc:
            logger.exception("chat stream failed")
            safe_error_msg = "Unable to complete the request. Please check server logs or try again."
            yield f"event: error\ndata: {json.dumps(safe_error_msg)}\n\n"

    headers = {}
    if intent_mode:
        headers["X-Agent-Mode"] = intent_mode

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=headers,
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
