#!/usr/bin/env bash
set -Eeuo pipefail

PURGE_CONFIG=0
REMOVE_CHECKOUT=0
CRON_MARKER='# ADHS-Lernpfad-Sync'

while (( $# )); do
  case "$1" in
    --purge-config) PURGE_CONFIG=1; shift ;;
    --remove-checkout) REMOVE_CHECKOUT=1; shift ;;
    --help|-h)
      cat <<'EOF'
Verwendung: ./Sync/BSD/uninstall.sh [Optionen]
  --purge-config      Konfiguration entfernen
  --remove-checkout   privaten Git-Checkout entfernen
Der Obsidian-Vault wird niemals gelöscht.
EOF
      exit 0
      ;;
    *) printf 'Unbekannte Option: %s\n' "$1" >&2; exit 64 ;;
  esac
done

if command -v crontab >/dev/null 2>&1; then
  TMP_CRON="$(mktemp "${TMPDIR:-/tmp}/adhs-cron.XXXXXX")"
  crontab -l 2>/dev/null | grep -vF "$CRON_MARKER" > "$TMP_CRON" || true
  crontab "$TMP_CRON"
  rm -f "$TMP_CRON"
fi

rm -f "$HOME/.local/bin/adhs-lernpfad-sync"
rm -rf "$HOME/.local/share/adhs-lernpfad-sync/lib"
if (( PURGE_CONFIG )); then
  rm -f "$HOME/.config/adhs-lernpfad-sync.env"
fi
if (( REMOVE_CHECKOUT )); then
  rm -rf "$HOME/.local/share/adhs-lernpfad-sync/repo"
fi
rmdir "$HOME/.local/share/adhs-lernpfad-sync" 2>/dev/null || true

printf 'BSD-Sync entfernt. Der Vault blieb unverändert.\n'
