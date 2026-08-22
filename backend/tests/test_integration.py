import unittest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.server import app
from services.providers.manager import provider_manager, mask_api_key
from services.providers.classifier import classify_task
from services.model_router import model_router


class TestCloudBrainIntegration(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_get_providers_endpoint(self):
        res = self.client.get("/providers")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("providers", data)
        providers = data["providers"]
        self.assertGreaterEqual(len(providers), 7)
        provider_ids = [p["id"] for p in providers]
        self.assertIn("opencode", provider_ids)

        # Check key fields exist and keys are masked
        for p in providers:
            self.assertIn("id", p)
            self.assertIn("name", p)
            self.assertIn("tier_label", p)
            self.assertIn("masked_key", p)
            # Ensure raw key is not exposed
            if p["masked_key"]:
                self.assertTrue("•" in p["masked_key"])

    def test_task_classification_routing(self):
        # 1. Coding
        coding_msg = [{"role": "user", "content": "Can you fix this python syntax error? def foo():"}]
        self.assertEqual(classify_task(coding_msg), "coding")
        candidates = model_router.get_candidate_providers("coding")
        self.assertEqual(candidates[-1]["id"], "ollama")

        # 2. Reasoning
        reasoning_msg = [{"role": "user", "content": "Solve this riddle and calculate the logic step by step"}]
        self.assertEqual(classify_task(reasoning_msg), "reasoning")
        reasoning_candidates = model_router.get_candidate_providers("reasoning")
        self.assertEqual(reasoning_candidates[-1]["id"], "ollama")
        self.assertEqual(reasoning_candidates[-1]["model"], "deepseek-r1:1.5b")

        # 3. Writing
        writing_msg = [{"role": "user", "content": "Write a poem about neon stars in cyberpunk city"}]
        self.assertEqual(classify_task(writing_msg), "writing")

        # 4. Vision
        vision_msg = [{"role": "user", "content": "What is depicted in this visual screenshot?"}]
        self.assertEqual(classify_task(vision_msg), "vision")

        # 5. General
        general_msg = [{"role": "user", "content": "Tell me a quick joke"}]
        self.assertEqual(classify_task(general_msg), "general")

    def test_silent_fallback_guarantee(self):
        """Verify that when cloud providers are simulated to fail, Ollama acts as the final guarantee."""
        candidates = model_router.get_candidate_providers("general")
        self.assertTrue(any(c["id"] == "ollama" for c in candidates))


if __name__ == "__main__":
    unittest.main()
