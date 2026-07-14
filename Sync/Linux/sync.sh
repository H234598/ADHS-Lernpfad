#!/usr/bin/env bash
set -Eeuo pipefail

REPO_URL="${ADHS_LERNPFAD_REPO_URL:-https://github.com/H234598/ADHS-Lernpfad.git}"
BRANCH="${ADHS_LERNPFAD_BRANCH:-main}"
TARGET_DIR="${ADHS_LERNPFAD_TARGET_DIR:-$HOME/Dokumente/Obsidian/ADHS-Lernpfad}"
SYNC_MODE="${ADHS_LERNPFAD_SYNC_MODE:-safe-pull}"
LOCK_FILE="${XDG_RUNTIME_DIR:-/tmp}/adhs-lernpfad-sync.lock"

log() {
  printf '[%s] %s\n' "$(date --iso-8601=seconds)" "$*"
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    log "Benötigtes Programm fehlt: $1"
    exit 127
  }
}

ensure_local_excludes() {
  local exclude_file="$TARGET_DIR/.git/info/exclude"
  local pattern
  mkdir -p "$(dirname "$exclude_file")"
  touch "$exclude_file"
  for pattern in '.obsidian/' '.stfolder' '.stignore' '.nomedia' '.trash/'; do
    grep -qxF "$pattern" "$exclude_file" || printf '%s\n' "$pattern" >> "$exclude_file"
  done
}

has_local_changes() {
  [[ -n "$(git status --porcelain --untracked-files=all)" ]]
}

show_local_changes() {
  log 'Lokale Änderungen im Spiegel:'
  git status --short
}

force_to_remote() {
  git reset --hard "origin/$BRANCH"
  git clean -fd \
    -e '.obsidian/' \
    -e '.stfolder' \
    -e '.stignore' \
    -e '.nomedia' \
    -e '.trash/'
  git switch -C "$BRANCH" "origin/$BRANCH" >/dev/null
}

case "$SYNC_MODE" in
  safe-pull|prompt-pull|forced-pull) ;;
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
require_command flock
mkdir -p "$(dirname "$TARGET_DIR")"
exec 9>"$LOCK_FILE"
flock -n 9 || exit 0

if [[ ! -e "$TARGET_DIR" ]]; then
  git clone --branch "$BRANCH" --single-branch "$REPO_URL" "$TARGET_DIR"
  ensure_local_excludes
  log "Erstinstallation abgeschlossen: $TARGET_DIR"
  exit 0
fi

[[ -d "$TARGET_DIR/.git" ]] || {
  log 'Ziel ist kein Git-Repository'
  exit 2
}

cd "$TARGET_DIR"
ensure_local_excludes

if has_local_changes; then
  case "$SYNC_MODE" in
    safe-pull)
      show_local_changes
      log 'safe-pull bricht ab und überschreibt nichts'
      exit 4
      ;;
    prompt-pull)
      show_local_changes
      if [[ ! -t 0 ]]; then
        log 'prompt-pull benötigt ein Terminal; sicherer Abbruch'
        exit 4
      fi
      read -r -p 'Lokale Änderungen verwerfen und origin/main spiegeln? [y/N] ' answer
      [[ "$answer" =~ ^[Yy]$ ]] || {
        log 'Abgebrochen; lokale Änderungen bleiben erhalten'
        exit 4
      }
      ;;
    forced-pull) ;;
  esac
fi

git fetch --prune origin "$BRANCH"

if [[ "$SYNC_MODE" == 'forced-pull' ]] || has_local_changes; then
  force_to_remote
else
  git switch "$BRANCH" >/dev/null
  git merge --ff-only "origin/$BRANCH"
fi

log "Synchronisierung abgeschlossen: Modus=$SYNC_MODE Ziel=$TARGET_DIR"
