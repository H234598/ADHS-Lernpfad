#!/usr/bin/env bash
set -Eeuo pipefail

# Gemeinsame Synchronisationsengine für Linux, Android/Termux, macOS, BSD und iSH.
# Plattform-Wrapper setzen nur Standardpfade und laden eine Konfigurationsdatei.

CONFIG_FILE="${ADHS_SYNC_CONFIG:-}"
if [[ -n "$CONFIG_FILE" && -f "$CONFIG_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$CONFIG_FILE"
  set +a
fi

REPO_URL="${ADHS_SYNC_REPO_URL:-https://github.com/H234598/ADHS-Lernpfad.git}"
REMOTE="${ADHS_SYNC_REMOTE:-origin}"
BASE_BRANCH="${ADHS_SYNC_BASE_BRANCH:-main}"
REPO_DIR="${ADHS_SYNC_REPO_DIR:?ADHS_SYNC_REPO_DIR fehlt}"
TARGET_DIR="${ADHS_SYNC_TARGET_DIR:?ADHS_SYNC_TARGET_DIR fehlt}"
SYNC_MODE="${ADHS_SYNC_MODE:-safe-pull}"
DEVICE_BRANCH="${ADHS_SYNC_DEVICE_BRANCH:-}"
NONINTERACTIVE="${ADHS_SYNC_NONINTERACTIVE:-0}"
PROTECT_OBSIDIAN="${ADHS_SYNC_PROTECT_OBSIDIAN:-1}"
DISCARD_PENDING="${ADHS_SYNC_DISCARD_PENDING:-0}"
ADOPT_EXISTING_TARGET="${ADHS_SYNC_ADOPT_EXISTING_TARGET:-0}"
GIT_AUTHOR_NAME="${ADHS_SYNC_GIT_AUTHOR_NAME:-ADHS Sync}"
GIT_AUTHOR_EMAIL="${ADHS_SYNC_GIT_AUTHOR_EMAIL:-adhs-sync@localhost}"
STATE_FILE="${ADHS_SYNC_STATE_FILE:-$REPO_DIR/.git/adhs-sync-state}"

LOCK_KEY="$(printf '%s' "$TARGET_DIR" | cksum | awk '{print $1}')"
LOCK_DIR="${ADHS_SYNC_LOCK_DIR:-${TMPDIR:-/tmp}/adhs-lernpfad-sync-${UID:-$(id -u)}-${LOCK_KEY}.lock}"
DIFF_FILE=""

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$*"
}

die() {
  local status="$1"
  shift
  log "FEHLER: $*"
  exit "$status"
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die 127 "Benötigtes Programm fehlt: $1"
}

cleanup() {
  [[ -z "$DIFF_FILE" ]] || rm -f "$DIFF_FILE"
  rmdir "$LOCK_DIR" 2>/dev/null || true
}

acquire_lock() {
  mkdir -p "$(dirname "$LOCK_DIR")"
  if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    log 'Ein anderer Synchronisationslauf ist bereits aktiv'
    exit 0
  fi
  trap cleanup EXIT INT TERM
}

build_rsync_excludes() {
  RSYNC_EXCLUDES=("--exclude=.git/")
  if [[ "$PROTECT_OBSIDIAN" == 1 ]]; then
    RSYNC_EXCLUDES+=("--exclude=.obsidian/")
  fi
  RSYNC_EXCLUDES+=(
    "--exclude=.stfolder"
    "--exclude=.stignore"
    "--exclude=.nomedia"
    "--exclude=.trash/"
    "--exclude=.DS_Store"
    "--exclude=Thumbs.db"
    "--exclude=desktop.ini"
  )
  if [[ -n "${ADHS_SYNC_EXCLUDE_FILE:-}" ]]; then
    [[ -f "$ADHS_SYNC_EXCLUDE_FILE" ]] || die 66 "Exclude-Datei fehlt: $ADHS_SYNC_EXCLUDE_FILE"
    RSYNC_EXCLUDES+=("--exclude-from=$ADHS_SYNC_EXCLUDE_FILE")
  fi
}

validate_configuration() {
  case "$SYNC_MODE" in
    safe-pull|prompt-pull|forced-pull|additive-pull|full-sync) ;;
    *) die 64 "Unbekannter Modus: $SYNC_MODE" ;;
  esac

  [[ "$BASE_BRANCH" != -* && "$BASE_BRANCH" != *[[:space:]]* ]] \
    || die 64 "Ungültiger Basisbranch: $BASE_BRANCH"

  if [[ "$SYNC_MODE" == full-sync ]]; then
    [[ -n "$DEVICE_BRANCH" ]] || die 64 'full-sync benötigt ADHS_SYNC_DEVICE_BRANCH'
    [[ "$DEVICE_BRANCH" != "$BASE_BRANCH" ]] \
      || die 64 'Der Full-Sync-Gerätebranch darf nicht dem Basisbranch entsprechen'
    [[ "$DEVICE_BRANCH" != -* && "$DEVICE_BRANCH" != *[[:space:]]* ]] \
      || die 64 "Ungültiger Gerätebranch: $DEVICE_BRANCH"
  fi
}

ensure_checkout() {
  mkdir -p "$(dirname "$REPO_DIR")" "$(dirname "$TARGET_DIR")"
  if [[ -e "$REPO_DIR" && ! -d "$REPO_DIR/.git" ]]; then
    die 65 "Privater Checkoutpfad ist kein Git-Repository: $REPO_DIR"
  fi
  if [[ ! -d "$REPO_DIR/.git" ]]; then
    git clone --branch "$BASE_BRANCH" --single-branch "$REPO_URL" "$REPO_DIR"
  fi
  git -C "$REPO_DIR" remote get-url "$REMOTE" >/dev/null 2>&1 \
    || git -C "$REPO_DIR" remote add "$REMOTE" "$REPO_URL"
  git -C "$REPO_DIR" remote set-url "$REMOTE" "$REPO_URL"
  git -C "$REPO_DIR" config user.name "$GIT_AUTHOR_NAME"
  git -C "$REPO_DIR" config user.email "$GIT_AUTHOR_EMAIL"
}

reset_private_worktree() {
  git -C "$REPO_DIR" reset --hard >/dev/null
  git -C "$REPO_DIR" clean -fd >/dev/null
}

current_branch() {
  git -C "$REPO_DIR" symbolic-ref --quiet --short HEAD 2>/dev/null || true
}

pending_commits() {
  local branch upstream
  branch="$(current_branch)"
  [[ -n "$branch" ]] || { printf '0\n'; return; }
  upstream="$(git -C "$REPO_DIR" rev-parse --abbrev-ref '@{upstream}' 2>/dev/null || true)"
  [[ -n "$upstream" ]] || { printf '0\n'; return; }
  git -C "$REPO_DIR" rev-list --count "$upstream..HEAD"
}

check_pending_before_pull() {
  local ahead
  ahead="$(pending_commits)"
  if (( ahead > 0 )); then
    if [[ "$DISCARD_PENDING" == 1 && "$SYNC_MODE" == forced-pull ]]; then
      log "Verwerfe $ahead ausstehende Commit(s) im privaten Checkout auf ausdrückliche Konfiguration"
    else
      die 9 "$ahead nicht gepushte Commit(s) im privaten Checkout; zuerst Full Sync reparieren oder ADHS_SYNC_DISCARD_PENDING=1 mit forced-pull setzen"
    fi
  fi
}

compare_trees() {
  local source="$1" destination="$2" status
  [[ -d "$destination" ]] || return 1
  [[ -z "$DIFF_FILE" ]] || rm -f "$DIFF_FILE"
  DIFF_FILE="$(mktemp "${TMPDIR:-/tmp}/adhs-sync-diff.XXXXXX")"
  if rsync -rcn --delete --itemize-changes \
      "${RSYNC_EXCLUDES[@]}" \
      "$source/" "$destination/" >"$DIFF_FILE"; then
    if [[ -s "$DIFF_FILE" ]]; then
      return 0
    fi
    rm -f "$DIFF_FILE"
    DIFF_FILE=""
    return 1
  else
    status=$?
    die "$status" "rsync-Vergleich fehlgeschlagen"
  fi
}

show_differences() {
  [[ -n "$DIFF_FILE" && -s "$DIFF_FILE" ]] || return 0
  log 'Erkannte lokale Abweichungen:'
  sed 's/^/  /' "$DIFF_FILE"
}

confirm_overwrite() {
  local reason="$1" answer
  if [[ "$NONINTERACTIVE" == 1 || ! -t 0 ]]; then
    die 4 "Interaktive Bestätigung nicht möglich: $reason"
  fi
  printf '%s\n' "$reason"
  read -r -p 'Lokale Abweichungen verwerfen? [y/N] ' answer
  [[ "$answer" =~ ^[Yy]$ ]] || die 4 'Abgebrochen; lokale Dateien bleiben erhalten'
}

mirror_checkout_to_target() {
  mkdir -p "$TARGET_DIR"
  case "$SYNC_MODE" in
    additive-pull)
      rsync -a --ignore-existing "${RSYNC_EXCLUDES[@]}" "$REPO_DIR/" "$TARGET_DIR/"
      ;;
    *)
      rsync -a --delete-after "${RSYNC_EXCLUDES[@]}" "$REPO_DIR/" "$TARGET_DIR/"
      ;;
  esac
}

import_target_to_checkout() {
  rsync -a --delete-after "${RSYNC_EXCLUDES[@]}" "$TARGET_DIR/" "$REPO_DIR/"
}

target_has_syncable_files() {
  [[ -d "$TARGET_DIR" ]] || return 1
  find "$TARGET_DIR" \
    -type d \( -name .git -o -name .obsidian -o -name .trash \) -prune -o \
    -type f ! -name .stfolder ! -name .stignore ! -name .nomedia \
      ! -name .DS_Store ! -name Thumbs.db ! -name desktop.ini -print \
    | grep -q .
}

write_state() {
  mkdir -p "$(dirname "$STATE_FILE")"
  {
    printf 'mode=%s\n' "$SYNC_MODE"
    printf 'branch=%s\n' "$(current_branch)"
    printf 'commit=%s\n' "$(git -C "$REPO_DIR" rev-parse HEAD)"
    printf 'target=%s\n' "$TARGET_DIR"
    printf 'updated_at=%s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')"
  } > "$STATE_FILE"
}

run_pull_mode() {
  local target_changed=false
  check_pending_before_pull

  if [[ "$SYNC_MODE" != additive-pull ]] && compare_trees "$REPO_DIR" "$TARGET_DIR"; then
    target_changed=true
    show_differences
  fi

  case "$SYNC_MODE" in
    safe-pull)
      [[ "$target_changed" == false ]] || die 4 'safe-pull bricht ab und überschreibt nichts'
      ;;
    prompt-pull)
      [[ "$target_changed" == false ]] || confirm_overwrite 'Der Vault weicht vom letzten Spiegelstand ab.'
      ;;
    forced-pull|additive-pull) ;;
  esac

  reset_private_worktree
  git -C "$REPO_DIR" fetch --prune "$REMOTE" "$BASE_BRANCH"
  git -C "$REPO_DIR" switch -f -C "$BASE_BRANCH" "$REMOTE/$BASE_BRANCH" >/dev/null
  mirror_checkout_to_target
  write_state
  log "Synchronisierung abgeschlossen: Modus=$SYNC_MODE Branch=$BASE_BRANCH Ziel=$TARGET_DIR"
}

remote_device_branch_exists() {
  git -C "$REPO_DIR" ls-remote --exit-code --heads "$REMOTE" "$DEVICE_BRANCH" >/dev/null 2>&1
}

prepare_device_branch() {
  local remote_exists="$1"
  if git -C "$REPO_DIR" show-ref --verify --quiet "refs/heads/$DEVICE_BRANCH"; then
    git -C "$REPO_DIR" switch "$DEVICE_BRANCH" >/dev/null
  elif [[ "$remote_exists" == true ]]; then
    git -C "$REPO_DIR" switch -c "$DEVICE_BRANCH" --track "$REMOTE/$DEVICE_BRANCH" >/dev/null
  else
    git -C "$REPO_DIR" switch -c "$DEVICE_BRANCH" "$REMOTE/$BASE_BRANCH" >/dev/null
  fi
}

commit_target_changes() {
  import_target_to_checkout
  git -C "$REPO_DIR" add -A
  if git -C "$REPO_DIR" diff --cached --quiet; then
    log 'Keine versionierbaren Änderungen nach Import des Vaults'
    return 1
  fi
  git -C "$REPO_DIR" commit -m "Sync from device: $(hostname 2>/dev/null || printf device) $(date '+%Y-%m-%d %H:%M:%S %z')" >/dev/null
  return 0
}

push_device_branch() {
  if ! git -C "$REPO_DIR" push -u "$REMOTE" "HEAD:refs/heads/$DEVICE_BRANCH"; then
    die 8 "Push nach $DEVICE_BRANCH fehlgeschlagen; der lokale Commit bleibt im privaten Checkout erhalten"
  fi
}

run_full_sync() {
  local remote_exists=false target_changed=false ahead=0 behind=0

  reset_private_worktree
  git -C "$REPO_DIR" fetch --prune "$REMOTE" "$BASE_BRANCH"
  if remote_device_branch_exists; then
    remote_exists=true
    git -C "$REPO_DIR" fetch "$REMOTE" "$DEVICE_BRANCH:refs/remotes/$REMOTE/$DEVICE_BRANCH"
  fi
  prepare_device_branch "$remote_exists"

  if compare_trees "$REPO_DIR" "$TARGET_DIR"; then
    target_changed=true
  fi

  if [[ ! -f "$STATE_FILE" && "$target_changed" == true && "$ADOPT_EXISTING_TARGET" != 1 ]]; then
    show_differences
    die 6 'Vorhandener Vault weicht beim ersten Full-Sync-Lauf ab; zum bewussten Übernehmen ADHS_SYNC_ADOPT_EXISTING_TARGET=1 setzen'
  fi

  if [[ "$remote_exists" == true ]]; then
    ahead="$(git -C "$REPO_DIR" rev-list --count "$REMOTE/$DEVICE_BRANCH..HEAD")"
    behind="$(git -C "$REPO_DIR" rev-list --count "HEAD..$REMOTE/$DEVICE_BRANCH")"
  fi

  if (( ahead > 0 && behind > 0 )); then
    die 7 'Privater Checkout und Remote-Gerätebranch sind divergiert; manuelle Git-Auflösung erforderlich'
  fi

  if [[ "$target_changed" == true ]] && (( behind > 0 )); then
    show_differences
    die 7 'Vault und Remote-Gerätebranch wurden seit dem letzten gemeinsamen Stand geändert; kontrollierter Konfliktabbruch'
  fi

  if [[ "$target_changed" == false ]] && (( behind > 0 )); then
    git -C "$REPO_DIR" merge --ff-only "$REMOTE/$DEVICE_BRANCH" >/dev/null
    mirror_checkout_to_target
    write_state
    log "Full Sync: Remote-Gerätebranch nach lokal übernommen: $DEVICE_BRANCH"
    return
  fi

  if [[ "$target_changed" == true ]]; then
    show_differences
    commit_target_changes || true
    ahead="$(git -C "$REPO_DIR" rev-list --count "$REMOTE/$DEVICE_BRANCH..HEAD" 2>/dev/null || git -C "$REPO_DIR" rev-list --count "$REMOTE/$BASE_BRANCH..HEAD")"
  fi

  if [[ "$remote_exists" == false || "$ahead" -gt 0 ]]; then
    push_device_branch
  fi

  mirror_checkout_to_target
  write_state
  log "Full Sync abgeschlossen: Gerätebranch=$DEVICE_BRANCH Ziel=$TARGET_DIR"
}

main() {
  require_command git
  require_command rsync
  require_command cksum
  validate_configuration
  build_rsync_excludes
  acquire_lock
  ensure_checkout

  if [[ "$SYNC_MODE" == full-sync ]]; then
    run_full_sync
  else
    run_pull_mode
  fi
}

main "$@"
