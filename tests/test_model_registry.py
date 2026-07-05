from __future__ import annotations

import unittest
from unittest.mock import patch

from ui.model_registry import normalize_model_id


class ModelRegistryTests(unittest.TestCase):
    def test_exact_id(self) -> None:
        records = {"google/gemma-4-31b-it:free": {"prompt": 0.0, "completion": 0.0}}
        with patch("pricing.fetch_model_records", return_value=records):
            self.assertEqual(
                normalize_model_id("google/gemma-4-31b-it:free"),
                "google/gemma-4-31b-it:free",
            )

    def test_short_slug(self) -> None:
        records = {
            "google/gemma-4-31b-it:free": {"prompt": 0.0, "completion": 0.0},
            "nvidia/nemotron-3-ultra-550b-a55b:free": {"prompt": 0.0, "completion": 0.0},
        }
        with patch("pricing.fetch_model_records", return_value=records):
            self.assertEqual(
                normalize_model_id("gemma-4-31b-it:free"),
                "google/gemma-4-31b-it:free",
            )

    def test_unknown_passthrough(self) -> None:
        with patch("pricing.fetch_model_records", return_value={}):
            self.assertEqual(normalize_model_id("my/custom-model"), "my/custom-model")


if __name__ == "__main__":
    unittest.main()
