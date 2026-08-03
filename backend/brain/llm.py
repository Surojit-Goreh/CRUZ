import asyncio

from brain.prompt_builder import build_prompt
from memory.extractor import extract_facts
from memory.long_term_memory import long_term_memory
from memory.memory_manager import memory_manager, DEFAULT_SESSION_ID
from services.ollama import chat, stream_chat, chat_with_tools
from executor.executor import run_tool_calls
from tools.registry import ALL_TOOL_SCHEMAS
from utils.logger import get_logger

logger = get_logger("brain.llm")

# Keeps references to fire-and-forget extraction tasks so asyncio
# doesn't garbage-collect them mid-flight; each task removes itself
# once done.
_background_tasks: set = set()

# Guards against a model getting stuck calling tools back-to-back
# without ever giving a plain-text answer. After this many rounds we
# force a final answer instead of running another tool.
MAX_TOOL_ITERATIONS = 4


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


async def _run_with_tools(messages: list) -> str:
    """
    Sends the conversation to the model with the file-tool schemas
    attached. If the model asks to call a tool, runs it locally through
    the executor and feeds the result back for a follow-up turn —
    repeating until the model responds with plain text, or
    MAX_TOOL_ITERATIONS is hit.

    `messages` is mutated in place (tool-call turns get appended to it)
    so the final list — including the tool exchange — is what's worth
    logging/debugging if something looks off.
    """
    for round_num in range(MAX_TOOL_ITERATIONS):
        message = await chat_with_tools(messages, tools=ALL_TOOL_SCHEMAS)
        tool_calls = message.get("tool_calls")

        if not tool_calls:
            if round_num == 0:
                # The model answered in plain text on the very first
                # round, with no tool call at all. Logged at INFO so you
                # can check cruz.log after a turn like "delete X" and
                # confirm whether CRUZ actually reached for a tool or
                # just talked about it — if you expected a tool call and
                # don't see one logged here, the model chose not to call
                # it (prompt/model issue), not a wiring bug.
                logger.info("model answered without calling any tool")
            return message.get("content", "")

        tool_names = [c.get("function", {}).get("name") for c in tool_calls]
        logger.info(f"round {round_num}: model called tool(s) {tool_names}")

        messages.append(message)
        messages.extend(run_tool_calls(tool_calls))

    # Model kept requesting tools past the limit — cut it off and force
    # a plain answer with whatever it's learned from the tool results so far.
    logger.warning(f"hit MAX_TOOL_ITERATIONS ({MAX_TOOL_ITERATIONS}), forcing a final answer")
    final_reply = await chat(messages)
    return final_reply


async def generate_response(user_message: str, session_id: str = DEFAULT_SESSION_ID):
    """
    Normal (non-streaming) response, with short-term + long-term memory
    and file-operation tool calling.
    """
    history = memory_manager.get_messages(session_id)
    facts = long_term_memory.get_all_facts()
    messages = build_prompt(user_message, history, facts)

    reply = await _run_with_tools(messages)

    memory_manager.add_message(session_id, "user", user_message)
    memory_manager.add_message(session_id, "assistant", reply)

    _remember_in_background(user_message)

    return reply


async def generate_stream(user_message: str, session_id: str = DEFAULT_SESSION_ID):
    """
    Streaming response, with short-term + long-term memory.

    Tool calling is NOT wired into streaming yet — Ollama can stream a
    tool-calling turn, but the intermediate "call a tool, wait, then
    stream the real answer" flow doesn't map cleanly onto a single
    token stream. Typed/streamed chat gets plain answers for now;
    generate_response() (used by voice) gets file-tool access. Worth
    revisiting if streamed tool use becomes important later.

    The full reply has to be buffered as it streams out, because we only
    know what CRUZ actually said once the last chunk arrives — that's
    what gets saved to memory, not the individual chunks.
    """
    history = memory_manager.get_messages(session_id)
    facts = long_term_memory.get_all_facts()
    messages = build_prompt(user_message, history, facts)

    full_reply = ""

    async for chunk in stream_chat(messages):
        full_reply += chunk
        yield chunk

    memory_manager.add_message(session_id, "user", user_message)
    memory_manager.add_message(session_id, "assistant", full_reply)

    _remember_in_background(user_message)
