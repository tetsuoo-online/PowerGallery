# ============================================================================
# STYLES CONFIGURATION - Dark theme
# Variables use semantic/role-based names, not color-based names.
# Style functions are loaded from styles_base_layout.py
# ============================================================================

COLORS = {
    # ── Backgrounds ──────────────────────────────────────────────────────────
    'bg1':          '#2e2e2e',
    'bg2':          '#2b2b2b',
    'bg3':          '#333333',
    'bg4':          '#2b2b2b',    # drop zone background
    # ── Borders ──────────────────────────────────────────────────────────────
    'border1':      '#444',
    'border2':      '#555',
    # ── Foreground / Text ─────────────────────────────────────────────────────
    'text1':        'white',      # primary text
    'text2':        '#888',       # secondary / muted text
    'crit1':        '#888',       # criterion button neutral text+border
    # ── Tabs ─────────────────────────────────────────────────────────────────
    'tab_bg':       '#1e1e1e',
    'tab_sel':      '#444',
    # ── Functional accents ───────────────────────────────────────────────────
    'accent':       '#2196F3',    # interactive / highlight / split handle
    'score':        'yellow',     # score indicator text
    'score_border': '#1e1e1e',
    'canvas':       'black',      # image viewer / fullscreen background
    # ── UI danger (close, clear, remove tab — indépendant des critères) ──────
    'danger':       '#c62828',
    'danger_hover': '#eb3535',
    # ── Critère positif ──────────────────────────────────────────────────────
    'pos':          '#4CAF50',    # bordure carte + bordure/texte bouton
    'pos_bg':       '#2d5016',    # fond bouton
    'pos_hover':    '#356019',    # fond bouton hover
    # ── Critère négatif ──────────────────────────────────────────────────────
    'neg':          '#c62828',    # bordure carte + bordure/texte bouton (assez clair pour les deux)
    'neg_bg':       '#5c1a1a',    # fond bouton
    'neg_hover':    '#6b2020',    # fond bouton hover
}

from pathlib import Path as _Path
exec((_Path(__file__).parent / 'styles_base_layout.py').read_text(encoding='utf-8'))
