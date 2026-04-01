#!/usr/bin/env bash
set -euo pipefail

APP_NAME="fuetem-imager"
INSTALL_DIR="/usr/local/share/${APP_NAME}"
BIN_LINK="/usr/local/bin/${APP_NAME}"
DESKTOP_FILE="/usr/share/applications/${APP_NAME}.desktop"
ICON_DIR="/usr/share/icons/hicolor/scalable/apps"
ICON_FILE="${ICON_DIR}/${APP_NAME}.svg"

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ── Root check ───────────────────────────────────────────────────────────────

if [[ $EUID -ne 0 ]]; then
    err "This script must be run as root (use sudo)."
fi

# ── Detect distro ────────────────────────────────────────────────────────────

detect_distro() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        case "${ID:-}" in
            arch|manjaro|endeavouros|garuda|cachyos)
                echo "arch" ;;
            debian|ubuntu|linuxmint|pop|zorin|elementary)
                echo "debian" ;;
            fedora|rhel|centos|rocky|alma|nobara)
                echo "fedora" ;;
            *)
                # Check ID_LIKE as fallback
                case "${ID_LIKE:-}" in
                    *arch*)   echo "arch" ;;
                    *debian*) echo "debian" ;;
                    *fedora*|*rhel*) echo "fedora" ;;
                    *) echo "unknown" ;;
                esac
                ;;
        esac
    else
        echo "unknown"
    fi
}

DISTRO=$(detect_distro)
info "Detected distro family: ${BOLD}${DISTRO}${NC}"

if [[ "$DISTRO" == "unknown" ]]; then
    err "Unsupported distribution. Supported: Arch, Debian/Ubuntu, Fedora."
fi

# ── Install dependencies ─────────────────────────────────────────────────────

install_deps_arch() {
    local pkgs=()
    pacman -Qi python       &>/dev/null || pkgs+=(python)
    pacman -Qi python-pillow &>/dev/null || pkgs+=(python-pillow)
    pacman -Qi python-gobject &>/dev/null || pkgs+=(python-gobject)
    pacman -Qi gtk4         &>/dev/null || pkgs+=(gtk4)
    pacman -Qi libadwaita   &>/dev/null || pkgs+=(libadwaita)

    if [[ ${#pkgs[@]} -gt 0 ]]; then
        info "Installing missing packages: ${pkgs[*]}"
        pacman -S --noconfirm --needed "${pkgs[@]}"
    else
        ok "All dependencies already installed."
    fi
}

install_deps_debian() {
    local pkgs=()
    dpkg -s python3            &>/dev/null || pkgs+=(python3)
    dpkg -s python3-pil        &>/dev/null || pkgs+=(python3-pil)
    dpkg -s python3-gi         &>/dev/null || pkgs+=(python3-gi)
    dpkg -s gir1.2-gtk-4.0     &>/dev/null || pkgs+=(gir1.2-gtk-4.0)
    dpkg -s gir1.2-adw-1       &>/dev/null || pkgs+=(gir1.2-adw-1)
    dpkg -s libgtk-4-1         &>/dev/null || pkgs+=(libgtk-4-1)
    dpkg -s libadwaita-1-0     &>/dev/null || pkgs+=(libadwaita-1-0)

    if [[ ${#pkgs[@]} -gt 0 ]]; then
        info "Installing missing packages: ${pkgs[*]}"
        apt-get update -qq
        apt-get install -y "${pkgs[@]}"
    else
        ok "All dependencies already installed."
    fi
}

install_deps_fedora() {
    local pkgs=()
    rpm -q python3             &>/dev/null || pkgs+=(python3)
    rpm -q python3-pillow      &>/dev/null || pkgs+=(python3-pillow)
    rpm -q python3-gobject     &>/dev/null || pkgs+=(python3-gobject)
    rpm -q gtk4                &>/dev/null || pkgs+=(gtk4)
    rpm -q libadwaita          &>/dev/null || pkgs+=(libadwaita)

    if [[ ${#pkgs[@]} -gt 0 ]]; then
        info "Installing missing packages: ${pkgs[*]}"
        dnf install -y "${pkgs[@]}"
    else
        ok "All dependencies already installed."
    fi
}

info "Checking dependencies..."
case "$DISTRO" in
    arch)   install_deps_arch   ;;
    debian) install_deps_debian ;;
    fedora) install_deps_fedora ;;
esac

# ── Install application ─────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

info "Installing ${APP_NAME}..."

# Create install directory and copy app
mkdir -p "${INSTALL_DIR}"
cp "${SCRIPT_DIR}/fuetem-imager.py" "${INSTALL_DIR}/"
chmod 755 "${INSTALL_DIR}/fuetem-imager.py"

# Create launcher symlink
cat > "${BIN_LINK}" << 'LAUNCHER'
#!/usr/bin/env bash
exec python3 /usr/local/share/fuetem-imager/fuetem-imager.py "$@"
LAUNCHER
chmod 755 "${BIN_LINK}"

# Install icon
mkdir -p "${ICON_DIR}"
cp "${SCRIPT_DIR}/icons/fuetem-imager.svg" "${ICON_FILE}"
chmod 644 "${ICON_FILE}"

# Install desktop file
cat > "${DESKTOP_FILE}" << 'EOF'
[Desktop Entry]
Type=Application
Name=fuetem-imager
Comment=Image format and dimension converter
Exec=fuetem-imager
Icon=fuetem-imager
Categories=Utility;Graphics;
StartupNotify=false
Keywords=image;convert;resize;format;crop;watermark;
EOF
chmod 644 "${DESKTOP_FILE}"

# Update icon cache
if command -v gtk-update-icon-cache &>/dev/null; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor/ 2>/dev/null || true
fi

# Update desktop database
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database /usr/share/applications/ 2>/dev/null || true
fi

ok "${APP_NAME} installed successfully!"
echo ""
echo -e "  Run from terminal:  ${BOLD}fuetem-imager${NC}"
echo -e "  Or find it in your application launcher."
echo ""
