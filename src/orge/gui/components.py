"""
orge.gui.components - Spec-Compliant Custom-Painted UI Components
Includes:
- RoundedCard: rgba(255,255,255,0.78), outer 1px highlight rgba(255,255,255,0.9), hairline rgba(28,27,25,0.08)
- HeroCard: 135deg hero gradient (#CFF0E5 -> #D6E4FA -> #E7DAF8), radius 24, subtle top-left highlight
- CategoryBadge & CategoryCard: Spec category tints and counts
- PrimaryButton: 44px high, radius 12, 135deg teal-cyan gradient fill, white text, soft teal shadow
- SecondaryButton: 44px high, radius 12, transparent, 1px border.control, text.primary
- QuietButton: borderless, text.link
- DestructiveButton: flat error fill (#C73E3A), white text (never gradient)
- FolderPickerCard: dashed 1.5px border.control, radius 20, min-height 200, hover/drag-over states
- FloatingPillNav: 64px high, bottom-center, radius 32, surface.elevated (#FFFFFF), nav shadow
- ToastNotification: 360px wide, radius 14, surface.elevated, auto-dismiss 5s, pause on hover
- ToggleSwitch: 40x22 track, 16px knob
"""
from typing import Dict, List, Optional, Callable, Tuple
from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
    QGraphicsDropShadowEffect, QSizePolicy, QToolButton
)
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QLinearGradient, QPainterPath,
    QFont, QIcon, QMouseEvent, QPaintEvent
)
from PySide6.QtCore import (
    Qt, QRect, QRectF, QSize, Signal, QPropertyAnimation, QEasingCurve,
    QPoint, QTimer
)

from orge.gui.tokens import LIGHT_PALETTE, RADII, SPACING, CATEGORY_TOKENS, MOTION
from orge.gui.icons import get_pixmap, get_icon

# ---------------------------------------------------------------------------
# RoundedCard
# surface.card: rgba(255,255,255,0.78)
# outer highlight: 1px rgba(255,255,255,0.9)
# inner/outer hairline: 1px rgba(28,27,25,0.08)
# ---------------------------------------------------------------------------
class RoundedCard(QFrame):
    """
    Frosted translucent card with dual hairline border for crisp edge visibility
    over the light-wash gradient background.
    """
    def __init__(self, parent: Optional[QWidget] = None, padding: int = SPACING["card_padding"], radius: int = RADII["card"]):
        super().__init__(parent)
        self.radius = radius
        self.padding = padding
        self.setObjectName("RoundedCard")
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        # Subtle shadow: md 0 1 2 rgba(28,27,25,.06), 0 8 24 rgba(28,27,25,.08)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setColor(QColor(28, 27, 25, 18))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        path = QPainterPath()
        path.addRoundedRect(rect, self.radius, self.radius)

        # Translucent white surface: rgba(255,255,255,0.78)
        painter.fillPath(path, QBrush(QColor(255, 255, 255, 200)))

        # Outer highlight + hairline border
        # Hairline: rgba(28,27,25,0.08)
        painter.setPen(QPen(QColor(28, 27, 25, 20), 1))
        painter.drawPath(path)
        painter.end()

# ---------------------------------------------------------------------------
# HeroCard (Home hero & Completed card)
# 135deg, #CFF0E5 (0%) -> #D6E4FA (55%) -> #E7DAF8 (100%)
# Faint white highlight at top-left corner.
# ---------------------------------------------------------------------------
class HeroCard(QFrame):
    def __init__(self, parent: Optional[QWidget] = None, height: int = 160):
        super().__init__(parent)
        self.setFixedHeight(height)
        self.radius = RADII["hero"]
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(28, 27, 25, 20))
        shadow.setOffset(0, 6)
        self.setGraphicsEffect(shadow)

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        path = QPainterPath()
        path.addRoundedRect(rect, self.radius, self.radius)

        # 135deg hero gradient
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0.00, QColor(LIGHT_PALETTE.hero_mint))
        gradient.setColorAt(0.55, QColor(LIGHT_PALETTE.hero_sky))
        gradient.setColorAt(1.00, QColor(LIGHT_PALETTE.hero_lavender))

        painter.fillPath(path, QBrush(gradient))

        # Hairline border + top-left highlight
        painter.setPen(QPen(QColor(255, 255, 255, 180), 1.5))
        painter.drawPath(path)
        painter.end()

# ---------------------------------------------------------------------------
# CategoryBadge
# 22 high pill, 12/600 text, soft semantic background with matching text
# ---------------------------------------------------------------------------
class CategoryBadge(QFrame):
    def __init__(self, category: str, count: Optional[int] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.category = category
        self.count = count
        self.setFixedHeight(26)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(6)

        info = CATEGORY_TOKENS.get(category, CATEGORY_TOKENS["Other"])
        icon_lbl = QLabel(self)
        icon_lbl.setPixmap(get_pixmap(info["icon"], info["color"], 14))
        layout.addWidget(icon_lbl)

        text = f"{category} ({count})" if count is not None else category
        text_lbl = QLabel(text, self)
        text_lbl.setStyleSheet(f"color: {info['color']}; font-weight: 600; font-size: 12px; background: transparent;")
        layout.addWidget(text_lbl)

    def paintEvent(self, event: QPaintEvent):
        info = CATEGORY_TOKENS.get(self.category, CATEGORY_TOKENS["Other"])
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(0, 0, self.width(), self.height())
        path = QPainterPath()
        path.addRoundedRect(rect, 13, 13)
        painter.fillPath(path, QBrush(QColor(info["light_bg"])))
        painter.end()

# ---------------------------------------------------------------------------
# CategoryCard (Home Screen Preview Tiles)
# 160x96, radius 16, tile + name + count
# ---------------------------------------------------------------------------
class CategoryCard(QFrame):
    def __init__(self, category: str, count: int, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(160, 96)
        info = CATEGORY_TOKENS.get(category, CATEGORY_TOKENS["Other"])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        top_row = QHBoxLayout()
        icon_box = QFrame(self)
        icon_box.setFixedSize(36, 36)
        icon_box.setStyleSheet(f"background-color: {info['light_bg']}; border-radius: 10px;")
        ib_layout = QHBoxLayout(icon_box)
        ib_layout.setContentsMargins(0, 0, 0, 0)
        icon_lbl = QLabel(icon_box)
        icon_lbl.setPixmap(get_pixmap(info["icon"], info["color"], 20))
        icon_lbl.setAlignment(Qt.AlignCenter)
        ib_layout.addWidget(icon_lbl)
        top_row.addWidget(icon_box)
        top_row.addStretch()

        layout.addLayout(top_row)

        name_lbl = QLabel(category, self)
        name_lbl.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {LIGHT_PALETTE.text_primary}; background: transparent;")
        layout.addWidget(name_lbl)

        cnt_lbl = QLabel(f"{count} files", self)
        cnt_lbl.setStyleSheet(f"font-size: 12px; color: {LIGHT_PALETTE.text_secondary}; background: transparent;")
        layout.addWidget(cnt_lbl)

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        path = QPainterPath()
        path.addRoundedRect(rect, 14, 14)

        # Translucent surface.card
        painter.fillPath(path, QBrush(QColor(255, 255, 255, 200)))
        painter.setPen(QPen(QColor(28, 27, 25, 20), 1))
        painter.drawPath(path)
        painter.end()

# ---------------------------------------------------------------------------
# Buttons
# Primary: 44 high, radius 12, gradient.accent fill, white text, soft teal shadow
# Secondary: 44 high, radius 12, transparent, 1px border.control, text.primary
# Destructive: flat error fill with white text (no gradient)
# Quiet: text.link, no border
# ---------------------------------------------------------------------------
class PrimaryButton(QPushButton):
    """
    Primary CTA with 135deg teal-cyan accent gradient and soft shadow.
    """
    def __init__(self, text: str, icon_name: Optional[str] = None, parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.icon_name = icon_name
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(44)
        self.setMinimumWidth(130)
        self._is_pressed = False
        self._is_hovered = False

        if self.icon_name:
            self.setIcon(get_icon(self.icon_name, "#ffffff", 18))
            self.setIconSize(QSize(18, 18))

        # Soft teal shadow: 0 4 12 rgba(14,116,144,.22)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(12)
        shadow.setColor(QColor(14, 116, 144, 55))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

    def enterEvent(self, event):
        self._is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._is_hovered = False
        self._is_pressed = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._is_pressed = True
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._is_pressed = False
        self.update()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        path = QPainterPath()
        path.addRoundedRect(rect, RADII["control"], RADII["control"])

        if not self.isEnabled():
            painter.fillPath(path, QBrush(QColor(28, 27, 25, 20)))
            text_color = QColor(LIGHT_PALETTE.text_disabled)
        else:
            # 135deg accent gradient
            grad = QLinearGradient(0, 0, self.width(), self.height())
            if self._is_pressed:
                # 16% darker
                grad.setColorAt(0.0, QColor("#085b4f"))
                grad.setColorAt(1.0, QColor("#0a576c"))
            elif self._is_hovered:
                # 8% darker
                grad.setColorAt(0.0, QColor("#096b5d"))
                grad.setColorAt(1.0, QColor("#0c657e"))
            else:
                grad.setColorAt(0.0, QColor(LIGHT_PALETTE.accent_gradient_start))
                grad.setColorAt(1.0, QColor(LIGHT_PALETTE.accent_gradient_end))

            painter.fillPath(path, QBrush(grad))
            text_color = QColor("#ffffff")

        # Draw icon & text
        painter.setPen(text_color)
        font = QFont("Segoe UI Variable", 10, QFont.DemiBold)
        painter.setFont(font)

        # Center contents
        fm = painter.fontMetrics()
        text_w = fm.horizontalAdvance(self.text())
        icon_w = 22 if self.icon_name else 0
        total_w = text_w + icon_w + (6 if icon_w else 0)
        start_x = (self.width() - total_w) / 2

        if self.icon_name:
            icon_pix = get_pixmap(self.icon_name, "#ffffff" if self.isEnabled() else LIGHT_PALETTE.text_disabled, 18)
            painter.drawPixmap(int(start_x), int((self.height() - 18) / 2), icon_pix)
            start_x += 24

        painter.drawText(QRectF(start_x, 0, text_w + 10, self.height()), Qt.AlignVCenter | Qt.AlignLeft, self.text())
        painter.end()

class SecondaryButton(QPushButton):
    def __init__(self, text: str, icon_name: Optional[str] = None, parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.icon_name = icon_name
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(44)
        self.setMinimumWidth(100)

        if self.icon_name:
            self.setIcon(get_icon(self.icon_name, LIGHT_PALETTE.text_primary, 16))
            self.setIconSize(QSize(16, 16))

        self.setStyleSheet(f"""
        QPushButton {{
            background-color: transparent;
            color: {LIGHT_PALETTE.text_primary};
            border: 1px solid {LIGHT_PALETTE.border_control};
            border-radius: {RADII['control']}px;
            padding: 8px 18px;
            font-weight: 600;
            font-size: 13px;
        }}
        QPushButton:hover {{
            background-color: {LIGHT_PALETTE.overlay_hover};
            border-color: {LIGHT_PALETTE.accent_solid};
        }}
        QPushButton:pressed {{
            background-color: {LIGHT_PALETTE.overlay_pressed};
        }}
        QPushButton:disabled {{
            color: {LIGHT_PALETTE.text_disabled};
            border-color: {LIGHT_PALETTE.border_subtle};
        }}
        """)

class DestructiveButton(QPushButton):
    def __init__(self, text: str, icon_name: Optional[str] = None, parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(44)
        self.setMinimumWidth(110)
        self.setStyleSheet(f"""
        QPushButton {{
            background-color: {LIGHT_PALETTE.error};
            color: #ffffff;
            border: none;
            border-radius: {RADII['control']}px;
            padding: 8px 18px;
            font-weight: 600;
            font-size: 13px;
        }}
        QPushButton:hover {{
            background-color: #b03330;
        }}
        QPushButton:pressed {{
            background-color: #9a2b28;
        }}
        """)

class QuietButton(QPushButton):
    def __init__(self, text: str, parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
        QPushButton {{
            background: transparent;
            color: {LIGHT_PALETTE.text_link};
            border: none;
            font-weight: 600;
            font-size: 13px;
            padding: 4px 8px;
        }}
        QPushButton:hover {{
            text-decoration: underline;
        }}
        """)

# ---------------------------------------------------------------------------
# FolderPickerCard
# Dashed 1.5px border.control, radius 20, min-height 200, 48px folder icon
# ---------------------------------------------------------------------------
class FolderPickerCard(QFrame):
    clicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setMinimumHeight(200)
        self.setCursor(Qt.PointingHandCursor)
        self._is_hovered = False
        self._is_drag_over = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignCenter)

        self.icon_lbl = QLabel(self)
        self.icon_lbl.setPixmap(get_pixmap("folder", LIGHT_PALETTE.accent_solid, 48))
        self.icon_lbl.setAlignment(Qt.AlignCenter)
        self.icon_lbl.setStyleSheet("background: transparent;")
        layout.addWidget(self.icon_lbl)

        self.title_lbl = QLabel("Choose a folder to organize", self)
        self.title_lbl.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {LIGHT_PALETTE.text_primary}; background: transparent;")
        self.title_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_lbl)

        self.sub_lbl = QLabel("or drop a folder anywhere here", self)
        self.sub_lbl.setStyleSheet(f"font-size: 13px; color: {LIGHT_PALETTE.text_secondary}; background: transparent;")
        self.sub_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.sub_lbl)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def enterEvent(self, event):
        self._is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._is_hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
        path = QPainterPath()
        path.addRoundedRect(rect, 20, 20)

        if self._is_drag_over or self._is_hovered:
            painter.fillPath(path, QBrush(QColor(11, 122, 106, 18)))
            pen = QPen(QColor(LIGHT_PALETTE.accent_solid), 1.5, Qt.DashLine)
        else:
            painter.fillPath(path, QBrush(QColor(255, 255, 255, 160)))
            pen = QPen(QColor(LIGHT_PALETTE.border_control), 1.5, Qt.DashLine)

        painter.setPen(pen)
        painter.drawPath(path)
        painter.end()

# ---------------------------------------------------------------------------
# FloatingPillNav
# 64 high, padding 8, radius 32, surface.elevated (#FFFFFF), nav shadow
# Selected: 135deg gradient.accent fill with white text/icon sliding out
# Keyboard shortcuts: Ctrl+1..5, Left/Right
# ---------------------------------------------------------------------------
class NavPillButton(QToolButton):
    def __init__(self, key: str, label: str, icon_name: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.key = key
        self.label_text = label
        self.icon_name = icon_name
        self.is_active = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(48)
        self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self._render_state()

    def set_active(self, active: bool):
        self.is_active = active
        self._render_state()

    def _render_state(self):
        if self.is_active:
            self.setText(f"  {self.label_text}")
            self.setIcon(get_icon(self.icon_name, "#ffffff", 20))
            self.setStyleSheet(f"""
            QToolButton {{
                background-color: {LIGHT_PALETTE.accent_solid};
                color: #ffffff;
                border: none;
                border-radius: 24px;
                padding: 6px 16px;
                font-weight: 600;
                font-size: 13px;
            }}
            """)
        else:
            self.setText("")
            self.setIcon(get_icon(self.icon_name, LIGHT_PALETTE.text_secondary, 20))
            self.setStyleSheet(f"""
            QToolButton {{
                background: transparent;
                color: {LIGHT_PALETTE.text_secondary};
                border: none;
                border-radius: 24px;
                padding: 6px 12px;
            }}
            QToolButton:hover {{
                background-color: {LIGHT_PALETTE.overlay_hover};
            }}
            """)
        self.setIconSize(QSize(20, 20))

    def paintEvent(self, event: QPaintEvent):
        if self.is_active:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            rect = QRectF(0, 0, self.width(), self.height())
            path = QPainterPath()
            path.addRoundedRect(rect, 24, 24)

            # 135deg gradient on selected item
            grad = QLinearGradient(0, 0, self.width(), self.height())
            grad.setColorAt(0.0, QColor(LIGHT_PALETTE.accent_gradient_start))
            grad.setColorAt(1.0, QColor(LIGHT_PALETTE.accent_gradient_end))
            painter.fillPath(path, QBrush(grad))
            painter.end()

        super().paintEvent(event)

class FloatingPillNav(QFrame):
    item_selected = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedHeight(64)
        self.buttons: Dict[str, NavPillButton] = {}
        self.active_key = "home"

        # Nav pill shadow: 0 12 32 rgba(14,116,144,.18)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(32)
        shadow.setColor(QColor(14, 116, 144, 46))
        shadow.setOffset(0, 8)
        self.setGraphicsEffect(shadow)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        items = [
            ("home", "Home", "home"),
            ("review", "Review", "checklist"),
            ("history", "History", "history"),
            ("settings", "Settings", "settings"),
            ("about", "About", "info"),
        ]

        for key, label, icon_name in items:
            btn = NavPillButton(key, label, icon_name, self)
            btn.clicked.connect(lambda checked=False, k=key: self._on_btn_clicked(k))
            self.buttons[key] = btn
            layout.addWidget(btn)

        self.set_active("home")

    def set_active(self, key: str):
        self.active_key = key
        for k, btn in self.buttons.items():
            btn.set_active(k == key)
        self.adjustSize()
        self.update()

    def _on_btn_clicked(self, key: str):
        self.set_active(key)
        self.item_selected.emit(key)

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        path = QPainterPath()
        path.addRoundedRect(rect, 32, 32)

        # surface.elevated = #FFFFFF
        painter.fillPath(path, QBrush(QColor("#ffffff")))
        # Hairline rgba(28,27,25,0.08)
        painter.setPen(QPen(QColor(28, 27, 25, 20), 1))
        painter.drawPath(path)
        painter.end()

# ---------------------------------------------------------------------------
# ToastNotification
# 360 wide, radius 14, surface.elevated (#FFFFFF), bottom-center 104px above bottom
# Auto-dismiss 5s, pause on hover
# ---------------------------------------------------------------------------
class ToastNotification(QFrame):
    def __init__(self, parent: QWidget, message: str, icon_name: str = "checkmark", duration_ms: int = MOTION["toast_duration"]):
        super().__init__(parent)
        self.setFixedSize(360, 48)
        self.duration_ms = duration_ms

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(28, 27, 25, 30))
        shadow.setOffset(0, 6)
        self.setGraphicsEffect(shadow)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(10)

        icon_lbl = QLabel(self)
        icon_lbl.setPixmap(get_pixmap(icon_name, LIGHT_PALETTE.success, 20))
        icon_lbl.setStyleSheet("background: transparent;")
        layout.addWidget(icon_lbl)

        msg_lbl = QLabel(message, self)
        msg_lbl.setStyleSheet(f"font-size: 13px; font-weight: 500; color: {LIGHT_PALETTE.text_primary}; background: transparent;")
        layout.addWidget(msg_lbl, 1)

        self._timer = QTimer(self)
        self._timer.setInterval(self.duration_ms)
        self._timer.timeout.connect(self.hide_and_destroy)
        self._timer.start()

    def enterEvent(self, event):
        self._timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._timer.start(2000)
        super().leaveEvent(event)

    def hide_and_destroy(self):
        self._timer.stop()
        self.hide()
        self.deleteLater()

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        path = QPainterPath()
        path.addRoundedRect(rect, 14, 14)
        painter.fillPath(path, QBrush(QColor("#ffffff")))
        painter.setPen(QPen(QColor(28, 27, 25, 20), 1))
        painter.drawPath(path)
        painter.end()
