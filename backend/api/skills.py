from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from skills.manager import skill_manager
from utils.logger import get_logger

logger = get_logger("api.skills")

router = APIRouter(prefix="/skills", tags=["skills"])


class ToggleSkillRequest(BaseModel):
    enabled: bool


@router.get("/")
def get_skills():
    """Returns the catalog of all discovered skills with enabled state and tools."""
    try:
        skills = skill_manager.get_all_skills()
        return {"skills": skills}
    except Exception as e:
        logger.exception("Failed to retrieve skills")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{name}/enable")
def enable_skill(name: str):
    """Enables a skill by name."""
    skill = skill_manager.get_skill(name)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")

    skill_manager.set_skill_enabled(name, True)
    return {"name": name, "enabled": True, "status": "enabled"}


@router.post("/{name}/disable")
def disable_skill(name: str):
    """Disables a skill by name (core skills cannot be disabled)."""
    skill = skill_manager.get_skill(name)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    if skill.is_core:
        raise HTTPException(status_code=400, detail=f"Skill '{name}' is a core system skill and cannot be disabled")

    skill_manager.set_skill_enabled(name, False)
    return {"name": name, "enabled": False, "status": "disabled"}


@router.post("/{name}/toggle")
def toggle_skill(name: str, request: ToggleSkillRequest):
    """Sets explicit enabled state for a skill."""
    skill = skill_manager.get_skill(name)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    if skill.is_core and not request.enabled:
        raise HTTPException(status_code=400, detail=f"Skill '{name}' is a core system skill and cannot be disabled")

    skill_manager.set_skill_enabled(name, request.enabled)
    return {"name": name, "enabled": request.enabled, "status": "updated"}


@router.get("/active")
def get_active_skills(task_category: Optional[str] = None, user_message: Optional[str] = None):
    """Returns active skills resolved for given task category or message."""
    active = skill_manager.get_active_skills(task_category=task_category, user_message=user_message)
    schemas = skill_manager.get_active_tool_schemas(task_category=task_category, user_message=user_message)
    return {
        "active_skills": [s.name for s in active],
        "tool_count": len(schemas),
        "tools": [s.get("function", {}).get("name") for s in schemas if "function" in s],
    }
