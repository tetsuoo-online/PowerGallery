"""
Dataset Manager Module
For each image, displays/edits the content of the matching .txt file
"""
from pathlib import Path
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QLabel, QLineEdit, QTextEdit, QCheckBox, QDialog)
from PyQt6.QtCore import QTimer


def _get_config():
    from config.settings import config
    return config


# ── Dialogs ───────────────────────────────────────────────────────────────────

class AddTagDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        config = _get_config()
        self.setWindowTitle(config.get_text('dataset_add_title'))
        self.setModal(True)
        self.setFixedSize(380, 200)

        main = QVBoxLayout()
        main.setSpacing(10)
        main.setContentsMargins(15, 15, 15, 15)

        tag_row = QHBoxLayout()
        tag_row.addWidget(QLabel(config.get_text('dataset_tag_to_insert') + ":"))
        self.tag_input = QLineEdit()
        tag_row.addWidget(self.tag_input)

        pos_row = QHBoxLayout()
        pos_row.addWidget(QLabel(config.get_text('dataset_at_position') + ":"))
        self.pos_input = QLineEdit("0")
        self.pos_input.setFixedWidth(70)
        pos_row.addWidget(self.pos_input)
        pos_row.addSpacing(10)

        self.from_begin = QPushButton(config.get_text('dataset_from_begin'))
        self.from_begin.setCheckable(True)
        self.from_begin.setChecked(True)
        self.from_begin.setFixedWidth(100)
        self.from_end = QPushButton(config.get_text('dataset_from_end'))
        self.from_end.setCheckable(True)
        self.from_end.setChecked(False)
        self.from_end.setFixedWidth(100)

        self.from_begin.clicked.connect(
            lambda: (self.from_begin.setChecked(True), self.from_end.setChecked(False)))
        self.from_end.clicked.connect(
            lambda: (self.from_end.setChecked(True), self.from_begin.setChecked(False)))

        pos_row.addWidget(self.from_begin)
        pos_row.addWidget(self.from_end)
        pos_row.addStretch()

        self.skip_existing = QCheckBox(config.get_text('dataset_skip_existing'))
        self.skip_existing.setChecked(True)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.setFixedWidth(80)
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton(config.get_text('options_close_cancel'))
        cancel_btn.setFixedWidth(80)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)

        main.addLayout(tag_row)
        main.addLayout(pos_row)
        main.addWidget(self.skip_existing)
        main.addStretch()
        main.addLayout(btn_row)
        self.setLayout(main)

    def get_params(self):
        tag = self.tag_input.text().strip()
        raw = self.pos_input.text().strip()
        from_end = self.from_end.isChecked()
        skip = self.skip_existing.isChecked()
        if (raw.startswith('"') and raw.endswith('"')) or \
           (raw.startswith("'") and raw.endswith("'")):
            position = raw[1:-1]
        else:
            try:
                position = int(raw)
            except ValueError:
                position = 0
        return tag, position, from_end, skip

    @staticmethod
    def insert_tag(current_text, tag, position, from_end, skip_existing):
        parts = [t.strip() for t in current_text.split(',') if t.strip()]
        if skip_existing and tag in parts:
            return current_text
        if isinstance(position, str):
            anchor = position.strip()
            try:
                idx = parts.index(anchor)
                insert_at = idx if not from_end else idx + 1
            except ValueError:
                insert_at = len(parts)
        else:
            insert_at = max(0, len(parts) - position) if from_end else min(position, len(parts))
        parts.insert(insert_at, tag)
        return ', '.join(parts)


class ReplaceTagDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        config = _get_config()
        self.setWindowTitle(config.get_text('dataset_replace_title'))
        self.setModal(True)
        self.setFixedSize(380, 175)

        main = QVBoxLayout()
        main.setSpacing(10)
        main.setContentsMargins(15, 15, 15, 15)

        for attr, key in [('old_input', 'dataset_replace_old'), ('new_input', 'dataset_replace_new')]:
            row = QHBoxLayout()
            lbl = QLabel(config.get_text(key) + ":")
            lbl.setFixedWidth(80)
            field = QLineEdit()
            setattr(self, attr, field)
            row.addWidget(lbl)
            row.addWidget(field)
            main.addLayout(row)

        self.case_sensitive = QCheckBox(config.get_text('dataset_case_sensitive'))
        self.case_sensitive.setChecked(False)
        main.addWidget(self.case_sensitive)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.setFixedWidth(80)
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton(config.get_text('options_close_cancel'))
        cancel_btn.setFixedWidth(80)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)

        main.addStretch()
        main.addLayout(btn_row)
        self.setLayout(main)

    def get_params(self):
        return (self.old_input.text().strip(),
                self.new_input.text().strip(),
                self.case_sensitive.isChecked())

    @staticmethod
    def replace_tag(current_text, old_tag, new_tag, case_sensitive):
        parts = [t.strip() for t in current_text.split(',') if t.strip()]
        result, changed = [], False
        for part in parts:
            match = part == old_tag if case_sensitive else part.lower() == old_tag.lower()
            if match:
                if new_tag:
                    result.append(new_tag)
                changed = True
            else:
                result.append(part)
        return ', '.join(result), changed


# ── Settings widget ───────────────────────────────────────────────────────────

class DatasetSettingsWidget(QWidget):
    def __init__(self, config_obj):
        super().__init__()
        self.config_obj = config_obj
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 0, 0, 0)
        self.clear_if_empty = QCheckBox(config_obj.get_text('dataset_clear_if_empty'))
        self.clear_if_empty.setChecked(config_obj.get('dataset_clear_if_empty') or False)
        layout.addWidget(self.clear_if_empty)
        self.setLayout(layout)

    def save(self):
        self.config_obj.set('dataset_clear_if_empty', self.clear_if_empty.isChecked())


# ── Module ────────────────────────────────────────────────────────────────────

class DatasetManager:
    is_text_module = True

    @staticmethod
    def get_module_name():
        return "Dataset"

    @staticmethod
    def get_dropdown_options():
        return ["dataset_action_add_tag", "dataset_action_replace_tag"]

    @staticmethod
    def get_settings_widget(config):
        return DatasetSettingsWidget(config)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def get_txt_path(image_path):
        return Path(image_path).with_suffix('.txt')

    @staticmethod
    def load_txt_content(image_path):
        txt_path = DatasetManager.get_txt_path(image_path)
        try:
            if txt_path.exists():
                return txt_path.read_text(encoding='utf-8')
        except Exception:
            pass
        return ""

    @staticmethod
    def save_txt_content(image_path, content):
        try:
            DatasetManager.get_txt_path(image_path).write_text(content, encoding='utf-8')
        except Exception as e:
            print(f"Dataset save error: {e}")

    # ── Card UI ───────────────────────────────────────────────────────────────

    @staticmethod
    def populate_card_top(card, top_layout):
        pass  # Dataset has no top section

    @staticmethod
    def build_card_bottom(card):
        txt_edit = QTextEdit()
        txt_edit.setFixedHeight(80)
        txt_edit.setPlaceholderText(_get_config().get_text('dataset_no_txt'))
        _colors = _get_config().get_styles().COLORS
        txt_edit.setStyleSheet(
            f"QTextEdit {{ background: {_colors.get('bg2', '#1e1e1e')}; "
            f"color: {_colors.get('text1', '#cccccc')}; "
            f"border: 1px solid {_colors.get('border1', '#444')}; "
            f"border-radius: 4px; font-size: 11px; padding: 2px; }}"
        )
        txt_edit.setPlainText(DatasetManager.load_txt_content(card.image_path))

        save_timer = QTimer(card)  # parented to card → auto-cleanup
        save_timer.setSingleShot(True)
        save_timer.timeout.connect(lambda: DatasetManager._save_txt(card))
        card._txt_save_timer = save_timer
        card.txt_edit = txt_edit

        txt_edit.textChanged.connect(lambda: save_timer.start(800))
        return txt_edit

    @staticmethod
    def _save_txt(card):
        if not hasattr(card, 'txt_edit'):
            return
        config = _get_config()
        content = card.txt_edit.toPlainText()
        txt_path = DatasetManager.get_txt_path(card.image_path)
        if not content.strip() and config.get('dataset_clear_if_empty'):
            try:
                if txt_path.exists():
                    txt_path.unlink()
            except Exception as e:
                print(f"Dataset delete error: {e}")
        else:
            DatasetManager.save_txt_content(card.image_path, content)

    @staticmethod
    def apply_card_styles(card):
        pass  # No special border/style for dataset

    @staticmethod
    def update_card_name(card, name):
        pass  # Dataset doesn't use checkpoint names

    # ── Data ──────────────────────────────────────────────────────────────────

    @staticmethod
    def card_to_json(card):
        return {}  # Data lives in .txt files, not JSON

    @staticmethod
    def json_to_module_data(json_data):
        return {}

    # ── Dropdown actions ──────────────────────────────────────────────────────

    @staticmethod
    def handle_dropdown_action(key, grid_tab):
        config = _get_config()

        if key == "dataset_action_add_tag":
            dialog = AddTagDialog(grid_tab.get_main_window())
            if dialog.exec() == QDialog.DialogCode.Accepted:
                tag, position, from_end, skip = dialog.get_params()
                if tag:
                    updated = sum(
                        DatasetManager._apply_add_tag(card, tag, position, from_end, skip)
                        for card in grid_tab.cards if hasattr(card, 'txt_edit')
                    )
                    return {'log': f"Tag '{tag}' ajouté à {updated} fichier(s)"}

        elif key == "dataset_action_replace_tag":
            dialog = ReplaceTagDialog(grid_tab.get_main_window())
            if dialog.exec() == QDialog.DialogCode.Accepted:
                old_tag, new_tag, case_sensitive = dialog.get_params()
                if old_tag:
                    updated = sum(
                        DatasetManager._apply_replace_tag(card, old_tag, new_tag, case_sensitive)
                        for card in grid_tab.cards if hasattr(card, 'txt_edit')
                    )
                    action = config.get_text('dataset_replaced_log')
                    return {'log': f"{action} '{old_tag}' → '{new_tag}' : {updated} fichier(s)"}
        return None

    @staticmethod
    def _apply_add_tag(card, tag, position, from_end, skip):
        old = card.txt_edit.toPlainText()
        new = AddTagDialog.insert_tag(old, tag, position, from_end, skip)
        if new != old:
            card.txt_edit.blockSignals(True)
            card.txt_edit.setPlainText(new)
            card.txt_edit.blockSignals(False)
            DatasetManager.save_txt_content(card.image_path, new)
            return 1
        return 0

    @staticmethod
    def _apply_replace_tag(card, old_tag, new_tag, case_sensitive):
        old_text = card.txt_edit.toPlainText()
        new_text, changed = ReplaceTagDialog.replace_tag(old_text, old_tag, new_tag, case_sensitive)
        if changed:
            card.txt_edit.blockSignals(True)
            card.txt_edit.setPlainText(new_text)
            card.txt_edit.blockSignals(False)
            DatasetManager.save_txt_content(card.image_path, new_text)
            return 1
        return 0
