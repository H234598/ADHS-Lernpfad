#!/usr/bin/env bash
set -Eeuo pipefail

BASE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$HOME/Documents/Obsidian/ADHS-Lernpfad"
SYNC_MODE="safe-pull"
DEVICE_BRANCH=""
BASE_BRANCH="main"
REPO_URL="https://github.com/H234598/ADHS-Lernpfad.git"
INTERVAL_MINUTES=30
SCHEDULER="launchd"
ADOPT_EXISTING=0

usage() {
  cat <<'EOF'
Verwendung: ./Sync/macOS/install.sh [Optionen]

  --target PFAD             Ziel-Vault
  --mode MODUS              safe-pull, prompt-pull, forced-pull,
                            additive-pull oder full-sync
  --device-branch BRANCH    eigener Branch für full-sync
  --branch BRANCH           Pull-Basisbranch, Standard main
  --repo-url URL            Git-Repository
  --interval-minutes N      LaunchAgent-Intervall, Standard 30
  --manual                  keinen LaunchAgent installieren
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
  printf 'full-sync benötigt --device-branch, z. B. sync/mein-mac\n' >&2
  exit 64
fi

for command in bash git rsync; do
  command -v "$command" >/dev/null 2>&1 || {
    printf 'Benötigtes Programm fehlt: %s\n' "$command" >&2
    [[ "$command" == git ]] && printf 'Installiere gegebenenfalls die Command Line Tools mit: xcode-select --install\n' >&2
    exit 127
  }
done
if [[ "$SCHEDULER" == launchd ]]; then
  command -v launchctl >/dev/null 2>&1 || { printf 'launchctl fehlt.\n' >&2; exit 127; }
fi

INSTALL_ROOT="$HOME/Library/Application Support/ADHS-Lernpfad-Sync"
REPO_DIR="$INSTALL_ROOT/repo"
BIN_DIR="$INSTALL_ROOT/bin"
BIN_FILE="$BIN_DIR/adhs-lernpfad-sync"
CONFIG_FILE="$INSTALL_ROOT/config.env"
PLIST="$HOME/Library/LaunchAgents/org.telacore.adhs-lernpfad-sync.plist"
LOG_FILE="$HOME/Library/Logs/ADHS-Lernpfad-Sync.log"
INTERVAL_SECONDS=$(( INTERVAL_MINUTES * 60 ))

mkdir -p "$INSTALL_ROOT/lib" "$BIN_DIR" "$(dirname "$PLIST")" "$(dirname "$LOG_FILE")"
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
} > "$CONFIG_FILE"
chmod 600 "$CONFIG_FILE"

xml_escape() {
  local value="$1"
  value="${value//&/&amp;}"
  value="${value//</&lt;}"
  value="${value//>/&gt;}"
  value="${value//\"/&quot;}"
  value="${value//\'/&apos;}"
  printf '%s' "$value"
}

if [[ "$SCHEDULER" == launchd ]]; then
  cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>org.telacore.adhs-lernpfad-sync</string>
  <key>ProgramArguments</key>
  <array>
    <string>$(xml_escape "$BIN_FILE")</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>ADHS_SYNC_NONINTERACTIVE</key>
    <string>1</string>
  </dict>
  <key>RunAtLoad</key>
  <true/>
  <key>StartInterval</key>
  <integer>$INTERVAL_SECONDS</integer>
  <key>ProcessType</key>
  <string>Background</string>
  <key>LowPriorityIO</key>
  <true/>
  <key>StandardOutPath</key>
  <string>$(xml_escape "$LOG_FILE")</string>
  <key>StandardErrorPath</key>
  <string>$(xml_escape "$LOG_FILE")</string>
</dict>
</plist>
EOF
  plutil -lint "$PLIST" >/dev/null
  launchctl bootout "gui/$UID" "$PLIST" 2>/dev/null || true
  launchctl bootstrap "gui/$UID" "$PLIST"
fi

ADHS_SYNC_NONINTERACTIVE=0 "$BIN_FILE"

printf 'Installiert: %s\n' "$BIN_FILE"
printf 'Ziel: %s\n' "$TARGET_DIR"
printf 'Privater Checkout: %s\n' "$REPO_DIR"
printf 'Modus: %s\n' "$SYNC_MODE"
printf 'Zeitplaner: %s\n' "$SCHEDULER"
