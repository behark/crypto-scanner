# Crypto Scanner — Phase C+

Automated crypto alerts to **Telegram** + desktop.

## What runs

| Component | What it does | Interval |
|-----------|--------------|----------|
| `scanner.py` | CoinGecko gainers, Binance OI, LAB-style vol/mcap | 1h |
| `chain_watcher.py` | New tokens on **Robinhood/BSC** (DexScreener) + volume spikes | 5m |
| `x_watcher.py` | **Phase 0** — X posts from merts_eth, bubblemaps, lookonchain… | 2m |

## Quick start

```bash
cd ~/Documents/crypto-scanner

# 1. Telegram already configured in .env

# 2. Test Telegram
./test_telegram.sh

# 3. Start Phase 0 watchers (X + chain) — runs forever
./run_watchers.sh

# 4. In another terminal: hourly scanner
./run_loop.sh
```

You should receive a **Telegram test message** when running `test_telegram.sh`.

## Telegram setup

Credentials live in `.env` (never commit this file):

```
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

1. Open Telegram → find your bot → press **Start**
2. Run `./test_telegram.sh`

## Phase 0 — how X watching works

Uses **FxTwitter API** (free, no X developer account):

- Polls accounts in `config.yaml` → `x_watcher.accounts`
- Alerts when tweet matches **keywords** or **$CASHTAGS**
- `bubblemaps` + `lookonchain` → every new post (high signal)
- **First run bootstraps** — no spam from old tweets; only **new** posts after that

**Would have caught CASHCAT:** merts_eth Jul 5 post matches `cashcat`, `aped`, `culturally significant`, `$CASHCAT`.

Add accounts in `config.yaml`:

```yaml
x_watcher:
  accounts:
    - merts_eth
    - your_other_alpha_account
```

## Chain watcher — Robinhood / BSC

- DexScreener **latest token profiles** on `robinhood` chain
- **Volume spikes** 2.5× on tracked tokens
- Links to DexScreener + Bubblemaps in every alert

## Commands

```bash
.venv/bin/python scanner.py scan          # one scan → Telegram if signals
.venv/bin/python scanner.py analyze cash-cat
.venv/bin/python x_watcher.py once        # one X poll
.venv/bin/python chain_watcher.py once    # one chain poll
.venv/bin/python x_watcher.py test --handle merts_eth --tweet-id 2073854238690570703
```

## Systemd (auto-start on boot)

```bash
cd ~/Documents/crypto-scanner
./install_systemd.sh
```

This installs two **user services** (no root needed):

| Service | Role |
|---------|------|
| `crypto-watchers` | Phase 0 — X posts + new Robinhood/BSC tokens (Telegram) |
| `crypto-scanner` | Hourly gainers + OI + watchlist |

```bash
systemctl --user status crypto-watchers
journalctl --user -u crypto-watchers -f    # live logs
systemctl --user restart crypto-watchers
```

Services run at boot (linger enabled).

## Cron example

```cron
# Phase 0 watchers (restart on reboot — use systemd or screen/tmux for loop)
@reboot /home/behar/Documents/crypto-scanner/run_watchers.sh >> /home/behar/Documents/crypto-scanner/watchers.log 2>&1

# Hourly scanner
0 * * * * /home/behar/Documents/crypto-scanner/run_scan.sh >> /home/behar/Documents/crypto-scanner/cron.log 2>&1
```

## Security

- **Regenerate your bot token** in [@BotFather](https://t.me/BotFather) if you shared it publicly — use `/revoke` then update `.env`
- `.env` is in `.gitignore` — never commit tokens

## Guides

- `~/Documents/crypto-low-float-playbook.html`
- `~/Documents/crypto-alert-spotting-guide.html`
- `cashcat-case-study.html`
