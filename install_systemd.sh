#!/usr/bin/env bash
# Install user systemd services (no sudo required)
set -e
cd "$(dirname "$0")"
USER_UNIT_DIR="${HOME}/.config/systemd/user"
mkdir -p "$USER_UNIT_DIR"

cp systemd/crypto-watchers.service "$USER_UNIT_DIR/"
cp systemd/crypto-scanner.service "$USER_UNIT_DIR/"

systemctl --user daemon-reload
systemctl --user enable crypto-watchers.service
systemctl --user enable crypto-scanner.service

# Run services even when not logged in (optional but recommended)
if loginctl show-user "$USER" -p Linger 2>/dev/null | grep -q "no"; then
  echo ""
  echo "Enabling linger so services start at boot without login..."
  echo "(may ask for your password once)"
  sudo loginctl enable-linger "$USER" || echo "Skip linger — services run only while logged in"
fi

systemctl --user restart crypto-watchers.service
systemctl --user restart crypto-scanner.service

echo ""
echo "Installed and started:"
systemctl --user status crypto-watchers.service --no-pager -l | head -12
echo ""
echo "Useful commands:"
echo "  systemctl --user status crypto-watchers   # Phase 0 (X + chain)"
echo "  systemctl --user status crypto-scanner    # Hourly scanner"
echo "  journalctl --user -u crypto-watchers -f   # live logs"
echo "  systemctl --user stop crypto-watchers"
