"""

syf_agent 后端服务

- 托管前端页面（主页面、计算器、天气、账单）

- 提供 AI 计算 API（/api/chat）

- 提供天气查询 API（/api/weather）

- 提供账单查询 API（/api/billing）

"""

from fastapi import FastAPI, HTTPException

from fastapi.middleware.cors import CORSMiddleware

from fastapi.staticfiles import StaticFiles

from fastapi.responses import FileResponse

from pydantic import BaseModel

from dotenv import load_dotenv

import os

import httpx

import json
import hashlib
from datetime import datetime
from html import escape



# 从 tools.py 导入所有工具

from tools import calculator, calculate_loan_interest

from browser import Browser, BrowserError



# 清除代理设置（防止冲突）

for key in list(os.environ.keys()):

    if 'proxy' in key.lower():

        del os.environ[key]



load_dotenv()

os.chdir(os.path.dirname(os.path.abspath(__file__)))

os.makedirs("browser_screenshots", exist_ok=True)

api_key = os.getenv("DEEPSEEK_API_KEY") or ""



# ===== FastAPI 应用 =====

app = FastAPI(title="syf_agent")



# CORS 允许跨域

app.add_middleware(

    CORSMiddleware,

    allow_origins=["*"],

    allow_methods=["*"],

    allow_headers=["*"],

)



# ===== 托管静态前端页面 =====

# ui 目录下的文件通过 /ui/ 访问

app.mount("/ui", StaticFiles(directory="ui", html=True), name="ui")
app.mount("/browser-screenshots", StaticFiles(directory="browser_screenshots"), name="browser-screenshots")

browser = Browser()





# ===== 请求/响应模型 =====

class ChatRequest(BaseModel):

    message: str

    conversation_history: list[dict] | None = None





class ChatResponse(BaseModel):

    reply: str

    tool_calls: list[dict] | None = None


class BrowserOpenRequest(BaseModel):
    url: str


class BrowserSearchRequest(BaseModel):
    keyword: str


class BrowserLocatorRequest(BaseModel):
    locator: str


class BrowserTypeRequest(BrowserLocatorRequest):
    text: str


class BrowserScreenshotRequest(BaseModel):
    filename: str = "latest.png"


class MoneyRequest(BaseModel):
    need: str
    rules: str = ""
    context: str = ""


class MoneyResponse(BaseModel):
    title: str
    summary: str
    fit_reason: str
    steps: list[str]
    cost: str
    cycle: str
    income: str
    risks: list[str]
    needs: list[dict]
    first_action: str


class MoneyState(BaseModel):
    mission: str = ""
    rules: str = ""
    initial_capital: float = 0
    target_amount: float = 0
    balance: float = 0
    status: str = "setup"
    active_task: str = ""
    subtasks: list[dict] = []
    permissions: list[dict] = []
    ledger: list[dict] = []
    activity: list[dict] = []
    artifacts: list[dict] = []


class MoneyAdvanceRequest(BaseModel):
    focus: str = ""


class MoneyRunRequest(BaseModel):
    focus: str = ""


class MoneyArtifactRequest(BaseModel):
    kind: str = "web-game"
    title: str = ""





# ===== AI 计算对话（保持使用 LangChain Agent） =====

from langchain_openai import ChatOpenAI

from langchain.agents import create_agent



llm = ChatOpenAI(

    model="deepseek-v4-flash",

    api_key=api_key,

    base_url="https://api.deepseek.com",

    temperature=0.3,

    timeout=30,

    max_retries=3,

)



calc_agent = create_agent(

    model=llm,

    tools=[calculator, calculate_loan_interest],

    system_prompt="""你是一个专业的数学计算助手。

你的任务是：

1. 理解用户的计算需求

2. 使用 calculator 工具执行精确计算

3. 用清晰的中文解释计算过程和结果

4. 涉及到贷款计算时，使用 calculate_loan_interest 工具



对于复杂计算，先分解问题，再逐步计算。"""

)


def _fallback_money_plan(request: MoneyRequest) -> dict:
    return {
        "title": "先做一个可验证的小服务",
        "summary": "围绕你的现有能力，把一个明确的小问题包装成可交付服务，先用低成本验证是否有人愿意付费。",
        "fit_reason": "这是启动成本低、反馈周期短、可以逐步扩大投入的路径。",
        "steps": [
            "从你的需求中选出一个具体、可在 1-3 天交付的结果。",
            "写出服务范围、交付物、价格和不包含的内容。",
            "找 5 位可能的用户做访谈或发布测试帖，记录真实反馈。",
            "拿到首个意向后再交付，复盘时间成本和利润。"
        ],
        "cost": "0-200 元，优先使用已有工具",
        "cycle": "7 天完成首轮验证",
        "income": "首轮目标：1 个付费用户；收入取决于定价与交付效率",
        "risks": ["需求不够具体导致无人购买", "低估交付时间", "不要在验证前购买长期服务或投放"],
        "needs": [
            {"name": "发布渠道", "reason": "发布测试信息并收集反馈", "status": "待你开放"},
            {"name": "收款方式", "reason": "有明确付费意向后再开通", "status": "按需开放"}
        ],
        "first_action": "把你当前最想解决的赚钱需求写成一句话，并补充可投入的时间与预算。"
    }


MONEY_STATE_FILE = "money_state.json"


def _default_money_state() -> dict:
    return {
        "mission": "",
        "rules": "",
        "initial_capital": 0,
        "target_amount": 0,
        "balance": 0,
        "status": "setup",
        "active_task": "",
        "subtasks": [],
        "permissions": [],
        "ledger": [],
        "activity": [],
        "artifacts": [],
    }


def _read_money_state() -> dict:
    try:
        with open(MONEY_STATE_FILE, "r", encoding="utf-8") as f:
            state = _default_money_state()
            state.update(json.load(f))
            return state
    except (FileNotFoundError, json.JSONDecodeError):
        return _default_money_state()


def _write_money_state(state: dict) -> dict:
    with open(MONEY_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    return state


@app.get("/api/money/state", response_model=MoneyState)
def money_state():
    return _read_money_state()


@app.put("/api/money/state", response_model=MoneyState)
def update_money_state(request: MoneyState):
    return _write_money_state(request.model_dump())


@app.post("/api/money/artifacts/create", response_model=MoneyState)
def create_money_artifact(request: MoneyArtifactRequest):
    """Create a real, locally verifiable starter content package."""
    state = _read_money_state()
    title = (request.title or state.get("mission") or "Pocket Tap").strip()[:80]
    safe_title = escape(title)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    package_id = f"{stamp}-{hashlib.sha256(title.encode('utf-8')).hexdigest()[:8]}"
    package_dir = os.path.join("money_artifacts", package_id)
    os.makedirs(package_dir, exist_ok=False)

    game_html = f"""<!doctype html>
<html lang=\"en\"><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>{safe_title}</title>
<style>body{{margin:0;min-height:100vh;display:grid;place-items:center;background:#101314;color:#edf4ee;font:16px system-ui}}main{{max-width:560px;padding:28px;border:1px solid #2a3333;background:#171c1d;border-radius:8px;text-align:center}}button{{padding:14px 22px;border:0;border-radius:6px;background:#f2b84b;color:#17130a;font-weight:700;font-size:18px;cursor:pointer}}small{{color:#91a09d}}</style>
<main><h1>{safe_title}</h1><p>Tap to collect stars. Reach 30 to finish.</p><h2 id=\"score\">0</h2><button id=\"tap\">Collect star</button><p id=\"status\"><small>Local demo build. Add platform metadata before publishing.</small></p></main>
<script>let score=0;const out=document.querySelector('#score');document.querySelector('#tap').onclick=()=>{{score++;out.textContent=score;if(score>=30)document.querySelector('#status').textContent='Demo complete. Thanks for playing!';}};</script>"""
    listing = f"""# {title}\n\n## Short description\nA compact browser clicker game with a clear 30-star goal.\n\n## Suggested listing fields\n- Category: Casual / Web game\n- Price: Test with free access first; do not promise earnings.\n- Delivery: Upload `index.html` where the platform supports HTML games.\n- Verification: Open the uploaded build and complete one 30-star round.\n\n## Before publishing\nUse only the platform's official publisher flow. Confirm its rules, payout requirements, content policy, and any fees before submitting.\n"""
    readme = f"""# Content package\n\nThis folder contains a real local web-game prototype and listing copy.\n\n1. Open `index.html` in a browser and test it.\n2. Review `listing.md` for platform fields.\n3. Use the official platform publisher page only after you have logged in yourself.\n4. Record a release only after the platform confirms it.\n\nThis package is a prototype, not proof of publication, sales, or revenue.\n"""
    files = {"index.html": game_html, "listing.md": listing, "README.md": readme}
    manifest_files = []
    for name, content in files.items():
        path = os.path.join(package_dir, name)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        manifest_files.append({"name": name, "path": path.replace("\\", "/"), "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest()})
    manifest_path = os.path.join(package_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump({"package_id": package_id, "title": title, "files": manifest_files}, handle, ensure_ascii=False, indent=2)

    artifact = {"id": package_id, "title": title, "kind": request.kind, "path": package_dir.replace("\\", "/"), "manifest": manifest_path.replace("\\", "/"), "created_at": datetime.now().strftime("%Y/%m/%d %H:%M:%S")}
    state.setdefault("artifacts", []).append(artifact)
    state.setdefault("activity", []).append({"text": f"[completed/local-artifact] Created verified local package: {artifact['path']}", "time": artifact["created_at"]})
    state["active_task"] = "Test the local package, then choose an official publishing platform."
    return _write_money_state(state)


def _fallback_action(state: dict) -> dict:
    return {
        "action": "先做公开市场侦察：整理 3 个可以发布数字产品或小游戏的平台，比较审核、收费和提现规则。",
        "reason": "当前本金较小，第一步应优先获得真实市场信息，避免先花钱或注册不必要的服务。",
        "permission_needed": [],
        "expected_result": "得到 3 个候选平台及其准入条件，选出最适合当前任务的一 个。",
        "mode": "可直接推进",
    }


@app.post("/api/money/advance", response_model=MoneyState)
def advance_money_task(request: MoneyAdvanceRequest):
    """Advance exactly one safe step and record it; external side effects stay gated."""
    state = _read_money_state()
    if state.get("status") != "active":
        raise HTTPException(status_code=409, detail="总任务尚未处于执行中")
    pending_permissions = [p for p in state.get("permissions", []) if not any(marker in str(p.get("status", "")) for marker in ("已完成", "complete", "done"))]
    if pending_permissions:
        raise HTTPException(status_code=409, detail="存在未完成的用户操作，请先在看板中确认完成")
    prompt = f"""你是正在执行赚钱总任务的自主执行代理。只能推进一个最小、合法、可验证的下一步。
总任务：{state.get('mission')}
本金：{state.get('initial_capital')}，当前余额：{state.get('balance')}，目标：{state.get('target_amount')}
规则：{state.get('rules') or '遵守法律，不借贷，不做高风险投机'}
已有权限申请：{state.get('permissions')}
最近行动：{state.get('activity', [])[-5:]}
用户补充重点：{request.focus}

只返回 JSON：action, reason, permission_needed, expected_result, mode。
action 必须是一个下一步动作，不要一次规划整个项目。mode 只能是“可直接推进”或“等待权限”。
可直接推进只能包含公开信息研究、代码编写、素材制作、数据整理和内部分析；涉及注册账号、登录、发布、付款、提现、联系他人、使用身份信息或真实资金时，必须 mode=等待权限，并在 permission_needed 中列出 name/reason。
不要要求密码、验证码、私钥。不要承诺收益，不要违法、欺诈、赌博、灰产或规避平台规则。"""
    try:
        response = llm.invoke([{"role": "user", "content": prompt}])
        content = response.content if isinstance(response.content, str) else str(response.content)
        content = content.strip().replace("```json", "").replace("```", "").strip()
        action = json.loads(content)
    except Exception:
        action = _fallback_action(state)
    for item in action.get("permission_needed", []):
        item.setdefault("status", "待确认")
        state["permissions"].append(item)
    mode = action.get("mode", "可直接推进")
    state["active_task"] = action.get("action", "等待下一步动作")
    state["activity"].append({
        "text": ("已生成下一步动作：" if mode == "可直接推进" else "下一步需要权限：") + state["active_task"],
        "time": __import__("datetime").datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
    })
    return _write_money_state(state)


@app.post("/api/money/run", response_model=MoneyState)
def run_money_task(request: MoneyRunRequest):
    """Run a batch of safe autonomous work and pause only at permission boundaries."""
    state = _read_money_state()
    if state.get("status") != "active":
        raise HTTPException(status_code=409, detail="总任务尚未处于执行中")
    pending_permissions = [p for p in state.get("permissions", []) if not any(marker in str(p.get("status", "")) for marker in ("已完成", "complete", "done"))]
    if pending_permissions:
        raise HTTPException(status_code=409, detail="存在未完成的用户操作，请先在看板中确认完成")
    prompt = f"""你是正在执行赚钱总任务的自主执行代理。请连续完成一轮不需要外部权限的工作。
总任务：{state.get('mission')}
本金：{state.get('initial_capital')}，当前余额：{state.get('balance')}，目标：{state.get('target_amount')}
规则：{state.get('rules') or '遵守法律，不借贷，不做高风险投机'}
最近行动：{state.get('activity', [])[-8:]}
用户补充重点：{request.focus}

只返回 JSON：actions（对象数组）、permission_needed（对象数组）。
actions 需要 2-5 项，每项含 action、result、next。只允许记录真实可以在当前环境完成的工作，例如公开信息整理、方案比较、代码编写、文件生成、内部分析。不要把计划冒充完成，不要声称已经访问或发布到网站，除非确实完成。
permission_needed 只列出注册、登录、发布、付款、提现、使用账号/身份信息或真实资金时必须由用户开放的项目，每项含 name/reason。
不要要求密码、验证码、私钥。不要承诺收益，不要违法、欺诈、赌博、灰产或规避平台规则。"""
    try:
        response = llm.invoke([{"role": "user", "content": prompt}])
        content = response.content if isinstance(response.content, str) else str(response.content)
        content = content.strip().replace("```json", "").replace("```", "").strip()
        result = json.loads(content)
    except Exception:
        result = {
            "actions": [
                {"action": "整理适合当前本金和规则的低成本方向", "result": "待验证：形成候选方向清单", "next": "比较公开平台的准入与收费规则"},
                {"action": "比较 3 个可发布数字产品或小游戏的平台规则", "result": "待验证：需要在可访问的公开页面核对规则", "next": "选择平台后再申请账号或发布权限"},
            ],
            "permission_needed": [],
        }
    now = __import__("datetime").datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    for item in result.get("actions", [])[:5]:
        text = f"计划/待验证：{item.get('action', '')}。预期结果：{item.get('result', '')}。下一步：{item.get('next', '')}"
        state["activity"].append({"text": text, "time": now})
        state["active_task"] = item.get("next") or item.get("action") or state.get("active_task", "")
    for item in result.get("permission_needed", []):
        item.setdefault("status", "待确认")
        state["permissions"].append(item)
        state["activity"].append({"text": f"等待权限：{item.get('name', '')}。原因：{item.get('reason', '')}", "time": now})
    return _write_money_state(state)


@app.post("/api/money/generate", response_model=MoneyResponse)
def generate_money_plan(request: MoneyRequest):
    """Generate a conservative, actionable earning plan without executing external actions."""
    if not request.need.strip():
        raise HTTPException(status_code=400, detail="请先填写赚钱需求")
    prompt = f"""你是一个务实的收入方案顾问。请基于以下信息，设计一个合法、低风险、可验证的赚钱方案。
用户需求：{request.need}
用户规则与边界：{request.rules or '未填写，请采用保守原则'}
已有资源与限制：{request.context or '未知，不要臆测'}

只返回 JSON，不要 Markdown，字段必须是：title(string), summary(string), fit_reason(string), steps(string数组，4-6项), cost(string), cycle(string), income(string), risks(string数组，3-5项), needs(对象数组，每项含 name/reason/status), first_action(string)。
不要承诺收益，不要建议违法、欺诈、赌博、灰产、违规爬取、借贷或高风险投机。不要索要密码、验证码或私钥；needs 只列出完成下一步所需的账号类型、公开资料或用户确认。"""
    try:
        response = llm.invoke([{"role": "user", "content": prompt}])
        content = response.content if isinstance(response.content, str) else str(response.content)
        content = content.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(content)
        return MoneyResponse(**data)
    except Exception:
        return MoneyResponse(**_fallback_money_plan(request))





# ===== API 路由 =====

@app.post("/api/chat", response_model=ChatResponse)

def chat(request: ChatRequest):

    """AI 计算对话接口"""

    messages = []

    if request.conversation_history:

        for msg in request.conversation_history:

            messages.append({"role": msg["role"], "content": msg["content"]})



    messages.append({"role": "user", "content": request.message})



    response = calc_agent.invoke({"messages": messages})



    tool_calls = []

    final_reply = ""



    for msg in response["messages"]:

        if msg.type == "ai" and msg.content:

            final_reply = msg.content

        elif msg.type == "tool":

            tool_calls.append({

                "tool": msg.name,

                "input": str(getattr(msg, 'additional_kwargs', {})),

                "output": msg.content

            })



    return ChatResponse(reply=final_reply, tool_calls=tool_calls)








@app.get("/api/weather")
def weather(city: str):
    """查询城市的实时天气（通过 Open-Meteo，优先内置坐标表，未知城市自动搜索）"""
    if not city:
        raise HTTPException(status_code=400, detail="请提供城市名称")

    # 内置城市经纬度映射（保证常见城市准确）
    city_coords = {
        "北京": (39.9042, 116.4074), "上海": (31.2304, 121.4737),
        "天津": (39.3434, 117.3616), "重庆": (29.4316, 106.9123),
        "广州": (23.1291, 113.2644), "深圳": (22.5431, 114.0579),
        "杭州": (30.2741, 120.1551), "成都": (30.5728, 104.0668),
        "武汉": (30.5928, 114.3054), "南京": (32.0603, 118.7969),
        "西安": (34.3416, 108.9398), "长沙": (28.2282, 112.9388),
        "郑州": (34.7466, 113.6253), "沈阳": (41.8057, 123.4315),
        "青岛": (36.0671, 120.3826), "厦门": (24.4798, 118.0894),
        "苏州": (31.2990, 120.5853), "宁波": (29.8683, 121.5440),
        "大连": (38.9140, 121.6147), "昆明": (25.0389, 102.7063),
        "福州": (26.0745, 119.2965), "济南": (36.6519, 116.9972),
        "哈尔滨": (45.8038, 126.5350), "长春": (43.8969, 125.3263),
        "合肥": (31.8206, 117.2272), "南昌": (28.6829, 115.8582),
        "南宁": (22.8170, 108.3665), "海口": (20.0440, 110.1934),
        "贵阳": (26.6470, 106.6302), "太原": (37.8706, 112.5489),
        "石家庄": (38.0428, 114.5149), "呼和浩特": (40.8422, 111.7499),
        "乌鲁木齐": (43.8256, 87.6168), "兰州": (36.0611, 103.8343),
        "银川": (38.4680, 106.2750), "西宁": (36.6175, 101.7780),
        "拉萨": (29.6520, 91.1721), "珠海": (22.2711, 113.5666),
        "东莞": (23.0208, 113.7518), "佛山": (23.0219, 113.1214),
        "中山": (22.5176, 113.3928), "惠州": (23.1123, 114.4158),
        "温州": (27.9939, 120.6994), "无锡": (31.4906, 120.3114),
        "徐州": (34.2058, 117.2841), "绍兴": (30.0024, 120.5821),
        "嘉兴": (30.7710, 120.7551), "唐山": (39.6309, 118.1804),
        "洛阳": (34.6180, 112.4540), "襄阳": (32.0090, 112.1226),
        "宜昌": (30.6919, 111.2864), "桂林": (25.2736, 110.2900),
        "三亚": (18.2528, 109.5119), "大理": (25.5916, 100.2299),
        "香港": (22.3193, 114.1694), "澳门": (22.2006, 113.5450),
        "台北": (25.0330, 121.5654),
    }

    # WMO 天气代码 -> 中文
    wmo_codes = {
        0: "晴天", 1: "少云", 2: "多云", 3: "阴天",
        45: "雾", 48: "雾凇",
        51: "小毛毛雨", 53: "毛毛雨", 55: "大毛毛雨",
        56: "冻毛毛雨", 57: "冻大毛毛雨",
        61: "小雨", 63: "中雨", 65: "大雨",
        66: "冻雨", 67: "冻大雨",
        71: "小雪", 73: "中雪", 75: "大雪", 77: "雪粒",
        80: "小阵雨", 81: "中阵雨", 82: "大阵雨",
        85: "小阵雪", 86: "大阵雪",
        95: "雷暴", 96: "雷暴加冰雹", 99: "强雷暴加冰雹"
    }

    # 风向中文映射
    wind_directions = {
        "N": "北", "NNE": "东北偏北", "NE": "东北", "ENE": "东北偏东",
        "E": "东", "ESE": "东南偏东", "SE": "东南", "SSE": "东南偏南",
        "S": "南", "SSW": "西南偏南", "SW": "西南", "WSW": "西南偏西",
        "W": "西", "WNW": "西北偏西", "NW": "西北", "NNW": "西北偏北"
    }

    try:
        # 第一步：获取城市坐标（优先内置表，否则搜索）
        lat, lon = None, None
        city_name = city

        if city in city_coords:
            lat, lon = city_coords[city]
        else:
            # 不在内置表中，通过 Open-Meteo 地理编码搜索
            geo_resp = httpx.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": city, "count": 5, "language": "zh", "format": "json"},
                timeout=10
            )
            if geo_resp.status_code == 200:
                geo_data = geo_resp.json()
                results = geo_data.get("results", [])
                if results:
                    cn_results = [r for r in results if r.get("country_code") == "CN"]
                    best = cn_results[0] if cn_results else results[0]
                    lat = best["latitude"]
                    lon = best["longitude"]
                    city_name = best.get("name", city)

        if lat is None or lon is None:
            return {"city": city, "error": "未找到该城市，请检查城市名称"}

        # 第二步：用坐标查实时天气
        weather_resp = httpx.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat, "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m,wind_direction_10m",
                "timezone": "Asia/Shanghai"
            },
            timeout=10
        )

        if weather_resp.status_code != 200:
            return {"city": city_name, "error": f"查询失败 (HTTP {weather_resp.status_code})"}

        data = weather_resp.json()
        current = data.get("current", {})

        code = current.get("weather_code", -1)
        condition = wmo_codes.get(code, "未知")

        angle = current.get("wind_direction_10m", 0)
        dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        idx = round(angle / 22.5) % 16
        wind_dir = wind_directions.get(dirs[idx], "")

        return {
            "city": city_name,
            "condition": condition,
            "temperature": f"{current.get("temperature_2m", "?")}\u00b0C",
            "humidity": f"{current.get("relative_humidity_2m", "?")}%",
            "wind": f"{wind_dir}\u98ce {current.get("wind_speed_10m", "?")}km/h",
            "precipitation": f"{current.get("precipitation", 0)}mm",
            "update_time": current.get("time", ""),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询天气失败: {str(e)}")
@app.get("/api/sports/nba")

def sports_nba():

    """获取 NBA 当日比赛结果（通过 ESPN API）"""

    try:

        resp = httpx.get(

            "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",

            timeout=10

        )

        if resp.status_code != 200:

            return {"error": f"查询失败 (HTTP {resp.status_code})"}



        data = resp.json()

        games = []



        for event in data.get("events", []):

            competition = event["competitions"][0]

            home = competition["competitors"][0]

            away = competition["competitors"][1]



            games.append({

                "id": event["id"],

                "date": event["date"],

                "status": competition["status"]["type"]["description"],

                "period": competition["status"].get("period", 0),

                "clock": competition["status"].get("displayClock", ""),

                "home_team": {

                    "name": home["team"]["displayName"],

                    "abbreviation": home["team"]["abbreviation"],

                    "logo": home["team"].get("logo", ""),

                    "score": home["score"],

                    "record": home.get("records", [{}])[0].get("summary", "") if home.get("records") else ""

                },

                "away_team": {

                    "name": away["team"]["displayName"],

                    "abbreviation": away["team"]["abbreviation"],

                    "logo": away["team"].get("logo", ""),

                    "score": away["score"],

                    "record": away.get("records", [{}])[0].get("summary", "") if away.get("records") else ""

                },

                "venue": competition.get("venue", {}).get("fullName", "N/A")

            })



        return {

            "date": data.get("day", ""),

            "season": data.get("league", {}).get("season", {}).get("displayName", ""),

            "total_games": len(games),

            "games": games

        }



    except Exception as e:

        raise HTTPException(status_code=500, detail=f"查询 NBA 数据失败: {str(e)}")





@app.get("/api/sports/feed/{league}")
def sports_feed(league: str, date: str | None = None):
    """Return dated scoreboard data for the daily sports module."""
    configs = {
        "nba": ("basketball", "nba", "NBA"),
        "worldcup": ("soccer", "fifa.world", "World Cup"),
    }
    if league not in configs:
        raise HTTPException(status_code=404, detail="Unsupported sports league")

    sport, competition, label = configs[league]
    query_date = date or __import__("datetime").date.today().isoformat()
    compact_date = query_date.replace("-", "")
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{competition}/scoreboard"

    try:
        response = httpx.get(url, params={"dates": compact_date}, timeout=12)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Sports data unavailable: {exc}")

    games = []
    for event in payload.get("events", []):
        competition_data = event.get("competitions", [{}])[0]
        competitors = competition_data.get("competitors", [])
        home = next((item for item in competitors if item.get("homeAway") == "home"), competitors[0] if competitors else {})
        away = next((item for item in competitors if item.get("homeAway") == "away"), competitors[1] if len(competitors) > 1 else {})
        status = competition_data.get("status", {}).get("type", {})
        games.append({
            "id": event.get("id"),
            "date": event.get("date"),
            "status": status.get("description", status.get("detail", "")),
            "state": status.get("state", "pre"),
            "clock": competition_data.get("status", {}).get("displayClock", ""),
            "home_team": _sports_team(home),
            "away_team": _sports_team(away),
            "venue": competition_data.get("venue", {}).get("fullName", ""),
        })
    return {"league": label, "date": query_date, "total_games": len(games), "games": games}


def _sports_team(competitor: dict) -> dict:
    team = competitor.get("team", {})
    return {
        "name": team.get("displayName", "Unknown"),
        "abbreviation": team.get("abbreviation", ""),
        "logo": team.get("logo", ""),
        "score": competitor.get("score", "-"),
        "record": (competitor.get("records") or [{}])[0].get("summary", ""),
    }


@app.get("/api/sports/game/{league}/{event_id}")
def sports_game(league: str, event_id: str):
    """Return a match summary and normalized player boxscore."""
    configs = {"nba": ("basketball", "nba"), "worldcup": ("soccer", "fifa.world")}
    if league not in configs:
        raise HTTPException(status_code=404, detail="Unsupported sports league")
    sport, competition = configs[league]
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{competition}/summary"
    try:
        response = httpx.get(url, params={"event": event_id}, timeout=12)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Match data unavailable: {exc}")

    competition_data = payload.get("header", {}).get("competitions", [{}])[0]
    competitors = competition_data.get("competitors", [])
    players = []
    for side in payload.get("boxscore", {}).get("players", []):
        team = side.get("team", {})
        statistics = side.get("statistics", [])
        labels = statistics[0].get("names", []) if statistics else []
        for athlete in side.get("statistics", [{}])[0].get("athletes", []):
            values = athlete.get("statistics", [])
            stats = dict(zip(labels, values))
            players.append({
                "name": athlete.get("athlete", {}).get("displayName", ""),
                "team": team.get("abbreviation", ""),
                "stats": stats,
            })
    return {"id": event_id, "competition": competition_data, "players": players}


@app.get("/api/billing")

def billing():

    """查询 API 余额信息"""

    masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "未配置"



    balance_info = None

    try:

        resp = httpx.get(

            "https://api.deepseek.com/user/balance",

            headers={"Authorization": f"Bearer {api_key}"},

            timeout=10

        )

        if resp.status_code == 200:

            balance_info = resp.json()

        else:

            balance_info = {"error": f"查询失败 (HTTP {resp.status_code})"}

    except Exception as e:

        balance_info = {"error": f"查询失败: {str(e)}"}



    return {

        "api_name": "DeepSeek (deepseek-v4-flash)",

        "api_key": masked_key,

        "base_url": "https://api.deepseek.com",

        "balance": balance_info

    }








class NoteSaveRequest(BaseModel):
    path: str
    content: str

class NoteFolderRequest(BaseModel):
    path: str
    name: str

class NoteDeleteRequest(BaseModel):
    path: str

NOTES_ROOT = "notes"
os.makedirs(NOTES_ROOT, exist_ok=True)

def _check_path(base, target):
    rt = os.path.realpath(os.path.join(base, target))
    rb = os.path.realpath(base)
    return rt.startswith(rb)

def _build_tree(dp, prefix):
    items = []
    for e in sorted(os.listdir(dp)):
        ep = os.path.join(dp, e)
        rp = prefix + "/" + e
        if os.path.isdir(ep):
            ch = _build_tree(ep, rp)
            items.append({"name": e, "path": rp, "type": "folder", "children": ch})
        elif e.endswith(".md"):
            items.append({"name": e[:-3], "path": rp, "type": "file"})
    return items

@app.get("/api/notes/tree")
def notes_tree():
    if not os.path.exists(NOTES_ROOT):
        return {"items": []}
    items = []
    for e in sorted(os.listdir(NOTES_ROOT)):
        ep = os.path.join(NOTES_ROOT, e)
        if os.path.isdir(ep):
            ch = _build_tree(ep, e)
            items.append({"name": e, "path": e, "type": "folder", "children": ch})
        elif e.endswith(".md"):
            items.append({"name": e[:-3], "path": e, "type": "file"})
    return {"items": items}

@app.get("/api/notes/read")
def notes_read(path: str):
    fp = os.path.join(NOTES_ROOT, path)
    if not os.path.exists(fp) or not fp.endswith(".md") or not _check_path(NOTES_ROOT, path):
        raise HTTPException(status_code=404, detail="Not found")
    with open(fp, "r", encoding="utf-8") as f:
        content = f.read()
    return {"path": path, "content": content, "name": os.path.basename(fp)[:-3]}

@app.post("/api/notes/save")
def notes_save(req: NoteSaveRequest):
    fp = os.path.join(NOTES_ROOT, req.path)
    if not req.path.endswith(".md"):
        req.path += ".md"
        fp = os.path.join(NOTES_ROOT, req.path)
    if not _check_path(NOTES_ROOT, req.path):
        raise HTTPException(status_code=403, detail="Forbidden")
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    with open(fp, "w", encoding="utf-8") as f:
        f.write(req.content)
    return {"status": "ok", "path": req.path}

@app.post("/api/notes/folder")
def notes_folder(req: NoteFolderRequest):
    fp = os.path.join(NOTES_ROOT, req.path, req.name)
    if not _check_path(NOTES_ROOT, os.path.join(req.path, req.name)):
        raise HTTPException(status_code=403, detail="Forbidden")
    os.makedirs(fp, exist_ok=True)
    return {"status": "ok"}

@app.delete("/api/notes/delete")
def notes_delete(req: NoteDeleteRequest):
    fp = os.path.join(NOTES_ROOT, req.path)
    if not _check_path(NOTES_ROOT, req.path):
        raise HTTPException(status_code=403, detail="Forbidden")
    if os.path.isdir(fp):
        import shutil
        shutil.rmtree(fp)
    elif os.path.isfile(fp):
        os.remove(fp)
    else:
        raise HTTPException(status_code=404, detail="Not found")
    return {"status": "ok"}


def _browser_action(action):
    try:
        return action()
    except BrowserError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/browser/open")
def browser_open(req: BrowserOpenRequest):
    return _browser_action(lambda: browser.open(req.url))


@app.post("/api/browser/search")
def browser_search(req: BrowserSearchRequest):
    return _browser_action(lambda: browser.search(req.keyword))


@app.post("/api/browser/click")
def browser_click(req: BrowserLocatorRequest):
    return _browser_action(lambda: browser.click(req.locator))


@app.post("/api/browser/type")
def browser_type(req: BrowserTypeRequest):
    return _browser_action(lambda: browser.type(req.locator, req.text))


@app.post("/api/browser/screenshot")
def browser_screenshot(req: BrowserScreenshotRequest):
    filename = os.path.basename(req.filename.strip()) or "latest.png"
    if not filename.lower().endswith((".png", ".jpg", ".jpeg")):
        filename += ".png"
    path = os.path.join("browser_screenshots", filename)
    result = _browser_action(lambda: browser.screenshot(path))
    result["filename"] = filename
    return result


@app.post("/api/browser/close")
def browser_close():
    browser.close()
    return {"message": "Browser 已关闭"}


@app.get("/api/browser/status")
def browser_status():
    return _browser_action(browser.state)

@app.get("/api/status")

def status():

    """服务状态"""

    return {

        "app": "syf_agent",

        "version": "1.0.0",

        "status": "running",

        "features": ["calculator", "weather", "sports", "billing", "notes", "money", "web", "browser"]

    }





# ===== 前端页面托管 =====

@app.get("/")

def root():

    """返回主页面"""

    return FileResponse("index.html")





@app.get("/{path:path}")

def catch_all(path: str):

    """处理其他路径，返回对应的静态文件"""

    # 尝试返回 ui 下的文件

    ui_path = f"ui/{path}"

    if os.path.isfile(ui_path):

        return FileResponse(ui_path)

    # 尝试返回当前目录下的文件

    if os.path.isfile(path):

        return FileResponse(path)

    raise HTTPException(status_code=404, detail="Not Found")





if __name__ == "__main__":

    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
