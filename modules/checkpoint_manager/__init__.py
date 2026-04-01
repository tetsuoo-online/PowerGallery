"""
Checkpoint Manager Module
"""
from pathlib import Path
from PyQt6.QtWidgets import (QFileDialog, QWidget, QPushButton, QLabel,
                              QLayout, QSizePolicy)
from PyQt6.QtCore import Qt, QPoint, QRect, QSize


def _get_styles():
    from config.settings import config
    return config.get_styles()

def _get_colors():
    from config.settings import config
    return config.get_merged_colors()

def _get_mod_style():
    from modules.checkpoint_manager import style as _mod_style
    return _mod_style


CRITERIA_LIST = ["beauty", "noErrors", "loras", "Pos prompt", "Neg prompt"]


class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=-1):
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self.item_list = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item): self.item_list.append(item)
    def count(self): return len(self.item_list)

    def itemAt(self, index):
        return self.item_list[index] if 0 <= index < len(self.item_list) else None

    def takeAt(self, index):
        return self.item_list.pop(index) if 0 <= index < len(self.item_list) else None

    def expandingDirections(self): return Qt.Orientation(0)
    def hasHeightForWidth(self): return True
    def heightForWidth(self, width): return self._do_layout(QRect(0, 0, width, 0), True)
    def setGeometry(self, rect): super().setGeometry(rect); self._do_layout(rect, False)
    def sizeHint(self): return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.item_list:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins().left()
        return size + QSize(2 * m, 2 * m)

    def _do_layout(self, rect, test_only):
        x, y, line_height = rect.x(), rect.y(), 0
        spacing = self.spacing()
        for item in self.item_list:
            w = item.widget()
            sx = spacing + w.style().layoutSpacing(
                QSizePolicy.ControlType.PushButton, QSizePolicy.ControlType.PushButton, Qt.Orientation.Horizontal)
            sy = spacing + w.style().layoutSpacing(
                QSizePolicy.ControlType.PushButton, QSizePolicy.ControlType.PushButton, Qt.Orientation.Vertical)
            next_x = x + item.sizeHint().width() + sx
            if next_x - sx > rect.right() and line_height > 0:
                x, y, next_x = rect.x(), y + line_height + sy, rect.x() + item.sizeHint().width() + sx
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            x = next_x
            line_height = max(line_height, item.sizeHint().height())
        return y + line_height - rect.y()


class CheckpointManager:

    @staticmethod
    def get_module_name():
        return "Checkpoint Manager"

    @staticmethod
    def get_dropdown_options():
        return ["Checkpoints Folder", "Checkpoints.txt"]

    @staticmethod
    def get_criteria_list():
        return CRITERIA_LIST.copy()

    @staticmethod
    def get_settings_widget(config):
        return None

    # ── Filename extraction ───────────────────────────────────────────────────

    @staticmethod
    def _extract_checkpoint(filename, checkpoints_list):
        """Sort by descending length to avoid substring matching shorter names first."""
        for checkpoint in sorted(checkpoints_list, key=len, reverse=True):
            if checkpoint in filename:
                return checkpoint
        return ''

    # ── Module data creation ──────────────────────────────────────────────────

    @staticmethod
    def create_module_data(filename, module_state):
        """Called when loading a new image file. Extracts checkpoint from filename."""
        checkpoints_list = module_state.get('checkpoints_list', [])
        checkpoint_name = CheckpointManager._extract_checkpoint(filename, checkpoints_list)
        return {
            'checkpoint_name': checkpoint_name,
            'display_title': checkpoint_name,
            'display_title_label': 'Checkpoint',
            'criteria': {},
            'score': 0,
        }

    @staticmethod
    def json_to_module_data(json_data):
        checkpoint_name = json_data.get('checkpointName', '')
        return {
            'checkpoint_name': checkpoint_name,
            'display_title': checkpoint_name,
            'display_title_label': 'Checkpoint',
            'criteria': json_data.get('criteria', {}),
            'score': json_data.get('totalScore', 0),
        }

    # ── Card name update (batch) ──────────────────────────────────────────────

    @staticmethod
    def update_existing_card_names(grid_tab):
        """Update all cards in grid_tab using the current checkpoints_list in module_state."""
        import os
        checkpoints_list = grid_tab.module_state.get('checkpoints_list', [])
        updated = 0
        for card in grid_tab.cards:
            filename = os.path.basename(card.image_path)
            new_name = CheckpointManager._extract_checkpoint(filename, checkpoints_list)
            if new_name and new_name != card.module_data.get('checkpoint_name', ''):
                CheckpointManager.update_card_name(card, new_name)
                updated += 1
        return updated

    # ── Card UI ───────────────────────────────────────────────────────────────

    @staticmethod
    def populate_card_top(card, top_layout):
        mod_style = _get_mod_style()
        colors = _get_colors()

        card.checkpoint_label = QLabel(card.module_data.get('checkpoint_name', ''))
        card.checkpoint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card.checkpoint_label.setStyleSheet(mod_style.checkpoint_label(colors))

        card.score_label = QLabel(str(card.module_data.get('score', 0)))
        card.score_label.setFixedSize(40, 40)
        card.score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card.score_label.setStyleSheet(mod_style.score_label(colors))

        top_layout.addWidget(card.checkpoint_label)
        top_layout.addStretch()
        top_layout.addWidget(card.score_label)

        CheckpointManager.apply_card_styles(card)

    @staticmethod
    def build_card_bottom(card):
        container = QWidget()
        layout = FlowLayout(spacing=5)
        criteria = card.module_data.get('criteria', {})
        card.criteria_buttons = {}

        for criterion in CRITERIA_LIST:
            btn = QPushButton(criterion)
            btn.setFixedSize(95, 30)
            CheckpointManager._style_btn(btn, criteria.get(criterion, 0))
            btn.clicked.connect(
                lambda _, c=criterion, b=btn: CheckpointManager.cycle_criterion(card, c, b))
            layout.addWidget(btn)
            card.criteria_buttons[criterion] = btn

        container.setLayout(layout)
        return container

    @staticmethod
    def cycle_criterion(card, criterion, button):
        criteria = card.module_data.setdefault('criteria', {})
        new_state = (criteria.get(criterion, 0) + 2) % 3 - 1
        criteria[criterion] = new_state
        card.module_data['score'] = sum(criteria.values())
        CheckpointManager._style_btn(button, new_state)
        CheckpointManager.apply_card_styles(card)

    @staticmethod
    def _style_btn(button, state):
        mod_style = _get_mod_style()
        colors = _get_colors()
        if state == 1:
            button.setStyleSheet(mod_style.criterion_button_green(colors))
        elif state == -1:
            button.setStyleSheet(mod_style.criterion_button_red(colors))
        else:
            button.setStyleSheet(mod_style.criterion_button_neutral(colors))

    @staticmethod
    def apply_card_styles(card):
        base_styles = _get_styles()
        mod_style = _get_mod_style()
        colors = _get_colors()
        score = card.module_data.get('score', 0)

        if score > 0:
            card.setStyleSheet(mod_style.card_border_pos(colors))
        elif score < 0:
            card.setStyleSheet(mod_style.card_border_red(colors))
        else:
            card.setStyleSheet(base_styles.card_style())

        if hasattr(card, 'score_label'):
            card.score_label.setText(str(score))
            card.score_label.setStyleSheet(mod_style.score_label(colors))
        if hasattr(card, 'checkpoint_label'):
            card.checkpoint_label.setStyleSheet(mod_style.checkpoint_label(colors))
        if hasattr(card, 'criteria_buttons'):
            criteria = card.module_data.get('criteria', {})
            for criterion, btn in card.criteria_buttons.items():
                CheckpointManager._style_btn(btn, criteria.get(criterion, 0))

    @staticmethod
    def update_card_name(card, name):
        card.module_data['checkpoint_name'] = name
        card.module_data['display_title'] = name
        card.module_data['display_title_label'] = 'Checkpoint'
        if hasattr(card, 'checkpoint_label'):
            card.checkpoint_label.setText(name)

    # ── Data ─────────────────────────────────────────────────────────────────

    @staticmethod
    def card_to_json(card):
        return {
            'checkpointName': card.module_data.get('checkpoint_name', ''),
            'criteria': card.module_data.get('criteria', {}),
            'totalScore': card.module_data.get('score', 0),
        }

    # ── Dropdown actions ──────────────────────────────────────────────────────

    @staticmethod
    def handle_dropdown_action(key, grid_tab):
        from config.settings import config as _config
        if key == "Checkpoints Folder":
            result = CheckpointManager.load_from_folder(grid_tab)
            if result:
                checkpoints = result['images']
                grid_tab.module_state['checkpoints_list'] = checkpoints
                updated = CheckpointManager.update_existing_card_names(grid_tab)
                msg = f"Loaded {len(checkpoints)} checkpoints"
                if result.get('txt_created'):
                    msg += f", saved to {Path(result['txt_created']).name}"
                if updated:
                    msg += f", updated {updated} card(s)"
                return {'log': msg}
            return {'log': "No checkpoints found"}

        elif key == "Checkpoints.txt":
            result = CheckpointManager.load_from_txt(grid_tab)
            if result:
                checkpoints = result['images']
                grid_tab.module_state['checkpoints_list'] = checkpoints
                updated = CheckpointManager.update_existing_card_names(grid_tab)
                msg = f"Loaded {len(checkpoints)} checkpoints"
                if updated:
                    msg += f", updated {updated} card(s)"
                return {'log': msg}
        return None

    # ── Loaders ───────────────────────────────────────────────────────────────

    @staticmethod
    def load_from_folder(parent_widget):
        folder = QFileDialog.getExistingDirectory(parent_widget, "Select Checkpoints Folder")
        if not folder:
            return None
        path = Path(folder)
        checkpoints = [
            item.stem for item in path.rglob("*.safetensors")
            if len(item.relative_to(path).parts) <= 3
        ]
        if not checkpoints:
            return None
        txt_path = path / f"checkpoints_{path.name}.txt"
        try:
            txt_path.write_text('\n'.join(checkpoints) + '\n', encoding='utf-8')
        except Exception as e:
            print(f"Error writing txt: {e}")
        return {'images': checkpoints, 'source': 'folder',
                'folder_path': folder, 'txt_created': str(txt_path)}

    @staticmethod
    def load_from_txt(parent_widget):
        file_path, _ = QFileDialog.getOpenFileName(
            parent_widget, "Select Checkpoints.txt", "", "Text Files (*.txt)")
        if not file_path:
            return None
        try:
            lines = Path(file_path).read_text(encoding='utf-8').splitlines()
            checkpoints = [l.strip() for l in lines if l.strip() and not l.startswith('#')]
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return None
        return {'images': checkpoints, 'source': 'txt', 'txt_path': file_path}