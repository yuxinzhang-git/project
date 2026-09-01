import json
import uuid
from datetime import datetime
from pathlib import Path

from app.config import settings


class XianyuTaskService:
    """Persistence and accounting for one-off Xianyu delivery tasks."""

    def __init__(self, state_file: Path | None = None):
        self.state_file = state_file or settings.xianyu_state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def default_state() -> dict:
        return {"tasks": []}

    def read_state(self) -> dict:
        try:
            state = self.default_state()
            state.update(json.loads(self.state_file.read_text(encoding="utf-8-sig")))
            state.setdefault("tasks", [])
            return state
        except (FileNotFoundError, json.JSONDecodeError):
            return self.default_state()

    def write_state(self, state: dict) -> dict:
        self.state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        return state

    def list_tasks(self) -> list[dict]:
        return self.read_state()["tasks"]

    def create_task(self, data: dict) -> dict:
        title = str(data.get("title", "")).strip()
        if not title:
            raise ValueError("task title cannot be empty")
        now = datetime.now().isoformat(timespec="seconds")
        task = {
            "id": uuid.uuid4().hex,
            "title": title[:120],
            "task_type": str(data.get("task_type", "one_off_delivery")),
            "customer_need": str(data.get("customer_need", "")).strip(),
            "deliverable": str(data.get("deliverable", "")).strip(),
            "amount": float(data.get("amount", 0)),
            "costs": float(data.get("costs", 0)),
            "status": "draft",
            "payment_status": "unpaid",
            "artifact_path": "",
            "notes": str(data.get("notes", "")).strip(),
            "created_at": now,
            "updated_at": now,
            "delivered_at": None,
            "settled_at": None,
        }
        state = self.read_state()
        state["tasks"].append(task)
        self.write_state(state)
        return task

    def update_task(self, task_id: str, changes: dict) -> dict:
        state = self.read_state()
        task = next((item for item in state["tasks"] if item["id"] == task_id), None)
        if task is None:
            raise KeyError(f"task not found: {task_id}")
        now = datetime.now().isoformat(timespec="seconds")
        for field in ("status", "payment_status", "deliverable", "artifact_path", "notes"):
            if changes.get(field) is not None:
                task[field] = changes[field]
        for field in ("amount", "costs"):
            if changes.get(field) is not None:
                task[field] = float(changes[field])
        task["updated_at"] = now
        if task["status"] == "delivered" and not task.get("delivered_at"):
            task["delivered_at"] = now
        if task["status"] == "settled" and not task.get("settled_at"):
            task["settled_at"] = now
        self.write_state(state)
        return task

    def summary(self) -> dict:
        tasks = self.list_tasks()
        settled = [task for task in tasks if task.get("status") == "settled"]
        gross = sum(float(task.get("amount", 0)) for task in settled)
        costs = sum(float(task.get("costs", 0)) for task in settled)
        return {
            "total_tasks": len(tasks),
            "settled_tasks": len(settled),
            "gross_revenue": round(gross, 2),
            "total_costs": round(costs, 2),
            "net_revenue": round(gross - costs, 2),
        }
