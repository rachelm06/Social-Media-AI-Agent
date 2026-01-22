#!/bin/bash
# Start FastAPI server
# This script can be run directly or via systemd

cd "$(dirname "$0")"
source .venv/bin/activate
uvicorn src.api:app --host 0.0.0.0 --port 8000
