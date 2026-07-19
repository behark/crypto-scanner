#!/usr/bin/env bash
# Copy repo docs into dashboard public folder before build (local monorepo).
# On Vercel only the dashboard/ directory is deployed — public/docs is committed there.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SRC="$ROOT/docs"
DEST="$(dirname "$0")/../public/docs"

if [[ ! -d "$SRC" ]]; then
  echo "copy-docs: $SRC not found — using committed public/docs"
  exit 0
fi

mkdir -p "$DEST"
cp -r "$SRC/." "$DEST/"
echo "copy-docs: synced $SRC -> $DEST"
