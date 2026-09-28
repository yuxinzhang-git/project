from pathlib import Path
import subprocess
import unittest

import httpx

from app.main import create_app


ROOT = Path(__file__).parents[1]


class StockPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "frontend" / "stock.html").read_text(encoding="utf-8")
        script_path = ROOT / "frontend" / "stock.js"
        cls.script = script_path.read_text(encoding="utf-8") if script_path.exists() else ""
        cls.main = (ROOT / "app" / "main.py").read_text(encoding="utf-8")

    def assertContains(self, expected, actual, description):
        self.assertTrue(expected in actual, description)

    def test_live_endpoints_and_refresh_guards_exist(self):
        self.assertContains('src="/stock.js"', self.html, "HTML should load /stock.js")
        self.assertContains(
            'const QUOTES_URL = "/api/stocks/quotes";',
            self.script,
            "quotes endpoint should be configured",
        )
        self.assertContains("/history?period=", self.script, "history endpoint should be used")
        self.assertContains("REFRESH_MS = 15000", self.script, "refresh interval should be 15 seconds")
        self.assertContains(
            'if (document.visibilityState === "visible")',
            self.script,
            "polling should check page visibility",
        )
        self.assertContains("数据已过期", self.script, "failed refresh should mark retained data stale")
        self.assertContains("行情暂不可用，请稍后重试", self.script, "first-load failure should be clear")
        self.assertContains("历史走势暂不可用", self.script, "history failure should be clear")
        self.assertNotIn("localStorage", self.script)

    def test_provider_values_are_rendered_as_text_nodes(self):
        self.assertContains("document.createElement", self.script, "rows/details should use DOM nodes")
        self.assertContains(".textContent", self.script, "provider values should use textContent")
        self.assertTrue("innerHTML" not in self.script, "provider content must not use innerHTML")

    def test_live_quote_fields_and_report_period_are_rendered(self):
        for field in (
            "last_price",
            "change_pct",
            "previous_close",
            "change_amount",
            "open",
            "high",
            "low",
            "volume_hands",
            "amount_yuan",
            "pe_dynamic",
            "pb",
            "roe",
            "roe_report_date",
        ):
            with self.subTest(field=field):
                self.assertContains(field, self.script, f"API field {field} should be displayed")

    def test_responsive_accessible_motion_and_old_advice_are_removed(self):
        self.assertContains("@media", self.html, "page should define responsive layouts")
        self.assertContains(":focus-visible", self.html, "keyboard focus should be visible")
        self.assertContains(
            "prefers-reduced-motion", self.html, "page should respect reduced-motion preferences"
        )
        self.assertContains(
            ".layout > section, .layout > aside",
            self.html,
            "layout grid items should shrink so the scrollable table does not widen the page",
        )
        for legacy_copy in ("综合评分", "建议观察仓位", "投资方式建议", "组合收益率"):
            with self.subTest(legacy_copy=legacy_copy):
                self.assertNotIn(legacy_copy, self.html)

    def test_page_uses_live_data_labels_and_out_of_hours_note(self):
        for element_id in (
            "portfolio-change",
            "benchmark-change",
            "strongest",
            "updated",
            "refresh",
            "sort",
            "stock-rows",
            "detail",
            "chart",
            "chart-title",
            "periods",
        ):
            self.assertContains(
                f'id="{element_id}"', self.html, f"required page element #{element_id} should exist"
            )
        self.assertContains("抓取时间", self.html, "page should label local fetch time")
        self.assertContains("非交易时间", self.html, "page should explain outside-hours data")
        self.assertTrue(
            "最近一个交易日" in self.html or "上一交易日" in self.html,
            "the page must explain that outside-hours values may be the latest previous quote",
        )
        self.assertContains("roe_report_date", self.script, "ROE should include its report date")
        self.assertContains("动态 PE", self.script, "page should label dynamic PE")
        self.assertContains("前复权收盘价", self.script, "history chart should label adjusted close")

    def test_sample_market_values_and_scores_are_removed(self):
        source = self.html + self.script
        for sample in (
            "1488",
            "47.62",
            "trend:[",
            "score:88",
            "+0.86%",
            "2026-07-22 15:00",
        ):
            with self.subTest(sample=sample):
                self.assertTrue(sample not in source, f"legacy sample value remains: {sample}")

    def test_static_middleware_includes_javascript_paths(self):
        self.assertContains('".js"', self.main, "static cache middleware should cover JavaScript")

    def test_overlapping_refresh_keeps_earlier_success_when_latest_request_fails(self):
        node = ROOT / ".tools" / "node" / "node.exe"
        self.assertTrue(node.exists(), "project Node runtime should be available for browser-script tests")
        harness = r"""
const fs = require("node:fs");
const vm = require("node:vm");
const assert = require("node:assert/strict");

class Element {
  constructor() {
    this.children = [];
    this.listeners = {};
    this.dataset = {};
    this.attributes = {};
    this.classList = {
      add() {},
      remove() {},
      toggle() {},
    };
    this.value = "change";
    this.textContent = "";
  }
  addEventListener(type, listener) { this.listeners[type] = listener; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = [...children]; }
  setAttribute(name, value) { this.attributes[name] = value; }
  contains() { return true; }
  querySelectorAll() { return []; }
}

const ids = [
  "refresh", "sort", "periods", "stock-rows", "portfolio-change",
  "benchmark-change", "strongest", "strongest-change", "updated",
  "source", "market-tape", "detail", "chart-title", "chart",
];
const elements = Object.fromEntries(ids.map((id) => [id, new Element()]));
const pending = [];
const document = {
  visibilityState: "visible",
  getElementById(id) { return elements[id] ?? (elements[id] = new Element()); },
  createElement() { return new Element(); },
  createElementNS() { return new Element(); },
  addEventListener() {},
};
const context = {
  document,
  window: { setInterval() {} },
  fetch() {
    return new Promise((resolve, reject) => pending.push({ resolve, reject }));
  },
  Intl,
  Number,
  String,
  Math,
  encodeURIComponent,
  setTimeout,
  clearTimeout,
};

(async () => {
vm.runInNewContext(fs.readFileSync(process.argv[1], "utf8"), context);
const latestRefresh = elements.refresh.listeners.click();
assert.equal(pending.length, 2, "initial load and manual refresh should overlap");

pending[1].reject(new Error("newest request failed"));
await Promise.resolve();
await Promise.resolve();

pending[0].resolve({
  ok: true,
  json: async () => ({
    source: "test source",
    fetched_at: "2026-09-23T12:00:00+08:00",
    quotes: [{
      code: "600519",
      name: "贵州茅台",
      sector: "消费",
      available: false,
      change_pct: null,
    }],
    benchmark: { available: false, change_pct: null },
  }),
});
await latestRefresh;
await new Promise((resolve) => setImmediate(resolve));
assert.equal(
  elements.updated.textContent,
  "2026-09-23T12:00:00+08:00",
  "a successful in-flight snapshot must be retained after a newer request fails",
);
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
"""
        result = subprocess.run(
            [str(node), "-e", harness, str(ROOT / "frontend" / "stock.js")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)


class StockPageStaticFileTests(unittest.IsolatedAsyncioTestCase):
    async def test_stock_script_is_served_with_no_cache_headers(self):
        app = create_app()
        transport = httpx.ASGITransport(app=app)

        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            response = await client.get("/stock.js")

        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response.headers.get("cache-control", ""))
        self.assertIn("no-cache", response.headers.get("cache-control", ""))
        self.assertEqual(response.headers.get("pragma"), "no-cache")
        self.assertEqual(response.headers.get("expires"), "0")


if __name__ == "__main__":
    unittest.main()
