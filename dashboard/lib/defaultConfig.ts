import type { ScannerConfig } from "./types";

export const defaultConfig: ScannerConfig = {
  scan: {
    interval_seconds: 3600,
    coingecko_per_page: 100,
    rate_limit_seconds: 1.2,
  },
  filters: {
    min_gain_24h_pct: 35,
    min_gain_7d_pct: 100,
    min_market_cap_usd: 500000,
    max_market_cap_usd: 500000000,
    min_volume_24h_usd: 500000,
  },
  signals: {
    oi_increase_pct: 25,
    vol_mcap_ratio_high: 0.45,
    vol_mcap_ratio_extreme: 0.8,
    price_drop_from_ath_pct: 25,
    alert_cooldown_hours: 4,
  },
  watchlist: ["cash-cat", "lab", "siren"],
  notifications: {
    desktop: true,
    console: true,
    log_file: "alerts.log",
    telegram: true,
  },
  chain_watcher: {
    enabled: true,
    poll_interval_seconds: 300,
    chains: ["robinhood", "bsc", "solana"],
    min_volume_h24_usd: 300000,
    volume_spike_multiplier: 2.5,
    new_token_profiles: true,
    quality_gate: {
      qualified_min_liquidity_usd: 25000,
      qualified_min_volume_h24_usd: 50000,
      qualified_min_buy_ratio: 0.52,
      watch_min_liquidity_usd: 8000,
      send_junk_alerts: false,
      send_watch_alerts: true,
    },
  },
  x_watcher: {
    enabled: true,
    poll_interval_seconds: 120,
    accounts: [
      "bubblemaps", "lookonchain", "EmberCN", "spotonchain", "zachxbt",
      "vladytenev", "BinanceWallet", "merts_eth", "ataberk", "boram992",
      "MemeRetire", "The__Solstice", "kilorippy", "favezy", "Tcalledpresence",
      "spunosounds", "BioStone_chad", "Stacco__", "fluffycrypt", "HBAcrypto",
      "Ansem", "binance", "DefiIgnas", "pentosh1",
    ],
    keywords: [
      "robinhood", "cashcat", "narrative", "aped", "culturally significant",
      "insider", "manipulation", "ugly", "cluster", "mainnet", "alpha", "gem",
      "stealth", "fair launch", "new chain", "green chain", "runner", "retirement",
    ],
    cashtag_min_length: 3,
    always_alert_accounts: [
      "bubblemaps", "lookonchain", "EmberCN", "spotonchain", "zachxbt",
      "vladytenev", "BinanceWallet",
    ],
  },
  paths: {
    state_file: "state.json",
    x_state_file: "x_state.json",
    chain_state_file: "chain_state.json",
    reports_dir: "reports",
  },
};
