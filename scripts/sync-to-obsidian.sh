#!/usr/bin/env bash
set -Eeuo pipefail
REPO_URL="${ADHS_LERNPFAD_REPO_URL:-https://github.com/H234598/ADHS-Lernpfad.git}"
BRANCH="${ADHS_LERNPFAD_BRANCH:-main}"
TARGET_DIR="${ADHS_LERNPFAD_TARGET_DIR:-$HOME/Dokumente/Obsidian/ADHS-Lernpfad}"
LOCK_FILE="${XDG_RUNTIME_DIR:-/tmp}/adhs-lernpfad-sync.lock"
log(){ printf '[%s] %s
' "$(date --iso-8601=seconds)" "$*"; }
command -v git >/dev/null || exit 127; command -v flock >/dev/null || exit 127
mkdir -p "$(dirname "$TARGET_DIR")"; exec 9>"$LOCK_FILE"; flock -n 9 || exit 0
if [[ ! -e "$TARGET_DIR" ]]; then git clone --branch "$BRANCH" --single-branch "$REPO_URL" "$TARGET_DIR"; exit 0; fi
[[ -d "$TARGET_DIR/.git" ]] || { log 'Ziel ist kein Git-Repository'; exit 2; }
cd "$TARGET_DIR"
[[ -z "$(git status --porcelain)" ]] || { log 'Lokale Änderungen: kein Überschreiben'; git status --short; exit 4; }
git fetch --prune origin "$BRANCH"; git switch "$BRANCH" >/dev/null; git merge --ff-only "origin/$BRANCH"
