from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from config_store import save_provider_settings
from provider_config import (
    is_llm_configured,
    normalize_base_url,
    resolve_llm_endpoint,
)


class ProviderConfigTests(unittest.TestCase):
    def test_normalize_base_url(self) -> None:
        self.assertEqual(
            normalize_base_url("https://api.groq.com/openai/v1/"),
            "https://api.groq.com/openai/v1",
        )

    def test_custom_provider_endpoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_config = Path(tmp) / "config.json"
            with patch("config_store.CONFIG_PATH", fake_config):
                save_provider_settings(
                    provider="custom",
                    custom_base_url="https://api.example.com/v1",
                    custom_api_key="test-key",
                )
                base, key = resolve_llm_endpoint()
                self.assertEqual(base, "https://api.example.com/v1")
                self.assertEqual(key, "test-key")
                self.assertTrue(is_llm_configured())

    def test_ollama_does_not_require_api_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_config = Path(tmp) / "config.json"
            with patch("config_store.CONFIG_PATH", fake_config):
                save_provider_settings(
                    provider="ollama",
                    ollama_base_url="http://127.0.0.1:11434/v1",
                )
                base, key = resolve_llm_endpoint()
                self.assertIn("11434", base)
                self.assertEqual(key, "ollama")
                self.assertTrue(is_llm_configured())

    def test_antigravity_provider(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_config = Path(tmp) / "config.json"
            with patch("config_store.CONFIG_PATH", fake_config):
                save_provider_settings(
                    provider="antigravity",
                    antigravity_api_key="test-antigravity-key",
                )
                base, key = resolve_llm_endpoint()
                self.assertEqual(base, "google-antigravity-sdk")
                self.assertEqual(key, "test-antigravity-key")
                self.assertTrue(is_llm_configured())



if __name__ == "__main__":
    unittest.main()
