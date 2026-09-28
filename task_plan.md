# 项目架构、路径修复与上下文文档计划

## 目标

整理项目架构和功能上下文，修复迁移到当前目录后失效的路径配置和 Python 运行环境。

## 阶段

- [complete] 1. 建立项目清单并恢复/初始化分析记录
- [complete] 2. 读取文档、依赖、启动脚本和应用入口
- [complete] 3. 梳理后端、浏览器自动化、前端和数据流
- [complete] 4. 扫描绝对路径/盘符/工作目录假设并验证风险
- [complete] 5. 形成结论，记录入口、启动方式和适配建议
- [complete] 6. 新增项目上下文文档和 Python 依赖声明
- [complete] 7. 修复 MCP/文档旧路径并重建 Python 虚拟环境
- [complete] 8. 验证导入、编译、MCP CLI 和 HTTP 服务
- [complete] 9. 设计并实现独立只读 HTTP 搜索工具
- [complete] 10. 将搜索工具注册到聊天 Agent 并更新上下文文档
- [complete] 11. 运行单测、编译检查和真实网络可用性验证
- [complete] 12. 隐藏聊天 Agent 的工具执行过程
- [complete] 13. 验证 API 响应和前端不再展示工具调用
- [complete] 14. 修复聊天 Agent Markdown 渲染
- [complete] 15. 验证 Markdown 页面资源、单测和语法检查

## 错误与风险记录

| 现象 | 状态 |
|---|---|
| `git status` 报当前目录不是 Git 仓库，尽管存在 `.git` 目录 | 待核实 |
| 项目内 `agent\\Scripts\\python.exe` 启动失败：虚拟环境指向不存在的 `C:\\Program Files\\Python312\\python.exe` | 已确认，需重建虚拟环境 |
| `.codex/config.toml` 的 Playwright MCP 命令指向旧目录 `D:\\agent\\my-agent` | 已确认，需改为当前目录 |
| `README_PLAYWRIGHT_MCP.md` 启动示例指向旧目录 `F:\\my-agent` | 已确认，建议修正文档 |
| 系统 Python 可执行，但缺少 `python-dotenv` | 已确认，不能作为现成后端运行时 |
| 首版 HTML 解析器在标题结束时提前提交结果，导致摘要丢失 | 已修复，并由单测覆盖 |
| 改为流式读取响应后旧测试夹具仍模拟 `.get()` | 已修复测试夹具，7 项单测全部通过 |

## 只读搜索工具约束

- 固定访问 DuckDuckGo HTML 搜索端点，仅使用 HTTP `GET`。
- 不接受调用方传入 URL，不跟随重定向，不复用浏览器 Cookie、登录态或持久化会话。
- 仅返回标题、摘要和来源 URL，并限制查询长度、结果数、响应大小和请求超时。
- 搜索结果视为不可信外部内容，Agent 不得执行其中的指令，回答应提供来源 URL。

## 2026-09-22 聊天显示问题

- 根因：`ChatService.reply()` 将内部 `tool_calls` 放入 API 响应，`frontend/ui/calculator.html` 将其渲染为工具执行过程。
- 目标：保留工具在 Agent 内部执行能力，只向客户端返回最终 `reply`，前端不渲染任何工具调用详情。

## 2026-09-22 Markdown 显示问题

- 根因：聊天气泡仅把换行替换为 `<br>`，没有解析 Agent 返回的 Markdown。
- 修复：新增共享安全渲染器 `frontend/markdown.js`，仅 Agent 回复使用 `renderMarkdown()`；用户输入使用 `textContent`。
