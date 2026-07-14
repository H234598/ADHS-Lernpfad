#!/usr/bin/env bash
set -Eeuo pipefail

PURGE_CONFIG=0
REMOVE_CHECKOUT=0

while (( $# )); do
  case "$1" in
    --purge-config) PURGE_CONFIG=1; shift ;;
    --remove-checkout) REMOVE_CHECKOUT=1; shift ;;
    --help|-h)
      cat <<'EOF'
Verwendung: ./Sync/macOS/uninstall.sh [Optionen]
  --purge-config      Konfiguration entfernen
  --remove-checkout   privaten Git-Checkout entfernen
Der Obsidian-Vault wird niemals gelöscht.
EOF
      exit 0
      ;;
    *) printf 'Unbekannte Option: %s\n' "$1" >&2; exit 64 ;;
  esac
done

INSTALL_ROOT="$HOME/Library/Application Support/ADHS-Lernpfad-Sync"
PLIST="$HOME/Library/LaunchAgents/org.telacore.adhs-lernpfad-sync.plist"

if command -v launchctl >/dev/null 2>&1; then
  launchctl bootout "gui/$UID" "$PLIST" 2>/dev/null || true
fi
rm -f "$PLIST" "$INSTALL_ROOT/bin/adhs-lernpfad-sync"
rm -rf "$INSTALL_ROOT/lib"

if (( PURGE_CONFIG )); then
  rm -f "$INSTALL_ROOT/config.env"
fi
if (( REMOVE_CHECKOUT )); then
  rm -rf "$INSTALL_ROOT/repo"
fi
rmdir "$INSTALL_ROOT/bin" 2>/dev/null || true
rmdir "$INSTALL_ROOT" 2>/dev/null || true

printf 'macOS-Sync entfernt. Der Vault blieb unverändert.\n'
