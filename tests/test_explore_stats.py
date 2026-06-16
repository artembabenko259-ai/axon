import unittest

from ui.explore_stats import ExploreStats, reset_turn_explore_stats, get_turn_explore_summary, record_explore_tool


class ExploreStatsTests(unittest.TestCase):
    def test_summary_files_and_searches(self) -> None:
        stats = ExploreStats()
        stats.record("read_file", "@a.py")
        stats.record("read_file", "@b.py")
        stats.record("search_code", '"foo" in @src')
        self.assertEqual(stats.summary(), "Explored 2 files, 1 search")

    def test_dedupe_same_file(self) -> None:
        stats = ExploreStats()
        stats.record("read_file", "@main.py")
        stats.record("read_file", "@main.py")
        self.assertEqual(stats.summary(), "Explored 1 file")

    def test_turn_helpers(self) -> None:
        reset_turn_explore_stats()
        record_explore_tool("glob_files", "*.py in @.")
        record_explore_tool("read_file", "@x.ts")
        self.assertEqual(get_turn_explore_summary(), "Explored 1 file, 1 search")


if __name__ == "__main__":
    unittest.main()
