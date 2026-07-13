export interface ScannerConfig {
  scan: {
    interval_seconds: number;
    coingecko_per_page: number;
    rate_limit_seconds: number;
  };
  filters: {
    min_gain_24h_pct: number;
    min_gain_7d_pct: number;
    min_market_cap_usd: number;
    max_market_cap_usd: number;
    min_volume_24h_usd: number;
  };
  signals: {
    oi_increase_pct: number;
    vol_mcap_ratio_high: number;
    vol_mcap_ratio_extreme: number;
    price_drop_from_ath_pct: number;
    alert_cooldown_hours: number;
  };
  watchlist: string[];
  notifications: {
    desktop: boolean;
    console: boolean;
    log_file: string;
    telegram: boolean;
  };
  chain_watcher: {
    enabled: boolean;
    poll_interval_seconds: number;
    chains: string[];
    min_volume_h24_usd: number;
    volume_spike_multiplier: number;
    new_token_profiles: boolean;
    quality_gate: {
      qualified_min_liquidity_usd: number;
      qualified_min_volume_h24_usd: number;
      qualified_min_buy_ratio: number;
      watch_min_liquidity_usd: number;
      send_junk_alerts: boolean;
      send_watch_alerts: boolean;
    };
  };
  x_watcher: {
    enabled: boolean;
    poll_interval_seconds: number;
    accounts: string[];
    keywords: string[];
    cashtag_min_length: number;
    always_alert_accounts: string[];
  };
  paths: {
    state_file: string;
    x_state_file: string;
    chain_state_file: string;
    reports_dir: string;
  };
}
