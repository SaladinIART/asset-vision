<#
.SYNOPSIS
    Start the Asset-Vision web dashboard on Windows.

.DESCRIPTION
    Activates the repo-local .venv and launches Uvicorn.
    Run scripts\install.ps1 first.

.PARAMETER Host
    Bind address (default: 127.0.0.1)

.PARAMETER Port
    Port number (default: 8100)

.EXAMPLE
    .\scripts\run.ps1
    .\scripts\run.ps1 -Host 0.0.0.0 -Port 9000
#>

[CmdletBinding()]
param(
    [string]$Host = "127.0.0.1",
    [int]$Port    = 8100
)

$ErrorActionPreference = "Stop"

# ── Locate repo root ──────────────────────────────────────────────────────────
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = (Resolve-Path (Join-Path $ScriptDir "..")).Path
Set-Location $RepoRoot

$VenvDir = Join-Path $RepoRoot ".venv"
$Uvicorn = Join-Path $VenvDir "Scripts\uvicorn.exe"

if (-not (Test-Path $VenvDir)) {
    Write-Host "[error] .venv not found. Run:  .\scripts\install.ps1" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $Uvicorn)) {
    Write-Host "[error] uvicorn not found inside .venv. Run:  .\scripts\install.ps1" -ForegroundColor Red
    exit 1
}

# ── Ensure data/frames exists ─────────────────────────────────────────────────
$FramesDir = Join-Path $RepoRoot "data\frames"
if (-not (Test-Path $FramesDir)) {
    New-Item -ItemType Directory -Force $FramesDir | Out-Null
}

Write-Host "[info]  Starting Asset-Vision dashboard on http://${Host}:${Port}" -ForegroundColor Cyan
Write-Host "[info]  Press Ctrl+C to stop." -ForegroundColor Cyan
Write-Host ""

& $Uvicorn web.app:app --host $Host --port $Port --reload
