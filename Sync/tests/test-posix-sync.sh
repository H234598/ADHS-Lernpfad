#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
ENGINE="$ROOT/Sync/Common/adhs-sync.sh"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/adhs-sync-test.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT

export GIT_AUTHOR_NAME='Sync Test'
export GIT_AUTHOR_EMAIL='sync-test@example.invalid'
export GIT_COMMITTER_NAME="$GIT_AUTHOR_NAME"
export GIT_COMMITTER_EMAIL="$GIT_AUTHOR_EMAIL"

fail() {
  printf 'TEST FEHLGESCHLAGEN: %s\n' "$*" >&2
  exit 1
}

assert_file_contains() {
  local file="$1" expected="$2"
  [[ -f "$file" ]] || fail "Datei fehlt: $file"
  grep -qF "$expected" "$file" || fail "$file enthält nicht: $expected"
}

assert_exit() {
  local expected="$1"
  shift
  set +e
  "$@"
  local status=$?
  set -e
  [[ "$status" -eq "$expected" ]] || fail "Erwarteter Exit $expected, erhalten $status: $*"
}

REMOTE="$TMP_ROOT/remote.git"
SEED="$TMP_ROOT/seed"
git init --bare "$REMOTE" >/dev/null
git init "$SEED" >/dev/null
git -C "$SEED" config user.name "$GIT_AUTHOR_NAME"
git -C "$SEED" config user.email "$GIT_AUTHOR_EMAIL"
printf 'version 1\n' > "$SEED/README.md"
mkdir -p "$SEED/01-Grundlagen"
printf 'Kapitel 1\n' > "$SEED/01-Grundlagen/01.md"
git -C "$SEED" add -A
git -C "$SEED" commit -m 'Initial' >/dev/null
git -C "$SEED" branch -M main
git -C "$SEED" remote add origin "$REMOTE"
git -C "$SEED" push -u origin main >/dev/null
git --git-dir="$REMOTE" symbolic-ref HEAD refs/heads/main

run_sync() {
  local repo_dir="$1" target_dir="$2" mode="$3" device_branch="${4:-}"
  ADHS_SYNC_REPO_URL="$REMOTE" \
  ADHS_SYNC_REPO_DIR="$repo_dir" \
  ADHS_SYNC_TARGET_DIR="$target_dir" \
  ADHS_SYNC_BASE_BRANCH=main \
  ADHS_SYNC_MODE="$mode" \
  ADHS_SYNC_DEVICE_BRANCH="$device_branch" \
  ADHS_SYNC_NONINTERACTIVE=1 \
  ADHS_SYNC_GIT_AUTHOR_NAME="$GIT_AUTHOR_NAME" \
  ADHS_SYNC_GIT_AUTHOR_EMAIL="$GIT_AUTHOR_EMAIL" \
  "$ENGINE"
}

PULL_REPO="$TMP_ROOT/pull-repo"
PULL_TARGET="$TMP_ROOT/pull-target"
run_sync "$PULL_REPO" "$PULL_TARGET" forced-pull
assert_file_contains "$PULL_TARGET/README.md" 'version 1'

mkdir -p "$PULL_TARGET/.obsidian"
printf '{"theme":"local"}\n' > "$PULL_TARGET/.obsidian/appearance.json"
printf 'lokale Änderung\n' > "$PULL_TARGET/README.md"
assert_exit 4 run_sync "$PULL_REPO" "$PULL_TARGET" safe-pull
assert_file_contains "$PULL_TARGET/README.md" 'lokale Änderung'

printf 'version 2\n' > "$SEED/README.md"
printf 'remote neu\n' > "$SEED/remote-new.md"
git -C "$SEED" add -A
git -C "$SEED" commit -m 'Remote update' >/dev/null
git -C "$SEED" push origin main >/dev/null

run_sync "$PULL_REPO" "$PULL_TARGET" forced-pull
assert_file_contains "$PULL_TARGET/README.md" 'version 2'
assert_file_contains "$PULL_TARGET/.obsidian/appearance.json" 'local'

printf 'lokal behalten\n' > "$PULL_TARGET/README.md"
printf 'noch neuer Remote-Inhalt\n' > "$SEED/additive.md"
git -C "$SEED" add additive.md
git -C "$SEED" commit -m 'Additive update' >/dev/null
git -C "$SEED" push origin main >/dev/null
run_sync "$PULL_REPO" "$PULL_TARGET" additive-pull
assert_file_contains "$PULL_TARGET/README.md" 'lokal behalten'
assert_file_contains "$PULL_TARGET/additive.md" 'noch neuer Remote-Inhalt'

printf 'prompt lokal\n' > "$PULL_TARGET/README.md"
assert_exit 4 run_sync "$PULL_REPO" "$PULL_TARGET" prompt-pull

FULL_REPO="$TMP_ROOT/full-repo"
FULL_TARGET="$TMP_ROOT/full-target"
DEVICE_BRANCH='sync/test-device'
run_sync "$FULL_REPO" "$FULL_TARGET" full-sync "$DEVICE_BRANCH"
assert_file_contains "$FULL_TARGET/README.md" 'version 2'

git --git-dir="$REMOTE" show-ref --verify --quiet "refs/heads/$DEVICE_BRANCH" \
  || fail 'Gerätebranch wurde nicht erzeugt'
printf 'lokale Full-Sync-Notiz\n' > "$FULL_TARGET/device-note.md"
run_sync "$FULL_REPO" "$FULL_TARGET" full-sync "$DEVICE_BRANCH"
git --git-dir="$REMOTE" show "$DEVICE_BRANCH:device-note.md" | grep -qF 'lokale Full-Sync-Notiz' \
  || fail 'Full-Sync-Änderung wurde nicht gepusht'

REMOTE_EDIT="$TMP_ROOT/remote-edit"
git clone --branch "$DEVICE_BRANCH" "$REMOTE" "$REMOTE_EDIT" >/dev/null
git -C "$REMOTE_EDIT" config user.name "$GIT_AUTHOR_NAME"
git -C "$REMOTE_EDIT" config user.email "$GIT_AUTHOR_EMAIL"
printf 'entfernte Änderung\n' > "$REMOTE_EDIT/remote-device.md"
git -C "$REMOTE_EDIT" add remote-device.md
git -C "$REMOTE_EDIT" commit -m 'Remote device change' >/dev/null
git -C "$REMOTE_EDIT" push origin "$DEVICE_BRANCH" >/dev/null
printf 'gleichzeitige lokale Änderung\n' > "$FULL_TARGET/local-conflict.md"
assert_exit 7 run_sync "$FULL_REPO" "$FULL_TARGET" full-sync "$DEVICE_BRANCH"
assert_file_contains "$FULL_TARGET/local-conflict.md" 'gleichzeitige lokale Änderung'

printf 'Alle POSIX-Sync-Integrationstests erfolgreich.\n'
