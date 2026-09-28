# 金钱控制台方案生成布局 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将金钱控制台的“方案生成”页面改为上下布局，并把生成结果呈现为带有鲜明分组标题的宽版纵向方案卡片。

**Architecture:** 保留现有 FastAPI、静态 HTML/CSS/JavaScript 和收入方案 API。只在 `frontend/money.html` 调整方案页的容器布局与视觉样式，在 `frontend/money.js` 给结果分组增加语义 class；现有字段、转义、接口调用和保存想法事件保持不变。

**Tech Stack:** 静态 HTML、CSS Grid、原生 JavaScript、Python `unittest`。

## Global Constraints

- 仅调整 `frontend/money.html` 的方案生成页面布局与样式。
- 调整 `frontend/money.js` 中方案结果的语义标记与展示 class，保持现有数据字段、API 调用和“保存为想法”交互不变。
- 不修改收入方案 API、Pydantic 模型或持久化逻辑。
- 桌面端结果信息块使用三列，中等宽度可降为两列，窄屏降为单列。
- 长标题、列表和成本拆分必须自然换行，不产生横向溢出。
- 所有用户可见动态文本继续通过现有 `esc()` 处理。

---

### Task 1: Add layout regression tests

**Files:**
- Modify: `F:\zyx\agent\my-agent\tests\test_income_plan.py`

**Interfaces:**
- Consumes: `frontend/money.html` and `frontend/money.js` source text.
- Produces: source-level regression coverage for the new `plan-layout`, `plan-form-panel`, `plan-results-panel`, and `plan-block-title` markers.

- [ ] **Step 1: Write the failing tests**

Add two methods to `IncomePlanFrontendTests`:

```python
    def test_money_page_uses_vertical_income_plan_layout(self):
        page = Path(__file__).parents[1] / "frontend" / "money.html"
        source = page.read_text(encoding="utf-8")

        self.assertIn('class="plan-layout"', source)
        self.assertIn('class="plan-form-panel"', source)
        self.assertIn('class="plan-results-panel"', source)

    def test_money_js_marks_plan_result_sections_for_emphasis(self):
        script = Path(__file__).parents[1] / "frontend" / "money.js"
        source = script.read_text(encoding="utf-8")

        self.assertIn("plan-block-title", source)
        self.assertIn("plan-block-content", source)
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run:

```powershell
.\agent\Scripts\python.exe -m unittest tests.test_income_plan.IncomePlanFrontendTests -v
```

Expected: the existing income-plan tests pass, and the two new tests fail because the new layout and result-section markers do not exist yet.

- [ ] **Step 3: Do not change production code in this task**

Keep the failure meaningful. The next tasks add the minimum HTML/CSS and JavaScript needed to satisfy these assertions.

### Task 2: Change the income-plan page to a vertical layout

**Files:**
- Modify: `F:\zyx\agent\my-agent\frontend\money.html`

**Interfaces:**
- Consumes: the existing plan form and `#plan-results` container.
- Produces: a `.plan-layout` single-column wrapper, a `.plan-form-panel` top section, and a `.plan-results-panel` lower section.

- [ ] **Step 1: Replace the plan-view two-column wrapper**

Change only the `#plan-view` wrapper so it follows this structure:

```html
<section id="plan-view" class="view">
  <div class="plan-layout">
    <form class="panel plan-form-panel" id="plan-form">
      <!-- keep the existing form fields and submit controls unchanged -->
    </form>
    <section class="panel plan-results-panel">
      <div class="panel-head">
        <div><div class="eyebrow">RESULTS</div><h2>生成结果</h2></div>
      </div>
      <div id="plan-results" class="list"><div class="empty">填写条件后生成方案</div></div>
    </section>
  </div>
</section>
```

Preserve every existing input `id`, `required` attribute, placeholder, submit button, `#plan-message`, and `#plan-results` id. The only copy adjustment is changing the empty-state text from “填写左侧条件后生成方案” to “填写条件后生成方案” because the form is no longer on the left.

- [ ] **Step 2: Add scoped layout and card presentation CSS**

Add these rules near the existing `.layout` and `.plan-card` rules:

```css
.plan-layout{display:grid;grid-template-columns:minmax(0,1fr);gap:18px}
.plan-form-panel,.plan-results-panel{min-width:0}
.plan-results-panel>.panel-head{margin-bottom:16px}
.plan-card{background:var(--panel-2);border:1px solid var(--line);border-radius:7px;padding:18px}
.plan-card+.plan-card{margin-top:14px}
.plan-card .item-head{padding-bottom:14px;border-bottom:1px solid var(--line)}
.plan-card .item-title{font-size:19px;line-height:1.35}
.plan-card .item-body{line-height:1.7}
.plan-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:16px}
.plan-block{min-width:0;border:1px solid #34413d;border-left:3px solid var(--amber);border-radius:5px;padding:0 12px 12px;background:#16201f}
.plan-block-title{display:block;margin:0 -12px 11px;padding:7px 12px;background:rgba(242,184,75,.12);color:#f7d48b;font-size:13px;font-weight:700;line-height:1.35}
.plan-block-content{min-width:0;color:#d4dfd7;line-height:1.65}
.plan-block-content ul{margin:0;padding-left:18px}
.plan-block-content li+li{margin-top:4px}
.plan-block--action{border-left-color:var(--green)}
.plan-block--action .plan-block-title{background:rgba(98,206,153,.12);color:#9be6bd}
.plan-block--cost{border-left-color:var(--blue)}
.plan-block--cost .plan-block-title{background:rgba(123,183,216,.12);color:#b9def1}
@media(max-width:1000px){.plan-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:620px){.plan-grid{grid-template-columns:1fr}.plan-card{padding:14px}.plan-card .item-title{font-size:18px}}
```

Do not remove the existing `.layout` rules because other tabs still use the two-column layout.

- [ ] **Step 3: Run the focused tests**

Run:

```powershell
.\agent\Scripts\python.exe -m unittest tests.test_income_plan.IncomePlanFrontendTests -v
```

Expected: the HTML layout test passes; the JavaScript marker test remains failing until Task 3.

### Task 3: Emphasize result section titles without changing behavior

**Files:**
- Modify: `F:\zyx\agent\my-agent\frontend\money.js`

**Interfaces:**
- Consumes: existing `listItems()` and `renderPlans(plans)`.
- Produces: result blocks with `.plan-block-title` and `.plan-block-content`, while retaining `data-save-plan` and existing plan data fields.

- [ ] **Step 1: Replace the result block markup in `renderPlans()`**

Keep `listItems()` unchanged, then update each result block from this form:

```javascript
<div class="plan-block"><label>目标客户</label>${listItems(plan.target_customers)}</div>
```

to this form:

```javascript
<div class="plan-block"><span class="plan-block-title">目标客户</span><div class="plan-block-content">${listItems(plan.target_customers)}</div></div>
```

Apply the same structure to these fields:

```javascript
<div class="plan-block"><span class="plan-block-title">产品/服务</span><div class="plan-block-content">${esc(plan.offer)}</div></div>
<div class="plan-block"><span class="plan-block-title">准备过程</span><div class="plan-block-content">${listItems(plan.preparation_steps)}</div></div>
<div class="plan-block"><span class="plan-block-title">7 天执行计划</span><div class="plan-block-content">${listItems(plan.seven_day_plan)}</div></div>
<div class="plan-block"><span class="plan-block-title">获客方式</span><div class="plan-block-content">${listItems(plan.customer_acquisition)}</div></div>
<div class="plan-block"><span class="plan-block-title">风险挑战</span><div class="plan-block-content">${listItems(plan.risks)}</div></div>
<div class="plan-block"><span class="plan-block-title">验证标准</span><div class="plan-block-content">${listItems(plan.validation_metrics)}</div></div>
<div class="plan-block plan-block--action"><span class="plan-block-title">第一步行动</span><div class="plan-block-content">${esc(plan.first_action)}</div></div>
<div class="plan-block plan-block--cost wide"><span class="plan-block-title">成本拆分</span><div class="plan-block-content">${esc(plan.cost_breakdown)}</div></div>
```

Keep the existing `esc()` calls, plan index, price/cost metadata, `data-save-plan="${index}"`, and save button text unchanged.

- [ ] **Step 2: Run the focused tests and verify they pass**

Run:

```powershell
.\agent\Scripts\python.exe -m unittest tests.test_income_plan.IncomePlanFrontendTests -v
```

Expected: all income-plan API and frontend tests pass.

### Task 4: Run regression and visual checks

**Files:**
- No additional source files.

**Interfaces:**
- Consumes: the completed HTML/CSS/JavaScript changes.
- Produces: verified page source and regression-test evidence.

- [ ] **Step 1: Run the complete unittest suite**

Run:

```powershell
.\agent\Scripts\python.exe -m unittest discover -s tests -v
```

Expected: exit code `0` with zero failures and zero errors.

- [ ] **Step 2: Compile the Python application**

Run:

```powershell
.\agent\Scripts\python.exe -m compileall -q app
```

Expected: exit code `0` and no diagnostic output.

- [ ] **Step 3: Inspect the final source for the required responsive rules**

Run:

```powershell
rg -n "plan-layout|plan-form-panel|plan-results-panel|plan-block-title|@media\(max-width:1000px\)|@media\(max-width:620px\)" frontend/money.html frontend/money.js
```

Expected: matches appear in the intended files, with `plan-layout` and panel classes in `money.html`, and result marker classes in both `money.html` CSS and `money.js` markup.

- [ ] **Step 4: Check the served static page when the local server is available**

Start the documented server:

```powershell
.\agent\Scripts\python.exe agent_api.py
```

Then request `http://127.0.0.1:8000/money.html` in a browser and inspect the `方案生成` tab at desktop width and a narrow mobile width. Confirm the form is above the results, every plan card spans the available content width, result titles are visibly boxed, and no text overlaps or clips. Stop the server after inspection.
