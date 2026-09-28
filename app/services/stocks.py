from datetime import date, datetime, timedelta, timezone
from math import isfinite
from time import monotonic
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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


def _shanghai_now():
    try:
        zone = ZoneInfo("Asia/Shanghai")
    except ZoneInfoNotFoundError:
        zone = timezone(timedelta(hours=8), name="Asia/Shanghai")
    return datetime.now(zone)


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
        if not isinstance(row, dict):
            continue
        code = str(row.get("SECURITY_CODE", ""))
        raw_report_date = str(row.get("REPORT_DATE") or "")
        try:
            if len(raw_report_date) == 10:
                parsed_report_date = date.fromisoformat(raw_report_date)
                if parsed_report_date.isoformat() != raw_report_date:
                    continue
            else:
                parsed_report_date = datetime.fromisoformat(raw_report_date).date()
        except ValueError:
            continue
        if code not in STOCK_CODES:
            continue
        report_date = parsed_report_date.isoformat()
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
        "fetched_at": _shanghai_now().isoformat(),
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
            "fetched_at": _shanghai_now().isoformat(),
            "bars": bars,
        }

    return _cached(f"history:{code}:{period}", 300, load)
