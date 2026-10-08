"""
orge.gui.theme - Light-Only Theme Manager & QSS Stylesheet Compiler
Enforces the gradient-themed light design system.
Safely ignores any legacy dark or system theme configuration values.
"""
from typing import Callable, List, Optional
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from orge.gui.tokens import Palette, LIGHT_PALETTE

class ThemeManager(QObject):
    """
    Light-only theme manager.
    Maintains compatibility with UI listeners via theme_changed signal.
    """
    theme_changed = Signal(Palette)

    def __init__(self, initial_mode: str = "Light"):
        super().__init__()
        # Always light, regardless of initial_mode or legacy config
        self._mode = "Light"
        self._current_palette = LIGHT_PALETTE

    @property
    def mode(self) -> str:
        return "Light"

    @property
    def palette(self) -> Palette:
        return self._current_palette

    @property
    def is_dark(self) -> bool:
        return False

    def set_mode(self, mode: str):
        # Ignore attempts to switch to Dark/System; always remain Light
        pass

    def build_stylesheet(self, p: Palette) -> str:
        """
        Compiles the global QSS for the Light-Only Gradient theme.
        Ensures proper contrast, readable inputs, subtle hairlines, and accessible focus rings.
        """
        return f"""
        * {{
            font-family: 'Segoe UI Variable', 'Segoe UI', system-ui, -apple-system, sans-serif;
            font-size: 13px;
        }}
        QMainWindow, QDialog {{
            background: transparent;
            color: {p.text_primary};
        }}
        QLabel {{
            color: {p.text_primary};
        }}
        QScrollArea {{
            background: transparent;
            border: none;
        }}
        QScrollBar:vertical {{
            border: none;
            background: transparent;
            width: 8px;
            margin: 0px;
        }}
        QScrollBar::handle:vertical {{
            background: rgba(28, 27, 25, 0.15);
            min-height: 24px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: rgba(28, 27, 25, 0.25);
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QLineEdit {{
            background-color: {p.bg_inset};
            color: {p.text_primary};
            border: 1px solid {p.border_subtle};
            border-radius: 12px;
            padding: 8px 14px;
            font-size: 13px;
            selection-background-color: {p.accent_solid};
            selection-color: #ffffff;
        }}
        QLineEdit:focus {{
            border: 2px solid {p.focus_ring};
            background-color: #ffffff;
        }}
        QComboBox {{
            background-color: {p.bg_inset};
            color: {p.text_primary};
            border: 1px solid {p.border_subtle};
            border-radius: 10px;
            padding: 8px 14px;
            font-size: 13px;
            min-height: 22px;
        }}
        QComboBox:hover {{
            border: 1px solid {p.accent_solid};
        }}
        QComboBox:focus {{
            border: 2px solid {p.focus_ring};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 24px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {p.surface_elevated};
            color: {p.text_primary};
            border: 1px solid {p.border_subtle};
            selection-background-color: {p.accent_soft};
            selection-color: {p.accent_solid};
            border-radius: 10px;
            outline: none;
            padding: 4px;
        }}
        QComboBox QAbstractItemView::item {{
            color: {p.text_primary};
            background-color: transparent;
            padding: 6px 12px;
            border-radius: 6px;
            min-height: 20px;
        }}
        QComboBox QAbstractItemView::item:hover {{
            background-color: {p.row_hover};
            color: {p.text_primary};
        }}
        QComboBox QAbstractItemView::item:selected {{
            background-color: {p.accent_soft};
            color: {p.accent_solid};
            font-weight: 600;
        }}
        QCheckBox {{
            spacing: 10px;
            font-size: 13px;
            color: {p.text_primary};
        }}
        QCheckBox::indicator {{
            width: 20px;
            height: 20px;
            border: 1.5px solid {p.border_control};
            border-radius: 6px;
            background-color: #ffffff;
        }}
        QCheckBox::indicator:hover {{
            border-color: {p.accent_solid};
        }}
        QCheckBox::indicator:checked {{
            background-color: {p.accent_solid};
            border-color: {p.accent_solid};
        }}
        QCheckBox::indicator:disabled {{
            border-color: {p.text_disabled};
            background-color: {p.bg_inset};
        }}
        QRadioButton {{
            spacing: 8px;
            font-size: 13px;
            color: {p.text_primary};
        }}
        QRadioButton::indicator {{
            width: 18px;
            height: 18px;
            border: 1.5px solid {p.border_control};
            border-radius: 9px;
            background-color: #ffffff;
        }}
        QRadioButton::indicator:checked {{
            background-color: {p.accent_solid};
            border: 4px solid #ffffff;
        }}
        QSpinBox {{
            background-color: {p.bg_inset};
            color: {p.text_primary};
            border: 1px solid {p.border_subtle};
            border-radius: 8px;
            padding: 6px 10px;
        }}
        QProgressBar {{
            background-color: rgba(28, 27, 25, 0.08);
            border-radius: 999px;
            text-align: center;
            border: none;
            height: 8px;
        }}
        QProgressBar::chunk {{
            background-color: {p.accent_solid};
            border-radius: 999px;
        }}
        QTreeWidget {{
            background-color: transparent;
            color: {p.text_primary};
            border: none;
            outline: none;
        }}
        QTreeWidget::item {{
            padding: 6px 4px;
            color: {p.text_primary};
            border-radius: 6px;
        }}
        QTreeWidget::item:hover {{
            background-color: {p.row_hover};
        }}
        QTreeWidget::item:selected {{
            background-color: {p.accent_soft};
            color: {p.accent_solid};
        }}
        QHeaderView::section {{
            background-color: transparent;
            color: {p.text_secondary};
            border: none;
            font-weight: 600;
            padding: 6px 8px;
        }}
        """

# Global singleton theme manager
theme_mgr = ThemeManager()
