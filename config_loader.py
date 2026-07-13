"""Load config.yaml with optional remote override from Vercel dashboard."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parent


def load_config_dict() -> dict:
    local_path = ROOT / "config.yaml"
    url = os.getenv("CONFIG_URL", "").strip()

    if url:
        try:
            r = requests.get(url, timeout=15, headers={"User-Agent": "crypto-scanner/1.0"})
            r.raise_for_status()
            remote = yaml.safe_load(r.text)
            if isinstance(remote, dict):
                logging.info("Loaded config from CONFIG_URL")
                return remote
        except Exception as e:
            logging.warning("CONFIG_URL failed (%s), using local config.yaml", e)

    with open(local_path) as f:
        return yaml.safe_load(f)
