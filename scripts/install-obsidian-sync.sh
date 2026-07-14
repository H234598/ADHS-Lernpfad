#!/usr/bin/env bash
set -Eeuo pipefail
D="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"; V="${1:-$HOME/Dokumente/Obsidian}"; T="$V/ADHS-Lernpfad"
install -Dm755 "$D/scripts/sync-to-obsidian.sh" "$HOME/.local/bin/adhs-lernpfad-sync"
install -Dm644 "$D/systemd/adhs-lernpfad-sync.service" "$HOME/.config/systemd/user/adhs-lernpfad-sync.service"
install -Dm644 "$D/systemd/adhs-lernpfad-sync.timer" "$HOME/.config/systemd/user/adhs-lernpfad-sync.timer"
mkdir -p "$HOME/.config"; printf 'ADHS_LERNPFAD_REPO_URL=https://github.com/H234598/ADHS-Lernpfad.git
ADHS_LERNPFAD_BRANCH=main
ADHS_LERNPFAD_TARGET_DIR=%s
' "$T" > "$HOME/.config/adhs-lernpfad-sync.env"
systemctl --user daemon-reload; systemctl --user enable --now adhs-lernpfad-sync.timer; systemctl --user start adhs-lernpfad-sync.service
