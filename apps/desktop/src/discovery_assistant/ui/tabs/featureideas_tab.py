from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any
import json

from PySide6 import QtWidgets, QtCore, QtGui
from discovery_assistant.ui.widgets.draggable_table import DraggableTableWidget
from discovery_assistant.baselogger import logging
from discovery_assistant.ui.widgets.info import InfoSection
from discovery_assistant.ui.info_text import FEATURE_IDEAS_INFO
from discovery_assistant.ui.widgets.screenshot_tool import ScreenshotTool
from discovery_assistant.storage import DatabaseSession, FileManager, get_files_dir, FeatureIdea as DBFeatureIdea

_LOGGER = logging.getLogger("DISCOVERY.ui.tabs.feature_ideas_tab")


# -------------------------
# Data models
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
class ProcessStep:
    """A single step in the automation process"""
    description: str
    order: int
    requires_data_access: bool = False
    data_source_ref: str = ""
    involves_decision_logic: bool = False

    def __post_init__(self):
        self.description = self.description.strip()
        self.data_source_ref = self.data_source_ref.strip()


@dataclass
class FeatureIdea:
    """A feature idea with problem description and implementation steps"""
    title: str
    problem_description: str = ""
    expected_outcome: str = ""
    steps: List[ProcessStep] = field(default_factory=list)
    attachments: List[AttachmentMetadata] = field(default_factory=list)

    @property
    def step_count(self) -> int:
        return len(self.steps)

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
        super().setGeometry(rect);
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
        cancel_btn.clicked.connect(self.reject)

        attach_btn = QtWidgets.QPushButton("Attach")
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
# Process Steps Widget
# -------------------------

class ProcessStepsWidget(QtWidgets.QWidget):
    """Widget for managing implementation steps"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Header
        header_widget = QtWidgets.QWidget()
        header_widget.setStyleSheet("background: transparent; border: none;")
        header_layout = QtWidgets.QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)

        steps_label = QtWidgets.QLabel("Implementation Steps")
        steps_label.setStyleSheet("font-size:13px; color:#334155; font-weight:500;")

        help_text = QtWidgets.QLabel("(Describe each step needed to accomplish this automation)")
        help_text.setStyleSheet("font-size:11px; color:#64748B; font-style:italic;")

        header_layout.addWidget(steps_label)
        header_layout.addWidget(help_text)
        header_layout.addStretch()
        layout.addWidget(header_widget)

        # Steps container
        self.steps_container = QtWidgets.QWidget()
        self.steps_layout = QtWidgets.QVBoxLayout(self.steps_container)
        self.steps_layout.setContentsMargins(0, 0, 0, 0)
        self.steps_layout.setSpacing(6)

        # Add container directly without scroll area
        layout.addWidget(self.steps_container)

        # Add step button
        add_btn = QtWidgets.QPushButton("+ Add Step")
        add_btn.setStyleSheet("""
            QPushButton {
                background:#F8FAFC;
                color:#374151;
                border:1px dashed #D1D5DB;
                border-radius:6px;
                padding:8px 12px;
            }
            QPushButton:hover { background:#F1F5F9; }
        """)
        add_btn.clicked.connect(self._add_step)
        layout.addWidget(add_btn)

    def _add_step(self):
        step_widget = self._create_step_widget(self.steps_layout.count())
        self.steps_layout.addWidget(step_widget)
        if hasattr(step_widget, '_step_text'):
            step_widget._step_text.setFocus()

    def _create_step_widget(self, index: int) -> QtWidgets.QWidget:
        step_widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(step_widget)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        # Main row
        main_row = QtWidgets.QHBoxLayout()

        # Step number
        step_num = QtWidgets.QLabel(f"{index + 1}")
        step_num.setStyleSheet("font-weight:600; color:#FFFFFF; background-color:#A5BBCF; font-size:13px;")
        step_num.setFixedWidth(20)
        step_num.setAlignment(QtCore.Qt.AlignCenter)
        main_row.addWidget(step_num)

        # Description
        step_text = QtWidgets.QTextEdit()
        step_text.setPlaceholderText("Describe what happens in this step...")
        step_text.setMinimumHeight(60)  # Start with reasonable minimum
        step_text.setMaximumHeight(200)  # Prevent it from getting too huge
        step_text.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        step_text.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        _force_dark_text(step_text)

        # Auto-resize functionality
        def adjust_height():
            # Get the document height
            doc_height = step_text.document().size().height()
            # Add some padding for margins/borders
            new_height = int(doc_height) + 20
            # Constrain between min and max
            new_height = max(60, min(200, new_height))
            step_text.setFixedHeight(new_height)

        # Connect to text changes
        step_text.textChanged.connect(adjust_height)
        # Set initial height
        adjust_height()

        main_row.addWidget(step_text)

        # Remove button
        remove_btn = QtWidgets.QToolButton()
        remove_btn.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_TitleBarCloseButton))
        remove_btn.setIconSize(QtCore.QSize(14, 14))
        remove_btn.clicked.connect(lambda: self._remove_step(step_widget))
        main_row.addWidget(remove_btn)

        layout.addLayout(main_row)

        # Data dependency section
        data_checkbox = QtWidgets.QCheckBox("Requires data access from a specific source")
        data_checkbox.setStyleSheet("color: #6B7280; font-size: 11px; border: none")
        layout.addWidget(data_checkbox)

        # Data details (hidden initially)
        data_details = QtWidgets.QWidget()
        data_details.setVisible(False)
        data_layout = QtWidgets.QHBoxLayout(data_details)
        data_layout.setContentsMargins(16, 4, 0, 4)

        source_label = QtWidgets.QLabel("Data source:")
        source_label.setStyleSheet('color: #6B7280; font-size: 11px; border: none')
        data_layout.addWidget(source_label)
        data_ref_edit = QtWidgets.QLineEdit()
        data_ref_edit.setPlaceholderText("Reference (e.g., customer_db)")
        _force_dark_text(data_ref_edit)
        data_layout.addWidget(data_ref_edit)

        decision_checkbox = QtWidgets.QCheckBox("Involves decision logic")
        decision_checkbox.setStyleSheet("color: #6B7280; font-size: 11px; border: none")
        data_layout.addWidget(decision_checkbox)
        data_layout.addSpacing(15)

        layout.addWidget(data_details)

        # Connect checkbox to show/hide details
        data_checkbox.toggled.connect(data_details.setVisible)

        # Store references
        step_widget._step_text = step_text
        step_widget._data_checkbox = data_checkbox
        step_widget._data_ref_edit = data_ref_edit
        step_widget._decision_checkbox = decision_checkbox
        step_widget._step_num = step_num

        step_widget.setStyleSheet("background:#FAFAFA; border:1px solid #E5E7EB; border-radius:6px;")
        return step_widget

    def _remove_step(self, step_widget: QtWidgets.QWidget):
        index = self.steps_layout.indexOf(step_widget)
        if index >= 0:
            self.steps_layout.removeWidget(step_widget)
            step_widget.deleteLater()
            self._renumber_steps()

    def _renumber_steps(self):
        for i in range(self.steps_layout.count()):
            widget = self.steps_layout.itemAt(i).widget()
            if widget and hasattr(widget, '_step_num'):
                widget._step_num.setText(f"{i + 1}.")

    def get_steps(self) -> List[ProcessStep]:
        steps = []
        for i in range(self.steps_layout.count()):
            widget = self.steps_layout.itemAt(i).widget()
            if widget and hasattr(widget, '_step_text'):
                text = widget._step_text.toPlainText().strip()
                if text:
                    step = ProcessStep(
                        description=text,
                        order=i + 1,
                        requires_data_access=widget._data_checkbox.isChecked(),
                        data_source_ref=widget._data_ref_edit.text().strip(),
                        involves_decision_logic=widget._decision_checkbox.isChecked()
                    )
                    steps.append(step)
        return steps

    def set_steps(self, steps: List[ProcessStep]):
        # Clear existing
        while self.steps_layout.count():
            child = self.steps_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Add steps
        for step in steps:
            widget = self._create_step_widget(step.order - 1)
            widget._step_text.setText(step.description)
            widget._data_checkbox.setChecked(step.requires_data_access)
            widget._data_ref_edit.setText(step.data_source_ref)
            widget._decision_checkbox.setChecked(step.involves_decision_logic)
            self.steps_layout.addWidget(widget)

    def clear(self):
        while self.steps_layout.count():
            child = self.steps_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()


# -------------------------
# Main Feature Ideas Tab
# -------------------------

class FeatureIdeasTab(QtWidgets.QWidget):
    requestScreenshot = QtCore.Signal(int)  # row index

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None, policy_enforcer=None) -> None:
        super().__init__(parent)
        self._policy_enforcer = policy_enforcer
        _LOGGER.info("FeatureIdeasTab initialized")

        # ---- scroller ----
        scroller = QtWidgets.QScrollArea(self)
        scroller.setObjectName("FeatureIdeasScroll")
        scroller.setWidgetResizable(True)
        scroller.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroller.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        scroller.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroller.setStyleSheet("""
            QScrollArea#FeatureIdeasScroll { background: transparent; border: none; }
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
        card.setObjectName("FeatureIdeasCard")
        card.setStyleSheet("""
            QFrame#FeatureIdeasCard {
                background:#FFFFFF;
                border:1px solid #E5E7EB;
                border-radius:12px;
            }
            QFrame#FeatureIdeasCard QLabel { background: transparent; }
            QFrame#FeatureIdeasCard QWidget#FeatureIdeasForm { background: transparent; }
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
            title="Feature Ideas",
            subtitle="Describe automation opportunities by outlining step-by-step implementation processes.",
            info_html=FEATURE_IDEAS_INFO,
            icon_size_px=28,
            parent=card,
        )
        card_layout.addWidget(section)
        section.bind_scrollarea(self._scroller)

        # ---- form ----
        form_host = QtWidgets.QWidget(card)
        form_host.setObjectName("FeatureIdeasForm")
        form = _StackedLabelForm(form_host)

        # Feature title
        self.title_edit = QtWidgets.QLineEdit()
        self.title_edit.setPlaceholderText("e.g., Automated Email Response System")
        _force_dark_text(self.title_edit)
        form.add_row("Feature Title", self.title_edit)

        # Problem description
        self.problem_edit = QtWidgets.QTextEdit()
        self.problem_edit.setPlaceholderText("What specific problem does this solve?")
        self.problem_edit.setMinimumHeight(80)
        _force_dark_text(self.problem_edit)
        form.add_row("Problem Description", self.problem_edit)

        card_layout.addWidget(form_host, 1)

        # ---- Steps widget ----
        self.steps_widget = ProcessStepsWidget()
        card_layout.addWidget(self.steps_widget, 0)

        # ---- Expected outcome form ----
        outcome_host = QtWidgets.QWidget(card)
        outcome_host.setObjectName("FeatureIdeasForm")
        outcome_form = _StackedLabelForm(outcome_host)

        self.outcome_edit = QtWidgets.QTextEdit()
        self.outcome_edit.setPlaceholderText("How would you know this automation is working successfully?")
        self.outcome_edit.setMinimumHeight(60)
        _force_dark_text(self.outcome_edit)
        outcome_form.add_row("Expected Outcome", self.outcome_edit)

        card_layout.addWidget(outcome_host, 1)

        # ---- actions row ----
        actions_row = QtWidgets.QHBoxLayout()
        actions_row.setSpacing(8)

        self.btn_attach = QtWidgets.QPushButton("Attach…")
        self.btn_attach.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_capture = QtWidgets.QPushButton("Capture Screenshot")
        self.btn_capture.setCursor(QtCore.Qt.PointingHandCursor)
        actions_row.addWidget(self.btn_attach, 0, QtCore.Qt.AlignLeft)
        actions_row.addWidget(self.btn_capture, 0, QtCore.Qt.AlignLeft)
        actions_row.addStretch(1)

        # Cancel button (hidden by default)
        self.btn_cancel = QtWidgets.QPushButton("Cancel Edit")
        self.btn_cancel.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_cancel.setVisible(False)
        actions_row.addWidget(self.btn_cancel, 0, QtCore.Qt.AlignRight)

        self.btn_add = QtWidgets.QPushButton("Add Feature Idea")
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
        # Create draggable table directly
        self.table = DraggableTableWidget(0, 4, card)
        print(f"Table type: {type(self.table)}")
        print(f"Has rowsReordered signal: {hasattr(self.table, 'rowsReordered')}")
        self.table.setObjectName("FeatureIdeasTable")
        self.table.setHorizontalHeaderLabels(["Title", "Problem & Steps", "Expected Outcome", "Attachments"])

        # Configure headers
        for c in range(self.table.columnCount()):
            item = self.table.horizontalHeaderItem(c)
            if item:
                item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        hdr = self.table.horizontalHeader()
        hdr.setStretchLastSection(False)
        hdr.setSectionResizeMode(0, QtWidgets.QHeaderView.Interactive)  # Title - user resizable
        hdr.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)  # Problem & Steps - stretches
        hdr.setSectionResizeMode(2, QtWidgets.QHeaderView.Interactive)  # Expected Outcome - user resizable
        hdr.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)  # Attachments - auto-size

        # Set minimum column widths
        self.table.setColumnWidth(0, 180)  # Title
        self.table.setColumnWidth(2, 150)  # Expected Outcome

        hdr.setDefaultAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        hdr.setHighlightSections(False)

        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setAutoScroll(False)
        self.table.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        # Table styling
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

        pal = self.table.palette()
        pal.setColor(QtGui.QPalette.Base, QtGui.QColor("#FFFFFF"))
        pal.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor("#C7D1DA"))
        pal.setColor(QtGui.QPalette.Text, QtGui.QColor("#0F172A"))
        pal.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor("#0F172A"))
        self.table.setPalette(pal)
        self.table.rowsReordered.connect(self._handle_row_reorder)
        card_layout.addWidget(self.table)

        # row actions
        row_actions = QtWidgets.QHBoxLayout()
        row_actions.addStretch(1)
        self.btn_open_doc = QtWidgets.QPushButton("Edit Feature Idea")
        self.btn_open_doc.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_delete = QtWidgets.QPushButton("Delete")
        self.btn_delete.setCursor(QtCore.Qt.PointingHandCursor)
        row_actions.addWidget(self.btn_open_doc)
        row_actions.addWidget(self.btn_delete)
        card_layout.addLayout(row_actions)

        # mount scroller
        root_layout = QtWidgets.QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(scroller)

        # state
        self._items: list[FeatureIdea] = []
        self._entry_attachments: list[AttachmentMetadata] = []
        self._editing_index: Optional[int] = None
        self._original_item: Optional[FeatureIdea] = None

        # initial scrollbar mode
        self._set_scrollbar_stealth(True)
        section.toggled.connect(lambda open_: self._set_scrollbar_stealth(not open_))

        # wire up buttons
        self.btn_attach.clicked.connect(self._attach_files)
        self.btn_capture.clicked.connect(self._capture_new_screenshot)
        self.btn_add.clicked.connect(self._add_feature_idea)
        self.btn_open_doc.clicked.connect(self._load_feature_idea_for_editing)
        self.btn_delete.clicked.connect(self._delete_selected)
        self.btn_cancel.clicked.connect(self._cancel_editing)

        self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._table_context_menu)

        # Screenshot tool
        self._shot_tool = ScreenshotTool(self)
        self.requestScreenshot.connect(self._launch_screenshot_for_row)
        self._shot_tool.screenshotSaved.connect(self._on_screenshot_saved)

        self._load_feature_ideas_data()

    def _get_section_name(self) -> str:
        return "feature_ideas"

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

    def _load_feature_ideas_data(self) -> None:
        """Load existing feature ideas from database into the table."""
        try:
            with DatabaseSession() as session:
                db_feature_ideas = session.query(DBFeatureIdea).order_by(DBFeatureIdea.priority_rank.asc()).all()

                for db_idea in db_feature_ideas:
                    # Parse steps and outcome from expected_outcome field
                    steps = []
                    actual_outcome = ""
                    attachments = []  # Initialize here

                    if db_idea.expected_outcome:
                        try:
                            # Try to parse as JSON first (for new format with steps)
                            outcome_data = json.loads(db_idea.expected_outcome)
                            if isinstance(outcome_data, dict):
                                # New format: JSON with 'outcome' and 'steps'
                                actual_outcome = outcome_data.get('outcome', '')
                                steps_list = outcome_data.get('steps', [])
                                for step_dict in steps_list:
                                    step = ProcessStep(
                                        description=step_dict.get('description', ''),
                                        order=step_dict.get('order', 0),
                                        requires_data_access=step_dict.get('requires_data_access', False),
                                        data_source_ref=step_dict.get('data_source_ref', ''),
                                        involves_decision_logic=step_dict.get('involves_decision_logic', False)
                                    )
                                    steps.append(step)

                                # Load attachments from the outcome data - MOVE THIS HERE
                                attachment_data = outcome_data.get('attachments', [])
                                for att_dict in attachment_data:
                                    file_path = Path(att_dict['file_path'])
                                    if FileManager.validate_file_exists(file_path):
                                        attachments.append(AttachmentMetadata(
                                            file_path=file_path,
                                            title=att_dict.get('title', ''),
                                            notes=att_dict.get('notes', ''),
                                            is_screenshot=att_dict.get('is_screenshot', False)
                                        ))
                                    else:
                                        _LOGGER.warning(f"Missing attachment file: {file_path}")
                            else:
                                # Unexpected JSON format
                                actual_outcome = str(outcome_data)
                        except (json.JSONDecodeError, TypeError):
                            # If it's not JSON, treat as plain text outcome (legacy format)
                            actual_outcome = db_idea.expected_outcome

                    # Convert database model to dataclass
                    feature_idea = FeatureIdea(
                        title=db_idea.feature_title,
                        problem_description=db_idea.problem_description or "",
                        expected_outcome=actual_outcome,
                        steps=steps,
                        attachments=attachments
                    )

                    self._items.append(feature_idea)
                    self._append_row(feature_idea)

                _LOGGER.info(f"Loaded {len(db_feature_ideas)} feature ideas from database")

        except Exception as e:
            _LOGGER.error(f"Failed to load feature ideas data: {e}")

    def _save_feature_ideas_data(self) -> None:
        """Save current feature ideas list to database."""
        try:
            with DatabaseSession() as session:
                # Clear existing feature ideas
                deleted_count = session.query(DBFeatureIdea).count()
                session.query(DBFeatureIdea).delete()
                _LOGGER.info(f"Deleted {deleted_count} existing feature ideas")

                # Save each feature idea with priority rank based on order
                for rank, idea in enumerate(self._items, 1):
                    # Create a combined data structure for steps and outcome
                    outcome_data = {
                        'outcome': idea.expected_outcome,
                        'steps': []
                    }

                    # Serialize steps
                    for step in idea.steps:
                        step_dict = {
                            'description': step.description,
                            'order': step.order,
                            'requires_data_access': step.requires_data_access,
                            'data_source_ref': step.data_source_ref,
                            'involves_decision_logic': step.involves_decision_logic
                        }
                        outcome_data['steps'].append(step_dict)

                    # Store as JSON in expected_outcome field
                    try:
                        outcome_json = json.dumps(outcome_data)
                    except (TypeError, ValueError) as e:
                        _LOGGER.warning(f"Failed to serialize feature idea data: {e}")
                        outcome_json = json.dumps({'outcome': idea.expected_outcome, 'steps': []})

                    db_feature_idea = DBFeatureIdea(
                        feature_title=idea.title,
                        priority_rank=rank,
                        problem_description=idea.problem_description,
                        expected_outcome=outcome_json  # Store JSON with steps and outcome
                    )
                    session.add(db_feature_idea)
                    session.flush()  # Get the ID for file management

                    # CRITICAL: Copy attachments to storage and update paths
                    if idea.attachments:
                        updated_attachments = self._copy_attachments_to_storage(
                            db_feature_idea.id, idea.attachments
                        )
                        # Update the idea with new paths
                        idea.attachments = updated_attachments

                        # Save attachment metadata
                        outcome_data['attachments'] = []
                        for att in idea.attachments:
                            outcome_data['attachments'].append({
                                'file_path': str(att.file_path),
                                'title': att.title,
                                'notes': att.notes,
                                'is_screenshot': att.is_screenshot
                            })

                        # Update the stored JSON
                        db_feature_idea.expected_outcome = json.dumps(outcome_data)

                    _LOGGER.info(f"Added feature idea: {idea.title}")

        except Exception as e:
            _LOGGER.error(f"Failed to save feature ideas data: {e}")

    def clear_fields(self) -> None:
        """Clear all feature ideas and form fields."""
        # Clear the table
        self.table.setRowCount(0)

        # Clean up all files for this section
        section = self._get_section_name()
        deleted_files = FileManager.cleanup_section_files(section)
        _LOGGER.info(f"Cleaned up {deleted_files} files during clear")

        # Clear the items list
        self._items.clear()

        # Clear the entry form
        self._clear_entry_form()

        # Reset editing state
        self._editing_index = None
        self._original_item = None
        self.btn_add.setText("Add Feature Idea")
        self.btn_cancel.setVisible(False)

        _LOGGER.info("Cleared all feature ideas and form fields")

    # ------------- Drag-drop handling -------------

    def _handle_row_reorder(self, old_index: int, new_index: int):
        """Handle when rows are reordered via drag-and-drop"""
        print(f"Row reorder called: {old_index} -> {new_index}")

        # Reorder the items list
        item = self._items.pop(old_index)
        self._items.insert(new_index, item)

        # Save to database after reordering
        self._save_feature_ideas_data()

        # Repopulate table
        self._repopulate_all_rows()

        # Select the moved row
        self.table.selectRow(new_index)

    # ------------- Scrollbar style -------------

    def _set_scrollbar_stealth(self, stealth: bool):
        sb = self._scroller.verticalScrollBar()
        sb.style().unpolish(sb)
        sb.style().polish(sb)
        sb.update()

    # ------------- Attachment methods -------------

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
        for i in reversed(range(self.chips_flow.count())):
            item = self.chips_flow.itemAt(i)
            w = item.widget()
            if isinstance(w, AttachmentChip) and w.attachment == attachment:
                self.chips_flow.takeAt(i)
                w.deleteLater()
                break
        self._entry_attachments = [att for att in self._entry_attachments if att != attachment]

    def _edit_attachment(self, attachment: AttachmentMetadata):
        """Edit an existing attachment's metadata"""
        dialog = AttachmentDialog(self, attachment)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            updated_attachment = dialog.get_attachment()
            if updated_attachment:
                for i, att in enumerate(self._entry_attachments):
                    if att == attachment:
                        self._entry_attachments[i] = updated_attachment
                        break

                for i in range(self.chips_flow.count()):
                    item = self.chips_flow.itemAt(i)
                    w = item.widget()
                    if isinstance(w, AttachmentChip) and w.attachment == attachment:
                        self.chips_flow.takeAt(i)
                        w.deleteLater()

                        new_chip = AttachmentChip(updated_attachment)
                        new_chip.removed.connect(self._remove_attachment_chip)
                        new_chip.edit_requested.connect(self._edit_attachment)
                        self.chips_flow.insertWidget(i, new_chip)
                        break

    def _capture_new_screenshot(self):
        """Capture a screenshot for the current entry"""
        idx = self._selected_row()
        if idx < 0:
            idx = -1
        self.requestScreenshot.emit(idx)

    def _add_feature_idea(self):
        """Add or update a feature idea with database saving"""
        title = self.title_edit.text().strip()
        if not title:
            title = f"Untitled Feature — {QtCore.QDateTime.currentDateTime().toString('yyyy-MM-dd hh:mm')}"

        problem_description = self.problem_edit.toPlainText().strip()
        expected_outcome = self.outcome_edit.toPlainText().strip()
        steps = self.steps_widget.get_steps()

        item = FeatureIdea(
            title=title,
            problem_description=problem_description,
            expected_outcome=expected_outcome,
            steps=steps,
            attachments=self._entry_attachments.copy()
        )

        if self._editing_index is not None:
            # Updating existing item
            insert_pos = min(self._editing_index, len(self._items))
            self._items.insert(insert_pos, item)
            self.table.insertRow(insert_pos)
            self._populate_table_row(insert_pos, item)
            self.table.selectRow(insert_pos)
            self.table.scrollToItem(self.table.item(insert_pos, 0), QtWidgets.QAbstractItemView.PositionAtCenter)

            # Reset editing mode
            self._editing_index = None
            self._original_item = None
            self.btn_add.setText("Add Feature Idea")
            self.btn_cancel.setVisible(False)
        else:
            # Adding new item
            self._items.append(item)
            self._append_row(item)
            new_row = self.table.rowCount() - 1
            if new_row >= 0:
                self.table.selectRow(new_row)
                self.table.scrollToItem(self.table.item(new_row, 0), QtWidgets.QAbstractItemView.PositionAtCenter)

        # Save to database after any add/update
        self._save_feature_ideas_data()

        self._clear_entry_form()

    # ------------- Table helpers -------------

    def _append_row(self, item: FeatureIdea):
        """Add a row to the table"""
        row = self.table.rowCount()
        self.table.insertRow(row)
        self._populate_table_row(row, item)

    def _populate_table_row(self, row: int, item: FeatureIdea):
        """Populate a table row with feature idea data"""

        def _cell(text: str) -> QtWidgets.QTableWidgetItem:
            it = QtWidgets.QTableWidgetItem(text)
            it.setFlags(it.flags() ^ QtCore.Qt.ItemIsEditable)
            return it

        # Problem + steps summary
        problem_preview = (item.problem_description[:60] + "…") if len(
            item.problem_description) > 60 else item.problem_description

        # Show step count and data dependencies
        step_info_parts = []
        if item.steps:
            step_info_parts.append(f"{len(item.steps)} steps")

            # Count data dependencies
            data_deps = set()
            decision_steps = 0
            for step in item.steps:
                if step.requires_data_access and step.data_source_ref:
                    data_deps.add(step.data_source_ref)
                if step.involves_decision_logic:
                    decision_steps += 1

            if data_deps:
                step_info_parts.append(f"{len(data_deps)} data sources")
            if decision_steps:
                step_info_parts.append(f"{decision_steps} decisions")

        steps_preview = " | " + ", ".join(step_info_parts) if step_info_parts else ""
        problem_and_steps = problem_preview + steps_preview

        outcome_preview = (item.expected_outcome[:50] + "…") if len(
            item.expected_outcome) > 50 else item.expected_outcome
        attachments_text = ", ".join(att.display_name for att in item.attachments) if item.attachments else ""

        self.table.setItem(row, 0, _cell(item.title))
        self.table.setItem(row, 1, _cell(problem_and_steps))
        self.table.setItem(row, 2, _cell(outcome_preview))
        self.table.setItem(row, 3, _cell(attachments_text))

    def _repopulate_all_rows(self):
        """Refresh table display after drag-and-drop reordering"""
        self.table.setRowCount(0)
        for item in self._items:
            self._append_row(item)

        # Maintain selection if possible
        if self.table.rowCount() > 0:
            self.table.selectRow(0)

    def _selected_row(self) -> int:
        """Get the currently selected row index"""
        sel = self.table.selectionModel().selectedRows()
        return sel[0].row() if sel else -1

    def _cancel_editing(self):
        """Cancel current editing and restore the original item to the table"""
        if self._editing_index is None or self._original_item is None:
            return

        if self._has_unsaved_changes():
            reply = QtWidgets.QMessageBox.question(
                self,
                "Cancel Edit",
                "Are you sure you want to cancel? Any changes will be lost.",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            if reply != QtWidgets.QMessageBox.Yes:
                return

        insert_pos = min(self._editing_index, len(self._items))
        self._items.insert(insert_pos, self._original_item)
        self.table.insertRow(insert_pos)
        self._populate_table_row(insert_pos, self._original_item)
        self.table.selectRow(insert_pos)
        self.table.scrollToItem(self.table.item(insert_pos, 0), QtWidgets.QAbstractItemView.PositionAtCenter)

        self._clear_entry_form()
        self._editing_index = None
        self._original_item = None
        self.btn_add.setText("Add Feature Idea")
        self.btn_cancel.setVisible(False)

    def _delete_selected(self):
        """Delete the selected feature idea and save to database"""
        idx = self._selected_row()
        if idx < 0:
            return

        if QtWidgets.QMessageBox.question(self, "Delete Feature Idea",
                                          "Remove the selected feature idea?") == QtWidgets.QMessageBox.Yes:
            # Clean up files before removing from database
            feature_idea = self._items[idx]
            self._cleanup_item_files(feature_idea.attachments)  # ADD THIS LINE

            self.table.removeRow(idx)
            del self._items[idx]

            # Save to database after deletion
            self._save_feature_ideas_data()

            if self._editing_index is not None and self._editing_index >= idx:
                if self._editing_index == idx:
                    self._editing_index = None
                    self._original_item = None
                    self.btn_add.setText("Add Feature Idea")
                    self.btn_cancel.setVisible(False)
                else:
                    self._editing_index -= 1

    def _load_feature_idea_for_editing(self):
        """Load selected feature idea into entry form and remove from table for editing"""
        idx = self._selected_row()
        if idx < 0:
            return

        if self._has_unsaved_changes():
            reply = QtWidgets.QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes in the entry form. Load the selected feature idea anyway?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            if reply != QtWidgets.QMessageBox.Yes:
                return

        item = self._items[idx]
        self._clear_entry_form()

        # Load item data into form
        self.title_edit.setText(item.title)
        self.problem_edit.setText(item.problem_description)
        self.outcome_edit.setText(item.expected_outcome)
        self.steps_widget.set_steps(item.steps)

        # Load attachments and recreate chips
        for attachment in item.attachments:
            if attachment.file_path.exists():
                self._add_attachment_chip(attachment)

        # Set editing mode and store original
        self._editing_index = idx
        self._original_item = FeatureIdea(
            title=item.title,
            problem_description=item.problem_description,
            expected_outcome=item.expected_outcome,
            steps=item.steps.copy(),
            attachments=item.attachments.copy()
        )

        # Remove from table and items list
        self.table.removeRow(idx)
        del self._items[idx]

        # Update UI for editing mode
        self.btn_add.setText("Update Feature Idea")
        self.btn_cancel.setVisible(True)

    def _has_unsaved_changes(self) -> bool:
        """Check if the entry form has unsaved data"""
        return (
            bool(self.title_edit.text().strip()) or
            bool(self.problem_edit.toPlainText().strip()) or
            bool(self.outcome_edit.toPlainText().strip()) or
            bool(self.steps_widget.get_steps()) or
            bool(self._entry_attachments)
        )

    def _clear_entry_form(self):
        """Clear all entry form fields and state"""
        self.title_edit.clear()
        self.problem_edit.clear()
        self.outcome_edit.clear()
        self.steps_widget.clear()

        # Clear chips
        for i in reversed(range(self.chips_flow.count())):
            it = self.chips_flow.itemAt(i)
            w = it.widget() if it else None
            self.chips_flow.takeAt(i)
            if w:
                w.deleteLater()

        self._entry_attachments.clear()

    def _table_context_menu(self, pos: QtCore.QPoint):
        """Show context menu for table"""
        idx = self.table.indexAt(pos).row()
        if idx < 0:
            return
        menu = QtWidgets.QMenu(self)
        act_open = menu.addAction("Edit Feature Idea")
        act_del = menu.addAction("Delete")
        act = menu.exec(self.table.viewport().mapToGlobal(pos))
        if act == act_open:
            self._load_feature_idea_for_editing()
        elif act == act_del:
            self._delete_selected()

    # ------------- Screenshot callbacks -------------

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

        title = metadata.get('title',
                             '') or f"Screenshot {QtCore.QDateTime.currentDateTime().toString('yyyy-MM-dd hh:mm')}"
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
            # Screenshot for existing feature idea
            if 0 <= idx < len(self._items):
                screenshot_attachment = AttachmentMetadata(
                    file_path=screenshot_path,
                    title=title,
                    notes=notes_text,
                    is_screenshot=True
                )

                self._items[idx].attachments.append(screenshot_attachment)
                self._populate_table_row(idx, self._items[idx])

    # ------------- Data access methods -------------

    def get_feature_ideas(self) -> List[FeatureIdea]:
        """Get all feature ideas"""
        return self._items.copy()

    def set_feature_ideas(self, ideas: List[FeatureIdea]):
        """Set feature ideas (for loading from storage)"""
        self._items = ideas.copy()
        self.table.setRowCount(0)
        for idea in self._items:
            self._append_row(idea)

    def get_data_source_dependencies(self) -> List[str]:
        """Get all unique data source references across feature ideas"""
        dependencies = set()
        for idea in self._items:
            for step in idea.steps:
                if step.requires_data_access and step.data_source_ref:
                    dependencies.add(step.data_source_ref)
        return sorted(list(dependencies))
