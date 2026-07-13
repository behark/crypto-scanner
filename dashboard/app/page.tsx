import Link from "next/link";

export default function HomePage() {
  return (
    <div className="space-y-8">
      <header>
        <p className="text-xs uppercase tracking-widest text-accent2 font-semibold mb-2">Dashboard</p>
        <h1 className="font-serif text-4xl text-white mb-3">Crypto Scanner</h1>
        <p className="text-zinc-400 max-w-xl">
          Configure alerts from the browser. The 24/7 watchers still run on your machine via systemd — Vercel hosts this UI + config storage.
        </p>
      </header>

      <div className="grid md:grid-cols-3 gap-4">
        <div className="card">
          <p className="text-xs uppercase text-accent mb-2">Layer 1</p>
          <h3 className="font-serif text-lg mb-1">X watcher</h3>
          <p className="text-sm text-zinc-500">Every 2 min · alpha accounts · $cashtags</p>
        </div>
        <div className="card">
          <p className="text-xs uppercase text-accent mb-2">Layer 2</p>
          <h3 className="font-serif text-lg mb-1">Chain watcher</h3>
          <p className="text-sm text-zinc-500">Robinhood · BSC · Solana · Elite gate</p>
        </div>
        <div className="card">
          <p className="text-xs uppercase text-accent2 mb-2">Layer 3</p>
          <h3 className="font-serif text-lg mb-1">Scanner</h3>
          <p className="text-sm text-zinc-500">Hourly gainers · Binance OI · LAB signals</p>
        </div>
      </div>

      <div className="card border-accent/20 bg-gradient-to-br from-surface to-accent/5">
        <h2 className="font-serif text-xl mb-3">Architecture</h2>
        <pre className="text-xs text-zinc-400 font-mono leading-relaxed overflow-x-auto">{`Vercel (this dashboard)
  ├── Edit config → Vercel Blob
  └── Export config.yaml

Your PC / VPS (systemd)
  ├── crypto-watchers.service  → Telegram
  ├── crypto-scanner.service   → Telegram
  └── Pulls config from Blob OR local config.yaml`}</pre>
      </div>

      <div className="card">
        <h2 className="font-serif text-xl mb-3">Quick actions</h2>
        <div className="flex flex-wrap gap-3">
          <Link href="/config" className="btn-primary">Open config editor</Link>
          <Link href="/docs" className="btn-ghost">Learning guides</Link>
          <a
            href="https://github.com/behark/crypto-scanner"
            className="btn-ghost"
            target="_blank"
            rel="noreferrer"
          >
            GitHub repo
          </a>
        </div>
      </div>

      <div className="card border-warn/20">
        <h2 className="font-serif text-xl mb-2 text-warn">Vercel limits</h2>
        <p className="text-sm text-zinc-400">
          Serverless cannot replace 24/7 Python loops on the free tier. Use Vercel for <strong className="text-white">config + docs UI</strong>.
          Keep <code className="text-accent">crypto-watchers</code> running at home. Optional: move scanners to a $5 VPS later.
        </p>
      </div>
    </div>
  );
}
