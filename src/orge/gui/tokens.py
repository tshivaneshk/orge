"""
orge.gui.tokens - Design Tokens for Light-Only Gradient-Themed ORGE
Spec-compliant typography, spacing, radii, motion, shadows, and exact light/gradient palette.
No hardcoded colors outside of this module.
"""
from dataclasses import dataclass
from typing import Dict, Any

# ---------------------------------------------------------------------------
# Typography Tokens
# Segoe UI Variable (Display/Text), fallback Segoe UI.
# Minimum text size: 12px.
# ---------------------------------------------------------------------------
FONT_FAMILY = "Segoe UI Variable, Segoe UI, system-ui, -apple-system, sans-serif"
FONT_FAMILY_MONO = "Cascadia Code, Consolas, monospace"

# (size_px, weight, line_height_px)
TYPOGRAPHY = {
    "display": (40, 600, 48),       # -1% tracking
    "page_title": (28, 600, 36),
    "section": (18, 600, 26),
    "body": (14, 400, 22),
    "body_strong": (14, 600, 22),
    "secondary": (13, 400, 20),
    "caption": (12, 400, 16),
    "button": (14, 600, 20),
    "numeric_stat": (32, 600, 40),  # Tabular figures
}

# ---------------------------------------------------------------------------
# Spacing & Layout Tokens (px)
# Scale: 4, 8, 12, 16, 24, 32, 48, 64
# ---------------------------------------------------------------------------
SPACING = {
    "4": 4,
    "8": 8,
    "12": 12,
    "16": 16,
    "24": 24,
    "32": 32,
    "48": 48,
    "64": 64,
    "page_margin": 32,
    "page_margin_compact": 24,
    "content_max_width": 960,
    "content_max_width_review": 1040,
    "content_bottom_inset": 112,
    "card_padding": 24,
    "hero_padding": 40,
    "section_gap": 32,
    "card_gap": 16,
    "min_window_width": 960,
    "min_window_height": 600,
    "default_window_width": 1280,
    "default_window_height": 720,
}

# ---------------------------------------------------------------------------
# Border Radii (px)
# sm 8, md 10, control 12, card 16, hero/dialog 24, pill 999
# ---------------------------------------------------------------------------
RADII = {
    "sm": 8,
    "md": 10,
    "control": 12,
    "card": 16,
    "hero": 24,
    "dialog": 24,
    "pill": 999,
}

# ---------------------------------------------------------------------------
# Motion Tokens (ms, cubic-bezier(0.2, 0, 0, 1))
# ---------------------------------------------------------------------------
MOTION = {
    "press": 100,
    "button_hover": 120,
    "card_hover": 120,
    "selection_slide": 150,
    "progress_ease": 150,
    "page_nav": 200,
    "nav_select": 200,
    "dialog_scale": 200,
    "toast_slide": 200,
    "folder_morph": 200,
    "check_pulse": 300,
    "check_stroke": 400,
    "hero_art_settle": 600,
    "toast_duration": 5000,
}

# ---------------------------------------------------------------------------
# Category Tints & Glyphs
# Images: #F6E3EC / #B23A74
# Documents: #E1EAF7 / #2F5FA8
# PDFs: #F8E1DE / #B8402F
# Audio: #EAE2F7 / #6A44B0
# Video: #F8EAD6 / #A8620F
# Compressed: #E4E8D6 / #5F7022
# Other: #E6E5E0 / #5F5D57
# ---------------------------------------------------------------------------
CATEGORY_TOKENS = {
    "Images": {"color": "#B23A74", "light_bg": "#F6E3EC", "icon": "image"},
    "Documents": {"color": "#2F5FA8", "light_bg": "#E1EAF7", "icon": "document-text"},
    "PDFs": {"color": "#B8402F", "light_bg": "#F8E1DE", "icon": "document-pdf"},
    "Audio": {"color": "#6A44B0", "light_bg": "#EAE2F7", "icon": "music-note"},
    "Video": {"color": "#A8620F", "light_bg": "#F8EAD6", "icon": "video"},
    "Compressed": {"color": "#5F7022", "light_bg": "#E4E8D6", "icon": "archive"},
    "Other": {"color": "#5F5D57", "light_bg": "#E6E5E0", "icon": "document"},
    "Python": {"color": "#2F5FA8", "light_bg": "#E1EAF7", "icon": "document"},
    "Installers": {"color": "#5F7022", "light_bg": "#E4E8D6", "icon": "archive"},
    "WebApps": {"color": "#2F5FA8", "light_bg": "#E1EAF7", "icon": "document"},
    "Misc": {"color": "#5F5D57", "light_bg": "#E6E5E0", "icon": "document"},
}

# ---------------------------------------------------------------------------
# Light-Only Color Tokens
# Spec exact values
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Palette:
    # Text
    text_primary: str = "#1C1B19"
    text_secondary: str = "#4F5855"
    text_disabled: str = "#98A09C"
    text_on_accent: str = "#FFFFFF"
    text_link: str = "#0B6E78"

    # Surfaces
    surface_card: str = "rgba(255, 255, 255, 0.78)"
    surface_card_outer_border: str = "rgba(255, 255, 255, 0.90)"
    surface_elevated: str = "#FFFFFF"
    bg_inset: str = "rgba(28, 27, 25, 0.05)"
    row_hover: str = "rgba(28, 27, 25, 0.04)"

    # Borders
    border_subtle: str = "rgba(28, 27, 25, 0.08)"
    border_control: str = "#8F9894"
    focus_ring: str = "#0B7A6A"

    # Accent
    accent_solid: str = "#0B7A6A"
    accent_soft: str = "rgba(11, 122, 106, 0.10)"
    accent_soft_strong: str = "rgba(11, 122, 106, 0.16)"
    accent_secondary: str = "#C9822B"

    # Accent Gradient (135deg)
    accent_gradient_start: str = "#0B7A6A"
    accent_gradient_end: str = "#0E7490"

    # App Background Gradient stops (135deg)
    bg_mint: str = "#E6F6F0"      # 0%
    bg_sky: str = "#E9F0FC"       # 55%
    bg_lavender: str = "#F1EAFB"  # 100%

    # Hero & Completed Gradient stops (135deg)
    hero_mint: str = "#CFF0E5"      # 0%
    hero_sky: str = "#D6E4FA"       # 55%
    hero_lavender: str = "#E7DAF8"  # 100%

    # Semantic
    success: str = "#1F8A4C"
    success_soft: str = "rgba(31, 138, 76, 0.12)"
    warning: str = "#A8690F"
    warning_soft: str = "rgba(201, 130, 43, 0.16)"
    error: str = "#C73E3A"
    error_soft: str = "rgba(199, 62, 58, 0.12)"

    # State Overlays
    overlay_hover: str = "rgba(28, 27, 25, 0.05)"
    overlay_pressed: str = "rgba(28, 27, 25, 0.10)"
    opacity_disabled: float = 0.40

LIGHT_PALETTE = Palette()

# Backwards compatibility alias
DARK_PALETTE = LIGHT_PALETTE
