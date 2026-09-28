# A 股实时行情看板 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the stock page's fabricated quote values and chart with clearly timestamped public A-share quotes, financial snapshots, and real daily history.

**Architecture:** Add a fixed-source Eastmoney adapter in `app/services/stocks.py`, expose whitelisted quote/history endpoints through a new router, and have the existing static stock page render only API responses. Keep quote, daily-history, and financial caches separate; show the client session's last successful quote as stale after refresh failures.

**Tech Stack:** Existing FastAPI, `httpx==0.28.1`, static HTML/CSS/JavaScript, and Python `unittest` tests.

## Global Constraints

- Use Eastmoney public endpoints only; they have no real-time SLA and are not represented as exchange-authorized feeds.
- Quote refresh interval is 15 seconds while the page is visible; quote cache is 10 seconds, history cache 5 minutes, and ROE/financial cache 24 hours.
- Only the ten existing A-share codes and CSI 300 code are accepted; no arbitrary URL, symbol, or provider input.
- Missing provider fields become `null`; never fall back to the current hard-coded sample prices, trends, scores, or advice.
- Report local fetch time; report provider time only if present and verifiable. Label ROE with its financial report date.
- Keep dependencies unchanged. The workspace has no recognized Git metadata, so do not stage or commit changes.

---

### Task 1: Eastmoney adapter and service tests

**Files:**
- Create: `tests/test_stocks_service.py`
- Create: `app/services/stocks.py`

**Interfaces:**
- Produces `get_stock_quotes() -> dict` with `fetched_at`, `quotes`, and `benchmark` keys.
- Produces `get_stock_history(code: str, period: str) -> dict` with `code`, `period`, `fetched_at`, and `bars` keys; each bar has `date`, `open`, `close`, `high`, `low`, `volume`, and `amount`.
- Raises `ValueError` for a non-whitelisted code/period and `StockDataError` for unusable upstream data.

- [x] **Step 1: Add failing quote normalization tests**

Create a test fixture with Eastmoney `data.diff` records containing fields `f12`, `f13`, `f14`, `f2`, `f3`, `f4`, `f5`, `f6`, `f9`, `f15`, `f16`, `f17`, `f18`, and `f23`. Mock the `httpx.Client` responses; assert the normalized price/change/high/low/open/previous-close/volume/amount/PE/PB, a Shanghai-time `fetched_at`, and a separately returned `000300` benchmark. Include one quote with absent and `"-"` fields and assert they normalize to `None`.

Use this response helper in the test file:

```python
from unittest.mock import Mock


def response(payload):
    result = Mock()
    result.raise_for_status.return_value = None
    result.json.return_value = payload
    return result
```

The quote test must use this shape and verify the public result rather than asserting provider internals only:

```python
from unittest.mock import patch

from app.services.stocks import _CACHE, get_stock_quotes


def test_normalizes_quotes_and_financial_report():
    _CACHE.clear()
    quote_payload = {
        "data": {"diff": [
            {"f12": "600519", "f13": 1, "f14": "贵州茅台", "f2": 1488,
             "f3": 1.21, "f4": 17.8, "f5": 12345, "f6": 123456789,
             "f9": 24.6, "f15": 1490, "f16": 1468, "f17": 1472,
             "f18": 1470.2, "f23": 8.1},
            {"f12": "000300", "f13": 1, "f14": "沪深300", "f2": 4000,
             "f3": 0.5, "f4": 20, "f5": 100, "f6": 200000,
             "f9": "-", "f15": 4010, "f16": 3980, "f17": 3990,
             "f18": 3980, "f23": "-"},
        ]}
    }
    finance_payload = {"result": {"data": [
        {"SECURITY_CODE": "600519", "REPORT_DATE": "2026-06-30", "WEIGHTAVG_ROE": 34.8}
    ]}}
    with patch("app.services.stocks.httpx.Client") as client_class:
        client = client_class.return_value.__enter__.return_value
        client.get.side_effect = [response(quote_payload), response(finance_payload)]
        result = get_stock_quotes()

    maotai = next(row for row in result["quotes"] if row["code"] == "600519")
    assert maotai["last_price"] == 1488.0
    assert maotai["change_pct"] == 1.21
    assert maotai["pe_dynamic"] == 24.6
    assert maotai["roe"] == 34.8
    assert maotai["roe_report_date"] == "2026-06-30"
    assert result["benchmark"]["code"] == "000300"
    assert result["fetched_at"].endswith("+08:00")
```

The history test must mock `data.klines` with the comma-separated sample in Step 3 and assert numeric values; validation tests clear `_CACHE` before invoking the service and assert invalid inputs do not call `httpx.Client`. Add a cache test patching `app.services.stocks.monotonic` with values `100.0`, `105.0`, and `111.0`, patch `_load_quotes` to return distinct snapshots, then call `get_stock_quotes()` three times: calls one and two return the same snapshot and invoke `_load_quotes` once; call three refreshes and invokes it twice. Clear `_CACHE` in `setUp` for every service test.

- [x] **Step 2: Run the service tests and confirm the missing-module failure**

Run: `& .\agent\Scripts\python.exe -m unittest tests.test_stocks_service -v`

Expected: FAIL because `app.services.stocks` does not exist.

- [x] **Step 3: Add failing daily-history and upstream-error tests**

Mock a K-line response whose `data.klines` contains `2026-09-22,100,102,103,99,1200,300000,4,2,2,1`; assert the parsed bar has numeric OHLC and volume/amount values. Assert an unsupported period raises `ValueError`, an unsupported code raises `ValueError`, and `httpx.TimeoutException` becomes `StockDataError`.

- [x] **Step 4: Implement the Eastmoney service**

In `app/services/stocks.py`, define the fixed ten-stock metadata and code-to-market mapping, plus the CSI 300 index mapping. Use only these fixed endpoints:

```python
QUOTE_URL = "https://push2.eastmoney.com/api/qt/ulist.np/get"
HISTORY_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
FINANCE_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
```

Request quotes with `fltt=2`, `invt=2`, `secids`, and the fixed fields above; map `f2/f3/f4/f5/f6/f9/f15/f16/f17/f18/f23` to last price, change percent/amount, volume (hands), turnover amount (yuan), dynamic PE, high, low, open, previous close, and PB. Parse `data.diff`, join by `f12`, preserve configured stock order, and represent omitted securities as unavailable instead of inventing values.

Request daily history with `klt=101`, `fqt=1`, `lmt=130` for `6m` or `260` for `1y`, and parse each comma-separated record in `data.klines`. Reject unknown symbols and periods before making a request.

Request the latest ROE rows for the fixed stock set from `FINANCE_URL` using `reportName=RPT_F10_FINANCE_MAINFINADATA`, `columns=SECURITY_CODE,REPORT_DATE,WEIGHTAVG_ROE`, a fixed `SECURITY_CODE in (...)` filter, `pageNumber=1`, and `pageSize=100`; group by code and select the latest `REPORT_DATE`. A finance-endpoint error must leave quotes usable with ROE fields null.

Use `httpx.Client(timeout=8, follow_redirects=False, trust_env=False, http2=False)` and a fixed user agent. Convert invalid numeric values (`None`, empty, `"-"`, non-numeric strings, NaN, and infinity) to `None`. Use process-local cache entries keyed by quotes/history parameters/financials with TTLs 10/300/86400 seconds, respectively. Store the local `Asia/Shanghai` retrieval timestamp with each cached value. Translate `httpx.HTTPError`, `OSError`, invalid JSON, and malformed top-level payloads to `StockDataError` without exposing raw upstream bodies. Ignore malformed non-string individual K-line records instead of raising an unhandled exception.

Use the following service implementation contract verbatim for names and parsing behavior; the ticker metadata table contains only the existing ten watchlist names/sectors and the benchmark:

```python
from datetime import datetime
from math import isfinite
from time import monotonic
from zoneinfo import ZoneInfo

import httpx

QUOTE_URL = "https://push2.eastmoney.com/api/qt/ulist.np/get"
HISTORY_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
FINANCE_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
QUOTE_FIELDS = "f12,f13,f14,f2,f3,f4,f5,f6,f9,f15,f16,f17,f18,f23"
HEADERS = {"User-Agent": "my-agent/2.0", "Referer": "https://quote.eastmoney.com/"}
STOCKS = (
    ("600519", "贵州茅台", "消费"), ("601318", "中国平安", "金融"),
    ("300750", "宁德时代", "新能源"), ("000858", "五粮液", "消费"),
    ("600900", "长江电力", "公用事业"), ("002594", "比亚迪", "汽车"),
    ("600276", "恒瑞医药", "医药"), ("601899", "紫金矿业", "资源"),
    ("000333", "美的集团", "家电"), ("600031", "三一重工", "工程机械"),
)
STOCK_CODES = tuple(item[0] for item in STOCKS)
BENCHMARK_CODE = "000300"
_CACHE = {}


class StockDataError(RuntimeError):
    pass


def _number(value):
    if value is None or value == "" or value == "-":
        return None
    try:
        number = float(str(value).replace(",", ""))
        return number if isfinite(number) else None
    except (TypeError, ValueError):
        return None


def _secid(code):
    if code == BENCHMARK_CODE or code.startswith(("5", "6", "9")):
        return f"1.{code}"
    return f"0.{code}"


def _get_json(url, params):
    try:
        with httpx.Client(timeout=8, follow_redirects=False, trust_env=False, http2=False) as client:
            response = client.get(url, params=params, headers=HEADERS)
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, OSError, ValueError) as exc:
        raise StockDataError("行情源请求失败") from exc
    if not isinstance(payload, dict):
        raise StockDataError("行情源响应格式无效")
    return payload


def _cached(key, ttl, loader):
    now = monotonic()
    entry = _CACHE.get(key)
    if entry and entry[0] > now:
        return entry[1]
    value = loader()
    _CACHE[key] = (now + ttl, value)
    return value


def _financials():
    codes = ",".join(f'"{code}"' for code in STOCK_CODES)
    payload = _get_json(FINANCE_URL, {
        "reportName": "RPT_F10_FINANCE_MAINFINADATA",
        "columns": "SECURITY_CODE,REPORT_DATE,WEIGHTAVG_ROE",
        "filter": f"(SECURITY_CODE in ({codes}))",
        "pageNumber": 1, "pageSize": 100, "sortColumns": "REPORT_DATE",
        "sortTypes": -1, "source": "HSF10", "client": "PC",
    })
    result = payload.get("result")
    if not isinstance(result, dict):
        raise StockDataError("财报响应格式无效")
    rows = result.get("data", [])
    if not isinstance(rows, list):
        raise StockDataError("财报响应格式无效")
    result = {}
    for row in rows:
        code = str(row.get("SECURITY_CODE", ""))
        report_date = str(row.get("REPORT_DATE", ""))[:10]
        if code not in STOCK_CODES or not report_date:
            continue
        if code not in result or report_date > result[code]["roe_report_date"]:
            result[code] = {"roe": _number(row.get("WEIGHTAVG_ROE")), "roe_report_date": report_date}
    return result


def _normalize_quote(code, name, sector, row, financials):
    record = row or {}
    finance = financials.get(code, {})
    return {
        "code": code, "name": name, "sector": sector, "available": bool(row),
        "last_price": _number(record.get("f2")), "change_pct": _number(record.get("f3")),
        "change_amount": _number(record.get("f4")), "volume_hands": _number(record.get("f5")),
        "amount_yuan": _number(record.get("f6")), "pe_dynamic": _number(record.get("f9")),
        "high": _number(record.get("f15")), "low": _number(record.get("f16")),
        "open": _number(record.get("f17")), "previous_close": _number(record.get("f18")),
        "pb": _number(record.get("f23")), "roe": finance.get("roe"),
        "roe_report_date": finance.get("roe_report_date"),
    }


def _load_quotes():
    codes = STOCK_CODES + (BENCHMARK_CODE,)
    payload = _get_json(QUOTE_URL, {
        "fltt": 2, "invt": 2, "secids": ",".join(_secid(code) for code in codes),
        "fields": QUOTE_FIELDS,
    })
    data = payload.get("data")
    if not isinstance(data, dict):
        raise StockDataError("行情响应格式无效")
    diff = data.get("diff")
    if isinstance(diff, dict):
        diff = list(diff.values())
    if not isinstance(diff, list) or not diff:
        raise StockDataError("行情源未返回报价")
    by_code = {str(row.get("f12", "")): row for row in diff if isinstance(row, dict)}
    try:
        financials = _cached("financials", 86400, _financials)
    except StockDataError:
        financials = {}
    quotes = [
        _normalize_quote(code, name, sector, by_code.get(code), financials)
        for code, name, sector in STOCKS
    ]
    benchmark_row = by_code.get(BENCHMARK_CODE)
    benchmark = _normalize_quote(BENCHMARK_CODE, "沪深300", "指数", benchmark_row, {})
    return {
        "source": "东方财富公开行情",
        "fetched_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "quotes": quotes, "benchmark": benchmark,
    }


def get_stock_quotes():
    return _cached("quotes", 10, _load_quotes)


def get_stock_history(code, period):
    if code not in STOCK_CODES:
        raise ValueError("不支持的股票代码")
    limits = {"6m": 130, "1y": 260}
    if period not in limits:
        raise ValueError("周期仅支持 6m 或 1y")

    def load():
        payload = _get_json(HISTORY_URL, {
            "secid": _secid(code), "klt": 101, "fqt": 1, "lmt": limits[period],
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        })
        data = payload.get("data")
        if not isinstance(data, dict):
            raise StockDataError("日线响应格式无效")
        records = data.get("klines", [])
        if not isinstance(records, list):
            raise StockDataError("日线响应格式无效")
        bars = []
        for record in records:
            if not isinstance(record, str):
                continue
            fields = record.split(",")
            if len(fields) < 7:
                continue
            bars.append({
                "date": fields[0], "open": _number(fields[1]), "close": _number(fields[2]),
                "high": _number(fields[3]), "low": _number(fields[4]),
                "volume": _number(fields[5]), "amount": _number(fields[6]),
            })
        if not bars:
            raise StockDataError("行情源未返回日线")
        return {
            "code": code, "period": period,
            "fetched_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
            "bars": bars,
        }

    return _cached(f"history:{code}:{period}", 300, load)
```

- [x] **Step 5: Run service tests and confirm they pass**

Run: `& .\agent\Scripts\python.exe -m unittest tests.test_stocks_service -v`

Expected: all quote normalization, missing-field, history parsing, validation, and upstream-error tests pass without network access.

---

### Task 2: Whitelisted FastAPI routes

**Files:**
- Create: `app/api/stocks.py`
- Create: `tests/test_stocks_api.py`
- Modify: `app/main.py`
- Modify: `app/api/router.py`

**Interfaces:**
- `GET /api/stocks/quotes` calls `get_stock_quotes()`.
- `GET /api/stocks/{code}/history?period=6m|1y` calls `get_stock_history(code, period)`.
- Invalid code/period returns HTTP 400; upstream failure returns HTTP 502.

- [x] **Step 1: Add failing ASGI endpoint tests**

Create `tests/test_stocks_api.py` using `httpx.ASGITransport(app=create_app())` and `httpx.AsyncClient`. Patch `app.api.stocks.get_stock_quotes` and `app.api.stocks.get_stock_history`; assert successful JSON passthrough, HTTP 400 for an unknown code and unsupported period, and HTTP 502 for `StockDataError`.

- [x] **Step 2: Run API tests and confirm route failures**

Run: `& .\agent\Scripts\python.exe -m unittest tests.test_stocks_api -v`

Expected: FAIL because the stocks router and routes are not registered.

- [x] **Step 3: Implement the router and register it**

Create `app/api/stocks.py` with `APIRouter(prefix="/api/stocks", tags=["stocks"])`. The route handlers call the service functions, map `ValueError` to `HTTPException(400, detail=str(exc))`, and map `StockDataError` to `HTTPException(502, detail="Stock data unavailable")` without echoing upstream content.

Import `stocks` in `app/main.py` and include `stocks` in the concrete module tuple. Also add `stocks.router` to `app/api/router.py` to keep the aggregate router consistent.

Use the complete route implementation below:

```python
from fastapi import APIRouter, HTTPException

from app.services.stocks import StockDataError, get_stock_history, get_stock_quotes

router = APIRouter(prefix="/api/stocks", tags=["stocks"])


@router.get("/quotes")
def quotes():
    try:
        return get_stock_quotes()
    except StockDataError as exc:
        raise HTTPException(status_code=502, detail="Stock data unavailable") from exc


@router.get("/{code}/history")
def history(code: str, period: str = "6m"):
    try:
        return get_stock_history(code, period)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except StockDataError as exc:
        raise HTTPException(status_code=502, detail="Stock data unavailable") from exc
```

- [x] **Step 4: Run API tests and confirm they pass**

Run: `& .\agent\Scripts\python.exe -m unittest tests.test_stocks_api -v`

Expected: quote/history responses pass through; invalid inputs return 400; provider failures return 502.

---

### Task 3: Live-data page, regression checks, and project context

**Files:**
- Modify: `frontend/stock.html`
- Create: `frontend/stock.js`
- Create: `tests/test_stock_page.py`
- Modify: `app/main.py`
- Modify: `PROJECT_CONTEXT.md`

**Interfaces:**
- Fetch quote snapshots from `/api/stocks/quotes`.
- Fetch selected history from `/api/stocks/{code}/history?period=6m|1y`.
- Preserve the most recent successful snapshot only in the current page session and mark it stale after a failed refresh.

**Visual direction:** Preserve the existing ink-dark research-board identity (`#0b0f14` canvas, `#111820` surfaces, slate dividers, warm amber for selection/data freshness, green gains, coral losses). Use a restrained system sans for labels and tabular/monospaced numerals for quotes. The single signature is a compact market-status tape in the hero that binds source, fetch time, and stale state into one clear instrument-like readout. Avoid flashing animation; retain responsive layout, keyboard focus, and reduced-motion behavior.

- [x] **Step 1: Add failing static-page regression checks**

Create tests that read `frontend/stock.html`, `frontend/stock.js`, and `app/main.py`; assert the HTML loads `/stock.js`, the JavaScript calls both stock API paths, contains a 15-second refresh interval and `document.visibilityState` guard, uses `document.createElement` and `.textContent` for provider text, and does not render provider text through `innerHTML`. Assert the page source does not contain old fixed prices (`1488`, `47.62`), synthetic `trend:[...]` arrays, static score fields, hard-coded `+0.86%`, or the old fixed timestamp `2026-07-22 15:00`. Also assert the HTML reports `抓取时间` and has an explicit latest-previous-quote note for outside trading hours. Add an ASGI static-file test that requests `/stock.js` and confirms the no-cache headers: `Cache-Control` includes `no-store`, `Pragma` is `no-cache`, and `Expires` is `0`.

- [x] **Step 2: Run page regression tests and confirm they fail**

Run: `& .\agent\Scripts\python.exe -m unittest tests.test_stock_page -v`

Expected: FAIL against the current hard-coded stock page.

- [x] **Step 3: Replace mock page data with API rendering**

Move page behavior into `frontend/stock.js`, load it from `frontend/stock.html`, and render the ten configured quotes, calculate equal-weight portfolio change and strongest stock from returned `change_pct`, and show the CSI 300 change. Display available price/change/OHLC/volume/amount/dynamic-PE/PB fields; display ROE with `roe_report_date`, or `暂无`. Show `fetched_at` as “抓取时间”, never “实时更新时间”. Include a fixed note that outside trading hours the provider value may be the latest previous quote. In `app/main.py`, also apply `Cache-Control: no-store, no-cache, must-revalidate, max-age=0`, `Pragma: no-cache`, and `Expires: 0` to JavaScript static paths so the separated page script cannot remain stale after a page reload.

Replace the chart's generated arrays with returned daily bars and their dates. Remove static composite/6-dimension scores, insight/recommendation copy, fake portfolio return, and fake benchmark line. Keep the manual refresh button. Run polling every 15 seconds only when `document.visibilityState === "visible"`; reload immediately on `visibilitychange` when visible. On refresh failure, keep the previous successful snapshot and visibly label it “数据已过期”; on first-load failure, render a clear unavailable state. Use `textContent` for provider-controlled labels and values.

- [x] **Step 4: Run page regression tests and confirm they pass**

Run: `& .\agent\Scripts\python.exe -m unittest tests.test_stock_page -v`

Expected: all API-path, polling, safe-rendering, data-label, removed-sample, and JavaScript no-cache assertions pass.

- [x] **Step 5: Update `PROJECT_CONTEXT.md`**

Document `app/api/stocks.py`, `app/services/stocks.py`, the two stock endpoints, Eastmoney public-source caveats, refresh/cache intervals, and the distinction between current quotes and dated ROE. Update the stock page description without changing unrelated sections.

- [x] **Step 6: Run the full verification suite**

Run: `& .\agent\Scripts\python.exe -m unittest discover -s tests -v`

Expected: all existing and new tests pass. Then run `& .\agent\Scripts\python.exe -m compileall -q app`; expected exit code is 0. If network is available, make one read-only request to the service through the local app and confirm a provider response; otherwise report live-provider integration as unverified and retain the mocked verification results.

## Concrete Code Contracts

The following snippets are the exact names, mappings, and client-side update contract for the steps above. Keep the existing HTML/CSS layout, but replace its inline script and sample-specific labels with the following element IDs and external script reference: `portfolio-change`, `benchmark-change`, `strongest`, `updated`, `refresh`, `sort`, `stock-rows`, `detail`, `chart`, `chart-title`, and `periods`; load `<script src="/stock.js" defer></script>`.

The service quote record returned to the UI has this shape:

```python
{
    "code": "600519", "name": "贵州茅台", "sector": "消费", "available": True,
    "last_price": 1488.0, "change_pct": 1.21, "change_amount": 17.8,
    "previous_close": 1470.2, "open": 1472.0, "high": 1490.0, "low": 1468.0,
    "volume_hands": 12345.0, "amount_yuan": 123456789.0,
    "pe_dynamic": 24.6, "pb": 8.1, "roe": 34.8, "roe_report_date": "2026-06-30"
}
```

`last_price`, all quote fields, and ROE may be `None`; unavailable securities have `available=False` and all quote fields `None`. Top-level quote response is `{"source":"东方财富公开行情","fetched_at":"<ISO-8601 +08:00>","quotes":[...],"benchmark":{...}}`. History response is `{"code":"600519","period":"6m","fetched_at":"<ISO-8601 +08:00>","bars":[{"date":"2026-09-22","open":100.0,"close":102.0,"high":103.0,"low":99.0,"volume":1200.0,"amount":300000.0}]}`.

For `frontend/stock.js`, implement these exact client requests and refresh conditions; render provider text through `textContent`, not interpolated HTML:

```javascript
const QUOTES_URL = "/api/stocks/quotes";
const HISTORY_URL = (code, period) =>
  `/api/stocks/${encodeURIComponent(code)}/history?period=${encodeURIComponent(period)}`;
const REFRESH_MS = 15000;
let snapshot = null;
let selectedCode = null;
let period = "6m";
let historyRequest = 0;

async function requestJson(url) {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

async function refreshQuotes() {
  const previousCode = selectedCode;
  try {
    const nextSnapshot = await requestJson(QUOTES_URL);
    if (!nextSnapshot || !Array.isArray(nextSnapshot.quotes)) throw new Error("Invalid quote payload");
    snapshot = nextSnapshot;
    if (!selectedCode || !snapshot.quotes.some(q => q.code === selectedCode)) {
      selectedCode = snapshot.quotes.find(q => q.available)?.code ?? null;
    }
    renderSnapshot();
    if (selectedCode && selectedCode !== previousCode) await refreshHistory();
  } catch {
    const status = document.getElementById("updated");
    status.textContent = snapshot
      ? `数据已过期 · 最近抓取于 ${snapshot.fetched_at}`
      : "行情暂不可用，请稍后重试";
  }
}

async function refreshHistory() {
  const requestId = ++historyRequest;
  if (!selectedCode) return;
  try {
    const result = await requestJson(HISTORY_URL(selectedCode, period));
    if (requestId === historyRequest && result.code === selectedCode) renderHistory(result.bars);
  } catch {
    document.getElementById("chart").textContent = "历史走势暂不可用";
  }
}

document.getElementById("refresh").addEventListener("click", refreshQuotes);
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible") refreshQuotes();
});
window.setInterval(() => {
  if (document.visibilityState === "visible") refreshQuotes();
}, REFRESH_MS);
refreshQuotes();
```

`renderSnapshot()` builds quote rows and detail elements with `document.createElement` and assigns all source-controlled content via `textContent`; it computes mean `change_pct` from quotes where both `available` is true and `change_pct` is numeric, uses benchmark `change_pct`, and picks the available quote with the greatest numeric `change_pct`. It displays `pe_dynamic` as “动态 PE”. Keep sorting but change choices to “涨跌幅” and “名称”; sort by numeric `change_pct` or localized name and never by a removed score. Clicking a row sets `selectedCode` and calls `refreshHistory()`. `renderHistory(bars)` plots `close` values in source order as “前复权收盘价”, labels the first/last date using SVG nodes and `textContent` (never interpolate provider dates into `innerHTML`), and renders no synthetic benchmark. Period buttons set `period` to exactly `6m` or `1y` and call `refreshHistory()`. Quote polling must not fetch history again unless the selected code changes.

The API module contract is:

```python
from fastapi import APIRouter, HTTPException

from app.services.stocks import StockDataError, get_stock_history, get_stock_quotes

router = APIRouter(prefix="/api/stocks", tags=["stocks"])


@router.get("/quotes")
def quotes():
    try:
        return get_stock_quotes()
    except StockDataError as exc:
        raise HTTPException(status_code=502, detail="Stock data unavailable") from exc


@router.get("/{code}/history")
def history(code: str, period: str = "6m"):
    try:
        return get_stock_history(code, period)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except StockDataError as exc:
        raise HTTPException(status_code=502, detail="Stock data unavailable") from exc
```

The API tests must construct the app through `create_app()` and patch the imported service symbols in `app.api.stocks`, not call the provider. Assert `/api/stocks/quotes` returns HTTP 200 and the exact patched JSON; `/api/stocks/999999/history?period=6m` returns 400; `/api/stocks/600519/history?period=1d` returns 400; and a patched `get_stock_quotes` raising `StockDataError` returns 502 with exactly `{"detail":"Stock data unavailable"}`. Patch with `unittest.mock.patch` in each async test and close the `AsyncClient` before the test completes so no live provider request occurs.

The stock-page regression test file must contain at least these checks:

```python
import unittest
from pathlib import Path


class StockPageTests(unittest.TestCase):
    def test_live_endpoints_and_refresh_guards_exist(self):
        root = Path(__file__).parents[1]
        html = (root / "frontend" / "stock.html").read_text(encoding="utf-8")
        script = (root / "frontend" / "stock.js").read_text(encoding="utf-8")
        self.assertIn('src="/stock.js"', html)
        self.assertIn('/api/stocks/quotes', script)
        self.assertIn('/history?period=', script)
        self.assertIn('REFRESH_MS = 15000', script)
        self.assertIn('document.visibilityState', script)
        self.assertIn('数据已过期', script)
        self.assertIn('行情暂不可用，请稍后重试', script)
        self.assertIn('历史走势暂不可用', script)
        self.assertNotIn('localStorage', script)

    def test_sample_market_values_and_scores_are_removed(self):
        root = Path(__file__).parents[1]
        source = (root / "frontend" / "stock.html").read_text(encoding="utf-8")
        source += (root / "frontend" / "stock.js").read_text(encoding="utf-8")
        for sample in ('1488', '47.62', 'trend:[', 'score:88', '+0.86%', '2026-07-22 15:00'):
            self.assertNotIn(sample, source)


if __name__ == "__main__":
    unittest.main()
```
