#!/usr/bin/env bash
# Test Telegram connection
cd "$(dirname "$0")"
.venv/bin/python -c "from dotenv import load_dotenv; load_dotenv(); from notifier import test_telegram; print('OK' if test_telegram() else 'FAILED')"
