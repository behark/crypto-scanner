#!/usr/bin/env bash
# Run scanner in loop (background service)
cd "$(dirname "$0")"
exec "$(dirname "$0")/.venv/bin/python" "$(dirname "$0")/scanner.py" loop
