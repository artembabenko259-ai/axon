import os
import tempfile
import unittest
from pathlib import Path

from audit_log import scan_secrets
from session_store import list_sessions, load_session, save_session
from skills.tools import glob_files, list_dir, read_file, write_file


class ToolsTests(unittest.TestCase):
    def test_list_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old = os.getcwd()
            os.chdir(tmp)
            try:
                root = Path(".")
                (root / "a.txt").write_text("hi", encoding="utf-8")
                out = list_dir(str(root))
                self.assertIn("a.txt", out)
            finally:
                os.chdir(old)

    def test_glob_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old = os.getcwd()
            os.chdir(tmp)
            try:
                (Path("a.py")).write_text("x", encoding="utf-8")
                out = glob_files("*.py", ".")
                self.assertIn("a.py", out)
            finally:
                os.chdir(old)

    def test_write_blocks_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old = os.getcwd()
            os.chdir(tmp)
            try:
                target = Path("secret.env")
                result = write_file(
                    str(target),
                    "OPENROUTER_API_KEY=sk-or-v1-abcdefghijklmnopqrstuvwxyz",
                )
                self.assertIn("blocked", result.lower())
            finally:
                os.chdir(old)

    def test_session_roundtrip(self) -> None:
        meta = save_session(
            session_id=None,
            messages=[{"role": "user", "content": "hello"}],
            model="test/model",
            title="Test",
        )
        loaded = load_session(meta.id)
        self.assertIsNotNone(loaded)
        assert loaded is not None
        self.assertEqual(loaded.meta.title, "Test")
        self.assertTrue(any(s.id == meta.id for s in list_sessions()))


class AuditTests(unittest.TestCase):
    def test_scan_secrets(self) -> None:
        hits = scan_secrets("token sk-or-v1-abcdefghijklmnopqrstuvwxyz")
        self.assertTrue(hits)


if __name__ == "__main__":
    unittest.main()
