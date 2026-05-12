"""
Criteria Manager Module
Like Checkpoint Manager but with fully customizable criteria
and numeric values (-10 to +10) instead of 3-state toggles.
"""
from PyQt6.QtWidgets import (QWidget, QPushButton, QLabel, QVBoxLayout,
                              QHBoxLayout, QDialog, QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt


DEFAULT_CRITERIA = ["beauty", "noErrors", "loras", "Pos prompt", "Neg prompt"]
MIN_VAL = -10
MAX_VAL = 10


def _get_config():
    from config.settings import config
    return config


def _get_colors():
    from config.settings import config
    return config.get_merged_colors()


def _get_mod_style():
    from modules.criteria_manager import style as _mod_style
    return _mod_style


def _get_criteria():
    stored = _get_config().get('criteria_manager_criteria')
    if stored and isinstance(stored, list) and len(stored) > 0:
        return list(stored)
    return DEFAULT_CRITERIA.copy()


def _fmt_val(val):
    return f"+{val}" if val > 0 else str(val)


# ── Criteria editor dialog ────────────────────────────────────────────────────

class CriteriaEditorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        config = _get_config()
        self.setWindowTitle(config.get_text('criteria_manager_dialog_title'))
        self.setModal(True)
        self.setFixedSize(360, 400)

        from config.options_style import apply_options_style
        apply_options_style(self)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 15, 15, 15)

        layout.addWidget(QLabel(config.get_text('criteria_manager_dialog_label') + ":"))

        self.list_widget = QListWidget()
        self.list_widget.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        layout.addWidget(self.list_widget)

        for name in _get_criteria():
            self._add_item(name)

        btn_row = QHBoxLayout()
        add_btn = QPushButton(config.get_text('criteria_manager_add'))
        add_btn.clicked.connect(self._add_new)
        remove_btn = QPushButton(config.get_text('criteria_manager_remove'))
        remove_btn.clicked.connect(self._remove_selected)
        reset_btn = QPushButton(config.get_text('criteria_manager_reset'))
        reset_btn.clicked.connect(self._reset_defaults)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(remove_btn)
        btn_row.addWidget(reset_btn)
        layout.addLayout(btn_row)

        ok_cancel = QHBoxLayout()
        ok_cancel.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.setFixedWidth(80)
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton(config.get_text('options_close_cancel'))
        cancel_btn.setFixedWidth(80)
        cancel_btn.clicked.connect(self.reject)
        ok_cancel.addWidget(ok_btn)
        ok_cancel.addWidget(cancel_btn)
        layout.addLayout(ok_cancel)

    def _add_item(self, name):
        item = QListWidgetItem(name)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        self.list_widget.addItem(item)

    def _add_new(self):
        self._add_item("New criterion")
        new_item = self.list_widget.item(self.list_widget.count() - 1)
        self.list_widget.setCurrentItem(new_item)
        self.list_widget.editItem(new_item)

    def _remove_selected(self):
        if self.list_widget.count() <= 1:
            return
        row = self.list_widget.currentRow()
        if row >= 0:
            self.list_widget.takeItem(row)

    def _reset_defaults(self):
        self.list_widget.clear()
        for name in DEFAULT_CRITERIA:
            self._add_item(name)

    def get_criteria(self):
        result = [
            self.list_widget.item(i).text().strip()
            for i in range(self.list_widget.count())
            if self.list_widget.item(i).text().strip()
        ]
        return result if result else DEFAULT_CRITERIA.copy()


# ── Module ────────────────────────────────────────────────────────────────────

class CriteriaManager:

    @staticmethod
    def get_module_name():
        return "Criteria Manager"

    @staticmethod
    def get_dropdown_options():
        return ["criteria_manager_action_criterias"]

    @staticmethod
    def get_settings_widget(config):
        return None

    # ── Data ──────────────────────────────────────────────────────────────────

    @staticmethod
    def create_module_data(filename, module_state):
        criteria = {c: 0 for c in _get_criteria()}
        return {'criteria': criteria, 'score': 0}

    @staticmethod
    def json_to_module_data(json_data):
        stored = json_data.get('criteria', {})
        current = _get_criteria()
        # Keep values for existing criteria, default to 0 for new ones
        criteria = {c: int(stored.get(c, 0)) for c in current}
        score = sum(criteria.values())
        return {'criteria': criteria, 'score': score}

    @staticmethod
    def card_to_json(card):
        return {
            'criteria': card.module_data.get('criteria', {}),
            'totalScore': card.module_data.get('score', 0),
        }

    # ── Card UI ───────────────────────────────────────────────────────────────

    @staticmethod
    def populate_card_top(card, top_layout):
        mod_style = _get_mod_style()
        colors = _get_colors()

        card.score_label = QLabel(str(card.module_data.get('score', 0)))
        card.score_label.setFixedSize(40, 40)
        card.score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card.score_label.setStyleSheet(mod_style.score_label(colors))

        top_layout.addStretch()
        top_layout.addWidget(card.score_label)

    @staticmethod
    def build_card_bottom(card):
        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 4, 2)
        layout.setSpacing(2)

        criteria = card.module_data.get('criteria', {})
        card.criteria_rows = {}

        for criterion in _get_criteria():
            val = criteria.get(criterion, 0)
            row_layout = CriteriaManager._build_criterion_row(card, criterion, val)
            layout.addLayout(row_layout)

        container.setLayout(layout)
        return container

    @staticmethod
    def _build_criterion_row(card, criterion, initial_val):
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(3)

        minus_btn = QPushButton("−")
        minus_btn.setFixedSize(22, 22)

        val_label = QLabel()
        val_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        plus_btn = QPushButton("+")
        plus_btn.setFixedSize(22, 22)

        card.criteria_rows[criterion] = {
            'minus': minus_btn,
            'label': val_label,
            'plus': plus_btn,
        }

        # Set initial appearance
        CriteriaManager._refresh_row(card, criterion, initial_val)

        minus_btn.clicked.connect(
            lambda _, c=criterion: CriteriaManager.change_value(card, c, -1))
        plus_btn.clicked.connect(
            lambda _, c=criterion: CriteriaManager.change_value(card, c, +1))

        row.addWidget(minus_btn)
        row.addWidget(val_label, 1)
        row.addWidget(plus_btn)
        return row

    @staticmethod
    def _refresh_row(card, criterion, val):
        mod_style = _get_mod_style()
        colors = _get_colors()
        rows = getattr(card, 'criteria_rows', {})
        if criterion not in rows:
            return
        row = rows[criterion]

        # Label color
        if val > 0:
            color = colors.get('pos', '#4CAF50')
        elif val < 0:
            color = colors.get('neg', '#c62828')
        else:
            color = colors.get('crit1', '#888')

        val_str = _fmt_val(val)
        row['label'].setText(f"{criterion}: {val_str}")
        row['label'].setStyleSheet(
            f"color: {color}; font-size: 11px; background: transparent;")

        row['minus'].setEnabled(val > MIN_VAL)
        row['plus'].setEnabled(val < MAX_VAL)
        row['minus'].setStyleSheet(mod_style.criterion_small_btn(colors, val <= MIN_VAL))
        row['plus'].setStyleSheet(mod_style.criterion_small_btn(colors, val >= MAX_VAL))

    @staticmethod
    def change_value(card, criterion, delta):
        criteria = card.module_data.setdefault('criteria', {})
        current = criteria.get(criterion, 0)
        new_val = max(MIN_VAL, min(MAX_VAL, current + delta))
        criteria[criterion] = new_val
        # Recalculate score from current criteria only
        active = _get_criteria()
        card.module_data['score'] = sum(criteria.get(c, 0) for c in active)
        CriteriaManager.apply_card_styles(card)

    @staticmethod
    def apply_card_styles(card):
        from config.settings import config as _config
        base_styles = _config.get_styles()
        mod_style = _get_mod_style()
        colors = _get_colors()

        active = _get_criteria()
        criteria = card.module_data.get('criteria', {})
        score = sum(criteria.get(c, 0) for c in active)
        card.module_data['score'] = score

        if score > 0:
            card.setStyleSheet(mod_style.card_border_pos(colors))
        elif score < 0:
            card.setStyleSheet(mod_style.card_border_red(colors))
        else:
            card.setStyleSheet(base_styles.card_style())

        if hasattr(card, 'score_label'):
            card.score_label.setText(str(score))
            card.score_label.setStyleSheet(mod_style.score_label(colors))

        if hasattr(card, 'criteria_rows'):
            for criterion in card.criteria_rows:
                CriteriaManager._refresh_row(card, criterion, criteria.get(criterion, 0))

    # ── Dropdown actions ──────────────────────────────────────────────────────

    @staticmethod
    def handle_dropdown_action(key, grid_tab):
        config = _get_config()
        if key == "criteria_manager_action_criterias":
            mw = grid_tab.get_main_window()
            dialog = CriteriaEditorDialog(mw)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_criteria = dialog.get_criteria()
                config.set('criteria_manager_criteria', new_criteria)
                grid_tab.refresh_cards()
                return {'log': config.get_text('criteria_manager_updated').format(n=len(new_criteria))}
        return None
