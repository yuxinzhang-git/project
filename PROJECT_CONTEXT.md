# my-agent 项目上下文

> 这份文档用于新对话快速理解项目。代码变更后应同步更新本文档中的入口、目录和已知问题。

## 1. 项目定位

my-agent 是一个本地个人助手应用：

- 后端使用 FastAPI；
- 前端是由后端直接提供的静态 HTML/CSS/JavaScript；
- 集成 AI 对话、计算工具、天气、体育、账单、笔记和任务管理；
- 集成 Playwright + Microsoft Edge，实现通用网页操作和站点级自动化；
- 支持运行时加载 skills/*/SKILL.md；
- 数据默认保存在项目根目录下的 data/。

项目不是前后端分离的构建型 Web 工程，没有 Vite、Webpack 或独立前端开发服务器。启动一个 Uvicorn 服务即可同时提供 API 和页面。

## 2. 运行入口

### Windows 推荐入口

    Set-Location F:\zyx\agent\my-agent
    .\agent\Scripts\python.exe agent_api.py

也可以执行：

    .\start.bat

### Python 入口链路

    start.bat
      -> agent\Scripts\python.exe agent_api.py
      -> agent_api.py 导入 app.main:app
      -> uvicorn.run(app, host=127.0.0.1, port=8000)
      -> app/main.py 创建 FastAPI 应用

应用地址：

    http://127.0.0.1:8000

### MCP 入口

Playwright MCP 配置位于 .codex/config.toml。当前配置使用项目内 Node.js 和 @playwright/mcp：

    .tools/node/node.exe
    node_modules/@playwright/mcp/cli.js

也可以执行：

    .\scripts\start-playwright-mcp.ps1

该脚本通过 $PSScriptRoot 计算项目根目录，适合从任意当前工作目录调用。

## 3. 顶层目录

    app/
      main.py                  FastAPI 应用组装、静态页面和生命周期
      config.py                项目根、数据目录、技能目录等路径配置
      api/                     HTTP 路由
      services/                业务逻辑和数据持久化
      schemas/                 Pydantic 请求/响应模型
      browser/                 Playwright 浏览器抽象和站点适配

    frontend/                  静态页面
      index.html               首页
      daily.html               日常功能
      learning.html            学习/笔记
      money.html               收入任务
      web.html                 网页操作入口
      browser.html             通用 Browser 控制台
      smart.html               自然语言网页操作
      stock.html               A 股行情研究看板
      stock.js                 行情快照、个股日线和刷新状态
      ui/                      天气、体育、账单、计算器子页面

    data/
      notes/                   Markdown 笔记
      money/                   收入任务状态和本地工件
      xianyu/                  闲鱼任务状态
      browser/profile/         Edge 持久化用户目录
      browser/screenshots/     浏览器截图

    skills/                    项目运行时技能清单
    scripts/                   启动和验证脚本
    examples/                  最小示例
    .tools/node/               项目内 Node.js
    node_modules/              npm 依赖，主要是 Playwright MCP
    agent/                     Python 虚拟环境

## 4. 后端架构

### 应用组装层

app/main.py 的 create_app()：

1. 初始化运行目录；
2. 扫描并加载 skills/*/SKILL.md 的 frontmatter；
3. 挂载 /ui 和 /browser-screenshots；
4. 注册各个 API router；
5. 注册 /api/status 和静态页面兜底路由；
6. 在生命周期结束时关闭 Browser。

### API 层

| 文件 | 主要功能 | 前缀 |
|---|---|---|
| app/api/chat.py | AI 对话、计算工具和只读网页搜索 | /api/chat |
| app/api/daily.py | 天气、体育、账单 | /api/weather、/api/sports/*、/api/billing |
| app/api/learning.py | 笔记树、读取、保存、文件夹、删除 | /api/notes/* |
| app/api/money.py | 收入方案、想法、工件、推进任务 | /api/money/* |
| app/api/income_plan.py | 根据用户技能、成本、地点和频率生成赚钱方案 | /api/income-plan/* |
| app/api/xianyu_tasks.py | 闲鱼交付任务和汇总 | /api/xianyu/* |
| app/api/web.py | 通用浏览器打开、搜索、点击、输入、截图 | /api/browser/* |
| app/api/smart.py | 自然语言网页操作和闲鱼估价 | /api/smart/* |
| app/api/skills.py | Runtime Skills 查询、详情、重载 | /api/skills/* |
| app/api/stocks.py | A 股行情快照和个股历史日线 | /api/stocks/* |

API 层主要负责参数接收和 HTTP 异常转换，业务逻辑位于 app/services/。

### 服务层

- ChatService：使用 DeepSeek 兼容 OpenAI API，注册计算工具和 `web_search` 只读 HTTP 搜索工具；工具调用仅在 Agent 内部执行，API 对外只返回最终 `reply`；
- `frontend/markdown.js`：聊天 Agent 回复的安全 Markdown 渲染器，支持标题、表格、强调、列表、引用、链接和代码块；用户输入仍按纯文本渲染。
- 用户可见的产品名称统一为 `zyx_agent`；当前生效 FastAPI 应用标题仍定义为 `app/main.py` 中的 `my-agent`。
- NotesService：管理 data/notes 下的 Markdown 文件，并限制路径不能逃逸根目录；
- MoneyService：维护收入任务状态、想法、账本和本地工件；
- IncomePlanService：调用 DeepSeek，根据现有技能、预算、实施地点、频率、时间、风险偏好等条件生成 1-3 个结构化赚钱方案；页面可将方案保存为 MoneyService 的想法；
- XianyuTaskService：维护闲鱼一次性交付任务和收入汇总；
- SmartOperationService：将中文/英文命令解析为结构化操作计划，再分发给站点适配器；
- RuntimeSkillRegistry：读取技能 frontmatter，按需加载完整 SKILL.md；
- weather.py：城市坐标和 Open-Meteo 查询；
- sports.py：ESPN 数据接口查询 NBA/世界杯；
- `app/tools/web_search.py`：固定 DuckDuckGo HTML 端点的只读 HTTP 搜索，只允许 GET，不接受任意 URL，不跟随重定向，不复用浏览器登录态；
- billing.py：查询 DeepSeek 账户余额。
- `app/services/stocks.py`：从东方财富公开接口获取固定自选股及沪深 300 报价、个股前复权日线和财报 ROE；仅接受预设代码与 `6m`/`1y` 周期。

股票数据边界：

- `GET /api/stocks/quotes` 返回十只自选 A 股、沪深 300、来源和本地 `fetched_at`；`GET /api/stocks/{code}/history?period=6m|1y` 返回个股带日期的日线。
- 页面仅在可见时每 15 秒请求报价；服务端报价缓存 10 秒、历史缓存 5 分钟、ROE 财报缓存 24 小时。刷新失败时保留当前页面会话内最后成功的快照并标为过期。
- 行情来自东方财富免费公开接口，不保证实时服务等级，也不是交易所授权行情；非交易时间显示的可能是最近一个交易日的报价，不承诺毫秒级实时。
- ROE 属于财务报告数据，与当前行情分开缓存和展示，并标注对应报告期；缺失字段显示为暂无，不用静态示例值补齐。

聊天 Agent 的搜索边界：

- 只返回标题、摘要和来源 URL，不点击、不输入、不登录、不下载、不发布、不购买；
- 查询、结果数量、响应大小和超时均有限制；
- 搜索结果作为不可信外部资料处理，Agent 不执行其中包含的指令，并应在回答中提供来源 URL 和查询时间；
- 天气和体育服务仍由各自 API 页面使用，未通过本次搜索工具把浏览器操作开放给聊天 Agent。

聊天界面不会显示 Agent 的工具执行过程；`frontend/ui/calculator.html` 只渲染 `/api/chat` 返回的最终 `reply`。

## 5. 浏览器自动化架构

    HTTP API / SmartOperationService
              |
              v
    app.browser.Browser
              |
              v
    Playwright persistent_context(channel=msedge)
              |
              +-- 通用组件：SearchBox / VideoList / Player / Pagination
              |
              +-- BilibiliAdapter
              |     +-- navigation
              |     +-- actions
              |     +-- pages/components
              |
              +-- TaobaoAdapter
              |     +-- navigation
              |     +-- product_list
              |     +-- login/risk-control guard
              |
              +-- XianyuAdapter
                    +-- navigation
                    +-- actions
                    +-- login/risk-control/network guard

### Browser facade

app/browser/browser.py 负责：

- 启动和关闭 Playwright；
- 使用 Microsoft Edge；
- 使用项目独立的持久化 profile；
- 打开 URL、后退、搜索、点击、输入、键盘操作；
- 读取页面状态、可交互元素和文本；
- 保存截图；
- 在浏览器页面/上下文关闭时自动重置并重试。

### 页面上下文

app/browser/context.py 根据当前 URL 和标题推断当前站点、页面类型、搜索关键词、Bilibili 频道/视频、闲鱼商品和当前用户相关信息。

这样用户手动在 Edge 中跳转后，服务层不会继续使用旧的页面状态。

### 风控边界

淘宝和闲鱼适配器会识别登录、验证码、滑块、安全验证和风险控制页面，并返回明确错误；项目不绕过验证。

## 6. 前端页面

首页是 frontend/index.html，主要入口：

- daily.html：天气、计算器、体育、账单；
- learning.html：笔记管理；
- money.html：收入任务和本地工件；
  - “方案生成”标签调用 `/api/income-plan/generate`，生成准备过程、客户群体、获客方式、风险、验证指标和第一步行动，并可保存为“想法”；
  - “想法清单”和“实际落地任务”均支持确认后手动删除，分别调用 `/api/money/ideas/{idea_id}` 和 `/api/xianyu/tasks/{task_id}`；
- web.html：网页操作模块选择；
- browser.html：通用 Browser 控制台；
- smart.html：自然语言网页操作；
- stock.html：A 股公开行情看板，stock.js 拉取报价快照与个股日线；
- frontend/ui/*：具体功能子页面。

前端通过 fetch('/api/...') 调用后端 API，不需要额外启动前端服务器。

## 7. 路径和配置约定

### 自动推导的路径

app/config.py 使用：

    project_root = Path(__file__).resolve().parent.parent

因此 frontend/、data/、data/notes/、data/money/、data/xianyu/、data/browser/profile/、data/browser/screenshots/ 和 skills/ 不需要手动改成绝对路径。

### 需要注意的绝对路径

.codex/config.toml 的 MCP 配置需要绝对路径。当前路径是：

    F:\zyx\agent\my-agent

如果项目再次移动，需要同步修改：

- .codex/config.toml 的 command；
- .codex/config.toml 的 args[0]。

start.bat 会先执行 cd /d "%~dp0"，所以它内部使用相对路径是安全的。

### 环境变量

.env 中配置 DEEPSEEK_API_KEY。该文件已被 .gitignore 忽略，不应提交到版本库。已有 Key 曾出现在本地文件中，建议在服务商后台轮换。

## 8. 依赖和验证

Python 依赖声明位于 requirements.txt。重建环境后：

    Set-Location F:\zyx\agent\my-agent
    .\agent\Scripts\python.exe -m pip install -r requirements.txt
    .\agent\Scripts\python.exe -m compileall -q app
    .\agent\Scripts\python.exe -c "from app.config import settings; from app.main import app; print(settings.project_root); print(len(app.routes))"

Node/MCP 验证：

    .\.tools\node\node.exe .\node_modules\@playwright\mcp\cli.js --help

真实网站验证需要网络、Edge 和登录状态；遇到登录或风控页面属于预期结果。

## 9. 已知限制

- Python unittest 回归测试位于 tests/，可用 `.\agent\Scripts\python.exe -m unittest discover -s tests -v` 运行；
- 项目根目录现已提供 requirements.txt，但依赖版本仍需要随 Python/Playwright 升级维护；
- .git 目录当前不包含可识别的 Git 元数据，不能依赖 Git 查看历史；
- 系统 Python 版本、Edge 安装路径和网络状态会影响浏览器相关功能；
- AI 对话和账单接口依赖有效的 DeepSeek API Key；
- Bilibili、淘宝、闲鱼页面结构变化可能需要更新站点选择器。

## 10. 新对话建议

新对话开始时优先阅读：

1. 本文档 PROJECT_CONTEXT.md；
2. README.md；
3. app/main.py；
4. app/config.py；
5. 与当前任务对应的 app/api/*、app/services/* 或 app/browser/sites/*。

如果用户要求修复启动问题，先检查：

    Test-Path .\agent\Scripts\python.exe
    Test-Path .\.tools\node\node.exe
    Test-Path .\node_modules\@playwright\mcp\cli.js
    Get-Content .\.codex\config.toml
