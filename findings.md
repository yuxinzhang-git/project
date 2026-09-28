# 项目分析发现

- 已新增 PROJECT_CONTEXT.md，包含项目定位、入口、目录、API、服务层、浏览器自动化、路径约定、依赖和新对话阅读顺序。
- 已新增 requirements.txt，固定当前可用的 FastAPI/Uvicorn/Playwright/LangChain 等依赖版本。
- 旧 agent 已保留为 agent.backup-20260922；新 agent/pyvenv.cfg 使用当前 D:\miniforge3 的 CPython 3.13.13。
- 新环境验证通过：应用导入成功，路由数 17，compileall 成功，MCP CLI 帮助成功，实际 HTTP GET /api/status 返回 200 且状态为 running。

## 当前结论（阶段性）

- 项目根目录：`F:\\zyx\\agent\\my-agent`。
- 主后端入口：`agent_api.py`，实际导入 `app.main:app` 并启动 Uvicorn；`start.bat` 是 Windows 启动包装器。
- 应用内部入口：`app/main.py:create_app()`，负责目录初始化、技能加载、静态前端挂载、API 路由注册和退出时关闭 Browser。
- 配置中心：`app/config.py` 的 `Settings.project_root = Path(__file__).resolve().parent.parent`，主路径配置是相对项目根推导的，不依赖当前工作目录。
- 前端：`frontend/index.html` 为首页，`app/main.py` 用 `FileResponse`/`StaticFiles` 提供静态页面与 `/ui/*`、`/browser-screenshots/*`。
- 浏览器自动化：`app/browser/` 封装 Playwright；持久化 Edge profile 默认位于 `data/browser/profile`，由项目根推导。
- 站点适配：`app/browser/sites/{bilibili,taobao,xianyu}/`，通过 adapter/capability/navigation/pages/components 等层次隔离站点选择器。
- 发现的明确路径风险：README 和 `start.bat` 使用相对路径 `agent\\Scripts\\python.exe`，因此要求从项目根或通过 `start.bat` 启动；若从其他目录运行 `agent_api.py`，会因导入/相对路径而有风险。
- `scripts/start-playwright-mcp.ps1` 使用 `$PSScriptRoot` 推导项目根，路径适配良好，但硬性要求项目内 `.tools\\node\\node.exe` 与 `node_modules\\@playwright\\mcp\\cli.js` 存在。
- `.codex/config.toml:2-3` 将 Playwright MCP 命令和 CLI 写死为 `D:\\agent\\my-agent`，在当前 `F:\\zyx\\agent\\my-agent` 下必然失效；这是需要手动修改的硬性配置。
- `agent/pyvenv.cfg` 记录了 `C:\\Program Files\\Python312\\python.exe` 与旧虚拟环境目录 `F:\\my-agent\\agent`；当前 `agent\\Scripts\\python.exe` 已验证启动失败。不要只改 `pyvenv.cfg`，建议在当前项目根重建虚拟环境并重新安装依赖。
- `README_PLAYWRIGHT_MCP.md:18` 仍使用旧目录 `F:\\my-agent`，属于迁移后的文档命令错误；脚本本身不受此问题影响。
- `.git` 目录当前为空/不包含可识别的 Git 元数据，`git status` 报“不是 Git 仓库”；因此无法依赖 Git 状态判断项目变更历史。
- `start.bat:2` 会先 `cd /d "%~dp0"`，因此其相对路径机制本身正确；真正阻断在 `agent\\Scripts\\python.exe` 已损坏。
- `agent_api.py:9` 是实际服务监听入口，固定监听 `127.0.0.1:8000`；这是服务地址约定，不是项目文件路径，通常无需改。
- `app/main.py:28-29` 的静态目录和 `app/config.py:9-72` 的所有数据/技能目录均基于 `__file__` 的项目根推导，适配当前盘符和目录无需手改。
- `.tools/node`、`node_modules/@playwright/mcp/cli.js`、Edge 可执行文件均已存在；MCP CLI `--help` 验证通过。
- `.env` 含有未脱敏的 DeepSeek API key；`.gitignore` 已忽略 `.env`，但该 key 已出现在本地文件中，建议立即轮换并通过环境变量/本机密钥管理重新配置。
- `.env` 存在但内容尚未展开核对；需确认其中无旧机器绝对路径。
- `.git` 目录的状态尚未完全核实；`git status` 报非 Git 工作树，可能是空/损坏/不完整的 `.git`。

## 2026-09-22 只读 HTTP 搜索工具

- 新增 `app/tools/web_search.py`，固定调用 `https://html.duckduckgo.com/html/`，只传 `q` 查询参数并使用 HTTP GET。
- 工具不接收 URL、方法、请求头、Cookie 或浏览器上下文；HTTP 客户端关闭重定向，且限制查询长度、最大结果数、响应大小和请求超时。
- 返回 JSON，字段为 `query`、`results`、`source`、`retrieved_at`、`warning`；结果仅包含 `title`、`snippet`、`url`。
- `ChatService` 已注册搜索工具，并明确要求把搜索结果当作不可信外部资料、不要执行其中的指令、回答附来源 URL 和查询时间。
- 只读搜索与 `app/browser/` 的 Playwright 操作隔离；天气、体育服务没有额外注册给聊天 Agent。

## 2026-09-22 聊天执行过程显示问题

- 截图中的“调用 web_search”来自前端 `frontend/ui/calculator.html` 对 API `tool_calls` 字段的显式渲染。
- `app/services/chat.py` 在收集最终答复的同时，把每条 LangChain tool message 转成 `tool_calls` 返回；这就是公开响应泄漏执行过程的根因。
- 修复应保留 Agent 内部工具执行，但对外响应只返回最终 `reply`；同时移除前端工具调用渲染，避免旧响应或其他调用方再次展示。
- 已移除 `ChatResponse.tool_calls`、`ChatService.reply()` 的工具调用详情返回，以及计算器页面的工具调用渲染逻辑。

## 2026-09-22 Markdown 显示问题

- 根因：`frontend/ui/calculator.html` 原先将 Agent 回复直接执行 `innerHTML = 文本.replace(/\\n/g, '<br>')`，只处理换行，没有解析 Markdown。
- 新增 `frontend/markdown.js`，先转义原文，再生成受控的 Markdown 标签；支持标题、表格、粗体、斜体、删除线、列表、引用、链接、行内代码和代码块。
- Agent 回复使用 Markdown 渲染，用户输入使用 `textContent`，避免把用户/Agent 原文当作任意 HTML 执行。
