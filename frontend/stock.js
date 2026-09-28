(() => {
  const QUOTES_URL = "/api/stocks/quotes";
  const HISTORY_URL = (code, period) =>
    `/api/stocks/${encodeURIComponent(code)}/history?period=${encodeURIComponent(period)}`;
  const REFRESH_MS = 15000;
  const SVG_NS = "http://www.w3.org/2000/svg";
  let snapshot = null;
  let selectedCode = null;
  let period = "6m";
  let historyRequest = 0;
  let quoteRequest = 0;
  let appliedQuoteRequest = 0;

  const byId = (id) => document.getElementById(id);
  const isNumber = (value) => typeof value === "number" && Number.isFinite(value);

  function formatNumber(value, digits = 2) {
    if (!isNumber(value)) return "暂无";
    return new Intl.NumberFormat("zh-CN", {
      maximumFractionDigits: digits,
      minimumFractionDigits: 0,
    }).format(value);
  }

  function formatChange(value) {
    if (!isNumber(value)) return "暂无";
    return `${value >= 0 ? "+" : ""}${formatNumber(value)}%`;
  }

  function setChange(element, value) {
    element.textContent = formatChange(value);
    element.classList.remove("up", "down");
    if (isNumber(value)) element.classList.add(value >= 0 ? "up" : "down");
  }

  function makeText(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    element.textContent = text == null ? "" : String(text);
    return element;
  }

  function appendField(container, label, value, subtext = "") {
    const field = document.createElement("div");
    field.className = "detail-field";
    field.append(makeText("span", "detail-label", label));
    field.append(makeText("span", "detail-value", value));
    if (subtext) field.append(makeText("span", "cell-sub", subtext));
    container.append(field);
  }

  function getSelectedQuote() {
    return snapshot?.quotes?.find((quote) => quote.code === selectedCode) ?? null;
  }

  function renderRows() {
    const body = byId("stock-rows");
    body.replaceChildren();
    const quotes = [...(snapshot?.quotes ?? [])];
    if (byId("sort").value === "name") {
      quotes.sort((left, right) => String(left.name ?? "").localeCompare(String(right.name ?? ""), "zh-CN"));
    } else {
      quotes.sort((left, right) => {
        const leftChange = isNumber(left.change_pct) && left.available ? left.change_pct : -Infinity;
        const rightChange = isNumber(right.change_pct) && right.available ? right.change_pct : -Infinity;
        return rightChange - leftChange;
      });
    }

    if (!quotes.length) {
      const row = document.createElement("tr");
      const cell = makeText("td", "empty-row", "暂无可显示的股票数据");
      cell.colSpan = 5;
      row.append(cell);
      body.append(row);
      return;
    }

    for (const quote of quotes) {
      const row = document.createElement("tr");
      row.tabIndex = 0;
      row.setAttribute("aria-selected", String(quote.code === selectedCode));
      row.addEventListener("click", () => selectStock(quote.code));
      row.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          selectStock(quote.code);
        }
      });

      const identity = document.createElement("td");
      identity.append(makeText("span", "name", quote.name));
      identity.append(makeText("span", "code", quote.code));
      row.append(identity);

      const price = document.createElement("td");
      price.textContent = quote.available ? formatNumber(quote.last_price) : "暂无";
      row.append(price);

      const change = document.createElement("td");
      if (quote.available) setChange(change, quote.change_pct);
      else change.textContent = "暂无";
      row.append(change);

      const pe = document.createElement("td");
      pe.textContent = quote.available && isNumber(quote.pe_dynamic)
        ? `${formatNumber(quote.pe_dynamic)}x`
        : "暂无";
      row.append(pe);

      const roe = document.createElement("td");
      roe.textContent = isNumber(quote.roe) ? `${formatNumber(quote.roe, 1)}%` : "暂无";
      if (quote.roe_report_date) {
        roe.append(makeText("span", "cell-sub", `报告期 ${quote.roe_report_date}`));
      }
      row.append(roe);
      body.append(row);
    }
  }

  function renderDetail() {
    const detail = byId("detail");
    detail.replaceChildren();
    const quote = getSelectedQuote();
    if (!quote) {
      detail.append(makeText("p", "detail-meta", "暂无可用报价"));
      return;
    }

    const header = document.createElement("div");
    header.className = "detail-head";
    const identity = document.createElement("div");
    identity.append(makeText("div", "detail-meta", `${quote.code} · ${quote.sector ?? "暂无"}`));
    identity.append(makeText("h3", "", quote.name));
    const price = document.createElement("div");
    price.className = "detail-price";
    price.append(makeText("strong", "", quote.available ? formatNumber(quote.last_price) : "暂无"));
    const change = document.createElement("span");
    if (quote.available) setChange(change, quote.change_pct);
    else change.textContent = "暂无";
    price.append(change);
    header.append(identity, price);
    detail.append(header);

    const fields = document.createElement("div");
    fields.className = "detail-grid";
    appendField(fields, "涨跌额", isNumber(quote.change_amount) ? formatNumber(quote.change_amount) : "暂无");
    appendField(fields, "昨收", formatNumber(quote.previous_close));
    appendField(fields, "今开", formatNumber(quote.open));
    appendField(fields, "最高", formatNumber(quote.high));
    appendField(fields, "最低", formatNumber(quote.low));
    appendField(fields, "成交量", isNumber(quote.volume_hands) ? `${formatNumber(quote.volume_hands, 0)} 手` : "暂无");
    appendField(fields, "成交额", isNumber(quote.amount_yuan) ? `${formatNumber(quote.amount_yuan, 0)} 元` : "暂无");
    appendField(fields, "动态 PE", isNumber(quote.pe_dynamic) ? `${formatNumber(quote.pe_dynamic)}x` : "暂无");
    appendField(fields, "PB", isNumber(quote.pb) ? `${formatNumber(quote.pb)}x` : "暂无");
    const roeDate = quote.roe_report_date ? `报告期 ${quote.roe_report_date}` : "";
    appendField(fields, "ROE · 报告期", isNumber(quote.roe) ? `${formatNumber(quote.roe, 1)}%` : "暂无", roeDate);
    detail.append(fields);
    detail.append(makeText("p", "detail-footnote", "未提供的字段显示为暂无，不以示例数据补齐。"));
  }

  function renderSnapshot() {
    renderRows();
    renderDetail();
    byId("source").textContent = snapshot.source || "暂无";
    byId("updated").textContent = snapshot.fetched_at;
    byId("market-tape").dataset.state = "fresh";

    const changes = snapshot.quotes
      .filter((quote) => quote.available && isNumber(quote.change_pct))
      .map((quote) => quote.change_pct);
    const portfolio = byId("portfolio-change");
    if (changes.length) {
      const average = changes.reduce((total, value) => total + value, 0) / changes.length;
      portfolio.textContent = formatChange(average);
      portfolio.classList.remove("up", "down");
      portfolio.classList.add(average >= 0 ? "up" : "down");
    } else {
      portfolio.textContent = "暂无";
      portfolio.classList.remove("up", "down");
    }

    const benchmark = snapshot.benchmark;
    setChange(byId("benchmark-change"), benchmark?.available ? benchmark.change_pct : null);

    const strongest = snapshot.quotes
      .filter((quote) => quote.available && isNumber(quote.change_pct))
      .reduce((best, quote) => !best || quote.change_pct > best.change_pct ? quote : best, null);
    byId("strongest").textContent = strongest ? strongest.name : "暂无";
    const strongestChange = byId("strongest-change");
    if (strongest) setChange(strongestChange, strongest.change_pct);
    else strongestChange.textContent = "按有效报价计算";

    const selected = getSelectedQuote();
    byId("chart-title").textContent = selected ? `${selected.name} · 前复权收盘价` : "历史走势";
  }

  function showChartMessage(message) {
    const chart = byId("chart");
    chart.replaceChildren(makeText("div", "chart-empty", message));
  }

  function svgElement(name, attributes = {}) {
    const element = document.createElementNS(SVG_NS, name);
    for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, String(value));
    return element;
  }

  function renderHistory(bars) {
    const usableBars = Array.isArray(bars)
      ? bars.filter((bar) => isNumber(bar.close))
      : [];
    if (!usableBars.length) {
      showChartMessage("暂无日线数据");
      return;
    }

    const width = 720;
    const height = 260;
    const pad = { left: 52, right: 14, top: 16, bottom: 34 };
    const closes = usableBars.map((bar) => bar.close);
    let min = Math.min(...closes);
    let max = Math.max(...closes);
    if (min === max) {
      min -= Math.max(Math.abs(min) * 0.02, 1);
      max += Math.max(Math.abs(max) * 0.02, 1);
    }
    const plotWidth = width - pad.left - pad.right;
    const plotHeight = height - pad.top - pad.bottom;
    const x = (index) => usableBars.length === 1
      ? pad.left + plotWidth / 2
      : pad.left + (index * plotWidth) / (usableBars.length - 1);
    const y = (value) => pad.top + ((max - value) * plotHeight) / (max - min);
    const svg = svgElement("svg", {
      viewBox: `0 0 ${width} ${height}`,
      role: "img",
      "aria-label": "前复权收盘价日线走势",
      preserveAspectRatio: "none",
    });

    for (let index = 0; index < 4; index += 1) {
      const lineY = pad.top + (plotHeight * index) / 3;
      svg.append(svgElement("line", {
        class: "gridline",
        x1: pad.left,
        x2: width - pad.right,
        y1: lineY,
        y2: lineY,
      }));
      const value = max - ((max - min) * index) / 3;
      const axisLabel = svgElement("text", {
        class: "axis-label",
        x: pad.left - 8,
        y: lineY + 3,
        "text-anchor": "end",
      });
      axisLabel.textContent = formatNumber(value);
      svg.append(axisLabel);
    }

    const points = closes.map((value, index) => `${x(index).toFixed(2)},${y(value).toFixed(2)}`).join(" ");
    svg.append(svgElement("polyline", { class: "chart-line", points }));
    svg.append(svgElement("circle", {
      class: "chart-dot",
      cx: x(closes.length - 1),
      cy: y(closes[closes.length - 1]),
      r: 4,
    }));

    const firstDate = svgElement("text", {
      class: "axis-label",
      x: pad.left,
      y: height - 8,
      "text-anchor": "start",
    });
    firstDate.textContent = String(usableBars[0].date ?? "");
    const lastDate = svgElement("text", {
      class: "axis-label",
      x: width - pad.right,
      y: height - 8,
      "text-anchor": "end",
    });
    lastDate.textContent = String(usableBars[usableBars.length - 1].date ?? "");
    svg.append(firstDate, lastDate);

    const chart = byId("chart");
    chart.replaceChildren(svg);
  }

  function renderUnavailable() {
    const body = byId("stock-rows");
    body.replaceChildren();
    const row = document.createElement("tr");
    const cell = makeText("td", "empty-row", "行情暂不可用，请稍后重试");
    cell.colSpan = 5;
    row.append(cell);
    body.append(row);
    byId("portfolio-change").textContent = "暂无";
    byId("benchmark-change").textContent = "暂无";
    byId("strongest").textContent = "暂无";
    byId("strongest-change").textContent = "暂无";
    byId("detail").replaceChildren(makeText("p", "detail-meta", "行情暂不可用，请稍后重试"));
    byId("chart-title").textContent = "历史走势";
    showChartMessage("历史走势暂不可用");
  }

  async function requestJson(url) {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  async function refreshQuotes() {
    const requestId = ++quoteRequest;
    const previousCode = selectedCode;
    try {
      const nextSnapshot = await requestJson(QUOTES_URL);
      const validSnapshot =
        nextSnapshot &&
        typeof nextSnapshot.source === "string" &&
        typeof nextSnapshot.fetched_at === "string" &&
        Array.isArray(nextSnapshot.quotes) &&
        nextSnapshot.quotes.length > 0 &&
        nextSnapshot.quotes.every((quote) =>
          quote && typeof quote.code === "string" && typeof quote.name === "string"
        );
      if (!validSnapshot) throw new Error("Invalid quote payload");
      if (requestId < appliedQuoteRequest) return;

      appliedQuoteRequest = requestId;
      snapshot = nextSnapshot;
      if (!selectedCode || !snapshot.quotes.some((quote) => quote.code === selectedCode)) {
        selectedCode = snapshot.quotes.find((quote) => quote.available)?.code ?? null;
      }
      renderSnapshot();
      if (selectedCode && selectedCode !== previousCode) await refreshHistory();
      else if (!selectedCode) showChartMessage("暂无可用股票的历史走势");
    } catch {
      if (requestId < appliedQuoteRequest) return;
      byId("market-tape").dataset.state = snapshot ? "stale" : "error";
      byId("updated").textContent = snapshot
        ? `数据已过期 · 最近抓取于 ${snapshot.fetched_at}`
        : "行情暂不可用，请稍后重试";
      if (!snapshot) renderUnavailable();
    }
  }

  async function refreshHistory() {
    const requestId = ++historyRequest;
    const requestedCode = selectedCode;
    if (!requestedCode) {
      showChartMessage("暂无可用股票的历史走势");
      return;
    }
    showChartMessage("正在获取日线…");
    try {
      const result = await requestJson(HISTORY_URL(requestedCode, period));
      if (requestId === historyRequest && result.code === selectedCode && Array.isArray(result.bars)) {
        renderHistory(result.bars);
      }
    } catch {
      if (requestId === historyRequest && requestedCode === selectedCode) {
        showChartMessage("历史走势暂不可用");
      }
    }
  }

  function selectStock(code) {
    if (code === selectedCode) return;
    selectedCode = code;
    renderRows();
    renderDetail();
    const quote = getSelectedQuote();
    byId("chart-title").textContent = quote ? `${quote.name} · 前复权收盘价` : "历史走势";
    refreshHistory();
  }

  byId("refresh").addEventListener("click", refreshQuotes);
  byId("sort").addEventListener("change", renderRows);
  byId("periods").addEventListener("click", (event) => {
    const button = event.target.closest("button[data-period]");
    if (!button || !byId("periods").contains(button)) return;
    const nextPeriod = button.dataset.period;
    if (nextPeriod !== "6m" && nextPeriod !== "1y") return;
    period = nextPeriod;
    for (const tab of byId("periods").querySelectorAll("button[data-period]")) {
      const active = tab === button;
      tab.classList.toggle("active", active);
      tab.setAttribute("aria-pressed", String(active));
    }
    refreshHistory();
  });
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") refreshQuotes();
  });
  window.setInterval(() => {
    if (document.visibilityState === "visible") refreshQuotes();
  }, REFRESH_MS);
  refreshQuotes();
})();
