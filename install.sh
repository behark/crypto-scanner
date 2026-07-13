#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv || { echo "Install: sudo apt install python3-venv"; exit 1; }
fi
.venv/bin/pip install -q -r requirements.txt
chmod +x run_scan.sh run_loop.sh scanner.py
echo "Done. Test: .venv/bin/python scanner.py analyze cash-cat"
