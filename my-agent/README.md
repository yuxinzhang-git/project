# my-agent

`my-agent` is a local FastAPI assistant application. It combines a small web UI, deterministic Chinese command parsing, LangChain-based chat/tools, runtime skill manifests, and a layered Playwright browser automation module.

It is designed as a local personal assistant and browser control workbench, not as a hosted multi-user service.

## Features

- Web UI served from `frontend/`
- FastAPI API modules under `app/api/`
- Calculator, weather, sports, billing, notes, money, and Xianyu task services
- Browser automation facade under `app/browser/`
- Site adapters for Bilibili, Taobao, and Xianyu
- Runtime skill manifest loading from `skills/*/SKILL.md`
- Deterministic smart-operation parser for supported Chinese commands

## Project Structure

```text
my-agent/
|-- agent_api.py              # Compatibility entry point for the FastAPI app
|-- app/
|   |-- main.py               # FastAPI app factory and static page routing
|   |-- api/                  # HTTP route modules
|   |-- browser/              # Playwright facade, site adapters, page objects
|   |-- schemas/              # Pydantic request/response models
|   |-- services/             # Business services
|   `-- tools/                # LangChain tools
|-- frontend/                 # Static HTML/JS pages
|-- skills/                   # Runtime skill manifests
|-- examples/                 # Local examples and smoke checks
|-- scripts/                  # Helper scripts
|-- package.json              # Node tooling for Playwright MCP
`-- requirements.txt          # Python dependencies for the app
```

Runtime data such as browser profiles, screenshots, logs, local sessions, and virtual environments should stay out of Git.

## Requirements

- Python 3.12 is known to work; Python 3.10+ should be compatible with the app code.
- Node.js is only needed for the optional Playwright MCP helper in `package.json`.
- Microsoft Edge or a compatible Playwright browser is required for browser automation.

## Setup

Create and activate a virtual environment from this directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -r requirements.txt
python -m playwright install
```

For optional Playwright MCP tooling:

```powershell
npm install
```

## Environment Variables

Create a local `.env` file when you need model-backed chat or billing APIs:

```text
DEEPSEEK_API_KEY=your_key_here
```

Do not commit `.env` or real API keys.

## Run

Start the single local server:

```powershell
python agent_api.py
```

Then open:

```text
http://127.0.0.1:8000
```

The app uses one persistent browser session. Avoid starting multiple Uvicorn processes against the same browser profile.

## Main API Areas

```text
GET  /api/status
GET  /api/smart/capabilities
GET  /api/skills
GET  /api/skills/{name}/manifest
GET  /api/skills/{name}
POST /api/skills/reload
```

Additional routes live in `app/api/` for chat, daily tools, notes, money, browser operations, smart operations, and Xianyu tasks.

## Browser Automation

All Playwright imports and calls are isolated inside `app/browser/`. Business code uses the `Browser` facade, site adapters, page objects, and semantic components. `Browser` owns the persistent browser session, navigation, basic interaction, state inspection, and screenshots.

`PageContext` is rebuilt from the current browser URL and title whenever an operation runs. It contains `site`, `page_type`, `url`, `title`, `keyword`, `channel_id`, `user_id`, and `current_video_id`, so manual browser navigation does not leave stale site state in the service.

Generic component contracts live in `app/browser/components/`:

- `VideoList`: `list()`, `open(index)`, `play(index)`
- `Player`: `play()`, `pause()`
- `SearchBox`: `search(keyword)`

Site-specific selectors remain inside site components and page objects.

## Supported Commands

The smart-operation parser keeps `category` and returns structured plans such as:

```json
{"category":"page_action","target":"video","action":"play","index":3}
```

Supported Chinese commands include examples such as `在哔哩哔哩搜索 Python 教程`, `打开第三个视频`, `播放下一个视频`, `打开淘宝`, `按销量排序`, and `返回搜索结果页`. These commands are deterministic and do not require a model API.

## Safety Boundaries

Taobao and Xianyu login pages, captcha pages, slider verification, and risk-control pages are reported as explicit errors. The automation does not bypass verification or authentication.

Real website checks require network access and a usable browser session. A login or verification page is a valid test result.

## Verification

Run a syntax check:

```powershell
python -m compileall -q app
```

Run the browser smoke example only when a browser session and network access are available:

```powershell
python examples/playwright_edge_smoke.py
```
