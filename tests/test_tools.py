import os
import tempfile
import unittest
from pathlib import Path

from audit_log import scan_secrets
from session_store import list_sessions, load_session, save_session
from skills.tools import (
    format_tool_activity,
    glob_files,
    list_dir,
    read_file,
    tool_activity_detail,
    write_file,
)


class ToolActivityTests(unittest.TestCase):
    def test_read_file_activity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old = os.getcwd()
            os.chdir(tmp)
            try:
                path = Path("src/main.py")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("x", encoding="utf-8")
                detail = tool_activity_detail("read_file", {"filepath": str(path)})
                self.assertEqual(detail, "@src/main.py")
                line = format_tool_activity("read_file", {"filepath": str(path)})
                self.assertEqual(line, "Read @src/main.py")
            finally:
                os.chdir(old)

    def test_grep_activity(self) -> None:
        line = format_tool_activity(
            "search_code",
            {"pattern": "def main", "path": "."},
        )
        self.assertIn("Grep", line)
        self.assertIn('"def main"', line)
        self.assertIn("@.", line)

    def test_shell_activity_truncates(self) -> None:
        cmd = "echo " + "x" * 200
        detail = tool_activity_detail("execute_shell", {"command": cmd})
        self.assertLessEqual(len(detail), 96)


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

    def test_read_file_cache_skips_unchanged_content(self) -> None:
        from skills.tools import clear_read_file_cache, read_file

        clear_read_file_cache()
        with tempfile.TemporaryDirectory() as tmp:
            previous = os.getcwd()
            try:
                os.chdir(tmp)
                path = Path("sample.txt")
                path.write_text("hello cache", encoding="utf-8")
                first = read_file(str(path))
                second = read_file(str(path))
            finally:
                os.chdir(previous)
        self.assertIn("hello cache", first)
        self.assertIn("Cached", second)
        self.assertNotIn("hello cache", second)


class VersionTests(unittest.TestCase):
    def test_compare_versions(self) -> None:
        from version_check import compare_versions

        self.assertEqual(compare_versions("1.0.0", "1.0.1"), -1)
        self.assertEqual(compare_versions("1.0.0", "1.0.0"), 0)
        self.assertEqual(compare_versions("1.2.0", "1.1.9"), 1)


if __name__ == "__main__":
    unittest.main()
