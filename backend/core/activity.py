"""
Standardized, user-safe activity and progress event model for CRUZ.

Guarantees:
- Only safe, high-level status messages are exposed to the UI.
- No chain-of-thought, internal deliberation, model thoughts, or raw prompts.
- Deterministic mapping from execution stages, tools, and skills to safe activity text.
"""
from dataclasses import dataclass, asdict
import time
from typing import Optional, Dict, Any


# Standard high-level execution phases
PHASE_UNDERSTANDING = "understanding"
PHASE_PLANNING = "planning"
PHASE_EXECUTING = "executing"
PHASE_RESEARCHING = "researching"
PHASE_ANALYZING = "analyzing"
PHASE_VERIFYING = "verifying"
PHASE_SYNTHESIZING = "synthesizing"
PHASE_COMPLETED = "completed"
PHASE_ERROR = "error"


# Deterministic tool mapping to safe user-facing specialist name and action message
TOOL_ACTIVITY_MAP: Dict[str, Dict[str, str]] = {
    # File tools
    "list_directory": {
        "specialist": "File Operations",
        "message": "Inspecting workspace directory structure...",
        "phase": PHASE_EXECUTING,
    },
    "read_file": {
        "specialist": "File Operations",
        "message": "Reading workspace file contents...",
        "phase": PHASE_EXECUTING,
    },
    "write_file": {
        "specialist": "File Operations",
        "message": "Creating and writing project files...",
        "phase": PHASE_EXECUTING,
    },
    "create_folder": {
        "specialist": "File Operations",
        "message": "Setting up directory hierarchy...",
        "phase": PHASE_EXECUTING,
    },
    "delete_path": {
        "specialist": "File Operations",
        "message": "Cleaning up workspace paths...",
        "phase": PHASE_EXECUTING,
    },
    "rename_path": {
        "specialist": "File Operations",
        "message": "Renaming workspace items...",
        "phase": PHASE_EXECUTING,
    },
    "copy_path": {
        "specialist": "File Operations",
        "message": "Duplicating project assets...",
        "phase": PHASE_EXECUTING,
    },
    "move_path": {
        "specialist": "File Operations",
        "message": "Reorganizing workspace files...",
        "phase": PHASE_EXECUTING,
    },
    "search_files": {
        "specialist": "File Operations",
        "message": "Searching workspace codebase...",
        "phase": PHASE_RESEARCHING,
    },
    "zip_path": {
        "specialist": "File Operations",
        "message": "Archiving project bundle...",
        "phase": PHASE_EXECUTING,
    },
    "extract_zip": {
        "specialist": "File Operations",
        "message": "Extracting archive contents...",
        "phase": PHASE_EXECUTING,
    },

    # Web & Research tools
    "search_web": {
        "specialist": "Web Search",
        "message": "Searching live web & documentation...",
        "phase": PHASE_RESEARCHING,
    },
    "scrape_page": {
        "specialist": "Web Researcher",
        "message": "Extracting web page content...",
        "phase": PHASE_RESEARCHING,
    },
    "crawl_site": {
        "specialist": "Web Researcher",
        "message": "Crawling domain documentation...",
        "phase": PHASE_RESEARCHING,
    },

    # Browser tools
    "open_url": {
        "specialist": "Browser Specialist",
        "message": "Navigating browser to destination...",
        "phase": PHASE_EXECUTING,
    },
    "read_page": {
        "specialist": "Browser Specialist",
        "message": "Reading active web page elements...",
        "phase": PHASE_EXECUTING,
    },
    "click_element": {
        "specialist": "Browser Specialist",
        "message": "Interacting with page controls...",
        "phase": PHASE_EXECUTING,
    },
    "type_text": {
        "specialist": "Browser Specialist",
        "message": "Entering input in browser form...",
        "phase": PHASE_EXECUTING,
    },
    "take_screenshot": {
        "specialist": "Browser Specialist",
        "message": "Capturing browser viewport snapshot...",
        "phase": PHASE_VERIFYING,
    },
    "browser_status": {
        "specialist": "Browser Specialist",
        "message": "Checking browser session state...",
        "phase": PHASE_EXECUTING,
    },
    "close_tab": {
        "specialist": "Browser Specialist",
        "message": "Closing browser tab...",
        "phase": PHASE_EXECUTING,
    },
    "close_browser": {
        "specialist": "Browser Specialist",
        "message": "Closing browser automation...",
        "phase": PHASE_EXECUTING,
    },

    # System & Desktop Automation
    "launch_app": {
        "specialist": "Desktop Automation",
        "message": "Launching system application...",
        "phase": PHASE_EXECUTING,
    },
    "get_system_stats": {
        "specialist": "System Specialist",
        "message": "Gathering system diagnostics & metrics...",
        "phase": PHASE_EXECUTING,
    },
    "set_agent_mode": {
        "specialist": "Agent Dispatcher",
        "message": "Switching active agent profile...",
        "phase": PHASE_PLANNING,
    },

    # Image Generation
    "generate_image": {
        "specialist": "Visual Designer",
        "message": "Rendering HD visual asset (Flux)...",
        "phase": PHASE_EXECUTING,
    },
}


# Category/Skill fallback mapping
CATEGORY_SPECIALIST_MAP: Dict[str, str] = {
    "coding": "Software Engineer",
    "reasoning": "Reasoning Specialist",
    "writing": "Writing Specialist",
    "vision": "Vision Specialist",
    "general": "General Assistant",
}


@dataclass
class ActivityEvent:
    """
    Structured user-safe progress event model.
    """
    event_type: str
    message: str
    phase: str = PHASE_UNDERSTANDING
    specialist: Optional[str] = None
    progress: Optional[int] = None
    execution_id: Optional[str] = None
    timestamp: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if not data["timestamp"]:
            data["timestamp"] = time.time()
        return {
            "type": "activity",
            **data,
        }


def get_tool_activity_info(tool_name: str) -> Dict[str, str]:
    """
    Returns user-safe specialist name, action message, and phase for a tool.
    Never reveals tool arguments or secrets.
    """
    if tool_name in TOOL_ACTIVITY_MAP:
        return TOOL_ACTIVITY_MAP[tool_name]

    # Clean fallback for dynamic or custom skill tools
    clean_name = tool_name.replace("_", " ").title()
    return {
        "specialist": f"{clean_name} Tool",
        "message": f"Executing {clean_name}...",
        "phase": PHASE_EXECUTING,
    }


def create_activity_event(
    event_type: str,
    message: str,
    phase: str = PHASE_UNDERSTANDING,
    specialist: Optional[str] = None,
    progress: Optional[int] = None,
    execution_id: Optional[str] = None,
) -> ActivityEvent:
    return ActivityEvent(
        event_type=event_type,
        message=message,
        phase=phase,
        specialist=specialist,
        progress=progress,
        execution_id=execution_id,
        timestamp=time.time(),
    )
