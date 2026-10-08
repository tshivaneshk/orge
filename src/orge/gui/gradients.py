"""
orge.gui.gradients - Cached Gradient Rendering and Background Painting
Strict Gradient Rules:
Allowed ONLY on:
1. The app background (135deg, mint #E6F6F0 -> sky #E9F0FC -> lavender #F1EAFB, plus soft radial washes)
2. The Home hero and Completed card (135deg, #CFF0E5 -> #D6E4FA -> #E7DAF8)
3. Primary button fills (135deg, #0B7A6A -> #0E7490)
4. Selected nav item (135deg, #0B7A6A -> #0E7490)
5. Progress bar fills (135deg, #0B7A6A -> #0E7490)
6. Completion check badge

Forbidden on: text, dense list rows, file rows, badges, dialogs, toasts, dropdown menus,
tooltips, input fields, destructive buttons, icons.
Always 135deg. Pre-rendered/cached per resize.
"""
from typing import Optional
from PySide6.QtGui import (
    QPainter, QColor, QLinearGradient, QRadialGradient, QPixmap, QBrush, QPaintEvent
)
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtWidgets import QWidget

from orge.gui.tokens import LIGHT_PALETTE

class BackgroundGradientWidget(QWidget):
    """
    Renders the signature ORGE 135deg light-wash gradient with two soft radial tints.
    Pre-renders onto an internal QPixmap cache to eliminate repaint overhead during scrolling.
    """
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._cached_pixmap: Optional[QPixmap] = None
        self._cached_size = (0, 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0 or (w, h) == self._cached_size:
            return

        self._cached_size = (w, h)
        pix = QPixmap(w, h)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing)

        # 135deg linear gradient from top-left to bottom-right
        # Angle 135 deg: (0, 0) to (w, h)
        lg = QLinearGradient(0, 0, w, h)
        lg.setColorAt(0.00, QColor(LIGHT_PALETTE.bg_mint))      # #E6F6F0 at 0%
        lg.setColorAt(0.55, QColor(LIGHT_PALETTE.bg_sky))       # #E9F0FC at 55%
        lg.setColorAt(1.00, QColor(LIGHT_PALETTE.bg_lavender))  # #F1EAFB at 100%

        painter.fillRect(0, 0, w, h, QBrush(lg))

        # Soft radial tint 1: mint at top-left, max 35% opacity
        r1_radius = max(w, h) * 0.6
        rg1 = QRadialGradient(QPointF(0, 0), r1_radius)
        rg1.setColorAt(0.0, QColor(190, 240, 224, 75))
        rg1.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.fillRect(0, 0, w, h, QBrush(rg1))

        # Soft radial tint 2: lavender at bottom-right, max 35% opacity
        r2_radius = max(w, h) * 0.6
        rg2 = QRadialGradient(QPointF(w, h), r2_radius)
        rg2.setColorAt(0.0, QColor(231, 218, 248, 75))
        rg2.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.fillRect(0, 0, w, h, QBrush(rg2))

        painter.end()
        self._cached_pixmap = pix

    def paintEvent(self, event: QPaintEvent):
        if self._cached_pixmap and not self._cached_pixmap.isNull():
            painter = QPainter(self)
            painter.drawPixmap(0, 0, self._cached_pixmap)
            painter.end()
        else:
            # Fallback
            super().paintEvent(event)
