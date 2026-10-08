"""
orge.gui.dialogs - Spec-Compliant Modern Desktop Dialogs
Width 440, radius 24, surface.elevated (#FFFFFF), shadow lg, scrim rgba(28,27,25,.35).
Exact spec copy and behaviors:
- Confirmation dialog: Info icon, accent-soft tile, gradient primary button
- Destructive dialog (Clear History, Clear All): Warning icon, error-soft tile, flat error primary, Cancel is default focus
- Undo dialog: Arrow-undo icon, gradient primary button (not destructive)
- Error / Warning dialogs: Human language, zero stack traces
"""
from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QFrame, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QSize, QRectF
from PySide6.QtGui import QColor, QPainter, QPainterPath, QBrush, QPen

from orge.gui.tokens import LIGHT_PALETTE, RADII, SPACING
from orge.gui.icons import get_pixmap
from orge.gui.components import PrimaryButton, SecondaryButton, DestructiveButton

class ModernDialogBase(QDialog):
    """
    Dialog with width 440, radius 24, surface.elevated (#FFFFFF), shadow lg.
    """
    def __init__(self, title: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedWidth(440)
        self.setStyleSheet("background: #ffffff;")

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(32)
        shadow.setColor(QColor(28, 27, 25, 45))
        shadow.setOffset(0, 12)
        self.setGraphicsEffect(shadow)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        path = QPainterPath()
        path.addRoundedRect(rect, RADII["dialog"], RADII["dialog"])
        painter.fillPath(path, QBrush(QColor("#ffffff")))
        painter.setPen(QPen(QColor(28, 27, 25, 20), 1))
        painter.drawPath(path)
        painter.end()

class ConfirmDialog(ModernDialogBase):
    def __init__(self, title: str, message: str, confirm_label: str = "Continue", parent: Optional[QWidget] = None):
        super().__init__(title, parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(18)

        # Header with 40px icon tile
        header_row = QHBoxLayout()
        icon_box = QFrame(self)
        icon_box.setFixedSize(40, 40)
        icon_box.setStyleSheet(f"background-color: {LIGHT_PALETTE.accent_soft}; border-radius: 12px;")
        ib_layout = QHBoxLayout(icon_box)
        ib_layout.setContentsMargins(0, 0, 0, 0)
        i_lbl = QLabel(icon_box)
        i_lbl.setPixmap(get_pixmap("info", LIGHT_PALETTE.accent_solid, 22))
        i_lbl.setAlignment(Qt.AlignCenter)
        ib_layout.addWidget(i_lbl)
        header_row.addWidget(icon_box)

        title_lbl = QLabel(title, self)
        title_lbl.setStyleSheet(f"font-size: 18px; font-weight: 600; color: {LIGHT_PALETTE.text_primary};")
        header_row.addWidget(title_lbl, 1)
        layout.addLayout(header_row)

        msg_lbl = QLabel(message, self)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet(f"font-size: 14px; color: {LIGHT_PALETTE.text_secondary}; line-height: 1.5;")
        layout.addWidget(msg_lbl)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = SecondaryButton("Cancel", parent=self)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        confirm_btn = PrimaryButton(confirm_label, "checkmark", parent=self)
        confirm_btn.clicked.connect(self.accept)
        confirm_btn.setDefault(True)
        btn_row.addWidget(confirm_btn)

        layout.addLayout(btn_row)

class UndoConfirmDialog(ModernDialogBase):
    """
    Undo confirmation dialog with arrow-undo icon and gradient primary button.
    Exact spec copy: 'Undo this organization?'
    """
    def __init__(self, folder_name: str, count: int, parent: Optional[QWidget] = None):
        super().__init__("Undo this organization?", parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(18)

        header_row = QHBoxLayout()
        icon_box = QFrame(self)
        icon_box.setFixedSize(40, 40)
        icon_box.setStyleSheet(f"background-color: {LIGHT_PALETTE.accent_soft}; border-radius: 12px;")
        ib_layout = QHBoxLayout(icon_box)
        ib_layout.setContentsMargins(0, 0, 0, 0)
        i_lbl = QLabel(icon_box)
        i_lbl.setPixmap(get_pixmap("arrow-undo", LIGHT_PALETTE.accent_solid, 22))
        i_lbl.setAlignment(Qt.AlignCenter)
        ib_layout.addWidget(i_lbl)
        header_row.addWidget(icon_box)

        title_lbl = QLabel("Undo this organization?", self)
        title_lbl.setStyleSheet(f"font-size: 18px; font-weight: 600; color: {LIGHT_PALETTE.text_primary};")
        header_row.addWidget(title_lbl, 1)
        layout.addLayout(header_row)

        body = (
            f"ORGE will move {count} files from {folder_name} back to where they were before. "
            "Folders ORGE created will be removed if they end up empty."
        )
        msg_lbl = QLabel(body, self)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet(f"font-size: 14px; color: {LIGHT_PALETTE.text_secondary}; line-height: 1.5;")
        layout.addWidget(msg_lbl)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = SecondaryButton("Cancel", parent=self)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        undo_btn = PrimaryButton("Undo Organization", "arrow-undo", parent=self)
        undo_btn.clicked.connect(self.accept)
        undo_btn.setDefault(True)
        btn_row.addWidget(undo_btn)

        layout.addLayout(btn_row)

class DestructiveConfirmDialog(ModernDialogBase):
    """
    Exact spec Clear History dialog:
    Cancel is the default focus.
    Flat error fill for primary button.
    """
    def __init__(self, title: str, count: int, all_undone: bool = False, parent: Optional[QWidget] = None):
        super().__init__(title, parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(18)

        header_row = QHBoxLayout()
        icon_box = QFrame(self)
        icon_box.setFixedSize(40, 40)
        icon_box.setStyleSheet(f"background-color: {LIGHT_PALETTE.error_soft}; border-radius: 12px;")
        ib_layout = QHBoxLayout(icon_box)
        ib_layout.setContentsMargins(0, 0, 0, 0)
        i_lbl = QLabel(icon_box)
        i_lbl.setPixmap(get_pixmap("warning", LIGHT_PALETTE.error, 22))
        i_lbl.setAlignment(Qt.AlignCenter)
        ib_layout.addWidget(i_lbl)
        header_row.addWidget(icon_box)

        title_lbl = QLabel(title, self)
        title_lbl.setStyleSheet(f"font-size: 18px; font-weight: 600; color: {LIGHT_PALETTE.text_primary};")
        header_row.addWidget(title_lbl, 1)
        layout.addLayout(header_row)

        if all_undone:
            body = (
                f"This removes these {count} entries from History. "
                "Your files will stay exactly where they are now. Clearing history doesn't move anything back."
            )
        else:
            body = (
                f"This removes these {count} entries from History. "
                "You won't be able to undo these organizations afterward. "
                "Your files will stay exactly where they are now. Clearing history doesn't move anything back."
            )

        msg_lbl = QLabel(body, self)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet(f"font-size: 14px; color: {LIGHT_PALETTE.text_secondary}; line-height: 1.5;")
        layout.addWidget(msg_lbl)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        # Cancel is DEFAULT focus to protect users
        cancel_btn = SecondaryButton("Cancel", parent=self)
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setDefault(True)
        cancel_btn.setFocus()
        btn_row.addWidget(cancel_btn)

        clear_btn = DestructiveButton("Clear History", "trash", parent=self)
        clear_btn.clicked.connect(self.accept)
        btn_row.addWidget(clear_btn)

        layout.addLayout(btn_row)

class ErrorDialog(ModernDialogBase):
    """
    Human-friendly error dialog. No technical stack traces.
    """
    def __init__(self, title: str, summary: str, details: Optional[str] = None, parent: Optional[QWidget] = None):
        super().__init__(title, parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(18)

        header_row = QHBoxLayout()
        icon_box = QFrame(self)
        icon_box.setFixedSize(40, 40)
        icon_box.setStyleSheet(f"background-color: {LIGHT_PALETTE.error_soft}; border-radius: 12px;")
        ib_layout = QHBoxLayout(icon_box)
        ib_layout.setContentsMargins(0, 0, 0, 0)
        i_lbl = QLabel(icon_box)
        i_lbl.setPixmap(get_pixmap("dismiss-circle", LIGHT_PALETTE.error, 22))
        i_lbl.setAlignment(Qt.AlignCenter)
        ib_layout.addWidget(i_lbl)
        header_row.addWidget(icon_box)

        title_lbl = QLabel(title, self)
        title_lbl.setStyleSheet(f"font-size: 18px; font-weight: 600; color: {LIGHT_PALETTE.text_primary};")
        header_row.addWidget(title_lbl, 1)
        layout.addLayout(header_row)

        sum_lbl = QLabel(summary, self)
        sum_lbl.setWordWrap(True)
        sum_lbl.setStyleSheet(f"font-size: 14px; color: {LIGHT_PALETTE.text_secondary}; line-height: 1.5;")
        layout.addWidget(sum_lbl)

        if details:
            details_box = QTextEdit(self)
            details_box.setReadOnly(True)
            details_box.setText(details)
            details_box.setFixedHeight(90)
            details_box.setStyleSheet(f"""
            QTextEdit {{
                background-color: {LIGHT_PALETTE.bg_inset};
                color: {LIGHT_PALETTE.text_secondary};
                border: 1px solid {LIGHT_PALETTE.border_subtle};
                border-radius: 8px;
                font-size: 12px;
                padding: 6px;
            }}
            """)
            layout.addWidget(details_box)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        ok_btn = SecondaryButton("OK", parent=self)
        ok_btn.clicked.connect(self.accept)
        ok_btn.setDefault(True)
        btn_row.addWidget(ok_btn)

        layout.addLayout(btn_row)
