#!/usr/bin/env bash
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
TARGET_DIR="${ADHS_LERNPFAD_TARGET_DIR:-$HOME/Dokumente/Obsidian/ADHS-Lernpfad}"
SYNC_MODE="${ADHS_LERNPFAD_SYNC_MODE:-safe-pull}"
LOCK_FILE="${XDG_RUNTIME_DIR:-/tmp}/adhs-lernpfad-sync-${UID:-$(id -u)}.lock"
NEEDS_FORCE=false
FORCE_CONFIRMED=false

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

has_worktree_changes() {
  [[ -n "$(git status --porcelain --untracked-files=all)" ]]
}

show_worktree_changes() {
  log 'Lokale Dateiänderungen im Spiegel:'
  git status --short
}

confirm_force() {
  local reason="$1"
  if [[ "$FORCE_CONFIRMED" == true ]]; then
    NEEDS_FORCE=true
    return
  fi
  if [[ ! -t 0 ]]; then
    log "prompt-pull benötigt ein Terminal; sicherer Abbruch: $reason"
    exit 4
  fi
  printf '%s\n' "$reason"
  read -r -p 'Lokalen Stand verwerfen und origin/main spiegeln? [y/N] ' answer
  [[ "$answer" =~ ^[Yy]$ ]] || {
    log 'Abgebrochen; lokaler Stand bleibt erhalten'
    exit 4
  }
  FORCE_CONFIRMED=true
  NEEDS_FORCE=true
}

force_to_remote() {
  git switch -f -C "$BRANCH" "origin/$BRANCH" >/dev/null
  git clean -fd \
    -e '.obsidian/' \
    -e '.stfolder' \
    -e '.stignore' \
    -e '.nomedia' \
    -e '.trash/'
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

if has_worktree_changes; then
  case "$SYNC_MODE" in
    safe-pull)
      show_worktree_changes
      log 'safe-pull bricht ab und überschreibt nichts'
      exit 4
      ;;
    prompt-pull)
      show_worktree_changes
      confirm_force 'Lokale Dateiänderungen wurden erkannt.'
      ;;
    forced-pull)
      NEEDS_FORCE=true
      ;;
  esac
fi

git fetch --prune origin "$BRANCH"

if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  LOCAL_AHEAD="$(git rev-list --count "origin/$BRANCH..$BRANCH")"
else
  LOCAL_AHEAD=0
fi

if (( LOCAL_AHEAD > 0 )); then
  case "$SYNC_MODE" in
    safe-pull)
      log "Lokaler Branch enthält $LOCAL_AHEAD nicht veröffentlichte Commit(s); sicherer Abbruch"
      exit 5
      ;;
    prompt-pull)
      confirm_force "Lokaler Branch enthält $LOCAL_AHEAD nicht veröffentlichte Commit(s)."
      ;;
    forced-pull)
      NEEDS_FORCE=true
      ;;
  esac
fi

if [[ "$NEEDS_FORCE" == true ]]; then
  force_to_remote
else
  if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
    git switch "$BRANCH" >/dev/null
    git merge --ff-only "origin/$BRANCH"
  else
    git switch -c "$BRANCH" --track "origin/$BRANCH" >/dev/null
  fi
fi

log "Synchronisierung abgeschlossen: Modus=$SYNC_MODE Ziel=$TARGET_DIR"
