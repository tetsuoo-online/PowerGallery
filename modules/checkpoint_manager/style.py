# ============================================================================
# CHECKPOINT MANAGER - Module styles
# COLORS_EXTRA : additional color keys, merged on top of the base theme.
# Style functions : only used by checkpoint_manager.
# ============================================================================

COLORS_EXTRA = {
    # ── Score widget ──────────────────────────────────────────────────────────
    'score':        'yellow',
    'score_border': '#1e1e1e',
    # ── Criterion button neutral ──────────────────────────────────────────────
    'crit1':        '#888',       # text + border, neutral state
    # ── Positive criterion ────────────────────────────────────────────────────
    'pos':          '#4CAF50',    # card border + button border/text
    'pos_bg':       '#2d5016',    # button background
    'pos_hover':    '#356019',    # button background hover
    # ── Negative criterion ────────────────────────────────────────────────────
    'neg':          '#c62828',    # card border + button border/text
    'neg_bg':       '#5c1a1a',    # button background
    'neg_hover':    '#6b2020',    # button background hover
    # ── Checkpoint name label ─────────────────────────────────────────────────
    'ckpt_label':   'white',      # independent from text1
}


def get_merged_colors(base_colors):
    """Return base COLORS merged with COLORS_EXTRA (module keys win)."""
    merged = dict(base_colors)
    merged.update(COLORS_EXTRA)
    return merged


# ── Style functions ───────────────────────────────────────────────────────────
# Each function receives the merged COLORS dict as argument.

def checkpoint_label(colors):
    return (f"font-size: 14px; font-weight: bold; "
            f"color: {colors['ckpt_label']}; background: transparent;")

def score_label(colors):
    return f"""
        color: {colors['score']};
        font-size: 20px;
        font-weight: bold;
        border: 2px solid {colors['score_border']};
        border-radius: 6px;
        background: transparent;
    """

def criterion_button_neutral(colors):
    return f"""
        QPushButton {{
            background: {colors['bg3']};
            color: {colors['crit1']};
            border: 1px solid {colors['crit1']};
            border-radius: 6px;
        }}
        QPushButton:hover {{
            background: {colors['border1']};
        }}
    """

def criterion_button_green(colors):
    return f"""
        QPushButton {{
            background: {colors['pos_bg']};
            color: {colors['pos']};
            border: 1px solid {colors['pos']};
            border-radius: 6px;
        }}
        QPushButton:hover {{
            background: {colors['pos_hover']};
        }}
    """

def criterion_button_red(colors):
    return f"""
        QPushButton {{
            background: {colors['neg_bg']};
            color: {colors['neg']};
            border: 1px solid {colors['neg']};
            border-radius: 6px;
        }}
        QPushButton:hover {{
            background: {colors['neg_hover']};
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
