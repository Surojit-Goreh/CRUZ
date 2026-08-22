"""
System automation tools: Read-only system resource monitoring (CPU %, RAM, Battery, Disk space).
"""
import psutil
from typing import Dict, Any
from utils.logger import get_logger

logger = get_logger("tools.system")


async def get_system_stats() -> Dict[str, Any]:
    """
    Retrieves read-only system resource usage (CPU %, RAM %, Battery %, Disk free space).
    """
    try:
        cpu_usage = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        battery = psutil.sensors_battery()

        return {
            "success": True,
            "cpu_percent": cpu_usage,
            "ram_used_gb": round(ram.used / (1024 ** 3), 2),
            "ram_total_gb": round(ram.total / (1024 ** 3), 2),
            "ram_percent": ram.percent,
            "disk_free_gb": round(disk.free / (1024 ** 3), 2),
            "battery_percent": battery.percent if battery else None,
            "power_plugged": battery.power_plugged if battery else None,
        }
    except Exception as e:
        logger.error(f"Failed to get system stats: {e}")
        return {"success": False, "error": str(e)}


VALID_AGENT_MODES = {
    "auto": "Auto Dispatcher",
    "build": "Build Agent (Coding)",
    "coding": "Build Agent (Coding)",
    "plan": "Plan Agent (Deep Reasoning)",
    "reasoning": "Plan Agent (Deep Reasoning)",
    "image": "Image / Vision Agent",
    "vision": "Image / Vision Agent",
    "writing": "Writer Agent",
    "writer": "Writer Agent",
    "chat": "Fast Chat",
    "general": "Fast Chat",
}


def set_agent_mode(mode: str) -> str:
    """
    Switches CRUZ's active agent mode dynamically (e.g. 'plan', 'build', 'image', 'writing', 'chat', 'auto').
    """
    normalized = mode.strip().lower()
    canonical = {
        "reasoning": "plan",
        "coding": "build",
        "vision": "image",
        "writer": "writing",
        "general": "chat",
        "speed": "chat",
    }.get(normalized, normalized)

    if canonical not in ["auto", "build", "plan", "image", "writing", "chat"]:
        return f"Unknown mode '{mode}'. Available modes are: auto, build (coding), plan (reasoning), image (vision), writing, chat."

    display_name = VALID_AGENT_MODES.get(canonical, canonical.title())
    logger.info(f"Agent mode switched to '{canonical}' ({display_name})")
    return f"AGENT_MODE_SWITCH:{canonical}: Switched active mode to {display_name}. I will now handle your requests with specialized models."
