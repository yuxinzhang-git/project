$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$shell = New-Object -ComObject WScript.Shell

function New-XingClawShortcut {
    param(
        [string]$Name,
        [string]$BatchFile,
        [string]$Directory
    )

    $shortcut = $shell.CreateShortcut((Join-Path $Directory "$Name.lnk"))
    $shortcut.TargetPath = "$env:ComSpec"
    $shortcut.Arguments = '/d /k "' + $BatchFile + '"'
    $shortcut.WorkingDirectory = $root
    $shortcut.Description = "XingClaw $Name"
    $shortcut.IconLocation = "$env:SystemRoot\System32\cmd.exe,0"
    $shortcut.Save()
}

$desktop = [Environment]::GetFolderPath("Desktop")
New-XingClawShortcut -Name "XingClaw-CLI" -BatchFile (Join-Path $root "run_cli.bat") -Directory $root
New-XingClawShortcut -Name "XingClaw-Feishu" -BatchFile (Join-Path $root "run_feishu.bat") -Directory $root
if ($desktop -and (Test-Path $desktop)) {
    New-XingClawShortcut -Name "XingClaw-CLI" -BatchFile (Join-Path $root "run_cli.bat") -Directory $desktop
    New-XingClawShortcut -Name "XingClaw-Feishu" -BatchFile (Join-Path $root "run_feishu.bat") -Directory $desktop
}

Write-Host "Created XingClaw CLI and Feishu shortcuts in:" -ForegroundColor Green
Write-Host "  $root"
if ($desktop) { Write-Host "  $desktop" }
