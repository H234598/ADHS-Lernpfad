#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_ROOT="${ADHS_SYNC_INSTALL_ROOT:-$HOME/Library/Application Support/ADHS-Lernpfad-Sync}"
CONFIG_FILE="${ADHS_SYNC_CONFIG:-$INSTALL_ROOT/config.env}"

if [[ -x "$INSTALL_ROOT/lib/adhs-sync.sh" ]]; then
  ENGINE="$INSTALL_ROOT/lib/adhs-sync.sh"
else
  ENGINE="$SCRIPT_DIR/../Common/adhs-sync.sh"
fi

[[ -x "$ENGINE" ]] || {
  printf 'Sync-Engine nicht gefunden: %s\n' "$ENGINE" >&2
  exit 66
}

export ADHS_SYNC_CONFIG="$CONFIG_FILE"
exec "$ENGINE" "$@"
