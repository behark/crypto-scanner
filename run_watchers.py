#!/usr/bin/env python3
"""Run chain + X watchers together (Phase 0 monitoring)."""

import logging
import threading
import time
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(threadName)s] %(message)s")
    with open(ROOT / "config.yaml") as f:
        cfg = yaml.safe_load(f)

    from chain_watcher import ChainWatcher
    from x_watcher import XWatcher

    threads = []

    if cfg.get("chain_watcher", {}).get("enabled", True):
        cw = ChainWatcher(cfg)
        t = threading.Thread(target=cw.loop, name="chain", daemon=True)
        t.start()
        threads.append(t)

    if cfg.get("x_watcher", {}).get("enabled", True):
        xw = XWatcher(cfg)
        t = threading.Thread(target=xw.loop, name="x", daemon=True)
        t.start()
        threads.append(t)

    if not threads:
        logging.error("No watchers enabled in config.yaml")
        return

    logging.info("Watchers running (%d threads). Ctrl+C to stop.", len(threads))
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logging.info("Stopped.")


if __name__ == "__main__":
    main()
