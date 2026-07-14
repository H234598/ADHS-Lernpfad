#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

BASE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VAULT_ROOT="${1:-$HOME/storage/shared/Documents/Obsidian}"
SYNC_MODE="${2:-forced-pull}"
START_MODE="${3:-manual}"
TARGET_DIR="$VAULT_ROOT/ADHS-Lernpfad"
REPO_DIR="$HOME/.local/share/adhs-lernpfad/repo"
ENV_FILE="$HOME/.config/adhs-lernpfad-sync.env"
BIN_FILE="$HOME/.local/bin/adhs-lernpfad-sync"

case "$SYNC_MODE" in
  safe-pull|prompt-pull|forced-pull|additive-pull) ;;
  *)
    printf 'Nicht unterstützter Android-Modus: %s\n' "$SYNC_MODE" >&2
    printf 'Erlaubt: safe-pull, prompt-pull, forced-pull, additive-pull\n' >&2
    exit 64
    ;;
esac

case "$START_MODE" in
  manual|boot) ;;
  *)
    printf 'Drittes Argument muss manual oder boot sein.\n' >&2
    exit 64
    ;;
esac

if command -v pkg >/dev/null 2>&1; then
  pkg install -y git rsync
fi

if [[ ! -d "$HOME/storage/shared" ]]; then
  printf 'Android-Speicher ist noch nicht freigegeben.\n' >&2
  printf 'Bitte zuerst termux-setup-storage ausführen und den Zugriff erlauben.\n' >&2
  exit 2
fi

install -Dm755 "$BASE_DIR/sync-termux.sh" "$BIN_FILE"
mkdir -p "$HOME/.config"
{
  printf 'ADHS_LERNPFAD_REPO_URL=%q\n' 'https://github.com/H234598/ADHS-Lernpfad.git'
  printf 'ADHS_LERNPFAD_BRANCH=%q\n' 'main'
  printf 'ADHS_LERNPFAD_REPO_DIR=%q\n' "$REPO_DIR"
  printf 'ADHS_LERNPFAD_TARGET_DIR=%q\n' "$TARGET_DIR"
  printf 'ADHS_LERNPFAD_SYNC_MODE=%q\n' "$SYNC_MODE"
} > "$ENV_FILE"

if [[ "$START_MODE" == 'boot' ]]; then
  BOOT_FILE="$HOME/.termux/boot/adhs-lernpfad-sync"
  mkdir -p "$(dirname "$BOOT_FILE")"
  {
    printf '%s\n' '#!/data/data/com.termux/files/usr/bin/bash'
    printf '%s\n' 'sleep 60'
    printf 'exec %q\n' "$BIN_FILE"
  } > "$BOOT_FILE"
  chmod 700 "$BOOT_FILE"
fi

"$BIN_FILE"

printf 'Installiert: %s\n' "$TARGET_DIR"
printf 'Privater Checkout: %s\n' "$REPO_DIR"
printf 'Modus: %s\n' "$SYNC_MODE"
printf 'Start: %s\n' "$START_MODE"
printf 'Manueller Befehl: adhs-lernpfad-sync\n'
