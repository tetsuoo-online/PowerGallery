import sys
import json
import os
from datetime import datetime
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QFileDialog, 
                             QScrollArea, QTabWidget, QSlider, QLineEdit, QTextEdit,
                             QGridLayout, QFrame, QDialog, QComboBox, QLayout, QSizePolicy,
                             QCheckBox, QGroupBox, QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt, QPoint, QRect, QTimer, pyqtSignal, QMimeData, QSize
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QDrag, QPalette, QPen, QIcon

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
        self.setWindowTitle(config.get_text('options_title'))
        self.setModal(True)
        self.setMinimumSize(500, 450)
        self.apply_options_style()

        main_layout = QVBoxLayout()
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_general_tab(), config.get_text('options_tab_general'))
        self.tabs.addTab(self.create_personalization_tab(), config.get_text('options_tab_style'))
        self.tabs.addTab(self.create_modules_tab(), config.get_text('options_tab_modules'))

        close_btn = QPushButton(config.get_text('options_close'))
        close_btn.clicked.connect(self.save_and_close)

        main_layout.addWidget(self.tabs)
        main_layout.addWidget(close_btn)
        self.setLayout(main_layout)

    def create_general_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        lang_group = QGroupBox(config.get_text('options_language'))
        lang_layout = QVBoxLayout()

        self.lang_list = QListWidget()
        self.lang_list.setIconSize(QSize(24, 16))
        self.lang_list.setFixedHeight(120)
        self.lang_list.setSpacing(2)

        current_lang = config.get('language')
        for lang_key, lang_info in config.get_languages().items():
            item = self._build_lang_list_item(lang_key, lang_info)
            self.lang_list.addItem(item)
            if lang_key == current_lang:
                self.lang_list.setCurrentItem(item)

        lang_layout.addWidget(self.lang_list)
        lang_group.setLayout(lang_layout)

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

        layout.addWidget(lang_group)
        layout.addWidget(import_group)
        layout.addWidget(self.import_in_tabs)
        layout.addWidget(self.auto_load_last)
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
        """Dynamically built from MODULE_REGISTRY — no hardcoded module names."""
        tab = QWidget()
        layout = QVBoxLayout()
        current_module = config.get('selected_module')

        self.module_checkboxes = {}   # key → QCheckBox
        self.module_settings_widgets = []  # widgets with .save()

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

        # Radio-like exclusivity
        def on_none(checked):
            if checked:
                for c in self.module_checkboxes.values():
                    c.setChecked(False)

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

    def save_and_close(self):
        old_lang = config.get('language')
        selected_lang_item = self.lang_list.currentItem()
        if selected_lang_item:
            config.set_language(selected_lang_item.data(Qt.ItemDataRole.UserRole))
        config.set_import_mode('replace' if self.import_replace.isChecked() else 'add')
        config.set_import_in_tabs(self.import_in_tabs.isChecked())
        config.set_auto_load_last(self.auto_load_last.isChecked())

        selected_module = next(
            (key for key, cb in self.module_checkboxes.items() if cb.isChecked()), None)
        config.set_selected_module(selected_module)

        for widget in self.module_settings_widgets:
            if hasattr(widget, 'save'):
                widget.save()

        lang_changed = config.get('language') != old_lang

        if isinstance(self.parent(), MainWindow):
            self.parent().refresh_ui_texts(lang_changed)
            self.parent().apply_styles()

        self.accept()


# ── Image card ────────────────────────────────────────────────────────────────

class ImageCard(QFrame):
    positionChanged = pyqtSignal()

    def __init__(self, image_path, checkpoint_name=None, parent=None,
                 source_json=None, module_data=None, raw_json_data=None):
        super().__init__(parent)
        self.image_path = image_path
        self.checkpoint_name = checkpoint_name or ""
        self.source_json = source_json
        self.module_data = module_data or {}
        self.raw_json_data = raw_json_data or {}

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

        self.setup_ui()

    def get_active_module(self):
        module_name = config.get('selected_module')
        return MODULE_REGISTRY.get(module_name) if module_name else None

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)

        # Top bar (close btn + optional module section)
        top_container = QWidget()
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

        top_container.setLayout(top_layout)

        # Image
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

        # Bottom module widget (criteria buttons, text edit, …)
        bottom_widget = None
        if module and hasattr(module, 'build_card_bottom'):
            bottom_widget = module.build_card_bottom(self)

        # Store containers for apply_styles
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

    def apply_styles(self):
        self.close_btn.setStyleSheet(get_styles().close_button())
        self._apply_container_bg()
        module = self.get_active_module()
        if module and hasattr(module, 'apply_card_styles'):
            module.apply_card_styles(self)
        else:
            self.setStyleSheet(get_styles().card_style())

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
        self.checkpoints_list = []
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

        # Controls row 1
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

        self.export_btn = QPushButton(config.get_text('btn_export'))
        self.export_btn.clicked.connect(self.export_grid)

        self.import_btn = QPushButton(config.get_text('btn_import'))
        self.import_btn.clicked.connect(self.import_grid)

        self.clear_btn = QPushButton(config.get_text('btn_clear'))
        self.clear_btn.setStyleSheet(get_styles().clear_button())
        self.clear_btn.clicked.connect(self.clear_grid)

        controls1.addWidget(self.close_tab_btn)
        controls1.addWidget(self.options_btn)
        controls1.addWidget(self.module_dropdown)
        controls1.addWidget(self.export_btn)
        controls1.addWidget(self.import_btn)
        controls1.addWidget(self.clear_btn)
        controls1.addStretch()

        # Controls row 2
        controls2 = QHBoxLayout()
        self.controls2_widget = QWidget()
        self.controls2_widget.setLayout(controls2)

        log_label = QLabel("ℹ️ Info :")
        log_label.setStyleSheet("font-weight: bold;")
        self.log_label = QLabel("")
        self.log_label.setStyleSheet(f"color: {get_styles().COLORS['text2']};")
        self.log_label.setMinimumWidth(300)
        self.size_label = QLabel(config.get_text('slider_label') + ":")
        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setMinimum(210)
        self.size_slider.setMaximum(1200)
        self.size_slider.setValue(210)
        self.size_slider.setFixedWidth(150)
        self.size_slider.sliderReleased.connect(self.on_slider_released)

        controls2.addWidget(log_label)
        controls2.addWidget(self.log_label)
        controls2.addStretch()
        controls2.addWidget(self.size_label)
        controls2.addWidget(self.size_slider)

        # Drop zone
        self.drop_zone = QLabel(config.get_text('drop_zone_text'))
        self.drop_zone.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_zone.setStyleSheet(get_styles().drop_zone())
        self.drop_zone.setAcceptDrops(True)
        self.drop_zone.dragEnterEvent = self.drop_zone_drag_enter
        self.drop_zone.dropEvent = self.drop_zone_drop
        self.drop_zone.mousePressEvent = self.drop_zone_click

        # Scroll area
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
        if result:
            if result.get('type') == 'checkpoints':
                self.checkpoints_list = result.get('images', [])
                self.update_existing_card_names()
            if result.get('log'):
                self.log(result['log'])

        self.module_dropdown.setCurrentIndex(0)

    # ── Options ───────────────────────────────────────────────────────────────

    def open_options(self):
        old_module = config.get('selected_module')
        dialog = OptionsDialog(self.get_main_window())
        dialog.exec()
        if old_module != config.get('selected_module'):
            self.refresh_cards()
        self.update_module_dropdown()

    # ── Logging ───────────────────────────────────────────────────────────────

    def _get_module_name(self):
        module_name = config.get('selected_module')
        if module_name and module_name in MODULE_REGISTRY:
            module = MODULE_REGISTRY[module_name]
            return module.get_module_name() if hasattr(module, 'get_module_name') else module_name
        return ""

    def _set_idle(self):
        """Restore log label to idle state (module name in muted color)."""
        try:
            if self.log_label is not None:
                self.log_label.setText(self._get_module_name())
                self.log_label.setStyleSheet(f"color: {get_styles().COLORS['text2']};")
        except RuntimeError:
            pass

    def log(self, message, persistent_callback=None):
        module = self._get_module_name()
        text = f"{module} - {message}" if module else message
        self.log_label.setText(text)
        self.log_label.setStyleSheet(f"color: {get_styles().COLORS['accent']}; font-weight: bold;")
        if persistent_callback:
            def run_then_idle():
                persistent_callback()
                QTimer.singleShot(5000, self._set_idle)
            QTimer.singleShot(3000, run_then_idle)
        else:
            QTimer.singleShot(3000, self._set_idle)

    def show_info_persistent(self, text, color=None):
        try:
            if self.log_label is not None:
                module = self._get_module_name()
                display = f"{module} - {text}" if module else text
                self.log_label.setText(display)
                c = color or get_styles().COLORS['accent']
                self.log_label.setStyleSheet(f"color: {c}; font-weight: bold;")
        except RuntimeError:
            pass

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
        else:
            self.log_label.setText(config.get_text('msg_cant_delete_last_tab'))
            self.log_label.setStyleSheet("color: yellow; font-weight: bold;")
            QTimer.singleShot(3000, self.safe_clear_log)
        if tab_widget and tab_widget.count() == 1:
            tab_widget.setTabText(0, "A")

    # ── Checkpoint name matching ───────────────────────────────────────────────

    def extract_checkpoint_from_filename(self, filename):
        for checkpoint in self.checkpoints_list:
            if checkpoint in filename:
                return checkpoint
        return ""

    def update_existing_card_names(self):
        module = self.get_active_module()
        if not module or not hasattr(module, 'update_card_name'):
            return
        updated = 0
        for card in self.cards:
            new_name = self.extract_checkpoint_from_filename(os.path.basename(card.image_path))
            if new_name and new_name != card.checkpoint_name:
                module.update_card_name(card, new_name)
                updated += 1
        if updated:
            self.log(config.get_text('msg_updated_names').format(n=updated))

    # ── Card management ───────────────────────────────────────────────────────

    def load_images_from_paths(self, files):
        existing_paths = {card.image_path for card in self.cards}
        new_images = duplicates = 0

        for file_path in files:
            if file_path in existing_paths:
                duplicates += 1
                continue
            filename = os.path.basename(file_path)
            checkpoint = self.extract_checkpoint_from_filename(filename)
            module = self.get_active_module()
            module_data = (module.json_to_module_data({}) if module and hasattr(module, 'json_to_module_data')
                           else {})
            card = ImageCard(file_path, checkpoint, self, module_data=module_data)
            card.positionChanged.connect(self.update_borders)
            self.cards.append(card)
            new_images += 1

        self.refresh_grid()
        total = len(self.cards)
        if new_images:
            self.log(config.get_text('msg_loaded_images').format(n=new_images),
                     lambda: self.show_info_persistent(f"{total} images"))
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
        if self.cards:
            self.show_info_persistent(f"{len(self.cards)} images")
        else:
            self.safe_clear_log()

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

                checkpoint = img_data.get("checkpointName", "")
                card = ImageCard(img_data["absolutePath"], checkpoint, self,
                                 source_json=source_json_name,
                                 module_data=module_data,
                                 raw_json_data=img_data)
                card.positionChanged.connect(self.update_borders)
                self.cards.append(card)
                added += 1

            self.refresh_grid()
            self.last_imported_json = file_path
            filename = os.path.basename(file_path)
            total = len(self.cards)

            msg = (f"{config.get_text('msg_imported')}: +{added} images (total: {total})"
                   if config.get('import_mode') == 'add'
                   else f"{config.get_text('msg_imported')}: {total} images")
            if missing:
                msg += f" ({missing} missing files skipped)"

            self.log(msg, lambda: self.show_info_persistent(f"{filename} - {total} images"))
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
        paths = []
        for i in range(mw.tabs.count()):
            tab = mw.tabs.widget(i)
            if isinstance(tab, GridTab) and getattr(tab, 'last_imported_json', None):
                if tab.last_imported_json not in paths:
                    paths.append(tab.last_imported_json)
        config.save_last_session(paths)

    # ── Card refresh ──────────────────────────────────────────────────────────

    def refresh_cards(self):
        if not self.cards:
            return
        cards_data = [{
            'image_path': card.image_path,
            'checkpoint_name': card.checkpoint_name,
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

            card = ImageCard(data['image_path'], data['checkpoint_name'], self,
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
        self.clear_btn.setText(config.get_text('btn_clear'))
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
        self.setStyleSheet(get_styles().fullscreen_background())

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

        self.image_container = QLabel()
        self.image_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_container.setStyleSheet(get_styles().image_container())
        self.image_container.mousePressEvent = self.mouse_press_on_image
        self.image_container.mouseMoveEvent = self.mouse_move_on_image
        self.image_container.mouseReleaseEvent = self.mouseReleaseEvent
        self.image_container.paintEvent = self.paint_image

        layout.addLayout(top_bar)
        layout.addWidget(self.image_container, stretch=1)
        layout.addLayout(info_layout)
        self.setLayout(layout)

        self.update_info_label()
        self.grid_combo.currentIndexChanged.connect(self.on_grid_changed)

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
        else:
            if selected_tab.cards:
                self.comparison_card = selected_tab.cards[0]
                pixmap2 = QPixmap(self.comparison_card.image_path)
                if not pixmap2.isNull():
                    self.comparison_pixmap = pixmap2
                self.info_label2.setVisible(True)
                self.split_position = 0.5
                self.update_info_label()
        self.image_container.update()

    def mouse_press_on_image(self, event):
        if self.comparison_pixmap:
            self.dragging_split = True
            self.update_split_from_mouse(event.pos().x())

    def mouse_move_on_image(self, event):
        if self.comparison_pixmap and (self.dragging_split or event.buttons() & Qt.MouseButton.LeftButton):
            self.dragging_split = True
            self.update_split_from_mouse(event.pos().x())

    def update_split_from_mouse(self, mouse_x):
        if self.image_width > 0:
            self.split_position = max(0.0, min(1.0, (mouse_x - self.image_x_offset) / self.image_width))
            self.image_container.update()

    def mouseReleaseEvent(self, event):
        self.dragging_split = False

    def update_info_label(self):
        module = self.grid_tab.get_active_module()
        self.info_label.setText(
            f"{self.card.checkpoint_name} - {os.path.basename(self.card.image_path)}"
            if module else os.path.basename(self.card.image_path))
        if self.comparison_card:
            self.info_label2.setText(
                f"{self.comparison_card.checkpoint_name} - {os.path.basename(self.comparison_card.image_path)}"
                if module else os.path.basename(self.comparison_card.image_path))

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
        self.ui_state_level1 = True  # True = visible (Espace/F11)
        self.ui_state_level2 = True  # True = visible (Ctrl+Espace/Ctrl+F11)

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

        self.remove_all_btn = QPushButton("-")
        self.remove_all_btn.setFixedSize(30, 30)
        self.remove_all_btn.setStyleSheet(get_styles().remove_tab_button())
        self.remove_all_btn.clicked.connect(self.remove_all_tabs)

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

    def close_tab_at_index(self, index):
        if self.tabs.count() > 1:
            widget = self.tabs.widget(index)
            self.tabs.removeTab(index)
            widget.deleteLater()
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
