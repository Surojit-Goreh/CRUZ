from typing import List, Dict, Any, Callable, Optional
from skills.base import BaseSkill
from tools import desktop, system
from tools.schemas import SYSTEM_DESKTOP_TOOL_SCHEMAS


class DesktopSkill(BaseSkill):
    name = "desktop"
    display_name = "Desktop & System Stats"
    description = "Launch allowlisted Windows desktop applications (Notepad, Calculator, VS Code, Chrome, Spotify) and monitor system CPU, RAM, Disk, and Battery stats."
    icon = "Laptop"
    version = "1.0.0"
    is_core = False
    enabled_by_default = True

    task_categories = ["general"]
    trigger_keywords = [
        "launch", "open app", "start app", "notepad", "calculator", "calc",
        "spotify", "vscode", "chrome", "system stats", "cpu", "ram", "battery", "memory usage"
    ]

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return SYSTEM_DESKTOP_TOOL_SCHEMAS

    def get_tool_registry(self) -> Dict[str, Callable]:
        return {
            "launch_app": desktop.launch_app,
            "get_system_stats": system.get_system_stats,
        }

    def get_prompt_instructions(self) -> Optional[str]:
        return (
            "DESKTOP AUTOMATION GUIDELINES:\n"
            "- Use 'launch_app' for allowlisted Windows applications.\n"
            "- Use 'get_system_stats' when user asks about machine health or resource usage."
        )


