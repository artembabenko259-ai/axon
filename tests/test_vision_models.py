from __future__ import annotations

import unittest
from unittest.mock import patch

from ui.vision_models import (
    is_confirmed_non_vision,
    is_vision_model,
    vision_capability,
)


class VisionModelTests(unittest.TestCase):
    def test_gemma4_openrouter_multimodal(self) -> None:
        records = {
            "google/gemma-4-31b-it:free": {
                "prompt": 0.0,
                "completion": 0.0,
                "input_modalities": ["image", "text", "video"],
            }
        }
        with patch("pricing.fetch_model_records", return_value=records):
            self.assertEqual(vision_capability("google/gemma-4-31b-it:free"), "yes")
            self.assertTrue(is_vision_model("google/gemma-4-31b-it:free"))
            self.assertFalse(is_confirmed_non_vision("google/gemma-4-31b-it:free"))

    def test_nemotron_openrouter_text_only(self) -> None:
        records = {
            "nvidia/nemotron-3-ultra-550b-a55b:free": {
                "prompt": 0.0,
                "completion": 0.0,
                "input_modalities": ["text"],
            }
        }
        with patch("pricing.fetch_model_records", return_value=records):
            self.assertEqual(
                vision_capability("nvidia/nemotron-3-ultra-550b-a55b:free"),
                "no",
            )
            self.assertFalse(is_vision_model("nvidia/nemotron-3-ultra-550b-a55b:free"))
            self.assertTrue(is_confirmed_non_vision("nvidia/nemotron-3-ultra-550b-a55b:free"))

    def test_unknown_model_is_optimistic(self) -> None:
        with patch("pricing.fetch_model_records", return_value={}):
            self.assertEqual(vision_capability("some/new-model"), "unknown")
            self.assertTrue(is_vision_model("some/new-model"))
            self.assertFalse(is_confirmed_non_vision("some/new-model"))

    def test_kimi_from_modalities(self) -> None:
        records = {
            "moonshotai/kimi-k2.7-code": {
                "prompt": 0.0,
                "completion": 0.0,
                "input_modalities": ["text", "image"],
            }
        }
        with patch("pricing.fetch_model_records", return_value=records):
            self.assertTrue(is_vision_model("moonshotai/kimi-k2.7-code"))

    def test_llama_text_only_from_openrouter(self) -> None:
        records = {
            "meta-llama/llama-3.1-8b-instruct": {
                "prompt": 0.0,
                "completion": 0.0,
                "input_modalities": ["text"],
            }
        }
        with patch("pricing.fetch_model_records", return_value=records):
            self.assertFalse(is_vision_model("meta-llama/llama-3.1-8b-instruct"))


if __name__ == "__main__":
    unittest.main()
