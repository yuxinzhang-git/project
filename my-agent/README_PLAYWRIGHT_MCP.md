# Playwright MCP + Microsoft Edge

当前项目使用官方 `@playwright/mcp`，通过 Microsoft Edge channel 启动浏览器，不下载 Chromium。

## 已安装组件

- Python 3.12.7，虚拟环境：`agent`
- Python Playwright 1.61.0
- Node.js 24.18.0 和 npm 11.16.0，位于 `.tools/node`
- `@playwright/mcp` 0.0.78
- Microsoft Edge：`C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`

## 启动 MCP

在项目根目录执行：

```powershell
Set-Location F:\my-agent
& .\.tools\node\node.exe .\node_modules\@playwright\mcp\cli.js --browser msedge --headless
```

也可以使用脚本：

```powershell
& .\scripts\start-playwright-mcp.ps1
```

MCP 使用 stdio 通信，启动后终端不会显示普通网页地址；它应由 MCP 客户端（例如 Codex）负责启动和调用。

项目配置位于 `.codex/config.toml`。如果当前 Codex 版本只读取用户级配置，请将该文件中的 `[mcp_servers.playwright]` 段合并到 `%USERPROFILE%\.codex\config.toml`，然后重启 Codex。

## 验证安装

1. 检查 MCP 参数：

```powershell
$env:PATH = (Join-Path (Get-Location) ".tools\node") + ";" + $env:PATH
& .\.tools\node\npx.cmd --no-install @playwright/mcp --help
```

输出中应包含 `--browser <browser>`，且支持 `msedge`。

2. 运行 Python 最小示例：

```powershell
& .\agent\Scripts\python.exe -m examples.playwright_edge_smoke
```

成功时应输出类似：

```text
title=Example Domain
h1=Example Domain
```

这个示例会启动 Microsoft Edge（无头模式），访问 `https://example.com`，读取页面标题和 `h1` 文本，然后自动关闭浏览器。当前环境的实际执行结果为：

```text
title=Example Domain
h1=Example Domain
```

由于示例使用 `headless=True`，执行时不会显示浏览器窗口。网页操作模块的默认 Browser 则使用可见 Edge，并将会话保存到 `data/browser/profile/`。

3. 重启 Codex 后，检查 MCP 工具列表中是否出现 Playwright 工具。MCP 配置使用 `--browser msedge`，因此后续浏览器调用走 Edge，不使用 Computer Use。

## 常见错误

### `node.exe` 或 npm 找不到

不要依赖系统 PATH。使用项目内的 `.tools\node\node.exe` 和 `.tools\node\npm.cmd`，或重新安装 Node.js 24 LTS 到 `.tools/node`。

### `@playwright/mcp` 找不到

在项目根目录执行：

```powershell
$env:PATH = (Join-Path (Get-Location) ".tools\node") + ";" + $env:PATH
& .\.tools\node\npm.cmd install
```

### `browserType.launch: Executable doesn't exist`

确认 Edge 已安装，并检查：

```powershell
Test-Path "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
```

如果 Edge 安装在其他位置，可在 MCP 启动命令中追加：

```text
--executable-path C:\path\to\msedge.exe
```

### Codex 看不到 MCP 工具

确认配置段位于 Codex 实际读取的 `%USERPROFILE%\.codex\config.toml`，不是只放在项目说明文件中；合并 `.codex/config.toml` 后完全重启 Codex。MCP 命令、CLI 路径和参数必须保持为绝对路径。

### Edge 被其他进程锁定或无法启动

保持 `--headless`，或给 MCP 增加 `--isolated` 使用临时浏览器上下文。不要复用个人 Edge 用户目录，避免配置和登录状态冲突。
