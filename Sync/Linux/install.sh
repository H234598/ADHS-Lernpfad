#!/usr/bin/env bash
set -Eeuo pipefail

BASE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$HOME/Dokumente/Obsidian/ADHS-Lernpfad"
SYNC_MODE="safe-pull"
DEVICE_BRANCH=""
BASE_BRANCH="main"
REPO_URL="https://github.com/H234598/ADHS-Lernpfad.git"
INTERVAL_MINUTES=30
SCHEDULER="systemd"
ADOPT_EXISTING=0

usage() {
  cat <<'EOF'
Verwendung: ./Sync/Linux/install.sh [Optionen]

  --target PFAD             Ziel-Vault
  --mode MODUS              safe-pull, prompt-pull, forced-pull,
                            additive-pull oder full-sync
  --device-branch BRANCH    eigener Branch für full-sync
  --branch BRANCH           Pull-Basisbranch, Standard main
  --repo-url URL            Git-Repository
  --interval-minutes N      systemd-Intervall, Standard 30
  --manual                  keinen systemd-Timer installieren
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
[[ "$INTERVAL_MINUTES" =~ ^[1-9][0-9]*$ ]] || {
  printf 'Ungültiges Intervall: %s\n' "$INTERVAL_MINUTES" >&2
  exit 64
}
if [[ "$SYNC_MODE" == full-sync && -z "$DEVICE_BRANCH" ]]; then
  printf 'full-sync benötigt --device-branch, z. B. sync/mein-laptop\n' >&2
  exit 64
fi

for command in bash git rsync install; do
  command -v "$command" >/dev/null 2>&1 || {
    printf 'Benötigtes Programm fehlt: %s\n' "$command" >&2
    exit 127
  }
done
if [[ "$SCHEDULER" == systemd ]]; then
  command -v systemctl >/dev/null 2>&1 || {
    printf 'systemctl fehlt; verwende --manual oder installiere systemd.\n' >&2
    exit 127
  }
fi

INSTALL_ROOT="$HOME/.local/share/adhs-lernpfad-sync"
BIN_FILE="$HOME/.local/bin/adhs-lernpfad-sync"
ENV_FILE="$HOME/.config/adhs-lernpfad-sync.env"
REPO_DIR="$INSTALL_ROOT/repo"
SERVICE_DIR="$HOME/.config/systemd/user"

install -Dm755 "$BASE_DIR/../Common/adhs-sync.sh" "$INSTALL_ROOT/lib/adhs-sync.sh"
install -Dm755 "$BASE_DIR/sync.sh" "$BIN_FILE"
mkdir -p "$HOME/.config"
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

if [[ "$SCHEDULER" == systemd ]]; then
  install -Dm644 "$BASE_DIR/systemd/adhs-lernpfad-sync.service" \
    "$SERVICE_DIR/adhs-lernpfad-sync.service"
  mkdir -p "$SERVICE_DIR"
  cat > "$SERVICE_DIR/adhs-lernpfad-sync.timer" <<EOF
[Unit]
Description=ADHS-Lernpfad regelmäßig synchronisieren

[Timer]
OnBootSec=2min
OnUnitActiveSec=${INTERVAL_MINUTES}min
RandomizedDelaySec=2min
Persistent=true

[Install]
WantedBy=timers.target
EOF
  systemctl --user daemon-reload
  systemctl --user enable --now adhs-lernpfad-sync.timer
fi

ADHS_SYNC_NONINTERACTIVE=0 "$BIN_FILE"

printf 'Installiert: %s\n' "$BIN_FILE"
printf 'Ziel: %s\n' "$TARGET_DIR"
printf 'Privater Checkout: %s\n' "$REPO_DIR"
printf 'Modus: %s\n' "$SYNC_MODE"
printf 'Zeitplaner: %s\n' "$SCHEDULER"
