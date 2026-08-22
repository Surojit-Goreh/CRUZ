import unittest
import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.image import generate_image
from tools.system import set_agent_mode
from tools.registry import TOOL_REGISTRY, ALL_TOOL_SCHEMAS
from tools.desktop import launch_app


class TestTools(unittest.TestCase):
    def test_generate_image(self):
        """Verify image generator creates high-res Flux Markdown snippet."""
        result = generate_image("A futuristic cyberpunk city in Kolkata", aspect_ratio="16:9")
        self.assertIn("![A futuristic cyberpunk city in Kolkata]", result)
        self.assertTrue("generated_images" in result or "pollinations.ai" in result)
        self.assertIn("Flux", result.replace("FLUX", "Flux"))

    def test_set_agent_mode(self):
        """Verify dynamic agent mode switching and canonicalization."""
        # 1. Reasoning -> Plan
        res1 = set_agent_mode("reasoning")
        self.assertIn("AGENT_MODE_SWITCH:plan:", res1)

        # 2. Build -> Build
        res2 = set_agent_mode("build")
        self.assertIn("AGENT_MODE_SWITCH:build:", res2)

        # 3. Vision -> Image
        res3 = set_agent_mode("vision")
        self.assertIn("AGENT_MODE_SWITCH:image:", res3)

        # 4. Fast Chat -> Chat
        res4 = set_agent_mode("chat")
        self.assertIn("AGENT_MODE_SWITCH:chat:", res4)

        # 5. Invalid mode
        res5 = set_agent_mode("invalid_super_mode")
        self.assertIn("Unknown mode", res5)

    def test_tool_registry(self):
        """Verify tools are registered in TOOL_REGISTRY and ALL_TOOL_SCHEMAS."""
        self.assertIn("generate_image", TOOL_REGISTRY)
        self.assertIn("set_agent_mode", TOOL_REGISTRY)
        schema_names = [s["function"]["name"] for s in ALL_TOOL_SCHEMAS]
        self.assertIn("generate_image", schema_names)
        self.assertIn("set_agent_mode", schema_names)
        self.assertNotIn("close_app", TOOL_REGISTRY)
        self.assertNotIn("close_app", schema_names)

    def test_desktop_launch_rejects_untrusted_inputs(self):
        unknown = asyncio.run(launch_app("cmd /c whoami"))
        with_args = asyncio.run(launch_app("notepad", "C:\\Windows\\System32"))
        self.assertFalse(unknown["success"])
        self.assertFalse(with_args["success"])


if __name__ == "__main__":
    unittest.main()
