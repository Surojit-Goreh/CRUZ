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
