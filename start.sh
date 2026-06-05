#!/usr/bin/env bash
# Start the Asset-Vision web dashboard.
# Usage: bash start.sh
set -e
cd "$(dirname "$0")"
mkdir -p data
source ~/asset-venv/bin/activate
exec uvicorn web.app:app --host 0.0.0.0 --port 8000 --reload
