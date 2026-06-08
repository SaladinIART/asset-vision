#!/usr/bin/env bash
# scripts/install.sh — one-command setup for Asset-Vision (WSL2 Ubuntu 22.04)
#
# Usage:
#   bash scripts/install.sh
#
# What it does:
#   1. Installs system packages (libzbar0, ffmpeg, python3-venv, …)
#   2. Creates a Python virtual environment at ~/asset-venv
#   3. Installs Python dependencies from requirements.txt
#   4. Copies config.example.yaml -> config.yaml if config.yaml is absent
#   5. Generates sample images (samples/) if missing
#   6. Creates the data/ directory
#
# Re-running is safe (idempotent).
set -euo pipefail

# ── Colours ────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${CYAN}[info]${NC}  $*"; }
success() { echo -e "${GREEN}[ok]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[warn]${NC}  $*"; }
error()   { echo -e "${RED}[error]${NC} $*" >&2; exit 1; }

echo -e "\n${BOLD}Asset-Vision — Setup${NC}\n"

# ── Locate repo root (the directory containing this script's parent) ───────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"
info "Repo root: ${REPO_ROOT}"

# ── 1. System packages ─────────────────────────────────────────────────────
info "Checking system packages…"
MISSING_PKGS=()
for pkg in python3 python3-venv python3-pip libzbar0 ffmpeg git; do
    dpkg -s "$pkg" &>/dev/null || MISSING_PKGS+=("$pkg")
done

if [[ ${#MISSING_PKGS[@]} -gt 0 ]]; then
    info "Installing: ${MISSING_PKGS[*]}"
    if [[ $EUID -ne 0 ]]; then
        sudo apt-get update -qq
        sudo apt-get install -y -qq "${MISSING_PKGS[@]}"
    else
        apt-get update -qq
        apt-get install -y -qq "${MISSING_PKGS[@]}"
    fi
    success "System packages installed."
else
    success "System packages already present."
fi

# ── 2. Python virtual environment ─────────────────────────────────────────
VENV_DIR="${HOME}/asset-venv"
if [[ ! -d "${VENV_DIR}" ]]; then
    info "Creating virtual environment at ${VENV_DIR}…"
    python3 -m venv "${VENV_DIR}"
    success "Virtual environment created."
else
    success "Virtual environment already exists at ${VENV_DIR}."
fi

# ── 3. Python dependencies ────────────────────────────────────────────────
info "Installing Python dependencies…"
"${VENV_DIR}/bin/pip" install --quiet --upgrade pip
"${VENV_DIR}/bin/pip" install --quiet -r "${REPO_ROOT}/requirements.txt"
# Install the asset_vision package in editable mode so all modules are importable
"${VENV_DIR}/bin/pip" install --quiet -e "${REPO_ROOT}"
success "Python dependencies installed (asset_vision package registered)."

# ── 4. Config file ────────────────────────────────────────────────────────
if [[ ! -f "${REPO_ROOT}/config.yaml" ]]; then
    info "Copying config.example.yaml → config.yaml…"
    cp "${REPO_ROOT}/config.example.yaml" "${REPO_ROOT}/config.yaml"
    success "config.yaml created (source: sample — no camera needed)."
else
    success "config.yaml already exists (not overwritten)."
fi

# ── 5. Sample images ──────────────────────────────────────────────────────
if [[ ! -d "${REPO_ROOT}/samples" ]] || \
   [[ $(find "${REPO_ROOT}/samples" -name "*.jpg" -o -name "*.png" 2>/dev/null | wc -l) -eq 0 ]]; then
    info "Generating sample images…"
    "${VENV_DIR}/bin/python" "${REPO_ROOT}/generate_samples.py"
    success "Sample images created."
else
    success "Sample images already present."
fi

# ── 6. Data directory ─────────────────────────────────────────────────────
mkdir -p "${REPO_ROOT}/data/frames"
success "data/ directory ready."

# ── Done ──────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}Setup complete!${NC}"
echo ""
echo "  Next steps:"
echo "    Run the dashboard:  bash scripts/run.sh"
echo "    Open in browser:    http://localhost:8100"
echo ""
echo "  Camera options (edit config.yaml → camera.source):"
echo "    sample      — offline demo, no hardware (current default)"
echo "    usb         — USB camera (native Linux; WSL2 needs usbipd-win)"
echo "    integrated  — built-in laptop cam (same as usb, index=0)"
echo "    ipcam       — phone running IP Webcam app over WiFi"
echo ""
echo "  See docs/CAMERA_SOURCES.md for a full comparison."
echo ""
