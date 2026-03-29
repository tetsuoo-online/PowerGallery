# ============================================================================
# STYLES CONFIGURATION - Light theme
# Variables use semantic/role-based names, not color-based names.
# Style functions are loaded from styles_base_layout.py
# ============================================================================

COLORS = {
    # ── Backgrounds ───────────────────────────────────────────────────────────
    'bg1':          '#ffffff',
    'bg2':          '#2b2b2b',
    'bg3':          '#3a3a3a',
    'bg4':          '#bababa',    # drop zone background
    # ── Borders ───────────────────────────────────────────────────────────────
    'border1':      '#666666',
    'border2':      '#888888',
    # ── Foreground / Text ─────────────────────────────────────────────────────
    'text1':        '#ffffff',    # primary text (on dark widgets)
    'text2':        '#888888',    # secondary / muted text
    # ── Tabs ──────────────────────────────────────────────────────────────────
    'tab_bg':       '#cccccc',
    'tab_sel':      '#cccccc',
    # ── Functional accents ────────────────────────────────────────────────────
    'accent':       '#2196F3',    # interactive / highlight / split handle
    'canvas':       'black',      # image viewer / fullscreen background
    # ── UI danger (close, clear, remove tab) ──────────────────────────────────
    'danger':       '#c62828',
    'danger_hover': '#eb3535',
}

from pathlib import Path as _Path
exec((_Path(__file__).parent / 'styles_base_layout.py').read_text(encoding='utf-8'))
