import unittest
from pathlib import Path


class MarkdownRendererTests(unittest.TestCase):
    def test_markdown_renderer_module_contains_safe_rich_formatting(self) -> None:
        source = (Path(__file__).parents[1] / "frontend" / "markdown.js").read_text(
            encoding="utf-8"
        )

        self.assertIn("function renderMarkdown", source)
        self.assertIn("escapeHtml", source)
        self.assertIn("<table>", source)
        self.assertIn("<strong>", source)
        self.assertIn("<pre><code", source)
        self.assertIn("window.renderMarkdown", source)


if __name__ == "__main__":
    unittest.main()
