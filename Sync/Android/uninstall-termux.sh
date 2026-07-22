#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

PURGE_CONFIG=0
REMOVE_CHECKOUT=0

while (( $# )); do
  case "$1" in
    --purge-config) PURGE_CONFIG=1; shift ;;
    --remove-checkout) REMOVE_CHECKOUT=1; shift ;;
    --help|-h)
      cat <<'EOF'
Verwendung: ./Sync/Android/uninstall-termux.sh [Optionen]
  --purge-config      Konfiguration entfernen
  --remove-checkout   privaten Git-Checkout entfernen
Der sichtbare Obsidian-Vault wird niemals gelöscht.
EOF
      exit 0
      ;;
    *) printf 'Unbekannte Option: %s\n' "$1" >&2; exit 64 ;;
  esac
done

rm -f \
  "$HOME/.local/bin/adhs-lernpfad-sync" \
  "$HOME/.termux/boot/adhs-lernpfad-sync"
rm -rf "$HOME/.local/share/adhs-lernpfad-sync/lib"

if (( PURGE_CONFIG )); then
  rm -f "$HOME/.config/adhs-lernpfad-sync.env"
fi
if (( REMOVE_CHECKOUT )); then
  rm -rf "$HOME/.local/share/adhs-lernpfad-sync/repo"
fi
rmdir "$HOME/.local/share/adhs-lernpfad-sync" 2>/dev/null || true

printf 'Termux-Sync entfernt. Der sichtbare Vault blieb unverändert.\n'
