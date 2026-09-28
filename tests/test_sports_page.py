import unittest
from pathlib import Path


class SportsPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (Path(__file__).parents[1] / "frontend" / "ui" / "sports.html").read_text(encoding="utf-8")

    def test_page_is_asian_games_only(self):
        self.assertIn("2026 年亚运会", self.source)
        self.assertIn("/api/sports/asian-games", self.source)
        self.assertNotIn("NBA", self.source)
        self.assertNotIn("世界杯", self.source)
        self.assertNotIn("热火", self.source)

    def test_page_supports_date_navigation_and_status_groups(self):
        for text in ("前一天", "今天", "后一天", "已结束", "进行中", "待开始", "项目"):
            self.assertIn(text, self.source)
        self.assertIn("finished", self.source)
        self.assertIn("live", self.source)
        self.assertIn("upcoming", self.source)


if __name__ == "__main__":
    unittest.main()
