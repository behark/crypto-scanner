import os
import glob
import json
import datetime
import time
import requests

REPORTS_DIR = "reports"
INVESTMENT_PER_SIGNAL = 5.0
CACHE_FILE = "coingecko_cache.json"

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                cache = json.load(f)
                # Use cache if it's less than 30 minutes old
                if time.time() - cache.get("timestamp", 0) < 1800:
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
            print(f"Rate limited by CoinGecko for {coin_id}. Waiting 10 seconds...")
            time.sleep(10)
        else:
            print(f"Failed to fetch {coin_id}: HTTP {resp.status_code}")
            break
    return []

def main():
    files = glob.glob(os.path.join(REPORTS_DIR, "scan_*.json"))
    files.sort()
    
    signals = []
    
    # 1. Parse all signals
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
                # We only want to test the BUY signals
                if item.get("kind") == "LONG_CANDIDATE":
                    signals.append({
                        "time": dt,
                        "coin_id": item.get("coingecko_id"),
                        "symbol": item.get("symbol"),
                        "price": item.get("price_usd", 0)
                    })
    
    if not signals:
        print("No LONG_CANDIDATE signals found in reports.")
        return

    # 2. Fetch price history per unique coin
    unique_coins = set(s['coin_id'] for s in signals if s['coin_id'])
    print(f"Found {len(signals)} buy signals across {len(unique_coins)} unique coins.")
    
    cache = load_cache()
    print("Fetching historical data from CoinGecko. This may take a minute to respect rate limits...")
    for idx, coin_id in enumerate(unique_coins):
        if coin_id not in cache:
            print(f"[{idx+1}/{len(unique_coins)}] Fetching data for {coin_id}...")
            get_coin_history(coin_id, cache)
            time.sleep(1.5) # Prevent rate limits
            
    save_cache(cache)
        
    # 3. Calculate accuracy
    total_invested = 0.0
    total_value_now = 0.0
    total_value_peak = 0.0
    winning_trades = 0
    
    results = []
    
    for s in signals:
        coin_id = s["coin_id"]
        buy_price = s["price"]
        buy_time_ms = s["time"].timestamp() * 1000
        
        if coin_id not in cache or buy_price <= 0:
            continue
            
        history = cache[coin_id]
        
        # Filter prices AFTER the signal was generated
        future_prices = [p[1] for p in history if p[0] >= buy_time_ms]
        
        if not future_prices:
            continue
            
        current_price = future_prices[-1]
        peak_price = max(future_prices)
        
        tokens_bought = INVESTMENT_PER_SIGNAL / buy_price
        value_now = tokens_bought * current_price
        value_peak = tokens_bought * peak_price
        
        total_invested += INVESTMENT_PER_SIGNAL
        total_value_now += value_now
        total_value_peak += value_peak
        
        if value_now > INVESTMENT_PER_SIGNAL:
            winning_trades += 1
            
        results.append({
            "symbol": s["symbol"],
            "time": s["time"].strftime("%Y-%m-%d %H:%M:%S"),
            "buy_price": buy_price,
            "current_price": current_price,
            "peak_price": peak_price,
            "value_now": value_now,
            "value_peak": value_peak
        })
        
    # 4. Print Report
    print("\n" + "="*50)
    print(" 📈 CRYPTO SCANNER BACKTEST REPORT 📉")
    print("="*50)
    print(f"Total Signals Evaluated: {len(results)}")
    print(f"Investment per Signal:   ${INVESTMENT_PER_SIGNAL:.2f}")
    print(f"Total Capital Invested:  ${total_invested:.2f}")
    print("-" * 50)
    
    roi_now = ((total_value_now - total_invested) / total_invested) * 100 if total_invested else 0
    roi_peak = ((total_value_peak - total_invested) / total_invested) * 100 if total_invested else 0
    win_rate = (winning_trades / len(results)) * 100 if results else 0
    
    print(f"Current Portfolio Value: ${total_value_now:.2f} ({roi_now:+.2f}%)")
    print(f"Maximum Peak Value:      ${total_value_peak:.2f} ({roi_peak:+.2f}%)")
    print(f"Win Rate (Held to Now):  {win_rate:.1f}%")
    print("-" * 50)
    
    print("\n🏆 Top 5 Best Performing Signals (by Peak Value):")
    results.sort(key=lambda x: x["value_peak"], reverse=True)
    for r in results[:5]:
        peak_gain = ((r["value_peak"] - INVESTMENT_PER_SIGNAL) / INVESTMENT_PER_SIGNAL) * 100
        print(f"• {r['symbol']} on {r['time']}: Peak ${r['value_peak']:.2f} (+{peak_gain:.1f}%)")

if __name__ == "__main__":
    main()
