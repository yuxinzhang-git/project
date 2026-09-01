param(
    [string]$Mode       = "im",
    [string]$Transport  = "webhook",
    [string]$ListenHost = "127.0.0.1",
    [int]   $Port       = 8787,
    [string]$Workspace  = ".",
    [string]$LogLevel   = "debug"
)

$ErrorActionPreference = "Stop"
$envFile = Join-Path $PSScriptRoot ".env.ps1"
if (Test-Path $envFile) {
    Write-Host "[dev] Loading $envFile ..." -ForegroundColor Cyan
    . $envFile
}

$workspaceInput = if ([string]::IsNullOrWhiteSpace($Workspace)) {
    (Get-Location).Path
} else {
    $Workspace
}
$workspaceCandidate = if ([IO.Path]::IsPathRooted($workspaceInput)) {
    $workspaceInput
} else {
    Join-Path (Get-Location).Path $workspaceInput
}
if (-not (Test-Path -LiteralPath $workspaceCandidate -PathType Container)) {
    Write-Host "Workspace does not exist: $workspaceCandidate" -ForegroundColor Red
    exit 1
}
$workspacePath = (Resolve-Path -LiteralPath $workspaceCandidate).Path

Set-Location $PSScriptRoot

$pythonExe = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand) {
        Write-Host "[dev] ERROR: Python 3.10+ was not found in PATH." -ForegroundColor Red
        exit 1
    }
    $pythonExe = $pythonCommand.Source
}

$installed = & $pythonExe -m pip show xingclaw 2>$null
if (-not $installed) {
    Write-Host "[dev] Installing xingclaw in editable mode ..." -ForegroundColor Yellow
    & $pythonExe -m pip install -e ".[dev]"
}

$provider = if ($env:XINGCLAW_PROVIDER) { $env:XINGCLAW_PROVIDER } else { "anthropic" }
$modelId  = if ($env:XINGCLAW_MODEL_ID) { $env:XINGCLAW_MODEL_ID } else { "claude-sonnet-4-5" }

if ($Mode -eq "im") {
    $appId     = $env:FEISHU_APP_ID
    $appSecret = $env:FEISHU_APP_SECRET
    $verifyTk  = $env:FEISHU_VERIFY_TOKEN

    if (-not $appId -or -not $appSecret) {
        Write-Host "[dev] ERROR: FEISHU_APP_ID and FEISHU_APP_SECRET must be set." -ForegroundColor Red
        Write-Host "[dev] Create .env.ps1 from .env.ps1.example and fill in values." -ForegroundColor Red
        exit 1
    }

    $pyArgs = @(
        "-m", "im",
        "--platform", "feishu",
        "--transport", $Transport,
        "--workspace", $workspacePath,
        "--host", $ListenHost,
        "--port", $Port,
        "--provider", $provider,
        "--model-id", $modelId,
        "--feishu-app-id", $appId,
        "--feishu-app-secret", $appSecret,
        "--log-level", $LogLevel
    )
    if ($verifyTk) {
        $pyArgs += @("--feishu-verify-token", $verifyTk)
    }

    Write-Host ("[dev] Starting IM service (" + $Transport + ") on " + $ListenHost + ":" + $Port + " ..." ) -ForegroundColor Green
    Write-Host ("[dev] Provider: " + $provider + " | Model: " + $modelId) -ForegroundColor Green
    & $pythonExe @pyArgs
} else {
    Write-Host "[XingClaw]" -ForegroundColor Cyan
    Write-Host "Workspace: $workspacePath"
    Write-Host "Provider: $provider"
    Write-Host "Model: $modelId"
    Write-Host "Entering interactive mode..."
    Write-Host "[dev] Workspace: $workspacePath" -ForegroundColor Green
    Write-Host "[dev] Provider: $provider" -ForegroundColor Green
    Write-Host "[dev] Model: $modelId" -ForegroundColor Green

    $pyArgs = @(
        "-m",
        "coding_agent",
        "--mode",
        "interactive",
        "--workspace",
        $workspacePath,
        "--provider",
        $provider,
        "--model-id",
        $modelId
    )
    Write-Host "[dev] Starting CLI interactive mode ..." -ForegroundColor Green
    & $pythonExe @pyArgs
}
