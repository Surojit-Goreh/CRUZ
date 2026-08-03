"""
Runs tool calls requested by the LLM.

This layer never thinks — it only executes what the planner/LLM already
decided, and guarantees a clean, JSON-serializable result comes back no
matter what goes wrong inside the tool.
"""
import json

from tools.registry import get_tool
from utils.validators import UnsafePathError
from utils.logger import get_logger

logger = get_logger("executor")


def execute_tool_call(name: str, arguments: dict) -> dict:
    tool = get_tool(name)

    if tool is None:
        return {"success": False, "error": f"Unknown tool '{name}'."}

    try:
        return tool(**arguments)
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


def run_tool_calls(tool_calls: list) -> list:
    """
    tool_calls: the list Ollama returns on message["tool_calls"], each
    shaped like {"function": {"name": ..., "arguments": {...}}}.

    Returns a list of {"role": "tool", ...} messages ready to append to
    the conversation and send back to the model for its final
    natural-language reply.
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

        result = execute_tool_call(name, arguments)

        results.append({
            "role": "tool",
            "name": name,
            "content": json.dumps(result),
        })

    return results
