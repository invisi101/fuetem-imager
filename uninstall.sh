#!/usr/bin/env bash
set -euo pipefail

APP_NAME="fuetem-imager"

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

info() { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()   { echo -e "${GREEN}[OK]${NC}    $*"; }
err()  { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

if [[ $EUID -ne 0 ]]; then
    err "This script must be run as root (use sudo)."
fi

info "Uninstalling ${APP_NAME}..."

rm -rf "/usr/local/share/${APP_NAME}"
rm -f  "/usr/local/bin/${APP_NAME}"
rm -f  "/usr/share/applications/${APP_NAME}.desktop"
rm -f  "/usr/share/icons/hicolor/scalable/apps/${APP_NAME}.svg"

if command -v gtk-update-icon-cache &>/dev/null; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor/ 2>/dev/null || true
fi
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database /usr/share/applications/ 2>/dev/null || true
fi

ok "${APP_NAME} has been uninstalled."
