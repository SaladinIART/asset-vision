#!/usr/bin/env bash
# scripts/run.sh — start the Asset-Vision web dashboard.
#
# Usage:
#   bash scripts/run.sh [--host 0.0.0.0] [--port 8100]
#
# Activates the venv and launches Uvicorn. Run scripts/install.sh first.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_DIR="${HOME}/asset-venv"

# Parse optional overrides
HOST="127.0.0.1"
PORT="8100"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --host) HOST="$2"; shift 2 ;;
        --port) PORT="$2"; shift 2 ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

if [[ ! -d "${VENV_DIR}" ]]; then
    echo "[error] Virtual environment not found at ${VENV_DIR}."
    echo "        Run:  bash scripts/install.sh"
    exit 1
fi

cd "${REPO_ROOT}"
mkdir -p data/frames

echo "[info]  Starting Asset-Vision dashboard on http://${HOST}:${PORT}"
echo "[info]  Press Ctrl+C to stop."
echo ""

source "${VENV_DIR}/bin/activate"
exec uvicorn web.app:app --host "${HOST}" --port "${PORT}" --reload
