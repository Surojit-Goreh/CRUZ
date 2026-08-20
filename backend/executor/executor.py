"""
Runs tool calls requested by the LLM.

This layer never thinks — it only executes what the planner/LLM already
decided, and guarantees a clean, JSON-serializable result comes back no
matter what goes wrong inside the tool.
"""
import inspect
import json

from tools.registry import get_tool
from utils.validators import UnsafePathError
from utils.logger import get_logger

logger = get_logger("executor")


async def execute_tool_call(name: str, arguments: dict) -> dict:
    tool = get_tool(name)

    if tool is None:
        return {"success": False, "error": f"Unknown tool '{name}'."}

    try:
        result = tool(**arguments)
        if inspect.isawaitable(result):
            result = await result
        return result
    except UnsafePathError as e:
        # Expected/handled — the tool refused to do something unsafe.
        logger.warning(f"blocked unsafe call to {name}({arguments}): {e}")
        return {"success": False, "error": str(e)}
    except TypeError as e:
        # Wrong/missing arguments from the model.
        logger.warning(f"bad arguments for {name}({arguments}): {e}")
        return {"success": False, "error": f"Invalid arguments for '{name}': {e}"}
    except Exception as e:
        # Anything unexpected — never let a tool crash the request.
        logger.exception(f"tool '{name}' failed")
        return {"success": False, "error": f"'{name}' failed: {e}"}


async def run_tool_calls(tool_calls: list) -> list:
    """
    tool_calls: the list model_router returns on message["tool_calls"], each
    shaped like {"id": ..., "type": "function", "function": {"name": ..., "arguments": {...}}}.
    `id` is guaranteed present by brain/llm.py before this is called, even
    for providers (like older Ollama) that don't supply one natively.

    Returns a list of {"role": "tool", "tool_call_id": ..., ...} messages
    ready to append to the conversation and send back to the model for its
    final natural-language reply. `tool_call_id` must match the `id` on the
    corresponding assistant tool_calls entry — OpenAI-compatible APIs (and
    Ollama's /api/chat) reject the request without it.
    """
    results = []

    for call in tool_calls:
        fn = call.get("function", {})
        name = fn.get("name")
        arguments = fn.get("arguments") or {}

        # Depending on model/Ollama version, arguments can arrive as a
        # dict already or as a raw JSON string — handle both.
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = {}

        result = await execute_tool_call(name, arguments)

        results.append({
            "role": "tool",
            "tool_call_id": call.get("id"),
            "name": name,
            "content": json.dumps(result),
        })

    return results