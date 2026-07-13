#!/usr/bin/env python3
"""
X / Twitter Phase 0 watcher — monitors accounts via FxTwitter API (no X API key needed).
Alerts on keywords, cashtags, and high-signal accounts (bubblemaps, lookonchain).
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv

from notifier import alert

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

FXTWITTER = "https://api.fxtwitter.com/2/profile"
HEADERS = {"User-Agent": "CryptoScanner/1.0 (personal)"}

CASHTAG_RE = re.compile(r"\$([A-Za-z][A-Za-z0-9]{1,14})\b")


def load_config() -> dict:
    with open(ROOT / "config.yaml") as f:
        return yaml.safe_load(f)


def load_state(path: Path) -> dict:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"last_id": {}, "alerts": {}}


def save_state(path: Path, data: dict) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def parse_tweet_time(created_at: str) -> datetime | None:
    try:
        return parsedate_to_datetime(created_at)
    except Exception:
        return None


def tweet_text(tweet: dict) -> str:
    raw = tweet.get("raw_text") or {}
    if isinstance(raw, dict) and raw.get("text"):
        return raw["text"]
    return tweet.get("text") or ""


def matches_keywords(text: str, keywords: list[str]) -> list[str]:
    lower = text.lower()
    return [k for k in keywords if k.lower() in lower]


def extract_cashtags(text: str, min_len: int = 3) -> list[str]:
    return [m.group(1).upper() for m in CASHTAG_RE.finditer(text) if len(m.group(1)) >= min_len]


class XWatcher:
    def __init__(self, cfg: dict):
        self.cfg = cfg["x_watcher"]
        self.state_path = ROOT / cfg["paths"]["x_state_file"]
        self.state = load_state(self.state_path)
        self.session = requests.Session()

    def fetch_timeline(self, handle: str, since_id: str | None = None) -> list[dict]:
        url = f"{FXTWITTER}/{handle}/statuses"
        params: dict = {"count": 20}
        if since_id:
            # Use since timestamp from last tweet for efficiency
            pass
        r = self.session.get(url, headers=HEADERS, params=params, timeout=30)
        if r.status_code == 204:
            return []
        r.raise_for_status()
        data = r.json()
        return data.get("results") or []

    def evaluate_tweet(self, handle: str, tweet: dict) -> tuple[bool, str]:
        text = tweet_text(tweet)
        always = set(a.lower() for a in self.cfg.get("always_alert_accounts", []))
        keywords = self.cfg.get("keywords", [])
        min_len = self.cfg.get("cashtag_min_length", 3)

        reasons: list[str] = []

        if handle.lower() in always:
            reasons.append(f"high-signal account @{handle}")

        kw_hits = matches_keywords(text, keywords)
        if kw_hits:
            reasons.append(f"keywords: {', '.join(kw_hits[:5])}")

        tags = extract_cashtags(text, min_len)
        if tags:
            reasons.append(f"cashtags: {', '.join(tags[:5])}")

        if not reasons:
            return False, ""

        preview = text[:280].replace("\n", " ")
        return True, f"@{handle}: {preview}\n\n→ {' | '.join(reasons)}"

    def process_account(self, handle: str) -> int:
        last_id = self.state.get("last_id", {}).get(handle)
        try:
            tweets = self.fetch_timeline(handle)
        except Exception as e:
            logging.error("@%s fetch failed: %s", handle, e)
            return 0

        if not tweets:
            return 0

        # API returns newest first
        newest_id = tweets[0].get("id")
        if not newest_id:
            return 0

        alerts = 0
        is_bootstrap = handle not in self.state.get("last_id", {})

        for tweet in tweets:
            tid = tweet.get("id")
            if not tid:
                continue
            if last_id and int(tid) <= int(last_id):
                break

            if is_bootstrap:
                # First run: record cursor only — don't alert on history
                continue

            ok, reason = self.evaluate_tweet(handle, tweet)
            if ok:
                url = tweet.get("url", f"https://x.com/{handle}/status/{tid}")
                created = tweet.get("created_at", "")
                tags = extract_cashtags(tweet_text(tweet), self.cfg.get("cashtag_min_length", 3))

                links = {"tweet": url}
                if tags:
                    sym = tags[0]
                    links["coingecko_search"] = f"https://www.coingecko.com/en/search?query={sym}"

                title = "PHASE 0 — X alert"
                body = f"{reason}\n\n{created}"
                alert(title, body, links)
                alerts += 1
                logging.info("X alert @%s: %s", handle, tid)

        self.state.setdefault("last_id", {})[handle] = newest_id
        if is_bootstrap:
            logging.info("@%s bootstrapped at tweet %s (no historical alerts)", handle, newest_id)
        return alerts

    def run_once(self) -> None:
        accounts = self.cfg.get("accounts", [])
        total = 0
        for handle in accounts:
            total += self.process_account(handle.strip().lstrip("@"))
            time.sleep(1.2)  # polite rate limit
        save_state(self.state_path, self.state)
        logging.info("X watcher: %d alerts from %d accounts", total, len(accounts))

    def loop(self) -> None:
        interval = self.cfg.get("poll_interval_seconds", 120)
        logging.info("X watcher loop every %ss", interval)
        while True:
            try:
                self.run_once()
            except Exception as e:
                logging.exception("X watcher error: %s", e)
            time.sleep(interval)

    def backfill_test(self, handle: str, tweet_id: str) -> None:
        """Fetch one known tweet to verify pipeline (won't spam if already seen)."""
        url = f"https://api.fxtwitter.com/{handle}/status/{tweet_id}"
        r = self.session.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        data = r.json()
        tweet = data.get("tweet") or data
        ok, reason = self.evaluate_tweet(handle, tweet)
        print(f"Match: {ok}\n{reason}")


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("cmd", choices=["once", "loop", "test"], default="once", nargs="?")
    parser.add_argument("--handle", default="merts_eth")
    parser.add_argument("--tweet-id", default="2073854238690570703")
    args = parser.parse_args()

    cfg = load_config()
    w = XWatcher(cfg)
    if args.cmd == "test":
        w.backfill_test(args.handle, args.tweet_id)
    elif args.cmd == "loop":
        w.loop()
    else:
        w.run_once()
