#!/bin/bash
set -e

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "ERROR: .venv not found. Run ./install.sh first."
    exit 1
fi

source .venv/bin/activate
exec python3 main.py
