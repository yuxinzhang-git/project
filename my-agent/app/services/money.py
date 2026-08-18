import hashlib
import json
import uuid
from datetime import datetime
from html import escape
from pathlib import Path

from app.config import settings
from app.schemas.money import MoneyRequest, MoneyResponse


class MoneyService:
    def __init__(self, state_file: Path | None = None, artifacts_dir: Path | None = None):
        self.state_file = state_file or settings.money_state_file
        self.artifacts_dir = artifacts_dir or settings.money_artifacts_dir
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def default_state() -> dict:
        return {"mission": "", "rules": "", "initial_capital": 0, "target_amount": 0, "balance": 0, "status": "setup", "active_task": "", "subtasks": [], "permissions": [], "ledger": [], "activity": [], "artifacts": [], "ideas": []}

    def read_state(self) -> dict:
        try:
            state = self.default_state()
            state.update(json.loads(self.state_file.read_text(encoding="utf-8-sig")))
            return state
        except (FileNotFoundError, json.JSONDecodeError):
            return self.default_state()

    def write_state(self, state: dict) -> dict:
        self.state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        return state

    def list_ideas(self) -> list[dict]:
        return self.read_state().get("ideas", [])

    def create_idea(self, data: dict) -> dict:
        title = str(data.get("title", "")).strip()
        if not title:
            raise ValueError("idea title cannot be empty")
        now = datetime.now().isoformat(timespec="seconds")
        idea = {
            "id": uuid.uuid4().hex,
            "title": title[:120],
            "description": str(data.get("description", "")).strip(),
            "target_user": str(data.get("target_user", "")).strip(),
            "deliverable": str(data.get("deliverable", "")).strip(),
            "suggested_price": float(data.get("suggested_price", 0)),
            "estimated_cost": float(data.get("estimated_cost", 0)),
            "risk": str(data.get("risk", "")).strip(),
            "status": "draft",
            "created_at": now,
            "updated_at": now,
        }
        state = self.read_state()
        state.setdefault("ideas", []).append(idea)
        self.write_state(state)
        return idea

    def generate(self, request: MoneyRequest) -> MoneyResponse:
        if not request.need.strip():
            raise ValueError("请先填写赚钱需求")
        return MoneyResponse(title="先验证一个可交付的小服务", summary=f"围绕“{request.need.strip()}”设计低成本、可验证的第一步。", fit_reason="先确认真实需求与交付成本，再扩大投入。", steps=["明确目标用户和交付物", "用公开渠道收集 5 个真实反馈", "完成一个最小可演示版本", "复盘成本、风险和下一步"], cost="优先使用现有工具，控制在可承受范围内", cycle="7 天完成首轮验证", income="不承诺收入；以真实反馈和首个付费意向为目标", risks=["需求不清晰", "低估交付时间", "平台规则变化"], needs=[{"name": "发布渠道", "reason": "验证目标用户反馈", "status": "待你确认"}], first_action="把需求改写为一个可在 1-3 天交付的具体结果。")

    def create_artifact(self, kind: str, title: str) -> dict:
        state = self.read_state()
        title = (title or state.get("mission") or "Pocket Tap").strip()[:80]
        package_id = f"{datetime.now():%Y%m%d-%H%M%S}-{hashlib.sha256(title.encode()).hexdigest()[:8]}"
        package_dir = self.artifacts_dir / package_id
        package_dir.mkdir(exist_ok=False)
        safe_title = escape(title)
        (package_dir / "index.html").write_text(f"<!doctype html><meta charset='utf-8'><title>{safe_title}</title><h1>{safe_title}</h1><p>Local starter artifact.</p>", encoding="utf-8")
        (package_dir / "README.md").write_text(f"# {title}\n\nLocal artifact created by my-agent.\n", encoding="utf-8")
        artifact = {"id": package_id, "title": title, "kind": kind, "path": str(package_dir.relative_to(settings.project_root)).replace('\\', '/'), "created_at": f"{datetime.now():%Y/%m/%d %H:%M:%S}"}
        state["artifacts"].append(artifact)
        state["activity"].append({"text": f"[completed/local-artifact] Created local package: {artifact['path']}", "time": artifact["created_at"]})
        state["active_task"] = "测试本地包，再选择官方发布平台。"
        return self.write_state(state)

    def advance(self, focus: str) -> dict:
        state = self.read_state()
        if state.get("status") != "active":
            raise RuntimeError("总任务尚未处于执行中")
        action = focus.strip() or "整理一个可验证的下一步，并记录所需权限。"
        state["active_task"] = action
        state["activity"].append({"text": f"已生成下一步动作：{action}", "time": f"{datetime.now():%Y/%m/%d %H:%M:%S}"})
        return self.write_state(state)

    def run(self, focus: str) -> dict:
        return self.advance(focus or "整理公开信息并形成候选方案。")
