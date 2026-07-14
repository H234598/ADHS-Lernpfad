#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

BASE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$HOME/storage/shared/Documents/Obsidian/ADHS-Lernpfad"
SYNC_MODE="forced-pull"
DEVICE_BRANCH=""
BASE_BRANCH="main"
REPO_URL="https://github.com/H234598/ADHS-Lernpfad.git"
START_MODE="manual"
ADOPT_EXISTING=0

usage() {
  cat <<'EOF'
Verwendung: ./Sync/Android/install-termux.sh [Optionen]

  --target PFAD             Ziel-Vault im Android-Speicher
  --mode MODUS              safe-pull, prompt-pull, forced-pull,
                            additive-pull oder full-sync
  --device-branch BRANCH    eigener Branch für full-sync
  --branch BRANCH           Pull-Basisbranch, Standard main
  --repo-url URL            Git-Repository
  --boot                    Startskript für Termux:Boot anlegen
  --manual                  nur manuelle Ausführung
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
    --boot) START_MODE="boot"; shift ;;
    --manual) START_MODE="manual"; shift ;;
    --adopt-existing-target) ADOPT_EXISTING=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) printf 'Unbekannte Option: %s\n' "$1" >&2; usage >&2; exit 64 ;;
  esac
done

case "$SYNC_MODE" in
  safe-pull|prompt-pull|forced-pull|additive-pull|full-sync) ;;
  *) printf 'Nicht unterstützter Modus: %s\n' "$SYNC_MODE" >&2; exit 64 ;;
esac
if [[ "$SYNC_MODE" == full-sync && -z "$DEVICE_BRANCH" ]]; then
  printf 'full-sync benötigt --device-branch, z. B. sync/mein-tablet\n' >&2
  exit 64
fi

command -v pkg >/dev/null 2>&1 || {
  printf 'Dieses Installationsskript ist für Termux vorgesehen.\n' >&2
  exit 127
}
pkg install -y git rsync

if [[ ! -d "$HOME/storage/shared" ]]; then
  printf 'Android-Speicher ist noch nicht freigegeben.\n' >&2
  printf 'Bitte zuerst termux-setup-storage ausführen und den Zugriff erlauben.\n' >&2
  exit 2
fi

INSTALL_ROOT="$HOME/.local/share/adhs-lernpfad-sync"
REPO_DIR="$INSTALL_ROOT/repo"
BIN_FILE="$HOME/.local/bin/adhs-lernpfad-sync"
ENV_FILE="$HOME/.config/adhs-lernpfad-sync.env"
BOOT_FILE="$HOME/.termux/boot/adhs-lernpfad-sync"

mkdir -p "$INSTALL_ROOT/lib" "$HOME/.local/bin" "$HOME/.config"
cp "$BASE_DIR/../Common/adhs-sync.sh" "$INSTALL_ROOT/lib/adhs-sync.sh"
cp "$BASE_DIR/sync-termux.sh" "$BIN_FILE"
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

if [[ "$START_MODE" == boot ]]; then
  mkdir -p "$(dirname "$BOOT_FILE")"
  {
    printf '%s\n' '#!/data/data/com.termux/files/usr/bin/bash'
    printf '%s\n' 'sleep 60'
    printf 'ADHS_SYNC_NONINTERACTIVE=1 exec %q\n' "$BIN_FILE"
  } > "$BOOT_FILE"
  chmod 700 "$BOOT_FILE"
else
  rm -f "$BOOT_FILE"
fi

ADHS_SYNC_NONINTERACTIVE=0 "$BIN_FILE"

printf 'Installiert: %s\n' "$BIN_FILE"
printf 'Ziel: %s\n' "$TARGET_DIR"
printf 'Privater Checkout: %s\n' "$REPO_DIR"
printf 'Modus: %s\n' "$SYNC_MODE"
printf 'Start: %s\n' "$START_MODE"
printf 'Manueller Befehl: adhs-lernpfad-sync\n'
