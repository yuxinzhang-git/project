[CmdletBinding()]
param(
    [string] $InstallDirectory
)

$ErrorActionPreference = "Stop"

$InstallDirectory = if ([string]::IsNullOrWhiteSpace($InstallDirectory)) {
    $PSScriptRoot
} else {
    $InstallDirectory
}

$resolvedInstallDirectory = (Resolve-Path -LiteralPath $InstallDirectory).Path.TrimEnd('\')
$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
$pathEntries = @()

if (-not [string]::IsNullOrWhiteSpace($userPath)) {
    $pathEntries = $userPath -split ';' | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
}

$alreadyPresent = $pathEntries | Where-Object {
    [string]::Equals($_.TrimEnd('\'), $resolvedInstallDirectory, [StringComparison]::OrdinalIgnoreCase)
}

if (-not $alreadyPresent) {
    $newPath = (@($pathEntries) + $resolvedInstallDirectory) -join ';'
    try {
        [Environment]::SetEnvironmentVariable('Path', $newPath, 'User')
    } catch {
        Write-Error ("Could not update the user PATH automatically. Add this directory to PATH manually: " + $resolvedInstallDirectory)
        exit 1
    }
    Write-Host "Added XingClaw to the user PATH: $resolvedInstallDirectory"
} else {
    Write-Host "XingClaw is already in the user PATH: $resolvedInstallDirectory"
}

Write-Host 'Open a new terminal before running xingclaw.'
