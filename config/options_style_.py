"""
Options Dialog Light Style
Fixed light theme for Options dialog for better readability
"""

def get_options_light_style():
    """Return the light style CSS for the Options dialog"""
    return """
QDialog {
    background-color: #f5f5f5;
    color: #222222;
}

QTabWidget::pane {
    border: 1px solid #cccccc;
    background: white;
}

QTabBar::tab {
    background: #e0e0e0;
    color: #222222;
    padding: 8px 20px;
    border: 1px solid #cccccc;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}

QTabBar::tab:selected {
    background: white;
    color: #222222;
}

QTabBar::tab:hover {
    background: #d5d5d5;
}

QGroupBox {
    border: 1px solid #cccccc;
    border-radius: 5px;
    margin-top: 10px;
    padding-top: 10px;
    background: white;
    color: #222222;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 5px;
    color: #222222;
}

QCheckBox {
    color: #222222;
    spacing: 5px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #999999;
    border-radius: 3px;
    background: white;
}

QCheckBox::indicator:checked {
    background: #2196f3;
    border: 1px solid #2196f3;
}

QLabel {
    color: #222222;
}

QPushButton {
    background-color: #2196f3;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #1976d2;
}

QPushButton:pressed {
    background-color: #1565c0;
}

QLineEdit {
    background: white;
    color: #222222;
    border: 1px solid #cccccc;
    border-radius: 4px;
    padding: 5px;
}

QListWidget {
    background: white;
    color: #222222;
    border: 1px solid #cccccc;
    border-radius: 4px;
}

QListWidget::item {
    padding: 5px;
}

QListWidget::item:selected {
    background: #e3f2fd;
    color: #222222;
}

QListWidget::item:hover {
    background: #f5f5f5;
}

QScrollArea {
    background: white;
    border: 1px solid #cccccc;
}
"""
