# Crypto Scanner — Phase C+

Automated crypto alerts to **Telegram** + desktop.

**📚 [Learning Hub (HTML docs)](docs/index.html)** — start with the [Complete Workflow Guide](docs/complete-workflow-guide.html)

## What runs

| Component | What it does | Interval |
|-----------|--------------|----------|
| `x_watcher.py` | Phase 0 — X posts, $cashtags, alpha accounts | 2m |
| `chain_watcher.py` | New tokens Robinhood/BSC/SOL + volume spikes | 5m |
| `scanner.py` | CoinGecko gainers, Binance OI, vol/mcap | 1h |

**Sniper Elite gate** — filters junk chain alerts (liquidity + volume + buy pressure). Bubblemaps is still manual.

## Quick start

```bash
git clone https://github.com/behark/crypto-scanner.git
cd crypto-scanner
cp .env.example .env   # add TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID
bash install.sh
./test_telegram.sh
./install_systemd.sh
```

## Documentation

| Guide | Description |
|-------|-------------|
| [docs/index.html](docs/index.html) | **Hub** — all guides |
| [docs/complete-workflow-guide.html](docs/complete-workflow-guide.html) | **Start here** — daily process, sizing, how to benefit |
| [docs/tools-reference.html](docs/tools-reference.html) | Every tool + when to use it |
| [docs/low-float-playbook.html](docs/low-float-playbook.html) | LAB/SIREN insider playbook |
| [docs/alert-spotting-guide.html](docs/alert-spotting-guide.html) | Rise/fall signals, Bubblemaps |
| [docs/cashcat-case-study.html](docs/cashcat-case-study.html) | CASHCAT Phase 0 example |

Open locally: `xdg-open docs/index.html`

## Telegram

```bash
./test_telegram.sh
systemctl --user status crypto-watchers
journalctl --user -u crypto-watchers -f
```

## Commands

```bash
.venv/bin/python scanner.py scan
.venv/bin/python scanner.py analyze cash-cat
.venv/bin/python x_watcher.py once
.venv/bin/python chain_watcher.py once
```

## Config

Edit `config.yaml` — chains, X accounts, Elite gate thresholds, watchlist.

## Security

- Never commit `.env` (Telegram token)
- Regenerate bot token via [@BotFather](https://t.me/BotFather) if exposed

## License

Private use. Not financial advice.
