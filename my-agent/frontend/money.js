const $ = id => document.getElementById(id);
const money = value => `¥${Number(value || 0).toFixed(2).replace(/\.00$/, "")}`;
const esc = value => String(value == null ? "" : value).replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[char]));
const statusLabels = {draft:"草稿", ready:"待交付", delivered:"已交付", settled:"已结清", archived:"已归档"};
const paymentLabels = {unpaid:"未付款", pending:"待确认", paid:"已付款"};
let tasks = [];

function setMessage(id, value, isError = false) {
  const element = $(id);
  element.textContent = value;
  element.className = isError ? "error" : "success";
}

async function request(url, options = {}) {
  const response = await fetch(url, {headers:{"Content-Type":"application/json"}, ...options});
  if (!response.ok) {
    const detail = await response.text();
    throw Error(detail || `HTTP ${response.status}`);
  }
  return response.json();
}

function renderIdeas(ideas) {
  $("idea-count").textContent = `${ideas.length} 条`;
  $("idea-list").innerHTML = ideas.length ? ideas.slice().reverse().map(idea => `
    <article class="item">
      <div class="item-head"><div class="item-title">${esc(idea.title)}</div><span class="tag">${esc(idea.status || "draft")}</span></div>
      <div class="item-meta"><span>目标：${esc(idea.target_user || "未填写")}</span><span>售价：${money(idea.suggested_price)}</span><span>成本：${money(idea.estimated_cost)}</span></div>
      ${idea.description ? `<div class="item-body">${esc(idea.description)}</div>` : ""}
      ${idea.deliverable ? `<small class="item-body">交付：${esc(idea.deliverable)}</small>` : ""}
      ${idea.risk ? `<small class="item-body">风险：${esc(idea.risk)}</small>` : ""}
    </article>`).join("") : '<div class="empty">暂无想法</div>';
}

function renderSummary(summary) {
  $("total-tasks").textContent = summary.total_tasks;
  $("settled-tasks").textContent = summary.settled_tasks;
  $("gross-revenue").textContent = money(summary.gross_revenue);
  $("total-costs").textContent = money(summary.total_costs);
  $("net-revenue").textContent = money(summary.net_revenue);
}

function renderEstimate(estimate) {
  const totalCount = estimate.total_count ?? (estimate.priced_count + estimate.missing_price_count);
  $("estimate-report").innerHTML = `
    <div class="panel-head"><h2>估价结果</h2><span class="tag">${estimate.sample_count} 个有效样本</span></div>
    <div class="report-grid">
      <div class="report-value"><label>快速成交价</label><strong class="blue">${money(estimate.quick_sale_price)}</strong></div>
      <div class="report-value"><label>建议售价</label><strong class="amber">${money(estimate.recommended_price)}</strong></div>
      <div class="report-value"><label>偏高参考价</label><strong>${money(estimate.high_price)}</strong></div>
      <div class="report-value"><label>有效区间</label><strong>${money(estimate.min_price)} - ${money(estimate.max_price)}</strong></div>
      <div class="report-value"><label>缺失价格</label><strong>${estimate.missing_price_count}</strong></div>
      <div class="report-value"><label>异常剔除</label><strong>${estimate.outlier_count}</strong></div>
    </div>
    <p class="report-note">${esc(estimate.disclaimer)}</p>
    <p class="report-note">\u8bfb\u53d6\u4e86 ${totalCount} \u4e2a\u516c\u5f00\u6837\u672c\uff1a${estimate.priced_count} \u4e2a\u8bc6\u522b\u5230\u4ef7\u683c\uff0c${estimate.missing_price_count} \u4e2a\u672a\u8bc6\u522b\u5230\u4ef7\u683c\u3002</p>`;
  $("estimate-report").classList.add("visible");
}

function taskActions(task) {
  const actions = [];
  if (task.status === "draft") actions.push(`<button class="btn secondary" data-action="ready" data-id="${task.id}">标记待交付</button>`);
  if (task.status === "ready") actions.push(`<button class="btn secondary" data-action="delivered" data-id="${task.id}">标记已交付</button>`);
  if (task.payment_status !== "paid") actions.push(`<button class="btn secondary" data-action="paid" data-id="${task.id}">标记已付款</button>`);
  if (task.status === "delivered" && task.payment_status === "paid") actions.push(`<button class="btn primary" data-action="settled" data-id="${task.id}">结清任务</button>`);
  return actions.join("");
}

function renderTasks() {
  $("task-list").innerHTML = tasks.length ? tasks.slice().reverse().map(task => `
    <article class="item">
      <div class="item-head"><div class="item-title">${esc(task.title)}</div><span class="tag ${task.status === "settled" ? "green" : ""}">${esc(statusLabels[task.status] || task.status)}</span></div>
      <div class="item-meta"><span>付款：${esc(paymentLabels[task.payment_status] || task.payment_status)}</span><span>成交：${money(task.amount)}</span><span>成本：${money(task.costs)}</span><span>净额：${money(Number(task.amount) - Number(task.costs))}</span></div>
      ${task.customer_need ? `<div class="item-body">需求：${esc(task.customer_need)}</div>` : ""}
      ${task.deliverable ? `<div class="item-body">交付：${esc(task.deliverable)}</div>` : ""}
      ${task.artifact_path ? `<div class="item-body">文件：${esc(task.artifact_path)}</div>` : ""}
      <div class="item-actions">${taskActions(task) || '<span class="muted">暂无可执行状态</span>'}</div>
    </article>`).join("") : '<div class="empty">暂无任务</div>';
}

async function loadIdeas() {
  renderIdeas(await request("/api/money/ideas"));
}

async function loadLegacyState() {
  const state = await request("/api/money/state");
  $("legacy-mission").textContent = state.mission || "暂无";
  $("legacy-status").textContent = state.status || "暂无";
  $("legacy-balance").textContent = money(state.balance);
}

async function loadXianyu() {
  const [summary, list] = await Promise.all([request("/api/xianyu/summary"), request("/api/xianyu/tasks")]);
  tasks = list;
  renderSummary(summary);
  renderTasks();
}

async function updateTask(id, action) {
  const changes = action === "paid" ? {payment_status:"paid"} : {status:action};
  if (action === "settled") changes.payment_status = "paid";
  await request(`/api/xianyu/tasks/${encodeURIComponent(id)}`, {method:"PATCH", body:JSON.stringify(changes)});
  await loadXianyu();
}

document.querySelectorAll(".tab").forEach(button => button.addEventListener("click", async () => {
  document.querySelectorAll(".tab").forEach(item => item.classList.toggle("active", item === button));
  document.querySelectorAll(".view").forEach(view => view.classList.toggle("active", view.id === button.dataset.view));
  if (button.dataset.view === "xianyu-view") await loadXianyu();
}));

$("idea-form").addEventListener("submit", async event => {
  event.preventDefault();
  setMessage("idea-message", "");
  try {
    await request("/api/money/ideas", {method:"POST", body:JSON.stringify({
      title:$("idea-title").value.trim(), description:$("idea-description").value.trim(), target_user:$("idea-target").value.trim(),
      deliverable:$("idea-deliverable").value.trim(), suggested_price:Number($("idea-price").value || 0), estimated_cost:Number($("idea-cost").value || 0), risk:$("idea-risk").value.trim()
    })});
    event.target.reset(); $("idea-price").value = "0"; $("idea-cost").value = "0"; setMessage("idea-message", "已保存"); await loadIdeas();
  } catch (error) { setMessage("idea-message", `保存失败：${error.message}`, true); }
});

$("task-form").addEventListener("submit", async event => {
  event.preventDefault();
  setMessage("task-message", "");
  try {
    await request("/api/xianyu/tasks", {method:"POST", body:JSON.stringify({
      title:$("task-title").value.trim(), customer_need:$("task-need").value.trim(), deliverable:$("task-deliverable").value.trim(),
      amount:Number($("task-amount").value || 0), costs:Number($("task-costs").value || 0), notes:$("task-notes").value.trim()
    })});
    event.target.reset(); $("task-amount").value = "0"; $("task-costs").value = "0"; setMessage("task-message", "任务已创建"); await loadXianyu();
  } catch (error) { setMessage("task-message", `创建失败：${error.message}`, true); }
});

$("estimate-form").addEventListener("submit", async event => {
  event.preventDefault();
  const keyword = $("estimate-keyword").value.trim();
  setMessage("estimate-message", "搜索中...");
  $("estimate-report").classList.remove("visible");
  try {
    const result = await request("/api/smart/xianyu/estimate", {method:"POST", body:JSON.stringify({keyword})});
    renderEstimate(result.estimate);
    setMessage("estimate-message", `已读取 ${result.estimate.total_count ?? result.estimate.priced_count} 个样本，其中 ${result.estimate.priced_count} 个有价格`);
  } catch (error) {
    setMessage("estimate-message", `估价失败：${error.message}`, true);
  }
});

$("task-list").addEventListener("click", async event => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  button.disabled = true;
  try { await updateTask(button.dataset.id, button.dataset.action); }
  catch (error) { alert(`更新失败：${error.message}`); button.disabled = false; }
});

$("refresh-tasks").addEventListener("click", async () => {
  try { await loadXianyu(); }
  catch (error) { alert(`刷新失败：${error.message}`); }
});

(async function init() {
  try { await Promise.all([loadIdeas(), loadLegacyState(), loadXianyu()]); }
  catch (error) { setMessage("idea-message", `页面数据加载失败：${error.message}`, true); }
})();
