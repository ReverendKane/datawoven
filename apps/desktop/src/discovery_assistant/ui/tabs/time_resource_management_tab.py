"""
Time & Resource Management Tab - Revised implementation with consistent styling
Captures time allocation, workload patterns, and resource constraints for ROI calculations.
"""

import json
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from PySide6 import QtWidgets, QtCore, QtGui
from discovery_assistant.baselogger import logging
from discovery_assistant.ui.widgets.info import InfoSection
from discovery_assistant.ui.widgets.screenshot_tool import ScreenshotTool
from discovery_assistant.storage import DatabaseSession, TimeAllocation, TimeResourceManagement
from discovery_assistant.storage import get_files_dir, FileManager

_LOGGER = logging.getLogger("DISCOVERY.ui.tabs.time_resource_management_tab")

# Priority levels for time allocations
PRIORITY_LEVELS = ["High", "Medium", "Low"]

# Info HTML content for the section
TIME_RESOURCE_INFO = """
<p><strong>Purpose:</strong> Track how you spend your time and identify resource constraints that impact productivity.</p>
<p>This information helps quantify automation opportunities and calculate potential ROI by understanding:</p>
<ul>
<li>Where your time is currently allocated</li>
<li>Which activities consume the most resources</li>
<li>What constraints limit your productivity</li>
<li>When workloads are most intense</li>
</ul>
<p>Use this section to document both regular activities and time spent waiting for information, approvals, or other resources.</p>
"""

@dataclass
class AttachmentMetadata:
    """Metadata for an attached file"""
    file_path: Path
    title: str = ""
    notes: str = ""
    is_screenshot: bool = False

    @property
    def display_name(self) -> str:
        """Return title if available, otherwise filename"""
        return self.title if self.title.strip() else self.file_path.name

@dataclass
class TimeAllocationItem:
    """Data class for time allocation entries"""
    activity_name: str
    hours_per_week: int
    priority_level: str
    notes: str = ""
    attachments: List[AttachmentMetadata] = field(default_factory=list)
    pain_point_id: Optional[int] = None
    process_id: Optional[int] = None


# Reusable style helpers
def _force_dark_text(widget: QtWidgets.QWidget,
                     text_hex: str = "#000000",
                     placeholder_hex: str = "#94A3B8") -> None:
    """Apply dark text + softer placeholder to inputs."""
    if isinstance(widget, (QtWidgets.QLineEdit, QtWidgets.QTextEdit, QtWidgets.QPlainTextEdit)):
        base = (
            f"color:{text_hex};"
            "background:#FFFFFF;"
            "border:1px solid #E2E8F0;"
            "border-radius:8px;"
            "padding:8px 10px;"
            "selection-background-color:#0F172A;"
        )
        focus = "border:1.5px solid #0F172A;"
        cls = widget.metaObject().className()
        widget.setStyleSheet(f"{cls}{{{base}}}{cls}:focus{{{focus}}}")

        pal = widget.palette()
        if hasattr(QtGui.QPalette, "PlaceholderText"):
            pal.setColor(QtGui.QPalette.PlaceholderText, QtGui.QColor(placeholder_hex))
        widget.setPalette(pal)


class _StackedLabelForm(QtWidgets.QVBoxLayout):
    """Label-above-field layout."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(12)

    def add_row(self, label: str, field: QtWidgets.QWidget) -> None:
        row = QtWidgets.QVBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        lbl = QtWidgets.QLabel(label)
        lbl.setStyleSheet("font-size:13px; color:#334155; background:transparent; font-weight:500;")
        row.addWidget(lbl)
        row.addWidget(field)
        self.addLayout(row)


class FlowLayout(QtWidgets.QLayout):
    """Simple flow layout for chips."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None, margin: int = 0, hspacing: int = 6,
                 vspacing: int = 6):
        super().__init__(parent)
        self._items: List[QtWidgets.QLayoutItem] = []
        self.setContentsMargins(margin, margin, margin, margin)
        self._hspace = hspacing
        self._vspace = vspacing

    def addItem(self, item: QtWidgets.QLayoutItem) -> None:
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, i: int) -> Optional[QtWidgets.QLayoutItem]:
        return self._items[i] if 0 <= i < len(self._items) else None

    def takeAt(self, i: int) -> Optional[QtWidgets.QLayoutItem]:
        return self._items.pop(i) if 0 <= i < len(self._items) else None

    def expandingDirections(self) -> QtCore.Qt.Orientations:
        return QtCore.Qt.Orientations(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, w: int) -> int:
        return self._do_layout(QtCore.QRect(0, 0, w, 0), True)

    def setGeometry(self, rect: QtCore.QRect) -> None:
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self) -> QtCore.QSize:
        return self.minimumSize()

    def minimumSize(self) -> QtCore.QSize:
        s = QtCore.QSize()
        for i in self._items:
            s = s.expandedTo(i.minimumSize())
        m = self.contentsMargins()
        s += QtCore.QSize(m.left() + m.right(), m.top() + m.bottom())
        return s

    def _do_layout(self, rect: QtCore.QRect, test_only: bool) -> int:
        x, y = rect.x(), rect.y()
        line_height = 0
        for item in self._items:
            w, h = item.sizeHint().width(), item.sizeHint().height()
            if x + w > rect.right() and line_height > 0:
                x = rect.x()
                y += line_height + self._vspace
                line_height = 0
            if not test_only:
                item.setGeometry(QtCore.QRect(QtCore.QPoint(x, y), item.sizeHint()))
            x += w + self._hspace
            line_height = max(line_height, h)
        return y + line_height - rect.y()


class AttachmentChip(QtWidgets.QFrame):
    """Chip widget for displaying attachments"""
    removed = QtCore.Signal("PyObject")  # emits AttachmentMetadata
    edit_requested = QtCore.Signal("PyObject")  # emits AttachmentMetadata

    def __init__(self, attachment: AttachmentMetadata, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.attachment = attachment
        self.setObjectName("AttachmentChip")

        # Different styling for screenshots vs documents
        if attachment.is_screenshot:
            bg_color = "#0891B2"  # Darker blue background
            border_color = "#0891B2"
            text_color = "#FFFFFF"  # White text on dark blue
        else:
            bg_color = "#DBE0E4"  # Light gray background
            border_color = "#E5E7EB"
            text_color = "#1F2937"  # Dark text on light background

        self.setStyleSheet(f"""
            QFrame#AttachmentChip {{
                background: {bg_color};
                border:1px solid {border_color};
                border-radius:4px;
            }}
            QLabel {{ 
                background:transparent; 
                color: {text_color};
            }}
            QToolButton {{ background:transparent; border:none; }}
            QToolButton:hover {{ background:#E5E7EB; border-radius:12px; }}
        """)

        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(8, 4, 6, 4)
        lay.setSpacing(6)

        # Icon
        icon_lbl = QtWidgets.QLabel()
        icon_lbl.setFixedSize(18, 18)
        icon_lbl.setPixmap(self._icon_for(attachment).pixmap(18, 18))

        # Name (with title if available, otherwise filename)
        self.name_lbl = QtWidgets.QLabel(self._elide(attachment.display_name))
        tooltip_text = f"File: {attachment.file_path.name}"
        if attachment.title:
            tooltip_text += f"\nTitle: {attachment.title}"
        if attachment.notes:
            tooltip_text += f"\nNotes: {attachment.notes}"
        self.name_lbl.setToolTip(tooltip_text)

        lay.addWidget(icon_lbl)
        lay.addWidget(self.name_lbl)

        # Remove button
        remove_btn = QtWidgets.QToolButton()
        remove_btn.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_TitleBarCloseButton))
        remove_btn.setIconSize(QtCore.QSize(12, 12))
        remove_btn.setToolTip("Remove attachment")
        remove_btn.setCursor(QtCore.Qt.PointingHandCursor)
        remove_btn.clicked.connect(lambda: self.removed.emit(self.attachment))
        lay.addWidget(remove_btn)

    def _icon_for(self, attachment: AttachmentMetadata) -> QtGui.QIcon:
        suffix = attachment.file_path.suffix.lower()
        st = self.style()

        # Check if it's an image file (including screenshots)
        if suffix in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp", ".svg"}:
            return st.standardIcon(QtWidgets.QStyle.SP_FileDialogContentsView)
        # For all other files (documents, etc.)
        else:
            return st.standardIcon(QtWidgets.QStyle.SP_FileIcon)

    def _elide(self, text: str, width: int = 180) -> str:
        metrics = QtGui.QFontMetrics(self.font())
        return metrics.elidedText(text, QtCore.Qt.ElideMiddle, width)

    def resizeEvent(self, e: QtGui.QResizeEvent) -> None:
        super().resizeEvent(e)
        # Keep about 60px for icon + buttons + paddings
        available_width = max(60, self.width() - 60)
        self.name_lbl.setText(self._elide(self.attachment.display_name, available_width))


class TimeResourceManagementTab(QtWidgets.QWidget):
    requestScreenshot = QtCore.Signal(int)  # row index

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None, policy_enforcer=None) -> None:
        super().__init__(parent)
        self._policy_enforcer = policy_enforcer
        _LOGGER.info("TimeResourceManagementTab initialized")

        # Internal data storage
        self._time_allocations: List[TimeAllocationItem] = []
        self._editing_index: Optional[int] = None
        self._original_item: Optional[TimeAllocationItem] = None
        self._entry_attachments: List[AttachmentMetadata] = []

        # Form data storage for single-instance fields
        self._form_data = {
            'primary_activities': '',
            'peak_workload_periods': '',
            'resource_constraints': '',
            'waiting_time': '',
            'overtime_patterns': '',
            'notes': ''
        }

        # ---- scroller ----
        scroller = QtWidgets.QScrollArea(self)
        scroller.setObjectName("TimeResourceScroll")
        scroller.setWidgetResizable(True)
        scroller.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroller.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        scroller.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self._scroller = scroller

        root = QtWidgets.QWidget()
        root.setStyleSheet("background:#F3F4F6;")
        scroller.setWidget(root)

        page = QtWidgets.QVBoxLayout(root)
        page.setContentsMargins(12, 10, 12, 12)
        page.setSpacing(12)

        # ---- card ----
        card = QtWidgets.QFrame(root)
        card.setObjectName("TimeResourceCard")
        card.setStyleSheet("""
            QFrame#TimeResourceCard {
                background:#FFFFFF;
                border:1px solid #E5E7EB;
                border-radius:12px;
            }
            QFrame#TimeResourceCard QLabel { background: transparent; }
            QPushButton {
                background:#A5BBCF;
                color:#FFFFFF;
                border:1px solid #A5BBCF;
                border-radius:6px;
                padding:6px 10px;
            }
            QPushButton:hover { background:#1f2937; border-color:#1f2937; }
            QPushButton:disabled { background:#9CA3AF; border-color:#9CA3AF; color:#F3F4F6; }
        """)
        page.addWidget(card)

        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(10)

        # ---- header + info ----
        section = InfoSection(
            title="Time & Resource Management",
            subtitle="Track how you spend your time and identify resource constraints that impact productivity. This information helps quantify automation opportunities and calculate potential ROI.",
            info_html=TIME_RESOURCE_INFO,
            icon_size_px=28,
            parent=card,
        )
        card_layout.addWidget(section)
        section.bind_scrollarea(self._scroller)

        # ---- Overview section ----
        overview_frame = QtWidgets.QFrame()
        overview_frame.setObjectName("OverviewFrame")
        overview_frame.setStyleSheet("""
            QFrame#OverviewFrame {
                background: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        card_layout.addWidget(overview_frame)

        overview_layout = QtWidgets.QVBoxLayout(overview_frame)
        overview_layout.setContentsMargins(6,6,6,6)
        overview_layout.setSpacing(12)

        # Overview form
        overview_form_host = QtWidgets.QWidget()
        overview_form_host.setStyleSheet("background:transparent;")
        overview_form = _StackedLabelForm(overview_form_host)

        # Primary Activities
        self.primary_activities_edit = QtWidgets.QTextEdit()
        self.primary_activities_edit.setPlaceholderText("Describe your main work activities and responsibilities")
        self.primary_activities_edit.setMaximumHeight(80)
        _force_dark_text(self.primary_activities_edit)
        self.primary_activities_edit.textChanged.connect(lambda: self._save_form_field('primary_activities', self.primary_activities_edit.toPlainText()))
        overview_form.add_row("Primary Activities", self.primary_activities_edit)

        # Peak Workload Periods
        self.peak_workload_periods_edit = QtWidgets.QTextEdit()
        self.peak_workload_periods_edit.setPlaceholderText("When is your workload most intense? (daily, weekly, monthly patterns)")
        self.peak_workload_periods_edit.setMaximumHeight(80)
        _force_dark_text(self.peak_workload_periods_edit)
        self.peak_workload_periods_edit.textChanged.connect(lambda: self._save_form_field('peak_workload_periods', self.peak_workload_periods_edit.toPlainText()))
        overview_form.add_row("Peak Workload Periods", self.peak_workload_periods_edit)

        # Resource Constraints
        self.resource_constraints_edit = QtWidgets.QTextEdit()
        self.resource_constraints_edit.setPlaceholderText("What limits your productivity? (tools, information, approvals, etc.)")
        self.resource_constraints_edit.setMaximumHeight(80)
        _force_dark_text(self.resource_constraints_edit)
        self.resource_constraints_edit.textChanged.connect(lambda: self._save_form_field('resource_constraints', self.resource_constraints_edit.toPlainText()))
        overview_form.add_row("Resource Constraints", self.resource_constraints_edit)

        # Waiting Time
        self.waiting_time_edit = QtWidgets.QTextEdit()
        self.waiting_time_edit.setPlaceholderText("Time spent waiting for approvals, information, responses, etc.")
        self.waiting_time_edit.setMaximumHeight(80)
        _force_dark_text(self.waiting_time_edit)
        self.waiting_time_edit.textChanged.connect(lambda: self._save_form_field('waiting_time', self.waiting_time_edit.toPlainText()))
        overview_form.add_row("Waiting Time", self.waiting_time_edit)

        # Overtime Patterns
        self.overtime_patterns_edit = QtWidgets.QTextEdit()
        self.overtime_patterns_edit.setPlaceholderText("When and why do you work overtime?")
        self.overtime_patterns_edit.setMaximumHeight(80)
        _force_dark_text(self.overtime_patterns_edit)
        self.overtime_patterns_edit.textChanged.connect(lambda: self._save_form_field('overtime_patterns', self.overtime_patterns_edit.toPlainText()))
        overview_form.add_row("Overtime Patterns", self.overtime_patterns_edit)

        # Additional Notes
        self.notes_edit = QtWidgets.QTextEdit()
        self.notes_edit.setPlaceholderText("Any other time management or resource-related observations")
        self.notes_edit.setMaximumHeight(80)
        _force_dark_text(self.notes_edit)
        self.notes_edit.textChanged.connect(lambda: self._save_form_field('notes', self.notes_edit.toPlainText()))
        overview_form.add_row("Additional Notes", self.notes_edit)

        overview_layout.addWidget(overview_form_host)

        # ---- Time Allocations section ----
        allocations_frame = QtWidgets.QFrame()
        allocations_frame.setObjectName("AllocationsFrame")
        allocations_frame.setStyleSheet("""
            QFrame#AllocationsFrame {
                background: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        card_layout.addWidget(allocations_frame)

        allocations_layout = QtWidgets.QVBoxLayout(allocations_frame)
        allocations_layout.setContentsMargins(6,6,6,6)
        allocations_layout.setSpacing(12)

        # Time Allocations header
        allocations_header = QtWidgets.QLabel("Time Allocations")
        allocations_header.setStyleSheet("font-size:14px; color:#1F2937; font-weight:600; background:transparent;")
        allocations_layout.addWidget(allocations_header)

        # Entry form
        entry_form = self._create_entry_form()
        allocations_layout.addWidget(entry_form)

        # Table
        self._create_table_section(allocations_layout)

        # Mount scroller
        root_layout = QtWidgets.QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(scroller)

        # Initial scrollbar mode
        self._set_scrollbar_stealth(True)
        section.toggled.connect(lambda open_: self._set_scrollbar_stealth(not open_))

        self._connect_signals()
        self._load_data()

        # Screenshot tool
        self._shot_tool = ScreenshotTool(self)
        self.requestScreenshot.connect(self._launch_screenshot_for_row)
        self._shot_tool.screenshotSaved.connect(self._on_screenshot_saved)

    def _get_section_name(self) -> str:
        return "time_resource_management"

    def _create_entry_form(self) -> QtWidgets.QWidget:
        """Create the time allocation entry form"""
        form_host = QtWidgets.QWidget()
        form_host.setStyleSheet("background:transparent;")
        form = _StackedLabelForm(form_host)

        # Activity name
        self.activity_name_edit = QtWidgets.QLineEdit()
        self.activity_name_edit.setPlaceholderText("e.g., Email processing, Report generation")
        _force_dark_text(self.activity_name_edit)
        form.add_row("Activity Name", self.activity_name_edit)

        # Hours and priority row
        hours_priority_row = QtWidgets.QHBoxLayout()
        hours_priority_row.setSpacing(12)

        # Hours per week
        self.hours_spinner = QtWidgets.QSpinBox()
        self.hours_spinner.setMinimum(0)
        self.hours_spinner.setMaximum(100)
        self.hours_spinner.setSuffix(" hrs")
        self.hours_spinner.setStyleSheet("""
                        QSpinBox {
                            background: white;
                            color: black;
                            padding: 4px 8px;
                        }
                    """)

        # Priority level
        self.priority_combo = QtWidgets.QComboBox()
        self.priority_combo.addItems(PRIORITY_LEVELS)
        self.priority_combo.setCurrentText("Medium")
        self.priority_combo.setStyleSheet("""
            QComboBox {
                background: white;
                color: black;
                padding: 4px 8px;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
            QComboBox QAbstractItemView {
                background: #F5F6F7;
                color: black;
                selection-background-color: rgb(100, 100, 100);
            }
        """)

        hours_priority_row.addWidget(self._create_labeled_field("Hours/Week", self.hours_spinner))
        hours_priority_row.addWidget(self._create_labeled_field("Priority", self.priority_combo))

        form.addLayout(hours_priority_row)

        # Notes
        self.allocation_notes_edit = QtWidgets.QTextEdit()
        self.allocation_notes_edit.setPlaceholderText("Additional details about this activity...")
        self.allocation_notes_edit.setMaximumHeight(60)
        _force_dark_text(self.allocation_notes_edit)
        form.add_row("Notes", self.allocation_notes_edit)

        # Attachment section
        attachment_section = self._create_attachment_section()
        form.addWidget(attachment_section)

        # Actions row
        actions_row = QtWidgets.QHBoxLayout()
        actions_row.setSpacing(8)

        # Create buttons with specific styling
        form_button_style = """
            QPushButton {
                background:#A5BBCF;
                color:#FFFFFF;
                border:1px solid #A5BBCF;
                border-radius:6px;
                padding:6px 10px;
            }
            QPushButton:hover { background:#1f2937; border-color:#1f2937; }
            QPushButton:disabled { background:#9CA3AF; border-color:#9CA3AF; color:#F3F4F6; }
        """

        self.btn_attach = QtWidgets.QPushButton("Attach...")
        self.btn_attach.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_attach.setStyleSheet(form_button_style)

        self.btn_capture = QtWidgets.QPushButton("Capture Screenshot")
        self.btn_capture.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_capture.setStyleSheet(form_button_style)

        actions_row.addWidget(self.btn_attach, 0, QtCore.Qt.AlignLeft)
        actions_row.addWidget(self.btn_capture, 0, QtCore.Qt.AlignLeft)
        actions_row.addStretch(1)

        # Cancel button (hidden by default)
        self.btn_cancel = QtWidgets.QPushButton("Cancel Edit")
        self.btn_cancel.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_cancel.setStyleSheet(form_button_style)
        self.btn_cancel.setVisible(False)
        actions_row.addWidget(self.btn_cancel, 0, QtCore.Qt.AlignRight)

        self.btn_add = QtWidgets.QPushButton("Add Allocation")
        self.btn_add.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_add.setStyleSheet(form_button_style)
        actions_row.addWidget(self.btn_add, 0, QtCore.Qt.AlignRight)

        form.addLayout(actions_row)

        return form_host

    def _create_labeled_field(self, label: str, field: QtWidgets.QWidget) -> QtWidgets.QWidget:
        """Create a labeled field widget"""
        container = QtWidgets.QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        lbl = QtWidgets.QLabel(label)
        lbl.setStyleSheet("font-size:13px; color:#334155; background:transparent; font-weight:500;")
        layout.addWidget(lbl)
        layout.addWidget(field)

        return container

    def _create_attachment_section(self) -> QtWidgets.QWidget:
        """Create attachment management section"""
        section = QtWidgets.QWidget()
        section.setStyleSheet("background: transparent;")
        layout = QtWidgets.QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Attachment chips area
        self.chips_area = QtWidgets.QWidget()
        self.chips_area.setStyleSheet("background: transparent;")
        self.chips_flow = FlowLayout(self.chips_area, margin=0, hspacing=6, vspacing=6)

        layout.addWidget(self.chips_area)

        return section

    def _create_table_section(self, parent_layout: QtWidgets.QVBoxLayout):
        """Create the time allocations table section"""
        # Table
        self.table = QtWidgets.QTableWidget()
        self.table.setObjectName("timeAllocationsTable")
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Activity", "Hours/Week", "Priority", "Attachments"])

        # Table settings
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.Fixed)

        self.table.setColumnWidth(1, 100)
        self.table.setColumnWidth(2, 80)
        self.table.setColumnWidth(3, 100)

        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(False)

        # Apply table styling
        self.table.setStyleSheet("""
            QTableWidget {
                background: #FFFFFF;
                color: #0F172A;
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                alternate-background-color: #F8FAFC;
                outline: none;
                gridline-color: #E5E7EB;
                show-decoration-selected: 1;
            }
            QHeaderView::section {
                background: #F1F5F9;
                color: #0F172A;
                padding: 6px 8px;
                border: none;
                border-right: 1px solid #E5E7EB;
                border-bottom: 1px solid #E5E7EB;
            }
            QTableWidget::item {
                padding: 6px 8px;
                border: none;
                margin: 0px;
                border-bottom: 1px solid #F1F5F9;
            }
            QTableWidget::item:selected {
                background: #E5E7EB;
                color: #0F172A;
            }
        """)

        parent_layout.addWidget(self.table)

        # Action buttons
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch(1)

        self.btn_edit = QtWidgets.QPushButton("Edit Selected")
        self.btn_edit.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_delete = QtWidgets.QPushButton("Delete Selected")
        self.btn_delete.setCursor(QtCore.Qt.PointingHandCursor)

        button_layout.addWidget(self.btn_edit)
        button_layout.addWidget(self.btn_delete)

        parent_layout.addLayout(button_layout)

    def _set_scrollbar_stealth(self, stealth: bool):
        """Toggle scrollbar visibility styling"""
        sb = self._scroller.verticalScrollBar()
        sb.style().unpolish(sb)
        sb.style().polish(sb)
        sb.update()

    def _connect_signals(self):
        """Connect UI signals"""
        # Entry form signals
        self.btn_add.clicked.connect(self._add_or_update_allocation)
        self.btn_cancel.clicked.connect(self._cancel_edit)
        self.btn_attach.clicked.connect(self._add_attachment)
        self.btn_capture.clicked.connect(self._capture_new_screenshot)

        # Table signals
        self.btn_edit.clicked.connect(self._edit_selected_allocation)
        self.btn_delete.clicked.connect(self._delete_selected_allocation)

        self.table.itemDoubleClicked.connect(lambda: self._edit_selected_allocation())
        self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._table_context_menu)

        # Form change detection
        self.activity_name_edit.textChanged.connect(self._update_add_button)
        self.hours_spinner.valueChanged.connect(self._update_add_button)

    def _save_form_field(self, field_key: str, value: str):
        """Save single form field with auto-save"""
        self._form_data[field_key] = value
        self._save_time_resource_data()

    def _update_add_button(self):
        """Enable/disable add button based on required fields"""
        has_name = bool(self.activity_name_edit.text().strip())
        has_hours = self.hours_spinner.value() > 0
        self.btn_add.setEnabled(has_name and has_hours)

    def _add_attachment(self):
        """Add file attachment"""
        file_dialog = QtWidgets.QFileDialog(self)
        file_dialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)

        if file_dialog.exec():
            file_paths = file_dialog.selectedFiles()
            if file_paths:
                file_path = Path(file_paths[0])

                # Create attachment
                attachment = AttachmentMetadata(
                    file_path=file_path,
                    title=file_path.name,
                    is_screenshot=False
                )

                # Avoid duplicates
                if attachment not in self._entry_attachments:
                    self._add_attachment_chip(attachment)

    def _add_attachment_chip(self, attachment: AttachmentMetadata):
        """Add attachment chip to the UI"""
        self._entry_attachments.append(attachment)

        chip = AttachmentChip(attachment)
        chip.removed.connect(self._remove_attachment_chip)

        # Add to flow layout
        self.chips_flow.addWidget(chip)

    def _remove_attachment_chip(self, attachment: AttachmentMetadata):
        """Remove attachment chip from the UI"""
        # Remove chip widget
        for i in range(self.chips_flow.count()):
            item = self.chips_flow.itemAt(i)
            w = item.widget() if item else None
            if isinstance(w, AttachmentChip) and w.attachment == attachment:
                self.chips_flow.takeAt(i)
                w.deleteLater()
                break

        # Remove from attachments list
        self._entry_attachments = [att for att in self._entry_attachments if att != attachment]

    def _capture_new_screenshot(self):
        """Capture a screenshot for the current entry"""
        idx = self._selected_row()
        if idx < 0:
            idx = -1  # For entry form
        self.requestScreenshot.emit(idx)

    @QtCore.Slot(int)
    def _launch_screenshot_for_row(self, row_idx: int):
        """Launch screenshot tool"""
        self._pending_row_idx = row_idx
        self._shot_tool.start()

    @QtCore.Slot(str, dict)
    def _on_screenshot_saved(self, file_path: str, metadata: dict):
        """Handle screenshot saved event"""
        idx = getattr(self, "_pending_row_idx", -1)
        screenshot_path = Path(file_path)

        if not screenshot_path.exists():
            return

        # Extract title and notes from metadata
        title = metadata.get('title', '') or f"Screenshot {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        description = metadata.get('description', '')
        markers = metadata.get('markers', [])

        # Combine description and marker notes
        notes_parts = []
        if description.strip():
            notes_parts.append(description.strip())

        for marker in markers:
            if isinstance(marker, dict) and marker.get('text', '').strip():
                marker_type = "Pin" if marker.get('kind') == 'pin' else "Arrow"
                marker_num = f" {marker.get('number', '')}" if marker.get('kind') == 'pin' else ""
                notes_parts.append(f"{marker_type}{marker_num}: {marker['text'].strip()}")

        notes_text = "\n".join(notes_parts)

        if idx < 0:
            # Screenshot for entry form
            screenshot_attachment = AttachmentMetadata(
                file_path=screenshot_path,
                title=title,
                notes=notes_text,
                is_screenshot=True
            )

            if screenshot_attachment not in self._entry_attachments:
                self._add_attachment_chip(screenshot_attachment)

        else:
            # Screenshot for existing allocation
            if 0 <= idx < len(self._time_allocations):
                screenshot_attachment = AttachmentMetadata(
                    file_path=screenshot_path,
                    title=title,
                    notes=notes_text,
                    is_screenshot=True
                )

                self._time_allocations[idx].attachments.append(screenshot_attachment)
                self._populate_table_row(idx, self._time_allocations[idx])
                self._save_time_resource_data()

    def _add_or_update_allocation(self):
        """Add new time allocation or update existing one"""
        activity_name = self.activity_name_edit.text().strip()
        if not activity_name:
            activity_name = f"Activity - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        hours_per_week = self.hours_spinner.value()
        priority_level = self.priority_combo.currentText()
        notes = self.allocation_notes_edit.toPlainText().strip()

        # Create/update item
        item = TimeAllocationItem(
            activity_name=activity_name,
            hours_per_week=hours_per_week,
            priority_level=priority_level,
            notes=notes,
            attachments=self._entry_attachments.copy()
        )

        if self._editing_index is not None:
            # Update existing item
            self._time_allocations[self._editing_index] = item
            self._populate_table_row(self._editing_index, item)

            # Reset editing state
            self._editing_index = None
            self._original_item = None
            self.btn_add.setText("Add Allocation")
            self.btn_cancel.setVisible(False)

            # Select updated row
            self.table.selectRow(self._editing_index or 0)
        else:
            # Add new item
            self._time_allocations.append(item)
            self._append_row(item)

            # Select new row
            new_row = self.table.rowCount() - 1
            if new_row >= 0:
                self.table.selectRow(new_row)

        # Clear form and save
        self._clear_entry_form()
        self._save_time_resource_data()

    def _clear_entry_form(self):
        """Clear the entry form"""
        self.activity_name_edit.clear()
        self.hours_spinner.setValue(0)
        self.priority_combo.setCurrentText("Medium")
        self.allocation_notes_edit.clear()

        # Clear attachment chips
        for i in reversed(range(self.chips_flow.count())):
            item = self.chips_flow.itemAt(i)
            w = item.widget() if item else None
            if isinstance(w, AttachmentChip):
                self.chips_flow.takeAt(i)
                w.deleteLater()

        # Clear attachment list
        self._entry_attachments.clear()

    def _cancel_edit(self):
        """Cancel editing and restore original item"""
        if self._editing_index is not None and self._original_item is not None:
            # Restore original item
            self._time_allocations[self._editing_index] = self._original_item
            self._populate_table_row(self._editing_index, self._original_item)
            self.table.selectRow(self._editing_index)

        # Reset editing state
        self._editing_index = None
        self._original_item = None
        self.btn_add.setText("Add Allocation")
        self.btn_cancel.setVisible(False)
        self._clear_entry_form()

    def _edit_selected_allocation(self):
        """Edit the selected time allocation"""
        row = self._selected_row()
        if row < 0 or row >= len(self._time_allocations):
            return

        # Store original item for cancellation
        self._original_item = self._time_allocations[row]
        self._editing_index = row

        # Load item into form
        item = self._time_allocations[row]
        self.activity_name_edit.setText(item.activity_name)
        self.hours_spinner.setValue(item.hours_per_week)
        self.priority_combo.setCurrentText(item.priority_level)
        self.allocation_notes_edit.setPlainText(item.notes)

        # Load attachments
        self._entry_attachments = item.attachments.copy()
        for attachment in self._entry_attachments:
            chip = AttachmentChip(attachment)
            chip.removed.connect(self._remove_attachment_chip)
            self.chips_flow.addWidget(chip)

        # Update UI state
        self.btn_add.setText("Update Allocation")
        self.btn_cancel.setVisible(True)

    def _delete_selected_allocation(self):
        """Delete the selected time allocation"""
        row = self._selected_row()
        if row < 0:
            return

        reply = QtWidgets.QMessageBox.question(
            self, "Delete Allocation",
            "Remove the selected time allocation?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )

        if reply == QtWidgets.QMessageBox.Yes:
            # Clean up files before deletion
            item = self._time_allocations[row]
            self._cleanup_item_files(item.attachments)

            self.table.removeRow(row)
            del self._time_allocations[row]
            self._save_time_resource_data()

            # Reset editing state if deleted item was being edited
            if self._editing_index == row:
                self._editing_index = None
                self._original_item = None
                self.btn_add.setText("Add Allocation")
                self.btn_cancel.setVisible(False)
                self._clear_entry_form()

    def _selected_row(self) -> int:
        """Get currently selected row index"""
        selection = self.table.selectionModel().selectedRows()
        return selection[0].row() if selection else -1

    def _table_context_menu(self, position: QtCore.QPoint):
        """Show context menu for table"""
        row = self.table.indexAt(position).row()
        if row < 0:
            return

        menu = QtWidgets.QMenu(self)
        edit_action = menu.addAction("Edit")
        delete_action = menu.addAction("Delete")

        action = menu.exec(self.table.viewport().mapToGlobal(position))

        if action == edit_action:
            self._edit_selected_allocation()
        elif action == delete_action:
            self._delete_selected_allocation()

    def _append_row(self, item: TimeAllocationItem):
        """Add a row to the table"""
        row = self.table.rowCount()
        self.table.insertRow(row)
        self._populate_table_row(row, item)

    def _populate_table_row(self, row: int, item: TimeAllocationItem):
        """Populate table row with item data"""

        def create_item(text: str) -> QtWidgets.QTableWidgetItem:
            item_widget = QtWidgets.QTableWidgetItem(text)
            item_widget.setFlags(item_widget.flags() ^ QtCore.Qt.ItemIsEditable)
            return item_widget

        self.table.setItem(row, 0, create_item(item.activity_name))
        self.table.setItem(row, 1, create_item(f"{item.hours_per_week} hrs"))
        self.table.setItem(row, 2, create_item(item.priority_level))

        files_text = ", ".join(att.display_name for att in item.attachments) if item.attachments else ""
        self.table.setItem(row, 3, create_item(files_text))

    def _copy_attachments_to_storage(self, item_id: int, attachments: List[AttachmentMetadata]) -> List[AttachmentMetadata]:
        """Copy attachments to organized storage and return updated attachment list"""
        section = self._get_section_name()
        updated_attachments = []

        for attachment in attachments:
            if not FileManager.validate_file_exists(attachment.file_path):
                _LOGGER.warning(f"Skipping missing file: {attachment.file_path}")
                continue

            # Check if file is already in our storage (avoid double-copying)
            if self._is_file_in_storage(attachment.file_path):
                updated_attachments.append(attachment)
                continue

            # Copy to storage
            new_path = FileManager.copy_attachment_to_storage(
                attachment.file_path,
                section,
                item_id,
                attachment.is_screenshot
            )

            if new_path:
                # Create new attachment with updated path
                updated_attachment = AttachmentMetadata(
                    file_path=new_path,
                    title=attachment.title,
                    notes=attachment.notes,
                    is_screenshot=attachment.is_screenshot
                )
                updated_attachments.append(updated_attachment)
            else:
                _LOGGER.error(f"Failed to copy attachment: {attachment.file_path}")

        return updated_attachments

    def _cleanup_item_files(self, attachments: List[AttachmentMetadata]) -> None:
        """Clean up files when an item is deleted"""
        for attachment in attachments:
            if self._is_file_in_storage(attachment.file_path):
                FileManager.delete_file(attachment.file_path)

    def _is_file_in_storage(self, file_path: Path) -> bool:
        """Check if a file is in our organized storage directory"""
        try:
            files_dir = get_files_dir()
            return files_dir in file_path.parents
        except Exception:
            return False

    def _load_data(self):
        """Load data from database"""
        try:
            with DatabaseSession() as session:
                # Load single-instance time resource management data
                time_resource = session.query(TimeResourceManagement).first()
                if time_resource:
                    self._form_data = {
                        'primary_activities': time_resource.primary_activities or '',
                        'peak_workload_periods': time_resource.peak_workload_periods or '',
                        'resource_constraints': time_resource.resource_constraints or '',
                        'waiting_time': time_resource.waiting_time or '',
                        'overtime_patterns': time_resource.overtime_patterns or '',
                        'notes': time_resource.notes or ''
                    }

                    # Populate form fields
                    self.primary_activities_edit.setPlainText(self._form_data['primary_activities'])
                    self.peak_workload_periods_edit.setPlainText(self._form_data['peak_workload_periods'])
                    self.resource_constraints_edit.setPlainText(self._form_data['resource_constraints'])
                    self.waiting_time_edit.setPlainText(self._form_data['waiting_time'])
                    self.overtime_patterns_edit.setPlainText(self._form_data['overtime_patterns'])
                    self.notes_edit.setPlainText(self._form_data['notes'])

                # Load time allocations
                allocations = session.query(TimeAllocation).order_by(TimeAllocation.priority_rank.asc()).all()
                for db_allocation in allocations:
                    item = TimeAllocationItem(
                        activity_name=db_allocation.activity_name,
                        hours_per_week=db_allocation.hours_per_week,
                        priority_level=db_allocation.priority_level,
                        pain_point_id=db_allocation.pain_point_id,
                        process_id=db_allocation.process_id
                    )
                    self._time_allocations.append(item)
                    self._append_row(item)

                _LOGGER.info(f"Loaded time resource data and {len(allocations)} time allocations")

        except Exception as e:
            _LOGGER.error(f"Failed to load time resource data: {e}")

    def _save_time_resource_data(self):
        """Save data to database"""
        try:
            with DatabaseSession() as session:
                # Save single-instance time resource management data
                time_resource = session.query(TimeResourceManagement).first()
                if not time_resource:
                    time_resource = TimeResourceManagement()
                    session.add(time_resource)

                time_resource.primary_activities = self._form_data.get('primary_activities', '')
                time_resource.peak_workload_periods = self._form_data.get('peak_workload_periods', '')
                time_resource.resource_constraints = self._form_data.get('resource_constraints', '')
                time_resource.waiting_time = self._form_data.get('waiting_time', '')
                time_resource.overtime_patterns = self._form_data.get('overtime_patterns', '')
                time_resource.notes = self._form_data.get('notes', '')

                # Save time allocations
                session.query(TimeAllocation).delete()
                for rank, item in enumerate(self._time_allocations, 1):
                    db_allocation = TimeAllocation(
                        activity_name=item.activity_name,
                        hours_per_week=item.hours_per_week,
                        priority_level=item.priority_level,
                        priority_rank=rank,
                        pain_point_id=item.pain_point_id,
                        process_id=item.process_id
                    )
                    session.add(db_allocation)

                _LOGGER.info(f"Saved time resource data and {len(self._time_allocations)} time allocations")

        except Exception as e:
            _LOGGER.error(f"Failed to save time resource data: {e}")

    def clear_fields(self):
        """Clear all fields - called on database reset"""
        # Clear form fields
        self.primary_activities_edit.clear()
        self.peak_workload_periods_edit.clear()
        self.resource_constraints_edit.clear()
        self.waiting_time_edit.clear()
        self.overtime_patterns_edit.clear()
        self.notes_edit.clear()

        self._form_data = {key: '' for key in self._form_data.keys()}

        # Clear time allocations
        self._time_allocations.clear()
        self.table.setRowCount(0)

        # Reset editing state
        self._editing_index = None
        self._original_item = None
        self.btn_add.setText("Add Allocation")
        self.btn_cancel.setVisible(False)
        self._clear_entry_form()
