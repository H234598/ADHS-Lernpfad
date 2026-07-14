#!/usr/bin/env bash
set -Eeuo pipefail

PURGE_CONFIG=0
REMOVE_CHECKOUT=0

usage() {
  cat <<'EOF'
Verwendung: ./Sync/Linux/uninstall.sh [Optionen]

  --purge-config      Konfigurationsdatei entfernen
  --remove-checkout   privaten Git-Checkout entfernen
  --help              Hilfe anzeigen

Der Obsidian-Vault wird niemals gelöscht.
EOF
}

while (( $# )); do
  case "$1" in
    --purge-config) PURGE_CONFIG=1; shift ;;
    --remove-checkout) REMOVE_CHECKOUT=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) printf 'Unbekannte Option: %s\n' "$1" >&2; exit 64 ;;
  esac
done

if command -v systemctl >/dev/null 2>&1; then
  systemctl --user disable --now adhs-lernpfad-sync.timer 2>/dev/null || true
  systemctl --user stop adhs-lernpfad-sync.service 2>/dev/null || true
fi

rm -f \
  "$HOME/.config/systemd/user/adhs-lernpfad-sync.service" \
  "$HOME/.config/systemd/user/adhs-lernpfad-sync.timer" \
  "$HOME/.local/bin/adhs-lernpfad-sync"
rm -rf "$HOME/.local/share/adhs-lernpfad-sync/lib"

if (( PURGE_CONFIG )); then
  rm -f "$HOME/.config/adhs-lernpfad-sync.env"
fi
if (( REMOVE_CHECKOUT )); then
  rm -rf "$HOME/.local/share/adhs-lernpfad-sync/repo"
fi
rmdir "$HOME/.local/share/adhs-lernpfad-sync" 2>/dev/null || true

if command -v systemctl >/dev/null 2>&1; then
  systemctl --user daemon-reload
fi

printf 'Linux-Sync entfernt. Der Vault blieb unverändert.\n'
