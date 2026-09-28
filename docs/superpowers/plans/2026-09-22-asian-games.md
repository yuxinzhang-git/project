# 2026 亚运会体育板块 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将体育页面改为通过后端代理展示 2026 年亚运会实时赛程与赛果，并支持北京时间的前后日期切换。

**Architecture:** 新增独立亚运会服务层，固定访问公开实时数据源并把原始响应转换为统一的已结束/进行中/待开始模型；新增 FastAPI 代理接口；前端只调用本地代理并按日期和状态渲染。旧 NBA/世界杯接口保留兼容。

**Tech Stack:** Python 3.13、FastAPI、httpx、标准库 `datetime`/`zoneinfo`、原生 HTML/CSS/JavaScript、标准库 `unittest`。

## Global Constraints

- 所有第三方访问只能由后端固定 URL 发起，前端不得传入任意 URL。
- 赛事时间统一转换为 `Asia/Shanghai` 后返回和展示。
- 数据源失败、无数据和字段缺失必须区分处理，禁止用静态虚构赛果兜底。
- 原有 NBA/世界杯兼容接口继续保留。
- 每个新服务行为先写失败测试，再写生产代码。

### Task 1: 设计实时数据适配器

**Files:**
- Create: `app/services/asian_games.py`
- Test: `tests/test_asian_games.py`

**Interfaces:**
- Produces `asian_games_feed(date: str | None) -> dict`。
- 返回 `event`、`date`、`timezone`、`updated_at`、`source`、`source_status`、`finished`、`live`、`upcoming`、`total`。

- [ ] **Step 1: Write failing tests**
  - 测试固定请求端点、日期参数、响应归一化、北京时间转换、三种状态分组和数据源异常。
- [ ] **Step 2: Run `tests.test_asian_games` and confirm failure**
- [ ] **Step 3: Implement the adapter**
  - 用 `httpx.Client` 固定访问数据源，仅 `GET`；对数据源响应字段做显式映射。
- [ ] **Step 4: Run adapter tests and confirm pass**

### Task 2: 增加 FastAPI 后端代理

**Files:**
- Modify: `app/api/daily.py`
- Test: `tests/test_asian_games_api.py`

**Interfaces:**
- `GET /api/sports/asian-games?date=YYYY-MM-DD`。

- [ ] **Step 1: Write failing API tests**
- [ ] **Step 2: Run tests and confirm missing route/failure behavior**
- [ ] **Step 3: Register route and date validation**
- [ ] **Step 4: Run API tests and confirm pass**

### Task 3: 重做体育页面

**Files:**
- Modify: `frontend/ui/sports.html`
- Test: `tests/test_sports_page.py`

**Interfaces:**
- 页面只请求 `/api/sports/asian-games`。
- 页面提供前一天、今天、后一天按钮，并渲染 `finished`、`live`、`upcoming` 三个分组。

- [ ] **Step 1: Write failing source-level tests**
- [ ] **Step 2: Run tests and confirm old NBA/世界杯 markup fails**
- [ ] **Step 3: Replace static demo markup and JS with Asian Games UI**
- [ ] **Step 4: Run source tests and Node syntax check**

### Task 4: 文档与全量验证

**Files:**
- Modify: `PROJECT_CONTEXT.md`, `findings.md`, `progress.md`, `task_plan.md`

- [ ] **Step 1: Record endpoint, data source and fallback behavior**
- [ ] **Step 2: Run all Python tests, compileall, Node syntax checks and app import**
- [ ] **Step 3: Run one real current-date API request when network is available**
