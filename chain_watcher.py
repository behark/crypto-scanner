#!/usr/bin/env python3
"""
DexScreener chain watcher — new Robinhood/BSC tokens + volume spikes.
Telegram alerts via notifier.py.
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
import yaml
from dotenv import load_dotenv

from notifier import alert
from quality_gate import score_pair

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

DEX = "https://api.dexscreener.com"
TOKEN_PROFILES = f"{DEX}/token-profiles/latest/v1"
HEADERS = {"User-Agent": "CryptoScanner/1.0 (personal)"}


def load_config() -> dict:
    with open(ROOT / "config.yaml") as f:
        return yaml.safe_load(f)


def load_json(path: Path) -> dict:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"tokens": {}, "profiles": [], "alerts": {}}


def save_json(path: Path, data: dict) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def cooldown_ok(state: dict, key: str, hours: float = 4) -> bool:
    last = state.get("alerts", {}).get(key)
    if not last:
        return True
    try:
        dt = datetime.fromisoformat(last)
        return (datetime.now(timezone.utc) - dt).total_seconds() >= hours * 3600
    except Exception:
        return True


def mark_alert(state: dict, key: str) -> None:
    state.setdefault("alerts", {})[key] = datetime.now(timezone.utc).isoformat()


def fetch_token_profiles(session: requests.Session) -> list[dict]:
    r = session.get(TOKEN_PROFILES, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


def fetch_token_pairs(session: requests.Session, address: str) -> list[dict]:
    r = session.get(f"{DEX}/latest/dex/tokens/{address}", headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json().get("pairs") or []


def best_pair(pairs: list[dict]) -> dict | None:
    if not pairs:
        return None
    return max(pairs, key=lambda p: float((p.get("liquidity") or {}).get("usd") or 0))


class ChainWatcher:
    def __init__(self, cfg: dict):
        self.cfg = cfg["chain_watcher"]
        self.paths = cfg["paths"]
        self.state_path = ROOT / self.paths["chain_state_file"]
        self.state = load_json(self.state_path)
        self.session = requests.Session()

    def check_new_profiles(self) -> int:
        if not self.cfg.get("new_token_profiles"):
            return 0
        chains = set(self.cfg.get("chains", []))
        known = set(self.state.get("profiles", []))
        bootstrap = not self.state.get("bootstrapped")
        count = 0
        try:
            profiles = fetch_token_profiles(self.session)
        except Exception as e:
            logging.error("token-profiles fetch failed: %s", e)
            return 0

        for p in profiles:
            chain = p.get("chainId", "")
            addr = (p.get("tokenAddress") or "").lower()
            if chain not in chains or not addr:
                continue
            pid = f"{chain}:{addr}"
            if pid in known:
                continue
            known.add(pid)
            self.state.setdefault("profiles", []).append(pid)

            if bootstrap:
                continue

            key = f"new_profile:{pid}"
            if not cooldown_ok(self.state, key, 6):
                continue

            # Sniper Elite gate — liquidity/volume (Bubblemaps still manual)
            try:
                pairs = fetch_token_pairs(self.session, addr)
                time.sleep(0.25)
            except Exception:
                pairs = []
            pair = best_pair(pairs)
            full_cfg = {"quality_gate": self.cfg.get("quality_gate", {})}
            scored = score_pair(pair, full_cfg)
            tier = scored["tier"]
            send_junk = self.cfg.get("quality_gate", {}).get("send_junk_alerts", False)
            send_watch = self.cfg.get("quality_gate", {}).get("send_watch_alerts", True)

            if tier == "junk" and not send_junk:
                logging.info("Skip junk profile %s: %s", pid, "; ".join(scored["reasons"]))
                continue
            if tier == "watch" and not send_watch:
                logging.info("Skip watch profile %s", pid)
                continue

            desc = (p.get("description") or "")[:200]
            m = scored.get("metrics") or {}
            sym = m.get("symbol", "?")
            links = {
                "dexscreener": p.get("url", f"https://dexscreener.com/{chain}/{addr}"),
                "bubblemaps": f"https://v2.bubblemaps.io/map?address={addr}&chain={chain}",
            }
            if tier == "qualified":
                title = f"ELITE — ${sym} on {chain}"
            elif tier == "watch":
                title = f"WATCH — ${sym} on {chain}"
            else:
                title = f"NEW (low quality) — {chain}"

            body = (
                f"{desc or '(no description)'}\n\n"
                f"Tier: {tier.upper()} | score {scored['score']}\n"
                + "\n".join(scored["reasons"])
            )
            if m:
                body += (
                    f"\n\nprice ${m.get('price_usd', 0):.6g} | "
                    f"liq ${m.get('liquidity_usd', 0)/1e3:.1f}K | "
                    f"vol ${m.get('volume_h24', 0)/1e3:.0f}K"
                )
            body += "\n\n⚠️ Open Bubblemaps before buying — not auto-checked"

            alert(title, body, links)
            mark_alert(self.state, key)
            count += 1
            logging.info("New profile: %s", pid)

        if bootstrap:
            self.state["bootstrapped"] = True
            logging.info("Chain watcher bootstrapped %d profiles (no historical alerts)", len(known))

        self.state["profiles"] = list(known)[-500:]
        return count

    def check_volume_spikes(self) -> int:
        chains = set(self.cfg.get("chains", []))
        min_vol = self.cfg.get("min_volume_h24_usd", 300000)
        mult = self.cfg.get("volume_spike_multiplier", 2.5)
        count = 0
        tokens = self.state.setdefault("tokens", {})

        # Re-check tokens we've seen + recent profiles
        addresses: set[str] = set()
        for pid in self.state.get("profiles", [])[-80:]:
            if ":" in pid:
                c, a = pid.split(":", 1)
                if c in chains:
                    addresses.add(a)

        for addr in list(addresses):
            try:
                pairs = fetch_token_pairs(self.session, addr)
                time.sleep(0.3)
            except Exception as e:
                logging.debug("pairs %s: %s", addr, e)
                continue

            pair = best_pair(pairs)
            if not pair or pair.get("chainId") not in chains:
                continue

            sym = (pair.get("baseToken") or {}).get("symbol", "?")
            vol = float((pair.get("volume") or {}).get("h24") or 0)
            price = float(pair.get("priceUsd") or 0)
            mcap = float(pair.get("marketCap") or pair.get("fdv") or 0)
            chg24 = float((pair.get("priceChange") or {}).get("h24") or 0)
            chain = pair.get("chainId", "")
            url = pair.get("url", "")

            prev = tokens.get(addr, {})
            prev_vol = prev.get("vol_h24", 0)

            tokens[addr] = {
                "symbol": sym,
                "vol_h24": vol,
                "price": price,
                "mcap": mcap,
                "chain": chain,
                "updated": datetime.now(timezone.utc).isoformat(),
            }

            if vol < min_vol:
                continue

            # First time seeing significant volume
            if prev_vol < min_vol and vol >= min_vol:
                key = f"vol_new:{addr}"
                if cooldown_ok(self.state, key) and self.state.get("bootstrapped"):
                    scored = score_pair(pair, {"quality_gate": self.cfg.get("quality_gate", {})})
                    if scored["tier"] == "junk":
                        logging.info("Skip junk vol spike %s", sym)
                        continue
                    title = f"ELITE VOL — ${sym} on {chain}" if scored["tier"] == "qualified" else f"VOLUME SPIKE — ${sym}"
                    body = (
                        f"24h vol ${vol/1e6:.2f}M | price ${price:.6g} | "
                        f"mcap ${mcap/1e6:.1f}M | 24h {chg24:+.1f}%"
                    )
                    links = {
                        "dexscreener": url,
                        "bubblemaps": f"https://v2.bubblemaps.io/map?address={addr}&chain={chain}",
                    }
                    alert(title, body, links)
                    mark_alert(self.state, key)
                    count += 1
                continue

            # Volume multiplier spike
            if prev_vol >= min_vol and vol >= prev_vol * mult:
                key = f"vol_spike:{addr}"
                if cooldown_ok(self.state, key, 2):
                    title = f"VOL {mult}× — ${sym}"
                    body = (
                        f"Vol ${prev_vol/1e6:.2f}M → ${vol/1e6:.2f}M | "
                        f"price ${price:.6g} | 24h {chg24:+.1f}%"
                    )
                    links = {"dexscreener": url}
                    alert(title, body, links)
                    mark_alert(self.state, key)
                    count += 1

        self.state["tokens"] = tokens
        return count

    def run_once(self) -> None:
        logging.info("Chain watcher cycle...")
        n1 = self.check_new_profiles()
        n2 = self.check_volume_spikes()
        save_json(self.state_path, self.state)
        logging.info("Chain watcher done: %d new profiles, %d vol alerts", n1, n2)

    def loop(self) -> None:
        interval = self.cfg.get("poll_interval_seconds", 300)
        logging.info("Chain watcher loop every %ss", interval)
        while True:
            try:
                self.run_once()
            except Exception as e:
                logging.exception("Chain watcher error: %s", e)
            time.sleep(interval)


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("cmd", choices=["once", "loop"], default="once", nargs="?")
    args = parser.parse_args()
    cfg = load_config()
    w = ChainWatcher(cfg)
    if args.cmd == "loop":
        w.loop()
    else:
        w.run_once()
