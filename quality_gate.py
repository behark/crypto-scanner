"""Token quality scoring before Telegram alerts (Sniper Elite gate)."""

from __future__ import annotations

from typing import Any


def pair_metrics(pair: dict) -> dict[str, Any]:
    liq = float((pair.get("liquidity") or {}).get("usd") or 0)
    vol = pair.get("volume") or {}
    txns = pair.get("txns") or {}
    h24 = txns.get("h24") or {}
    buys = int(h24.get("buys") or 0)
    sells = int(h24.get("sells") or 0)
    total_tx = buys + sells
    buy_ratio = buys / total_tx if total_tx else 0
    return {
        "symbol": (pair.get("baseToken") or {}).get("symbol", "?"),
        "price_usd": float(pair.get("priceUsd") or 0),
        "liquidity_usd": liq,
        "volume_h24": float(vol.get("h24") or 0),
        "volume_h6": float(vol.get("h6") or 0),
        "volume_h1": float(vol.get("h1") or 0),
        "buys_h24": buys,
        "sells_h24": sells,
        "buy_ratio_h24": round(buy_ratio, 3),
        "mcap": float(pair.get("marketCap") or pair.get("fdv") or 0),
        "chg_h24": float((pair.get("priceChange") or {}).get("h24") or 0),
        "url": pair.get("url", ""),
        "chain": pair.get("chainId", ""),
    }


def score_pair(pair: dict | None, cfg: dict) -> dict[str, Any]:
    """Return tier: junk | watch | qualified and human reasons."""
    q = cfg.get("quality_gate", {})
    min_liq_q = q.get("qualified_min_liquidity_usd", 25000)
    min_vol_q = q.get("qualified_min_volume_h24_usd", 50000)
    min_buy = q.get("qualified_min_buy_ratio", 0.52)
    min_liq_w = q.get("watch_min_liquidity_usd", 8000)

    if not pair:
        return {
            "tier": "junk",
            "score": 0,
            "reasons": ["no DEX pair found yet"],
            "metrics": {},
        }

    m = pair_metrics(pair)
    reasons: list[str] = []
    score = 0

    if m["liquidity_usd"] >= min_liq_q:
        score += 35
        reasons.append(f"liquidity ${m['liquidity_usd']/1e3:.1f}K ✓")
    elif m["liquidity_usd"] >= min_liq_w:
        score += 15
        reasons.append(f"liquidity ${m['liquidity_usd']/1e3:.1f}K (low)")
    else:
        reasons.append(f"liquidity ${m['liquidity_usd']/1e3:.1f}K ✗")

    if m["volume_h24"] >= min_vol_q:
        score += 35
        reasons.append(f"vol 24h ${m['volume_h24']/1e6:.2f}M ✓")
    elif m["volume_h24"] >= min_vol_q * 0.2:
        score += 15
        reasons.append(f"vol 24h ${m['volume_h24']/1e3:.0f}K (building)")
    else:
        reasons.append(f"vol 24h ${m['volume_h24']/1e3:.0f}K ✗")

    if m["buy_ratio_h24"] >= min_buy and (m["buys_h24"] + m["sells_h24"]) >= 10:
        score += 20
        reasons.append(f"buy pressure {m['buy_ratio_h24']:.0%} ✓")
    elif m["buys_h24"] + m["sells_h24"] >= 5:
        reasons.append(f"buy pressure {m['buy_ratio_h24']:.0%}")

    if m["chg_h24"] > 50:
        score += 10
        reasons.append(f"24h +{m['chg_h24']:.0f}% momentum")

    # Tier decision
    qualified = (
        m["liquidity_usd"] >= min_liq_q
        and m["volume_h24"] >= min_vol_q
        and m["buy_ratio_h24"] >= min_buy
    )
    watch = m["liquidity_usd"] >= min_liq_w and score >= 25

    if qualified:
        tier = "qualified"
    elif watch:
        tier = "watch"
    else:
        tier = "junk"

    return {"tier": tier, "score": score, "reasons": reasons, "metrics": m}


# CASHCAT reference thresholds (Jul 5 ~$0.004 phase) — for documentation / backtest notes
CASHCAT_REFERENCE = {
    "jul_5_price_usd": 0.004,
    "jul_8_price_usd": 0.14,
    "note": (
        "At true Phase 0 (Jul 1-5), CASHCAT likely FAILED strict liquidity gates. "
        "Elite gate fires at 'narrative + liquidity' phase (~Jul 5-7). "
        "Bubblemaps is never automatic — always manual link in alert."
    ),
}
