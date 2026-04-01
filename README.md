# fuetem-imager

A GTK4/Libadwaita image converter with format conversion, resizing, transforms, watermarking, and batch processing.

## Features

### Edit Mode

- **Open images** via file chooser, drag & drop, or recent files list
- **Preview** with switchable background (dark, checkerboard, light) for inspecting transparency, plus a before/after toggle to compare against the original
- **Image info** panel showing format, dimensions, file size, color mode, bit depth, DPI, and expandable EXIF metadata viewer
- **Transform** — rotate (90 CW, 90 CCW, 180), flip (horizontal, vertical), center crop with ratio presets (1:1, 4:3, 3:2, 16:9, 9:16, 3:4, 2:3), and color space conversion (RGB, Grayscale, RGBA)
- **Resize** — set exact pixel dimensions with aspect ratio lock, apply percentage scaling (25%–400%), or pick from presets (HD, Full HD, 2K, 4K, common icon sizes, social media dimensions)
- **Output options** — choose output format (PNG, JPEG, BMP, TIFF, ICO, WebP, AVIF), adjust quality for lossy formats, set a background color to replace transparency (JPEG/BMP), adjust output DPI, strip EXIF metadata, and see an estimated output file size
- **Watermark** — add text watermarks with configurable font size, opacity, color, and position (center or any corner)
- **Undo** — up to 20 levels of undo for all transforms
- **Save** as a new file or **copy to clipboard**

### Batch Mode

- Add multiple images at once
- Set a common output format, optional resize dimensions, quality, and EXIF stripping
- Choose an output directory or save alongside originals
- Progress bar tracks conversion

## Installation

### Quick Install

```bash
git clone https://github.com/invisi101/fuetem-imager.git
cd fuetem-imager
sudo ./install.sh
```

The install script automatically detects your distribution and installs any missing dependencies.

**Supported distributions:** Arch (and derivatives like Manjaro, EndeavourOS, CachyOS), Debian/Ubuntu (and derivatives like Linux Mint, Pop!_OS), Fedora (and derivatives like Nobara).

### Uninstall

```bash
sudo ./uninstall.sh
```

### Manual Dependency Install

If you prefer to install dependencies yourself:

**Arch Linux:**
```bash
sudo pacman -S python python-pillow python-gobject gtk4 libadwaita
```

**Debian / Ubuntu:**
```bash
sudo apt install python3 python3-pil python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 libgtk-4-1 libadwaita-1-0
```

**Fedora:**
```bash
sudo dnf install python3 python3-pillow python3-gobject gtk4 libadwaita
```

Then run directly:
```bash
python3 fuetem-imager.py
```

## Usage

After installation, launch from the terminal:

```bash
fuetem-imager
```

Or find **fuetem-imager** in your desktop application launcher.

## License

MIT
