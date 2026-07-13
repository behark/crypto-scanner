#!/usr/bin/env bash
# Run one scan cycle
cd "$(dirname "$0")"
exec "$(dirname "$0")/.venv/bin/python" "$(dirname "$0")/scanner.py" scan
