#!/usr/bin/env bash
set -euo pipefail

PURPLE='\033[0;35m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

say() {
  printf "${PURPLE}==>${NC} %s\n" "$1"
}

ok() {
  printf "${GREEN}OK${NC} %s\n" " $1"
}

warn() {
  printf "${YELLOW}WARN${NC} %s\n" " $1"
}

die() {
  printf "${RED}ERROR${NC} %s\n" " $1" >&2
  exit 1
}

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$SCRIPT_DIR/source"
LIVE_DIR="$SCRIPT_DIR/live-install"

[[ -d "$SOURCE_DIR/keystone_osk" ]] || die "Missing source directory: $SOURCE_DIR"
[[ -f "$LIVE_DIR/home-local-bin/keystone-osk" ]] || die "Missing launcher stub in live-install"

say "Restoring Keystone app"
mkdir -p "$HOME/.local/share/keystone-osk"
rsync -a --delete "$SOURCE_DIR/" "$HOME/.local/share/keystone-osk/"
ok "source restored to ~/.local/share/keystone-osk"

mkdir -p "$HOME/.local/bin"
install -m 755 "$LIVE_DIR/home-local-bin/keystone-osk" "$HOME/.local/bin/keystone-osk"
ok "launcher restored to ~/.local/bin/keystone-osk"

mkdir -p "$HOME/.local/share/applications"
desktop_file="$HOME/.local/share/applications/keystone-osk.desktop"
install -m 644 "$LIVE_DIR/applications/keystone-osk.desktop" "$desktop_file"
local_launcher="$HOME/.local/bin/keystone-osk"
desktop_tmp="$desktop_file.tmp"
sed \
  -e "s|^Exec=.*|Exec=$local_launcher|" \
  -e "s|^TryExec=.*|TryExec=$local_launcher|" \
  "$desktop_file" > "$desktop_tmp"
mv "$desktop_tmp" "$desktop_file"
ok "desktop launcher restored"

mkdir -p "$HOME/.local/share/icons/hicolor/256x256/apps"
install -m 644 "$LIVE_DIR/icons/hicolor/256x256/apps/keystone.png" \
  "$HOME/.local/share/icons/hicolor/256x256/apps/keystone.png"
install -m 644 "$LIVE_DIR/icons/hicolor/256x256/apps/keystone-transparent.png" \
  "$HOME/.local/share/icons/hicolor/256x256/apps/keystone-transparent.png"
ok "launcher icons restored"

if [[ -f "$LIVE_DIR/config/window-state.json" ]]; then
  mkdir -p "$HOME/.local/state/keystone-osk"
  install -m 644 "$LIVE_DIR/config/window-state.json" "$HOME/.local/state/keystone-osk/window-state.json"
  ok "window state restored"
fi

if ! command -v python3 >/dev/null 2>&1; then
  warn "python3 is missing"
fi
if ! command -v ydotool >/dev/null 2>&1; then
  warn "ydotool is missing"
fi
if ! python3 -c 'import PySide6' >/dev/null 2>&1; then
  warn "PySide6 is missing"
fi

gtk-update-icon-cache -q -t -f "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

ok "restore complete"
printf "${PURPLE}Run:${NC} keystone-osk\n"
