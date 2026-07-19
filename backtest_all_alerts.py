import os
import glob
import json
import datetime
import time
import requests
from collections import defaultdict

REPORTS_DIR = "reports"
CACHE_FILE = "coingecko_cache.json"

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                cache = json.load(f)
                if time.time() - cache.get("timestamp", 0) < 3600:
                    return cache.get("data", {})
        except:
            pass
    return {}

def save_cache(data):
    with open(CACHE_FILE, "w") as f:
        json.dump({"timestamp": time.time(), "data": data}, f)

def get_coin_history(coin_id, cache):
    if coin_id in cache:
        return cache[coin_id]
        
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days=14"
    for _ in range(3):
        resp = requests.get(url)
        if resp.status_code == 200:
            prices = resp.json().get('prices', [])
            cache[coin_id] = prices
            return prices
        elif resp.status_code == 429:
            print(f"Rate limited by CoinGecko for {coin_id}. Waiting 10s...")
            time.sleep(10)
        else:
            break
    return []

def main():
    files = glob.glob(os.path.join(REPORTS_DIR, "scan_*.json"))
    files.sort()
    
    signals = []
    
    for fpath in files:
        fname = os.path.basename(fpath)
        date_str = fname.replace("scan_", "").replace(".json", "")
        try:
            dt = datetime.datetime.strptime(date_str, "%Y%m%d_%H%M%S")
        except ValueError:
            continue
            
        with open(fpath, "r") as f:
            try:
                data = json.load(f)
            except:
                continue
                
            for item in data:
                signals.append({
                    "time": dt,
                    "kind": item.get("kind", "UNKNOWN"),
                    "coin_id": item.get("coingecko_id"),
                    "symbol": item.get("symbol"),
                    "price": item.get("price_usd", 0)
                })
    
    if not signals:
        print("No signals found in reports.")
        return

    unique_coins = set(s['coin_id'] for s in signals if s['coin_id'])
    print(f"Found {len(signals)} TOTAL alerts across {len(unique_coins)} unique coins.")
    
    cache = load_cache()
    for idx, coin_id in enumerate(unique_coins):
        if coin_id not in cache:
            get_coin_history(coin_id, cache)
            time.sleep(1.5)
            
    save_cache(cache)
        
    summary = defaultdict(lambda: {"count": 0, "win": 0, "peak_gain_sum": 0.0, "max_drop_sum": 0.0})
    
    print("\n" + "="*60)
    print(" 📊 CRYPTO SCANNER MULTI-ALERT BACKTEST REPORT 📊")
    print("="*60)
    
    for s in signals:
        coin_id = s["coin_id"]
        buy_price = s["price"]
        buy_time_ms = s["time"].timestamp() * 1000
        kind = s["kind"]
        
        if coin_id not in cache or buy_price <= 0:
            continue
            
        history = cache[coin_id]
        future_prices = [p[1] for p in history if p[0] >= buy_time_ms]
        
        if not future_prices:
            continue
            
        peak_price = max(future_prices)
        low_price = min(future_prices)
        
        peak_gain_pct = ((peak_price - buy_price) / buy_price) * 100
        drop_pct = ((low_price - buy_price) / buy_price) * 100
        
        is_win = False
        if "LONG" in kind:
            # A win for a LONG is if the price peaked higher than the buy price
            if peak_gain_pct > 0: is_win = True
        elif "EXIT" in kind:
            # A win for an EXIT warning is if the price dropped after the warning
            if drop_pct < 0: is_win = True
        else:
            if peak_gain_pct > 0: is_win = True
            
        summary[kind]["count"] += 1
        if is_win: summary[kind]["win"] += 1
        summary[kind]["peak_gain_sum"] += peak_gain_pct
        summary[kind]["max_drop_sum"] += drop_pct
        
    for kind, stats in summary.items():
        count = stats["count"]
        if count == 0: continue
        
        win_rate = (stats["win"] / count) * 100
        avg_peak = stats["peak_gain_sum"] / count
        avg_drop = stats["max_drop_sum"] / count
        
        print(f"[{kind}] Alerts evaluated: {count}")
        
        if "LONG" in kind:
            print(f"  -> Accuracy: {win_rate:.1f}% (Coins went UP after signal)")
            print(f"  -> Average Peak Gain: +{avg_peak:.2f}%")
        elif "EXIT" in kind:
            print(f"  -> Accuracy: {win_rate:.1f}% (Coins went DOWN after warning)")
            print(f"  -> Average Maximum Drop: {avg_drop:.2f}%")
        print("-" * 60)

if __name__ == "__main__":
    main()
