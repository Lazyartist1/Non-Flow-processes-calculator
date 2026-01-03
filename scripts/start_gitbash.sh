#!/usr/bin/env bash
# start_gitbash.sh - helper for Git Bash / MSYS
# Creates venv if missing, installs deps using the venv python, and runs the API.

set -euo pipefail

echo "Starting helper: start_gitbash.sh"

if [ ! -x ".venv/Scripts/python" ]; then
  echo "Creating virtual environment .venv"
  if command -v python >/dev/null 2>&1; then
    python -m venv .venv
  elif command -v py >/dev/null 2>&1; then
    py -3 -m venv .venv
  else
    echo "No python executable found in PATH. Install Python or run from PowerShell." >&2
    exit 1
  fi
fi

echo "Installing/upgrading pip and dependencies"
.venv/Scripts/python -m pip install --upgrade pip setuptools wheel
.venv/Scripts/python -m pip install -r requirements.txt

echo "Running API (press Ctrl-C to stop)"
.venv/Scripts/python api.py


