# ============================================================================
# STYLES BASE LAYOUT
# Shared style functions for all themes (dark, light, custom).
# Each theme file defines COLORS then exec()'s this file.
#
# COLOR FAMILIES:
#   bg1-4, border1-2, text1-2  → UI générale
#   tab_bg, tab_sel             → Onglets
#   accent                      → Interactif / highlight
#   canvas                      → Image viewer / fullscreen background
#   danger, danger_hover        → Boutons destructifs UI (close, clear, remove)
# ============================================================================

# Styles as functions |Marker for style_editor, don't edit or remove
def card_style():
    return f"""
        ImageCard {{
            border: 2px solid {COLORS['border1']};
            border-radius: 12px;
            background: {COLORS['bg2']};
        }}
    """

def close_button():
    return f"""
        QPushButton {{
            background: {COLORS['danger']};
            color: {COLORS['text1']};
            font-weight: bold;
            font-size: 18px;
        }}
        QPushButton:hover {{
            background: {COLORS['danger_hover']};
        }}
    """

def main_theme():
    return f"""
        QWidget {{
            background-color: {COLORS['tab_bg']};
            color: {COLORS['text1']};
        }}
        QGroupBox {{
            color: {COLORS['text1']};
            border: 1px solid {COLORS['border2']};
            border-radius: 6px;
            margin-top: 8px;
            padding-top: 8px;
        }}
        QGroupBox::title {{
            color: {COLORS['text1']};
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 3px;
        }}
        QPushButton {{
            background: {COLORS['bg3']};
            color: {COLORS['text1']};
            border: 1px solid {COLORS['border2']};
            border-radius: 6px;
            padding: 5px 10px;
        }}
        QPushButton:hover {{
            background: {COLORS['border1']};
        }}
        QLabel {{
            color: {COLORS['text1']};
        }}
        QSlider::groove:horizontal {{
            background: {COLORS['bg3']};
            height: 8px;
            border-radius: 4px;
        }}
        QSlider::handle:horizontal {{
            background: {COLORS['accent']};
            width: 18px;
            margin: -5px 0;
            border-radius: 9px;
        }}
        QScrollArea {{
            border: none;
            background: {COLORS['tab_bg']};
        }}
    """

def drop_zone():
    return f"""
        QLabel {{
            border: 3px dashed {COLORS['border2']};
            background: {COLORS['bg4']};
            color: {COLORS['text2']};
            font-size: 16px;
            font-weight: bold;
            min-height: 80px;
            border-radius: 8px;
        }}
        QLabel:hover {{
            border-color: {COLORS['accent']};
            color: {COLORS['accent']};
        }}
    """

def clear_button():
    return f"""
        QPushButton {{
            background: {COLORS['danger']};
            color: {COLORS['text1']};
            font-weight: bold;
        }}
        QPushButton:hover {{
            background: {COLORS['danger_hover']};
        }}
    """

def refresh_button():
    return f"""
        QPushButton {{
            background: {COLORS['accent']};
            color: {COLORS['text1']};
            font-weight: bold;
        }}
        QPushButton:hover {{
            background: {COLORS['bg4']};
        }}
    """

def main_window():
    return f"""
        QMainWindow {{
            background-color: {COLORS['bg1']};
        }}
        QTabWidget::pane {{
            border: 1px solid {COLORS['border1']};
            background: {COLORS['tab_bg']};
            border-radius: 8px;
        }}
        QTabBar::tab {{
            background: {COLORS['bg2']};
            color: {COLORS['text1']};
            border: 1px solid {COLORS['border1']};
            padding: 8px 16px;
            margin-right: 2px;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
        }}
        QTabBar::tab:selected {{
            background: {COLORS['tab_sel']};
            border: 1px solid {COLORS['tab_sel']};
            border-bottom: 1px solid {COLORS['tab_sel']};
        }}
        QTabBar::tab:!selected:hover {{
            background: {COLORS['tab_bg']};
        }}
    """

def add_tab_button():
    return f"""
        QPushButton {{
            background: {COLORS['bg3']};
            color: {COLORS['text1']};
            border: 1px solid {COLORS['border2']};
            border-radius: 6px;
            font-weight: bold;
            font-size: 18px;
        }}
        QPushButton:hover {{
            background: {COLORS['border1']};
        }}
    """

def remove_tab_button():
    return f"""
        QPushButton {{
            background: {COLORS['danger']};
            color: {COLORS['text1']};
            border: 1px solid {COLORS['danger']};
            border-radius: 6px;
            font-weight: bold;
            font-size: 18px;
        }}
        QPushButton:hover {{
            background: {COLORS['danger_hover']};
        }}
    """

def fullscreen_background():
    return f"background-color: {COLORS['canvas']};"

def fullscreen_close_button():
    return f"""
        QPushButton {{
            background: {COLORS['danger']};
            color: {COLORS['text1']};
            border: none;
            border-radius: 6px;
            font-size: 16px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background: {COLORS['danger_hover']};
        }}
    """

def fullscreen_label():
    return f"color: {COLORS['text1']}; font-size: 14px; margin-left: 20px;"

def fullscreen_combo():
    return f"""
        QComboBox {{
            background: {COLORS['bg3']};
            color: {COLORS['text1']};
            border: 1px solid {COLORS['border2']};
            border-radius: 6px;
            padding: 5px 10px;
            min-width: 150px;
            font-size: 14px;
        }}
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        QComboBox::down-arrow {{
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid {COLORS['text1']};
            width: 0px;
            height: 0px;
        }}
        QComboBox QAbstractItemView {{
        	background: {COLORS['bg3']};
            color: {COLORS['text1']};
        }}
        QComboBox QAbstractItemView::item:selected {{
            background: {COLORS['accent']};
        }}
    """

def fullscreen_info():
    return f"color: {COLORS['text1']}; font-size: 14px; font-weight: bold; padding: 10px;"

def fullscreen_info_selectable():
    return (f"color: {COLORS['text1']}; font-size: 14px; font-weight: bold; padding: 10px; "
            f"selection-background-color: {COLORS['accent']}; selection-color: {COLORS['text1']};")

def image_container():
    return f"background: {COLORS['canvas']};"

def options_button():
    return f"""
        QPushButton {{
            background: {COLORS['bg3']};
            color: {COLORS['text1']};
            border: 1px solid {COLORS['border2']};
            border-radius: 6px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background: {COLORS['border1']};
        }}
    """
