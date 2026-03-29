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
    # ── Tabs ─────────────────────────────────────────────────────────────────
    'tab_bg':       '#1e1e1e',
    'tab_sel':      '#444',
    # ── Functional accents ───────────────────────────────────────────────────
    'accent':       '#2196F3',    # interactive / highlight / split handle
    'canvas':       'black',      # image viewer / fullscreen background
    # ── UI danger (close, clear, remove tab) ─────────────────────────────────
    'danger':       '#c62828',
    'danger_hover': '#eb3535',
}

from pathlib import Path as _Path
exec((_Path(__file__).parent / 'styles_base_layout.py').read_text(encoding='utf-8'))
