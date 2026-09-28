import inspect
import json
import unittest
from unittest.mock import Mock, patch


from app.tools.web_search import (
    SEARCH_ENDPOINT,
    MAX_RESULTS,
    MAX_QUERY_LENGTH,
    web_search,
)


RESULT_HTML = """
<html><body>
  <div class="result">
    <a class="result__a" href="https://example.com/article">Example title</a>
    <a class="result__snippet">Example summary</a>
  </div>
  <div class="result">
    <a class="result__a" href="https://example.org/second">Second title</a>
    <a class="result__snippet">Second summary</a>
  </div>
</body></html>
"""


class WebSearchTests(unittest.TestCase):
    def _client_response(self, html: str = RESULT_HTML) -> Mock:
        response = Mock()
        response.content = html.encode("utf-8")
        response.text = html
        response.iter_bytes.return_value = [response.content]
        response.raise_for_status.return_value = None
        return response

    def test_rejects_empty_query_without_http_request(self) -> None:
        with patch("app.tools.web_search.httpx.Client") as client_cls:
            result = json.loads(web_search.invoke({"query": "   "}))

        self.assertIn("error", result)
        client_cls.assert_not_called()

    def test_rejects_overlong_query_without_http_request(self) -> None:
        query = "x" * (MAX_QUERY_LENGTH + 1)
        with patch("app.tools.web_search.httpx.Client") as client_cls:
            result = json.loads(web_search.invoke({"query": query}))

        self.assertIn("error", result)
        client_cls.assert_not_called()

    def test_uses_only_fixed_get_endpoint_without_redirects(self) -> None:
        response = self._client_response()
        stream = Mock()
        stream.__enter__ = Mock(return_value=response)
        stream.__exit__ = Mock(return_value=None)
        with patch("app.tools.web_search.httpx.Client") as client_cls:
            client_cls.return_value.__enter__.return_value.stream.return_value = stream
            result = json.loads(web_search.invoke({"query": "latest python"}))

        self.assertEqual(result["results"][0]["url"], "https://example.com/article")
        self.assertEqual(result["results"][0]["snippet"], "Example summary")
        client_cls.assert_called_once()
        client_kwargs = client_cls.call_args.kwargs
        self.assertFalse(client_kwargs["follow_redirects"])
        client_cls.return_value.__enter__.return_value.stream.assert_called_once_with(
            "GET",
            SEARCH_ENDPOINT,
            params={"q": "latest python"},
        )

    def test_stops_when_streamed_response_exceeds_size_limit(self) -> None:
        response = self._client_response()
        response.iter_bytes.return_value = [b"x" * (2 * 1024 * 1024 + 1)]
        stream = Mock()
        stream.__enter__ = Mock(return_value=response)
        stream.__exit__ = Mock(return_value=None)
        with patch("app.tools.web_search.httpx.Client") as client_cls:
            client_cls.return_value.__enter__.return_value.stream.return_value = stream
            result = json.loads(web_search.invoke({"query": "large response"}))

        self.assertEqual(result, {"error": "搜索响应超过允许大小"})

    def test_limits_result_count_and_returns_untrusted_content_warning(self) -> None:
        result_html = "".join(
            f'<div class="result"><a class="result__a" href="https://example.com/{i}">Title {i}</a>'
            f'<a class="result__snippet">Summary {i}</a></div>'
            for i in range(MAX_RESULTS + 3)
        )
        response = self._client_response(result_html)
        stream = Mock()
        stream.__enter__ = Mock(return_value=response)
        stream.__exit__ = Mock(return_value=None)
        with patch("app.tools.web_search.httpx.Client") as client_cls:
            client_cls.return_value.__enter__.return_value.stream.return_value = stream
            result = json.loads(
                web_search.invoke({"query": "python", "max_results": MAX_RESULTS + 20})
            )

        self.assertEqual(len(result["results"]), MAX_RESULTS)
        self.assertIn("不可信", result["warning"])
        self.assertEqual(result["source"], SEARCH_ENDPOINT)
        self.assertTrue(result["retrieved_at"])

    def test_tool_does_not_accept_a_url_argument(self) -> None:
        parameters = inspect.signature(web_search.func).parameters
        self.assertNotIn("url", parameters)
        self.assertNotIn("method", parameters)
        self.assertNotIn("headers", parameters)


if __name__ == "__main__":
    unittest.main()
