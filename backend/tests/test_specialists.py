from fastapi.testclient import TestClient

from api.server import app
from skills.specialists.registry import specialist_registry, ALL_DEPARTMENTS
from skills.specialists.orchestrator import command_orchestrator
from skills.specialists.models import TaskContext


def test_100_specialists_catalog_integrity():
    """Verify that all 100 specialists (X001-X100) are loaded with valid IDs, departments, and capabilities."""
    specs = specialist_registry.get_all_specialists()
    assert len(specs) == 100, f"Expected 100 specialists, got {len(specs)}"

    # Check ID sequence X001 to X100
    for i in range(1, 101):
        expected_id = f"X{i:03d}"
        spec = specialist_registry.get_specialist(expected_id)
        assert spec is not None, f"Specialist {expected_id} is missing from registry"
        assert spec.id == expected_id
        assert len(spec.name) > 0
        assert spec.department in ALL_DEPARTMENTS
        assert len(spec.capabilities) > 0


def test_10_departments_breakdown():
    """Verify all 10 departments contain exactly 10 specialists each."""
    depts = specialist_registry.get_departments()
    assert len(depts) == 10

    for d in depts:
        assert d["total_specialists"] == 10, f"Department {d['name']} has {d['total_specialists']} specialists instead of 10"
        assert d["enabled_specialists"] >= 0


def test_capability_search_and_matching():
    """Test searching and matching specialists by capability keywords."""
    python_matches = specialist_registry.find_specialists_by_capabilities(["python", "fastapi"], department="Coding")
    assert len(python_matches) > 0
    assert any(s.id == "X011" for s in python_matches)  # Python Developer

    search_res = specialist_registry.search_specialists("Supreme Judge")
    assert len(search_res) == 1
    assert search_res[0].id == "X100"


def test_specialist_toggle_and_core_protection():
    """Verify core specialists cannot be disabled, while non-core can be toggled."""
    # X001 is core
    x001_toggle = specialist_registry.set_specialist_enabled("X001", False)
    assert x001_toggle is False, "Core specialist X001 should not be disableable"

    # X011 is non-core
    x011_toggle = specialist_registry.set_specialist_enabled("X011", False)
    assert x011_toggle is True
    spec = specialist_registry.get_specialist("X011")
    assert spec.enabled is False

    # Restore
    specialist_registry.set_specialist_enabled("X011", True)
    assert specialist_registry.get_specialist("X011").enabled is True


def test_dynamic_task_planning():
    """Test dynamic execution planning with DAG subtask generation."""
    # 1. Coding task
    plan1 = command_orchestrator.plan_task("fix the python async race condition in websocket stream")
    assert plan1.intent == "coding"
    assert "Coding" in plan1.departments
    assert "Quality" in plan1.departments
    assert any(st.specialist_id in ["X011", "X017", "X020"] for st in plan1.subtasks)
    assert plan1.subtasks[-1].specialist_id == "X010"  # Final synthesizer at the end

    # 2. Simple greeting (fast path)
    plan2 = command_orchestrator.plan_task("hi how are you")
    assert plan2.intent == "general"
    assert plan2.complexity == "simple"
    assert len(plan2.subtasks) == 1
    assert plan2.subtasks[0].specialist_id == "X010"


def test_quality_evaluation():
    """Test Quality Department evaluation (X091-X100)."""
    ctx = TaskContext()

    # Valid output
    v1 = command_orchestrator.evaluate_quality("Here are the top 3 monitors under 10000 with detailed specs...", ctx)
    assert v1.verdict in ["PASS", "PASS_WITH_WARNINGS"]
    assert v1.score >= 80.0

    # Output with raw tool tags
    v2 = command_orchestrator.evaluate_quality("<tool_call> <function=read_page> </tool_call>", ctx)
    assert len(v2.criticisms) > 0
    assert any("tool markup" in c.lower() for c in v2.criticisms)

    # Empty output
    v3 = command_orchestrator.evaluate_quality("", ctx)
    assert v3.verdict == "FAIL"


def test_rest_api_endpoints():
    """Test FastAPI REST endpoints for the specialists system."""
    client = TestClient(app)

    # GET /specialists
    res = client.get("/specialists")
    assert res.status_code == 200
    assert len(res.json()) == 100

    # GET /specialists?department=Coding
    res_coding = client.get("/specialists?department=Coding")
    assert res_coding.status_code == 200
    assert len(res_coding.json()) == 10

    # GET /specialists/departments
    res_depts = client.get("/specialists/departments")
    assert res_depts.status_code == 200
    assert len(res_depts.json()) == 10

    # GET /specialists/X001
    res_x001 = client.get("/specialists/X001")
    assert res_x001.status_code == 200
    assert res_x001.json()["name"] == "Supreme Commander"

    # POST /specialists/plan
    res_plan = client.post("/specialists/plan", json={"message": "generate a realistic visual prompt for cyberpunk city"})
    assert res_plan.status_code == 200
    data = res_plan.json()
    assert "Visual" in data["departments"]
    assert len(data["subtasks"]) > 0
