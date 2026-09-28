import unittest
from unittest.mock import patch

import httpx

from app.main import create_app
from app.services.stocks import StockDataError


class StocksApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app()),
            base_url="http://testserver",
        )

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_quotes_returns_service_json_unchanged(self):
        payload = {"source": "test", "quotes": [{"code": "600519", "last_price": None}]}
        with patch("app.api.stocks.get_stock_quotes", return_value=payload) as get_quotes:
            response = await self.client.get("/api/stocks/quotes")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), payload)
        get_quotes.assert_called_once_with()

    async def test_history_returns_service_json_unchanged(self):
        payload = {"code": "600519", "period": "1y", "bars": []}
        with patch("app.api.stocks.get_stock_history", return_value=payload) as get_history:
            response = await self.client.get("/api/stocks/600519/history?period=1y")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), payload)
        get_history.assert_called_once_with("600519", "1y")

    async def test_unknown_code_returns_bad_request(self):
        with patch(
            "app.api.stocks.get_stock_history",
            side_effect=ValueError("不支持的股票代码"),
        ) as get_history:
            response = await self.client.get("/api/stocks/999999/history?period=6m")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"detail": "不支持的股票代码"})
        get_history.assert_called_once_with("999999", "6m")

    async def test_unsupported_period_returns_bad_request(self):
        with patch(
            "app.api.stocks.get_stock_history",
            side_effect=ValueError("周期仅支持 6m 或 1y"),
        ) as get_history:
            response = await self.client.get("/api/stocks/600519/history?period=5y")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"detail": "周期仅支持 6m 或 1y"})
        get_history.assert_called_once_with("600519", "5y")

    async def test_quote_provider_error_returns_sanitized_bad_gateway(self):
        with patch(
            "app.api.stocks.get_stock_quotes",
            side_effect=StockDataError("private upstream detail"),
        ) as get_quotes:
            response = await self.client.get("/api/stocks/quotes")

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json(), {"detail": "Stock data unavailable"})
        self.assertNotIn("private upstream detail", response.text)
        get_quotes.assert_called_once_with()

    async def test_history_provider_error_returns_sanitized_bad_gateway(self):
        with patch(
            "app.api.stocks.get_stock_history",
            side_effect=StockDataError("private upstream detail"),
        ) as get_history:
            response = await self.client.get("/api/stocks/600519/history?period=6m")

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json(), {"detail": "Stock data unavailable"})
        self.assertNotIn("private upstream detail", response.text)
        get_history.assert_called_once_with("600519", "6m")


if __name__ == "__main__":
    unittest.main()
