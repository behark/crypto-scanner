"""Shared alerts: Telegram + desktop + logging."""

from __future__ import annotations

import logging
import os
import subprocess
import sys

import requests

_session = requests.Session()


def telegram_configured() -> bool:
    return bool(os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"))


def send_telegram(text: str, parse_mode: str = "HTML") -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat:
        logging.warning("Telegram not configured (missing .env)")
        return False
    try:
        # Telegram limit 4096 chars
        if len(text) > 4000:
            text = text[:3997] + "..."
        r = _session.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": text, "parse_mode": parse_mode, "disable_web_page_preview": False},
            timeout=20,
        )
        data = r.json()
        if not data.get("ok"):
            logging.error("Telegram API error: %s", data)
            return False
        return True
    except Exception as e:
        logging.error("Telegram send failed: %s", e)
        return False


def send_desktop(title: str, body: str) -> None:
    if sys.platform != "linux":
        return
    try:
        subprocess.run(
            ["notify-send", "-u", "critical", title, body[:200]],
            check=False,
            timeout=5,
        )
    except Exception as e:
        logging.debug("notify-send failed: %s", e)


def alert(title: str, body: str, links: dict[str, str] | None = None, telegram: bool = True, desktop: bool = True) -> None:
    logging.info("ALERT %s | %s", title, body[:120])
    if desktop:
        send_desktop(title, body)
    if telegram:
        lines = [f"<b>{title}</b>", body]
        if links:
            lines.append("")
            for k, v in links.items():
                lines.append(f'<a href="{v}">{k}</a>')
        send_telegram("\n".join(lines))


def test_telegram() -> bool:
    return send_telegram("<b>Crypto Scanner</b>\nTelegram alerts are working.")
