from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ui.code_diff import build_approval_preview, split_approval_message
from ui import tui_render


class CodeDiffTests(unittest.TestCase):
    def test_write_file_preview_shows_added_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.py"
            path.write_text("old\n", encoding="utf-8")
            preview = build_approval_preview(
                "write_file",
                {"filepath": str(path), "content": "old\nnew\n"},
            )
        self.assertIn("@@", preview)
        self.assertIn("+new", preview)

    def test_split_approval_message(self) -> None:
        from ui.code_diff import APPROVAL_PREVIEW_MARKER, combine_approval_message

        combined = combine_approval_message("@file.py", "@@ file (+1 -0)\n+line")
        detail, preview = split_approval_message(combined)
        self.assertEqual(detail, "@file.py")
        self.assertIn("+line", preview)
        self.assertIn(APPROVAL_PREVIEW_MARKER, combined)

    def test_render_change_preview_formats_cursor_style(self) -> None:
        block = tui_render.render_change_preview(
            "@@ ui/test.py (+1 -1)\n-old\n+new",
            80,
        )
        self.assertIn("@@ ui/test.py", block)
        self.assertIn("- old", block)
        self.assertIn("+ new", block)


if __name__ == "__main__":
    unittest.main()
