import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.api.daily import asian_games


class AsianGamesApiTests(unittest.TestCase):
    @patch("app.api.daily.asian_games_feed")
    def test_proxy_returns_service_payload(self, feed):
        feed.return_value = {"date": "2026-09-23", "finished": [], "live": [], "upcoming": [], "total": 0}

        result = asian_games("2026-09-23")

        self.assertEqual(result["date"], "2026-09-23")
        feed.assert_called_once_with("2026-09-23")

    def test_proxy_rejects_invalid_date_as_bad_request(self):
        with patch("app.api.daily.asian_games_feed", side_effect=ValueError("日期必须为 YYYY-MM-DD")):
            with self.assertRaises(HTTPException) as context:
                asian_games("bad-date")

        self.assertEqual(context.exception.status_code, 400)

    def test_proxy_maps_provider_failure_to_bad_gateway(self):
        with patch("app.api.daily.asian_games_feed", side_effect=RuntimeError("provider down")):
            with self.assertRaises(HTTPException) as context:
                asian_games("2026-09-23")

        self.assertEqual(context.exception.status_code, 502)


if __name__ == "__main__":
    unittest.main()
