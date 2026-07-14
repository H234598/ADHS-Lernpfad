#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

CONFIG_FILE="${ADHS_LERNPFAD_CONFIG:-$HOME/.config/adhs-lernpfad-sync.env}"
if [[ -f "$CONFIG_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$CONFIG_FILE"
  set +a
fi

REPO_URL="${ADHS_LERNPFAD_REPO_URL:-https://github.com/H234598/ADHS-Lernpfad.git}"
BRANCH="${ADHS_LERNPFAD_BRANCH:-main}"
REPO_DIR="${ADHS_LERNPFAD_REPO_DIR:-$HOME/.local/share/adhs-lernpfad/repo}"
TARGET_DIR="${ADHS_LERNPFAD_TARGET_DIR:-$HOME/storage/shared/Documents/Obsidian/ADHS-Lernpfad}"
SYNC_MODE="${ADHS_LERNPFAD_SYNC_MODE:-forced-pull}"
LOCK_DIR="${TMPDIR:-$HOME/.cache}/adhs-lernpfad-sync.lock"

RSYNC_EXCLUDES=(
  "--exclude=.git/"
  "--exclude=.obsidian/"
  "--exclude=.stfolder"
  "--exclude=.stignore"
  "--exclude=.nomedia"
  "--exclude=.trash/"
)

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$*"
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    log "Benötigtes Programm fehlt: $1"
    exit 127
  }
}

release_lock() {
  rmdir "$LOCK_DIR" 2>/dev/null || true
}

has_target_changes() {
  [[ -d "$TARGET_DIR" ]] || return 1
  local differences
  differences="$(
    rsync -rcn --delete --itemize-changes \
      "${RSYNC_EXCLUDES[@]}" \
      "$REPO_DIR/" "$TARGET_DIR/"
  )"
  [[ -n "$differences" ]]
}

show_target_changes() {
  log 'Lokale Abweichungen im Android-Vault:'
  rsync -rcn --delete --itemize-changes \
    "${RSYNC_EXCLUDES[@]}" \
    "$REPO_DIR/" "$TARGET_DIR/"
}

case "$SYNC_MODE" in
  safe-pull|prompt-pull|forced-pull|additive-pull) ;;
  full-sync)
    log 'full-sync ist noch nicht implementiert; siehe Sync/MODES.md'
    exit 64
    ;;
  *)
    log "Unbekannter Sync-Modus: $SYNC_MODE"
    exit 64
    ;;
esac

require_command git
require_command rsync
mkdir -p "$(dirname "$LOCK_DIR")"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  log 'Ein anderer Sync-Lauf ist bereits aktiv'
  exit 0
fi
trap release_lock EXIT

mkdir -p "$(dirname "$REPO_DIR")" "$(dirname "$TARGET_DIR")"

if [[ ! -d "$REPO_DIR/.git" ]]; then
  rm -rf "$REPO_DIR"
  git clone --branch "$BRANCH" --single-branch "$REPO_URL" "$REPO_DIR"
fi

if [[ "$SYNC_MODE" == 'safe-pull' || "$SYNC_MODE" == 'prompt-pull' ]]; then
  if has_target_changes; then
    show_target_changes
    if [[ "$SYNC_MODE" == 'safe-pull' ]]; then
      log 'safe-pull bricht ab und überschreibt nichts'
      exit 4
    fi
    if [[ ! -t 0 ]]; then
      log 'prompt-pull benötigt ein Terminal; sicherer Abbruch'
      exit 4
    fi
    read -r -p 'Lokale Vault-Abweichungen verwerfen und origin/main spiegeln? [y/N] ' answer
    [[ "$answer" =~ ^[Yy]$ ]] || {
      log 'Abgebrochen; lokale Dateien bleiben erhalten'
      exit 4
    }
  fi
fi

git -C "$REPO_DIR" fetch --prune origin "$BRANCH"
git -C "$REPO_DIR" reset --hard
git -C "$REPO_DIR" clean -fd
git -C "$REPO_DIR" switch -C "$BRANCH" "origin/$BRANCH" >/dev/null

mkdir -p "$TARGET_DIR"
if [[ "$SYNC_MODE" == 'additive-pull' ]]; then
  rsync -a --ignore-existing \
    "${RSYNC_EXCLUDES[@]}" \
    "$REPO_DIR/" "$TARGET_DIR/"
else
  rsync -a --delete-after \
    "${RSYNC_EXCLUDES[@]}" \
    "$REPO_DIR/" "$TARGET_DIR/"
fi

log "Synchronisierung abgeschlossen: Modus=$SYNC_MODE Ziel=$TARGET_DIR"
