#!/usr/bin/env bash
# Run Phase 0 watchers (X + DexScreener chain) — sends Telegram alerts
cd "$(dirname "$0")"
exec .venv/bin/python run_watchers.py
