"""
Style Editor — visual interface for creating and editing custom styles.
Two sub-tabs: Base (theme colors) and Module (module COLORS_EXTRA).
"""

import importlib
import sys
from pathlib import Path
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QListWidget, QColorDialog, QLineEdit,
                             QMessageBox, QTabWidget, QWidget, QGridLayout,
                             QScrollArea, QGroupBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor


# ── Shared color editor panel ─────────────────────────────────────────────────

class ColorEditorPanel(QWidget):
    """
    Reusable panel: list of styles on the left, color grid on the right.
    Works for both base themes and module styles.
    """

    def __init__(self, config, mode, parent=None):
        """
        mode : 'base' | 'module'
        """
        super().__init__(parent)
        self.config = config
        self.mode = mode
        self.current_style_name = None
        self.current_colors = {}
        self.color_buttons = {}
        self._readonly = True   # True when a built-in / locked style is selected
        self._setup_ui()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _setup_ui(self):
        main = QVBoxLayout()
        main.setContentsMargins(0, 0, 0, 0)

        top = QHBoxLayout()

        # Style list
        list_group = QGroupBox(self.config.get_text('style_available_styles'))
        ll = QVBoxLayout()
        self.style_list = QListWidget()
        self.style_list.currentItemChanged.connect(self._on_style_selected)
        ll.addWidget(self.style_list)
        list_group.setLayout(ll)

        # Actions
        act_group = QGroupBox(self.config.get_text('style_actions'))
        al = QVBoxLayout()
        self.new_name_input = QLineEdit()
        self.new_name_input.setPlaceholderText(self.config.get_text('style_new_name_placeholder'))
        self.duplicate_btn = QPushButton(self.config.get_text('style_duplicate_btn'))
        self.duplicate_btn.clicked.connect(self.duplicate_style)
        self.delete_btn = QPushButton(self.config.get_text('style_delete_btn'))
        self.delete_btn.clicked.connect(self.delete_style)
        self.delete_btn.setEnabled(False)
        al.addWidget(QLabel(self.config.get_text('style_select_to_duplicate')))
        al.addWidget(self.new_name_input)
        al.addWidget(self.duplicate_btn)
        al.addWidget(QLabel(""))
        al.addWidget(self.delete_btn)
        al.addStretch()
        act_group.setLayout(al)

        top.addWidget(list_group, 2)
        top.addWidget(act_group, 1)

        # Color grid
        editor_group = QGroupBox(self.config.get_text('style_color_editor'))
        el = QVBoxLayout()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        sw = QWidget()
        self.colors_grid = QGridLayout()
        sw.setLayout(self.colors_grid)
        scroll.setWidget(sw)
        el.addWidget(scroll)
        editor_group.setLayout(el)

        main.addLayout(top, 1)
        main.addWidget(editor_group, 2)
        self.setLayout(main)

    # ── Style list loading ────────────────────────────────────────────────────

    def load_styles_list(self, select_name=None):
        self.style_list.currentItemChanged.disconnect(self._on_style_selected)
        self.style_list.clear()

        if self.mode == 'base':
            self._load_base_list()
            current = select_name or self.config.get('current_style')
        else:
            self._load_module_list()
            current = select_name or self.config.get('current_module_style')

        # Select matching item
        for i in range(self.style_list.count()):
            text = self.style_list.item(i).text()
            name = text.split()[-1] if text.split()[-1] not in ['(built-in)', self.config.get_text('style_builtin_suffix')] else text.split()[1]
            # simpler: check if current name is contained
            if current and current in text:
                self.style_list.setCurrentRow(i)
                self._readonly = text.startswith('🔒')
                self.delete_btn.setEnabled(not self._readonly)
                self.current_style_name = current
                self._load_colors(current)
                break

        self.style_list.currentItemChanged.connect(self._on_style_selected)

    def _load_base_list(self):
        suffix = self.config.get_text('style_builtin_suffix')
        self.style_list.addItem(f"🔒 dark {suffix}")
        self.style_list.addItem(f"🔒 light {suffix}")
        custom_dir = Path(__file__).parent / 'custom_styles'
        if custom_dir.exists():
            for f in sorted(custom_dir.glob('*.py')):
                if f.name != '__init__.py':
                    self.style_list.addItem(f"✏️ {f.stem}")

    def _load_module_list(self):
        module_key = self.config.get('selected_module')
        if not module_key:
            return
        suffix = self.config.get_text('style_builtin_suffix')
        self.style_list.addItem(f"🔒 style {suffix}")
        custom_dir = self._module_custom_dir(module_key)
        if custom_dir and custom_dir.exists():
            for f in sorted(custom_dir.glob('*.py')):
                if f.name != '__init__.py':
                    self.style_list.addItem(f"✏️ {f.stem}")

    @staticmethod
    def _module_custom_dir(module_key):
        base = Path(__file__).parent.parent / 'modules' / module_key / 'custom'
        return base

    # ── Selection handler ─────────────────────────────────────────────────────

    def _on_style_selected(self, current, previous):
        if not current:
            return
        text = current.text()
        if text.startswith('🔒'):
            self.current_style_name = text.split()[1]
            self._readonly = True
            self.delete_btn.setEnabled(False)
        elif text.startswith('✏️'):
            self.current_style_name = text.split()[1]
            self._readonly = False
            self.delete_btn.setEnabled(True)
        else:
            return

        self._load_colors(self.current_style_name)

        if self.mode == 'base':
            self.config.set_current_style(self.current_style_name)
            self._notify_style_change()
        else:
            self.config.set('current_module_style', self.current_style_name)
            self._notify_style_change()

    def _notify_style_change(self):
        parent = self.parent()
        while parent:
            if parent.__class__.__name__ == 'MainWindow':
                parent.apply_styles()
                break
            parent = parent.parent() if hasattr(parent, 'parent') else None

    # ── Color loading ─────────────────────────────────────────────────────────

    def _load_colors(self, style_name):
        try:
            if self.mode == 'base':
                mod = self._load_base_module(style_name)
                self.current_colors = mod.COLORS.copy()
            else:
                mod = self._load_module_style(style_name)
                self.current_colors = mod.COLORS_EXTRA.copy()
            self._display_color_editor()
        except Exception as e:
            QMessageBox.warning(self, "Error",
                                self.config.get_text('style_load_error').format(e=e))

    def _load_base_module(self, name):
        if name == 'dark':
            import config.styles_dark as m; return m
        if name == 'light':
            import config.styles_light as m; return m
        return importlib.import_module(f'config.custom_styles.{name}')

    def _load_module_style(self, name):
        module_key = self.config.get('selected_module')
        if name == 'style':
            return importlib.import_module(f'modules.{module_key}.style')
        # custom override
        custom_dir = self._module_custom_dir(module_key)
        path = custom_dir / f'{name}.py'
        spec = importlib.util.spec_from_file_location(
            f'modules.{module_key}.custom.{name}', path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    # ── Color editor display ──────────────────────────────────────────────────

    def _display_color_editor(self):
        while self.colors_grid.count():
            item = self.colors_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.color_buttons.clear()

        for row, (name, value) in enumerate(self.current_colors.items()):
            lbl = QLabel(name + ":")
            lbl.setMinimumWidth(150)

            btn = QPushButton()
            btn.setFixedSize(80, 30)
            btn.setStyleSheet(f"background-color: {value}; border: 1px solid #888;")
            btn.setEnabled(not self._readonly)
            if not self._readonly:
                btn.clicked.connect(lambda checked, n=name: self._pick_color(n))

            val_lbl = QLabel(value)
            val_lbl.setMinimumWidth(80)

            self.colors_grid.addWidget(lbl, row, 0)
            self.colors_grid.addWidget(btn, row, 1)
            self.colors_grid.addWidget(val_lbl, row, 2)
            self.color_buttons[name] = (btn, val_lbl)

    def _pick_color(self, color_name):
        if self._readonly:
            QMessageBox.information(
                self,
                self.config.get_text('style_readonly_title'),
                self.config.get_text('style_readonly_msg'))
            return
        qcolor = QColor(self.current_colors[color_name])
        color = QColorDialog.getColor(
            qcolor, self,
            self.config.get_text('style_pick_color').format(name=color_name))
        if color.isValid():
            hex_val = color.name()
            self.current_colors[color_name] = hex_val
            btn, lbl = self.color_buttons[color_name]
            btn.setStyleSheet(f"background-color: {hex_val}; border: 1px solid #888;")
            lbl.setText(hex_val)
            self._save_current()
            self._notify_style_change()

    # ── Save ──────────────────────────────────────────────────────────────────

    def _save_current(self):
        if self._readonly or not self.current_style_name:
            return
        if self.mode == 'base':
            self._save_base_style(self.current_style_name, self.current_colors)
        else:
            self._save_module_style(self.current_style_name, self.current_colors)

    def _save_base_style(self, name, colors):
        custom_dir = Path(__file__).parent / 'custom_styles'
        custom_dir.mkdir(exist_ok=True)
        path = custom_dir / f'{name}.py'
        lines = [f"# Custom style: {name}", "# Auto-generated by Style Editor", "",
                 "COLORS = {"]
        for k, v in colors.items():
            lines.append(f"    '{k}': '{v}',")
        lines += ["}", "",
                  "from pathlib import Path as _Path",
                  "exec((_Path(__file__).parent.parent / 'styles_base_layout.py').read_text(encoding='utf-8'))"]
        path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        mod_name = f'config.custom_styles.{name}'
        if mod_name in sys.modules:
            importlib.reload(sys.modules[mod_name])
        else:
            importlib.import_module(mod_name)

    def _save_module_style(self, name, colors):
        module_key = self.config.get('selected_module')
        custom_dir = self._module_custom_dir(module_key)
        custom_dir.mkdir(parents=True, exist_ok=True)
        init = custom_dir / '__init__.py'
        if not init.exists():
            init.write_text('', encoding='utf-8')
        path = custom_dir / f'{name}.py'
        lines = [f"# Module style override: {name}", "# Auto-generated by Style Editor", "",
                 "COLORS_EXTRA = {"]
        for k, v in colors.items():
            lines.append(f"    '{k}': '{v}',")
        lines += ["}"]
        path.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    # ── Duplicate / Delete ────────────────────────────────────────────────────

    def duplicate_style(self):
        if not self.current_style_name:
            QMessageBox.warning(self, "Warning", "Please select a style to duplicate")
            return
        new_name = self.new_name_input.text().strip()
        if not new_name:
            QMessageBox.warning(self, "Warning", "Please enter a name for the new style")
            return
        if self.mode == 'base' and new_name.lower() in ['dark', 'light']:
            QMessageBox.warning(self,
                self.config.get_text('style_reserved_title'),
                self.config.get_text('style_reserved_msg').format(name=new_name))
            return
        if self.mode == 'module' and new_name.lower() == 'style':
            QMessageBox.warning(self,
                self.config.get_text('style_reserved_title'),
                self.config.get_text('style_reserved_msg').format(name=new_name))
            return
        if not new_name.replace('_', '').isalnum():
            QMessageBox.warning(self, "Warning", self.config.get_text('style_invalid_name'))
            return

        if self.mode == 'base':
            dest = Path(__file__).parent / 'custom_styles' / f'{new_name}.py'
        else:
            dest = self._module_custom_dir(self.config.get('selected_module')) / f'{new_name}.py'

        if dest.exists():
            QMessageBox.warning(self, "Warning",
                self.config.get_text('style_already_exists').format(name=new_name))
            return

        if self.mode == 'base':
            self._save_base_style(new_name, self.current_colors)
        else:
            self._save_module_style(new_name, self.current_colors)

        self.load_styles_list(select_name=new_name)
        self.new_name_input.clear()

    def delete_style(self):
        if not self.current_style_name or self._readonly:
            return
        reply = QMessageBox.question(
            self,
            self.config.get_text('style_confirm_delete_title'),
            self.config.get_text('style_confirm_delete_msg').format(name=self.current_style_name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return

        if self.mode == 'base':
            target = Path(__file__).parent / 'custom_styles' / f'{self.current_style_name}.py'
        else:
            target = (self._module_custom_dir(self.config.get('selected_module'))
                      / f'{self.current_style_name}.py')
        try:
            target.unlink()
            self.load_styles_list()
        except Exception as e:
            QMessageBox.critical(self, "Error",
                self.config.get_text('style_delete_error').format(e=e))


# ── StyleEditorWidget (embedded in Options > Style tab) ───────────────────────

class StyleEditorWidget(QWidget):

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self._setup_ui()
        self.reload()

    def _setup_ui(self):
        main = QVBoxLayout()
        main.setContentsMargins(0, 0, 0, 0)

        self.sub_tabs = QTabWidget()

        self.base_panel = ColorEditorPanel(self.config, mode='base', parent=self)
        self.module_panel = ColorEditorPanel(self.config, mode='module', parent=self)

        self.sub_tabs.addTab(self.base_panel, self.config.get_text('style_tab_base'))
        self.sub_tabs.addTab(self.module_panel, self.config.get_text('style_tab_module'))

        main.addWidget(self.sub_tabs)
        self.setLayout(main)

    def reload(self):
        """Refresh both panels — call after module or style change."""
        self.base_panel.load_styles_list()
        module_key = self.config.get('selected_module')
        has_module_style = False
        if module_key:
            try:
                importlib.import_module(f'modules.{module_key}.style')
                has_module_style = True
            except ModuleNotFoundError:
                pass

        self.sub_tabs.setTabEnabled(1, has_module_style)
        if has_module_style:
            self.module_panel.load_styles_list()
        else:
            # Clear module panel
            while self.module_panel.colors_grid.count():
                item = self.module_panel.colors_grid.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self.module_panel.style_list.clear()
            self.module_panel.style_list.addItem(
                self.config.get_text('style_module_no_style'))


# ── StyleEditorDialog (standalone dialog, kept for compatibility) ──────────────

class StyleEditorDialog(QDialog):

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Style Editor")
        self.setModal(True)
        self.setMinimumSize(700, 600)

        layout = QVBoxLayout()
        self.editor = StyleEditorWidget(config, self)
        close_btn = QPushButton(self.config.get_text('style_apply_close'))
        close_btn.clicked.connect(self.accept)
        layout.addWidget(self.editor)
        layout.addWidget(close_btn)
        self.setLayout(layout)
