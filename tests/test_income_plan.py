import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import httpx

from app.main import create_app


class IncomePlanServiceTests(unittest.TestCase):
    def test_generate_parses_model_json_into_plan_items(self):
        from app.schemas.income_plan import IncomePlanRequest
        from app.services.income_plan import IncomePlanService

        payload = {
            "plans": [
                {
                    "title": "周末英语邮件润色服务",
                    "fit_reason": "英语能力和周末时间可以直接转成轻量服务。",
                    "target_customers": ["跨境卖家", "求职者"],
                    "offer": "提供英文邮件和简历段落润色。",
                    "preparation_steps": ["整理服务范围", "准备 3 个样例"],
                    "seven_day_plan": ["确定报价", "发布服务说明"],
                    "cost_breakdown": "主要成本为平台展示和样例制作，控制在 1000 元内。",
                    "customer_acquisition": ["朋友圈", "闲鱼"],
                    "risks": ["需求不稳定", "交付边界不清"],
                    "validation_metrics": ["获得 3 个咨询", "完成 1 单付费"],
                    "first_action": "写出 100 字服务说明。",
                    "idea_title": "英语邮件润色服务",
                    "idea_description": "面向跨境卖家和求职者的一次性英文文本润色。",
                    "idea_deliverable": "润色后的英文文本和修改说明。",
                    "suggested_price": 49,
                    "estimated_cost": 50,
                }
            ]
        }
        fake_model = SimpleNamespace(invoke=lambda messages: SimpleNamespace(content=json.dumps(payload, ensure_ascii=False)))
        service = IncomePlanService(model=fake_model)

        result = service.generate(
            IncomePlanRequest(
                skills="英语能力",
                budget="1000 元",
                location="线上",
                frequency="一周两三次，周末",
                available_time="每次 2 小时",
                risk_preference="保守",
                avoid="不露脸",
                income_cycle="30 天",
            )
        )

        self.assertEqual(result.plans[0].title, "周末英语邮件润色服务")
        self.assertEqual(result.plans[0].suggested_price, 49)
        self.assertIn("跨境卖家", result.plans[0].target_customers)

    def test_generate_rejects_request_without_skills(self):
        from app.schemas.income_plan import IncomePlanRequest
        from app.services.income_plan import IncomePlanService

        service = IncomePlanService(model=SimpleNamespace(invoke=lambda messages: None))

        with self.assertRaisesRegex(ValueError, "请先填写现有技能"):
            service.generate(IncomePlanRequest(skills="   "))


class IncomePlanApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app()),
            base_url="http://testserver",
        )

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_generate_returns_service_response(self):
        payload = {
            "plans": [
                {
                    "title": "英语资料包",
                    "fit_reason": "匹配英语技能。",
                    "target_customers": ["学生"],
                    "offer": "整理英语学习资料。",
                    "preparation_steps": ["选题"],
                    "seven_day_plan": ["发布"],
                    "cost_breakdown": "低成本。",
                    "customer_acquisition": ["社群"],
                    "risks": ["同质化"],
                    "validation_metrics": ["一次咨询"],
                    "first_action": "写简介。",
                    "idea_title": "英语资料包",
                    "idea_description": "英语学习资料整理。",
                    "idea_deliverable": "资料包。",
                    "suggested_price": 19,
                    "estimated_cost": 0,
                }
            ]
        }
        with patch("app.api.income_plan.service.generate", return_value=payload) as generate:
            response = await self.client.post(
                "/api/income-plan/generate",
                json={"skills": "英语能力", "budget": "1000 元", "location": "线上"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), payload)
        generate.assert_called_once()


class IncomePlanFrontendTests(unittest.TestCase):
    def test_money_page_uses_vertical_income_plan_layout(self):
        page = Path(__file__).parents[1] / "frontend" / "money.html"
        source = page.read_text(encoding="utf-8")

        self.assertIn('plan-layout', source)
        self.assertIn("plan-form-panel", source)
        self.assertIn("plan-results-panel", source)
        self.assertIn('.plan-card .item-head>div{min-width:0}', source)
        self.assertIn('.plan-card .item-title,.plan-block-content{overflow-wrap:anywhere}', source)
        self.assertIn('.plan-card .item-body{line-height:1.7;overflow-wrap:anywhere}', source)

    def test_money_js_marks_plan_result_sections_for_emphasis(self):
        script = Path(__file__).parents[1] / "frontend" / "money.js"
        source = script.read_text(encoding="utf-8")

        self.assertIn("plan-block-title", source)
        self.assertIn("plan-block-content", source)

    def test_money_page_exposes_income_plan_tab_and_inputs(self):
        page = Path(__file__).parents[1] / "frontend" / "money.html"
        source = page.read_text(encoding="utf-8")

        self.assertIn("方案生成", source)
        self.assertIn('id="plan-skills"', source)
        self.assertIn('id="plan-budget"', source)
        self.assertIn('id="plan-location"', source)
        self.assertIn('id="plan-frequency"', source)
        self.assertIn('id="plan-results"', source)

    def test_money_js_generates_plans_and_saves_ideas(self):
        script = Path(__file__).parents[1] / "frontend" / "money.js"
        source = script.read_text(encoding="utf-8")

        self.assertIn("/api/income-plan/generate", source)
        self.assertIn("renderPlans", source)
        self.assertIn("data-save-plan", source)
        self.assertIn("/api/money/ideas", source)


if __name__ == "__main__":
    unittest.main()
