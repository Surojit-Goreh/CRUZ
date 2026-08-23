"""
Specialists REST API endpoints for CRUZ.
Provides discovery, filtering, toggling, and dynamic plan previews
for the 100-Specialist System (X001–X100).
"""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from skills.specialists.registry import specialist_registry
from skills.specialists.orchestrator import command_orchestrator

router = APIRouter(prefix="/specialists", tags=["Specialists"])


class ToggleSpecialistRequest(BaseModel):
    enabled: bool


class PlanPreviewRequest(BaseModel):
    message: str
    agent_mode: Optional[str] = "auto"


@router.get("", response_model=List[Dict[str, Any]])
async def list_specialists(
    department: Optional[str] = Query(None, description="Filter by department name"),
    search: Optional[str] = Query(None, description="Search term for specialist name, ID, or capabilities"),
    enabled_only: bool = Query(False, description="Filter only enabled specialists"),
):
    """
    Returns the complete specialist catalog, optionally filtered by department, search, or enabled status.
    """
    if search:
        specs = specialist_registry.search_specialists(search)
        if department:
            specs = [s for s in specs if s.department.lower() == department.lower()]
        if enabled_only:
            specs = [s for s in specs if s.enabled]
    else:
        specs = specialist_registry.get_all_specialists(department=department, enabled_only=enabled_only)

    return [s.to_dict() for s in specs]


@router.get("/departments", response_model=List[Dict[str, Any]])
async def list_departments():
    """
    Returns summary statistics for all 10 departments (total specialists, enabled count).
    """
    return specialist_registry.get_departments()


@router.get("/{specialist_id}", response_model=Dict[str, Any])
async def get_specialist(specialist_id: str):
    """
    Returns detailed metadata for a single specialist by ID (e.g. 'X001', 'X011').
    """
    spec = specialist_registry.get_specialist(specialist_id)
    if not spec:
        raise HTTPException(status_code=404, detail=f"Specialist '{specialist_id}' not found.")
    return spec.to_dict()


@router.post("/{specialist_id}/toggle", response_model=Dict[str, Any])
async def toggle_specialist(specialist_id: str, req: ToggleSpecialistRequest):
    """
    Toggles a specialist's enabled status and persists state to SQLite.
    Core specialists cannot be disabled.
    """
    spec = specialist_registry.get_specialist(specialist_id)
    if not spec:
        raise HTTPException(status_code=404, detail=f"Specialist '{specialist_id}' not found.")

    if spec.is_core and not req.enabled:
        raise HTTPException(status_code=400, detail=f"Specialist '{spec.id}' is a core system specialist and cannot be disabled.")

    success = specialist_registry.set_specialist_enabled(specialist_id, req.enabled)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update specialist state.")

    return {
        "id": spec.id,
        "name": spec.name,
        "department": spec.department,
        "enabled": spec.enabled,
        "message": f"Specialist '{spec.name}' ({spec.id}) set to enabled={spec.enabled}."
    }


@router.post("/plan", response_model=Dict[str, Any])
async def preview_execution_plan(req: PlanPreviewRequest):
    """
    Generates and returns the dynamic execution plan (departments, specialists, DAG subtasks)
    for a given user message.
    """
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    plan = command_orchestrator.plan_task(req.message, agent_mode=req.agent_mode)
    return plan.to_dict()
