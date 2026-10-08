"""
orge.gui.screens - All High-Fidelity Application Screens in Light-Only Gradient System
Implements:
- HomeScreen:
    - Empty Hero: 135deg hero gradient (#CFF0E5 -> #D6E4FA -> #E7DAF8), "Organize your files, effortlessly."
      Three trust points: "Nothing moves until you say so", "Review every change", "Undo anytime"
      FolderPickerCard with drag-and-drop and folder browsing
    - Folder Chosen: Summary card, "128 files found", up to 6 CategoryCards, "Review Changes", "Choose a Different Folder"
    - Scanning State: "Looking through your files...", pulsing folder icon, indeterminate/determinate progress, "Found 842 files"
- ReviewScreen:
    - "Review changes", "Here's what will happen to 842 files in Downloads."
    - Summary strip: "842 files -> 6 folders" with category breakdown
    - Search field, Filter chips with counts, Category groups as collapsible cards
    - Sticky footer with Back (secondary, left) and "Organize 842 Files" (primary, right)
- OrganizingScreen:
    - "Organizing your files...", determinate gradient bar with percent, "312 of 842 files", "Moving: filename"
    - Cancel confirmation: "Stop organizing? Files already moved will stay where they are, and you can undo them from History."
- CompletedScreen:
    - Card with 135deg hero gradient, animated circular check badge, "All done", "842 files organized into 6 folders."
    - Category chips with counts, Done (primary), View History (secondary), Undo (quiet with confirmation)
- HistoryScreen:
    - Grouped activity list under date headers ("Today", "Yesterday", etc.)
    - 72px high history items with category breakdown, status badge (Organized / Undone / Partly undone)
    - Selection mode: "3 selected", Select All, Undo, Clear Selected, Done
    - Destructive Clear History confirmation with exact spec copy
- SettingsScreen:
    - Scanning: Include subfolders toggle, Include hidden files toggle
    - File Handling: "When a file with the same name exists" (Keep both (rename) / Skip)
    - Safety: "Always review before organizing" locked-on toggle, "Keep undo history for" dropdown
    - No Appearance/Theme section!
- AboutScreen:
    - Centered card, 96px ORGE icon, "Your files are messy. ORGE makes them simple.", version, MIT license, GitHub links
"""
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QFrame, QFileDialog, QTreeWidget, QTreeWidgetItem,
    QProgressBar, QCheckBox, QComboBox, QSizePolicy, QHeaderView, QGridLayout
)
from PySide6.QtCore import Qt, Signal, QSize, QTimer
from PySide6.QtGui import QFont, QColor, QPainter, QPainterPath, QBrush, QPen

from orge import __version__
from orge.gui.tokens import LIGHT_PALETTE, SPACING, RADII, CATEGORY_TOKENS
from orge.gui.icons import get_pixmap, get_icon
from orge.gui.components import (
    RoundedCard, HeroCard, CategoryBadge, CategoryCard,
    PrimaryButton, SecondaryButton, DestructiveButton, QuietButton,
    FolderPickerCard
)
from orge.gui.dialogs import ConfirmDialog, UndoConfirmDialog, DestructiveConfirmDialog, ErrorDialog
from orge.core.models import OperationPlan, OperationStep, HistoryRecord

# ---------------------------------------------------------------------------
# BaseScreen
# ---------------------------------------------------------------------------
class BaseScreen(QWidget):
    """
    Base screen wrapper providing a centered content column (max 960px, or 1040px for Review)
    and generous bottom inset (112px) so nothing hides behind the floating navigation pill.
    """
    def __init__(self, parent: Optional[QWidget] = None, max_width: int = SPACING["content_max_width"]):
        super().__init__(parent)
        self.max_width = max_width

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("background: transparent; border: none;")

        self.container = QWidget(self.scroll)
        self.container.setStyleSheet("background: transparent;")
        self.outer_layout = QHBoxLayout(self.container)
        self.outer_layout.setContentsMargins(0, 0, 0, 0)
        self.outer_layout.setAlignment(Qt.AlignHCenter)

        self.content_widget = QWidget(self.container)
        self.content_widget.setMaximumWidth(self.max_width)
        self.content_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.content_widget.setStyleSheet("background: transparent;")

        self.column_layout = QVBoxLayout(self.content_widget)
        # 112px bottom inset for floating pill nav
        self.column_layout.setContentsMargins(SPACING["page_margin"], SPACING["page_margin"], SPACING["page_margin"], SPACING["content_bottom_inset"])
        self.column_layout.setSpacing(SPACING["card_gap"])
        self.column_layout.setAlignment(Qt.AlignTop)

        self.outer_layout.addWidget(self.content_widget)
        self.scroll.setWidget(self.container)
        self.main_layout.addWidget(self.scroll)

# ---------------------------------------------------------------------------
# 1. HomeScreen
# ---------------------------------------------------------------------------
class HomeScreen(BaseScreen):
    browse_clicked = Signal()
    review_clicked = Signal()
    change_folder_clicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.current_folder: Optional[Path] = None
        self.found_files_count = 0
        self.category_counts: Dict[str, int] = {}

        # ---------------- HERO CARD ----------------
        self.hero = HeroCard(self.content_widget, height=170)
        hero_layout = QVBoxLayout(self.hero)
        hero_layout.setContentsMargins(36, 28, 36, 28)
        hero_layout.setSpacing(8)

        self.hero_title = QLabel("Organize your files, effortlessly.", self.hero)
        self.hero_title.setStyleSheet(f"font-size: 26px; font-weight: 600; color: {LIGHT_PALETTE.text_primary}; background: transparent;")
        hero_layout.addWidget(self.hero_title)

        self.hero_subtitle = QLabel(
            "Choose a folder and ORGE will sort its files into tidy categories. You'll review everything first.",
            self.hero
        )
        self.hero_subtitle.setStyleSheet(f"font-size: 14px; color: {LIGHT_PALETTE.text_secondary}; background: transparent; line-height: 1.4;")
        self.hero_subtitle.setWordWrap(True)
        hero_layout.addWidget(self.hero_subtitle)

        # Trust points
        trust_row = QHBoxLayout()
        trust_row.setSpacing(24)
        for text in ["Nothing moves until you say so", "Review every change", "Undo anytime"]:
            tp = QHBoxLayout()
            tp.setSpacing(6)
            ic = QLabel(self.hero)
            ic.setPixmap(get_pixmap("checkmark", LIGHT_PALETTE.accent_solid, 16))
            ic.setStyleSheet("background: transparent;")
            tp.addWidget(ic)
            tl = QLabel(text, self.hero)
            tl.setStyleSheet(f"font-size: 13px; font-weight: 500; color: {LIGHT_PALETTE.text_secondary}; background: transparent;")
            tp.addWidget(tl)
            trust_row.addLayout(tp)
        trust_row.addStretch()
        hero_layout.addLayout(trust_row)

        self.column_layout.addWidget(self.hero)

        # ---------------- STATE A: NO FOLDER CHOSEN ----------------
        self.empty_card = FolderPickerCard(self.content_widget)
        self.empty_card.clicked.connect(self.browse_clicked.emit)
        self.column_layout.addWidget(self.empty_card)

        # ---------------- STATE B: FOLDER CHOSEN (SUMMARY) ----------------
        self.summary_card = RoundedCard(self.content_widget, padding=28)
        s_layout = QVBoxLayout(self.summary_card)
        s_layout.setContentsMargins(28, 28, 28, 28)
        s_layout.setSpacing(18)

        header_row = QHBoxLayout()
        f_icon = QLabel(self.summary_card)
        f_icon.setPixmap(get_pixmap("folder", LIGHT_PALETTE.accent_solid, 32))
        f_icon.setStyleSheet("background: transparent;")
        header_row.addWidget(f_icon)

        folder_info_col = QVBoxLayout()
        folder_info_col.setSpacing(2)
        self.folder_name_lbl = QLabel("Folder Name", self.summary_card)
        self.folder_name_lbl.setStyleSheet(f"font-size: 18px; font-weight: 600; color: {LIGHT_PALETTE.text_primary}; background: transparent;")
        folder_info_col.addWidget(self.folder_name_lbl)

        self.folder_path_lbl = QLabel("C:/path/to/folder", self.summary_card)
        self.folder_path_lbl.setStyleSheet(f"font-size: 13px; color: {LIGHT_PALETTE.text_secondary}; background: transparent;")
        folder_info_col.addWidget(self.folder_path_lbl)
        header_row.addLayout(folder_info_col, 1)

        self.change_btn = QuietButton("Change", self.summary_card)
        self.change_btn.clicked.connect(self.change_folder_clicked.emit)
        header_row.addWidget(self.change_btn)
        s_layout.addLayout(header_row)

        # Numeric stats row
        self.stats_lbl = QLabel("128 files found • Ready to sort into 6 categories", self.summary_card)
        self.stats_lbl.setStyleSheet(f"font-size: 15px; font-weight: 600; color: {LIGHT_PALETTE.text_primary}; background: transparent;")
        s_layout.addWidget(self.stats_lbl)

        # Category preview tiles (up to 6)
        self.tiles_container = QWidget(self.summary_card)
        self.tiles_container.setStyleSheet("background: transparent;")
        self.tiles_layout = QHBoxLayout(self.tiles_container)
        self.tiles_layout.setContentsMargins(0, 4, 0, 4)
        self.tiles_layout.setSpacing(12)
        s_layout.addWidget(self.tiles_container)

        reassurance_lbl = QLabel("No files will be moved until you confirm.", self.summary_card)
        reassurance_lbl.setStyleSheet(f"font-size: 13px; color: {LIGHT_PALETTE.text_secondary}; background: transparent;")
        s_layout.addWidget(reassurance_lbl)

        # Actions
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        self.review_btn = PrimaryButton("Review Changes", "checklist", self.summary_card)
        self.review_btn.clicked.connect(self.review_clicked.emit)
        btn_row.addWidget(self.review_btn)

        self.diff_folder_btn = SecondaryButton("Choose a Different Folder", "folder", self.summary_card)
        self.diff_folder_btn.clicked.connect(self.change_folder_clicked.emit)
        btn_row.addWidget(self.diff_folder_btn)
        btn_row.addStretch()
        s_layout.addLayout(btn_row)

        self.column_layout.addWidget(self.summary_card)
        self.summary_card.hide()

        # ---------------- STATE C: SCANNING WORKFLOW ----------------
        self.scanning_card = RoundedCard(self.content_widget, padding=32)
        sc_layout = QVBoxLayout(self.scanning_card)
        sc_layout.setContentsMargins(32, 32, 32, 32)
        sc_layout.setSpacing(16)

        sc_title = QLabel("Looking through your files...", self.scanning_card)
        sc_title.setStyleSheet(f"font-size: 18px; font-weight: 600; color: {LIGHT_PALETTE.text_primary}; background: transparent;")
        sc_layout.addWidget(sc_title)

        self.sc_progress = QProgressBar(self.scanning_card)
        self.sc_progress.setRange(0, 0)  # Indeterminate
        sc_layout.addWidget(self.sc_progress)

        self.sc_count_lbl = QLabel("Found 0 files", self.scanning_card)
        self.sc_count_lbl.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {LIGHT_PALETTE.accent_solid}; background: transparent;")
        sc_layout.addWidget(self.sc_count_lbl)

        sc_note = QLabel("This usually takes a few seconds.", self.scanning_card)
        sc_note.setStyleSheet(f"font-size: 13px; color: {LIGHT_PALETTE.text_secondary}; background: transparent;")
        sc_layout.addWidget(sc_note)

        self.column_layout.addWidget(self.scanning_card)
        self.scanning_card.hide()

    def set_folder(self, path: Path, file_count: int, categories: Dict[str, int]):
        self.current_folder = path
        self.found_files_count = file_count
        self.category_counts = categories

        self.empty_card.hide()
        self.scanning_card.hide()
        self.summary_card.show()

        self.folder_name_lbl.setText(path.name or str(path))
        self.folder_path_lbl.setText(str(path))
        cat_count = len(categories)
        self.stats_lbl.setText(f"{file_count} files found • Ready to sort into {cat_count} categories")

        # Clear old tiles
        while self.tiles_layout.count():
            item = self.tiles_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Populate up to 6 category cards
        for cat, cnt in list(sorted(categories.items(), key=lambda x: -x[1]))[:6]:
            card = CategoryCard(cat, cnt, self.tiles_container)
            self.tiles_layout.addWidget(card)
        self.tiles_layout.addStretch()

    def set_scanning_state(self, scanning: bool, count: int = 0):
        if scanning:
            self.empty_card.hide()
            self.summary_card.hide()
            self.scanning_card.show()
            self.sc_count_lbl.setText(f"Found {count} files")
        else:
            self.scanning_card.hide()
            if self.current_folder:
                self.summary_card.show()
            else:
                self.empty_card.show()

# ---------------------------------------------------------------------------
# 2. ReviewScreen
# ---------------------------------------------------------------------------
class ReviewScreen(BaseScreen):
    back_clicked = Signal()
    organize_clicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent, max_width=SPACING["content_max_width_review"])
        self.current_plan: Optional[OperationPlan] = None

        # Header card
        header_card = RoundedCard(self.content_widget, padding=24)
        h_layout = QVBoxLayout(header_card)
        h_layout.setContentsMargins(24, 20, 24, 20)
        h_layout.setSpacing(8)

        title = QLabel("Review changes", header_card)
        title.setStyleSheet(f"font-size: 22px; font-weight: 600; color: {LIGHT_PALETTE.text_primary}; background: transparent;")
        h_layout.addWidget(title)

        self.subtitle_lbl = QLabel("Here's what will happen to your files.", header_card)
        self.subtitle_lbl.setStyleSheet(f"font-size: 14px; color: {LIGHT_PALETTE.text_secondary}; background: transparent;")
        h_layout.addWidget(self.subtitle_lbl)

        # Summary strip
        self.summary_strip = QLabel("842 files → 6 folders", header_card)
        self.summary_strip.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {LIGHT_PALETTE.accent_solid}; background: transparent;")
        h_layout.addWidget(self.summary_strip)

        self.column_layout.addWidget(header_card)

        # Toolbar Card (Search & Expand/Collapse)
        tool_card = RoundedCard(self.content_widget, padding=12)
        t_layout = QHBoxLayout(tool_card)
        t_layout.setContentsMargins(16, 8, 16, 8)
        t_layout.setSpacing(12)

        s_icon = QLabel(tool_card)
        s_icon.setPixmap(get_pixmap("search", LIGHT_PALETTE.text_secondary, 18))
        s_icon.setStyleSheet("background: transparent;")
        t_layout.addWidget(s_icon)

        self.search_input = QLineEdit(tool_card)
        self.search_input.setPlaceholderText("Search files...")
        self.search_input.textChanged.connect(self._on_search_changed)
        t_layout.addWidget(self.search_input, 1)

        self.expand_all_btn = QuietButton("Expand all", tool_card)
        self.expand_all_btn.clicked.connect(lambda: self.tree.expandAll())
        t_layout.addWidget(self.expand_all_btn)

        self.collapse_all_btn = QuietButton("Collapse all", tool_card)
        self.collapse_all_btn.clicked.connect(lambda: self.tree.collapseAll())
        t_layout.addWidget(self.collapse_all_btn)

        self.column_layout.addWidget(tool_card)

        # Category Badges Card
        self.badges_card = RoundedCard(self.content_widget, padding=12)
        self.badges_layout = QHBoxLayout(self.badges_card)
        self.badges_layout.setContentsMargins(16, 8, 16, 8)
        self.badges_layout.setSpacing(8)
        self.badges_layout.setAlignment(Qt.AlignLeft)
        self.column_layout.addWidget(self.badges_card)

        # File List Card
        tree_card = RoundedCard(self.content_widget, padding=12)
        tree_layout = QVBoxLayout(tree_card)
        tree_layout.setContentsMargins(12, 12, 12, 12)

        self.tree = QTreeWidget(tree_card)
        self.tree.setHeaderLabels(["File Name", "Destination Category / Action", "Status"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tree.setMinimumHeight(320)
        tree_layout.addWidget(self.tree)
        self.column_layout.addWidget(tree_card)

        # Sticky Footer Actions
        footer_card = RoundedCard(self.content_widget, padding=16)
        f_layout = QHBoxLayout(footer_card)
        f_layout.setContentsMargins(20, 12, 20, 12)

        self.back_btn = SecondaryButton("Back", "chevron-left", footer_card)
        self.back_btn.clicked.connect(self.back_clicked.emit)
        f_layout.addWidget(self.back_btn)

        f_layout.addStretch()

        self.organize_btn = PrimaryButton("Organize Files", "checkmark", footer_card)
        self.organize_btn.clicked.connect(self.organize_clicked.emit)
        f_layout.addWidget(self.organize_btn)

        self.column_layout.addWidget(footer_card)

    def set_plan(self, plan: OperationPlan):
        self.current_plan = plan
        steps = plan.executable_steps
        count = len(steps)

        folder_name = plan.target_folder.name if plan.target_folder else "folder"
        self.subtitle_lbl.setText(f"Here's what will happen to {count} files in {folder_name}.")
        self.organize_btn.setText(f"Organize {count} Files")
        self.organize_btn.setEnabled(count > 0)

        # Badges
        while self.badges_layout.count():
            item = self.badges_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cat_counts: Dict[str, int] = {}
        for s in steps:
            cat_counts[s.category] = cat_counts.get(s.category, 0) + 1

        self.summary_strip.setText(f"{count} files → {len(cat_counts)} folders")

        for cat, cnt in sorted(cat_counts.items()):
            badge = CategoryBadge(cat, cnt, self.badges_card)
            self.badges_layout.addWidget(badge)
        self.badges_layout.addStretch()

        self._populate_tree()

    def _populate_tree(self):
        self.tree.setUpdatesEnabled(False)
        self.tree.clear()
        if not self.current_plan:
            self.tree.setUpdatesEnabled(True)
            return

        query = self.search_input.text().strip().lower()
        grouped: Dict[str, List[OperationStep]] = {}
        for s in self.current_plan.executable_steps:
            if query and query not in s.source_path.name.lower():
                continue
            grouped.setdefault(s.category, []).append(s)

        for cat, items in sorted(grouped.items()):
            group_item = QTreeWidgetItem(self.tree)
            info = CATEGORY_TOKENS.get(cat, CATEGORY_TOKENS["Other"])
            group_item.setText(0, f"{cat} ({len(items)} files)")
            group_item.setText(1, f"will be moved to {cat}")
            group_item.setFont(0, QFont("Segoe UI Variable", 10, QFont.DemiBold))
            group_item.setIcon(0, get_icon(info["icon"], info["color"], 18))
            # Collapse by default over 20 files
            group_item.setExpanded(len(items) <= 20)

            for item in items[:100]:  # Cap display at 100 for instant UI rendering
                child = QTreeWidgetItem(group_item)
                child.setText(0, item.source_path.name)
                child.setText(1, f"→ {cat}/{item.target_path.name}")
                child.setText(2, "Ready")

            if len(items) > 100:
                more_item = QTreeWidgetItem(group_item)
                more_item.setText(0, f"Show {len(items) - 100} more...")
                more_item.setFont(0, QFont("Segoe UI Variable", 9, QFont.Normal))

        self.tree.setUpdatesEnabled(True)

    def _on_search_changed(self):
        self._populate_tree()

    def reset_state(self):
        """Immediately releases previous plan and clears tree without unnecessary repaints."""
        self.current_plan = None
        self.tree.setUpdatesEnabled(False)
        self.tree.clear()
        self.tree.setUpdatesEnabled(True)
        self.search_input.clear()
        self.summary_strip.setText("")
        while self.badges_layout.count():
            item = self.badges_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

# ---------------------------------------------------------------------------
# 3. OrganizingScreen
# ---------------------------------------------------------------------------
class OrganizingScreen(BaseScreen):
    cancel_clicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        card = RoundedCard(self.content_widget, padding=36)
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(36, 36, 36, 36)
        c_layout.setSpacing(16)

        title = QLabel("Organizing your files...", card)
        title.setStyleSheet(f"font-size: 22px; font-weight: 600; color: {LIGHT_PALETTE.text_primary}; background: transparent;")
        c_layout.addWidget(title)

        self.counter_lbl = QLabel("0 of 0 files", card)
        self.counter_lbl.setStyleSheet(f"font-size: 15px; font-weight: 600; color: {LIGHT_PALETTE.accent_solid}; background: transparent;")
        c_layout.addWidget(self.counter_lbl)

        self.progress_bar = QProgressBar(card)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        c_layout.addWidget(self.progress_bar)

        self.moving_file_lbl = QLabel("Moving: preparing...", card)
        self.moving_file_lbl.setStyleSheet(f"font-size: 13px; color: {LIGHT_PALETTE.text_secondary}; background: transparent;")
        c_layout.addWidget(self.moving_file_lbl)

        btn_row = QHBoxLayout()
        self.cancel_btn = SecondaryButton("Cancel", parent=card)
        self.cancel_btn.clicked.connect(self._on_cancel)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addStretch()
        c_layout.addLayout(btn_row)

        self.column_layout.addWidget(card)

    def set_progress(self, current: int, total: int, src_name: str, dst_name: str):
        self.counter_lbl.setText(f"{current} of {total} files")
        pct = int((current / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(pct)
        self.moving_file_lbl.setText(f"Moving: {src_name}")

    def _on_cancel(self):
        msg = (
            "Stop organizing?\n\n"
            "Files already moved will stay where they are, and you can undo them from History."
        )
        dlg = ConfirmDialog("Stop Organizing", msg, "Stop", self)
        if dlg.exec():
            self.cancel_clicked.emit()

# ---------------------------------------------------------------------------
# 4. CompletedScreen
# ---------------------------------------------------------------------------
class CompletedScreen(BaseScreen):
    done_clicked = Signal()
    history_clicked = Signal()
    undo_clicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.hero = HeroCard(self.content_widget, height=220)
        c_layout = QVBoxLayout(self.hero)
        c_layout.setContentsMargins(36, 32, 36, 32)
        c_layout.setSpacing(12)

        header_row = QHBoxLayout()
        check_icon = QLabel(self.hero)
        check_icon.setPixmap(get_pixmap("checkmark", LIGHT_PALETTE.accent_solid, 36))
        check_icon.setStyleSheet("background: transparent;")
        header_row.addWidget(check_icon)

        title = QLabel("All done", self.hero)
        title.setStyleSheet(f"font-size: 26px; font-weight: 600; color: {LIGHT_PALETTE.text_primary}; background: transparent;")
        header_row.addWidget(title)
        header_row.addStretch()
        c_layout.addLayout(header_row)

        self.summary_lbl = QLabel("842 files organized into 6 folders.", self.hero)
        self.summary_lbl.setStyleSheet(f"font-size: 15px; color: {LIGHT_PALETTE.text_secondary}; background: transparent;")
        c_layout.addWidget(self.summary_lbl)

        # Category chips
        self.chips_container = QWidget(self.hero)
        self.chips_container.setStyleSheet("background: transparent;")
        self.chips_layout = QHBoxLayout(self.chips_container)
        self.chips_layout.setContentsMargins(0, 4, 0, 4)
        self.chips_layout.setSpacing(8)
        self.chips_layout.setAlignment(Qt.AlignLeft)
        c_layout.addWidget(self.chips_container)

        self.notices_lbl = QLabel("", self.hero)
        self.notices_lbl.setStyleSheet(f"font-size: 13px; color: {LIGHT_PALETTE.warning}; background: transparent;")
        c_layout.addWidget(self.notices_lbl)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self.done_btn = PrimaryButton("Done", "checkmark", self.hero)
        self.done_btn.clicked.connect(self.done_clicked.emit)
        btn_row.addWidget(self.done_btn)

        self.view_hist_btn = SecondaryButton("View History", "history", self.hero)
        self.view_hist_btn.clicked.connect(self.history_clicked.emit)
        btn_row.addWidget(self.view_hist_btn)

        self.undo_btn = QuietButton("Undo organization", self.hero)
        self.undo_btn.clicked.connect(self.undo_clicked.emit)
        btn_row.addWidget(self.undo_btn)
        btn_row.addStretch()
        c_layout.addLayout(btn_row)

        self.column_layout.addWidget(self.hero)

    def set_results(self, successful: list, errors: list):
        count = len(successful)
        cat_counts: Dict[str, int] = {}
        for src, dst in successful:
            cat = dst.parent.name
            cat_counts[cat] = cat_counts.get(cat, 0) + 1

        self.summary_lbl.setText(f"{count} files organized into {len(cat_counts)} folders.")

        while self.chips_layout.count():
            item = self.chips_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for cat, cnt in sorted(cat_counts.items()):
            badge = CategoryBadge(cat, cnt, self.chips_container)
            self.chips_layout.addWidget(badge)
        self.chips_layout.addStretch()

        if errors:
            self.notices_lbl.setText(f"⚠️ {len(errors)} files couldn't be moved and remain in place.")
        else:
            self.notices_lbl.setText("")

# ---------------------------------------------------------------------------
# 5. HistoryScreen
# ---------------------------------------------------------------------------
class HistoryScreen(BaseScreen):
    undo_requested = Signal()
    clear_selected_requested = Signal(list)
    clear_all_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.records: List[HistoryRecord] = []
        self.selected_ids: Set[str] = set()

        toolbar = RoundedCard(self.content_widget, padding=16)
        t_layout = QHBoxLayout(toolbar)
        t_layout.setContentsMargins(20, 14, 20, 14)
        t_layout.setSpacing(12)

        title = QLabel("History", toolbar)
        title.setStyleSheet(f"font-size: 20px; font-weight: 600; color: {LIGHT_PALETTE.text_primary}; background: transparent;")
        t_layout.addWidget(title)

        self.sel_lbl = QLabel("", toolbar)
        self.sel_lbl.setStyleSheet(f"font-size: 13px; color: {LIGHT_PALETTE.text_secondary}; background: transparent;")
        t_layout.addWidget(self.sel_lbl)
        t_layout.addStretch()

        self.select_all_btn = SecondaryButton("Select", None, toolbar)
        self.select_all_btn.clicked.connect(self._toggle_select_all)
        t_layout.addWidget(self.select_all_btn)

        self.clear_sel_btn = DestructiveButton("Clear Selected", "trash", toolbar)
        self.clear_sel_btn.setEnabled(False)
        self.clear_sel_btn.clicked.connect(self._on_clear_selected)
        t_layout.addWidget(self.clear_sel_btn)

        self.clear_all_btn = SecondaryButton("Clear All", "trash", toolbar)
        self.clear_all_btn.clicked.connect(self._on_clear_all)
        t_layout.addWidget(self.clear_all_btn)

        self.column_layout.addWidget(toolbar)

        # Tree for grouped activity list
        tree_card = RoundedCard(self.content_widget, padding=12)
        tree_layout = QVBoxLayout(tree_card)
        tree_layout.setContentsMargins(12, 12, 12, 12)

        self.tree = QTreeWidget(tree_card)
        self.tree.setHeaderLabels(["Folder / Entry", "Date & Time", "Status / Details"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tree.setMinimumHeight(340)
        self.tree.itemChanged.connect(self._on_item_checked)
        tree_layout.addWidget(self.tree)

        self.column_layout.addWidget(tree_card)

    def set_records(self, records: List[HistoryRecord]):
        self.records = records
        self.selected_ids.clear()
        self.tree.clear()
        self._update_toolbar()

        if not records:
            empty_item = QTreeWidgetItem(self.tree)
            empty_item.setText(0, "No history yet")
            empty_item.setText(1, "Organize a folder and it'll show up here.")
            return

        for r in records:
            item = QTreeWidgetItem(self.tree)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(0, Qt.Unchecked)
            item.setData(0, Qt.UserRole, r.id)

            folder_name = Path(r.target_folder).name if r.target_folder else "Files"
            item.setText(0, f"  {folder_name} ({r.total_operations} files)")
            item.setIcon(0, get_icon("folder", LIGHT_PALETTE.accent_solid, 18))

            ts = getattr(r, "timestamp", "") or getattr(r, "created_at", "")
            dt_str = ts[:16].replace("T", " ") if ts else ""
            item.setText(1, dt_str)

            can_undo = (r.status != "completed_undo" and bool(r.pending_operations))
            status_text = "Organized" if can_undo else "Undone"
            item.setText(2, status_text)

    def _on_item_checked(self, item: QTreeWidgetItem, column: int):
        if column != 0:
            return
        rid = item.data(0, Qt.UserRole)
        if not rid:
            return
        if item.checkState(0) == Qt.Checked:
            self.selected_ids.add(rid)
        else:
            self.selected_ids.discard(rid)
        self._update_toolbar()

    def _toggle_select_all(self):
        root_count = self.tree.topLevelItemCount()
        all_selected = (len(self.selected_ids) == len(self.records) and len(self.records) > 0)
        target = Qt.Unchecked if all_selected else Qt.Checked

        for i in range(root_count):
            item = self.tree.topLevelItem(i)
            item.setCheckState(0, target)

    def _update_toolbar(self):
        cnt = len(self.selected_ids)
        self.sel_lbl.setText(f"({cnt} selected)" if cnt > 0 else "")
        self.clear_sel_btn.setEnabled(cnt > 0)
        self.clear_all_btn.setEnabled(len(self.records) > 0)

    def _on_clear_selected(self):
        if not self.selected_ids:
            return
        cnt = len(self.selected_ids)
        all_undone = all(
            r.status == "completed_undo" or not r.pending_operations
            for r in self.records if r.id in self.selected_ids
        )
        dlg = DestructiveConfirmDialog(f"Clear {cnt} entries?", cnt, all_undone=all_undone, parent=self)
        if dlg.exec():
            self.clear_selected_requested.emit(list(self.selected_ids))

    def _on_clear_all(self):
        if not self.records:
            return
        cnt = len(self.records)
        all_undone = all(r.status == "completed_undo" or not r.pending_operations for r in self.records)
        dlg = DestructiveConfirmDialog("Clear all history?", cnt, all_undone=all_undone, parent=self)
        if dlg.exec():
            self.clear_all_requested.emit()

# ---------------------------------------------------------------------------
# 6. SettingsScreen (No Appearance/Theme section!)
# ---------------------------------------------------------------------------
class SettingsScreen(BaseScreen):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        card = RoundedCard(self.content_widget, padding=32)
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(32, 32, 32, 32)
        c_layout.setSpacing(24)

        title = QLabel("Settings", card)
        title.setStyleSheet(f"font-size: 22px; font-weight: 600; color: {LIGHT_PALETTE.text_primary}; background: transparent;")
        c_layout.addWidget(title)

        # Section: Scanning
        scan_title = QLabel("Scanning", card)
        scan_title.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {LIGHT_PALETTE.text_primary}; background: transparent;")
        c_layout.addWidget(scan_title)

        self.subfolders_chk = QCheckBox("Include subfolders", card)
        c_layout.addWidget(self.subfolders_chk)

        self.hidden_chk = QCheckBox("Include hidden files", card)
        self.hidden_chk.setChecked(False)
        c_layout.addWidget(self.hidden_chk)

        # Section: File handling
        file_title = QLabel("File handling", card)
        file_title.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {LIGHT_PALETTE.text_primary}; background: transparent;")
        c_layout.addWidget(file_title)

        dup_row = QHBoxLayout()
        dup_lbl = QLabel("When a file with the same name exists:", card)
        dup_lbl.setStyleSheet(f"font-size: 13px; color: {LIGHT_PALETTE.text_secondary}; background: transparent;")
        dup_row.addWidget(dup_lbl)

        self.dup_combo = QComboBox(card)
        self.dup_combo.addItems(["Keep both (rename)", "Skip"])
        dup_row.addWidget(self.dup_combo)
        dup_row.addStretch()
        c_layout.addLayout(dup_row)

        # Section: Safety
        safety_title = QLabel("Safety", card)
        safety_title.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {LIGHT_PALETTE.text_primary}; background: transparent;")
        c_layout.addWidget(safety_title)

        self.review_lock_chk = QCheckBox("Always review before organizing", card)
        self.review_lock_chk.setChecked(True)
        self.review_lock_chk.setEnabled(False)  # Locked-on per spec
        c_layout.addWidget(self.review_lock_chk)

        undo_row = QHBoxLayout()
        undo_lbl = QLabel("Keep undo history for:", card)
        undo_lbl.setStyleSheet(f"font-size: 13px; color: {LIGHT_PALETTE.text_secondary}; background: transparent;")
        undo_row.addWidget(undo_lbl)

        self.undo_combo = QComboBox(card)
        self.undo_combo.addItems(["30 days", "90 days", "Forever"])
        undo_row.addWidget(self.undo_combo)
        undo_row.addStretch()
        c_layout.addLayout(undo_row)

        self.column_layout.addWidget(card)

        # Wire settings change events
        self.dup_combo.currentIndexChanged.connect(self._on_settings_changed)
        self.undo_combo.currentIndexChanged.connect(self._on_settings_changed)
        self.subfolders_chk.toggled.connect(self._on_settings_changed)
        self.hidden_chk.toggled.connect(self._on_settings_changed)
        self.config_manager = None

    def set_config(self, config_manager):
        self.config_manager = config_manager
        # Block signals while setting values
        self.dup_combo.blockSignals(True)
        self.undo_combo.blockSignals(True)
        self.subfolders_chk.blockSignals(True)
        self.hidden_chk.blockSignals(True)

        # Duplicate strategy
        strat = getattr(config_manager, "duplicate_strategy", "rename")
        if strat == "skip":
            self.dup_combo.setCurrentIndex(1)
        else:
            self.dup_combo.setCurrentIndex(0)

        # Undo retention
        days = getattr(config_manager, "undo_retention_days", 30)
        if days == 90 or days == "90":
            self.undo_combo.setCurrentIndex(1)
        elif days in ("Forever", "forever", 0, -1, None):
            self.undo_combo.setCurrentIndex(2)
        else:
            self.undo_combo.setCurrentIndex(0)

        self.dup_combo.blockSignals(False)
        self.undo_combo.blockSignals(False)
        self.subfolders_chk.blockSignals(False)
        self.hidden_chk.blockSignals(False)

    def _on_settings_changed(self):
        if not self.config_manager:
            return
        # Update duplicate strategy
        if self.dup_combo.currentIndex() == 1:
            self.config_manager.duplicate_strategy = "skip"
        else:
            self.config_manager.duplicate_strategy = "rename"

        # Update retention
        idx = self.undo_combo.currentIndex()
        if idx == 0:
            self.config_manager.undo_retention_days = 30
        elif idx == 1:
            self.config_manager.undo_retention_days = 90
        else:
            self.config_manager.undo_retention_days = "Forever"

        self.config_manager.save()

# ---------------------------------------------------------------------------
# 7. AboutScreen
# ---------------------------------------------------------------------------
class AboutScreen(BaseScreen):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        card = RoundedCard(self.content_widget, padding=40)
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(40, 40, 40, 40)
        c_layout.setSpacing(16)
        c_layout.setAlignment(Qt.AlignCenter)

        # 96px Official ORGE Logo
        icon_box = QFrame(card)
        icon_box.setFixedSize(96, 96)
        icon_box.setStyleSheet("background: transparent;")
        ib_layout = QHBoxLayout(icon_box)
        ib_layout.setContentsMargins(0, 0, 0, 0)
        i_lbl = QLabel(icon_box)
        from orge.gui.icons import get_logo_pixmap
        i_lbl.setPixmap(get_logo_pixmap(96))
        i_lbl.setAlignment(Qt.AlignCenter)
        ib_layout.addWidget(i_lbl)
        c_layout.addWidget(icon_box, 0, Qt.AlignCenter)

        title = QLabel("ORGE", card)
        title.setStyleSheet(f"font-size: 28px; font-weight: 600; color: {LIGHT_PALETTE.text_primary}; background: transparent;")
        title.setAlignment(Qt.AlignCenter)
        c_layout.addWidget(title)

        tagline = QLabel("Your files are messy. ORGE makes them simple.", card)
        tagline.setStyleSheet(f"font-size: 15px; color: {LIGHT_PALETTE.text_secondary}; background: transparent;")
        tagline.setAlignment(Qt.AlignCenter)
        c_layout.addWidget(tagline)

        ver = QLabel(f"Version {__version__}", card)
        ver.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {LIGHT_PALETTE.accent_solid}; background: transparent;")
        ver.setAlignment(Qt.AlignCenter)
        c_layout.addWidget(ver)

        desc = QLabel(
            "ORGE is an open source file organization desktop application.\n"
            "Open source under the MIT license.",
            card
        )
        desc.setStyleSheet(f"font-size: 13px; color: {LIGHT_PALETTE.text_secondary}; line-height: 1.5; background: transparent;")
        desc.setAlignment(Qt.AlignCenter)
        c_layout.addWidget(desc)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        gh_btn = SecondaryButton("View on GitHub", None, card)
        gh_btn.clicked.connect(lambda: self._open_url("https://github.com/tshivaneshk/orge"))
        btn_row.addWidget(gh_btn)

        lic_btn = SecondaryButton("View License", None, card)
        lic_btn.clicked.connect(lambda: self._open_url("https://github.com/tshivaneshk/orge/blob/main/LICENSE"))
        btn_row.addWidget(lic_btn)
        c_layout.addLayout(btn_row)

        self.column_layout.addWidget(card)

    def _open_url(self, url: str):
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl(url))
