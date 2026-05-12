# ============================================================================
# CRITERIA MANAGER - Module styles
# COLORS_EXTRA : additional color keys, merged on top of the base theme.
# Style functions : only used by criteria_manager.
# ============================================================================

COLORS_EXTRA = {
    # ── Score widget ──────────────────────────────────────────────────────────
    'score':        'yellow',
    'score_border': '#1e1e1e',
    # ── Criterion neutral ─────────────────────────────────────────────────────
    'crit1':        '#888',
    # ── Positive ──────────────────────────────────────────────────────────────
    'pos':          '#4CAF50',
    'pos_bg':       '#2d5016',
    'pos_hover':    '#356019',
    # ── Negative ──────────────────────────────────────────────────────────────
    'neg':          '#c62828',
    'neg_bg':       '#5c1a1a',
    'neg_hover':    '#6b2020',
}


def get_merged_colors(base_colors):
    merged = dict(base_colors)
    merged.update(COLORS_EXTRA)
    return merged


def score_label(colors):
    return f"""
        color: {colors['score']};
        font-size: 20px;
        font-weight: bold;
        border: 2px solid {colors['score_border']};
        border-radius: 6px;
        background: transparent;
    """


def criterion_small_btn(colors, disabled=False):
    if disabled:
        return f"""
            QPushButton {{
                background: {colors['bg3']};
                color: {colors['border1']};
                border: 1px solid {colors['border1']};
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:disabled {{
                color: {colors['border1']};
            }}
        """
    return f"""
        QPushButton {{
            background: {colors['bg3']};
            color: {colors['text1']};
            border: 1px solid {colors['border2']};
            border-radius: 4px;
            font-weight: bold;
            font-size: 14px;
        }}
        QPushButton:hover {{
            background: {colors['border1']};
        }}
    """


def card_border_pos(colors):
    return f"""
        ImageCard {{
            border: 2px solid {colors['pos']};
            border-radius: 12px;
            background: {colors['bg2']};
        }}
    """


def card_border_red(colors):
    return f"""
        ImageCard {{
            border: 2px solid {colors['neg']};
            border-radius: 12px;
            background: {colors['bg2']};
        }}
    """
