import unittest
import os
import sys
from unittest.mock import patch, AsyncMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.activity import (
    ActivityEvent,
    create_activity_event,
    get_tool_activity_info,
    PHASE_UNDERSTANDING,
    PHASE_PLANNING,
    PHASE_EXECUTING,
    PHASE_RESEARCHING,
    PHASE_SYNTHESIZING,
)
from fastapi.testclient import TestClient
from api.server import app


class TestActivityEvents(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_activity_event_model(self):
        ev = create_activity_event(
            event_type="task.started",
            message="Understanding request...",
            phase=PHASE_UNDERSTANDING,
            progress=10,
            execution_id="exec_123",
        )
        d = ev.to_dict()
        self.assertEqual(d["type"], "activity")
        self.assertEqual(d["event_type"], "task.started")
        self.assertEqual(d["message"], "Understanding request...")
        self.assertEqual(d["phase"], PHASE_UNDERSTANDING)
        self.assertEqual(d["progress"], 10)
        self.assertEqual(d["execution_id"], "exec_123")
        self.assertGreater(d["timestamp"], 0)

    def test_deterministic_tool_mapping(self):
        # Web search tool
        web_info = get_tool_activity_info("search_web")
        self.assertEqual(web_info["specialist"], "Web Search")
        self.assertEqual(web_info["phase"], PHASE_RESEARCHING)

        # File tool
        file_info = get_tool_activity_info("read_file")
        self.assertEqual(file_info["specialist"], "File Operations")
        self.assertEqual(file_info["phase"], PHASE_EXECUTING)

        # Unknown / custom tool
        custom_info = get_tool_activity_info("custom_analyzer_tool")
        self.assertEqual(custom_info["specialist"], "Custom Analyzer Tool Tool")
        self.assertIn("Executing", custom_info["message"])

    @patch("brain.llm.extract_facts", new_callable=AsyncMock)
    @patch("brain.llm.model_router")
    def test_chat_stream_activity_events(self, mock_router, mock_extract):
        mock_extract.return_value = []

        async def mock_stream(*args, **kwargs):
            yield "Hello "
            yield "from CRUZ!"

        mock_router.chat_with_tools = AsyncMock(return_value={"content": "Direct reply", "tool_calls": None})
        mock_router.stream_chat = mock_stream
        mock_router.last_provider_info = {"provider_name": "TestProvider", "model": "test-model"}

        res = self.client.post(
            "/chat/stream",
            json={"message": "ping"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/event-stream", res.headers.get("content-type", ""))
        body = res.text
        self.assertIn("event: activity", body)
        self.assertIn("Understanding request...", body)
        self.assertIn("Planning task...", body)
        self.assertIn("event: done", body)


if __name__ == "__main__":
    unittest.main()
