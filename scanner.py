#!/usr/bin/env python3
"""
Crypto Scanner — Phase C automation
Scans gainers, Binance perp OI, volume/mcap ratios; alerts for LONG/EXIT signals.

Usage:
  python scanner.py scan              # one scan cycle
  python scanner.py loop              # run forever (interval from config)
  python scanner.py analyze cash-cat  # deep-dive one token (CoinGecko id)
  python scanner.py watchlist         # scan only watchlist tokens
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

COINGECKO = "https://api.coingecko.com/api/v3"
BINANCE_FAPI = "https://fapi.binance.com/fapi/v1"
DEXSCREENER = "https://api.dexscreener.com/latest/dex"

# Known contracts for Bubblemaps links (extend as needed)
KNOWN_CONTRACTS: dict[str, dict[str, str]] = {
    "cash-cat": {
        "chain": "robinhood",
        "address": "0x020bfC650A365f8BB26819deAAbF3E21291018b4",
    },
    "siren": {
        "chain": "bsc",
        "address": "0x997a58129890bbda032231a52ed1ddc845fc18e1",
    },
}


def usd_val(value: Any) -> float | None:
    """CoinGecko returns nested {usd: n} or sometimes a bare number."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        v = value.get("usd")
        return float(v) if v is not None else None
    return None


@dataclass
class Signal:
    kind: str  # LONG_CANDIDATE | EXIT_WARNING | WATCH | INFO
    symbol: str
    name: str
    coingecko_id: str
    price_usd: float
    message: str
    score: int = 0
    links: dict[str, str] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)


def load_config() -> dict:
    from config_loader import load_config_dict
    return load_config_dict()


def load_state(path: Path) -> dict:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"oi": {}, "alerts": {}, "last_scan": None}


def save_state(path: Path, state: dict) -> None:
    with open(path, "w") as f:
        json.dump(state, f, indent=2)


def setup_logging(log_file: str | None) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(ROOT / log_file, encoding="utf-8"))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
    )


class CryptoScanner:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "crypto-scanner/1.0 (personal)"
        state_path = ROOT / cfg["paths"]["state_file"]
        self.state = load_state(state_path)
        self.state_path = state_path
        self.reports_dir = ROOT / cfg["paths"]["reports_dir"]
        self.reports_dir.mkdir(exist_ok=True)
        self._binance_perps: set[str] | None = None

    def _get(self, url: str, params: dict | None = None, pause: float = 0) -> Any:
        if pause:
            time.sleep(pause)
        r = self.session.get(url, params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    def binance_perp_symbols(self) -> set[str]:
        if self._binance_perps is None:
            data = self._get(f"{BINANCE_FAPI}/exchangeInfo")
            self._binance_perps = {
                s["symbol"]
                for s in data["symbols"]
                if s.get("contractType") == "PERPETUAL" and s.get("status") == "TRADING"
            }
        return self._binance_perps

    def symbol_to_binance_perp(self, symbol: str) -> str | None:
        sym = symbol.upper().replace("-", "")
        candidates = [f"{sym}USDT", f"1000{sym}USDT"]
        perps = self.binance_perp_symbols()
        for c in candidates:
            if c in perps:
                return c
        return None

    def fetch_markets_page(self, page: int, per_page: int) -> list[dict]:
        pause = self.cfg["scan"].get("rate_limit_seconds", 1.2)
        return self._get(
            f"{COINGECKO}/coins/markets",
            params={
                "vs_currency": "usd",
                "order": "price_change_percentage_24h_desc",
                "per_page": per_page,
                "page": page,
                "sparkline": "false",
                "price_change_percentage": "24h,7d",
            },
            pause=pause,
        )

    def fetch_coin(self, coin_id: str) -> dict:
        pause = self.cfg["scan"].get("rate_limit_seconds", 1.2)
        return self._get(
            f"{COINGECKO}/coins/{coin_id}",
            params={
                "localization": "false",
                "tickers": "false",
                "market_data": "true",
                "community_data": "false",
                "developer_data": "false",
            },
            pause=pause,
        )

    def fetch_open_interest(self, binance_symbol: str) -> float | None:
        try:
            data = self._get(f"{BINANCE_FAPI}/openInterest", params={"symbol": binance_symbol})
            return float(data["openInterest"])
        except Exception as e:
            logging.debug("OI fetch failed %s: %s", binance_symbol, e)
            return None

    def fetch_funding_rate(self, binance_symbol: str) -> float | None:
        try:
            data = self._get(f"{BINANCE_FAPI}/premiumIndex", params={"symbol": binance_symbol})
            return float(data.get("lastFundingRate", 0))
        except Exception:
            return None

    def fetch_dexscreener(self, address: str) -> dict | None:
        try:
            data = self._get(f"{DEXSCREENER}/tokens/{address}")
            pairs = data.get("pairs") or []
            if not pairs:
                return None
            # highest liquidity pair
            best = max(pairs, key=lambda p: float((p.get("liquidity") or {}).get("usd") or 0))
            return best
        except Exception as e:
            logging.debug("DexScreener failed: %s", e)
            return None

    def bubblemaps_url(self, coin_id: str) -> str | None:
        info = KNOWN_CONTRACTS.get(coin_id)
        if not info:
            return None
        chain = info["chain"]
        addr = info["address"]
        return f"https://v2.bubblemaps.io/map?address={addr}&chain={chain}"

    def passes_filters(self, m: dict) -> bool:
        f = self.cfg["filters"]
        gain = m.get("price_change_percentage_24h") or 0
        mcap = m.get("market_cap") or 0
        vol = m.get("total_volume") or 0
        if gain < f["min_gain_24h_pct"]:
            return False
        if mcap < f["min_market_cap_usd"] or mcap > f["max_market_cap_usd"]:
            return False
        if vol < f["min_volume_24h_usd"]:
            return False
        min_7d = f.get("min_gain_7d_pct", 0)
        if min_7d:
            chg7_raw = m.get("price_change_percentage_7d_in_currency")
            if isinstance(chg7_raw, dict):
                gain7 = chg7_raw.get("usd") or 0
                if gain7 < min_7d:
                    return False
        return True

    def evaluate_market(self, m: dict) -> list[Signal]:
        signals: list[Signal] = []
        cid = m["id"]
        sym = m["symbol"].upper()
        name = m["name"]
        price = m.get("current_price") or 0
        mcap = m.get("market_cap") or 1
        vol = m.get("total_volume") or 0
        gain24 = m.get("price_change_percentage_24h") or 0
        high24 = m.get("high_24h") or price
        vol_mcap = vol / mcap if mcap else 0
        drop_from_high = ((high24 - price) / high24 * 100) if high24 else 0

        links = {
            "coingecko": f"https://www.coingecko.com/en/coins/{cid}",
            "tradingview": f"https://www.tradingview.com/chart/?symbol=BINANCE:{sym}USDT",
        }
        bm = self.bubblemaps_url(cid)
        if bm:
            links["bubblemaps"] = bm

        metrics = {
            "gain_24h_pct": round(gain24, 2),
            "market_cap_usd": mcap,
            "volume_24h_usd": vol,
            "vol_mcap_ratio": round(vol_mcap, 3),
            "drop_from_24h_high_pct": round(drop_from_high, 2),
        }

        sig = self.cfg["signals"]
        binance_sym = self.symbol_to_binance_perp(sym)

        # OI tracking
        if binance_sym:
            oi = self.fetch_open_interest(binance_sym)
            funding = self.fetch_funding_rate(binance_sym)
            if oi is not None:
                prev = self.state["oi"].get(binance_sym)
                self.state["oi"][binance_sym] = {
                    "oi": oi,
                    "ts": datetime.now(timezone.utc).isoformat(),
                }
                metrics["open_interest"] = oi
                metrics["binance_perp"] = binance_sym
                if funding is not None:
                    metrics["funding_rate"] = funding
                if prev and prev.get("oi"):
                    oi_chg = (oi - prev["oi"]) / prev["oi"] * 100
                    metrics["oi_change_pct"] = round(oi_chg, 2)
                    if oi_chg >= sig["oi_increase_pct"] and gain24 > 20:
                        signals.append(
                            Signal(
                                kind="LONG_CANDIDATE",
                                symbol=sym,
                                name=name,
                                coingecko_id=cid,
                                price_usd=price,
                                score=min(100, int(40 + oi_chg)),
                                message=(
                                    f"OI +{oi_chg:.1f}% on {binance_sym} with +{gain24:.1f}% 24h — "
                                    "momentum / perp buildup (check Bubblemaps before long)"
                                ),
                                links=links,
                                metrics=metrics,
                            )
                        )

        # Volume/mcap distribution warnings
        if vol_mcap >= sig["vol_mcap_ratio_extreme"]:
            signals.append(
                Signal(
                    kind="EXIT_WARNING",
                    symbol=sym,
                    name=name,
                    coingecko_id=cid,
                    price_usd=price,
                    score=90,
                    message=(
                        f"EXTREME vol/mcap {vol_mcap:.2f} — entire float trading hands; "
                        "distribution / exit zone likely"
                    ),
                    links=links,
                    metrics=metrics,
                )
            )
        elif vol_mcap >= sig["vol_mcap_ratio_high"]:
            signals.append(
                Signal(
                    kind="EXIT_WARNING",
                    symbol=sym,
                    name=name,
                    coingecko_id=cid,
                    price_usd=price,
                    score=60,
                    message=f"High vol/mcap {vol_mcap:.2f} — caution, possible distribution",
                    links=links,
                    metrics=metrics,
                )
            )

        # Gainer without exit flags
        if (
            self.passes_filters(m)
            and not any(s.kind == "EXIT_WARNING" for s in signals)
            and gain24 >= self.cfg["filters"]["min_gain_24h_pct"]
        ):
            signals.append(
                Signal(
                    kind="LONG_CANDIDATE",
                    symbol=sym,
                    name=name,
                    coingecko_id=cid,
                    price_usd=price,
                    score=min(100, int(30 + gain24 / 5)),
                    message=(
                        f"+{gain24:.1f}% 24h, mcap ${mcap/1e6:.1f}M, vol ${vol/1e6:.1f}M — "
                        "gainer screen hit; verify clusters on Bubblemaps"
                    ),
                    links=links,
                    metrics=metrics,
                )
            )

        # Sharp drop from 24h high after big run
        if drop_from_high >= sig["price_drop_from_ath_pct"] and gain24 > 50:
            signals.append(
                Signal(
                    kind="EXIT_WARNING",
                    symbol=sym,
                    name=name,
                    coingecko_id=cid,
                    price_usd=price,
                    score=70,
                    message=(
                        f"Price -{drop_from_high:.1f}% from 24h high after +{gain24:.1f}% day — "
                        "possible top / short scalp zone"
                    ),
                    links=links,
                    metrics=metrics,
                )
            )

        return signals

    def analyze_token(self, coin_id: str) -> dict:
        """Full analysis report for one token."""
        coin = self.fetch_coin(coin_id)
        md = coin.get("market_data") or {}
        sym = coin["symbol"].upper()
        price = md.get("current_price") or {}
        if isinstance(price, dict):
            price_usd = price.get("usd", 0)
        else:
            price_usd = price
        mcap = (md.get("market_cap") or {}).get("usd", 0)
        vol = (md.get("total_volume") or {}).get("usd", 0)
        ath = (md.get("ath") or {}).get("usd", 0)
        atl = (md.get("atl") or {}).get("usd", 0)
        chg24 = md.get("price_change_percentage_24h", 0)
        chg7 = md.get("price_change_percentage_7d", 0)
        vol_mcap = vol / mcap if mcap else 0

        platforms = coin.get("platforms") or {}
        contract = None
        chain = None
        for c, addr in platforms.items():
            if addr:
                contract, chain = addr, c
                break
        if coin_id in KNOWN_CONTRACTS:
            contract = KNOWN_CONTRACTS[coin_id]["address"]
            chain = KNOWN_CONTRACTS[coin_id]["chain"]

        dex = self.fetch_dexscreener(contract) if contract else None
        binance_sym = self.symbol_to_binance_perp(sym)
        oi = self.fetch_open_interest(binance_sym) if binance_sym else None
        funding = self.fetch_funding_rate(binance_sym) if binance_sym else None

        # Playbook-style verdict
        verdicts = []
        if vol_mcap > 0.8:
            verdicts.append("EXIT/SHORT bias — extreme volume vs mcap")
        elif vol_mcap > 0.45:
            verdicts.append("CAUTION — high churn, watch CEX outflows")
        elif chg24 > 35 and vol_mcap < 0.3:
            verdicts.append("LONG scalp candidate — momentum with room (verify Bubblemaps clusters)")
        else:
            verdicts.append("NEUTRAL — mixed or low momentum")

        if dex:
            buys = (dex.get("txns") or {}).get("h24", {}).get("buys", 0)
            sells = (dex.get("txns") or {}).get("h24", {}).get("sells", 0)
            liq = (dex.get("liquidity") or {}).get("usd", 0)
            verdicts.append(f"DEX: {buys} buys / {sells} sells 24h, liq ${liq/1e6:.2f}M")

        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "id": coin_id,
            "name": coin["name"],
            "symbol": sym,
            "price_usd": price_usd,
            "market_cap_usd": mcap,
            "volume_24h_usd": vol,
            "vol_mcap_ratio": round(vol_mcap, 4),
            "change_24h_pct": chg24,
            "change_7d_pct": chg7,
            "ath_usd": ath,
            "atl_usd": atl,
            "contract": contract,
            "chain": chain,
            "binance_perp": binance_sym,
            "open_interest": oi,
            "funding_rate": funding,
            "bubblemaps": self.bubblemaps_url(coin_id),
            "verdicts": verdicts,
            "dex_pair": dex.get("url") if dex else None,
        }
        return report

    def should_alert(self, key: str) -> bool:
        cooldown_h = self.cfg["signals"]["alert_cooldown_hours"]
        last = self.state["alerts"].get(key)
        if not last:
            return True
        try:
            last_dt = datetime.fromisoformat(last)
            elapsed = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600
            return elapsed >= cooldown_h
        except Exception:
            return True

    def mark_alerted(self, key: str) -> None:
        self.state["alerts"][key] = datetime.now(timezone.utc).isoformat()

    def notify(self, signal: Signal) -> None:
        key = f"{signal.kind}:{signal.coingecko_id}"
        if not self.should_alert(key):
            logging.info("Skipping (cooldown): %s", key)
            return

        title = f"{signal.kind} — {signal.symbol}"
        body = f"${signal.price_usd:.6g} | {signal.message}"
        logging.info("ALERT %s | %s", title, body)

        notif = self.cfg["notifications"]
        if notif.get("console", True):
            print("\n" + "=" * 60)
            print(f"  {title}  (score {signal.score})")
            print(f"  {body}")
            for k, v in signal.links.items():
                print(f"  {k}: {v}")
            if signal.metrics:
                print(f"  metrics: {signal.metrics}")
            print("=" * 60 + "\n")

        if notif.get("desktop") and sys.platform == "linux":
            try:
                subprocess.run(
                    ["notify-send", "-u", "critical", title, body[:200]],
                    check=False,
                    timeout=5,
                )
            except Exception as e:
                logging.debug("notify-send failed: %s", e)

        if notif.get("telegram"):
            from notifier import alert as notify_alert
            notify_alert(title, body, signal.links)

        self.mark_alerted(key)

    def _telegram(self, text: str) -> None:
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat = os.getenv("TELEGRAM_CHAT_ID")
        if not token or not chat:
            logging.warning("Telegram enabled but TELEGRAM_BOT_TOKEN/CHAT_ID missing")
            return
        try:
            self.session.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat, "text": text, "parse_mode": "HTML"},
                timeout=15,
            )
        except Exception as e:
            logging.error("Telegram send failed: %s", e)

    def scan_gainers(self, pages: int = 2) -> list[Signal]:
        all_signals: list[Signal] = []
        per_page = self.cfg["scan"]["coingecko_per_page"]
        seen: set[str] = set()

        for page in range(1, pages + 1):
            try:
                markets = self.fetch_markets_page(page, per_page)
            except Exception as e:
                logging.error("CoinGecko page %s failed: %s", page, e)
                break
            for m in markets:
                if m["id"] in seen:
                    continue
                seen.add(m["id"])
                try:
                    for sig in self.evaluate_market(m):
                        all_signals.append(sig)
                except Exception as e:
                    logging.error("Evaluate %s failed: %s", m.get("id"), e)

        all_signals.sort(key=lambda s: s.score, reverse=True)
        return all_signals

    def scan_watchlist(self) -> list[Signal]:
        signals: list[Signal] = []
        for coin_id in self.cfg.get("watchlist", []):
            try:
                coin = self.fetch_coin(coin_id)
                md = coin.get("market_data") or {}
                m = {
                    "id": coin_id,
                    "symbol": coin["symbol"],
                    "name": coin["name"],
                    "current_price": usd_val(md.get("current_price")),
                    "market_cap": usd_val(md.get("market_cap")),
                    "total_volume": usd_val(md.get("total_volume")),
                    "high_24h": usd_val(md.get("high_24h")),
                    "price_change_percentage_24h": md.get("price_change_percentage_24h"),
                }
                signals.extend(self.evaluate_market(m))
            except Exception as e:
                logging.error("Watchlist %s failed: %s", coin_id, e)
        return signals

    def run_scan(self, watchlist_only: bool = False) -> list[Signal]:
        logging.info("Starting scan...")
        if watchlist_only:
            signals = self.scan_watchlist()
        else:
            signals = self.scan_gainers(pages=2)
            wl = self.scan_watchlist()
            # merge watchlist without dupes
            existing = {s.coingecko_id for s in signals}
            signals.extend(s for s in wl if s.coingecko_id not in existing)

        self.state["last_scan"] = datetime.now(timezone.utc).isoformat()
        save_state(self.state_path, self.state)

        # notify top signals
        for sig in signals[:15]:
            if sig.kind in ("LONG_CANDIDATE", "EXIT_WARNING") and sig.score >= 50:
                self.notify(sig)

        # save report
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.reports_dir / f"scan_{ts}.json"
        with open(report_path, "w") as f:
            json.dump([asdict(s) for s in signals], f, indent=2)
        logging.info("Wrote %d signals to %s", len(signals), report_path)
        return signals

    def print_analysis(self, coin_id: str) -> None:
        report = self.analyze_token(coin_id)
        print(json.dumps(report, indent=2))
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.reports_dir / f"analyze_{coin_id}_{ts}.json"
        with open(path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nSaved: {path}")
        print("\n--- VERDICT ---")
        for v in report["verdicts"]:
            print(f"  • {v}")
        if report.get("bubblemaps"):
            print(f"\n  Bubblemaps: {report['bubblemaps']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Crypto Scanner Phase C")
    parser.add_argument("command", choices=["scan", "loop", "analyze", "watchlist"])
    parser.add_argument("token", nargs="?", help="CoinGecko id for analyze")
    args = parser.parse_args()

    cfg = load_config()
    setup_logging(cfg["notifications"].get("log_file"))
    scanner = CryptoScanner(cfg)

    if args.command == "scan":
        scanner.run_scan()
    elif args.command == "watchlist":
        scanner.run_scan(watchlist_only=True)
    elif args.command == "loop":
        interval = cfg["scan"]["interval_seconds"]
        logging.info("Loop mode — every %ss (Ctrl+C to stop)", interval)
        while True:
            try:
                scanner.run_scan()
            except Exception as e:
                logging.exception("Scan error: %s", e)
            time.sleep(interval)
    elif args.command == "analyze":
        if not args.token:
            print("Usage: python scanner.py analyze <coingecko-id>")
            sys.exit(1)
        scanner.print_analysis(args.token)


if __name__ == "__main__":
    main()
