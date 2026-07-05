from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ui.image_cmd import (
    normalize_image_path,
    parse_image_command,
    resolve_image_path,
)


class ImageCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.shot = self.root / "Снимок экрана.png"
        self.shot.write_bytes(b"\x89PNG\r\n\x1a\n")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_at_path(self) -> None:
        path, prompt = parse_image_command("/image @screenshot.png что на экране?")
        self.assertEqual(path, "screenshot.png")
        self.assertIn("экране", prompt)

    def test_plain_path(self) -> None:
        path, prompt = parse_image_command("/image screen.png")
        self.assertEqual(path, "screen.png")
        self.assertEqual(prompt, "Analyze this image.")

    def test_normalize_strips_at(self) -> None:
        self.assertEqual(normalize_image_path("@foo.png"), "foo.png")

    def test_windows_path_with_spaces_unquoted(self) -> None:
        full = str(self.shot)
        path, prompt = parse_image_command(f"/image {full} что на картинке?")
        self.assertEqual(path, full)
        self.assertIn("картинке", prompt)

    def test_quoted_cyrillic_path(self) -> None:
        full = str(self.shot)
        path, prompt = parse_image_command(f'/image "{full}"')
        self.assertEqual(path, full)
        self.assertEqual(prompt, "Analyze this image.")

    def test_resolve_fuzzy_screenshot_prefix(self) -> None:
        partial = str(self.root / "Снимок")
        resolved, error = resolve_image_path(partial)
        self.assertIsNone(error)
        assert resolved is not None
        self.assertEqual(resolved.name, "Снимок экрана.png")

    def test_resolve_missing_extension(self) -> None:
        path = self.root / "shot.png"
        path.write_bytes(b"\x89PNG\r\n\x1a\n")
        no_ext = str(self.root / "shot")
        resolved, error = resolve_image_path(no_ext)
        self.assertIsNone(error)
        assert resolved is not None
        self.assertTrue(resolved.is_file())


if __name__ == "__main__":
    unittest.main()
