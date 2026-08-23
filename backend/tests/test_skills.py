from fastapi.testclient import TestClient

from api.server import app
from skills.manager import skill_manager


client = TestClient(app)


def test_skills_auto_discovery():
    """Verify all 6 built-in skills are discovered on startup."""
    skills = skill_manager.get_all_skills()
    skill_names = [s["name"] for s in skills]

    assert "filesystem" in skill_names
    assert "browser" in skill_names
    assert "web_search" in skill_names
    assert "desktop" in skill_names
    assert "image_gen" in skill_names
    assert "agent_control" in skill_names
    assert len(skill_names) >= 6


def test_core_skill_cannot_be_disabled():
    """Ensure core skill 'agent_control' stays enabled even if disabled is attempted."""
    agent_skill = skill_manager.get_skill("agent_control")
    assert agent_skill is not None
    assert agent_skill.is_core is True

    # Attempting to disable core skill via set_skill_enabled should be a no-op or return True
    skill_manager.set_skill_enabled("agent_control", False)
    assert skill_manager.is_skill_enabled("agent_control") is True

    # API endpoint should return 400
    res = client.post("/skills/agent_control/disable")
    assert res.status_code == 400


def test_skill_toggle_and_persistence():
    """Test enable/disable state persistence in SQLite."""
    # Disable desktop skill
    res = client.post("/skills/desktop/disable")
    assert res.status_code == 200
    assert res.json()["enabled"] is False
    assert skill_manager.is_skill_enabled("desktop") is False

    # Check active skills does not include desktop
    active_skills = [s.name for s in skill_manager.get_active_skills()]
    assert "desktop" not in active_skills

    # Re-enable desktop skill
    res = client.post("/skills/desktop/enable")
    assert res.status_code == 200
    assert res.json()["enabled"] is True
    assert skill_manager.is_skill_enabled("desktop") is True


def test_context_aware_filtering():
    """Test category-based skill resolution and keyword triggers."""
    # In coding mode without extra keywords
    coding_skills = [s.name for s in skill_manager.get_active_skills(task_category="coding", user_message="write python function")]
    assert "filesystem" in coding_skills
    assert "agent_control" in coding_skills
    assert "desktop" not in coding_skills

    # In general mode with image trigger keyword
    image_skills = [s.name for s in skill_manager.get_active_skills(task_category="general", user_message="please generate image of a cyber cat")]
    assert "image_gen" in image_skills


def test_tool_schemas_and_registry_lookup():
    """Verify tool schemas merging and tool lookup."""
    schemas = skill_manager.get_active_tool_schemas(task_category="coding")
    tool_names = [s.get("function", {}).get("name") for s in schemas]

    assert "read_file" in tool_names
    assert "write_file" in tool_names
    assert "set_agent_mode" in tool_names

    # Resolve tool function
    tool_fn = skill_manager.get_tool("read_file")
    assert callable(tool_fn)


def test_skills_api_endpoints():
    """Test REST API /skills and /skills/active endpoints."""
    res = client.get("/skills")
    assert res.status_code == 200
    data = res.json()
    assert "skills" in data
    assert len(data["skills"]) >= 6

    res_active = client.get("/skills/active?task_category=coding")
    assert res_active.status_code == 200
    active_data = res_active.json()
    assert "active_skills" in active_data
    assert "filesystem" in active_data["active_skills"]
