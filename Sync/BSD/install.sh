#!/usr/bin/env bash
set -Eeuo pipefail

BASE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$HOME/Obsidian/ADHS-Lernpfad"
SYNC_MODE="safe-pull"
DEVICE_BRANCH=""
BASE_BRANCH="main"
REPO_URL="https://github.com/H234598/ADHS-Lernpfad.git"
INTERVAL_MINUTES=30
SCHEDULER="cron"
ADOPT_EXISTING=0

usage() {
  cat <<'EOF'
Verwendung: ./Sync/BSD/install.sh [Optionen]

  --target PFAD             Ziel-Vault
  --mode MODUS              safe-pull, prompt-pull, forced-pull,
                            additive-pull oder full-sync
  --device-branch BRANCH    eigener Branch für full-sync
  --branch BRANCH           Pull-Basisbranch, Standard main
  --repo-url URL            Git-Repository
  --interval-minutes N      Cron-Intervall von 1 bis 59, Standard 30
  --manual                  keinen Cronjob installieren
  --adopt-existing-target   vorhandenen Vault beim ersten Full Sync übernehmen
  --help                    Hilfe anzeigen
EOF
}

while (( $# )); do
  case "$1" in
    --target) TARGET_DIR="${2:?Pfad fehlt}"; shift 2 ;;
    --mode) SYNC_MODE="${2:?Modus fehlt}"; shift 2 ;;
    --device-branch) DEVICE_BRANCH="${2:?Branch fehlt}"; shift 2 ;;
    --branch) BASE_BRANCH="${2:?Branch fehlt}"; shift 2 ;;
    --repo-url) REPO_URL="${2:?URL fehlt}"; shift 2 ;;
    --interval-minutes) INTERVAL_MINUTES="${2:?Intervall fehlt}"; shift 2 ;;
    --manual) SCHEDULER="manual"; shift ;;
    --adopt-existing-target) ADOPT_EXISTING=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) printf 'Unbekannte Option: %s\n' "$1" >&2; usage >&2; exit 64 ;;
  esac
done

case "$SYNC_MODE" in
  safe-pull|prompt-pull|forced-pull|additive-pull|full-sync) ;;
  *) printf 'Nicht unterstützter Modus: %s\n' "$SYNC_MODE" >&2; exit 64 ;;
esac
[[ "$INTERVAL_MINUTES" =~ ^[1-9][0-9]*$ ]] && (( INTERVAL_MINUTES <= 59 )) || {
  printf 'Cron-Intervall muss zwischen 1 und 59 Minuten liegen.\n' >&2
  exit 64
}
if [[ "$SYNC_MODE" == full-sync && -z "$DEVICE_BRANCH" ]]; then
  printf 'full-sync benötigt --device-branch, z. B. sync/mein-bsd-host\n' >&2
  exit 64
fi

missing=()
for command in bash git rsync; do
  command -v "$command" >/dev/null 2>&1 || missing+=("$command")
done
if (( ${#missing[@]} )); then
  printf 'Benötigte Programme fehlen: %s\n' "${missing[*]}" >&2
  case "$(uname -s)" in
    FreeBSD) printf 'Beispiel: sudo pkg install bash git rsync\n' >&2 ;;
    OpenBSD) printf 'Beispiel: doas pkg_add bash git rsync\n' >&2 ;;
    NetBSD) printf 'Beispiel: sudo pkgin install bash git-base rsync\n' >&2 ;;
  esac
  exit 127
fi
if [[ "$SCHEDULER" == cron ]] && ! command -v crontab >/dev/null 2>&1; then
  printf 'crontab fehlt; verwende --manual oder installiere cron.\n' >&2
  exit 127
fi

INSTALL_ROOT="$HOME/.local/share/adhs-lernpfad-sync"
REPO_DIR="$INSTALL_ROOT/repo"
BIN_FILE="$HOME/.local/bin/adhs-lernpfad-sync"
ENV_FILE="$HOME/.config/adhs-lernpfad-sync.env"
LOG_FILE="$HOME/.local/state/adhs-lernpfad-sync.log"
CRON_MARKER='# ADHS-Lernpfad-Sync'

mkdir -p "$INSTALL_ROOT/lib" "$HOME/.local/bin" "$HOME/.config" "$(dirname "$LOG_FILE")"
cp "$BASE_DIR/../Common/adhs-sync.sh" "$INSTALL_ROOT/lib/adhs-sync.sh"
cp "$BASE_DIR/sync.sh" "$BIN_FILE"
chmod 700 "$INSTALL_ROOT/lib/adhs-sync.sh" "$BIN_FILE"

{
  printf 'ADHS_SYNC_REPO_URL=%q\n' "$REPO_URL"
  printf 'ADHS_SYNC_REMOTE=%q\n' origin
  printf 'ADHS_SYNC_BASE_BRANCH=%q\n' "$BASE_BRANCH"
  printf 'ADHS_SYNC_REPO_DIR=%q\n' "$REPO_DIR"
  printf 'ADHS_SYNC_TARGET_DIR=%q\n' "$TARGET_DIR"
  printf 'ADHS_SYNC_MODE=%q\n' "$SYNC_MODE"
  printf 'ADHS_SYNC_DEVICE_BRANCH=%q\n' "$DEVICE_BRANCH"
  printf 'ADHS_SYNC_PROTECT_OBSIDIAN=%q\n' 1
  printf 'ADHS_SYNC_ADOPT_EXISTING_TARGET=%q\n' "$ADOPT_EXISTING"
} > "$ENV_FILE"
chmod 600 "$ENV_FILE"

if [[ "$SCHEDULER" == cron ]]; then
  TMP_CRON="$(mktemp "${TMPDIR:-/tmp}/adhs-cron.XXXXXX")"
  trap 'rm -f "$TMP_CRON"' EXIT
  crontab -l 2>/dev/null | grep -vF "$CRON_MARKER" > "$TMP_CRON" || true
  printf '*/%s * * * * ADHS_SYNC_NONINTERACTIVE=1 %q >> %q 2>&1 %s\n' \
    "$INTERVAL_MINUTES" "$BIN_FILE" "$LOG_FILE" "$CRON_MARKER" >> "$TMP_CRON"
  crontab "$TMP_CRON"
  rm -f "$TMP_CRON"
  trap - EXIT
fi

ADHS_SYNC_NONINTERACTIVE=0 "$BIN_FILE"

printf 'Installiert: %s\n' "$BIN_FILE"
printf 'Ziel: %s\n' "$TARGET_DIR"
printf 'Privater Checkout: %s\n' "$REPO_DIR"
printf 'Modus: %s\n' "$SYNC_MODE"
printf 'Zeitplaner: %s\n' "$SCHEDULER"
