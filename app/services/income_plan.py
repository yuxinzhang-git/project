import json
import os
import re
from typing import Any

from langchain_openai import ChatOpenAI

from app.config import settings  # Load .env before reading the API key.
from app.schemas.income_plan import IncomePlanRequest, IncomePlanResponse


SYSTEM_PROMPT = """你是谨慎、务实的中文赚钱方案顾问。
根据用户已有技能、资金、地点、频率和约束，生成 1-3 个低成本、合法、可验证的赚钱方案。
不要承诺收益，不要建议灰产、违法、赌博、金融投机、刷单、侵犯隐私、医疗法律高风险服务。
每个方案必须具体到目标客户、交付物、准备过程、7 天执行计划、成本、获客方式、风险、验证指标和第一步行动。
只返回 JSON，不要返回 Markdown、解释或代码块。
JSON 顶层格式必须是：
{"plans":[{"title":"","fit_reason":"","target_customers":[],"offer":"","preparation_steps":[],"seven_day_plan":[],"cost_breakdown":"","customer_acquisition":[],"risks":[],"validation_metrics":[],"first_action":"","idea_title":"","idea_description":"","idea_deliverable":"","suggested_price":0,"estimated_cost":0}]}
"""


class IncomePlanService:
    def __init__(self, model: Any | None = None) -> None:
        self.model = model

    def generate(self, request: IncomePlanRequest) -> IncomePlanResponse:
        if not request.skills.strip():
            raise ValueError("请先填写现有技能")

        model = self.model or self._create_model()
        response = model.invoke(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": self._build_user_prompt(request)},
            ]
        )
        content = self._extract_content(response)
        payload = self._parse_json(content)
        result = IncomePlanResponse.model_validate(payload)
        if not result.plans:
            raise ValueError("模型没有生成可用方案")
        return result

    @staticmethod
    def _create_model() -> ChatOpenAI:
        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        if not api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is not configured")
        return ChatOpenAI(
            model="deepseek-v4-flash",
            api_key=api_key,
            base_url="https://api.deepseek.com",
            temperature=0.4,
            timeout=45,
            max_retries=2,
        )

    @staticmethod
    def _build_user_prompt(request: IncomePlanRequest) -> str:
        return "\n".join(
            [
                f"现有技能：{request.skills.strip()}",
                f"可用资金/成本：{request.budget.strip() or '未填写'}",
                f"实施地点：{request.location.strip() or '未填写'}",
                f"实施频率：{request.frequency.strip() or '未填写'}",
                f"可投入时间：{request.available_time.strip() or '未填写'}",
                f"风险偏好：{request.risk_preference.strip() or '未填写'}",
                f"不想做的事：{request.avoid.strip() or '未填写'}",
                f"期望收益周期：{request.income_cycle.strip() or '未填写'}",
                "请生成 1-3 个可执行方案，并让 idea_* 字段适合保存为想法清单。",
            ]
        )

    @staticmethod
    def _extract_content(response: Any) -> str:
        content = getattr(response, "content", response)
        if isinstance(content, list):
            content = "".join(str(item.get("text", item)) if isinstance(item, dict) else str(item) for item in content)
        return str(content or "").strip()

    @staticmethod
    def _parse_json(content: str) -> dict:
        if not content:
            raise ValueError("模型返回为空")
        fenced = re.search(r"```(?:json)?\s*(.*?)```", content, flags=re.DOTALL | re.IGNORECASE)
        if fenced:
            content = fenced.group(1).strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError("模型返回格式不是有效 JSON") from exc
