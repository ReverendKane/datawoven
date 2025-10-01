from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List
import json

from PySide6 import QtWidgets, QtCore, QtGui
from discovery_assistant.ui.widgets.draggable_table import DraggableTableWidget
from discovery_assistant.baselogger import logging
from discovery_assistant.ui.widgets.info import InfoSection
from discovery_assistant.ui.info_text import PROCESSES_INFO
from discovery_assistant.ui.widgets.screenshot_tool import ScreenshotTool
from discovery_assistant.storage import DatabaseSession, Process, get_attachments_dir, get_screenshots_dir, FileManager, get_files_dir

_LOGGER = logging.getLogger("DISCOVERY.ui.tabs.processes_tab")


# -------------------------
# Enhanced data models
# -------------------------

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
class ProcessItem:
    title: str
    notes: str = ""
    attachments: List[AttachmentMetadata] = field(default_factory=list)

    @property
    def documents(self) -> List[str]:
        """Legacy compatibility - return file paths as strings"""
        return [str(att.file_path) for att in self.attachments if not att.is_screenshot]

    @property
    def screenshots(self) -> int:
        """Count of screenshot attachments"""
        return len([att for att in self.attachments if att.is_screenshot])


# -------------------------
# Attachment dialog
# -------------------------

class AttachmentDialog(QtWidgets.QDialog):
    """Dialog for adding file attachments with metadata"""

    def __init__(self, parent=None, attachment: Optional[AttachmentMetadata] = None):
        super().__init__(parent)
        self.setWindowTitle("Attach Document")
        self.setModal(True)
        self.resize(520, 380)
        self.setStyleSheet("background-color: rgb(255, 255, 255);")

        self._selected_path: Optional[Path] = None

        body = QtWidgets.QVBoxLayout(self)
        body.setContentsMargins(16, 16, 16, 16)
        body.setSpacing(12)

        # File selection
        file_section = QtWidgets.QVBoxLayout()
        file_section.setSpacing(6)

        file_label = QtWidgets.QLabel("Document File")
        file_label.setStyleSheet("font-size:13px; color:#334155; font-weight:500;")
        file_section.addWidget(file_label)

        file_row = QtWidgets.QHBoxLayout()
        file_row.setSpacing(8)

        self.file_path_edit = QtWidgets.QLineEdit()
        self.file_path_edit.setPlaceholderText("Select a file to attach...")
        self.file_path_edit.setReadOnly(True)
        self._apply_input_style(self.file_path_edit)

        self.browse_btn = QtWidgets.QPushButton("Browse...")
        self.browse_btn.setStyleSheet("""
            QPushButton {
                background:#A5BBCF;
                color:#FFFFFF;
                border:1px solid #A5BBCF;
                border-radius:6px;
                padding:6px 12px;
                font-weight:500;
            }
            QPushButton:hover { background:#1f2937; border-color:#1f2937; }
        """)
        self.browse_btn.clicked.connect(self._browse_file)

        file_row.addWidget(self.file_path_edit, 1)
        file_row.addWidget(self.browse_btn, 0)
        file_section.addLayout(file_row)

        body.addLayout(file_section)

        # Title field
        title_section = QtWidgets.QVBoxLayout()
        title_section.setSpacing(6)

        title_label = QtWidgets.QLabel("Title")
        title_label.setStyleSheet("font-size:13px; color:#334155; font-weight:500;")
        title_section.addWidget(title_label)

        self.title_edit = QtWidgets.QLineEdit()
        self.title_edit.setPlaceholderText("Optional: Descriptive title for this document")
        self._apply_input_style(self.title_edit)
        title_section.addWidget(self.title_edit)

        body.addLayout(title_section)

        # Notes field
        notes_section = QtWidgets.QVBoxLayout()
        notes_section.setSpacing(6)

        notes_label = QtWidgets.QLabel("Notes")
        notes_label.setStyleSheet("font-size:13px; color:#334155; font-weight:500;")
        notes_section.addWidget(notes_label)

        self.notes_edit = QtWidgets.QTextEdit()
        self.notes_edit.setPlaceholderText("Optional: Additional context, purpose, or notes about this document...")
        self.notes_edit.setMinimumHeight(100)
        self._apply_input_style(self.notes_edit)
        notes_section.addWidget(self.notes_edit)

        body.addLayout(notes_section)

        # Dialog buttons
        body.addStretch(1)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch(1)

        cancel_btn = QtWidgets.QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background:#F3F4F6;
                color:#374151;
                border:1px solid #D1D5DB;
                border-radius:6px;
                padding:6px 16px;
                font-weight:500;
            }
            QPushButton:hover { background:#E5E7EB; }
        """)
        cancel_btn.clicked.connect(self.reject)

        attach_btn = QtWidgets.QPushButton("Attach")
        attach_btn.setStyleSheet("""
            QPushButton {
                background:#A5BBCF;
                color:#FFFFFF;
                border:1px solid #A5BBCF;
                border-radius:6px;
                padding:6px 16px;
                font-weight:500;
            }
            QPushButton:hover { background:#1f2937; border-color:#1f2937; }
            QPushButton:disabled { background:#9CA3AF; border-color:#9CA3AF; color:#F3F4F6; }
        """)
        attach_btn.clicked.connect(self.accept)

        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(attach_btn)
        body.addLayout(button_layout)

        # Load existing attachment if provided
        if attachment:
            self._selected_path = attachment.file_path
            self.file_path_edit.setText(str(attachment.file_path))
            self.title_edit.setText(attachment.title)
            self.notes_edit.setText(attachment.notes)

        # Enable/disable attach button based on file selection
        self._update_attach_button()
        self.file_path_edit.textChanged.connect(self._update_attach_button)

    def _apply_input_style(self, widget: QtWidgets.QWidget):
        """Apply consistent input styling"""
        style = """
            background:#FFFFFF;
            border:1px solid #E2E8F0;
            border-radius:8px;
            padding:8px 10px;
            color:#000000;
            selection-background-color:#0F172A;
        """
        focus_style = "border:1.5px solid #0F172A;"

        if isinstance(widget, QtWidgets.QLineEdit):
            widget.setStyleSheet(f"QLineEdit{{{style}}}QLineEdit:focus{{{focus_style}}}")
        elif isinstance(widget, QtWidgets.QTextEdit):
            widget.setStyleSheet(f"QTextEdit{{{style}}}QTextEdit:focus{{{focus_style}}}")

        # Set placeholder color
        pal = widget.palette()
        if hasattr(QtGui.QPalette, "PlaceholderText"):
            pal.setColor(QtGui.QPalette.PlaceholderText, QtGui.QColor("#94A3B8"))
        widget.setPalette(pal)

    def _browse_file(self):
        """Open file dialog to select document"""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select Document",
            "",
            "All Files (*)"
        )

        if file_path:
            self._selected_path = Path(file_path)
            self.file_path_edit.setText(file_path)

            # Auto-populate title with filename if title is empty
            if not self.title_edit.text().strip():
                self.title_edit.setText(self._selected_path.stem)

    def _update_attach_button(self):
        """Enable/disable attach button based on file selection"""
        # Find the attach button (it's the last one we created)
        buttons = self.findChildren(QtWidgets.QPushButton)
        if buttons:
            attach_btn = buttons[-1]  # Last button should be attach
            # Enable if we have a valid file path
            has_file = (hasattr(self, '_selected_path') and
                        self._selected_path is not None and
                        self._selected_path.exists())
            attach_btn.setEnabled(bool(has_file))

    def get_attachment(self) -> Optional[AttachmentMetadata]:
        """Get the attachment metadata from dialog"""
        if not self._selected_path or not self._selected_path.exists():
            return None

        return AttachmentMetadata(
            file_path=self._selected_path,
            title=self.title_edit.text().strip(),
            notes=self.notes_edit.toPlainText().strip(),
            is_screenshot=False
        )


# -------------------------
# Reusable style helpers
# -------------------------

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

        # Ensure placeholder text color matches across all input types
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
        lbl.setStyleSheet("font-size:13px; color:#334155; background:#FFFFFF;")
        row.addWidget(lbl)
        row.addWidget(field)
        self.addLayout(row)


# -------------------------
# Flow layout for chips
# -------------------------

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
        super().setGeometry(rect); self._do_layout(rect, False)

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


# -------------------------
# Enhanced attachment chip
# -------------------------

class AttachmentChip(QtWidgets.QFrame):
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

        # Edit button (only for non-screenshots)
        if not attachment.is_screenshot:
            edit_btn = QtWidgets.QToolButton()
            edit_btn.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_FileDialogDetailedView))
            edit_btn.setIconSize(QtCore.QSize(12, 12))
            edit_btn.setToolTip("Edit attachment details")
            edit_btn.setCursor(QtCore.Qt.PointingHandCursor)
            edit_btn.clicked.connect(lambda: self.edit_requested.emit(self.attachment))
            lay.addWidget(edit_btn)

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


# -------------------------
# Add/Edit dialog (reused)
# -------------------------

class ProcessDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, item: Optional[ProcessItem] = None):
        super().__init__(parent)
        self.setWindowTitle("Process")
        self.setModal(True)
        self.resize(520, 420)

        body = QtWidgets.QVBoxLayout(self)
        body.setContentsMargins(16, 16, 16, 16)
        body.setSpacing(12)

        form_w = QtWidgets.QWidget(self)
        form = _StackedLabelForm(form_w)

        self.title_edit = QtWidgets.QLineEdit()
        self.title_edit.setPlaceholderText("e.g., New ticket intake in Helpdesk")
        _force_dark_text(self.title_edit)
        form.add_row("Title", self.title_edit)

        self.notes_edit = QtWidgets.QTextEdit()
        self.notes_edit.setPlaceholderText("Describe the steps, systems, and handoffs involved…")
        self.notes_edit.setMinimumHeight(150)
        _force_dark_text(self.notes_edit)
        form.add_row("Notes", self.notes_edit)

        # Attachments quick-view (read-only in dialog)
        self.attachments_view = QtWidgets.QListWidget()
        self.attachments_view.setStyleSheet(
            "QListWidget { background:#FFFFFF; border:1px solid #E5E7EB; border-radius:8px; }"
        )
        form.add_row("Attachments", self.attachments_view)

        # Screenshot button for editing
        self.btn_screenshot = QtWidgets.QPushButton("Capture Screenshot")
        self.btn_screenshot.setToolTip("Launch the screenshot tool to capture a form or procedure.")

        # Actions
        actions = QtWidgets.QHBoxLayout()
        actions.addStretch(1)
        ok_btn = QtWidgets.QPushButton("Save")
        cancel_btn = QtWidgets.QPushButton("Cancel")
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        actions.addWidget(cancel_btn)
        actions.addWidget(ok_btn)

        body.addLayout(form)
        body.addWidget(self.btn_screenshot, 0, QtCore.Qt.AlignLeft)
        body.addStretch(1)
        body.addLayout(actions)

        if item:
            self.title_edit.setText(item.title)
            self.notes_edit.setText(item.notes)
            for attachment in item.attachments:
                display_name = attachment.display_name
                if attachment.title != attachment.file_path.name:
                    display_name += f" ({attachment.file_path.name})"
                self.attachments_view.addItem(display_name)

    def get_data(self) -> ProcessItem:
        return ProcessItem(
            title=self.title_edit.text().strip(),
            notes=self.notes_edit.toPlainText().strip(),
            attachments=[],  # This will be populated by the caller
        )


# -------------------------
# Main tab (updated)
# -------------------------

class ProcessesTab(QtWidgets.QWidget):
    requestScreenshot = QtCore.Signal(int)  # row index

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        _LOGGER.info("ProcessesTab initialized")

        # ---- scroller ----
        scroller = QtWidgets.QScrollArea(self)
        scroller.setObjectName("ProcessesScroll")
        scroller.setWidgetResizable(True)
        scroller.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroller.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        scroller.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroller.setStyleSheet("""
            QScrollArea#ProcessesScroll { background: transparent; border: none; }
            QScrollBar:vertical { background: transparent; width: 12px; margin: 8px 2px 8px 0px; }
            QScrollBar::handle:vertical { background: #D1D5DB; min-height: 24px; border-radius: 6px; }
            QScrollBar::handle:vertical:hover { background: #9CA3AF; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
        """)
        self._scroller = scroller

        root = QtWidgets.QWidget()
        root.setStyleSheet("background:#F3F4F6;")
        scroller.setWidget(root)

        page = QtWidgets.QVBoxLayout(root)
        page.setContentsMargins(12, 10, 12, 12)
        page.setSpacing(12)

        # ---- card ----
        card = QtWidgets.QFrame(root)
        card.setObjectName("ProcessesCard")
        card.setStyleSheet("""
            QFrame#ProcessesCard {
                background:#FFFFFF;
                border:1px solid #E5E7EB;
                border-radius:12px;
            }
            QFrame#ProcessesCard QLabel { background: transparent; }
            QFrame#ProcessesCard QWidget#ProcessesForm { background: transparent; }
            QLineEdit, QTextEdit {
                background:#FFFFFF;
                border:1px solid #E2E8F0;
                border-radius:8px;
                padding:8px 10px;
                color:#000000;
                selection-background-color:#0F172A;
            }
            QLineEdit:focus, QTextEdit:focus { border:1.5px solid #0F172A; }
            QPushButton {
                background:#A5BBCF;
                color:#FFFFFF;
                border:1px solid #A5BBCF;
                border-radius:6px;
                padding:6px 10px;
            }
            QPushButton:hover { background:#1f2937; border-color:#1f2937; }
            QPushButton:disabled { background:#9CA3AF; border-color:#9CA3AF; color:#F3F4F6; }
            QToolButton { background:transparent; border:none; }
        """)
        page.addWidget(card)

        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(10)

        # ---- header + info ----
        section = InfoSection(
            title="Core Processes",
            subtitle="Add one process per entry. You can attach documents and capture screenshots.",
            info_html=PROCESSES_INFO,
            icon_size_px=28,
            parent=card,
        )
        card_layout.addWidget(section)
        section.bind_scrollarea(self._scroller)

        # ---- form (title + notes) ----
        form_host = QtWidgets.QWidget(card)
        form_host.setObjectName("ProcessesForm")
        form = _StackedLabelForm(form_host)

        self.title_edit = QtWidgets.QLineEdit()
        self.title_edit.setPlaceholderText("Process title (e.g., Client Onboarding Workflow)")
        _force_dark_text(self.title_edit)
        form.add_row("Title", self.title_edit)

        self.notes_edit = QtWidgets.QTextEdit()
        self.notes_edit.setPlaceholderText("Briefly describe the steps, systems involved, and expected outcomes.")
        self.notes_edit.setMinimumHeight(100)
        _force_dark_text(self.notes_edit)
        form.add_row("Notes", self.notes_edit)

        card_layout.addWidget(form_host)

        # ---- actions row (compact) ----
        actions_row = QtWidgets.QHBoxLayout()
        actions_row.setSpacing(8)

        self.btn_attach = QtWidgets.QPushButton("Attach…")
        self.btn_attach.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_capture = QtWidgets.QPushButton("Capture Screenshot")
        self.btn_capture.setCursor(QtCore.Qt.PointingHandCursor)
        actions_row.addWidget(self.btn_attach, 0, QtCore.Qt.AlignLeft)
        actions_row.addWidget(self.btn_capture, 0, QtCore.Qt.AlignLeft)
        actions_row.addStretch(1)

        self.btn_add = QtWidgets.QPushButton("Add Process")
        self.btn_add.setCursor(QtCore.Qt.PointingHandCursor)
        actions_row.addWidget(self.btn_add, 0, QtCore.Qt.AlignRight)
        card_layout.addLayout(actions_row)

        # ---- attachment chips strip ----
        chips_box = QtWidgets.QFrame(card)
        chips_box.setObjectName("ChipsBox")
        chips_box.setStyleSheet("""
            QFrame#ChipsBox {
                background:#FFFFFF;
                border:1px solid #E2E8F0;
                border-radius:4px;
            }
        """)
        chips_col = QtWidgets.QVBoxLayout(chips_box)
        chips_col.setContentsMargins(10, 8, 10, 8)
        chips_col.setSpacing(6)

        chips_label = QtWidgets.QLabel("Attachments")
        chips_label.setStyleSheet("font-size:13px; color:#334155; background:transparent;")
        self.chips_area = QtWidgets.QWidget()
        self.chips_area.setStyleSheet("background: transparent;")
        self.chips_flow = FlowLayout(self.chips_area, margin=0, hspacing=6, vspacing=6)

        chips_col.addWidget(chips_label)
        chips_col.addWidget(self.chips_area)
        card_layout.addWidget(chips_box)

        # ---- table ----
        self.table = DraggableTableWidget(0, 3, card)
        self.table.setObjectName("ProcessesTable")
        self.table.setHorizontalHeaderLabels(
            ["Title", "Notes (preview)", "Attached Files"])  # Removed Screenshots column

        for c in range(self.table.columnCount()):
            item = self.table.horizontalHeaderItem(c)
            if item:
                item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        hdr = self.table.horizontalHeader()
        hdr.setStretchLastSection(False)
        hdr.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        hdr.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        hdr.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)  # Only 3 columns now
        hdr.setDefaultAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        hdr.setHighlightSections(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setAutoScroll(False)
        self.table.setFocusPolicy(QtCore.Qt.NoFocus)
        self.table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

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
                    QHeaderView {
                        border-top-left-radius: 6px;
                        border-top-right-radius: 6px;
                    }
                    QHeaderView::section {
                        background: #F1F5F9;
                        color: #0F172A;
                        padding: 6px 8px;
                        border: none;
                        border-right: 1px solid #E5E7EB;
                        border-bottom: 1px solid #E5E7EB;
                    }
                    QHeaderView::section:first {
                        border-top-left-radius: 12px;
                        border-left: none;
                    }
                    QHeaderView::section:last {
                        border-top-right-radius: 6px;
                        border-right: none;
                    }
                    QHeaderView::section:only-one {
                        border-top-left-radius: 6px;
                        border-top-right-radius: 6px;
                    }
                    QHeaderView::section:horizontal {
                        border-left: 1px solid #E5E7EB;
                    }
                    QHeaderView::section:horizontal:first {
                        border-left: none;
                    }
                    QTableWidget::item {
                        padding: 6px 8px;
                        border: none;
                        margin: 0px;
                        border-bottom: 1px solid #F1F5F9;
                    }
                    QTableWidget::item:selected,
                    QTableWidget::item:selected:active,
                    QTableWidget::item:selected:!active {
                        background: #E5E7EB;
                        color: #0F172A;
                        padding: 6px 8px;
                        border: none;
                        margin: 0px;
                        outline: none;
                    }
                    QTableWidget::item:hover {
                        background: #F8FAFC;
                        padding: 6px 8px;
                        border: none;
                        margin: 0px;
                    }
                    QTableWidget::item:alternate {
                        background: #F8FAFC;
                    }
                """)

        self.table.rowsReordered.connect(self._handle_row_reorder)

        pal = self.table.palette()
        pal.setColor(QtGui.QPalette.Base, QtGui.QColor("#FFFFFF"))
        pal.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor("#C7D1DA"))
        pal.setColor(QtGui.QPalette.Text, QtGui.QColor("#0F172A"))
        pal.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor("#0F172A"))
        self.table.setPalette(pal)
        card_layout.addWidget(self.table)

        # row actions
        row_actions = QtWidgets.QHBoxLayout()
        row_actions.addStretch(1)
        self.btn_open_doc = QtWidgets.QPushButton("Open Process")
        self.btn_open_doc.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_delete = QtWidgets.QPushButton("Delete")
        self.btn_delete.setCursor(QtCore.Qt.PointingHandCursor)
        row_actions.addWidget(self.btn_open_doc)
        row_actions.addWidget(self.btn_delete)
        card_layout.addLayout(row_actions)

        # cancel button
        self.btn_cancel = QtWidgets.QPushButton("Cancel Edit")
        self.btn_cancel.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_cancel.setVisible(False)
        actions_row.addWidget(self.btn_cancel, 0, QtCore.Qt.AlignRight)
        actions_row.addWidget(self.btn_add, 0, QtCore.Qt.AlignRight)
        card_layout.addLayout(actions_row)

        # mount scroller
        root_layout = QtWidgets.QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(scroller)

        # state - Updated to use new data structures
        self._items: list[ProcessItem] = []
        self._entry_attachments: list[AttachmentMetadata] = []  # Changed from Path to AttachmentMetadata
        self._editing_index: Optional[int] = None
        self._original_item: Optional[ProcessItem] = None

        # initial scrollbar mode
        self._set_scrollbar_stealth(True)
        section.toggled.connect(lambda open_: self._set_scrollbar_stealth(not open_))

        # wire up - Updated method names
        self.btn_attach.clicked.connect(self._attach_files)
        self.btn_capture.clicked.connect(self._capture_new_screenshot)
        self.btn_add.clicked.connect(self._add_process)

        self.btn_open_doc.clicked.connect(self._load_process_for_editing)
        self.btn_delete.clicked.connect(self._delete_selected)
        self.btn_cancel.clicked.connect(self._cancel_editing)

        self.table.itemDoubleClicked.connect(lambda *_: self._load_process_for_editing())
        self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._table_context_menu)

        # Screenshot tool
        self._shot_tool = ScreenshotTool(self)
        self.requestScreenshot.connect(self._launch_screenshot_for_row)
        self._shot_tool.screenshotSaved.connect(self._on_screenshot_saved)

        # Load existing data after all UI setup is complete
        self._load_processes_data()

    def _get_section_name(self) -> str:
        return "processes"

    def _handle_row_reorder(self, old_index: int, new_index: int):
        """Handle when rows are reordered via drag-and-drop"""
        if 0 <= old_index < len(self._items) and 0 <= new_index < len(self._items):
            item = self._items.pop(old_index)
            self._items.insert(new_index, item)

            # Save to database after reordering
            self._save_processes_data()

            # Refresh table
            self._repopulate_table()

            # Select the moved row
            self.table.selectRow(new_index)

    def _repopulate_table(self):
        """Refresh table display after drag-and-drop reordering"""
        self.table.setRowCount(0)
        for item in self._items:
            self._append_row(item)

    def _load_processes_data(self) -> None:
        """Load existing processes from database with file validation."""
        try:
            with DatabaseSession() as session:
                processes = session.query(Process).order_by(Process.priority_rank.asc()).all()

                for db_process in processes:
                    attachments = []
                    notes = db_process.notes or ""

                    # Extract attachment metadata from notes
                    if "__ATTACHMENTS__:" in notes:
                        try:
                            notes_part, attachments_json = notes.split("__ATTACHMENTS__:", 1)
                            attachment_data = json.loads(attachments_json)

                            for att_dict in attachment_data:
                                file_path = Path(att_dict['file_path'])
                                # Validate file exists
                                if FileManager.validate_file_exists(file_path):
                                    attachments.append(AttachmentMetadata(
                                        file_path=file_path,
                                        title=att_dict.get('title', ''),
                                        notes=att_dict.get('notes', ''),
                                        is_screenshot=att_dict.get('is_screenshot', False)
                                    ))
                                else:
                                    _LOGGER.warning(f"Missing attachment file: {file_path}")

                            notes = notes_part.strip()
                        except Exception as e:
                            _LOGGER.error(f"Error parsing attachments: {e}")

                    process_item = ProcessItem(
                        title=db_process.title,
                        notes=notes,
                        attachments=attachments
                    )

                    self._items.append(process_item)
                    self._append_row(process_item)

        except Exception as e:
            _LOGGER.error(f"Failed to load processes data: {e}")

    def _save_processes_data(self) -> None:
        """Save current processes list to database with file management."""
        try:
            with DatabaseSession() as session:
                # Clear existing processes
                session.query(Process).delete()

                # Save each process with file management
                for rank, item in enumerate(self._items, 1):
                    # First save to get ID
                    db_process = Process(
                        title=item.title,
                        priority_rank=rank,
                        notes=item.notes
                    )
                    session.add(db_process)
                    session.flush()  # Get the ID

                    # Copy attachments to storage and update paths
                    if item.attachments:
                        updated_attachments = self._copy_attachments_to_storage(
                            db_process.id, item.attachments
                        )
                        # Update the item with new paths
                        item.attachments = updated_attachments

                    # Save attachment metadata as JSON in notes or separate field
                    attachment_data = []
                    for att in item.attachments:
                        attachment_data.append({
                            'file_path': str(att.file_path),
                            'title': att.title,
                            'notes': att.notes,
                            'is_screenshot': att.is_screenshot
                        })

                    # Store attachment metadata (you may want to add a separate field to DB)
                    if attachment_data:
                        import json
                        db_process.notes += f"\n\n__ATTACHMENTS__:{json.dumps(attachment_data)}"

                _LOGGER.info(f"Saved {len(self._items)} processes to database")

        except Exception as e:
            _LOGGER.error(f"Failed to save processes data: {e}")

    def _copy_attachments_to_storage(self, item_id: int, attachments: List[AttachmentMetadata]) -> List[
        AttachmentMetadata]:
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

    def clear_fields(self) -> None:
        """Clear all processes and form fields."""
        section = self._get_section_name()
        deleted_files = FileManager.cleanup_section_files(section)
        _LOGGER.info(f"Cleaned up {deleted_files} files during clear")

        # Clear the table
        self.table.setRowCount(0)

        # Clear the items list
        self._items.clear()

        # Clear the entry form
        self._clear_entry_form()

        # Reset editing state
        self._editing_index = None
        self._original_item = None
        self.btn_add.setText("Add Process")
        self.btn_cancel.setVisible(False)

        _LOGGER.info("Cleared all processes and form fields")

    # ------------- Scrollbar style -------------

    def _set_scrollbar_stealth(self, stealth: bool):
        sb = self._scroller.verticalScrollBar()
        if stealth:
            sb.setStyleSheet("""
                QScrollBar:vertical {
                    background: #F3F4F6;
                    width: 12px;
                    margin: 8px 2px 8px 0;
                }
                QScrollBar::handle:vertical {
                    background: #F3F4F6;
                    border-radius: 6px;
                    min-height: 24px;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; width: 0; }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: #F3F4F6; }
            """)
        else:
            sb.setStyleSheet("""
                QScrollBar:vertical {
                    background: transparent;
                    width: 12px;
                    margin: 8px 2px 8px 0;
                }
                QScrollBar::handle:vertical {
                    background: #D1D5DB;
                    border-radius: 6px;
                    min-height: 24px;
                }
                QScrollBar::handle:vertical:hover { background: #9CA3AF; }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; width: 0; }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
            """)
        sb.style().unpolish(sb);
        sb.style().polish(sb);
        sb.update()

    # ------------- Enhanced attachment methods -------------

    def _attach_files(self):
        """Open enhanced attachment dialog"""
        dialog = AttachmentDialog(self)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            attachment = dialog.get_attachment()
            if attachment and attachment not in self._entry_attachments:
                self._add_attachment_chip(attachment)

    def _add_attachment_chip(self, attachment: AttachmentMetadata):
        """Add an attachment chip to the UI"""
        chip = AttachmentChip(attachment)
        chip.removed.connect(self._remove_attachment_chip)
        chip.edit_requested.connect(self._edit_attachment)
        self.chips_flow.addWidget(chip)
        self._entry_attachments.append(attachment)

    def _remove_attachment_chip(self, attachment: AttachmentMetadata):
        """Remove attachment chip and data"""
        # Remove chip widget
        for i in reversed(range(self.chips_flow.count())):
            item = self.chips_flow.itemAt(i)
            w = item.widget()
            if isinstance(w, AttachmentChip) and w.attachment == attachment:
                self.chips_flow.takeAt(i)
                w.deleteLater()
                break

        # Remove from attachments list
        self._entry_attachments = [att for att in self._entry_attachments if att != attachment]

    def _edit_attachment(self, attachment: AttachmentMetadata):
        """Edit an existing attachment's metadata"""
        dialog = AttachmentDialog(self, attachment)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            updated_attachment = dialog.get_attachment()
            if updated_attachment:
                # Find and update the attachment in our list
                for i, att in enumerate(self._entry_attachments):
                    if att == attachment:
                        self._entry_attachments[i] = updated_attachment
                        break

                # Update the chip
                for i in range(self.chips_flow.count()):
                    item = self.chips_flow.itemAt(i)
                    w = item.widget()
                    if isinstance(w, AttachmentChip) and w.attachment == attachment:
                        # Replace the chip
                        self.chips_flow.takeAt(i)
                        w.deleteLater()

                        new_chip = AttachmentChip(updated_attachment)
                        new_chip.removed.connect(self._remove_attachment_chip)
                        new_chip.edit_requested.connect(self._edit_attachment)

                        # Insert at the same position
                        self.chips_flow.insertWidget(i, new_chip)
                        break

    def _capture_new_screenshot(self):
        """Capture a screenshot for the current entry"""
        idx = self._selected_row()
        if idx < 0:
            idx = -1
        self.requestScreenshot.emit(idx)

    def _add_process(self):
        """Add or update a process with enhanced attachment support and database saving"""
        # Title can be empty; if so, generate a friendly default
        title = self.title_edit.text().strip()
        if not title:
            title = f"Untitled — {QtCore.QDateTime.currentDateTime().toString('yyyy-MM-dd hh:mm')}"

        notes = self.notes_edit.toPlainText().strip()

        # Create/update item with new attachment structure
        item = ProcessItem(
            title=title,
            notes=notes,
            attachments=self._entry_attachments.copy()  # Copy the list of AttachmentMetadata objects
        )

        if self._editing_index is not None:
            # We're updating an existing item
            insert_pos = min(self._editing_index, len(self._items))
            self._items.insert(insert_pos, item)
            self.table.insertRow(insert_pos)

            # Populate the row
            self._populate_table_row(insert_pos, item)

            # Select the updated row
            self.table.selectRow(insert_pos)
            self.table.scrollToItem(self.table.item(insert_pos, 0), QtWidgets.QAbstractItemView.PositionAtCenter)

            # Reset editing mode
            self._editing_index = None
            self._original_item = None
            self.btn_add.setText("Add Process")
            self.btn_cancel.setVisible(False)

        else:
            # Adding new item
            self._items.append(item)
            self._append_row(item)

            # Select and reveal the newly added row
            new_row = self.table.rowCount() - 1
            if new_row >= 0:
                self.table.selectRow(new_row)
                self.table.scrollToItem(self.table.item(new_row, 0), QtWidgets.QAbstractItemView.PositionAtCenter)

        # Save to database after any add/update
        self._save_processes_data()

        # Reset entry form
        self._clear_entry_form()

    # ------------- Table helpers - Updated for new data structure -------------

    def _append_row(self, item: ProcessItem):
        """Add a row to the table"""
        row = self.table.rowCount()
        self.table.insertRow(row)
        self._populate_table_row(row, item)

    def _populate_table_row(self, row: int, item: ProcessItem):
        """Populate a table row with process item data"""

        def _cell(text: str) -> QtWidgets.QTableWidgetItem:
            it = QtWidgets.QTableWidgetItem(text)
            it.setFlags(it.flags() ^ QtCore.Qt.ItemIsEditable)
            return it

        preview = (item.notes[:80] + "…") if item.notes and len(item.notes) > 80 else (item.notes or "")

        # Show ALL attachments (documents AND screenshots)
        files_text = ", ".join(att.display_name for att in item.attachments) if item.attachments else ""

        self.table.setItem(row, 0, _cell(item.title))
        self.table.setItem(row, 1, _cell(preview))
        self.table.setItem(row, 2, _cell(files_text))

    def _selected_row(self) -> int:
        """Get the currently selected row index"""
        sel = self.table.selectionModel().selectedRows()
        return sel[0].row() if sel else -1

    def _cancel_editing(self):
        """Cancel current editing and restore the original item to the table"""
        if self._editing_index is None or self._original_item is None:
            return

        # Check if there are unsaved changes
        if self._has_unsaved_changes():
            reply = QtWidgets.QMessageBox.question(
                self,
                "Cancel Edit",
                "Are you sure you want to cancel? Any changes will be lost.",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            if reply != QtWidgets.QMessageBox.Yes:
                return

        # Restore the original item back to the table
        insert_pos = min(self._editing_index, len(self._items))
        self._items.insert(insert_pos, self._original_item)
        self.table.insertRow(insert_pos)
        self._populate_table_row(insert_pos, self._original_item)

        # Select the restored row
        self.table.selectRow(insert_pos)
        self.table.scrollToItem(self.table.item(insert_pos, 0), QtWidgets.QAbstractItemView.PositionAtCenter)

        # Clear the entry form and reset editing state
        self._clear_entry_form()
        self._editing_index = None
        self._original_item = None
        self.btn_add.setText("Add Process")
        self.btn_cancel.setVisible(False)

    def _delete_selected(self):
        """Delete the selected process and save to database"""
        idx = self._selected_row()
        if idx < 0:
            return

        if QtWidgets.QMessageBox.question(self, "Delete Process",
                                          "Remove the selected process?") == QtWidgets.QMessageBox.Yes:
            item = self._items[idx]
            self._cleanup_item_files(item.attachments)

            self.table.removeRow(idx)
            del self._items[idx]

            # Save to database after deletion
            self._save_processes_data()

            # If we were editing an item that got deleted by index shift, reset editing state
            if self._editing_index is not None and self._editing_index >= idx:
                if self._editing_index == idx:
                    self._editing_index = None
                    self._original_item = None
                    self.btn_add.setText("Add Process")
                    self.btn_cancel.setVisible(False)
                else:
                    self._editing_index -= 1

    def _load_process_for_editing(self):
        """Load selected process into entry form and remove from table for editing"""
        idx = self._selected_row()
        if idx < 0:
            return

        # Check if entry form has unsaved changes
        if self._has_unsaved_changes():
            reply = QtWidgets.QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes in the entry form. Load the selected process anyway?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            if reply != QtWidgets.QMessageBox.Yes:
                return

        item = self._items[idx]

        # Clear current form state
        self._clear_entry_form()

        # Load item data into form
        self.title_edit.setText(item.title)
        self.notes_edit.setText(item.notes)

        # Load attachments and recreate chips
        for attachment in item.attachments:
            if attachment.file_path.exists():
                self._add_attachment_chip(attachment)

        # Set editing mode and store original
        self._editing_index = idx
        self._original_item = ProcessItem(
            title=item.title,
            notes=item.notes,
            attachments=item.attachments.copy()
        )

        # Remove from table and items list
        self.table.removeRow(idx)
        del self._items[idx]

        # Update UI for editing mode
        self.btn_add.setText("Update Process")
        self.btn_cancel.setVisible(True)

    def _has_unsaved_changes(self) -> bool:
        """Check if the entry form has unsaved data"""
        return (
            bool(self.title_edit.text().strip()) or
            bool(self.notes_edit.toPlainText().strip()) or
            bool(self._entry_attachments)
        )

    def _clear_entry_form(self):
        """Clear all entry form fields and state"""
        self.title_edit.clear()
        self.notes_edit.clear()

        # Clear chips
        for i in reversed(range(self.chips_flow.count())):
            it = self.chips_flow.itemAt(i)
            w = it.widget() if it else None
            self.chips_flow.takeAt(i)
            if w:
                w.deleteLater()

        # Clear attachment list
        self._entry_attachments.clear()

    def _table_context_menu(self, pos: QtCore.QPoint):
        """Show context menu for table"""
        idx = self.table.indexAt(pos).row()
        if idx < 0:
            return
        menu = QtWidgets.QMenu(self)
        act_open = menu.addAction("Open Process")
        act_del = menu.addAction("Delete")
        act = menu.exec(self.table.viewport().mapToGlobal(pos))
        if act == act_open:
            self._load_process_for_editing()
        elif act == act_del:
            self._delete_selected()

    # ------------- Screenshot callbacks - Updated for new data structure -------------

    @QtCore.Slot(int)
    def _launch_screenshot_for_row(self, row_idx: int):
        """Launch screenshot tool"""
        self._pending_row_idx = row_idx
        self._shot_tool.start()

    @QtCore.Slot(str, dict)
    def _on_screenshot_saved(self, file_path: str, metadata: dict):
        """Handle screenshot saved event with enhanced metadata"""
        idx = getattr(self, "_pending_row_idx", -1)
        screenshot_path = Path(file_path)

        if not screenshot_path.exists():
            return

        # Extract title, description and notes from metadata
        title = metadata.get('title',
                             '') or f"Screenshot {QtCore.QDateTime.currentDateTime().toString('yyyy-MM-dd hh:mm')}"
        description = metadata.get('description', '')
        markers = metadata.get('markers', [])

        # Combine description and marker notes
        notes_parts = []
        if description.strip():
            notes_parts.append(description.strip())

        # Add marker notes
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

            # Check if already exists
            if screenshot_attachment not in self._entry_attachments:
                self._add_attachment_chip(screenshot_attachment)

        else:
            # Screenshot for existing process
            if 0 <= idx < len(self._items):
                screenshot_attachment = AttachmentMetadata(
                    file_path=screenshot_path,
                    title=title,
                    notes=notes_text,
                    is_screenshot=True
                )

                self._items[idx].attachments.append(screenshot_attachment)

                # Update table display
                self._populate_table_row(idx, self._items[idx])
