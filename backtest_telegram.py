import os
import glob
import re
import json
import time
import requests

EXPORT_DIR = "/home/behar/.var/app/org.telegram.desktop/data/TelegramDesktop/tdata/temp_data/ChatExport_2026-07-19"
INVESTMENT_PER_SIGNAL = 5.0

def main():
    html_files = glob.glob(os.path.join(EXPORT_DIR, "messages*.html"))
    if not html_files:
        return
        
    signals = []
    re_time = re.compile(r'class="pull_right date details" title="([^"]+)"')
    re_signal_type = re.compile(r'<strong>(WATCH|ELITE VOL|ELITE|VOLUME SPIKE)\s*—')
    re_symbol = re.compile(r'\$([a-zA-Z0-9_]+)')
    re_price = re.compile(r'price\s+\$([0-9\.eE\-]+)')
    re_address = re.compile(r'address=([a-zA-Z0-9]+)')
    
    for file_path in html_files:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        messages = content.split('class="message default')
        for msg in messages[1:]:
            t_match = re_time.search(msg)
            if not t_match: continue
            msg_time = t_match.group(1)
            
            type_match = re_signal_type.search(msg)
            if not type_match: continue
            sig_type = type_match.group(1).strip()
            
            header_end = msg.find("</strong>", type_match.end())
            if header_end == -1: header_end = type_match.end() + 50
            header_text = msg[type_match.start():header_end]
            sym_match = re_symbol.search(header_text)
            symbol = sym_match.group(1) if sym_match else "UNKNOWN"
            
            price_match = re_price.search(msg)
            if not price_match: continue
            try:
                price = float(price_match.group(1))
            except ValueError:
                continue
                
            addr_match = re_address.search(msg)
            if not addr_match: continue
            address = addr_match.group(1)
            
            signals.append({
                "time": msg_time,
                "type": sig_type,
                "symbol": symbol,
                "price": price,
                "address": address,
                "original_html": msg
            })
            
    unique_addresses = list(set(s['address'] for s in signals))
    
    current_prices = {}
    for i in range(0, len(unique_addresses), 30):
        batch = unique_addresses[i:i+30]
        url = f"https://api.dexscreener.com/latest/dex/tokens/{','.join(batch)}"
        try:
            resp = requests.get(url).json()
            pairs = resp.get("pairs", [])
            for pair in pairs:
                addr = pair.get("baseToken", {}).get("address", "").lower()
                price_str = pair.get("priceUsd")
                if price_str and addr:
                    price_val = float(price_str)
                    if addr not in current_prices:
                        current_prices[addr] = price_val
        except:
            pass
        time.sleep(0.5)
        
    individual_results = []
    
    for s in signals:
        addr = s["address"].lower()
        buy_price = s["price"]
        
        if addr in current_prices:
            curr_price = current_prices[addr]
            val_now = (INVESTMENT_PER_SIGNAL / buy_price) * curr_price
            profit = val_now - INVESTMENT_PER_SIGNAL
            roi_pct = (profit / INVESTMENT_PER_SIGNAL) * 100
            
            individual_results.append({
                "symbol": s["symbol"],
                "type": s["type"],
                "time": s["time"],
                "profit": profit,
                "roi_pct": roi_pct,
                "original_html": s["original_html"]
            })
        else:
            individual_results.append({
                "symbol": s["symbol"],
                "type": s["type"],
                "time": s["time"],
                "profit": -INVESTMENT_PER_SIGNAL,
                "roi_pct": -100.0,
                "original_html": s["original_html"]
            })
            
    # Sort by profit descending
    individual_results.sort(key=lambda x: x["profit"], reverse=True)
    top_20 = individual_results[:20]
    
    html_content = """
    <html>
    <head>
        <title>Top 20 Winning Alerts</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #1e1e2e; color: #cdd6f4; padding: 40px; margin: 0; }
            h1 { color: #a6e3a1; text-align: center; font-size: 2.5em; margin-bottom: 40px; }
            .alert-card { background: #313244; padding: 25px; margin-bottom: 30px; border-radius: 12px; border-left: 6px solid #a6e3a1; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
            .pnl-header { font-size: 1.4em; font-weight: bold; color: #a6e3a1; margin-bottom: 15px; border-bottom: 2px solid #45475a; padding-bottom: 10px; }
            .telegram-msg { background: #181825; padding: 15px; border-radius: 8px; margin-top: 15px; font-size: 1.1em; line-height: 1.5; color: #bac2de; }
            .telegram-msg strong { color: #f9e2af; }
            a { color: #89b4fa; text-decoration: none; }
            a:hover { text-decoration: underline; }
            .profit-amount { color: #a6e3a1; font-size: 1.3em; }
        </style>
    </head>
    <body>
        <h1>🏆 Top 20 Telegram Alerts (Hold to Now) 🏆</h1>
    """
    
    for rank, r in enumerate(top_20, 1):
        html_content += f'''
        <div class="alert-card">
            <div class="pnl-header">
                #{rank} - {r['type']} Alert at {r['time']}<br>
                <span class="profit-amount">Profit: +${r['profit']:.2f} (+{r['roi_pct']:.1f}%)</span> from a $5 investment
            </div>
            <div class="telegram-msg">
                {r['original_html']}
            </div>
        </div>
        '''
        
    html_content += """
    </body>
    </html>
    """
    
    report_path = "/home/behar/Documents/crypto-scanner/top_20_winners.html"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"\\nSaved top 20 winners HTML report to {report_path}")

if __name__ == "__main__":
    main()
