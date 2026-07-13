# Dashboard — Vercel deployment

Beautiful config UI for the crypto scanner. **Does not replace** local systemd watchers.

## Deploy to Vercel

1. Push repo to GitHub (already done)
2. [vercel.com](https://vercel.com) → Import `behark/crypto-scanner`
3. Set **Root Directory** → `dashboard`
4. Environment variables:

| Variable | Required | Purpose |
|----------|----------|---------|
| `DASHBOARD_SECRET` | Recommended | Password to save config via API |
| `BLOB_READ_WRITE_TOKEN` | Optional | Persist config on Vercel (enable Blob store in project) |

5. Deploy

## Local dev

```bash
cd dashboard
npm install
npm run dev
# open http://localhost:3000
```

## Sync config to your scanner

**Option A — Manual (simplest)**  
Configure in dashboard → Save → downloads `config.yaml` → copy to scanner root → `systemctl --user restart crypto-watchers`

**Option B — Remote pull**  
After deploy, set on your machine in `.env`:

```
CONFIG_URL=https://your-app.vercel.app/api/config?format=yaml&secret=YOUR_SECRET
```

Watchers reload config each cycle (see `config_loader.py`).

## What runs where

| Component | Vercel | Your PC |
|-----------|--------|---------|
| Dashboard UI | ✓ | |
| Config storage (Blob) | ✓ | |
| X watcher 24/7 | | ✓ systemd |
| Chain watcher | | ✓ systemd |
| Telegram alerts | | ✓ |

## Docs

Guides are served from `/docs/` (copied to `public/docs` at build).

To refresh after editing repo docs:

```bash
cp -r ../docs public/docs
```
