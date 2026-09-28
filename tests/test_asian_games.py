import json
import unittest
from datetime import datetime
from unittest.mock import Mock, patch

from app.services.asian_games import (
    ASIAN_GAMES_SOURCE,
    asian_games_feed,
    decode_bornan_payload,
    normalize_event,
)


class AsianGamesServiceTests(unittest.TestCase):
    def test_normalizes_event_and_converts_time_to_shanghai(self) -> None:
        event = normalize_event(
            {
                "Id": "ath-1",
                "Sport": {"Name": "Athletics"},
                "Discipline": {"Name": "Track and Field"},
                "Name": "Men's 100m Final",
                "StartDate": "2026-09-23T01:30:00Z",
                "Status": "FINISHED",
                "Venue": {"Name": "Nagoya Stadium"},
                "Competitors": [{"Name": "Runner A"}, {"Name": "Runner B"}],
                "Results": {"Winner": "Runner A", "Score": "10.01"},
            }
        )

        self.assertEqual(event["id"], "ath-1")
        self.assertEqual(event["sport"], "田径")
        self.assertEqual(event["discipline"], "田径")
        self.assertEqual(event["status"], "finished")
        self.assertEqual(event["start_time"], "2026-09-23T09:30:00+08:00")
        self.assertEqual([item["name"] for item in event["participants"]], ["Runner A", "Runner B"])
        self.assertEqual(event["score"]["Winner"], "Runner A")

    def test_decodes_bornan_zlib_payload_wrapped_as_utf8_text(self) -> None:
        import zlib

        original = json.dumps({"events": [{"id": "one"}]}).encode("utf-8")
        encoded = zlib.compress(original).decode("latin1").encode("utf-8")

        self.assertEqual(decode_bornan_payload(encoded), {"events": [{"id": "one"}]})

    @patch("app.services.asian_games.httpx.Client")
    def test_fetches_fixed_official_day_endpoint_and_groups_statuses(self, client_cls) -> None:
        import zlib

        payload = {
            "events": [
                {"id": "finished", "name": "Finished", "start_time": "2026-09-23T00:00:00Z", "status": "finished"},
                {"id": "live", "name": "Live", "start_time": "2026-09-23T02:00:00Z", "status": "live"},
                {"id": "upcoming", "name": "Upcoming", "start_time": "2026-09-23T10:00:00Z", "status": "upcoming"},
            ]
        }
        response = Mock(status_code=200, content=zlib.compress(json.dumps(payload).encode()))
        response.headers = {"content-type": "application/json"}
        response.raise_for_status.return_value = None
        client = client_cls.return_value.__enter__.return_value
        client.get.return_value = response

        result = asian_games_feed("2026-09-23")

        client.get.assert_called_once_with(
            f"{ASIAN_GAMES_SOURCE}/s/AG2026/en/ALL/schedule/day/2026-09-23",
            headers=unittest.mock.ANY,
        )
        self.assertEqual([item["id"] for item in result["finished"]], ["finished"])
        self.assertEqual([item["id"] for item in result["live"]], ["live"])
        self.assertEqual([item["id"] for item in result["upcoming"]], ["upcoming"])
        self.assertEqual(result["total"], 3)
        self.assertEqual(result["source_status"], "live")

    def test_rejects_invalid_date(self) -> None:
        with self.assertRaises(ValueError):
            asian_games_feed("2026-9-23")

    @patch("app.services.asian_games._request_payload")
    def test_parses_official_schedule_records(self, request_payload) -> None:
        request_payload.return_value = [
            {
                "Disc": "ATH",
                "DiscDesc": "Athletics",
                "Key": "M.WALKHM------------.FNL-.000100--",
                "Status": "OFFICIAL",
                "DateTimeRaw": "2026-09-23T07:30:00+09:00",
                "EventDesc": "Men's Half Marathon Race Walk",
                "UnitDesc": "Men's Half Marathon Race Walk Final",
                "VenueDesc": "Aichi-Nagoya Race Walking Course",
                "ShowResults": True,
            },
            {
                "Disc": "BK3",
                "DiscDesc": "3x3 Basketball",
                "Key": "M.TEAM3-------------.GPD-.000500--",
                "Status": "SCHEDULED",
                "DateTimeRaw": "2026-09-23T20:35:00+09:00",
                "PhaseDesc": "Men Round Robin Pool D",
                "UnitDesc": "Men Round Robin Pool D Game 5",
                "VenueDesc": "Kinjo Futo Station Square Venue",
                "ShowResults": False,
            },
        ]

        result = asian_games_feed("2026-09-23")

        self.assertEqual(result["total"], 2)
        self.assertEqual(result["finished"][0]["id"], "M.WALKHM------------.FNL-.000100--")
        self.assertEqual(result["finished"][0]["discipline"], "田径")
        self.assertEqual(result["finished"][0]["title"], "男子半程马拉松竞走决赛")
        self.assertEqual(result["upcoming"][0]["discipline"], "三人篮球")
        self.assertEqual(result["upcoming"][0]["venue"], "金城码头站前广场赛场")

    def test_localizes_official_english_fields_to_chinese(self) -> None:
        event = normalize_event(
            {
                "Key": "TST-1",
                "DiscDesc": "Soft Tennis",
                "Status": "SCHEDULED",
                "DateTimeRaw": "2026-09-23T09:00:00+09:00",
                "UnitDesc": "Women's Singles Quarterfinals Match 1",
                "Venue": "HPT",
                "VenueDesc": "Nagoya City Higashiyama Park Tennis Center",
            }
        )

        self.assertEqual(event["discipline"], "软式网球")
        self.assertEqual(event["title"], "女子单打四分之一决赛第1场")
        self.assertEqual(event["venue"], "名古屋市东山公园网球中心")


if __name__ == "__main__":
    unittest.main()
