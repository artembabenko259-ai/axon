from __future__ import annotations

import unittest

from ui.image_cmd import normalize_image_path, parse_image_command


class ImageCommandTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
