$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$node = Join-Path $projectRoot ".tools\node\node.exe"
$mcpCli = Join-Path $projectRoot "node_modules\@playwright\mcp\cli.js"

if (-not (Test-Path -LiteralPath $node)) {
    throw "Node.js was not found at $node. Run the setup commands in README_PLAYWRIGHT_MCP.md."
}
if (-not (Test-Path -LiteralPath $mcpCli)) {
    throw "Playwright MCP was not found at $mcpCli. Run npm install first."
}

& $node $mcpCli --browser msedge --headless @args

