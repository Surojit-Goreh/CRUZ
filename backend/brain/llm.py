import asyncio
import json
import uuid
import inspect
from typing import Optional, Any, Callable, Dict, List

from brain.prompt_builder import build_prompt
from memory.extractor import extract_facts
from memory.long_term_memory import long_term_memory
from memory.memory_manager import memory_manager, DEFAULT_SESSION_ID
from services.model_router import model_router
from executor.executor import run_tool_calls
from skills.manager import skill_manager
from utils.logger import get_logger

logger = get_logger("brain.llm")

# Keeps references to fire-and-forget extraction tasks so asyncio
# doesn't garbage-collect them mid-flight; each task removes itself
# once done.
_background_tasks: set = set()

# Guards against infinite tool loops. Set high enough for multi-file project creation.
MAX_TOOL_ITERATIONS = 12


def _remember_in_background(user_message: str) -> None:
    """
    Kick off fact extraction without making the user wait for it.

    Extraction is itself an LLM call, so doing it inline would roughly
    double response time on a local 3B model. Firing it after the reply
    is already on its way keeps the chat feeling snappy.
    """
    task = asyncio.create_task(_remember(user_message))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def _remember(user_message: str) -> None:
    try:
        facts = await extract_facts(user_message)
        for fact in facts:
            long_term_memory.save_fact(fact["category"], fact["key"], fact["value"])
    except Exception:
        # A failed extraction should never crash anything — it just
        # means nothing new got saved this turn.
        pass
AGENT_MODE_TASK_MAP = {
    "build": "coding",
    "coding": "coding",
    "plan": "reasoning",
    "reasoning": "reasoning",
    "image": "vision",
    "vision": "vision",
    "writing": "writing",
    "writer": "writing",
    "chat": "general",
    "general": "general",
    "auto": None,
}


from core.activity import (
    ActivityEvent,
    create_activity_event,
    PHASE_UNDERSTANDING,
    PHASE_PLANNING,
    PHASE_SYNTHESIZING,
    PHASE_COMPLETED,
)


async def run_tool_pipeline(
    messages: list,
    task_category: Optional[str] = None,
    selected_model: Optional[str] = None,
    user_message: Optional[str] = None,
    on_event: Optional[Any] = None,
    execution_id: Optional[str] = None,
) -> Optional[str]:
    """
    Executes the tool-calling loop using dynamically selected active skills & tools.
    Emits safe progress events via on_event callback without leaking private reasoning.
    """
    # Contextually resolve tool schemas for the active skills matching this task & prompt
    active_tools = skill_manager.get_active_tool_schemas(task_category=task_category, user_message=user_message)
    logger.info(f"Active skills loaded {len(active_tools)} tools for task '{task_category}'")

    for round_num in range(MAX_TOOL_ITERATIONS):
        message = await model_router.chat_with_tools(
            messages,
            tools=active_tools if active_tools else None,
            task_category=task_category,
            selected_model=selected_model,
        )
        tool_calls = message.get("tool_calls")

        if not tool_calls:
            final_text = message.get("content") or ""
            if round_num == 0:
                logger.info("model answered without calling any tool")
            else:
                logger.info(f"model finished tool execution loop on round {round_num}")
            return final_text if final_text.strip() else None

        tool_names = [c.get("function", {}).get("name") for c in tool_calls]
        logger.info(f"round {round_num}: model called tool(s) {tool_names}")

        # Synthesize call IDs for providers that omit them
        for tc in tool_calls:
            if not tc.get("id"):
                tc["id"] = f"call_{uuid.uuid4().hex[:24]}"
            tc.setdefault("type", "function")

        history_message = dict(message)
        history_message["tool_calls"] = [
            {
                **tc,
                "function": {
                    **tc["function"],
                    "arguments": (
                        tc["function"]["arguments"]
                        if isinstance(tc["function"].get("arguments"), str)
                        else json.dumps(tc["function"].get("arguments", {}))
                    ),
                },
            }
            for tc in tool_calls
        ]

        messages.append(history_message)
        executed_tool_messages = await run_tool_calls(
            tool_calls,
            on_event=on_event,
            execution_id=execution_id,
        )
        messages.extend(executed_tool_messages)

    logger.warning(f"hit MAX_TOOL_ITERATIONS ({MAX_TOOL_ITERATIONS})")
    return None


async def generate_response(
    user_message: str,
    session_id: str = DEFAULT_SESSION_ID,
    agent_mode: Optional[str] = "auto",
    selected_model: Optional[str] = None,
    on_event: Optional[Any] = None,
) -> str:
    """
    Normal (non-streaming) response, with skills instructions, short-term + long-term memory,
    and contextual tool calling. Emits safe activity events if on_event callback provided.
    """
    execution_id = f"exec_{uuid.uuid4().hex[:8]}"
    if on_event:
        ev = create_activity_event(
            event_type="task.started",
            message="Understanding request...",
            phase=PHASE_UNDERSTANDING,
            progress=10,
            execution_id=execution_id,
        )
        if inspect.iscoroutinefunction(on_event):
            await on_event(ev)
        else:
            res = on_event(ev)
            if inspect.isawaitable(res):
                await res

    task_category = AGENT_MODE_TASK_MAP.get((agent_mode or "auto").lower())
    history = memory_manager.get_messages(session_id)
    facts = long_term_memory.get_all_facts()
    skill_instructions = skill_manager.get_active_prompt_instructions(task_category=task_category, user_message=user_message)
    messages = build_prompt(user_message, history, facts, skill_instructions=skill_instructions)

    if on_event:
        ev_plan = create_activity_event(
            event_type="planning.started",
            message="Planning task...",
            phase=PHASE_PLANNING,
            progress=30,
            execution_id=execution_id,
        )
        if inspect.iscoroutinefunction(on_event):
            await on_event(ev_plan)
        else:
            res = on_event(ev_plan)
            if inspect.isawaitable(res):
                await res

    initial_reply = await run_tool_pipeline(
        messages,
        task_category=task_category,
        selected_model=selected_model,
        user_message=user_message,
        on_event=on_event,
        execution_id=execution_id,
    )
    if initial_reply is not None:
        reply = initial_reply
    else:
        if on_event:
            ev_synth = create_activity_event(
                event_type="synthesis.started",
                message="Writing response...",
                phase=PHASE_SYNTHESIZING,
                progress=85,
                execution_id=execution_id,
            )
            if inspect.iscoroutinefunction(on_event):
                await on_event(ev_synth)
            else:
                res = on_event(ev_synth)
                if inspect.isawaitable(res):
                    await res

        # Preserve the user's explicit model choice after tool execution too.
        reply = await model_router.chat(
            messages,
            task_category=task_category,
            selected_model=selected_model,
        )

    memory_manager.add_message(session_id, "user", user_message)
    memory_manager.add_message(session_id, "assistant", reply)

    _remember_in_background(user_message)

    return reply


import inspect

async def generate_stream(
    user_message: str,
    session_id: str = DEFAULT_SESSION_ID,
    agent_mode: Optional[str] = "auto",
    selected_model: Optional[str] = None,
):
    """
    Streaming response with safe, high-level structured activity events,
    skills instructions, memory, and tool calling.
    """
    model_router.reset_request_models()
    execution_id = f"exec_{uuid.uuid4().hex[:8]}"

    # 1. Understanding & Intent Detection Phase (X002)
    yield create_activity_event(
        event_type="task.started",
        message="Understanding request & extracting intent...",
        phase=PHASE_UNDERSTANDING,
        specialist="X002 Intent Detector",
        progress=15,
        execution_id=execution_id,
    )

    # 2. Master Planning & Department Allocation (X001, X004, X005, X006)
    from skills.specialists.orchestrator import command_orchestrator
    from skills.specialists.registry import specialist_registry

    plan = command_orchestrator.plan_task(user_message, agent_mode=agent_mode)
    
    # Emit structured plan object
    yield {
        "type": "plan",
        "execution_id": execution_id,
        "plan": plan.to_dict(),
    }

    # Department & Specialists activation events
    spec_objs = [specialist_registry.get_specialist(sid) for sid in plan.specialists if specialist_registry.get_specialist(sid)]
    primary_spec = spec_objs[1] if len(spec_objs) > 1 else spec_objs[0] if spec_objs else None
    spec_names = [f"{s.id} {s.name}" for s in spec_objs[:3]]

    yield create_activity_event(
        event_type="plan.created",
        message=f"Supreme Commander (X001) activated {', '.join(plan.departments)} ({len(plan.specialists)} specialists)",
        phase=PHASE_PLANNING,
        specialist="X001 Supreme Commander",
        progress=30,
        execution_id=execution_id,
    )

    if spec_names:
        yield create_activity_event(
            event_type="specialists.selected",
            message=f"Dispatching to {', '.join(spec_names)}...",
            phase=PHASE_PLANNING,
            specialist=f"{primary_spec.id} {primary_spec.name}" if primary_spec else "X001 Supreme Commander",
            progress=45,
            execution_id=execution_id,
        )

    task_category = AGENT_MODE_TASK_MAP.get((agent_mode or "auto").lower()) or plan.intent
    history = memory_manager.get_messages(session_id)
    facts = long_term_memory.get_all_facts()
    skill_instructions = skill_manager.get_active_prompt_instructions(task_category=task_category, user_message=user_message)
    messages = build_prompt(user_message, history, facts, skill_instructions=skill_instructions)

    # 3. Tool execution phase with event queue
    event_queue: asyncio.Queue = asyncio.Queue()

    async def on_tool_event(ev: ActivityEvent):
        await event_queue.put(ev)

    pipeline_task = asyncio.create_task(
        run_tool_pipeline(
            messages,
            task_category=task_category,
            selected_model=selected_model,
            user_message=user_message,
            on_event=on_tool_event,
            execution_id=execution_id,
        )
    )

    while not pipeline_task.done():
        try:
            ev = await asyncio.wait_for(event_queue.get(), timeout=0.08)
            yield ev
        except asyncio.TimeoutError:
            continue

    while not event_queue.empty():
        yield event_queue.get_nowait()

    initial_reply = await pipeline_task
    full_reply = ""

    # 4. Synthesis / Generation phase
    yield create_activity_event(
        event_type="synthesis.started",
        message="Finalizing response...",
        phase=PHASE_SYNTHESIZING,
        progress=90,
        execution_id=execution_id,
    )

    if initial_reply is not None:
        full_reply = initial_reply
        yield initial_reply
    else:
        async for chunk in model_router.stream_chat(messages, task_category=task_category, selected_model=selected_model):
            full_reply += chunk
            yield chunk

    memory_manager.add_message(session_id, "user", user_message)
    memory_manager.add_message(session_id, "assistant", full_reply)

    _remember_in_background(user_message)



