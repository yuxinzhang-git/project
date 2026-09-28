import unittest
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfoNotFoundError

import httpx

from app.services.stocks import (
    _CACHE,
    StockDataError,
    get_stock_history,
    get_stock_quotes,
)


def response(payload):
    result = Mock()
    result.raise_for_status.return_value = None
    result.json.return_value = payload
    return result


class StocksServiceTests(unittest.TestCase):
    def setUp(self):
        _CACHE.clear()

    def test_normalizes_quotes_and_financial_report(self):
        quote_payload = {
            "data": {"diff": [
                {"f12": "600519", "f13": 1, "f14": "贵州茅台", "f2": 1488,
                 "f3": 1.21, "f4": 17.8, "f5": 12345, "f6": 123456789,
                 "f9": 24.6, "f15": 1490, "f16": 1468, "f17": 1472,
                 "f18": 1470.2, "f23": 8.1},
                {"f12": "000300", "f13": 1, "f14": "沪深300", "f2": 4000,
                 "f3": 0.5, "f4": 20, "f5": 100, "f6": 200000,
                 "f9": "-", "f15": 4010, "f16": 3980, "f17": 3990,
                 "f18": 3980, "f23": "-"},
                {"f12": "601318", "f13": 1, "f14": "中国平安", "f3": "-",
                 "f4": "-", "f5": "", "f6": None, "f9": "not-a-number",
                 "f15": "NaN", "f16": "Infinity", "f23": "-"},
            ]}
        }
        finance_payload = {"result": {"data": [
            {"SECURITY_CODE": "600519", "REPORT_DATE": "2026-06-30T00:00:00", "WEIGHTAVG_ROE": 34.8}
        ]}}

        with patch("app.services.stocks.httpx.Client") as client_class:
            client = client_class.return_value.__enter__.return_value
            client.get.side_effect = [response(quote_payload), response(finance_payload)]
            result = get_stock_quotes()

        maotai = next(row for row in result["quotes"] if row["code"] == "600519")
        self.assertEqual(maotai["last_price"], 1488.0)
        self.assertEqual(maotai["change_pct"], 1.21)
        self.assertEqual(maotai["change_amount"], 17.8)
        self.assertEqual(maotai["volume_hands"], 12345.0)
        self.assertEqual(maotai["amount_yuan"], 123456789.0)
        self.assertEqual(maotai["pe_dynamic"], 24.6)
        self.assertEqual(maotai["high"], 1490.0)
        self.assertEqual(maotai["low"], 1468.0)
        self.assertEqual(maotai["open"], 1472.0)
        self.assertEqual(maotai["previous_close"], 1470.2)
        self.assertEqual(maotai["pb"], 8.1)
        self.assertEqual(maotai["roe"], 34.8)
        self.assertEqual(maotai["roe_report_date"], "2026-06-30")

        pingan = next(row for row in result["quotes"] if row["code"] == "601318")
        self.assertTrue(pingan["available"])
        self.assertIsNone(pingan["last_price"])
        self.assertIsNone(pingan["change_pct"])
        self.assertIsNone(pingan["change_amount"])
        self.assertIsNone(pingan["volume_hands"])
        self.assertIsNone(pingan["amount_yuan"])
        self.assertIsNone(pingan["pe_dynamic"])
        self.assertIsNone(pingan["high"])
        self.assertIsNone(pingan["low"])
        self.assertIsNone(pingan["pb"])

        unavailable = next(row for row in result["quotes"] if row["code"] == "300750")
        self.assertFalse(unavailable["available"])
        self.assertIsNone(unavailable["last_price"])

        self.assertEqual(result["benchmark"]["code"], "000300")
        self.assertIsNone(result["benchmark"]["pe_dynamic"])
        self.assertIsNone(result["benchmark"]["pb"])
        self.assertTrue(result["fetched_at"].endswith("+08:00"))

    def test_quote_cache_refreshes_after_ttl(self):
        first = {"snapshot": 1}
        second = {"snapshot": 2}
        with patch("app.services.stocks.monotonic", side_effect=[100.0, 105.0, 111.0]), \
                patch("app.services.stocks._load_quotes", side_effect=[first, second]) as loader:
            first_result = get_stock_quotes()
            cached_result = get_stock_quotes()
            refreshed_result = get_stock_quotes()

        self.assertIs(first_result, first)
        self.assertIs(cached_result, first)
        self.assertIs(refreshed_result, second)
        self.assertEqual(loader.call_count, 2)

    def test_uses_latest_financial_report_for_roe(self):
        quote_payload = {"data": {"diff": [{"f12": "600519", "f2": 1488}]}}
        finance_payload = {"result": {"data": [
            {"SECURITY_CODE": "600519", "REPORT_DATE": "2025-12-31", "WEIGHTAVG_ROE": 31.2},
            {"SECURITY_CODE": "600519", "REPORT_DATE": "2026-06-30", "WEIGHTAVG_ROE": 34.8},
        ]}}
        with patch("app.services.stocks.httpx.Client") as client_class:
            client = client_class.return_value.__enter__.return_value
            client.get.side_effect = [response(quote_payload), response(finance_payload)]
            result = get_stock_quotes()

        maotai = next(row for row in result["quotes"] if row["code"] == "600519")
        self.assertEqual(maotai["roe"], 34.8)
        self.assertEqual(maotai["roe_report_date"], "2026-06-30")

    def test_parses_daily_history_values_and_ignores_malformed_records(self):
        payload = {
            "data": {"klines": [
                "2026-09-22,100,102,103,99,1200,300000,4,2,2,1",
                None,
                "malformed",
            ]}
        }
        with patch("app.services.stocks.httpx.Client") as client_class:
            client = client_class.return_value.__enter__.return_value
            client.get.return_value = response(payload)
            result = get_stock_history("600519", "6m")

        self.assertEqual(result["code"], "600519")
        self.assertEqual(result["period"], "6m")
        self.assertTrue(result["fetched_at"].endswith("+08:00"))
        self.assertEqual(result["bars"], [{
            "date": "2026-09-22", "open": 100.0, "close": 102.0,
            "high": 103.0, "low": 99.0, "volume": 1200.0, "amount": 300000.0,
        }])

    def test_uses_shanghai_offset_when_timezone_database_is_unavailable(self):
        with patch("app.services.stocks.ZoneInfo", side_effect=ZoneInfoNotFoundError):
            with patch("app.services.stocks.httpx.Client") as client_class:
                client = client_class.return_value.__enter__.return_value
                client.get.return_value = response({"data": {"klines": [
                    "2026-09-22,100,102,103,99,1200,300000,4,2,2,1",
                ]}})
                result = get_stock_history("600519", "6m")

        self.assertTrue(result["fetched_at"].endswith("+08:00"))

    def test_rejects_unknown_code_and_period_before_http_request(self):
        with patch("app.services.stocks.httpx.Client") as client_class:
            with self.assertRaises(ValueError):
                get_stock_history("999999", "6m")
            with self.assertRaises(ValueError):
                get_stock_history("600519", "5y")

        client_class.assert_not_called()

    def test_translates_history_timeout_to_stock_data_error(self):
        with patch("app.services.stocks.httpx.Client") as client_class:
            client = client_class.return_value.__enter__.return_value
            client.get.side_effect = httpx.TimeoutException("private upstream detail")

            with self.assertRaises(StockDataError) as raised:
                get_stock_history("600519", "1y")

        self.assertNotIn("private upstream detail", str(raised.exception))

    def test_finance_failure_keeps_quotes_with_null_roe(self):
        quote_payload = {"data": {"diff": [
            {"f12": "600519", "f2": 1488},
        ]}}
        finance_response = response({})
        finance_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "private upstream detail", request=Mock(), response=Mock()
        )
        with patch("app.services.stocks.httpx.Client") as client_class:
            client = client_class.return_value.__enter__.return_value
            client.get.side_effect = [response(quote_payload), finance_response]
            result = get_stock_quotes()

        maotai = next(row for row in result["quotes"] if row["code"] == "600519")
        self.assertEqual(maotai["last_price"], 1488.0)
        self.assertIsNone(maotai["roe"])
        self.assertIsNone(maotai["roe_report_date"])

    def test_malformed_finance_row_does_not_break_quote_retrieval(self):
        quote_payload = {"data": {"diff": [
            {"f12": "600519", "f2": 1488},
        ]}}
        finance_payload = {"result": {"data": [
            "malformed finance row",
            {"SECURITY_CODE": "601318", "REPORT_DATE": "2026-06-30", "WEIGHTAVG_ROE": 17.5},
        ]}}
        with patch("app.services.stocks.httpx.Client") as client_class:
            client = client_class.return_value.__enter__.return_value
            client.get.side_effect = [response(quote_payload), response(finance_payload)]
            result = get_stock_quotes()

        maotai = next(row for row in result["quotes"] if row["code"] == "600519")
        self.assertTrue(maotai["available"])
        self.assertEqual(maotai["last_price"], 1488.0)
        self.assertIsNone(maotai["roe"])
        self.assertIsNone(maotai["roe_report_date"])

        pingan = next(row for row in result["quotes"] if row["code"] == "601318")
        self.assertEqual(pingan["roe"], 17.5)
        self.assertEqual(pingan["roe_report_date"], "2026-06-30")

    def test_finance_row_with_missing_report_date_does_not_attach_roe(self):
        quote_payload = {"data": {"diff": [
            {"f12": "600519", "f2": 1488},
        ]}}
        finance_payload = {"result": {"data": [
            {"SECURITY_CODE": "600519", "REPORT_DATE": None, "WEIGHTAVG_ROE": 34.8},
        ]}}
        with patch("app.services.stocks.httpx.Client") as client_class:
            client = client_class.return_value.__enter__.return_value
            client.get.side_effect = [response(quote_payload), response(finance_payload)]
            result = get_stock_quotes()

        maotai = next(row for row in result["quotes"] if row["code"] == "600519")
        self.assertTrue(maotai["available"])
        self.assertEqual(maotai["last_price"], 1488.0)
        self.assertIsNone(maotai["roe"])
        self.assertIsNone(maotai["roe_report_date"])

    def test_finance_row_with_malformed_report_date_does_not_attach_roe(self):
        quote_payload = {"data": {"diff": [
            {"f12": "600519", "f2": 1488},
        ]}}
        finance_payload = {"result": {"data": [
            {"SECURITY_CODE": "600519", "REPORT_DATE": "2026-06-30garbage", "WEIGHTAVG_ROE": 34.8},
        ]}}
        with patch("app.services.stocks.httpx.Client") as client_class:
            client = client_class.return_value.__enter__.return_value
            client.get.side_effect = [response(quote_payload), response(finance_payload)]
            result = get_stock_quotes()

        maotai = next(row for row in result["quotes"] if row["code"] == "600519")
        self.assertTrue(maotai["available"])
        self.assertEqual(maotai["last_price"], 1488.0)
        self.assertIsNone(maotai["roe"])
        self.assertIsNone(maotai["roe_report_date"])


if __name__ == "__main__":
    unittest.main()
