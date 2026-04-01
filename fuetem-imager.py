#!/usr/bin/env python3
"""fuetem-imager — Image format, dimension, and transform converter."""

import io
import json
import os
import tempfile
import threading
from copy import deepcopy
from pathlib import Path

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib, GdkPixbuf, Gdk

from PIL import Image, ImageDraw, ImageFont, ExifTags


# ── Constants ────────────────────────────────────────────────────────────────

SAVE_FORMATS = ['png', 'jpeg', 'bmp', 'tiff', 'ico', 'webp', 'avif']

DIMENSION_PRESETS = {
    'HD 1280x720':      (1280, 720),
    'Full HD 1920x1080': (1920, 1080),
    '2K 2560x1440':     (2560, 1440),
    '4K 3840x2160':     (3840, 2160),
    'Square 512x512':   (512, 512),
    'Square 1024x1024': (1024, 1024),
    'Icon 16x16':       (16, 16),
    'Icon 32x32':       (32, 32),
    'Icon 48x48':       (48, 48),
    'Icon 64x64':       (64, 64),
    'Icon 128x128':     (128, 128),
    'Icon 256x256':     (256, 256),
    'Icon 512x512':     (512, 512),
    'Instagram 1080x1080': (1080, 1080),
    'Twitter Banner 1500x500': (1500, 500),
    'Facebook Cover 820x312': (820, 312),
}

CROP_RATIOS = {
    'Free':   None,
    '1:1':    (1, 1),
    '4:3':    (4, 3),
    '3:2':    (3, 2),
    '16:9':   (16, 9),
    '9:16':   (9, 16),
    '3:4':    (3, 4),
    '2:3':    (2, 3),
}

SCALE_PRESETS = ['25%', '50%', '75%', '100%', '125%', '150%', '200%', '300%', '400%']

WATERMARK_POSITIONS = ['Center', 'Top-Left', 'Top-Right', 'Bottom-Left', 'Bottom-Right']

MAX_UNDO = 20

RECENT_FILE = Path.home() / '.config' / 'fuetem-imager' / 'recent.json'
MAX_RECENT = 10


# ── CSS (same neon theme as DD-Imager) ───────────────────────────────────────

CUSTOM_CSS = """
/* ==== fuetem-imager Neon Theme ==== */

@define-color accent_bg_color #818cf8;
@define-color accent_fg_color #ffffff;
@define-color accent_color #a5b4fc;
@define-color window_bg_color #0f0f23;
@define-color view_bg_color #141428;
@define-color card_bg_color #1a1a2e;
@define-color headerbar_bg_color #12122a;
@define-color headerbar_fg_color #e0e0ff;
@define-color popover_bg_color #1a1a2e;
@define-color dialog_bg_color #1a1a2e;

window.background {
    background-image:
        radial-gradient(ellipse at 50% 20%, alpha(#818cf8, 0.06) 0%, transparent 70%),
        linear-gradient(180deg, #0f0f23, #12122e);
}

headerbar {
    background-image: linear-gradient(180deg, #1a1a2e, #12122a);
    border-bottom: 1px solid alpha(#818cf8, 0.2);
    box-shadow: 0 1px 8px alpha(#000000, 0.5);
}

headerbar .title {
    color: #e0e0ff;
    font-weight: bold;
    letter-spacing: 0.5px;
}

headerbar button { color: #c4c4f0; }
headerbar button:hover {
    color: #e0e0ff;
    background-color: alpha(#818cf8, 0.15);
}

button.suggested-action {
    background-image: linear-gradient(135deg, #f472b6, #818cf8);
    color: #ffffff;
    border: none;
    box-shadow: 0 2px 10px alpha(#f472b6, 0.35);
    text-shadow: 0 1px 2px alpha(#000000, 0.3);
    font-weight: 600;
    transition: all 200ms ease;
}
button.suggested-action:hover {
    background-image: linear-gradient(135deg, #f9a8d4, #a5b4fc);
    box-shadow: 0 2px 20px alpha(#f472b6, 0.6);
}
button.suggested-action:active {
    background-image: linear-gradient(135deg, #ec4899, #6366f1);
}

button.destructive-action {
    background-image: linear-gradient(135deg, #ef4444, #b91c1c);
    border: none;
    box-shadow: 0 2px 10px alpha(#ef4444, 0.35);
    font-weight: 600;
    transition: all 200ms ease;
}
button.destructive-action:hover {
    box-shadow: 0 2px 20px alpha(#ef4444, 0.6);
    background-image: linear-gradient(135deg, #f87171, #dc2626);
}

button.pill {
    border: 1px solid alpha(#818cf8, 0.3);
    transition: all 200ms ease;
}
button.pill:hover {
    border-color: alpha(#818cf8, 0.6);
    box-shadow: 0 0 10px alpha(#818cf8, 0.2);
}

button.flat { color: #c4c4f0; }
button.flat:hover {
    color: #e0e0ff;
    background-color: alpha(#818cf8, 0.12);
}

entry, spinbutton {
    background-color: #16213e;
    border: 1px solid #2d2d5e;
    color: #e0e0ff;
    border-radius: 8px;
    caret-color: #818cf8;
    transition: all 200ms ease;
}
entry:focus, spinbutton:focus {
    border-color: #818cf8;
    box-shadow: 0 0 10px alpha(#818cf8, 0.35);
}

.card {
    background-color: #1a1a2e;
    border: 1px solid alpha(#818cf8, 0.15);
    border-radius: 12px;
    box-shadow: 0 4px 12px alpha(#000000, 0.3);
}

.title-1 {
    color: #e0e0ff;
    font-weight: 800;
    letter-spacing: 0.3px;
}
.title-2 { color: #c4c4f0; font-weight: 700; }
.heading { color: #f472b6; font-weight: 600; }
.dim-label { color: alpha(#c4c4f0, 0.5); }
.success { color: #34d399; font-weight: 600; }
.error { color: #f87171; font-weight: 600; }
.warning { color: #fbbf24; font-weight: 600; }

separator {
    background-color: alpha(#818cf8, 0.12);
    min-height: 1px;
}

scrollbar slider {
    background-color: alpha(#818cf8, 0.25);
    border-radius: 4px;
    min-width: 6px;
}
scrollbar slider:hover { background-color: alpha(#818cf8, 0.45); }

dialog { background-color: #1a1a2e; }

.info-card {
    background-color: #1a1a2e;
    border: 1px solid alpha(#818cf8, 0.15);
    border-radius: 12px;
    padding: 20px;
}

.info-label {
    color: alpha(#c4c4f0, 0.6);
    font-size: 12px;
    font-weight: 500;
}
.info-value {
    color: #e0e0ff;
    font-weight: 600;
    font-size: 14px;
}

.preview-frame {
    background-color: #141428;
    border: 1px solid alpha(#818cf8, 0.1);
    border-radius: 8px;
    padding: 8px;
}

.preview-checker {
    background-image:
        linear-gradient(45deg, #222244 25%, transparent 25%),
        linear-gradient(-45deg, #222244 25%, transparent 25%),
        linear-gradient(45deg, transparent 75%, #222244 75%),
        linear-gradient(-45deg, transparent 75%, #222244 75%);
    background-size: 20px 20px;
    background-position: 0 0, 0 10px, 10px -10px, -10px 0px;
    border: 1px solid alpha(#818cf8, 0.1);
    border-radius: 8px;
    padding: 8px;
}

.preview-light {
    background-color: #e0e0e0;
    border: 1px solid alpha(#818cf8, 0.1);
    border-radius: 8px;
    padding: 8px;
}

.section-heading {
    color: #f472b6;
    font-weight: 600;
    font-size: 15px;
    margin-top: 8px;
}

checkbutton { color: #c4c4f0; }
switch:checked { background-image: linear-gradient(135deg, #34d399, #06b6d4); }

dropdown button {
    background-color: #16213e;
    border: 1px solid #2d2d5e;
    color: #e0e0ff;
    border-radius: 8px;
    transition: all 200ms ease;
}
dropdown button:hover { border-color: alpha(#818cf8, 0.4); }
dropdown button:focus {
    border-color: #818cf8;
    box-shadow: 0 0 10px alpha(#818cf8, 0.35);
}

scale trough {
    background-color: #1a1a2e;
    border: 1px solid #2d2d5e;
    border-radius: 6px;
    min-height: 8px;
}
scale trough highlight {
    background-image: linear-gradient(90deg, #34d399, #06b6d4, #818cf8);
    border-radius: 6px;
}
scale slider {
    background-image: linear-gradient(135deg, #f472b6, #818cf8);
    border: none;
    box-shadow: 0 0 6px alpha(#f472b6, 0.4);
    min-width: 18px;
    min-height: 18px;
    border-radius: 9px;
}

/* Transform button row */
.transform-btn {
    background-color: #16213e;
    border: 1px solid #2d2d5e;
    color: #c4c4f0;
    font-weight: 600;
    padding: 8px 14px;
    border-radius: 8px;
    transition: all 200ms ease;
}
.transform-btn:hover {
    background-color: alpha(#818cf8, 0.15);
    border-color: alpha(#818cf8, 0.4);
    color: #e0e0ff;
}

/* Batch list */
.batch-row {
    background-color: #1a1a2e;
    border-bottom: 1px solid alpha(#818cf8, 0.08);
    padding: 8px 12px;
}

/* EXIF row */
.exif-key { color: #818cf8; font-weight: 600; font-size: 12px; }
.exif-val { color: #c4c4f0; font-size: 12px; }

/* View switcher */
viewswitcher button:checked {
    background-image: linear-gradient(135deg, alpha(#f472b6, 0.2), alpha(#818cf8, 0.2));
}

/* Estimated size label */
.est-size {
    color: #06b6d4;
    font-weight: 600;
    font-size: 13px;
}

/* Color button frame */
.color-btn {
    border: 1px solid #2d2d5e;
    border-radius: 6px;
    min-width: 32px;
    min-height: 32px;
}

progressbar trough {
    background-color: #1a1a2e;
    border: 1px solid #2d2d5e;
    border-radius: 10px;
    min-height: 22px;
}
progressbar trough progress {
    background-image: linear-gradient(90deg, #34d399, #06b6d4, #818cf8);
    border-radius: 10px;
    box-shadow: 0 0 14px alpha(#34d399, 0.5);
    min-height: 22px;
}
progressbar text {
    color: #e0e0ff;
    font-weight: bold;
    font-size: 12px;
    text-shadow: 0 1px 3px alpha(#000000, 0.6);
}
"""


# ── Recent files helper ──────────────────────────────────────────────────────

def load_recent():
    try:
        return json.loads(RECENT_FILE.read_text())[:MAX_RECENT]
    except Exception:
        return []

def save_recent(paths):
    RECENT_FILE.parent.mkdir(parents=True, exist_ok=True)
    RECENT_FILE.write_text(json.dumps(paths[:MAX_RECENT]))

def add_recent(path):
    recents = load_recent()
    if path in recents:
        recents.remove(path)
    recents.insert(0, path)
    save_recent(recents[:MAX_RECENT])


# ── PIL ↔ GdkPixbuf helpers ─────────────────────────────────────────────────

def pil_to_pixbuf(pil_img):
    """Convert a PIL Image to GdkPixbuf (keeps reference to data alive)."""
    img = pil_img.convert('RGBA')
    data = img.tobytes()
    pixbuf = GdkPixbuf.Pixbuf.new_from_bytes(
        GLib.Bytes.new(data), GdkPixbuf.Colorspace.RGB, True, 8,
        img.width, img.height, img.width * 4,
    )
    return pixbuf

def pil_to_texture(pil_img):
    """Convert a PIL Image to Gdk.Texture for Gtk.Picture."""
    pixbuf = pil_to_pixbuf(pil_img)
    return Gdk.Texture.new_for_pixbuf(pixbuf)

def estimate_file_size(pil_img, fmt, quality=90):
    """Estimate output file size by encoding to a buffer."""
    buf = io.BytesIO()
    save_img = pil_img
    if fmt.upper() == 'JPEG':
        save_img = pil_img.convert('RGB')
    try:
        if fmt.upper() == 'JPEG':
            save_img.save(buf, format=fmt, quality=quality)
        elif fmt.upper() == 'WEBP':
            save_img.save(buf, format='WEBP', quality=quality)
        else:
            save_img.save(buf, format=fmt)
    except Exception:
        return 0
    return buf.tell()


# ── Helper: format bytes ─────────────────────────────────────────────────────

def format_size(size_bytes):
    for unit in ('B', 'KB', 'MB', 'GB'):
        if size_bytes < 1024 or unit == 'GB':
            if size_bytes == int(size_bytes):
                return f'{int(size_bytes)} {unit}'
            return f'{size_bytes:.1f} {unit}'
        size_bytes /= 1024


# ── Helper: get readable EXIF ────────────────────────────────────────────────

def get_exif_dict(pil_img):
    """Return dict of human-readable EXIF tag→value."""
    raw = pil_img.getexif()
    if not raw:
        return {}
    result = {}
    for tag_id, value in raw.items():
        tag = ExifTags.TAGS.get(tag_id, str(tag_id))
        if isinstance(value, bytes):
            value = value.hex()[:40]
        result[tag] = str(value)[:120]
    return result


# ══════════════════════════════════════════════════════════════════════════════
# Main Application
# ══════════════════════════════════════════════════════════════════════════════

class FuetemImagerApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id='com.invisi101.fuetem-imager')
        self.connect('activate', self.on_activate)

    # ── Activation ───────────────────────────────────────────────────────

    def on_activate(self, app):
        style_manager = Adw.StyleManager.get_default()
        style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        self._load_css()

        self.win = Adw.ApplicationWindow(
            application=app,
            title='fuetem-imager',
            default_width=720,
            default_height=780,
        )

        # ── State ────────────────────────────────────────────────────────
        self.source_path = None
        self.pil_image = None          # current working PIL image
        self.pil_original = None       # original loaded PIL image
        self.undo_stack = []
        self.lock_aspect = True
        self._updating_dims = False
        self._preview_bg = 'dark'      # 'dark', 'checker', 'light'
        self._temp_files = []
        self._orig_format = ''         # preserved across transforms
        self._orig_dpi = (72, 72)      # preserved across transforms

        # ── Header bar ───────────────────────────────────────────────────
        self.header = Adw.HeaderBar()
        self.title_label = Gtk.Label(label='fuetem-imager', css_classes=['title'])
        self.header.set_title_widget(self.title_label)

        # Undo button (left)
        self.btn_undo = Gtk.Button(icon_name='edit-undo-symbolic', tooltip_text='Undo')
        self.btn_undo.connect('clicked', self._on_undo)
        self.btn_undo.set_sensitive(False)
        self.header.pack_start(self.btn_undo)

        # View switcher for Edit / Batch tabs
        self.view_stack = Adw.ViewStack()
        switcher = Adw.ViewSwitcher(stack=self.view_stack, policy=Adw.ViewSwitcherPolicy.WIDE)
        self.header.set_title_widget(switcher)

        # ── Edit page ────────────────────────────────────────────────────
        edit_scroll = Gtk.ScrolledWindow(vexpand=True)
        edit_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.content_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=16,
            margin_top=20, margin_bottom=20, margin_start=24, margin_end=24,
        )
        edit_scroll.set_child(self.content_box)

        # Branding heading
        branding = Gtk.Label()
        branding.set_markup(
            '<span font_family="Vegan Style Personal Use" size="30000" foreground="#f472b6">Fuetem Imager</span>'
        )
        branding.set_halign(Gtk.Align.START)
        self.content_box.append(branding)

        self._build_select_section()
        self._build_preview_section()
        self._build_info_section()
        self.content_box.append(Gtk.Separator())
        self._build_transform_section()
        self.content_box.append(Gtk.Separator())
        self._build_resize_section()
        self.content_box.append(Gtk.Separator())
        self._build_output_section()
        self.content_box.append(Gtk.Separator())
        self._build_watermark_section()
        self.content_box.append(Gtk.Separator())
        self._build_save_section()

        self.view_stack.add_titled_with_icon(
            edit_scroll, 'edit', 'Edit', 'document-edit-symbolic')

        # ── Batch page ───────────────────────────────────────────────────
        self._build_batch_page()

        # ── Assemble ─────────────────────────────────────────────────────
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.append(self.header)
        vbox.append(self.view_stack)

        self.win.set_content(vbox)
        self._update_sensitivity()
        self.win.present()

    # ── CSS ──────────────────────────────────────────────────────────────

    def _load_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(CUSTOM_CSS.encode('utf-8'))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    # ══════════════════════════════════════════════════════════════════════
    #  Edit Page Sections
    # ══════════════════════════════════════════════════════════════════════

    # ── 1. Select Image ──────────────────────────────────────────────────

    def _build_select_section(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        heading = Gtk.Label(label='Select Image', xalign=0, css_classes=['section-heading'])
        box.append(heading)

        row = Gtk.Box(spacing=12, valign=Gtk.Align.CENTER)

        self.btn_select = Gtk.Button(label='Choose Image...')
        self.btn_select.add_css_class('suggested-action')
        self.btn_select.connect('clicked', self._on_select_image)
        row.append(self.btn_select)

        # Recent files dropdown
        self.recent_dropdown = Gtk.DropDown(model=Gtk.StringList())
        self.recent_dropdown.set_tooltip_text('Recent files')
        self.recent_dropdown.connect('notify::selected', self._on_recent_selected)
        self._refresh_recent_dropdown()
        row.append(self.recent_dropdown)

        self.file_label = Gtk.Label(label='No image selected', xalign=0, hexpand=True)
        self.file_label.add_css_class('dim-label')
        self.file_label.set_ellipsize(3)
        row.append(self.file_label)

        box.append(row)

        # Drag and drop hint
        drop_label = Gtk.Label(label='or drag & drop an image here', xalign=0.5)
        drop_label.add_css_class('dim-label')
        box.append(drop_label)

        # Set up drag-and-drop on the entire content area
        drop_target = Gtk.DropTarget.new(Gio.File, Gdk.DragAction.COPY)
        drop_target.connect('drop', self._on_drop)
        box.add_controller(drop_target)

        self.content_box.append(box)

    # ── 2. Preview ───────────────────────────────────────────────────────

    def _build_preview_section(self):
        self.preview_outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.preview_outer.set_visible(False)

        # Toggle row: bg mode + before/after
        toggle_row = Gtk.Box(spacing=8, halign=Gtk.Align.CENTER)

        bg_label = Gtk.Label(label='Preview BG:', css_classes=['info-label'])
        toggle_row.append(bg_label)

        self.btn_bg_dark = Gtk.ToggleButton(label='Dark')
        self.btn_bg_dark.set_active(True)
        self.btn_bg_checker = Gtk.ToggleButton(label='Checker', group=self.btn_bg_dark)
        self.btn_bg_light = Gtk.ToggleButton(label='Light', group=self.btn_bg_dark)
        for b in (self.btn_bg_dark, self.btn_bg_checker, self.btn_bg_light):
            b.add_css_class('flat')
            b.connect('toggled', self._on_preview_bg_changed)
            toggle_row.append(b)

        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        toggle_row.append(sep)

        self.btn_show_original = Gtk.ToggleButton(label='Show Original')
        self.btn_show_original.add_css_class('flat')
        self.btn_show_original.connect('toggled', self._on_toggle_original)
        toggle_row.append(self.btn_show_original)

        self.preview_outer.append(toggle_row)

        # Preview container
        self.preview_frame = Gtk.Frame()
        self.preview_frame.add_css_class('preview-frame')
        self.preview_image = Gtk.Picture()
        self.preview_image.set_size_request(-1, 240)
        self.preview_image.set_content_fit(Gtk.ContentFit.CONTAIN)
        self.preview_frame.set_child(self.preview_image)
        self.preview_outer.append(self.preview_frame)

        self.content_box.append(self.preview_outer)

    # ── 3. Info ──────────────────────────────────────────────────────────

    def _build_info_section(self):
        self.info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.info_box.add_css_class('info-card')
        self.info_box.set_visible(False)

        heading = Gtk.Label(label='Image Info', xalign=0, css_classes=['section-heading'])
        self.info_box.append(heading)

        grid = Gtk.Grid(column_spacing=24, row_spacing=6)

        def _row(label_text, row_idx):
            lbl = Gtk.Label(label=label_text, xalign=0, css_classes=['info-label'])
            grid.attach(lbl, 0, row_idx, 1, 1)
            val = Gtk.Label(label='—', xalign=0, css_classes=['info-value'])
            grid.attach(val, 1, row_idx, 1, 1)
            return val

        self.lbl_format = _row('Format:', 0)
        self.lbl_dimensions = _row('Dimensions:', 1)
        self.lbl_filesize = _row('File Size:', 2)
        self.lbl_color_mode = _row('Color Mode:', 3)
        self.lbl_bit_depth = _row('Bit Depth:', 4)
        self.lbl_dpi = _row('DPI:', 5)

        self.info_box.append(grid)

        # EXIF expander
        self.exif_expander = Gtk.Expander(label='EXIF Metadata')
        self.exif_expander.add_css_class('heading')
        self.exif_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.exif_expander.set_child(self.exif_box)
        self.info_box.append(self.exif_expander)

        self.content_box.append(self.info_box)

    # ── 4. Transform ─────────────────────────────────────────────────────

    def _build_transform_section(self):
        self.transform_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.transform_box.set_visible(False)

        heading = Gtk.Label(label='Transform', xalign=0, css_classes=['section-heading'])
        self.transform_box.append(heading)

        # Rotate / flip row
        row = Gtk.Box(spacing=8, halign=Gtk.Align.START)

        for label, cb in [
            ('Rotate 90° CW',  self._on_rotate_cw),
            ('Rotate 90° CCW', self._on_rotate_ccw),
            ('Rotate 180°',    self._on_rotate_180),
            ('Flip H',         self._on_flip_h),
            ('Flip V',         self._on_flip_v),
        ]:
            btn = Gtk.Button(label=label)
            btn.add_css_class('transform-btn')
            btn.connect('clicked', cb)
            row.append(btn)

        self.transform_box.append(row)

        # Crop section
        crop_heading = Gtk.Label(label='Crop (center)', xalign=0, css_classes=['info-label'],
                                 margin_top=8)
        self.transform_box.append(crop_heading)

        crop_row = Gtk.Box(spacing=8, valign=Gtk.Align.CENTER)

        crop_model = Gtk.StringList()
        for name in CROP_RATIOS:
            crop_model.append(name)
        self.crop_dropdown = Gtk.DropDown(model=crop_model)
        crop_row.append(self.crop_dropdown)

        btn_crop = Gtk.Button(label='Apply Crop')
        btn_crop.add_css_class('pill')
        btn_crop.connect('clicked', self._on_crop)
        crop_row.append(btn_crop)

        self.transform_box.append(crop_row)

        # Color space
        cs_heading = Gtk.Label(label='Color Space', xalign=0, css_classes=['info-label'],
                               margin_top=8)
        self.transform_box.append(cs_heading)

        cs_row = Gtk.Box(spacing=8)
        cs_model = Gtk.StringList()
        for m in ['Keep Original', 'RGB', 'Grayscale', 'RGBA']:
            cs_model.append(m)
        self.color_space_dropdown = Gtk.DropDown(model=cs_model)
        cs_row.append(self.color_space_dropdown)

        btn_cs = Gtk.Button(label='Apply')
        btn_cs.add_css_class('pill')
        btn_cs.connect('clicked', self._on_apply_color_space)
        cs_row.append(btn_cs)

        self.transform_box.append(cs_row)

        self.content_box.append(self.transform_box)

    # ── 5. Resize ────────────────────────────────────────────────────────

    def _build_resize_section(self):
        self.resize_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.resize_box.set_visible(False)

        heading = Gtk.Label(label='Resize', xalign=0, css_classes=['section-heading'])
        self.resize_box.append(heading)

        # Dimension spinbuttons
        dim_grid = Gtk.Grid(column_spacing=12, row_spacing=8)

        dim_grid.attach(Gtk.Label(label='Width:', xalign=0, css_classes=['info-label']), 0, 0, 1, 1)
        self.spin_width = Gtk.SpinButton()
        self.spin_width.set_range(1, 99999)
        self.spin_width.set_increments(1, 10)
        self.spin_width.connect('value-changed', self._on_width_changed)
        dim_grid.attach(self.spin_width, 1, 0, 1, 1)
        dim_grid.attach(Gtk.Label(label='px', xalign=0, css_classes=['dim-label']), 2, 0, 1, 1)

        dim_grid.attach(Gtk.Label(label='Height:', xalign=0, css_classes=['info-label']), 0, 1, 1, 1)
        self.spin_height = Gtk.SpinButton()
        self.spin_height.set_range(1, 99999)
        self.spin_height.set_increments(1, 10)
        self.spin_height.connect('value-changed', self._on_height_changed)
        dim_grid.attach(self.spin_height, 1, 1, 1, 1)
        dim_grid.attach(Gtk.Label(label='px', xalign=0, css_classes=['dim-label']), 2, 1, 1, 1)

        self.resize_box.append(dim_grid)

        # Lock aspect
        self.chk_aspect = Gtk.CheckButton(label='Lock aspect ratio')
        self.chk_aspect.set_active(True)
        self.chk_aspect.connect('toggled', lambda c: setattr(self, 'lock_aspect', c.get_active()))
        self.resize_box.append(self.chk_aspect)

        # Scale percentage
        scale_row = Gtk.Box(spacing=8, valign=Gtk.Align.CENTER)
        scale_row.append(Gtk.Label(label='Scale:', xalign=0, css_classes=['info-label']))

        scale_model = Gtk.StringList()
        for s in SCALE_PRESETS:
            scale_model.append(s)
        self.scale_dropdown = Gtk.DropDown(model=scale_model)
        self.scale_dropdown.set_selected(3)  # 100%
        scale_row.append(self.scale_dropdown)

        btn_apply_scale = Gtk.Button(label='Apply')
        btn_apply_scale.add_css_class('pill')
        btn_apply_scale.connect('clicked', self._on_apply_scale)
        scale_row.append(btn_apply_scale)

        self.resize_box.append(scale_row)

        # Presets
        preset_row = Gtk.Box(spacing=8, valign=Gtk.Align.CENTER)
        preset_row.append(Gtk.Label(label='Preset:', xalign=0, css_classes=['info-label']))

        preset_model = Gtk.StringList()
        preset_model.append('Custom')
        for name in DIMENSION_PRESETS:
            preset_model.append(name)
        self.preset_dropdown = Gtk.DropDown(model=preset_model)
        preset_row.append(self.preset_dropdown)

        btn_apply_preset = Gtk.Button(label='Apply')
        btn_apply_preset.add_css_class('pill')
        btn_apply_preset.connect('clicked', self._on_apply_preset)
        preset_row.append(btn_apply_preset)

        self.resize_box.append(preset_row)

        # Reset button
        btn_reset = Gtk.Button(label='Reset to Original Size')
        btn_reset.add_css_class('pill')
        btn_reset.connect('clicked', self._on_reset_dims)
        self.resize_box.append(btn_reset)

        self.content_box.append(self.resize_box)

    # ── 6. Output Options ────────────────────────────────────────────────

    def _build_output_section(self):
        self.output_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.output_box.set_visible(False)

        heading = Gtk.Label(label='Output Options', xalign=0, css_classes=['section-heading'])
        self.output_box.append(heading)

        # Format dropdown
        fmt_row = Gtk.Box(spacing=8, valign=Gtk.Align.CENTER)
        fmt_row.append(Gtk.Label(label='Format:', xalign=0, css_classes=['info-label']))
        format_model = Gtk.StringList()
        for fmt in SAVE_FORMATS:
            format_model.append(fmt.upper())
        self.format_dropdown = Gtk.DropDown(model=format_model)
        self.format_dropdown.connect('notify::selected', self._on_format_changed)
        fmt_row.append(self.format_dropdown)
        self.output_box.append(fmt_row)

        # JPEG / WebP quality
        self.quality_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.quality_box.set_visible(False)
        self.quality_box.append(Gtk.Label(label='Quality', xalign=0, css_classes=['info-label']))
        self.quality_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 100, 1)
        self.quality_scale.set_value(90)
        self.quality_scale.set_draw_value(True)
        self.quality_scale.connect('value-changed', lambda _s: self._update_estimated_size())
        self.quality_box.append(self.quality_scale)
        self.output_box.append(self.quality_box)

        # Transparency background color (for formats that don't support alpha)
        self.alpha_bg_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.alpha_bg_box.set_visible(False)
        self.alpha_bg_box.append(
            Gtk.Label(label='Background color (replaces transparency)', xalign=0,
                      css_classes=['info-label']))
        color_row = Gtk.Box(spacing=8)
        self.color_btn = Gtk.ColorButton()
        self.color_btn.set_rgba(Gdk.RGBA(red=1.0, green=1.0, blue=1.0, alpha=1.0))
        color_row.append(self.color_btn)
        color_row.append(Gtk.Label(label='Used when saving JPEG/BMP (no alpha)', css_classes=['dim-label']))
        self.alpha_bg_box.append(color_row)
        self.output_box.append(self.alpha_bg_box)

        # DPI
        dpi_row = Gtk.Box(spacing=8, valign=Gtk.Align.CENTER)
        dpi_row.append(Gtk.Label(label='DPI:', xalign=0, css_classes=['info-label']))
        self.spin_dpi = Gtk.SpinButton()
        self.spin_dpi.set_range(1, 2400)
        self.spin_dpi.set_increments(1, 10)
        self.spin_dpi.set_value(72)
        dpi_row.append(self.spin_dpi)
        self.output_box.append(dpi_row)

        # Strip EXIF
        self.chk_strip_exif = Gtk.CheckButton(label='Strip EXIF metadata')
        self.chk_strip_exif.set_active(False)
        self.output_box.append(self.chk_strip_exif)

        # Estimated output size
        self.lbl_est_size = Gtk.Label(label='', xalign=0, css_classes=['est-size'])
        self.lbl_est_size.set_visible(False)
        self.output_box.append(self.lbl_est_size)

        self.content_box.append(self.output_box)

    # ── 7. Watermark ─────────────────────────────────────────────────────

    def _build_watermark_section(self):
        self.watermark_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.watermark_box.set_visible(False)

        heading = Gtk.Label(label='Watermark', xalign=0, css_classes=['section-heading'])
        self.watermark_box.append(heading)

        # Text
        txt_row = Gtk.Box(spacing=8)
        txt_row.append(Gtk.Label(label='Text:', xalign=0, css_classes=['info-label']))
        self.watermark_entry = Gtk.Entry(placeholder_text='Watermark text...', hexpand=True)
        txt_row.append(self.watermark_entry)
        self.watermark_box.append(txt_row)

        # Font size
        size_row = Gtk.Box(spacing=8, valign=Gtk.Align.CENTER)
        size_row.append(Gtk.Label(label='Font size:', xalign=0, css_classes=['info-label']))
        self.spin_wm_size = Gtk.SpinButton()
        self.spin_wm_size.set_range(8, 500)
        self.spin_wm_size.set_increments(1, 10)
        self.spin_wm_size.set_value(36)
        size_row.append(self.spin_wm_size)
        self.watermark_box.append(size_row)

        # Opacity
        opacity_row = Gtk.Box(spacing=8, valign=Gtk.Align.CENTER)
        opacity_row.append(Gtk.Label(label='Opacity:', xalign=0, css_classes=['info-label']))
        self.wm_opacity_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.wm_opacity_scale.set_value(50)
        self.wm_opacity_scale.set_draw_value(True)
        self.wm_opacity_scale.set_hexpand(True)
        opacity_row.append(self.wm_opacity_scale)
        self.watermark_box.append(opacity_row)

        # Color
        wm_color_row = Gtk.Box(spacing=8, valign=Gtk.Align.CENTER)
        wm_color_row.append(Gtk.Label(label='Color:', xalign=0, css_classes=['info-label']))
        self.wm_color_btn = Gtk.ColorButton()
        self.wm_color_btn.set_rgba(Gdk.RGBA(red=1.0, green=1.0, blue=1.0, alpha=1.0))
        wm_color_row.append(self.wm_color_btn)
        self.watermark_box.append(wm_color_row)

        # Position
        pos_row = Gtk.Box(spacing=8, valign=Gtk.Align.CENTER)
        pos_row.append(Gtk.Label(label='Position:', xalign=0, css_classes=['info-label']))
        pos_model = Gtk.StringList()
        for p in WATERMARK_POSITIONS:
            pos_model.append(p)
        self.wm_pos_dropdown = Gtk.DropDown(model=pos_model)
        pos_row.append(self.wm_pos_dropdown)
        self.watermark_box.append(pos_row)

        # Apply button
        btn_wm = Gtk.Button(label='Apply Watermark')
        btn_wm.add_css_class('pill')
        btn_wm.connect('clicked', self._on_apply_watermark)
        self.watermark_box.append(btn_wm)

        self.content_box.append(self.watermark_box)

    # ── 8. Save ──────────────────────────────────────────────────────────

    def _build_save_section(self):
        self.save_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.save_box.set_visible(False)

        heading = Gtk.Label(label='Save', xalign=0, css_classes=['section-heading'])
        self.save_box.append(heading)

        btn_row = Gtk.Box(spacing=12, halign=Gtk.Align.CENTER)

        self.btn_save = Gtk.Button(label='Save As...')
        self.btn_save.add_css_class('suggested-action')
        self.btn_save.connect('clicked', self._on_save)
        btn_row.append(self.btn_save)

        self.btn_clipboard = Gtk.Button(label='Copy to Clipboard')
        self.btn_clipboard.add_css_class('pill')
        self.btn_clipboard.connect('clicked', self._on_copy_clipboard)
        btn_row.append(self.btn_clipboard)

        self.save_box.append(btn_row)

        self.save_status = Gtk.Label(label='')
        self.save_status.set_visible(False)
        self.save_box.append(self.save_status)

        self.content_box.append(self.save_box)

    # ══════════════════════════════════════════════════════════════════════
    #  Batch Page
    # ══════════════════════════════════════════════════════════════════════

    def _build_batch_page(self):
        batch_scroll = Gtk.ScrolledWindow(vexpand=True)
        batch_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        batch_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=16,
            margin_top=20, margin_bottom=20, margin_start=24, margin_end=24,
        )

        heading = Gtk.Label(label='Batch Convert', xalign=0, css_classes=['section-heading'])
        batch_box.append(heading)

        desc = Gtk.Label(
            label='Add multiple images and convert them all with the same settings.',
            xalign=0, css_classes=['dim-label'], wrap=True,
        )
        batch_box.append(desc)

        # Add / clear buttons
        btn_row = Gtk.Box(spacing=8)
        self.btn_batch_add = Gtk.Button(label='Add Images...')
        self.btn_batch_add.add_css_class('suggested-action')
        self.btn_batch_add.connect('clicked', self._on_batch_add)
        btn_row.append(self.btn_batch_add)

        self.btn_batch_clear = Gtk.Button(label='Clear All')
        self.btn_batch_clear.add_css_class('destructive-action')
        self.btn_batch_clear.connect('clicked', self._on_batch_clear)
        btn_row.append(self.btn_batch_clear)

        self.batch_count_label = Gtk.Label(label='0 files', xalign=0, hexpand=True,
                                           css_classes=['info-value'])
        btn_row.append(self.batch_count_label)
        batch_box.append(btn_row)

        # File list
        self.batch_list_box = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.batch_list_box.add_css_class('boxed-list')
        batch_box.append(self.batch_list_box)

        # Batch settings
        batch_box.append(Gtk.Separator())

        settings_heading = Gtk.Label(label='Batch Settings', xalign=0, css_classes=['section-heading'])
        batch_box.append(settings_heading)

        # Format
        fmt_row = Gtk.Box(spacing=8, valign=Gtk.Align.CENTER)
        fmt_row.append(Gtk.Label(label='Output Format:', xalign=0, css_classes=['info-label']))
        batch_fmt_model = Gtk.StringList()
        for fmt in SAVE_FORMATS:
            batch_fmt_model.append(fmt.upper())
        self.batch_format_dropdown = Gtk.DropDown(model=batch_fmt_model)
        fmt_row.append(self.batch_format_dropdown)
        batch_box.append(fmt_row)

        # Resize option
        resize_row = Gtk.Box(spacing=8, valign=Gtk.Align.CENTER)
        self.batch_chk_resize = Gtk.CheckButton(label='Resize to:')
        resize_row.append(self.batch_chk_resize)

        self.batch_spin_w = Gtk.SpinButton()
        self.batch_spin_w.set_range(1, 99999)
        self.batch_spin_w.set_increments(1, 10)
        self.batch_spin_w.set_value(1920)
        resize_row.append(self.batch_spin_w)
        resize_row.append(Gtk.Label(label='x', css_classes=['dim-label']))
        self.batch_spin_h = Gtk.SpinButton()
        self.batch_spin_h.set_range(1, 99999)
        self.batch_spin_h.set_increments(1, 10)
        self.batch_spin_h.set_value(1080)
        resize_row.append(self.batch_spin_h)
        resize_row.append(Gtk.Label(label='px', css_classes=['dim-label']))
        batch_box.append(resize_row)

        # Quality
        q_row = Gtk.Box(spacing=8, valign=Gtk.Align.CENTER)
        q_row.append(Gtk.Label(label='Quality:', css_classes=['info-label']))
        self.batch_quality = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 100, 1)
        self.batch_quality.set_value(90)
        self.batch_quality.set_draw_value(True)
        self.batch_quality.set_hexpand(True)
        q_row.append(self.batch_quality)
        batch_box.append(q_row)

        # Strip EXIF
        self.batch_chk_strip = Gtk.CheckButton(label='Strip EXIF metadata')
        batch_box.append(self.batch_chk_strip)

        # Output directory
        dir_row = Gtk.Box(spacing=8, valign=Gtk.Align.CENTER)
        dir_row.append(Gtk.Label(label='Output folder:', xalign=0, css_classes=['info-label']))
        self.batch_dir_label = Gtk.Label(label='Same as source', xalign=0, hexpand=True,
                                         css_classes=['info-value'])
        dir_row.append(self.batch_dir_label)
        btn_dir = Gtk.Button(label='Choose...')
        btn_dir.add_css_class('pill')
        btn_dir.connect('clicked', self._on_batch_choose_dir)
        dir_row.append(btn_dir)
        batch_box.append(dir_row)
        self.batch_output_dir = None

        # Convert button
        batch_box.append(Gtk.Separator())

        self.btn_batch_convert = Gtk.Button(label='Convert All')
        self.btn_batch_convert.add_css_class('suggested-action')
        self.btn_batch_convert.set_halign(Gtk.Align.CENTER)
        self.btn_batch_convert.connect('clicked', self._on_batch_convert)
        batch_box.append(self.btn_batch_convert)

        self.batch_progress = Gtk.ProgressBar(show_text=True)
        self.batch_progress.set_visible(False)
        batch_box.append(self.batch_progress)

        self.batch_status = Gtk.Label(label='', css_classes=['success'])
        self.batch_status.set_visible(False)
        batch_box.append(self.batch_status)

        batch_scroll.set_child(batch_box)

        self.batch_files = []

        self.view_stack.add_titled_with_icon(
            batch_scroll, 'batch', 'Batch', 'view-grid-symbolic')

    # ══════════════════════════════════════════════════════════════════════
    #  Callbacks — Image Loading
    # ══════════════════════════════════════════════════════════════════════

    def _on_select_image(self, _btn):
        dialog = Gtk.FileDialog()
        dialog.set_title('Select an Image')

        img_filter = Gtk.FileFilter()
        img_filter.set_name('Images')
        for p in ('*.png', '*.jpg', '*.jpeg', '*.bmp', '*.tiff', '*.tif',
                   '*.ico', '*.webp', '*.avif', '*.gif', '*.svg'):
            img_filter.add_pattern(p)

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(img_filter)
        all_f = Gtk.FileFilter()
        all_f.set_name('All Files')
        all_f.add_pattern('*')
        filters.append(all_f)

        dialog.set_filters(filters)
        dialog.set_default_filter(img_filter)
        dialog.open(self.win, None, self._on_file_selected)

    def _on_file_selected(self, dialog, result):
        try:
            gfile = dialog.open_finish(result)
        except GLib.Error:
            return
        path = gfile.get_path()
        if path:
            self._load_image(path)

    def _on_drop(self, _target, value, _x, _y):
        if isinstance(value, Gio.File):
            path = value.get_path()
            if path:
                self._load_image(path)
                return True
        return False

    def _on_recent_selected(self, dropdown, _pspec):
        if getattr(self, '_refreshing_recent', False):
            return
        idx = dropdown.get_selected()
        recents = load_recent()
        if 0 <= idx < len(recents):
            path = recents[idx]
            if os.path.isfile(path):
                self._load_image(path)

    def _load_image(self, path):
        try:
            pil_img = Image.open(path)
            pil_img.load()
        except Exception as e:
            self._show_error(f'Failed to load image:\n{e}')
            return

        self.source_path = path
        self.pil_original = pil_img.copy()
        self.pil_image = pil_img.copy()
        self._orig_format = pil_img.format or Path(path).suffix.lstrip('.').upper()
        self._orig_dpi = pil_img.info.get('dpi', (72, 72))
        self.undo_stack.clear()
        self.btn_undo.set_sensitive(False)

        add_recent(path)
        self._refresh_recent_dropdown()

        self.file_label.set_label(os.path.basename(path))
        self.file_label.remove_css_class('dim-label')
        self.file_label.add_css_class('info-value')

        self._refresh_info()
        self._refresh_preview()
        self._sync_dims_to_image()
        self._auto_select_format()
        self._update_sensitivity()

    def _refresh_recent_dropdown(self):
        self._refreshing_recent = True
        recents = load_recent()
        model = Gtk.StringList()
        for p in recents:
            model.append(os.path.basename(p))
        self.recent_dropdown.set_model(model)
        self._refreshing_recent = False

    # ══════════════════════════════════════════════════════════════════════
    #  Refresh helpers
    # ══════════════════════════════════════════════════════════════════════

    def _refresh_info(self):
        img = self.pil_image
        if not img:
            return

        self.lbl_format.set_label(self._orig_format)
        self.lbl_dimensions.set_label(f'{img.width} x {img.height} px')
        self.lbl_filesize.set_label(format_size(os.path.getsize(self.source_path)))
        self.lbl_color_mode.set_label(img.mode)

        # Bit depth
        mode_bits = {'1': '1', 'L': '8', 'P': '8', 'RGB': '8', 'RGBA': '8',
                     'CMYK': '8', 'YCbCr': '8', 'LAB': '8', 'HSV': '8',
                     'I': '32', 'F': '32', 'I;16': '16', 'I;16L': '16',
                     'LA': '8', 'PA': '8', 'RGBa': '8'}
        self.lbl_bit_depth.set_label(f'{mode_bits.get(img.mode, "?")} bits/channel')

        # DPI — use stored original since transforms lose img.info
        dpi = self._orig_dpi
        try:
            dpi_x, dpi_y = int(dpi[0]), int(dpi[1])
        except (TypeError, IndexError):
            dpi_x = dpi_y = 72
        self.lbl_dpi.set_label(f'{dpi_x} x {dpi_y}')
        self.spin_dpi.set_value(dpi_x)

        # EXIF
        while (child := self.exif_box.get_first_child()):
            self.exif_box.remove(child)

        exif = get_exif_dict(img)
        if exif:
            for key, val in exif.items():
                row = Gtk.Box(spacing=12)
                row.append(Gtk.Label(label=key, xalign=0, css_classes=['exif-key'],
                                     width_chars=20, max_width_chars=20, ellipsize=3))
                row.append(Gtk.Label(label=val, xalign=0, css_classes=['exif-val'],
                                     hexpand=True, ellipsize=3))
                self.exif_box.append(row)
        else:
            self.exif_box.append(Gtk.Label(label='No EXIF data', css_classes=['dim-label']))

        self._update_estimated_size()

    def _refresh_preview(self):
        img = self.pil_image
        if not img:
            return

        show_orig = self.btn_show_original.get_active()
        display_img = self.pil_original if show_orig else img

        texture = pil_to_texture(display_img)
        self.preview_image.set_paintable(texture)

        # Update background class
        frame = self.preview_frame
        for cls in ('preview-frame', 'preview-checker', 'preview-light'):
            frame.remove_css_class(cls)

        if self._preview_bg == 'dark':
            frame.add_css_class('preview-frame')
        elif self._preview_bg == 'checker':
            frame.add_css_class('preview-checker')
        else:
            frame.add_css_class('preview-light')

    def _sync_dims_to_image(self):
        if not self.pil_image:
            return
        self._updating_dims = True
        self.spin_width.set_value(self.pil_image.width)
        self.spin_height.set_value(self.pil_image.height)
        self._updating_dims = False

    def _auto_select_format(self):
        if not self.pil_image:
            return
        fmt = self._orig_format.lower()
        if fmt in SAVE_FORMATS:
            self.format_dropdown.set_selected(SAVE_FORMATS.index(fmt))

    def _update_sensitivity(self):
        has = self.pil_image is not None
        for w in (self.preview_outer, self.info_box, self.transform_box,
                  self.resize_box, self.output_box, self.watermark_box, self.save_box):
            w.set_visible(has)

    def _update_estimated_size(self):
        if not self.pil_image:
            return
        idx = self.format_dropdown.get_selected()
        fmt = SAVE_FORMATS[idx]
        quality = int(self.quality_scale.get_value())

        # Read widget values on main thread, then do heavy work in background
        new_w = int(self.spin_width.get_value())
        new_h = int(self.spin_height.get_value())
        img_copy = self.pil_image.copy()

        def _estimate():
            if (new_w, new_h) != img_copy.size:
                resized = img_copy.resize((new_w, new_h), Image.LANCZOS)
            else:
                resized = img_copy
            size = estimate_file_size(resized, fmt, quality)
            GLib.idle_add(self._set_est_size, size)

        threading.Thread(target=_estimate, daemon=True).start()

    def _set_est_size(self, size):
        if size > 0:
            self.lbl_est_size.set_label(f'Estimated output size: ~{format_size(size)}')
            self.lbl_est_size.set_visible(True)
        else:
            self.lbl_est_size.set_visible(False)

    # ══════════════════════════════════════════════════════════════════════
    #  Undo
    # ══════════════════════════════════════════════════════════════════════

    def _push_undo(self):
        self.undo_stack.append(self.pil_image.copy())
        if len(self.undo_stack) > MAX_UNDO:
            self.undo_stack.pop(0)
        self.btn_undo.set_sensitive(True)

    def _on_undo(self, _btn):
        if not self.undo_stack:
            return
        self.pil_image = self.undo_stack.pop()
        self.btn_undo.set_sensitive(bool(self.undo_stack))
        self._sync_dims_to_image()
        self._refresh_preview()
        self._refresh_info()

    # ══════════════════════════════════════════════════════════════════════
    #  Callbacks — Preview
    # ══════════════════════════════════════════════════════════════════════

    def _on_preview_bg_changed(self, btn):
        if not btn.get_active():
            return
        if btn is self.btn_bg_dark:
            self._preview_bg = 'dark'
        elif btn is self.btn_bg_checker:
            self._preview_bg = 'checker'
        else:
            self._preview_bg = 'light'
        self._refresh_preview()

    def _on_toggle_original(self, _btn):
        self._refresh_preview()

    # ══════════════════════════════════════════════════════════════════════
    #  Callbacks — Transform
    # ══════════════════════════════════════════════════════════════════════

    def _apply_transform(self, fn):
        if not self.pil_image:
            return
        self._push_undo()
        self.pil_image = fn(self.pil_image)
        self._sync_dims_to_image()
        self._refresh_preview()
        self._refresh_info()

    def _on_rotate_cw(self, _b):
        self._apply_transform(lambda img: img.rotate(-90, expand=True))

    def _on_rotate_ccw(self, _b):
        self._apply_transform(lambda img: img.rotate(90, expand=True))

    def _on_rotate_180(self, _b):
        self._apply_transform(lambda img: img.rotate(180, expand=True))

    def _on_flip_h(self, _b):
        self._apply_transform(lambda img: img.transpose(Image.FLIP_LEFT_RIGHT))

    def _on_flip_v(self, _b):
        self._apply_transform(lambda img: img.transpose(Image.FLIP_TOP_BOTTOM))

    def _on_crop(self, _b):
        if not self.pil_image:
            return
        idx = self.crop_dropdown.get_selected()
        ratio_name = list(CROP_RATIOS.keys())[idx]
        ratio = CROP_RATIOS[ratio_name]
        if ratio is None:
            return

        w, h = self.pil_image.size
        rw, rh = ratio
        target_ratio = rw / rh

        if w / h > target_ratio:
            new_w = int(h * target_ratio)
            new_h = h
        else:
            new_w = w
            new_h = int(w / target_ratio)

        left = (w - new_w) // 2
        top = (h - new_h) // 2

        self._push_undo()
        self.pil_image = self.pil_image.crop((left, top, left + new_w, top + new_h))
        self._sync_dims_to_image()
        self._refresh_preview()
        self._refresh_info()

    def _on_apply_color_space(self, _b):
        if not self.pil_image:
            return
        idx = self.color_space_dropdown.get_selected()
        modes = [None, 'RGB', 'L', 'RGBA']
        mode = modes[idx]
        if mode is None or mode == self.pil_image.mode:
            return
        self._push_undo()
        self.pil_image = self.pil_image.convert(mode)
        self._refresh_preview()
        self._refresh_info()

    # ══════════════════════════════════════════════════════════════════════
    #  Callbacks — Resize
    # ══════════════════════════════════════════════════════════════════════

    def _on_width_changed(self, spin):
        if self._updating_dims or not self.pil_image:
            return
        if not self.lock_aspect or self.pil_image.width == 0:
            return
        ratio = self.pil_image.height / self.pil_image.width
        self._updating_dims = True
        self.spin_height.set_value(int(spin.get_value() * ratio))
        self._updating_dims = False

    def _on_height_changed(self, spin):
        if self._updating_dims or not self.pil_image:
            return
        if not self.lock_aspect or self.pil_image.height == 0:
            return
        ratio = self.pil_image.width / self.pil_image.height
        self._updating_dims = True
        self.spin_width.set_value(int(spin.get_value() * ratio))
        self._updating_dims = False

    def _on_apply_scale(self, _b):
        if not self.pil_image:
            return
        idx = self.scale_dropdown.get_selected()
        pct = int(SCALE_PRESETS[idx].rstrip('%'))
        # Scale relative to current image dimensions
        cur_w, cur_h = self.pil_image.size
        new_w = max(1, int(cur_w * pct / 100))
        new_h = max(1, int(cur_h * pct / 100))
        self._push_undo()
        self.pil_image = self.pil_image.resize((new_w, new_h), Image.LANCZOS)
        self._sync_dims_to_image()
        self._refresh_preview()
        self._refresh_info()

    def _on_apply_preset(self, _b):
        if not self.pil_image:
            return
        idx = self.preset_dropdown.get_selected()
        if idx == 0:
            return
        name = list(DIMENSION_PRESETS.keys())[idx - 1]
        w, h = DIMENSION_PRESETS[name]
        self._push_undo()
        self.pil_image = self.pil_image.resize((w, h), Image.LANCZOS)
        self._sync_dims_to_image()
        self._refresh_preview()
        self._refresh_info()

    def _on_reset_dims(self, _b):
        if not self.pil_original:
            return
        self._push_undo()
        self.pil_image = self.pil_original.copy()
        self._sync_dims_to_image()
        self._refresh_preview()
        self._refresh_info()

    # ══════════════════════════════════════════════════════════════════════
    #  Callbacks — Output Options
    # ══════════════════════════════════════════════════════════════════════

    def _on_format_changed(self, dropdown, _pspec):
        fmt = SAVE_FORMATS[dropdown.get_selected()]
        self.quality_box.set_visible(fmt in ('jpeg', 'webp', 'avif'))
        self.alpha_bg_box.set_visible(fmt in ('jpeg', 'bmp'))
        self._update_estimated_size()

    # ══════════════════════════════════════════════════════════════════════
    #  Callbacks — Watermark
    # ══════════════════════════════════════════════════════════════════════

    def _on_apply_watermark(self, _b):
        if not self.pil_image:
            return
        text = self.watermark_entry.get_text().strip()
        if not text:
            return

        self._push_undo()

        img = self.pil_image.convert('RGBA')
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        font_size = int(self.spin_wm_size.get_value())
        try:
            font = ImageFont.truetype('/usr/share/fonts/TTF/DejaVuSans-Bold.ttf', font_size)
        except Exception:
            try:
                font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', font_size)
            except Exception:
                font = ImageFont.load_default()

        opacity = int(self.wm_opacity_scale.get_value() * 255 / 100)

        rgba = self.wm_color_btn.get_rgba()
        r, g, b = int(rgba.red * 255), int(rgba.green * 255), int(rgba.blue * 255)
        fill = (r, g, b, opacity)

        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

        pos_idx = self.wm_pos_dropdown.get_selected()
        pos_name = WATERMARK_POSITIONS[pos_idx]
        pad = 20

        if pos_name == 'Center':
            x, y = (img.width - tw) // 2, (img.height - th) // 2
        elif pos_name == 'Top-Left':
            x, y = pad, pad
        elif pos_name == 'Top-Right':
            x, y = img.width - tw - pad, pad
        elif pos_name == 'Bottom-Left':
            x, y = pad, img.height - th - pad
        else:  # Bottom-Right
            x, y = img.width - tw - pad, img.height - th - pad

        draw.text((x, y), text, font=font, fill=fill)
        self.pil_image = Image.alpha_composite(img, overlay)
        self._refresh_preview()
        self._refresh_info()

    # ══════════════════════════════════════════════════════════════════════
    #  Callbacks — Save / Clipboard
    # ══════════════════════════════════════════════════════════════════════

    def _build_output_image(self):
        """Build the final output image with current resize + options applied."""
        img = self.pil_image.copy()

        # Resize if spinbutton values differ
        new_w = int(self.spin_width.get_value())
        new_h = int(self.spin_height.get_value())
        if (new_w, new_h) != img.size:
            img = img.resize((new_w, new_h), Image.LANCZOS)

        return img

    def _prepare_for_save(self, img, fmt):
        """Handle alpha removal and EXIF stripping."""
        # Remove alpha for formats that don't support it
        if fmt in ('jpeg', 'bmp') and img.mode in ('RGBA', 'LA', 'PA'):
            rgba = self.color_btn.get_rgba()
            bg_r = int(rgba.red * 255)
            bg_g = int(rgba.green * 255)
            bg_b = int(rgba.blue * 255)
            background = Image.new('RGB', img.size, (bg_r, bg_g, bg_b))
            background.paste(img, mask=img.split()[-1])
            img = background
        elif fmt == 'jpeg' and img.mode != 'RGB':
            img = img.convert('RGB')

        return img

    def _get_save_kwargs(self, fmt):
        kwargs = {}
        quality = int(self.quality_scale.get_value())
        dpi = int(self.spin_dpi.get_value())

        if fmt in ('jpeg', 'webp', 'avif'):
            kwargs['quality'] = quality
        if fmt in ('png', 'jpeg', 'tiff', 'webp'):
            kwargs['dpi'] = (dpi, dpi)

        # Strip EXIF — only for formats that accept the exif kwarg
        if self.chk_strip_exif.get_active() and fmt in ('jpeg', 'png', 'webp', 'avif'):
            kwargs['exif'] = b''

        return kwargs

    def _on_save(self, _btn):
        if not self.pil_image:
            return

        fmt = SAVE_FORMATS[self.format_dropdown.get_selected()]
        ext = 'jpg' if fmt == 'jpeg' else fmt

        dialog = Gtk.FileDialog()
        dialog.set_title('Save Image As')
        if self.source_path:
            dialog.set_initial_name(f'{Path(self.source_path).stem}.{ext}')
        dialog.save(self.win, None, self._on_save_finish)

    def _on_save_finish(self, dialog, result):
        try:
            gfile = dialog.save_finish(result)
        except GLib.Error:
            return
        out_path = gfile.get_path()
        if not out_path:
            return

        fmt = SAVE_FORMATS[self.format_dropdown.get_selected()]
        img = self._build_output_image()
        img = self._prepare_for_save(img, fmt)
        kwargs = self._get_save_kwargs(fmt)

        # Map format names for PIL
        pil_fmt = fmt.upper()
        if pil_fmt == 'AVIF':
            pil_fmt = 'AVIF'

        try:
            img.save(out_path, format=pil_fmt, **kwargs)
            self.save_status.set_label(f'Saved: {os.path.basename(out_path)}')
            self.save_status.remove_css_class('error')
            self.save_status.add_css_class('success')
            self.save_status.set_visible(True)
        except Exception as e:
            self.save_status.set_label(f'Error: {e}')
            self.save_status.remove_css_class('success')
            self.save_status.add_css_class('error')
            self.save_status.set_visible(True)

    def _on_copy_clipboard(self, _btn):
        if not self.pil_image:
            return
        img = self._build_output_image()
        texture = pil_to_texture(img)
        clipboard = self.win.get_clipboard()
        clipboard.set(texture)
        self.save_status.set_label('Copied to clipboard')
        self.save_status.remove_css_class('error')
        self.save_status.add_css_class('success')
        self.save_status.set_visible(True)

    # ══════════════════════════════════════════════════════════════════════
    #  Batch Callbacks
    # ══════════════════════════════════════════════════════════════════════

    def _on_batch_add(self, _btn):
        dialog = Gtk.FileDialog()
        dialog.set_title('Select Images')

        img_filter = Gtk.FileFilter()
        img_filter.set_name('Images')
        for p in ('*.png', '*.jpg', '*.jpeg', '*.bmp', '*.tiff', '*.tif',
                   '*.ico', '*.webp', '*.avif', '*.gif'):
            img_filter.add_pattern(p)
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(img_filter)
        dialog.set_filters(filters)
        dialog.set_default_filter(img_filter)
        dialog.open_multiple(self.win, None, self._on_batch_files_selected)

    def _on_batch_files_selected(self, dialog, result):
        try:
            file_list = dialog.open_multiple_finish(result)
        except GLib.Error:
            return

        for i in range(file_list.get_n_items()):
            gfile = file_list.get_item(i)
            path = gfile.get_path()
            if path and path not in self.batch_files:
                self.batch_files.append(path)
                row = Gtk.ListBoxRow()
                label = Gtk.Label(label=os.path.basename(path), xalign=0,
                                  css_classes=['info-value'],
                                  margin_top=6, margin_bottom=6,
                                  margin_start=12, margin_end=12)
                row.set_child(label)
                self.batch_list_box.append(row)

        self.batch_count_label.set_label(f'{len(self.batch_files)} files')

    def _on_batch_clear(self, _btn):
        self.batch_files.clear()
        while (child := self.batch_list_box.get_first_child()):
            self.batch_list_box.remove(child)
        self.batch_count_label.set_label('0 files')
        self.batch_status.set_visible(False)

    def _on_batch_choose_dir(self, _btn):
        dialog = Gtk.FileDialog()
        dialog.set_title('Select Output Folder')
        dialog.select_folder(self.win, None, self._on_batch_dir_selected)

    def _on_batch_dir_selected(self, dialog, result):
        try:
            gfile = dialog.select_folder_finish(result)
        except GLib.Error:
            return
        path = gfile.get_path()
        if path:
            self.batch_output_dir = path
            self.batch_dir_label.set_label(path)

    def _on_batch_convert(self, _btn):
        if not self.batch_files:
            return

        fmt = SAVE_FORMATS[self.batch_format_dropdown.get_selected()]
        ext = 'jpg' if fmt == 'jpeg' else fmt
        quality = int(self.batch_quality.get_value())
        do_resize = self.batch_chk_resize.get_active()
        new_w = int(self.batch_spin_w.get_value())
        new_h = int(self.batch_spin_h.get_value())
        strip_exif = self.batch_chk_strip.get_active()
        out_dir = self.batch_output_dir

        self.batch_progress.set_visible(True)
        self.batch_progress.set_fraction(0)
        self.batch_status.set_visible(False)
        self.btn_batch_convert.set_sensitive(False)

        files = list(self.batch_files)
        total = len(files)

        def _worker():
            errors = []
            for i, path in enumerate(files):
                try:
                    img = Image.open(path)
                    img.load()

                    if do_resize:
                        img = img.resize((new_w, new_h), Image.LANCZOS)

                    # Handle alpha
                    if fmt in ('jpeg', 'bmp') and img.mode in ('RGBA', 'LA', 'PA'):
                        bg = Image.new('RGB', img.size, (255, 255, 255))
                        bg.paste(img, mask=img.split()[-1])
                        img = bg
                    elif fmt == 'jpeg' and img.mode != 'RGB':
                        img = img.convert('RGB')

                    dest_dir = out_dir or os.path.dirname(path)
                    stem = Path(path).stem
                    out_path = os.path.join(dest_dir, f'{stem}.{ext}')

                    kwargs = {}
                    if fmt in ('jpeg', 'webp', 'avif'):
                        kwargs['quality'] = quality
                    if strip_exif:
                        kwargs['exif'] = b''

                    img.save(out_path, format=fmt.upper(), **kwargs)
                except Exception as e:
                    errors.append(f'{os.path.basename(path)}: {e}')

                GLib.idle_add(self.batch_progress.set_fraction, (i + 1) / total)
                GLib.idle_add(self.batch_progress.set_text, f'{i + 1}/{total}')

            def _done():
                self.btn_batch_convert.set_sensitive(True)
                if errors:
                    self.batch_status.set_label(
                        f'Done with {len(errors)} error(s):\n' + '\n'.join(errors[:5]))
                    self.batch_status.remove_css_class('success')
                    self.batch_status.add_css_class('error')
                else:
                    self.batch_status.set_label(f'All {total} images converted successfully')
                    self.batch_status.remove_css_class('error')
                    self.batch_status.add_css_class('success')
                self.batch_status.set_visible(True)

            GLib.idle_add(_done)

        threading.Thread(target=_worker, daemon=True).start()

    # ══════════════════════════════════════════════════════════════════════
    #  Helpers
    # ══════════════════════════════════════════════════════════════════════

    def _show_error(self, message):
        dialog = Adw.AlertDialog(heading='Error', body=message)
        dialog.add_response('ok', 'OK')
        dialog.present(self.win)


def main():
    app = FuetemImagerApp()
    app.run(None)


if __name__ == '__main__':
    main()
