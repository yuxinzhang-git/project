# 只读 HTTP 搜索工具实施计划

## 目标

为聊天 Agent 接入独立的只读互联网搜索工具，让它可以检索最新公开信息，同时不开放浏览器操作、登录态或任意 URL 访问。

## 实施范围

1. 先以标准库 `unittest` 编写固定端点、请求方法、参数限制、解析和输出安全边界测试。
2. 新增 `app/tools/web_search.py`，使用 `httpx` 访问固定 DuckDuckGo HTML 搜索端点并解析标题、摘要和来源 URL。
3. 导出并注册工具，更新 Agent system prompt，明确外部结果不可信且需附来源。
4. 更新 `PROJECT_CONTEXT.md`、`findings.md` 和 `progress.md`，记录工具边界与运行配置。
5. 运行单元测试、Python 编译检查、Agent 导入检查，并在网络允许时执行一次真实搜索验证。

## 验收标准

- 调用方无法指定任意 URL、HTTP 方法、Cookie 或重定向行为。
- 空查询、超长查询和超范围结果数不会发出网络请求。
- 搜索失败返回可读错误，不泄漏异常堆栈或响应原文。
- Agent 工具列表包含 `web_search`，原计算工具仍保持可用。

## 结果

- 已完成 `app/tools/web_search.py`、工具导出、Agent 注册和上下文文档更新。
- 已通过 7 项标准库单元测试、Python 编译检查和 Agent 导入检查。
- 已在 2026-09-22 成功执行一次真实 DuckDuckGo 搜索验证。
