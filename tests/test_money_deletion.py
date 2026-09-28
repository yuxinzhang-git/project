import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import httpx

from app.main import create_app
from app.services.money import MoneyService
from app.services.xianyu_tasks import XianyuTaskService


class MoneyDeletionServiceTests(unittest.TestCase):
    def test_delete_idea_removes_only_matching_idea(self):
        with TemporaryDirectory() as temp_dir:
            service = MoneyService(state_file=Path(temp_dir) / "money.json", artifacts_dir=Path(temp_dir) / "artifacts")
            first = service.create_idea({"title": "保留想法"})
            second = service.create_idea({"title": "删除想法"})

            ideas = service.delete_idea(second["id"])

            self.assertEqual([idea["id"] for idea in ideas], [first["id"]])
            self.assertEqual(service.list_ideas()[0]["title"], "保留想法")

    def test_delete_idea_raises_for_unknown_id(self):
        with TemporaryDirectory() as temp_dir:
            service = MoneyService(state_file=Path(temp_dir) / "money.json", artifacts_dir=Path(temp_dir) / "artifacts")

            with self.assertRaisesRegex(KeyError, "idea not found"):
                service.delete_idea("missing")

    def test_delete_task_removes_task_and_updates_summary(self):
        with TemporaryDirectory() as temp_dir:
            service = XianyuTaskService(state_file=Path(temp_dir) / "xianyu.json")
            keep = service.create_task({"title": "保留任务", "amount": 10, "costs": 1})
            remove = service.create_task({"title": "删除任务", "amount": 20, "costs": 2})

            tasks = service.delete_task(remove["id"])

            self.assertEqual([task["id"] for task in tasks], [keep["id"]])
            self.assertEqual(service.summary()["total_tasks"], 1)


class MoneyDeletionApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app()),
            base_url="http://testserver",
        )

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_delete_idea_returns_remaining_ideas(self):
        payload = [{
            "id": "keep",
            "title": "保留",
            "description": "",
            "target_user": "",
            "deliverable": "",
            "suggested_price": 0,
            "estimated_cost": 0,
            "risk": "",
            "status": "draft",
            "created_at": "2026-09-24T00:00:00",
            "updated_at": "2026-09-24T00:00:00",
        }]
        with patch("app.api.money.service.delete_idea", return_value=payload) as delete_idea:
            response = await self.client.delete("/api/money/ideas/remove-me")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), payload)
        delete_idea.assert_called_once_with("remove-me")

    async def test_delete_unknown_idea_returns_not_found(self):
        with patch("app.api.money.service.delete_idea", side_effect=KeyError("idea not found: missing")):
            response = await self.client.delete("/api/money/ideas/missing")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "'idea not found: missing'"})

    async def test_delete_task_returns_remaining_tasks(self):
        payload = [{
            "id": "keep",
            "title": "保留",
            "task_type": "one_off_delivery",
            "customer_need": "",
            "deliverable": "",
            "amount": 0,
            "costs": 0,
            "status": "draft",
            "payment_status": "unpaid",
            "artifact_path": "",
            "notes": "",
            "created_at": "2026-09-24T00:00:00",
            "updated_at": "2026-09-24T00:00:00",
            "delivered_at": None,
            "settled_at": None,
        }]
        with patch("app.api.xianyu_tasks.service.delete_task", return_value=payload) as delete_task:
            response = await self.client.delete("/api/xianyu/tasks/remove-me")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), payload)
        delete_task.assert_called_once_with("remove-me")

    async def test_delete_unknown_task_returns_not_found(self):
        with patch("app.api.xianyu_tasks.service.delete_task", side_effect=KeyError("task not found: missing")):
            response = await self.client.delete("/api/xianyu/tasks/missing")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "'task not found: missing'"})


class MoneyDeletionFrontendTests(unittest.TestCase):
    def test_money_page_script_supports_manual_delete_actions(self):
        source = (Path(__file__).parents[1] / "frontend" / "money.js").read_text(encoding="utf-8")

        self.assertIn("data-delete-idea", source)
        self.assertIn("data-action=\"delete\"", source)
        self.assertIn('method:"DELETE"', source)
        self.assertIn("/api/money/ideas/", source)
        self.assertIn("/api/xianyu/tasks/", source)


if __name__ == "__main__":
    unittest.main()
