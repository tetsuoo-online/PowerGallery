import sys
import json
import os
import re
import struct
import zlib
import subprocess
from datetime import datetime
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QFileDialog, 
                             QScrollArea, QTabWidget, QSlider, QLineEdit, QTextEdit,
                             QGridLayout, QFrame, QDialog, QComboBox, QLayout, QSizePolicy,
                             QCheckBox, QGroupBox, QListWidget, QListWidgetItem, QStackedWidget,
QDialogButtonBox, QFormLayout, QSpinBox, QMessageBox)
from PyQt6.QtCore import Qt, QPoint, QRect, QTimer, pyqtSignal, QMimeData, QSize
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QDrag, QPalette, QPen, QIcon, QFontMetrics

from config.settings import config
from widgets import CardDetailsDialog
from modules.checkpoint_manager import CheckpointManager
from modules.dataset_manager import DatasetManager


def get_styles():
    return config.get_styles()


MODULE_REGISTRY = {
    'checkpoint_manager': CheckpointManager,
    'dataset': DatasetManager,
}


# ── Metadata reader ───────────────────────────────────────────────────────────

# exiftool path — tools/exiftool.exe next to power_gallery.py
_EXIFTOOL_PATH = Path(__file__).parent / 'tools' / 'exiftool.exe'


def _exiftool_available():
    return _EXIFTOOL_PATH.exists()


def _read_via_exiftool(image_path):
    """
    Run exiftool -json on the file, return a flat dict of tag→value strings.
    Returns {} on any error or if exiftool is not found.
    """
    if not _exiftool_available():
        return {}
    try:
        result = subprocess.run(
            [str(_EXIFTOOL_PATH), '-json', '-charset', 'utf8', str(image_path)],
            capture_output=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        if result.returncode != 0:
            return {}
        data = json.loads(result.stdout.decode('utf-8', errors='replace'))
        if data:
            # exiftool returns a list with one entry per file
            return {k: str(v) for k, v in data[0].items() if not k.startswith('SourceFile')}
    except Exception as e:
        print(f"[exiftool] {image_path}: {e}")
    return {}


def _read_png_chunks(path):
    """Parse PNG text chunks (tEXt, iTXt, zTXt) — fast, no external tool needed."""
    meta = {}
    data = path.read_bytes()
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        return meta
    pos = 8
    while pos < len(data):
        if pos + 8 > len(data):
            break
        length = struct.unpack('>I', data[pos:pos+4])[0]
        chunk_type = data[pos+4:pos+8]
        chunk_data = data[pos+8:pos+8+length]
        pos += 12 + length

        if chunk_type == b'tEXt':
            try:
                null = chunk_data.index(b'\x00')
                meta[chunk_data[:null].decode('latin-1')] = chunk_data[null+1:].decode('latin-1')
            except Exception:
                pass
        elif chunk_type == b'iTXt':
            try:
                null = chunk_data.index(b'\x00')
                key = chunk_data[:null].decode('utf-8')
                rest = chunk_data[null+1:]
                compress_flag = rest[0]
                rest = rest[2:]
                rest = rest[rest.index(b'\x00')+1:]
                value_bytes = rest[rest.index(b'\x00')+1:]
                if compress_flag:
                    value_bytes = zlib.decompress(value_bytes)
                meta[key] = value_bytes.decode('utf-8')
            except Exception:
                pass
        elif chunk_type == b'zTXt':
            try:
                null = chunk_data.index(b'\x00')
                key = chunk_data[:null].decode('latin-1')
                meta[key] = zlib.decompress(chunk_data[null+2:]).decode('latin-1')
            except Exception:
                pass
    return meta


def read_image_metadata(image_path):
    """
    Strategy:
      PNG  → parse chunks directly (fast, reliable for SD) + optionally enrich via exiftool
      JPEG → exiftool only
      WebP → exiftool only (manual RIFF parsing was unreliable)
    Returns a normalised dict (canonical SD field names).
    """
    path = Path(image_path)
    ext = path.suffix.lower()
    raw = {}

    try:
        if ext == '.png':
            raw = _read_png_chunks(path)
            # If exiftool available, merge extra fields (EXIF, XMP) that chunks don't cover
            if _exiftool_available():
                et = _read_via_exiftool(image_path)
                # PNG chunks have priority for SD params; exiftool fills gaps
                for k, v in et.items():
                    if k not in raw:
                        raw[k] = v
        elif ext in ('.jpg', '.jpeg', '.webp'):
            raw = _read_via_exiftool(image_path)
            if not raw:
                raw['_no_exiftool'] = (
                    'exiftool not found. Place exiftool.exe in tools/ to read JPEG/WebP metadata.'
                )
    except Exception as e:
        print(f"[metadata] Error reading {image_path}: {e}")

    return parse_sd_metadata(raw)


def parse_sd_metadata(raw):
    """
    Normalise raw metadata dict into canonical SD field names.
    Handles both PNG-chunk keys and exiftool-style keys.
    """
    result = {}

    # ── SD parameters string (PNG chunks / exiftool UserComment / Description) ──
    params_str = (
        raw.get('parameters') or
        raw.get('Parameters') or
        raw.get('UserComment') or
        raw.get('Comment') or
        raw.get('ImageDescription') or
        raw.get('Description') or
        ''
    )

    if params_str and not params_str.startswith('exiftool'):
        result['_raw_parameters'] = params_str
        _parse_sd_params_string(params_str, result)

    # ── Direct exiftool field mappings (JPEG / WebP EXIF/XMP) ──────────────────
    _map = {
        'Model':          ('model',   result.get('model')),
        'Make':           ('make',    None),
        'Software':       ('software',None),
        'ExifImageWidth': ('width',   None),
        'ExifImageHeight':('height',  None),
        'CreateDate':     ('date',    None),
        'XMP:Description':('xmp_desc',None),
        'XMP:Subject':    ('xmp_subject', None),
        'IPTC:Caption-Abstract': ('iptc_caption', None),
    }
    for et_key, (canon_key, existing) in _map.items():
        if et_key in raw and not existing:
            result[canon_key] = raw[et_key]

    # ── Pass-through: keep any unrecognised exiftool field with its original name ─
    _known_raw = {'parameters', 'Parameters', 'UserComment', 'Comment',
                  'ImageDescription', 'Description', '_no_exiftool'}
    for k, v in raw.items():
        if k not in _known_raw and k not in result:
            # Only surface fields that look useful (skip binary blobs etc.)
            if isinstance(v, str) and len(v) < 1000 and not k.startswith('_'):
                result[f'_{k}'] = v

    # Surface no-exiftool warning
    if '_no_exiftool' in raw:
        result['_warning'] = raw['_no_exiftool']

    return result


def _parse_sd_params_string(params_str, result):
    """
    Parse the SD 'parameters' text block into result dict.
    Format:  <prompt>\nNegative prompt: <neg>\nSteps: X, Sampler: Y, CFG scale: Z, ...
    """
    lines = params_str.strip().split('\n')

    neg_idx   = next((i for i, l in enumerate(lines)
                      if l.strip().lower().startswith('negative prompt:')), None)
    steps_idx = next((i for i, l in enumerate(lines)
                      if l.strip().lower().startswith('steps:')), None)

    if neg_idx is not None:
        result['prompt'] = '\n'.join(lines[:neg_idx]).strip()
        end = steps_idx if (steps_idx is not None and steps_idx > neg_idx) else len(lines)
        result['negative_prompt'] = (
            '\n'.join(lines[neg_idx:end])
            .replace('Negative prompt:', '', 1).strip()
        )
    elif steps_idx is not None:
        result['prompt'] = '\n'.join(lines[:steps_idx]).strip()
    else:
        result['prompt'] = params_str.strip()

    settings_line = ' '.join(lines[steps_idx:]) if steps_idx is not None else ''
    _parse_sd_settings(settings_line, result)


def _parse_sd_settings(line, result):
    """Parse 'Steps: X, Sampler: Y, CFG scale: Z, ...' into result dict."""
    patterns = {
        'steps':      r'Steps:\s*(\d+)',
        'sampler':    r'Sampler:\s*([^,]+)',
        'cfg':        r'CFG scale:\s*([\d.]+)',
        'seed':       r'Seed:\s*(\d+)',
        'size':       r'Size:\s*([^\s,]+)',
        'model':      r'Model:\s*([^,]+)',
        'model_hash': r'Model hash:\s*([^,]+)',
        'vae':        r'VAE:\s*([^,]+)',
        'clip_skip':  r'Clip skip:\s*(\d+)',
        'lora_hashes':r'Lora hashes:\s*"([^"]+)"',
        'scheduler':  r'Schedule type:\s*([^,]+)',
        'distilled_cfg': r'Distilled CFG Scale:\s*([\d.]+)',
    }
    for key, pattern in patterns.items():
        if key not in result:  # don't overwrite values already set
            m = re.search(pattern, line, re.IGNORECASE)
            if m:
                result[key] = m.group(1).strip()


def format_metadata_for_display(card):
    """
    Format card.all_metadata into a human-readable string for the fullscreen overlay.
    Priority fields first, then prompt/neg, then any extra exiftool fields.
    """
    meta = getattr(card, 'all_metadata', {})
    if not meta:
        return ""

    lines = []

    # Warning (e.g. exiftool missing)
    if '_warning' in meta:
        lines.append(f"⚠ {meta['_warning']}")
        lines.append('')

    priority = [
        ('model',        'Model'),
        ('sampler',      'Sampler'),
        ('scheduler',    'Schedule'),
        ('steps',        'Steps'),
        ('cfg',          'CFG'),
        ('distilled_cfg','Distilled CFG'),
        ('seed',         'Seed'),
        ('size',         'Size'),
        ('vae',          'VAE'),
        ('clip_skip',    'Clip skip'),
        ('lora_hashes',  'LoRAs'),
        ('software',     'Software'),
        ('date',         'Date'),
    ]
    for key, label in priority:
        if key in meta:
            lines.append(f"{label}: {meta[key]}")

    if 'prompt' in meta:
        p = meta['prompt']
        if len(p) > 250:
            p = p[:250] + '…'
        lines.append(f"\nPrompt:\n{p}")

    if 'negative_prompt' in meta:
        n = meta['negative_prompt']
        if len(n) > 180:
            n = n[:180] + '…'
        lines.append(f"\nNeg:\n{n}")

    # Extra exiftool pass-through fields (prefixed with _)
    extras = [(k[1:], v) for k, v in meta.items()
              if k.startswith('_') and k not in ('_raw_parameters', '_warning')]
    if extras:
        lines.append('\n— Extra —')
        for k, v in extras[:12]:  # cap at 12 extra fields
            if len(v) > 80:
                v = v[:80] + '…'
            lines.append(f"{k}: {v}")

    return '\n'.join(lines)




class Grid2ImgDialog(QDialog):
    from config.options_style import apply_options_style

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Grid2Img")
        self.resize(320, 420)
        self.apply_options_style()

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Optional title")
        form.addRow("Title:", self.title_edit)

        self.bg_combo = QComboBox()
        self.bg_combo.addItems(["White", "Black", "Gray", "Light Gray"])
        form.addRow("Background:", self.bg_combo)

        self.spacing_spin = QSpinBox()
        self.spacing_spin.setRange(0, 100)
        self.spacing_spin.setValue(10)
        form.addRow("Spacing:", self.spacing_spin)

        self.padding_spin = QSpinBox()
        self.padding_spin.setRange(0, 200)
        self.padding_spin.setValue(20)
        form.addRow("Padding:", self.padding_spin)

        self.title_size_spin = QSpinBox()
        self.title_size_spin.setRange(10, 96)
        self.title_size_spin.setValue(24)
        form.addRow("Title size:", self.title_size_spin)

        self.text_size_spin = QSpinBox()
        self.text_size_spin.setRange(8, 48)
        self.text_size_spin.setValue(14)
        form.addRow("Text size:", self.text_size_spin)

        layout.addLayout(form)
        layout.addWidget(QLabel("Fields to print under each image:"))

        self.field_prompt = QCheckBox("Prompt")
        self.field_checkpoint = QCheckBox("Checkpoint")
        self.field_cfg = QCheckBox("CFG")
        self.field_sampler = QCheckBox("Sampler")
        self.field_steps = QCheckBox("Steps")
        self.field_seed = QCheckBox("Seed")
        self.field_lora = QCheckBox("LoRA")
        self.field_lora_strength = QCheckBox("LoRA strength")
        self.field_checkpoint.setChecked(True)

        for w in [
            self.field_prompt, self.field_checkpoint, self.field_cfg, self.field_sampler,
            self.field_steps, self.field_seed, self.field_lora, self.field_lora_strength,
        ]:
            layout.addWidget(w)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_options(self):
        bg_map = {
            "White": QColor("white"),
            "Black": QColor("black"),
            "Gray": QColor(128, 128, 128),
            "Light Gray": QColor(235, 235, 235),
        }
        fields = []
        if self.field_prompt.isChecked():
            fields.append("prompt")
        if self.field_checkpoint.isChecked():
            fields.append("checkpoint")
        if self.field_cfg.isChecked():
            fields.append("cfg")
        if self.field_sampler.isChecked():
            fields.append("sampler")
        if self.field_steps.isChecked():
            fields.append("steps")
        if self.field_seed.isChecked():
            fields.append("seed")
        if self.field_lora.isChecked():
            fields.append("lora")
        if self.field_lora_strength.isChecked():
            fields.append("lora_strength")
        return {
            "title": self.title_edit.text().strip(),
            "background": bg_map[self.bg_combo.currentText()],
            "spacing": self.spacing_spin.value(),
            "padding": self.padding_spin.value(),
            "title_size": self.title_size_spin.value(),
            "text_size": self.text_size_spin.value(),
            "fields": fields,
        }

# ── Tab widget ────────────────────────────────────────────────────────────────

class CustomTabBar(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tabBar().installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj == self.tabBar() and event.type() == event.Type.MouseButtonDblClick:
            index = self.tabBar().tabAt(event.pos())
            if index >= 0:
                main_window = self.window()
                if isinstance(main_window, MainWindow):
                    main_window.close_tab_at_index(index)
                return True
        return super().eventFilter(obj, event)


# ── Options dialog ────────────────────────────────────────────────────────────

class OptionsDialog(QDialog):
    from config.options_style import apply_options_style

    def __init__(self, parent=None):
        super().__init__(parent)
        self._initial_style = config.get('current_style')
        self._initial_module_style = config.get('current_module_style')
        self.setWindowTitle(config.get_text('options_title'))
        self.setModal(True)
        self.setMinimumSize(500, 490)
        self.apply_options_style()

        main_layout = QVBoxLayout()
        main_layout.setSpacing(4)
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_general_tab(), config.get_text('options_tab_general'))
        self.tabs.addTab(self.create_personalization_tab(), config.get_text('options_tab_style'))
        self.tabs.addTab(self.create_modules_tab(), config.get_text('options_tab_modules'))

        info_row = QHBoxLayout()
        info_row.setContentsMargins(4, 0, 4, 0)
        info_icon = QLabel("ℹ️")
        self.options_info_label = QLabel("")
        self.options_info_label.setStyleSheet("color: #888; font-style: italic;")
        self.options_info_label.setWordWrap(True)
        _font = self.options_info_label.font()
        self.options_info_label.setFont(_font)
        info_row.addWidget(info_icon, 0, Qt.AlignmentFlag.AlignTop)
        info_row.addWidget(self.options_info_label, 1, Qt.AlignmentFlag.AlignTop)
        info_widget = QWidget()
        info_widget.setFixedHeight(35)
        info_widget.setLayout(info_row)

        close_btn = QPushButton(config.get_text('options_close'))
        close_btn.clicked.connect(self.save_and_close)

        main_layout.addWidget(self.tabs)
        main_layout.addWidget(info_widget)
        main_layout.addWidget(close_btn)
        self.setLayout(main_layout)

    def create_general_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        lang_group = QGroupBox(config.get_text('options_language'))
        lang_layout = QVBoxLayout()
        lang_layout.setContentsMargins(12, 12, 12, 12)

        self.lang_list = QListWidget()
        self.lang_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.lang_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.lang_list.setMovement(QListWidget.Movement.Static)
        self.lang_list.setIconSize(QSize(24, 16))
        self.lang_list.setGridSize(QSize(100, 40))
        self.lang_list.setFixedHeight(84)
        self.lang_list.setSpacing(2)

        current_lang = config.get('language')
        for lang_key, lang_info in config.get_languages().items():
            item = self._build_lang_list_item(lang_key, lang_info)
            self.lang_list.addItem(item)
            if lang_key == current_lang:
                self.lang_list.setCurrentItem(item)

        lang_layout.addWidget(self.lang_list)
        lang_group.setLayout(lang_layout)
        lang_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        import_group = QGroupBox(config.get_text('options_import_mode'))
        import_layout = QHBoxLayout()
        self.import_replace = QCheckBox(config.get_text('options_import_replace'))
        self.import_add = QCheckBox(config.get_text('options_import_add'))
        (self.import_add if config.get('import_mode') == 'add' else self.import_replace).setChecked(True)
        self.import_replace.toggled.connect(lambda c: self.import_add.setChecked(not c) if c else None)
        self.import_add.toggled.connect(lambda c: self.import_replace.setChecked(not c) if c else None)
        import_layout.addWidget(self.import_add)
        import_layout.addWidget(self.import_replace)
        import_layout.addStretch()
        import_group.setLayout(import_layout)

        self.import_in_tabs = QCheckBox(config.get_text('options_import_in_tabs'))
        self.import_in_tabs.setChecked(config.get('import_in_tabs'))
        self.auto_load_last = QCheckBox(config.get_text('options_auto_load_last'))
        self.auto_load_last.setChecked(config.get('auto_load_last'))
        self.auto_save_session = QCheckBox(config.get_text('options_auto_save_session'))
        self.auto_save_session.setChecked(config.get('auto_save_session'))
        self.show_title = QCheckBox(config.get_text('options_show_title'))
        self.show_title.setChecked(config.get('show_title') or False)
        self.show_description = QCheckBox(config.get_text('options_show_description'))
        self.show_description.setChecked(config.get('show_description') or False)
        self.read_metadata = QCheckBox(config.get_text('options_read_metadata'))
        self.read_metadata.setChecked(config.get('read_metadata') or False)

        # Fullscreen opacity
        opacity_row = QHBoxLayout()
        opacity_label = QLabel(config.get_text('options_fullscreen_opacity') + ":")
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setMinimum(1)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(config.get('fullscreen_opacity') or 100)
        self.opacity_slider.setFixedWidth(120)
        self.opacity_spinbox = QLineEdit(str(self.opacity_slider.value()))
        self.opacity_spinbox.setFixedWidth(40)
        self.opacity_spinbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.opacity_slider.valueChanged.connect(lambda v: self.opacity_spinbox.setText(str(v)))
        self.opacity_spinbox.editingFinished.connect(self._sync_opacity_spinbox)
        opacity_row.addWidget(opacity_label)
        opacity_row.addWidget(self.opacity_slider)
        opacity_row.addWidget(self.opacity_spinbox)
        opacity_row.addWidget(QLabel("%"))
        opacity_row.addStretch()
        opacity_widget = QWidget()
        opacity_widget.setLayout(opacity_row)

        self._install_option_hover(import_group, 'hint_import_mode')
        self._install_option_hover(self.import_in_tabs, 'hint_import_in_tabs')
        self._install_option_hover(self.auto_load_last, 'hint_auto_load_last')
        self._install_option_hover(self.auto_save_session, 'hint_auto_save_session')
        self._install_option_hover(self.read_metadata, 'hint_read_metadata')

        layout.addWidget(lang_group)
        layout.addWidget(import_group)
        layout.addWidget(self.import_in_tabs)
        layout.addWidget(self.auto_load_last)
        layout.addWidget(self.auto_save_session)
        layout.addWidget(self.show_title)
        layout.addWidget(self.show_description)
        layout.addWidget(self.read_metadata)
        layout.addWidget(opacity_widget)
        layout.addStretch()
        tab.setLayout(layout)
        return tab

    def create_personalization_tab(self):
        from config.style_editor import StyleEditorWidget
        tab = QWidget()
        layout = QVBoxLayout()
        self.style_editor = StyleEditorWidget(config, self)
        layout.addWidget(self.style_editor)
        tab.setLayout(layout)
        return tab

    def create_modules_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        current_module = config.get('selected_module')

        self.module_checkboxes = {}
        self.module_settings_widgets = []

        self.module_none = QCheckBox(config.get_text('options_module_none'))
        self.module_none.setChecked(current_module is None)
        layout.addWidget(self.module_none)

        for key, module_class in MODULE_REGISTRY.items():
            name = module_class.get_module_name() if hasattr(module_class, 'get_module_name') else key
            cb = QCheckBox(name)
            cb.setChecked(current_module == key)
            self.module_checkboxes[key] = cb
            layout.addWidget(cb)

            if hasattr(module_class, 'get_settings_widget'):
                extra = module_class.get_settings_widget(config)
                if extra:
                    layout.addWidget(extra)
                    self.module_settings_widgets.append(extra)

        def on_none(checked):
            if checked:
                for c in self.module_checkboxes.values():
                    c.setChecked(False)
            elif not any(c.isChecked() for c in self.module_checkboxes.values()):
                self.module_none.setChecked(True)

        def make_exclusive(selected_key):
            def on_toggle(checked):
                if checked:
                    self.module_none.setChecked(False)
                    for k, c in self.module_checkboxes.items():
                        if k != selected_key:
                            c.setChecked(False)
                elif not any(c.isChecked() for c in self.module_checkboxes.values()):
                    self.module_none.setChecked(True)
            return on_toggle

        self.module_none.toggled.connect(on_none)
        for key, cb in self.module_checkboxes.items():
            cb.toggled.connect(make_exclusive(key))

        layout.addStretch()
        tab.setLayout(layout)
        return tab

    def _install_option_hover(self, widget, hint_key):
        widget.enterEvent = lambda e, k=hint_key: self.options_info_label.setText(config.get_text(k))
        widget.leaveEvent = lambda e: self.options_info_label.setText("")

    @staticmethod
    def _build_lang_list_item(lang_key, lang_info):
        from pathlib import Path as _Path
        item = QListWidgetItem(lang_info['name'])
        item.setData(Qt.ItemDataRole.UserRole, lang_key)
        icon_rel = lang_info.get('icon')
        icon_path = (_Path(__file__).parent / 'config' / 'lang' / icon_rel
                     if icon_rel else None)
        if icon_path and icon_path.exists():
            item.setIcon(QIcon(str(icon_path)))
        else:
            placeholder = QPixmap(24, 16)
            placeholder.fill(Qt.GlobalColor.transparent)
            item.setIcon(QIcon(placeholder))
        return item

    def _sync_opacity_spinbox(self):
        try:
            v = max(1, min(100, int(self.opacity_spinbox.text())))
        except ValueError:
            v = self.opacity_slider.value()
        self.opacity_slider.setValue(v)
        self.opacity_spinbox.setText(str(v))

    def save_and_close(self):
        old_lang = config.get('language')
        old_show_title = config.get('show_title')
        old_show_description = config.get('show_description')
        old_module = config.get('selected_module')

        selected_lang_item = self.lang_list.currentItem()
        if selected_lang_item:
            config.set_language(selected_lang_item.data(Qt.ItemDataRole.UserRole))
        config.set_import_mode('replace' if self.import_replace.isChecked() else 'add')
        config.set_import_in_tabs(self.import_in_tabs.isChecked())
        config.set_auto_load_last(self.auto_load_last.isChecked())
        config.set_auto_save_session(self.auto_save_session.isChecked())
        config.set('show_title', self.show_title.isChecked())
        config.set('show_description', self.show_description.isChecked())
        config.set('read_metadata', self.read_metadata.isChecked())
        config.set('fullscreen_opacity', self.opacity_slider.value())

        selected_module = next(
            (key for key, cb in self.module_checkboxes.items() if cb.isChecked()), None)
        config.set_selected_module(selected_module)

        for widget in self.module_settings_widgets:
            if hasattr(widget, 'save'):
                widget.save()

        lang_changed = config.get('language') != old_lang
        cards_need_refresh = (
            lang_changed or
            selected_module != old_module or
            config.get('show_title') != old_show_title or
            config.get('show_description') != old_show_description
        )

        if isinstance(self.parent(), MainWindow):
            self.parent().refresh_ui_texts(lang_changed)
            self.parent().apply_styles()

        self.accept()

    def _cancel_style_changes(self):
        changed = (config.get('current_style') != self._initial_style or
                   config.get('current_module_style') != self._initial_module_style)
        if changed:
            config.set_current_style(self._initial_style)
            config.set('current_module_style', self._initial_module_style)
            if isinstance(self.parent(), MainWindow):
                self.parent().apply_styles()

    def reject(self):
        self._cancel_style_changes()
        super().reject()

    def closeEvent(self, event):
        self._cancel_style_changes()
        super().closeEvent(event)


# ── Image card ────────────────────────────────────────────────────────────────

class ImageCard(QFrame):
    positionChanged = pyqtSignal()

    def __init__(self, image_path, parent=None,
                 source_json=None, module_data=None, raw_json_data=None):
        super().__init__(parent)
        self.image_path = image_path
        self.source_json = source_json
        self.module_data = module_data or {}
        self.raw_json_data = raw_json_data or {}
        self.all_metadata = {}  # populated after init if read_metadata is enabled

        self.setFrameStyle(QFrame.Shape.Box)
        self.setLineWidth(2)
        self.setAcceptDrops(True)
        self.drag_start_pos = None
        self.press_timer = QTimer()
        self.press_timer.setSingleShot(True)
        self.press_timer.timeout.connect(self.start_drag_operation)
        self.long_press_started = False

        self.setStyleSheet(get_styles().card_style())
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.details_popup = None

        # Read metadata if enabled
        if config.get('read_metadata'):
            self.all_metadata = read_image_metadata(image_path)

        self.setup_ui()

    def get_active_module(self):
        module_name = config.get('selected_module')
        return MODULE_REGISTRY.get(module_name) if module_name else None

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)

        top_container = QWidget()
        top_outer = QVBoxLayout()
        top_outer.setContentsMargins(0, 0, 0, 0)
        top_outer.setSpacing(2)

        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(25, 25)
        self.close_btn.setStyleSheet(get_styles().close_button())
        self.close_btn.clicked.connect(self.delete_card)
        top_layout.addWidget(self.close_btn)
        top_layout.addStretch()

        module = self.get_active_module()
        if module and hasattr(module, 'populate_card_top'):
            module.populate_card_top(self, top_layout)

        top_outer.addLayout(top_layout)

        self.title_edit = None
        if config.get('show_title'):
            self.title_edit = QLineEdit()
            self.title_edit.setPlaceholderText(config.get_text('card_title_placeholder'))
            self.title_edit.setText(self.raw_json_data.get('title', ''))
            self.title_edit.setStyleSheet(self._title_edit_style())
            self.title_edit.textChanged.connect(lambda: self.title_edit.setStyleSheet(self._title_edit_style()))
            top_outer.addWidget(self.title_edit)

        top_container.setLayout(top_outer)

        image_container = QWidget()
        img_layout = QHBoxLayout()
        img_layout.setContentsMargins(0, 0, 0, 0)
        img_layout.addStretch()
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setScaledContents(False)
        pixmap = QPixmap(self.image_path)
        if not pixmap.isNull():
            cropped = self.smart_square_crop(pixmap)
            self.image_label.setPixmap(
                cropped.scaled(200, 200, Qt.AspectRatioMode.IgnoreAspectRatio,
                               Qt.TransformationMode.SmoothTransformation))
        img_layout.addWidget(self.image_label)
        img_layout.addStretch()
        image_container.setLayout(img_layout)

        bottom_widget = None
        if module and hasattr(module, 'build_card_bottom'):
            bottom_widget = module.build_card_bottom(self)
            if bottom_widget is not None:
                bottom_widget.setParent(self)

        self.description_edit = None
        if config.get('show_description'):
            self.description_edit = QTextEdit()
            self.description_edit.setFixedHeight(55)
            self.description_edit.setPlaceholderText(config.get_text('card_description_placeholder'))
            self.description_edit.setPlainText(self.raw_json_data.get('description', ''))
            _c = get_styles().COLORS
            self.description_edit.setStyleSheet(
                f"QTextEdit {{ background: {_c.get('bg2')}; "
                f"color: {_c.get('text1')}; "
                f"border: 1px solid {_c.get('border1')}; "
                f"border-radius: 4px; font-size: 11px; padding: 2px; }}"
            )
        if bottom_widget or self.description_edit:
            wrapper = QWidget()
            wl = QVBoxLayout()
            wl.setContentsMargins(0, 0, 0, 0)
            wl.setSpacing(3)
            if bottom_widget:
                wl.addWidget(bottom_widget)
            if self.description_edit:
                wl.addWidget(self.description_edit)
            wrapper.setLayout(wl)
            bottom_widget = wrapper
        else:
            bottom_widget = None

        self._top_container = top_container
        self._image_container = image_container
        self._bottom_widget = bottom_widget

        layout.addWidget(top_container)
        layout.addWidget(image_container)
        if bottom_widget:
            layout.addWidget(bottom_widget)

        self.setLayout(layout)
        self._apply_container_bg()

    def smart_square_crop(self, pixmap):
        w, h = pixmap.width(), pixmap.height()
        new_size = int(max(w, h) * 0.8)
        x = (w - new_size) // 2
        y = (h - new_size) // 2
        return pixmap.copy(x, y, new_size, new_size)

    def _apply_container_bg(self):
        bg = get_styles().COLORS.get('bg2', '#2b2b2b')
        style = f"background-color: {bg};"
        self._top_container.setStyleSheet(style)
        self._image_container.setStyleSheet(style)
        if self._bottom_widget:
            self._bottom_widget.setStyleSheet(style)

    def _title_edit_style(self):
        c = get_styles().COLORS
        filled = self.title_edit is not None and self.title_edit.text() != ""
        border_color = c['text1'] if filled else c['border1']
        return (
            f"QLineEdit {{ background: transparent; border: none; "
            f"border-bottom: 1px solid {border_color}; color: {c['text1']}; "
            f"font-size: 11px; padding: 1px 3px; }}"
            f"QLineEdit:focus {{ border-bottom: 1px solid {c['text1']}; }}"
        )

    def apply_styles(self):
        self.close_btn.setStyleSheet(get_styles().close_button())
        self._apply_container_bg()
        self.setStyleSheet(get_styles().card_style())
        if self.title_edit:
            self.title_edit.setStyleSheet(self._title_edit_style())
        module = self.get_active_module()
        if module and hasattr(module, 'apply_card_styles'):
            module.apply_card_styles(self)

    def delete_card(self):
        grid_tab = self.find_grid_tab()
        if grid_tab:
            grid_tab.remove_card(self)

    def find_grid_tab(self):
        parent = self.parent()
        while parent:
            if isinstance(parent, GridTab):
                return parent
            parent = parent.parent()
        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.pos()
            self.press_timer.start(500)
            self.long_press_started = False
        elif event.button() == Qt.MouseButton.RightButton:
            self.show_details()

    def mouseReleaseEvent(self, event):
        self.press_timer.stop()
        if event.button() == Qt.MouseButton.LeftButton and not self.long_press_started:
            grid_tab = self.find_grid_tab()
            if grid_tab:
                grid_tab.show_fullscreen(self)

    def mouseMoveEvent(self, event):
        if self.long_press_started and event.buttons() & Qt.MouseButton.LeftButton:
            if (event.pos() - self.drag_start_pos).manhattanLength() > 10:
                self.perform_drag()

    def start_drag_operation(self):
        self.long_press_started = True

    def perform_drag(self):
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(self.image_path)
        drag.setMimeData(mime_data)
        pixmap = self.image_label.pixmap()
        if pixmap:
            drag.setPixmap(pixmap.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio))
        drag.exec(Qt.DropAction.MoveAction)

    def dragEnterEvent(self, event):
        if event.source() != self and event.source().__class__.__name__ == 'ImageCard':
            event.acceptProposedAction()
            self._original_stylesheet = self.styleSheet()
            styles = get_styles()
            self.setStyleSheet(
                f"ImageCard {{ border: 3px solid {styles.COLORS['accent']}; "
                f"border-radius: 12px; background: {styles.COLORS['bg2']}; }}")

    def dragLeaveEvent(self, event):
        if hasattr(self, '_original_stylesheet'):
            self.setStyleSheet(self._original_stylesheet)
        else:
            self.apply_styles()

    def dropEvent(self, event):
        source_card = event.source()
        if isinstance(source_card, ImageCard) and source_card != self:
            grid_tab = self.find_grid_tab()
            if grid_tab:
                grid_tab.swap_cards(source_card, self)
            event.acceptProposedAction()
        if hasattr(self, '_original_stylesheet'):
            self.setStyleSheet(self._original_stylesheet)
            delattr(self, '_original_stylesheet')
        else:
            self.apply_styles()

    def show_details(self):
        grid_tab = self.find_grid_tab()
        if grid_tab:
            if grid_tab.active_details_dialog:
                grid_tab.active_details_dialog.close()
            self.details_popup = CardDetailsDialog(self, self.window())
            grid_tab.active_details_dialog = self.details_popup
            self.details_popup.show_near_card()


# ── Grid tab ──────────────────────────────────────────────────────────────────

class GridTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.cards = []
        self.module_state = {}
        self.card_size = 210
        self.active_details_dialog = None
        self.last_imported_json = None
        self.setup_ui()
        self.apply_theme()

    def get_active_module(self):
        module_name = config.get('selected_module')
        return MODULE_REGISTRY.get(module_name) if module_name else None

    def setup_ui(self):
        main_layout = QVBoxLayout()

        controls1 = QHBoxLayout()
        self.controls1_widget = QWidget()
        self.controls1_widget.setLayout(controls1)

        self.close_tab_btn = QPushButton("×")
        self.close_tab_btn.setFixedSize(30, 30)
        self.close_tab_btn.setStyleSheet("font-weight: bold; font-size: 16px;")
        self.close_tab_btn.clicked.connect(self.close_current_tab)

        self.options_btn = QPushButton(config.get_text('btn_options'))
        self.options_btn.clicked.connect(self.open_options)
        self.options_btn.setStyleSheet(get_styles().options_button())

        self.module_dropdown = QComboBox()
        self.module_dropdown.setMinimumWidth(150)
        self.update_module_dropdown()
        self.module_dropdown.currentIndexChanged.connect(self.on_module_action_selected)

        self.import_btn = QPushButton(config.get_text('btn_import'))
        self.import_btn.clicked.connect(self.import_grid)

        self.save_tabs_btn = QPushButton(config.get_text('btn_save_tabs'))
        self.save_tabs_btn.clicked.connect(self.save_tabs_manually)

        self.grid2img_btn = QPushButton("Grid2Img")
        self.grid2img_btn.clicked.connect(self.open_grid2img_dialog)

        self.export_btn = QPushButton(config.get_text('btn_export'))
        self.export_btn.clicked.connect(self.export_grid)

        self.clear_btn = QPushButton(config.get_text('btn_clear'))
        self.clear_btn.setStyleSheet(get_styles().clear_button())
        self.clear_btn.clicked.connect(self.clear_grid)

        self.refresh_btn = QPushButton(config.get_text('btn_refresh'))
        self.refresh_btn.setStyleSheet(get_styles().refresh_button())
        self.refresh_btn.clicked.connect(self.refresh_cards)

        controls1.addWidget(self.close_tab_btn)
        controls1.addWidget(self.options_btn)
        controls1.addWidget(self.module_dropdown)
        controls1.addWidget(self.import_btn)
        controls1.addWidget(self.save_tabs_btn)
        controls1.addWidget(self.grid2img_btn)
        controls1.addWidget(self.export_btn)
        controls1.addWidget(self.clear_btn)
        controls1.addWidget(self.refresh_btn)
        controls1.addStretch()

        controls2 = QHBoxLayout()
        self.controls2_widget = QWidget()
        self.controls2_widget.setLayout(controls2)
        self.controls2_widget.setFixedHeight(36)

        log_label = QLabel("ℹ️ Info :")
        log_label.setStyleSheet("font-weight: bold;")
        self.log_label = QLabel("")
        self.log_label.setStyleSheet(f"color: {get_styles().COLORS['text2']};")
        self.log_label.setMinimumWidth(300)
        self._hover_label = QLabel("")
        self._hover_label.setMinimumWidth(300)
        self._log_stack = QStackedWidget()
        self._log_stack.addWidget(self.log_label)
        self._log_stack.addWidget(self._hover_label)
        self.size_label = QLabel(config.get_text('slider_label') + ":")
        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setMinimum(210)
        self.size_slider.setMaximum(1200)
        self.size_slider.setValue(210)
        self.size_slider.setFixedWidth(150)
        self.size_slider.sliderReleased.connect(self.on_slider_released)

        controls2.addWidget(log_label)
        controls2.addWidget(self._log_stack)
        controls2.addStretch()
        controls2.addWidget(self.size_label)
        controls2.addWidget(self.size_slider)

        self.drop_zone = QLabel(config.get_text('drop_zone_text'))
        self.drop_zone.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_zone.setStyleSheet(get_styles().drop_zone())
        self.drop_zone.setAcceptDrops(True)
        self.drop_zone.dragEnterEvent = self.drop_zone_drag_enter
        self.drop_zone.dropEvent = self.drop_zone_drop
        self.drop_zone.mousePressEvent = self.drop_zone_click

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.verticalScrollBar().valueChanged.connect(self.close_active_dialog)
        self.scroll_area.horizontalScrollBar().valueChanged.connect(self.close_active_dialog)
        self.scroll_widget = QWidget()
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(15)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.scroll_widget.setLayout(self.grid_layout)
        self.scroll_area.setWidget(self.scroll_widget)

        main_layout.addWidget(self.controls1_widget)
        main_layout.addWidget(self.controls2_widget)
        main_layout.addWidget(self.drop_zone)
        main_layout.addWidget(self.scroll_area)
        self.setLayout(main_layout)

        self._install_hover(self.close_tab_btn, 'hover_close_tab', 'accent')
        self._install_hover(self.clear_btn,     'hover_clear_tab', 'danger')

    def _install_hover(self, button, text_key, color_key):
        button.enterEvent = lambda e, k=text_key, c=color_key: self._show_hover(k, c)
        button.leaveEvent = lambda e: self._hide_hover()

    # ── Module dropdown ───────────────────────────────────────────────────────

    def update_module_dropdown(self):
        self.module_dropdown.clear()
        module_name = config.get('selected_module')
        if module_name and module_name in MODULE_REGISTRY:
            module = MODULE_REGISTRY[module_name]
            options = module.get_dropdown_options() if hasattr(module, 'get_dropdown_options') else []
            if options:
                self.module_dropdown.addItem(config.get_text('dropdown_select_action'))
                for key in options:
                    label = config.get_text(key) if key.startswith('dataset_action') else key
                    self.module_dropdown.addItem(label, userData=key)
            else:
                name = module.get_module_name() if hasattr(module, 'get_module_name') else module_name
                self.module_dropdown.addItem(f"< {name} >")
        else:
            self.module_dropdown.addItem(config.get_text('dropdown_no_module'))
        self.module_dropdown.setCurrentIndex(0)

    def on_module_action_selected(self, index):
        if index <= 0:
            return
        text = self.module_dropdown.currentText()
        if text in (config.get_text('dropdown_no_module'), config.get_text('dropdown_select_action')):
            return

        module_name = config.get('selected_module')
        if not module_name or module_name not in MODULE_REGISTRY:
            return

        module = MODULE_REGISTRY[module_name]
        if not hasattr(module, 'handle_dropdown_action'):
            return

        key = self.module_dropdown.currentData() or text
        result = module.handle_dropdown_action(key, self)
        if result and result.get('log'):
            self.log(result['log'])

        self.module_dropdown.setCurrentIndex(0)

    # ── Options ───────────────────────────────────────────────────────────────

    def open_options(self):
        old_module = config.get('selected_module')
        old_show_title = config.get('show_title')
        old_show_description = config.get('show_description')
        dialog = OptionsDialog(self.get_main_window())
        dialog.exec()
        cards_need_refresh = (
            old_module != config.get('selected_module') or
            old_show_title != config.get('show_title') or
            old_show_description != config.get('show_description')
        )
        if cards_need_refresh:
            self.refresh_cards()
        self.update_module_dropdown()

    # ── Logging ───────────────────────────────────────────────────────────────

    def _show_hover(self, text_key, color_key):
        color = get_styles().COLORS.get(color_key, get_styles().COLORS['accent'])
        self._hover_label.setText(config.get_text(text_key))
        self._hover_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        self._log_stack.setCurrentIndex(1)

    def _hide_hover(self):
        self._log_stack.setCurrentIndex(0)

    def _get_module_name(self):
        module_name = config.get('selected_module')
        if module_name and module_name in MODULE_REGISTRY:
            module = MODULE_REGISTRY[module_name]
            return module.get_module_name() if hasattr(module, 'get_module_name') else module_name
        return ""

    def _build_idle_text(self):
        parts = []
        module = self._get_module_name()
        if module:
            parts.append(module)
        if getattr(self, 'last_imported_json', None):
            parts.append(os.path.basename(self.last_imported_json))
        n = len(self.cards) if hasattr(self, 'cards') else 0
        if n > 0:
            parts.append(f"{n} images")
        return " - ".join(parts)

    def _set_idle(self):
        try:
            if self.log_label is not None:
                self.log_label.setText(self._build_idle_text())
                self.log_label.setStyleSheet(f"color: {get_styles().COLORS['text2']};")
        except RuntimeError:
            pass

    def log(self, message):
        module = self._get_module_name()
        text = f"{module} - {message}" if module else message
        self.log_label.setText(text)
        self.log_label.setStyleSheet(f"color: {get_styles().COLORS['accent']}; font-weight: bold;")
        QTimer.singleShot(3000, self._set_idle)

    def safe_clear_log(self):
        self._set_idle()

    # ── Styles ────────────────────────────────────────────────────────────────

    def apply_theme(self):
        self.setStyleSheet(get_styles().main_theme())
        self.drop_zone.setStyleSheet(get_styles().drop_zone())

    def apply_styles(self):
        styles = get_styles()
        self.setStyleSheet(styles.main_theme())
        self.drop_zone.setStyleSheet(styles.drop_zone())
        self.options_btn.setStyleSheet(styles.options_button())
        self.clear_btn.setStyleSheet(styles.clear_button())
        self.refresh_btn.setStyleSheet(styles.refresh_button())
        for card in self.cards:
            card.apply_styles()

    # ── Drop zone ─────────────────────────────────────────────────────────────

    def drop_zone_drag_enter(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def drop_zone_drop(self, event):
        files, json_files = [], []
        for url in event.mimeData().urls():
            fp = url.toLocalFile()
            (json_files if fp.lower().endswith('.json')
             else files if fp.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
             else []).append(fp)

        import_in_tabs = config.get('import_in_tabs')
        should_new_tab = import_in_tabs and len(self.cards) > 0

        if json_files:
            if len(json_files) > 1:
                self.log(config.get_text('msg_multiple_json'))
            self._route_import_json(json_files[0], should_new_tab)
        elif files:
            self._route_load_images(files, should_new_tab)

        event.acceptProposedAction()

    def drop_zone_click(self, event):
        files, _ = QFileDialog.getOpenFileNames(
            self, config.get_text('dialog_open_images_json'), "",
            config.get_text('file_filter_images_json'))
        if not files:
            return
        image_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
        json_files  = [f for f in files if f.lower().endswith('.json')]
        should_new_tab = config.get('import_in_tabs') and len(self.cards) > 0

        if json_files:
            if len(json_files) > 1:
                self.log(config.get_text('msg_multiple_json'))
            self._route_import_json(json_files[0], should_new_tab)
        elif image_files:
            self._route_load_images(image_files, should_new_tab)

    def _route_import_json(self, file_path, new_tab):
        if new_tab:
            tab = self._open_new_tab()
            if tab:
                tab.import_from_file(file_path)
        else:
            self.import_from_file(file_path)

    def _route_load_images(self, files, new_tab):
        if new_tab:
            tab = self._open_new_tab()
            if tab:
                tab.load_images_from_paths(files)
        else:
            self.load_images_from_paths(files)

    def _open_new_tab(self):
        mw = self.get_main_window()
        if mw:
            mw.add_tab()
            new_tab = mw.tabs.widget(mw.tabs.count() - 1)
            if isinstance(new_tab, GridTab):
                return new_tab
        return None

    # ── Tab management ────────────────────────────────────────────────────────

    def close_current_tab(self):
        tab_widget = self.get_tab_widget()
        if tab_widget and tab_widget.count() > 1:
            idx = tab_widget.indexOf(self)
            if idx >= 0:
                tab_widget.removeTab(idx)
                self.deleteLater()
                mw = self.get_main_window() if tab_widget.count() > 0 else None
                if mw:
                    mw._auto_save_session_if_enabled()
        else:
            self.log_label.setText(config.get_text('msg_cant_delete_last_tab'))
            self.log_label.setStyleSheet("color: yellow; font-weight: bold;")
            QTimer.singleShot(3000, self._set_idle)
        if tab_widget and tab_widget.count() == 1:
            tab_widget.setTabText(0, "A")

    # ── Card management ───────────────────────────────────────────────────────

    def load_images_from_paths(self, files):
        existing_paths = {card.image_path for card in self.cards}
        new_images = duplicates = 0

        for file_path in files:
            if file_path in existing_paths:
                duplicates += 1
                continue
            filename = os.path.basename(file_path)
            module = self.get_active_module()
            if module and hasattr(module, 'create_module_data'):
                module_data = module.create_module_data(filename, self.module_state)
            elif module and hasattr(module, 'json_to_module_data'):
                module_data = module.json_to_module_data({})
            else:
                module_data = {}
            card = ImageCard(file_path, self, module_data=module_data)
            card.positionChanged.connect(self.update_borders)
            self.cards.append(card)
            new_images += 1

        self.refresh_grid()
        if new_images:
            self.log(config.get_text('msg_loaded_images').format(n=new_images))
        if duplicates:
            self.log(config.get_text('msg_skipped_duplicates').format(n=duplicates))
        if not new_images and not duplicates:
            self.log(config.get_text('msg_no_images_to_load'))

    def refresh_grid(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        for i in range(self.grid_layout.columnCount()):
            self.grid_layout.setColumnStretch(i, 0)

        actual_card_width = max(210, self.card_size) + 20
        available_width = self.scroll_area.viewport().width() - 40
        cols = max(1, available_width // actual_card_width)

        for idx, card in enumerate(self.cards):
            self.grid_layout.addWidget(
                card, idx // cols, idx % cols,
                Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.grid_layout.setColumnStretch(cols, 1)
        self.update_borders()

    def on_slider_released(self):
        self.resize_cards(self.size_slider.value())

    def resize_cards(self, size):
        if self.card_size == size:
            return
        self.card_size = size
        for card in self.cards:
            pixmap = QPixmap(card.image_path)
            if not pixmap.isNull():
                cropped = card.smart_square_crop(pixmap)
                card.image_label.setPixmap(
                    cropped.scaled(size, size, Qt.AspectRatioMode.IgnoreAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation))
        self.refresh_grid()

    def update_borders(self):
        module = self.get_active_module()
        if not module or not hasattr(module, 'apply_card_styles'):
            return
        for card in self.cards:
            module.apply_card_styles(card)

    def remove_card(self, card):
        if card in self.cards:
            self.cards.remove(card)
        self.refresh_grid()
        self._set_idle()

    def swap_cards(self, source_card, target_card):
        """
        CRITICAL: DO NOT MODIFY THIS METHOD!
        Uses pop() + insert() logic to PUSH cards, not swap them.
        """
        if source_card and target_card and source_card != target_card:
            source_idx = self.cards.index(source_card)
            target_idx = self.cards.index(target_card)
            self.cards.pop(source_idx)
            self.cards.insert(target_idx, source_card)
            self.refresh_grid()

    def close_active_dialog(self):
        if self.active_details_dialog:
            self.active_details_dialog.close()
            self.active_details_dialog = None

    def clear_grid(self):
        for card in self.cards[:]:
            card.deleteLater()
        self.cards.clear()
        self.refresh_grid()
        self.log(config.get_text('msg_loaded'))

    # ── Save Tabs (manual) ────────────────────────────────────────────────────

    def save_tabs_manually(self):
        mw = self.get_main_window()
        if not mw:
            return
        grids_dir = Path(__file__).parent / 'grids'
        grids_dir.mkdir(exist_ok=True)
        saved_paths = []
        saved_count = 0
        for i in range(mw.tabs.count()):
            tab = mw.tabs.widget(i)
            if not isinstance(tab, GridTab) or not tab.cards:
                continue
            tab_name = mw.tabs.tabText(i)
            module = tab.get_active_module()
            data = {"card_size": tab.card_size, "images": []}
            for card in tab.cards:
                card_data = {"absolutePath": card.image_path}
                if config.get('show_title') and hasattr(card, 'title_edit') and card.title_edit:
                    card_data['title'] = card.title_edit.text()
                if config.get('show_description') and hasattr(card, 'description_edit') and card.description_edit:
                    card_data['description'] = card.description_edit.toPlainText()
                if module and hasattr(module, 'card_to_json'):
                    card_data.update(module.card_to_json(card))
                data["images"].append(card_data)
            filename = f"grid-{tab_name}_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
            save_path = grids_dir / filename
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            tab.last_imported_json = str(save_path)
            saved_paths.append(str(save_path))
            saved_count += 1
        config.save_last_session(saved_paths)
        self.log(config.get_text('msg_session_saved').format(n=saved_count))

    # ── Export / Import ───────────────────────────────────────────────────────

    def export_grid(self):
        if not self.cards:
            self.log(config.get_text('msg_no_images'))
            return
        tab_widget = self.get_tab_widget()
        tab_index = tab_widget.indexOf(self) if tab_widget else 0
        tab_name = tab_widget.tabText(tab_index) if tab_widget else "A"
        module = self.get_active_module()

        data = {"card_size": self.card_size, "images": []}
        for card in self.cards:
            card_data = {"absolutePath": card.image_path}
            if config.get('show_title') and hasattr(card, 'title_edit') and card.title_edit:
                card_data['title'] = card.title_edit.text()
            if config.get('show_description') and hasattr(card, 'description_edit') and card.description_edit:
                card_data['description'] = card.description_edit.toPlainText()
            if module and hasattr(module, 'card_to_json'):
                card_data.update(module.card_to_json(card))
            data["images"].append(card_data)

        filename = f"grid-{tab_name}_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        save_path, _ = QFileDialog.getSaveFileName(
            self, config.get_text('dialog_export_title'),
            filename, config.get_text('file_filter_json'))
        if save_path:
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.log(config.get_text('msg_exported'))

    def import_from_file(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if config.get('import_mode') == 'replace':
                self.clear_grid()

            if 'card_size' in data:
                self.card_size = data['card_size']
                self.size_slider.setValue(self.card_size)

            existing_paths = {card.image_path for card in self.cards}
            source_json_name = os.path.basename(file_path)
            module = self.get_active_module()
            added = missing = 0

            for img_data in data.get("images", []):
                if not os.path.exists(img_data["absolutePath"]):
                    missing += 1
                    continue
                if config.get('import_mode') == 'add' and img_data["absolutePath"] in existing_paths:
                    continue

                module_data = {}
                if module and hasattr(module, 'json_to_module_data'):
                    module_data = module.json_to_module_data(img_data)

                card = ImageCard(img_data["absolutePath"], self,
                                 source_json=source_json_name,
                                 module_data=module_data,
                                 raw_json_data=img_data)
                card.positionChanged.connect(self.update_borders)
                self.cards.append(card)
                added += 1

            self.refresh_grid()
            self.last_imported_json = file_path
            total = len(self.cards)

            msg = (f"{config.get_text('msg_imported')}: +{added} images (total: {total})"
                   if config.get('import_mode') == 'add'
                   else f"{config.get_text('msg_imported')}: {total} images")
            if missing:
                msg += f" ({missing} missing files skipped)"

            self.log(msg)
            self.save_to_last_session(file_path)

        except Exception as e:
            self.log(config.get_text('msg_import_error').format(e=str(e)))

    def import_grid(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, config.get_text('dialog_import_title'),
            "", config.get_text('file_filter_json'))
        if not file_path:
            return
        if config.get('import_in_tabs') and len(self.cards) > 0:
            tab = self._open_new_tab()
            if tab:
                tab.import_from_file(file_path)
                return
        self.import_from_file(file_path)

    def save_to_last_session(self, json_path):
        mw = self.get_main_window()
        if not mw:
            return
        paths = mw._collect_session_paths()
        config.save_last_session(paths)
        mw._auto_save_session_if_enabled()

    # ── Card refresh ──────────────────────────────────────────────────────────

    def open_grid2img_dialog(self):
        cards = self.get_all_image_cards()
        if not cards:
            QMessageBox.information(self, "Grid2Img", "No images to export.")
            return

        dlg = Grid2ImgDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        options = dlg.get_options()
        self.export_grid_to_image(options)

    def get_all_image_cards(self):
        cards = []
        for i in range(self.grid_layout.count()):
            item = self.grid_layout.itemAt(i)
            if not item:
                continue
            w = item.widget()
            if isinstance(w, ImageCard):
                cards.append(w)
        return cards

    def get_card_export_values(self, card):
        values = {}
        raw = card.raw_json_data or {}
        module = card.module_data or {}
        meta = getattr(card, 'all_metadata', {}) or {}

        def first_non_empty(*vals):
            for v in vals:
                if v is None:
                    continue
                if isinstance(v, str) and not v.strip():
                    continue
                return v
            return None

        values["checkpoint"] = first_non_empty(
            card.module_data.get('checkpoint_name'), raw.get("checkpointName"), meta.get('model')
        )
        values["prompt"] = first_non_empty(
            module.get("prompt"), raw.get("prompt"), raw.get("positivePrompt"), raw.get("description"), getattr(card, "description", None), meta.get('prompt')
        )
        values["cfg"] = first_non_empty(module.get("cfg"), raw.get("cfg"), raw.get("cfgScale"), meta.get('cfg'))
        values["sampler"] = first_non_empty(module.get("sampler"), raw.get("sampler"), meta.get('sampler'))
        values["steps"] = first_non_empty(module.get("steps"), raw.get("steps"), meta.get('steps'))
        values["seed"] = first_non_empty(module.get("seed"), raw.get("seed"), meta.get('seed'))
        values["lora"] = first_non_empty(module.get("lora"), raw.get("lora"), raw.get("loraName"), meta.get('lora_hashes'))
        values["lora_strength"] = first_non_empty(module.get("loraStrength"), raw.get("loraStrength"), raw.get("lora_strength"))
        return values

    def build_card_export_lines(self, card, selected_fields):
        values = self.get_card_export_values(card)
        labels = {
            "prompt": "Prompt",
            "checkpoint": "Checkpoint",
            "cfg": "CFG",
            "sampler": "Sampler",
            "steps": "Steps",
            "seed": "Seed",
            "lora": "LoRA",
            "lora_strength": "LoRA strength",
        }
        lines = []
        for key in selected_fields:
            val = values.get(key)
            if val is None:
                continue
            text = str(val).strip()
            if not text:
                continue
            if key == "prompt" and len(text) > 180:
                text = text[:177] + "..."
            lines.append(f"{labels[key]}: {text}")
        return lines

    def export_grid_to_image(self, options):
        cards = self.get_all_image_cards()
        if not cards:
            QMessageBox.information(self, "Grid2Img", "No images to export.")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Save grid image", "grid_export.png", "PNG Images (*.png)")
        if not path:
            return

        columns = max(1, self.grid_layout.columnCount())
        spacing = options["spacing"]
        padding = options["padding"]
        title = options["title"]
        title_size = options["title_size"]
        text_size = options["text_size"]
        bg = options["background"]
        selected_fields = options["fields"]

        cell_width = self.card_size
        thumb_height = self.card_size

        title_font = QFont()
        title_font.setPointSize(title_size)
        title_font.setBold(True)
        text_font = QFont()
        text_font.setPointSize(text_size)

        fm_title = QFontMetrics(title_font)
        fm_text = QFontMetrics(text_font)

        card_lines = [self.build_card_export_lines(card, selected_fields) for card in cards]
        line_heights = []
        for lines in card_lines:
            h = 0
            for line in lines:
                br = fm_text.boundingRect(0, 0, cell_width, 1000, int(Qt.TextFlag.TextWordWrap), line)
                h += br.height() + 4
            line_heights.append(h)

        cell_heights = [thumb_height + (8 + h if h > 0 else 0) for h in line_heights]
        max_cell_height = max(cell_heights) if cell_heights else thumb_height
        title_height = fm_title.height() + spacing if title else 0
        rows = (len(cards) + columns - 1) // columns

        canvas_width = padding * 2 + columns * cell_width + (columns - 1) * spacing
        canvas_height = padding * 2 + title_height + rows * max_cell_height + (rows - 1) * spacing

        canvas = QPixmap(canvas_width, canvas_height)
        canvas.fill(bg)

        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        y0 = padding
        text_color = Qt.GlobalColor.black if bg.lightness() > 128 else Qt.GlobalColor.white
        painter.setPen(text_color)

        if title:
            painter.setFont(title_font)
            painter.drawText(QRect(padding, y0, canvas_width - 2 * padding, fm_title.height() + 10), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, title)
            y0 += title_height

        for idx, card in enumerate(cards):
            row = idx // columns
            col = idx % columns
            x = padding + col * (cell_width + spacing)
            y = y0 + row * (max_cell_height + spacing)

            pm = QPixmap(card.image_path)
            if pm.isNull():
                continue

            cropped = card.smart_square_crop(pm)
            thumb = cropped.scaled(cell_width, thumb_height, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
            painter.drawPixmap(x, y, thumb)

            lines = card_lines[idx]
            if lines:
                painter.setFont(text_font)
                ty = y + thumb_height + 8
                for line in lines:
                    rect = QRect(x, ty, cell_width, 1000)
                    br = painter.boundingRect(rect, int(Qt.TextFlag.TextWordWrap), line)
                    painter.drawText(rect, int(Qt.TextFlag.TextWordWrap), line)
                    ty += br.height() + 4

        painter.end()

        if not canvas.save(path):
            QMessageBox.warning(self, "Grid2Img", "Failed to save image.")
            return

        QMessageBox.information(self, "Grid2Img", f"Saved:\n{path}")

    def refresh_cards(self):
        if not self.cards:
            return
        cards_data = [{
            'image_path': card.image_path,
            'source_json': card.source_json,
            'raw_json_data': card.raw_json_data,
            'module_data': card.module_data,
        } for card in self.cards]

        for card in self.cards[:]:
            card.deleteLater()
        self.cards.clear()

        module = self.get_active_module()
        for data in cards_data:
            raw_json = data.get('raw_json_data', {})
            if module and hasattr(module, 'json_to_module_data') and raw_json:
                module_data = module.json_to_module_data(raw_json)
            else:
                module_data = data.get('module_data', {})

            card = ImageCard(data['image_path'], self,
                             source_json=data.get('source_json'),
                             module_data=module_data,
                             raw_json_data=raw_json)
            card.positionChanged.connect(self.update_borders)
            self.cards.append(card)

        self.refresh_grid()
        self.log(config.get_text('msg_refreshed_cards').format(n=len(self.cards)))

    # ── UI helpers ────────────────────────────────────────────────────────────

    def refresh_ui_texts(self, lang_changed=False):
        self.options_btn.setText(config.get_text('btn_options'))
        self.export_btn.setText(config.get_text('btn_export'))
        self.import_btn.setText(config.get_text('btn_import'))
        self.save_tabs_btn.setText(config.get_text('btn_save_tabs'))
        self.clear_btn.setText(config.get_text('btn_clear'))
        self.refresh_btn.setText(config.get_text('btn_refresh'))
        self.size_label.setText(config.get_text('slider_label') + ":")
        self.drop_zone.setText(config.get_text('drop_zone_text'))
        self.update_module_dropdown()
        self._set_idle()
        if lang_changed:
            self.refresh_cards()

    def get_tab_widget(self):
        parent = self.parent()
        while parent:
            if isinstance(parent, QTabWidget):
                return parent
            parent = parent.parent()
        return None

    def get_main_window(self):
        parent = self.parent()
        while parent:
            if isinstance(parent, MainWindow):
                return parent
            parent = parent.parent()
        return None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.close_active_dialog()
        if hasattr(self, 'cards') and self.cards:
            QTimer.singleShot(100, self.refresh_grid)

    def show_fullscreen(self, card):
        viewer = FullscreenViewer(card, self, self.get_main_window())
        viewer.showFullScreen()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F5:
            self.refresh_cards()
        else:
            super().keyPressEvent(event)


# ── Metadata overlay widget ───────────────────────────────────────────────────

class MetadataOverlay(QWidget):
    """
    Semi-transparent overlay panel showing image metadata.
    Drawn on top of the image_container using absolute positioning.
    side: 'left' | 'right'
    """
    PANEL_WIDTH = 440

    def __init__(self, parent, side='left'):
        super().__init__(parent)
        self.side = side
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._text = ""
        self._visible = False
        self.setVisible(False)

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        self.text_label = QLabel()
        self.text_label.setWordWrap(True)
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.text_label.setStyleSheet(
            "color: white; font-size: 11px; background: transparent;"
        )
        self.text_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        scroll = QScrollArea()
        scroll.setWidget(self.text_label)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        scroll.viewport().setStyleSheet("background: transparent;")

        layout.addWidget(scroll)
        self.setLayout(layout)

    def set_text(self, text):
        self._text = text
        self.text_label.setText(text)

    def toggle(self):
        self._visible = not self._visible
        self.setVisible(self._visible)
        if self._visible:
            self._reposition()

    def show_panel(self):
        self._visible = True
        self.setVisible(True)
        self._reposition()

    def hide_panel(self):
        self._visible = False
        self.setVisible(False)

    def _reposition(self):
        parent = self.parent()
        if not parent:
            return
        h = parent.height()
        w = self.PANEL_WIDTH
        margin = 10
        if self.side == 'left':
            self.setGeometry(margin, margin, w, h - 2 * margin)
        else:
            self.setGeometry(parent.width() - w - margin, margin, w, h - 2 * margin)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(get_styles().COLORS['bg3'])
        color.setAlpha(50)
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 10, 10)
        painter.end()

    def resizeEvent(self, event):
        super().resizeEvent(event)


# ── Fullscreen viewer ─────────────────────────────────────────────────────────

class FullscreenViewer(QWidget):
    def __init__(self, card, grid_tab, main_window, parent=None):
        super().__init__(parent)
        self.card = card
        self.grid_tab = grid_tab
        self.main_window = main_window
        self.comparison_card = None
        self.comparison_pixmap = None
        self.main_pixmap = QPixmap(card.image_path)
        self.split_position = 0.5
        self.dragging_split = False
        self.image_x_offset = 0
        self.image_width = 0
        self.current_card_index = grid_tab.cards.index(card) if card in grid_tab.cards else 0

        self.setWindowTitle("Fullscreen View")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._bg_opacity = (config.get('fullscreen_opacity') or 100) / 100.0
        canvas = get_styles().COLORS.get('canvas', '#000000').strip()
        self._bg_color = QColor(canvas) if QColor(canvas).isValid() else QColor(0, 0, 0)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        top_bar = QHBoxLayout()
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(40, 40)
        close_btn.setStyleSheet(get_styles().fullscreen_close_button())
        close_btn.clicked.connect(self.close)

        grid_label = QLabel(config.get_text('fullscreen_compare'))
        grid_label.setStyleSheet(get_styles().fullscreen_label())
        self.grid_combo = QComboBox()
        self.grid_combo.setMinimumHeight(30)
        self.grid_combo.setStyleSheet(get_styles().fullscreen_combo())

        if main_window:
            current_tab_index = main_window.tabs.indexOf(grid_tab)
            for i in range(main_window.tabs.count()):
                tab_name = main_window.tabs.tabText(i)
                self.grid_combo.addItem(
                    config.get_text('fullscreen_tab_current').format(name=tab_name)
                    if i == current_tab_index else tab_name, i)
            for idx in range(self.grid_combo.count()):
                if self.grid_combo.itemData(idx) == current_tab_index:
                    self.grid_combo.setCurrentIndex(idx)
                    break
        else:
            self.grid_combo.addItem("Grid A (current)", 0)

        top_bar.addWidget(close_btn)
        top_bar.addStretch()
        top_bar.addWidget(grid_label)
        top_bar.addWidget(self.grid_combo)
        top_bar.addWidget(QLabel("   "))

        info_layout = QHBoxLayout()
        self.info_label = QLabel()
        self.info_label.setStyleSheet(get_styles().fullscreen_info_selectable())
        self.info_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.info_label2 = QLabel()
        self.info_label2.setStyleSheet(get_styles().fullscreen_info_selectable())
        self.info_label2.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.info_label2.setVisible(False)
        info_layout.addWidget(self.info_label)
        info_layout.addStretch()
        info_layout.addWidget(self.info_label2)

        # Image container — metadata overlays are children of this widget
        self.image_container = QLabel()
        self.image_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_container.setStyleSheet("background: transparent;")
        self.image_container.mousePressEvent = self.mouse_press_on_image
        self.image_container.mouseMoveEvent = self.mouse_move_on_image
        self.image_container.mouseReleaseEvent = self.mouseReleaseEvent
        self.image_container.paintEvent = self.paint_image
        self.image_container.resizeEvent = self._on_image_container_resize

        # Metadata overlays
        self.meta_overlay_left = MetadataOverlay(self.image_container, side='left')
        self.meta_overlay_right = MetadataOverlay(self.image_container, side='right')

        layout.addLayout(top_bar)
        layout.addWidget(self.image_container, stretch=1)
        layout.addLayout(info_layout)
        self.setLayout(layout)

        self.update_info_label()
        self._update_meta_overlay_left()
        self.grid_combo.currentIndexChanged.connect(self.on_grid_changed)

    def _on_image_container_resize(self, event):
        # Reposition overlays when container resizes
        if self.meta_overlay_left.isVisible():
            self.meta_overlay_left._reposition()
        if self.meta_overlay_right.isVisible():
            self.meta_overlay_right._reposition()

    def _update_meta_overlay_left(self):
        if not config.get('read_metadata'):
            self.meta_overlay_left.hide_panel()
            return
        text = format_metadata_for_display(self.card)
        self.meta_overlay_left.set_text(text)
        # Don't auto-show — user toggles with click

    def _update_meta_overlay_right(self):
        if not config.get('read_metadata') or not self.comparison_card:
            self.meta_overlay_right.hide_panel()
            return
        text = format_metadata_for_display(self.comparison_card)
        self.meta_overlay_right.set_text(text)
        # Don't auto-show — user toggles with click

    def paint_image(self, event):
        if self.main_pixmap.isNull():
            return
        painter = QPainter(self.image_container)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        cr = self.image_container.rect()

        if not self.comparison_pixmap:
            scaled = self.main_pixmap.scaled(cr.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                             Qt.TransformationMode.SmoothTransformation)
            x = (cr.width() - scaled.width()) // 2
            y = (cr.height() - scaled.height()) // 2
            self.image_x_offset = x
            self.image_width = scaled.width()
            painter.drawPixmap(x, y, scaled)
        else:
            s1 = self.main_pixmap.scaled(cr.width(), cr.height(), Qt.AspectRatioMode.KeepAspectRatio,
                                         Qt.TransformationMode.SmoothTransformation)
            s2 = self.comparison_pixmap.scaled(cr.width(), cr.height(), Qt.AspectRatioMode.KeepAspectRatio,
                                               Qt.TransformationMode.SmoothTransformation)
            dw = min(s1.width(), s2.width())
            dh = min(s1.height(), s2.height())
            x = (cr.width() - dw) // 2
            y = (cr.height() - dh) // 2
            self.image_x_offset = x
            self.image_width = dw
            split_x = int(x + dw * self.split_position)
            lw = int(dw * self.split_position)
            painter.drawPixmap(x, y, s1, 0, 0, lw, dh)
            painter.drawPixmap(split_x, y, s2, int(s2.width() * self.split_position), 0, dw - lw, dh)
            painter.setPen(QPen(QColor(get_styles().COLORS['text1']), 3))
            painter.drawLine(split_x, y, split_x, y + dh)
            handle_y = y + dh // 2
            painter.setBrush(QColor(get_styles().COLORS['accent']))
            painter.drawEllipse(split_x - 15, handle_y - 15, 30, 30)
            painter.setPen(QPen(QColor(get_styles().COLORS['text1']), 2))
            painter.drawLine(split_x - 8, handle_y, split_x + 8, handle_y)
        painter.end()

    def on_grid_changed(self, index):
        if not self.main_window:
            return
        selected_tab_index = self.grid_combo.itemData(index)
        if selected_tab_index is None:
            return
        selected_tab = self.main_window.tabs.widget(selected_tab_index)
        current_tab_index = self.main_window.tabs.indexOf(self.grid_tab)

        if selected_tab_index == current_tab_index or not selected_tab or not hasattr(selected_tab, 'cards'):
            self.info_label2.setVisible(False)
            self.comparison_card = None
            self.comparison_pixmap = None
            self.meta_overlay_right.hide_panel()
        else:
            if selected_tab.cards:
                self.comparison_card = selected_tab.cards[0]
                pixmap2 = QPixmap(self.comparison_card.image_path)
                if not pixmap2.isNull():
                    self.comparison_pixmap = pixmap2
                self.info_label2.setVisible(True)
                self.split_position = 0.5
                self.update_info_label()
                self._update_meta_overlay_right()
        self.image_container.update()

    def mouse_press_on_image(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.comparison_pixmap:
                # Check if click is near split handle → drag, else toggle metadata
                mouse_x = event.pos().x()
                split_x = int(self.image_x_offset + self.image_width * self.split_position)
                if abs(mouse_x - split_x) < 30:
                    self.dragging_split = True
                    self.update_split_from_mouse(mouse_x)
                else:
                    # Toggle metadata overlays based on which side was clicked
                    self._toggle_meta_from_click(mouse_x)
            else:
                self._toggle_meta_left()

    def _toggle_meta_from_click(self, mouse_x):
        """Toggle left or right overlay based on click position relative to split."""
        if not config.get('read_metadata'):
            return
        split_x = int(self.image_x_offset + self.image_width * self.split_position)
        if mouse_x < split_x:
            self.meta_overlay_left.toggle()
            if self.meta_overlay_left._visible:
                self.meta_overlay_left._reposition()
        else:
            self.meta_overlay_right.toggle()
            if self.meta_overlay_right._visible:
                self.meta_overlay_right._reposition()

    def _toggle_meta_left(self):
        if not config.get('read_metadata'):
            return
        self.meta_overlay_left.toggle()
        if self.meta_overlay_left._visible:
            self.meta_overlay_left._reposition()

    def mouse_move_on_image(self, event):
        if self.comparison_pixmap and self.dragging_split:
            self.update_split_from_mouse(event.pos().x())

    def update_split_from_mouse(self, mouse_x):
        if self.image_width > 0:
            self.split_position = max(0.0, min(1.0, (mouse_x - self.image_x_offset) / self.image_width))
            self.image_container.update()

    def mouseReleaseEvent(self, event):
        self.dragging_split = False

    def update_info_label(self):
        module = self.grid_tab.get_active_module()
        ckpt = self.card.module_data.get('checkpoint_name', '') if module else ''
        self.info_label.setText(
            f"{ckpt} - {os.path.basename(self.card.image_path)}"
            if ckpt else os.path.basename(self.card.image_path))
        if self.comparison_card:
            ckpt2 = self.comparison_card.module_data.get('checkpoint_name', '') if module else ''
            self.info_label2.setText(
                f"{ckpt2} - {os.path.basename(self.comparison_card.image_path)}"
                if ckpt2 else os.path.basename(self.comparison_card.image_path))

    def show_previous_image(self):
        if self.current_card_index > 0:
            self.current_card_index -= 1
            self.load_card_at_index(self.current_card_index)
            if self.comparison_card:
                self.load_comparison_at_index(self.current_card_index)

    def show_next_image(self):
        if self.current_card_index < len(self.grid_tab.cards) - 1:
            self.current_card_index += 1
            self.load_card_at_index(self.current_card_index)
            if self.comparison_card:
                self.load_comparison_at_index(self.current_card_index)

    def load_card_at_index(self, index):
        if 0 <= index < len(self.grid_tab.cards):
            self.card = self.grid_tab.cards[index]
            pixmap = QPixmap(self.card.image_path)
            if not pixmap.isNull():
                self.main_pixmap = pixmap
                self.image_container.update()
            self.update_info_label()
            self._update_meta_overlay_left()

    def load_comparison_at_index(self, index):
        if not self.main_window:
            return
        selected_tab_index = self.grid_combo.itemData(self.grid_combo.currentIndex())
        if selected_tab_index is None:
            return
        selected_tab = self.main_window.tabs.widget(selected_tab_index)
        if selected_tab and hasattr(selected_tab, 'cards') and selected_tab.cards:
            comp_index = min(index, len(selected_tab.cards) - 1)
            self.comparison_card = selected_tab.cards[comp_index]
            pixmap2 = QPixmap(self.comparison_card.image_path)
            if not pixmap2.isNull():
                self.comparison_pixmap = pixmap2
                self.image_container.update()
            self.update_info_label()
            self._update_meta_overlay_right()

    def paintEvent(self, event):
        painter = QPainter(self)
        color = QColor(self._bg_color)
        color.setAlphaF(self._bg_opacity)
        painter.fillRect(self.rect(), color)
        painter.end()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() == Qt.Key.Key_Left:
            self.show_previous_image()
        elif event.key() == Qt.Key.Key_Right:
            self.show_next_image()


# ── Main window ───────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(config.get_text('window_title'))
        self.setGeometry(100, 100, 1400, 900)
        self.setStyleSheet(get_styles().main_window())

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout()

        self.tabs = CustomTabBar()
        self.tabs.setTabsClosable(False)
        self.ui_state_level1 = True
        self.ui_state_level2 = True

        self.zoom_timer = QTimer()
        self.zoom_timer.setSingleShot(True)
        self.zoom_timer.timeout.connect(self.apply_pending_zoom)
        self.pending_zoom_value = None

        button_widget = QWidget()
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(2)

        self.add_tab_btn = QPushButton("+")
        self.add_tab_btn.setFixedSize(30, 30)
        self.add_tab_btn.setStyleSheet(get_styles().add_tab_button())
        self.add_tab_btn.clicked.connect(self.add_tab)
        self.add_tab_btn.enterEvent = lambda e: self._tab_btn_hover('hover_add_tab', 'accent')
        self.add_tab_btn.leaveEvent  = lambda e: self._tab_btn_hover_end()

        self.remove_all_btn = QPushButton("-")
        self.remove_all_btn.setFixedSize(30, 30)
        self.remove_all_btn.setStyleSheet(get_styles().remove_tab_button())
        self.remove_all_btn.clicked.connect(self.remove_all_tabs)
        self.remove_all_btn.enterEvent = lambda e: self._tab_btn_hover('hover_remove_tabs', 'danger')
        self.remove_all_btn.leaveEvent  = lambda e: self._tab_btn_hover_end()

        button_layout.addWidget(self.add_tab_btn)
        button_layout.addWidget(self.remove_all_btn)
        button_widget.setLayout(button_layout)
        self.tabs.setCornerWidget(button_widget, Qt.Corner.TopRightCorner)

        main_layout.addWidget(self.tabs)
        central.setLayout(main_layout)

        if config.get('auto_load_last'):
            self.load_last_session()
        else:
            self.add_tab()

    # ── Session helpers ───────────────────────────────────────────────────────

    def _tab_btn_hover(self, text_key, color_key):
        tab = self.tabs.currentWidget()
        if isinstance(tab, GridTab):
            tab._show_hover(text_key, color_key)

    def _tab_btn_hover_end(self):
        tab = self.tabs.currentWidget()
        if isinstance(tab, GridTab):
            tab._hide_hover()

    def _collect_session_paths(self):
        paths = []
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if isinstance(tab, GridTab) and getattr(tab, 'last_imported_json', None):
                if tab.last_imported_json not in paths:
                    paths.append(tab.last_imported_json)
        return paths

    def _auto_save_session_if_enabled(self):
        if config.get('auto_save_session'):
            paths = self._collect_session_paths()
            config.save_last_session(paths)

    # ── Tab management ────────────────────────────────────────────────────────

    def load_last_session(self):
        last_session = config.get_last_session()
        if not last_session:
            self.add_tab()
            return
        for json_path in last_session:
            if os.path.exists(json_path):
                self.add_tab()
                new_tab = self.tabs.widget(self.tabs.count() - 1)
                if isinstance(new_tab, GridTab):
                    new_tab.import_from_file(json_path)
        if self.tabs.count() == 0:
            self.add_tab()

    def add_tab(self):
        if self.tabs.count() >= 26:
            return
        letter = chr(65 + self.tabs.count())
        grid_tab = GridTab()
        grid_tab.scroll_area.viewport().installEventFilter(self)
        tab_index = self.tabs.addTab(grid_tab, letter)
        self.tabs.setCurrentIndex(tab_index)
        if self.tabs.count() == 1:
            self.tabs.setTabText(0, "A")
        self._auto_save_session_if_enabled()

    def close_tab_at_index(self, index):
        if self.tabs.count() > 1:
            widget = self.tabs.widget(index)
            self.tabs.removeTab(index)
            widget.deleteLater()
            self._auto_save_session_if_enabled()
        else:
            tab = self.tabs.widget(index)
            if hasattr(tab, 'log'):
                tab.log(config.get_text('msg_cant_delete_last_tab'))
        if self.tabs.count() == 1:
            self.tabs.setTabText(0, "A")

    def remove_all_tabs(self):
        while self.tabs.count() > 0:
            widget = self.tabs.widget(0)
            self.tabs.removeTab(0)
            widget.deleteLater()
        self.add_tab()

    def closeEvent(self, event):
        self._auto_save_session_if_enabled()
        super().closeEvent(event)

    # ── UI ────────────────────────────────────────────────────────────────────

    def refresh_ui_texts(self, lang_changed=False):
        self.setWindowTitle(config.get_text('window_title'))
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if hasattr(tab, 'refresh_ui_texts'):
                tab.refresh_ui_texts(lang_changed)

    def apply_styles(self):
        styles = get_styles()
        self.setStyleSheet(styles.main_window())
        self.add_tab_btn.setStyleSheet(styles.add_tab_button())
        self.remove_all_btn.setStyleSheet(styles.remove_tab_button())
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if hasattr(tab, 'apply_styles'):
                tab.apply_styles()

    def moveEvent(self, event):
        super().moveEvent(event)
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if hasattr(tab, 'close_active_dialog'):
                tab.close_active_dialog()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if hasattr(tab, 'close_active_dialog'):
                tab.close_active_dialog()

    def toggle_ui_level1(self):
        self.ui_state_level1 = not self.ui_state_level1
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if isinstance(tab, GridTab):
                tab.controls1_widget.setVisible(self.ui_state_level1)
                tab.controls2_widget.setVisible(self.ui_state_level1)
                tab.drop_zone.setVisible(self.ui_state_level1)

    def toggle_ui_level2(self):
        self.ui_state_level2 = not self.ui_state_level2
        self.tabs.tabBar().setVisible(self.ui_state_level2)
        corner_widget = self.tabs.cornerWidget(Qt.Corner.TopRightCorner)
        if corner_widget:
            corner_widget.setVisible(self.ui_state_level2)
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if isinstance(tab, GridTab):
                tab.controls1_widget.setVisible(self.ui_state_level2)
                tab.controls2_widget.setVisible(self.ui_state_level2)
                tab.drop_zone.setVisible(self.ui_state_level2)

    def eventFilter(self, obj, event):
        if event.type() == event.Type.Wheel:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                for i in range(self.tabs.count()):
                    tab = self.tabs.widget(i)
                    if isinstance(tab, GridTab) and obj == tab.scroll_area.viewport():
                        delta = event.angleDelta().y()
                        step = 50
                        new_value = tab.size_slider.value() + (step if delta > 0 else -step)
                        new_value = max(tab.size_slider.minimum(),
                                        min(tab.size_slider.maximum(), new_value))
                        tab.size_slider.setValue(new_value)
                        self.pending_zoom_value = new_value
                        self.zoom_timer.start(150)
                        return True
        return super().eventFilter(obj, event)

    def apply_pending_zoom(self):
        if self.pending_zoom_value is not None:
            current_tab = self.tabs.currentWidget()
            if isinstance(current_tab, GridTab):
                current_tab.resize_cards(self.pending_zoom_value)
            self.pending_zoom_value = None

    def keyPressEvent(self, event):
        modifiers = event.modifiers()
        if (modifiers & Qt.KeyboardModifier.ControlModifier) and \
                event.key() in (Qt.Key.Key_Space, Qt.Key.Key_F11):
            self.toggle_ui_level2()
            event.accept()
            return
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_F11):
            self.toggle_ui_level1()
            event.accept()
            return
        if event.key() == Qt.Key.Key_F5:
            for i in range(self.tabs.count()):
                tab = self.tabs.widget(i)
                if hasattr(tab, 'refresh_cards'):
                    tab.refresh_cards()
            event.accept()
            return
        super().keyPressEvent(event)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()