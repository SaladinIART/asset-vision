<#
.SYNOPSIS
    One-command Windows setup for Asset-Vision Phase A dashboard.

.DESCRIPTION
    1. Creates a repo-local .venv with the py launcher
    2. Installs Python dependencies from requirements.txt
    3. Installs asset_vision as an editable package (pip install -e .)
    4. Copies config.example.yaml -> config.yaml if absent
    5. Creates data\frames directory

    Re-running is safe (idempotent).
    For the manual step-by-step guide, see WINDOWS.md.

.EXAMPLE
    .\scripts\install.ps1
    .\scripts\install.ps1 -PythonCmd "py -3.11"
#>

[CmdletBinding()]
param(
    [string]$PythonCmd = "py"   # change to "python" if py launcher not installed
)

$ErrorActionPreference = "Stop"

function info    { Write-Host "[info]  $args" -ForegroundColor Cyan }
function ok      { Write-Host "[ok]    $args" -ForegroundColor Green }
function warn    { Write-Host "[warn]  $args" -ForegroundColor Yellow }
function err     { Write-Host "[error] $args" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "Asset-Vision — Windows Setup" -ForegroundColor White
Write-Host ""

# ── Locate repo root ──────────────────────────────────────────────────────────
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = (Resolve-Path (Join-Path $ScriptDir "..")).Path
Set-Location $RepoRoot
info "Repo root: $RepoRoot"

# ── 1. Verify Python ──────────────────────────────────────────────────────────
info "Checking Python…"
try {
    $PyVer = & $PythonCmd --version 2>&1
    ok "$PyVer found."
} catch {
    err "Python not found via '$PythonCmd'. Install Python 3.10+ from python.org and ensure the py launcher is available, or pass -PythonCmd 'python'."
}

# ── 2. Create .venv ───────────────────────────────────────────────────────────
$VenvDir = Join-Path $RepoRoot ".venv"
if (Test-Path $VenvDir) {
    ok ".venv already exists — skipping creation."
} else {
    info "Creating virtual environment at .venv …"
    & $PythonCmd -m venv $VenvDir
    ok ".venv created."
}

$Pip    = Join-Path $VenvDir "Scripts\pip.exe"
$Python = Join-Path $VenvDir "Scripts\python.exe"

# ── 3. Upgrade pip silently ───────────────────────────────────────────────────
info "Upgrading pip…"
& $Python -m pip install --quiet --upgrade pip
ok "pip up to date."

# ── 4. Install Python dependencies ───────────────────────────────────────────
info "Installing Python dependencies from requirements.txt…"
& $Pip install --quiet -r (Join-Path $RepoRoot "requirements.txt")
ok "Dependencies installed."

# ── 5. Install asset_vision package (editable) ───────────────────────────────
info "Installing asset_vision package (editable)…"
& $Pip install --quiet -e $RepoRoot
ok "asset_vision installed."

# ── 6. Config file ────────────────────────────────────────────────────────────
$ConfigSrc  = Join-Path $RepoRoot "config.example.yaml"
$ConfigDest = Join-Path $RepoRoot "config.yaml"
if (Test-Path $ConfigDest) {
    ok "config.yaml already exists — not overwritten."
} else {
    info "Copying config.example.yaml -> config.yaml…"
    Copy-Item $ConfigSrc $ConfigDest
    ok "config.yaml created (source: sample — no camera needed)."
}

# ── 7. Data directory ─────────────────────────────────────────────────────────
$FramesDir = Join-Path $RepoRoot "data\frames"
if (-not (Test-Path $FramesDir)) {
    New-Item -ItemType Directory -Force $FramesDir | Out-Null
}
ok "data\frames directory ready."

# ── 8. Sample images ──────────────────────────────────────────────────────────
$SamplesDir  = Join-Path $RepoRoot "samples"
$SampleCount = 0
if (Test-Path $SamplesDir) {
    $SampleCount = (Get-ChildItem $SamplesDir -Include "*.jpg","*.png" -Recurse).Count
}
if ($SampleCount -eq 0) {
    info "Generating sample images…"
    & $Python (Join-Path $RepoRoot "generate_samples.py")
    ok "Sample images generated."
} else {
    ok "Sample images already present ($SampleCount files)."
}

# ── Done ──────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "  Next steps:"
Write-Host "    Run the dashboard:  .\scripts\run.ps1"
Write-Host "    Open in browser:    http://localhost:8100"
Write-Host ""
Write-Host "  Camera options (edit config.yaml -> camera.source):"
Write-Host "    sample      -- offline demo, no hardware (current default)"
Write-Host "    usb         -- USB camera (native Windows; no usbipd needed)"
Write-Host "    integrated  -- built-in laptop cam (same as usb, index=0)"
Write-Host "    ipcam       -- phone running IP Webcam app over WiFi"
Write-Host ""
Write-Host "  See docs/CAMERA_SOURCES.md for a full comparison."
Write-Host "  For manual step-by-step instructions, see WINDOWS.md."
Write-Host ""
