#!/usr/bin/env bash
set -Eeuo pipefail

BASE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VAULT_ROOT="${1:-$HOME/Dokumente/Obsidian}"
SYNC_MODE="${2:-safe-pull}"
TARGET_DIR="$VAULT_ROOT/ADHS-Lernpfad"
ENV_FILE="$HOME/.config/adhs-lernpfad-sync.env"

case "$SYNC_MODE" in
  safe-pull|prompt-pull|forced-pull) ;;
  *)
    printf 'Nicht unterstützter Linux-Modus: %s\n' "$SYNC_MODE" >&2
    printf 'Erlaubt: safe-pull, prompt-pull, forced-pull\n' >&2
    exit 64
    ;;
esac

command -v systemctl >/dev/null 2>&1 || {
  printf 'systemctl fehlt; dieses Paket benötigt systemd.\n' >&2
  exit 127
}

install -Dm755 "$BASE_DIR/sync.sh" "$HOME/.local/bin/adhs-lernpfad-sync"
install -Dm644 \
  "$BASE_DIR/systemd/adhs-lernpfad-sync.service" \
  "$HOME/.config/systemd/user/adhs-lernpfad-sync.service"
install -Dm644 \
  "$BASE_DIR/systemd/adhs-lernpfad-sync.timer" \
  "$HOME/.config/systemd/user/adhs-lernpfad-sync.timer"

mkdir -p "$HOME/.config"
{
  printf 'ADHS_LERNPFAD_REPO_URL="https://github.com/H234598/ADHS-Lernpfad.git"\n'
  printf 'ADHS_LERNPFAD_BRANCH="main"\n'
  printf 'ADHS_LERNPFAD_TARGET_DIR="%s"\n' "${TARGET_DIR//\"/\\\"}"
  printf 'ADHS_LERNPFAD_SYNC_MODE="%s"\n' "$SYNC_MODE"
} > "$ENV_FILE"

systemctl --user daemon-reload
systemctl --user enable --now adhs-lernpfad-sync.timer
systemctl --user start adhs-lernpfad-sync.service

printf 'Installiert: %s\n' "$TARGET_DIR"
printf 'Modus: %s\n' "$SYNC_MODE"
printf 'Konfiguration: %s\n' "$ENV_FILE"
