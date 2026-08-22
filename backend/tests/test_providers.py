import unittest
import asyncio
import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.providers.registry import PROVIDERS_CATALOG
from services.providers.manager import provider_manager, mask_api_key
from services.providers.classifier import classify_task
from services.model_router import CircuitBreaker, model_router


class TestProviders(unittest.TestCase):
    def test_catalog_seeded(self):
        """Verify that all required providers exist in catalog."""
        expected_ids = {"opencode", "gemini", "groq", "openrouter", "cloudflare", "nvidia", "cruz_node", "ollama"}
        for p_id in expected_ids:
            self.assertIn(p_id, PROVIDERS_CATALOG)
            info = PROVIDERS_CATALOG[p_id]
            self.assertTrue(len(info.name) > 0)
            self.assertTrue(len(info.tier_label) > 0)
            self.assertIn("coding", info.task_models)

    def test_mask_api_key(self):
        """Verify API keys are safely masked."""
        self.assertEqual(mask_api_key(""), "")
        self.assertEqual(mask_api_key("short"), "••••••••")
        masked = mask_api_key("gsk_1234567890abcdef")
        self.assertTrue(masked.endswith("cdef"))
        self.assertNotIn("1234567890", masked)

    def test_task_classifier(self):
        """Verify rule-based task classifier for coding, reasoning, writing, vision, general."""
        # 1. Coding
        coding_msg = [{"role": "user", "content": "Can you write a python function to binary search an array? ```def search():```"}]
        self.assertEqual(classify_task(coding_msg), "coding")

        # 2. Reasoning
        reasoning_msg = [{"role": "user", "content": "Solve this complex probability math puzzle step by step and prove it."}]
        self.assertEqual(classify_task(reasoning_msg), "reasoning")

        # 3. Writing
        writing_msg = [{"role": "user", "content": "Please write an essay and story about exploring ancient Mars."}]
        self.assertEqual(classify_task(writing_msg), "writing")

        # 4. Vision
        vision_msg = [{"role": "user", "content": "What is in this picture and screenshot?"}]
        self.assertEqual(classify_task(vision_msg), "vision")

        # 5. General
        general_msg = [{"role": "user", "content": "Hello Cruz! How is the weather today?"}]
        self.assertEqual(classify_task(general_msg), "general")

    def test_dynamic_task_model_resolution(self):
        """Verify that candidate providers dynamically resolve task-specialized models."""
        coding_candidates = model_router.get_candidate_providers("coding")
        self.assertTrue(len(coding_candidates) > 0)
        self.assertEqual(coding_candidates[-1]["id"], "ollama")
        self.assertEqual(coding_candidates[-1]["model"], "qwen2.5:3b")

        reasoning_candidates = model_router.get_candidate_providers("reasoning")
        self.assertTrue(len(reasoning_candidates) > 0)
        self.assertEqual(reasoning_candidates[-1]["id"], "ollama")
        self.assertEqual(reasoning_candidates[-1]["model"], "deepseek-r1:1.5b")

    def test_circuit_breaker(self):
        """Verify circuit breaker trips and cools down after repeated failures."""
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=60.0)
        self.assertTrue(cb.is_available("groq"))

        cb.record_failure("groq")
        cb.record_failure("groq")
        self.assertTrue(cb.is_available("groq"))

        cb.record_failure("groq")
        self.assertFalse(cb.is_available("groq"))

        cb.record_success("groq")
        self.assertTrue(cb.is_available("groq"))

    def test_provider_manager_crud(self):
        """Verify provider connection persistence and status without wiping user credentials."""
        providers = provider_manager.get_all_providers()
        self.assertTrue(len(providers) >= 7)

        # Ollama is always present as local fallback
        connected = provider_manager.get_connected_providers()
        self.assertIn("ollama", connected)


if __name__ == "__main__":
    unittest.main()
