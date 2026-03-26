# ============================================================================
# STYLES CONFIGURATION - Dark theme
# Variables use semantic/role-based names, not color-based names.
# Style functions are loaded from styles_base_layout.py
# ============================================================================

COLORS = {
    # ── Backgrounds ─────────────────────────
    'bg1':     '#2e2e2e',
    'bg2':     '#2b2b2b',
    'bg3':     '#333333',
    'bg4':     '#2b2b2b',    # drop zone background
    # ── Borders ───────────────────────────────────────────────────────────────
    'border1': '#444',
    'border2': '#555',
    # ── Foreground / Text ─────────────────────────────────────────────────────
    'text1':   'white',      # primary text
    'text2':   '#888',       # secondary / muted text
    'crit1':   '#888',       # tertiary text
    'tab_bg':  '#1e1e1e',    # grid bg color
    # ── Tabs ─────────────────────────────────────────────────────────────────
    'tab_sel': '#444',
    # ── Functional accents ────────────────────────────────────────────────────
    'accent':       '#2196F3',  # interactive / highlight / split handle
    'score':        'yellow',   # score indicator
    'score_border': '#1e1e1e',
    'canvas':       'black',    # image viewer / fullscreen background
    # ── Positive state ────────────────────────────────────────────────────────
    'pos':          '#4CAF50',
    'pos_bg':       '#2d5016',
    'pos_hover':    '#356019',
    # ── Negative state ────────────────────────────────────────────────────────
    'neg':          '#c62828',
    'neg_hover':    '#eb3535',
    'neg_bg':       '#5c1a1a',
    'neg_bg_hover': '#6b2020',
}

from pathlib import Path as _Path
exec((_Path(__file__).parent / 'styles_base_layout.py').read_text(encoding='utf-8'))
