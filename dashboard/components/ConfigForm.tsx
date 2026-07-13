"use client";

import { useCallback, useEffect, useState } from "react";
import type { ScannerConfig } from "@/lib/types";
import { defaultConfig } from "@/lib/defaultConfig";
import { configToYaml, linesToList, listToLines } from "@/lib/yaml";

function getSecret(): string {
  if (typeof window === "undefined") return "";
  return sessionStorage.getItem("dashboard_secret") || "";
}

function ListField({
  label,
  value,
  onChange,
  rows = 6,
}: {
  label: string;
  value: string[];
  onChange: (v: string[]) => void;
  rows?: number;
}) {
  return (
    <div>
      <label>{label}</label>
      <textarea
        rows={rows}
        value={listToLines(value)}
        onChange={(e) => onChange(linesToList(e.target.value))}
      />
    </div>
  );
}

function NumField({
  label,
  value,
  onChange,
  step = 1,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  step?: number;
}) {
  return (
    <div>
      <label>{label}</label>
      <input
        type="number"
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
      />
    </div>
  );
}

export function ConfigForm() {
  const [config, setConfig] = useState<ScannerConfig>(defaultConfig);
  const [secret, setSecret] = useState("");
  const [status, setStatus] = useState("");
  const [blobEnabled, setBlobEnabled] = useState(false);

  const load = useCallback(async () => {
    const s = getSecret() || secret;
    const res = await fetch(`/api/config${s ? `?secret=${encodeURIComponent(s)}` : ""}`, {
      headers: s ? { "x-dashboard-secret": s } : {},
    });
    if (res.ok) {
      const data = await res.json();
      setConfig(data.config);
      setBlobEnabled(data.blobEnabled);
    }
  }, [secret]);

  useEffect(() => {
    const stored = sessionStorage.getItem("dashboard_secret");
    if (stored) setSecret(stored);
    load();
  }, [load]);

  const save = async () => {
    setStatus("Saving…");
    const s = secret || getSecret();
    if (s) sessionStorage.setItem("dashboard_secret", s);
    const res = await fetch("/api/config", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(s ? { "x-dashboard-secret": s } : {}),
      },
      body: JSON.stringify({ config }),
    });
    const data = await res.json();
    if (!res.ok) {
      setStatus(`Error: ${data.error}`);
      return;
    }
    setStatus(data.savedToBlob ? "Saved to Vercel Blob ✓" : "Generated YAML — download below");
    if (data.yaml) {
      const blob = new Blob([data.yaml], { type: "text/yaml" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "config.yaml";
      a.click();
    }
  };

  const c = config;
  const set = <K extends keyof ScannerConfig>(key: K, val: ScannerConfig[K]) =>
    setConfig((prev) => ({ ...prev, [key]: val }));

  return (
    <div className="space-y-6">
      <div className="card">
        <h2 className="font-serif text-xl mb-3">Access</h2>
        <p className="text-sm text-zinc-500 mb-3">
          Set <code className="text-accent">DASHBOARD_SECRET</code> on Vercel. Enter it here to save config remotely.
        </p>
        <input
          type="password"
          placeholder="Dashboard secret (optional locally)"
          value={secret}
          onChange={(e) => setSecret(e.target.value)}
        />
        {blobEnabled && <p className="text-xs text-accent mt-2">Vercel Blob connected</p>}
      </div>

      <div className="card space-y-4">
        <h2 className="font-serif text-xl">Chain watcher + Elite gate</h2>
        <div className="grid grid-cols-2 gap-4">
          <label className="flex items-center gap-2 col-span-2 text-sm text-zinc-300">
            <input
              type="checkbox"
              checked={c.chain_watcher.enabled}
              onChange={(e) =>
                set("chain_watcher", { ...c.chain_watcher, enabled: e.target.checked })
              }
            />
            Enabled
          </label>
          <NumField
            label="Poll interval (sec)"
            value={c.chain_watcher.poll_interval_seconds}
            onChange={(v) => set("chain_watcher", { ...c.chain_watcher, poll_interval_seconds: v })}
          />
          <NumField
            label="Min volume 24h ($)"
            value={c.chain_watcher.min_volume_h24_usd}
            onChange={(v) => set("chain_watcher", { ...c.chain_watcher, min_volume_h24_usd: v })}
          />
        </div>
        <ListField
          label="Chains (one per line)"
          value={c.chain_watcher.chains}
          onChange={(v) => set("chain_watcher", { ...c.chain_watcher, chains: v })}
          rows={3}
        />
        <div className="border-t border-white/10 pt-4 grid grid-cols-2 gap-4">
          <NumField
            label="ELITE min liquidity ($)"
            value={c.chain_watcher.quality_gate.qualified_min_liquidity_usd}
            onChange={(v) =>
              set("chain_watcher", {
                ...c.chain_watcher,
                quality_gate: { ...c.chain_watcher.quality_gate, qualified_min_liquidity_usd: v },
              })
            }
          />
          <NumField
            label="ELITE min volume 24h ($)"
            value={c.chain_watcher.quality_gate.qualified_min_volume_h24_usd}
            onChange={(v) =>
              set("chain_watcher", {
                ...c.chain_watcher,
                quality_gate: { ...c.chain_watcher.quality_gate, qualified_min_volume_h24_usd: v },
              })
            }
          />
          <NumField
            label="Min buy ratio (0.52 = 52%)"
            value={c.chain_watcher.quality_gate.qualified_min_buy_ratio}
            step={0.01}
            onChange={(v) =>
              set("chain_watcher", {
                ...c.chain_watcher,
                quality_gate: { ...c.chain_watcher.quality_gate, qualified_min_buy_ratio: v },
              })
            }
          />
          <NumField
            label="WATCH min liquidity ($)"
            value={c.chain_watcher.quality_gate.watch_min_liquidity_usd}
            onChange={(v) =>
              set("chain_watcher", {
                ...c.chain_watcher,
                quality_gate: { ...c.chain_watcher.quality_gate, watch_min_liquidity_usd: v },
              })
            }
          />
          <label className="flex items-center gap-2 text-sm text-zinc-300">
            <input
              type="checkbox"
              checked={c.chain_watcher.quality_gate.send_junk_alerts}
              onChange={(e) =>
                set("chain_watcher", {
                  ...c.chain_watcher,
                  quality_gate: { ...c.chain_watcher.quality_gate, send_junk_alerts: e.target.checked },
                })
              }
            />
            Send JUNK alerts (spam)
          </label>
          <label className="flex items-center gap-2 text-sm text-zinc-300">
            <input
              type="checkbox"
              checked={c.chain_watcher.quality_gate.send_watch_alerts}
              onChange={(e) =>
                set("chain_watcher", {
                  ...c.chain_watcher,
                  quality_gate: { ...c.chain_watcher.quality_gate, send_watch_alerts: e.target.checked },
                })
              }
            />
            Send WATCH alerts
          </label>
        </div>
      </div>

      <div className="card space-y-4">
        <h2 className="font-serif text-xl">X watcher</h2>
        <div className="grid grid-cols-2 gap-4">
          <label className="flex items-center gap-2 col-span-2 text-sm text-zinc-300">
            <input
              type="checkbox"
              checked={c.x_watcher.enabled}
              onChange={(e) => set("x_watcher", { ...c.x_watcher, enabled: e.target.checked })}
            />
            Enabled
          </label>
          <NumField
            label="Poll interval (sec)"
            value={c.x_watcher.poll_interval_seconds}
            onChange={(v) => set("x_watcher", { ...c.x_watcher, poll_interval_seconds: v })}
          />
          <NumField
            label="Cashtag min length"
            value={c.x_watcher.cashtag_min_length}
            onChange={(v) => set("x_watcher", { ...c.x_watcher, cashtag_min_length: v })}
          />
        </div>
        <ListField
          label="Accounts (no @)"
          value={c.x_watcher.accounts}
          onChange={(v) => set("x_watcher", { ...c.x_watcher, accounts: v })}
          rows={8}
        />
        <ListField
          label="Always alert (every post)"
          value={c.x_watcher.always_alert_accounts}
          onChange={(v) => set("x_watcher", { ...c.x_watcher, always_alert_accounts: v })}
          rows={4}
        />
        <ListField
          label="Keywords"
          value={c.x_watcher.keywords}
          onChange={(v) => set("x_watcher", { ...c.x_watcher, keywords: v })}
          rows={5}
        />
      </div>

      <div className="card space-y-4">
        <h2 className="font-serif text-xl">Scanner (hourly)</h2>
        <div className="grid grid-cols-2 gap-4">
          <NumField
            label="Min gain 24h %"
            value={c.filters.min_gain_24h_pct}
            onChange={(v) => set("filters", { ...c.filters, min_gain_24h_pct: v })}
          />
          <NumField
            label="Max market cap ($)"
            value={c.filters.max_market_cap_usd}
            onChange={(v) => set("filters", { ...c.filters, max_market_cap_usd: v })}
          />
          <NumField
            label="OI increase %"
            value={c.signals.oi_increase_pct}
            onChange={(v) => set("signals", { ...c.signals, oi_increase_pct: v })}
          />
          <NumField
            label="Vol/mcap exit"
            value={c.signals.vol_mcap_ratio_high}
            step={0.05}
            onChange={(v) => set("signals", { ...c.signals, vol_mcap_ratio_high: v })}
          />
        </div>
        <ListField
          label="Watchlist (CoinGecko ids)"
          value={c.watchlist}
          onChange={(v) => set("watchlist", v)}
          rows={3}
        />
      </div>

      <div className="flex flex-wrap gap-3 items-center">
        <button type="button" onClick={save} className="btn-primary">
          Save &amp; download config.yaml
        </button>
        <button
          type="button"
          className="btn-ghost"
          onClick={() => {
            const blob = new Blob([configToYaml(config)], { type: "text/yaml" });
            const a = document.createElement("a");
            a.href = URL.createObjectURL(blob);
            a.download = "config.yaml";
            a.click();
          }}
        >
          Export YAML only
        </button>
        <button type="button" className="btn-ghost" onClick={load}>
          Reload
        </button>
        {status && <span className="text-sm text-accent">{status}</span>}
      </div>

      <p className="text-xs text-zinc-600">
        After save: copy <code>config.yaml</code> to your scanner folder, or set{" "}
        <code>CONFIG_URL</code> on your machine to pull from Vercel (see dashboard README).
      </p>
    </div>
  );
}
