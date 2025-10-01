from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any
import os
import json
from datetime import datetime

from PySide6 import QtWidgets, QtCore, QtGui
from discovery_assistant.ui.widgets.draggable_table import DraggableTableWidget
from discovery_assistant.baselogger import logging
from discovery_assistant.ui.widgets.info import InfoSection
from discovery_assistant.ui.info_text import REFERENCE_LIBRARY_INFO  # You'll need to add this
from discovery_assistant.ui.widgets.screenshot_tool import ScreenshotTool
from discovery_assistant.storage import DatabaseSession, FileManager, get_files_dir, ReferenceDocument as DBReferenceDocument

_LOGGER = logging.getLogger("DISCOVERY.ui.tabs.reference_library_tab")


# -------------------------
# Data models
# -------------------------

@dataclass
class ReferenceDocument:
    """A reference document with categorization and metadata"""
    file_path: Path
    title: str = ""
    description: str = ""
    category: str = ""
    tags: List[str] = field(default_factory=list)
    upload_date: datetime = field(default_factory=datetime.now)
    file_size: int = 0
    is_screenshot: bool = False

    def __post_init__(self):
        self.title = self.title.strip()
        self.description = self.description.strip()
        self.category = self.category.strip()

        # Calculate file size if not provided
        if self.file_size == 0 and self.file_path.exists():
            try:
                self.file_size = self.file_path.stat().st_size
            except OSError:
                self.file_size = 0

    @property
    def display_name(self) -> str:
        """Return title if available, otherwise filename"""
        return self.title if self.title.strip() else self.file_path.stem

    @property
    def file_extension(self) -> str:
        """Return file extension"""
        return self.file_path.suffix.lower()

    @property
    def formatted_file_size(self) -> str:
        """Return human-readable file size"""
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        else:
            return f"{self.file_size / (1024 * 1024):.1f} MB"


# Document categories for different business types
DEFAULT_CATEGORIES = [
    "Organizational",
    "Process Documentation",
    "Policies & Procedures",
    "Technical Specifications",
    "Compliance & Regulatory",
    "Training Materials",
    "Financial Documents",
    "Vendor/Supplier Info",
    "Industry Standards",
    "Meeting Notes & Records",
    "Legacy Documentation",
    "Other"
]


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


# -------------------------
# Tag input widget
# -------------------------

class TagInputWidget(QtWidgets.QWidget):
    """Widget for entering and displaying tags"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tags = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Input field
        self.tag_input = QtWidgets.QLineEdit()
        self.tag_input.setPlaceholderText("Type tags separated by commas (e.g., urgent, finance, policy)")
        _force_dark_text(self.tag_input)
        self.tag_input.returnPressed.connect(self._process_tags)
        layout.addWidget(self.tag_input)

        # Tags display area
        self.tags_area = QtWidgets.QWidget()
        self.tags_layout = QtWidgets.QHBoxLayout(self.tags_area)
        self.tags_layout.setContentsMargins(0, 0, 0, 0)
        self.tags_layout.setSpacing(4)
        layout.addWidget(self.tags_area)

    def _process_tags(self):
        """Process input text into tags"""
        text = self.tag_input.text().strip()
        if text:
            new_tags = [tag.strip() for tag in text.split(',') if tag.strip()]
            for tag in new_tags:
                if tag not in self._tags:
                    self._tags.append(tag)
                    self._add_tag_chip(tag)
            self.tag_input.clear()

    def _add_tag_chip(self, tag: str):
        """Add a visual tag chip"""
        chip = QtWidgets.QFrame()
        chip.setStyleSheet("""
            QFrame {
                background: #E5E7EB;
                border: 1px solid #D1D5DB;
                border-radius: 4px;
                padding: 2px 6px;
            }
        """)

        chip_layout = QtWidgets.QHBoxLayout(chip)
        chip_layout.setContentsMargins(4, 2, 4, 2)
        chip_layout.setSpacing(4)

        label = QtWidgets.QLabel(tag)
        label.setStyleSheet("background: transparent; color: #374151; font-size: 12px;")

        remove_btn = QtWidgets.QToolButton()
        remove_btn.setText("×")
        remove_btn.setStyleSheet("""
            QToolButton {
                background: transparent;
                border: none;
                color: #6B7280;
                font-size: 14px;
                font-weight: bold;
                width: 16px;
                height: 16px;
            }
            QToolButton:hover {
                color: #EF4444;
                background: rgba(239, 68, 68, 0.1);
                border-radius: 8px;
            }
        """)
        remove_btn.clicked.connect(lambda: self._remove_tag(tag, chip))

        chip_layout.addWidget(label)
        chip_layout.addWidget(remove_btn)

        self.tags_layout.addWidget(chip)

    def _remove_tag(self, tag: str, chip: QtWidgets.QFrame):
        """Remove a tag"""
        if tag in self._tags:
            self._tags.remove(tag)
        chip.deleteLater()

    def get_tags(self) -> List[str]:
        """Get current tags"""
        # Process any remaining input
        self._process_tags()
        return self._tags.copy()

    def set_tags(self, tags: List[str]):
        """Set tags"""
        # Clear existing
        self.clear_tags()

        # Add new tags
        for tag in tags:
            if tag.strip() and tag not in self._tags:
                self._tags.append(tag.strip())
                self._add_tag_chip(tag.strip())

    def clear_tags(self):
        """Clear all tags"""
        self._tags.clear()
        # Remove all chip widgets
        while self.tags_layout.count():
            child = self.tags_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()


# -------------------------
# Document upload dialog
# -------------------------

class DocumentUploadDialog(QtWidgets.QDialog):
    """Dialog for uploading reference documents with metadata"""

    def __init__(self, parent=None, document: Optional[ReferenceDocument] = None):
        super().__init__(parent)
        self.setWindowTitle("Add Reference Document" if not document else "Edit Reference Document")
        self.setModal(True)
        self.resize(600, 500)
        self.setStyleSheet("""
           QDialog { background-color: rgb(255, 255, 255); }
           QPushButton {
                        background:#A5BBCF;
                        color:#FFFFFF;
                        border:1px solid #A5BBCF;
                        border-radius:6px;
                        padding:8px 12px;
                    }
                    QPushButton:hover { background:#1f2937; border-color:#1f2937; }
                    QPushButton:disabled { background:#9CA3AF; border-color:#9CA3AF; color:#F3F4F6; } 
            """)


        self._selected_path: Optional[Path] = None
        self._editing_document = document

        body = QtWidgets.QVBoxLayout(self)
        body.setContentsMargins(16, 16, 16, 16)
        body.setSpacing(16)

        # File selection
        file_section = QtWidgets.QVBoxLayout()
        file_section.setSpacing(6)

        file_label = QtWidgets.QLabel("Document File")
        file_label.setStyleSheet("font-size:13px; color:#334155; font-weight:500;")
        file_section.addWidget(file_label)

        file_row = QtWidgets.QHBoxLayout()
        file_row.setSpacing(8)

        self.file_path_edit = QtWidgets.QLineEdit()
        self.file_path_edit.setPlaceholderText("Select a file to upload...")
        self.file_path_edit.setReadOnly(True)
        self._apply_input_style(self.file_path_edit)

        self.browse_btn = QtWidgets.QPushButton("Browse...")
        self.browse_btn.clicked.connect(self._browse_file)

        file_row.addWidget(self.file_path_edit, 1)
        file_row.addWidget(self.browse_btn, 0)
        file_section.addLayout(file_row)

        body.addLayout(file_section)

        # Title and Category row
        title_cat_row = QtWidgets.QHBoxLayout()
        title_cat_row.setSpacing(12)

        # Title field
        title_section = QtWidgets.QVBoxLayout()
        title_section.setSpacing(6)

        title_label = QtWidgets.QLabel("Title")
        title_label.setStyleSheet("font-size:13px; color:#334155; font-weight:500;")
        title_section.addWidget(title_label)

        self.title_edit = QtWidgets.QLineEdit()
        self.title_edit.setPlaceholderText("Descriptive title for this document")
        self._apply_input_style(self.title_edit)
        title_section.addWidget(self.title_edit)

        title_cat_row.addLayout(title_section, 2)

        # Category field
        category_section = QtWidgets.QVBoxLayout()
        category_section.setSpacing(6)

        category_label = QtWidgets.QLabel("Category")
        category_label.setStyleSheet("font-size:13px; color:#334155; font-weight:500;")
        category_section.addWidget(category_label)

        self.category_combo = QtWidgets.QComboBox()
        self.category_combo.setStyleSheet("""
            QComboBox {
                background: white;
                color: black;
                padding: 4px 8px;
                }
            QComboBox QAbstractItemView {
                background: #F5F6F7;
                color: black;
                selection-background-color: rgb(100, 100, 100); /* Optional: darker gray for selected item */
            }
        """)
        self.category_combo.setEditable(True)
        self.category_combo.addItems(DEFAULT_CATEGORIES)
        category_section.addWidget(self.category_combo)

        title_cat_row.addLayout(category_section, 1)
        body.addLayout(title_cat_row)

        # Description field
        desc_section = QtWidgets.QVBoxLayout()
        desc_section.setSpacing(6)

        desc_label = QtWidgets.QLabel("Description")
        desc_label.setStyleSheet("font-size:13px; color:#334155; font-weight:500;")
        desc_section.addWidget(desc_label)

        self.description_edit = QtWidgets.QTextEdit()
        self.description_edit.setPlaceholderText("Brief description of the document's content and purpose...")
        self.description_edit.setMinimumHeight(80)
        self.description_edit.setMaximumHeight(120)
        self._apply_input_style(self.description_edit)
        desc_section.addWidget(self.description_edit)

        body.addLayout(desc_section)

        # Tags field
        tags_section = QtWidgets.QVBoxLayout()
        tags_section.setSpacing(6)

        tags_label = QtWidgets.QLabel("Tags")
        tags_label.setStyleSheet("font-size:13px; color:#334155; font-weight:500;")
        tags_section.addWidget(tags_label)

        self.tags_widget = TagInputWidget()
        tags_section.addWidget(self.tags_widget)

        body.addLayout(tags_section)

        # Dialog buttons
        body.addStretch(1)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch(1)

        cancel_btn = QtWidgets.QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        save_btn = QtWidgets.QPushButton("Save" if document else "Add Document")
        save_btn.clicked.connect(self.accept)
        save_btn.setDefault(True)

        button_layout.addWidget(cancel_btn)
        button_layout.addSpacing(-7)
        button_layout.addWidget(save_btn)
        body.addLayout(button_layout)

        # Load existing document if provided
        if document:
            self._load_document(document)

        # Enable/disable save button based on file selection
        self._update_save_button()
        self.file_path_edit.textChanged.connect(self._update_save_button)
        self.title_edit.textChanged.connect(self._update_save_button)

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

    def _browse_file(self):
        """Open file dialog to select document"""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select Reference Document",
            "",
            "All Files (*)"
        )

        if file_path:
            self._selected_path = Path(file_path)
            self.file_path_edit.setText(file_path)

            # Auto-populate title with filename if title is empty
            if not self.title_edit.text().strip():
                self.title_edit.setText(self._selected_path.stem)

    def _load_document(self, document: ReferenceDocument):
        """Load document data into form"""
        self._selected_path = document.file_path
        self.file_path_edit.setText(str(document.file_path))
        self.title_edit.setText(document.title)
        self.description_edit.setText(document.description)

        # Set category
        if document.category:
            index = self.category_combo.findText(document.category)
            if index >= 0:
                self.category_combo.setCurrentIndex(index)
            else:
                self.category_combo.setEditText(document.category)

        # Set tags
        self.tags_widget.set_tags(document.tags)

    def _update_save_button(self):
        """Enable/disable save button based on required fields"""
        buttons = self.findChildren(QtWidgets.QPushButton)
        if buttons:
            save_btn = buttons[-1]  # Last button should be save

            # For editing, file path is optional; for new docs, it's required
            has_file = (hasattr(self, '_selected_path') and
                        self._selected_path is not None and
                        self._selected_path.exists())
            has_title = bool(self.title_edit.text().strip())

            if self._editing_document:
                # When editing, only title is required
                save_btn.setEnabled(has_title)
            else:
                # When creating new, both file and title required
                save_btn.setEnabled(has_file and has_title)

    def get_document(self) -> Optional[ReferenceDocument]:
        """Get the document data from dialog"""
        if not self._editing_document:
            # New document requires file
            if not self._selected_path or not self._selected_path.exists():
                return None

        title = self.title_edit.text().strip()
        if not title:
            return None

        # Use existing file path if editing and no new file selected
        file_path = self._selected_path
        if self._editing_document and (not file_path or not file_path.exists()):
            file_path = self._editing_document.file_path

        return ReferenceDocument(
            file_path=file_path,
            title=title,
            description=self.description_edit.toPlainText().strip(),
            category=self.category_combo.currentText().strip(),
            tags=self.tags_widget.get_tags(),
            upload_date=self._editing_document.upload_date if self._editing_document else datetime.now()
        )


# -------------------------
# Main Reference Library Tab
# -------------------------

class ReferenceLibraryTab(QtWidgets.QWidget):
    requestScreenshot = QtCore.Signal(int)  # row index

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        _LOGGER.info("ReferenceLibraryTab initialized")

        # ---- scroller ----
        scroller = QtWidgets.QScrollArea(self)
        scroller.setObjectName("ReferenceLibraryScroll")
        scroller.setWidgetResizable(True)
        scroller.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroller.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        scroller.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroller.setStyleSheet("""
            QScrollArea#ReferenceLibraryScroll { background: transparent; border: none; }
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
        card.setObjectName("ReferenceLibraryCard")
        card.setStyleSheet("""
            QFrame#ReferenceLibraryCard {
                background:#FFFFFF;
                border:1px solid #E5E7EB;
                border-radius:12px;
            }
            QFrame#ReferenceLibraryCard QLabel { background: transparent; }
            QPushButton {
                background:#A5BBCF;
                color:#FFFFFF;
                border:1px solid #A5BBCF;
                border-radius:6px;
                padding:8px 12px;
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
            title="Reference Library",
            subtitle="Central repository for organizational documents, policies, and reference materials.",
            info_html="<p>Upload company documents, policies, process documentation, and other reference materials that support the discovery process. These documents will be indexed and made available for analysis.</p>",
            icon_size_px=28,
            parent=card,
        )
        card_layout.addWidget(section)
        section.bind_scrollarea(self._scroller)

        # ---- actions row ----
        actions_row = QtWidgets.QHBoxLayout()
        actions_row.setSpacing(8)

        self.btn_upload = QtWidgets.QPushButton("Upload Document")
        self.btn_upload.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_capture = QtWidgets.QPushButton("Capture Screenshot")
        self.btn_capture.setCursor(QtCore.Qt.PointingHandCursor)
        actions_row.addWidget(self.btn_upload, 0, QtCore.Qt.AlignLeft)
        actions_row.addWidget(self.btn_capture, 0, QtCore.Qt.AlignLeft)
        actions_row.addStretch(1)

        card_layout.addLayout(actions_row)

        # ---- table ----
        self.table = DraggableTableWidget(0, 6, card)
        self.table.setObjectName("ReferenceLibraryTable")
        self.table.setHorizontalHeaderLabels(["Title", "Category", "Description", "Tags", "File Size", "Upload Date"])

        # Configure headers
        for c in range(self.table.columnCount()):
            item = self.table.horizontalHeaderItem(c)
            if item:
                item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        hdr = self.table.horizontalHeader()
        hdr.setStretchLastSection(False)
        hdr.setSectionResizeMode(0, QtWidgets.QHeaderView.Interactive)  # Title - user resizable
        hdr.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)  # Category - auto-size
        hdr.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)  # Description - stretches
        hdr.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)  # Tags - auto-size
        hdr.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)  # File Size - auto-size
        hdr.setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeToContents)  # Upload Date - auto-size

        # Set minimum column widths
        self.table.setColumnWidth(0, 200)  # Title
        self.table.setColumnWidth(1, 120)  # Category

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
            QTableWidget::item:hover {
                background: #F8FAFC;
            }
        """)

        pal = self.table.palette()
        pal.setColor(QtGui.QPalette.Base, QtGui.QColor("#FFFFFF"))
        pal.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor("#C7D1DA"))
        pal.setColor(QtGui.QPalette.Text, QtGui.QColor("#0F172A"))
        pal.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor("#0F172A"))
        self.table.setPalette(pal)

        # Connect drag-drop reordering
        self.table.rowsReordered.connect(self._handle_row_reorder)

        card_layout.addWidget(self.table)

        # ---- row actions ----
        row_actions = QtWidgets.QHBoxLayout()
        row_actions.addStretch(1)
        self.btn_open = QtWidgets.QPushButton("Open File")
        self.btn_open.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_edit = QtWidgets.QPushButton("Edit Details")
        self.btn_edit.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_delete = QtWidgets.QPushButton("Delete")
        self.btn_delete.setCursor(QtCore.Qt.PointingHandCursor)
        row_actions.addWidget(self.btn_open)
        row_actions.addWidget(self.btn_edit)
        row_actions.addWidget(self.btn_delete)
        card_layout.addLayout(row_actions)

        # mount scroller
        root_layout = QtWidgets.QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(scroller)

        # ---- state ----
        self._documents: List[ReferenceDocument] = []

        # initial scrollbar mode
        self._set_scrollbar_stealth(True)
        section.toggled.connect(lambda open_: self._set_scrollbar_stealth(not open_))

        # wire up buttons
        self.btn_upload.clicked.connect(self._upload_document)
        self.btn_capture.clicked.connect(self._capture_screenshot)
        self.btn_open.clicked.connect(self._open_selected_file)
        self.btn_edit.clicked.connect(self._edit_selected_document)
        self.btn_delete.clicked.connect(self._delete_selected)

        self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._table_context_menu)
        self.table.itemDoubleClicked.connect(self._open_selected_file)

        # Screenshot tool
        self._shot_tool = ScreenshotTool(self)
        self.requestScreenshot.connect(self._launch_screenshot_for_row)
        self._shot_tool.screenshotSaved.connect(self._on_screenshot_saved)

        # Load data from database
        self._load_reference_documents_data()

    def _get_section_name(self) -> str:
        return "reference_library"

    def _copy_attachments_to_storage(self, item_id: int, file_path: Path, is_screenshot: bool = False) -> Optional[
        Path]:
        """Copy file to organized storage and return new path"""
        section = self._get_section_name()

        if not FileManager.validate_file_exists(file_path):
            _LOGGER.warning(f"Skipping missing file: {file_path}")
            return None

        # Check if file is already in our storage (avoid double-copying)
        if self._is_file_in_storage(file_path):
            return file_path

        # Copy to storage
        new_path = FileManager.copy_attachment_to_storage(
            file_path,
            section,
            item_id,
            is_screenshot
        )

        return new_path

    def _cleanup_item_files(self, file_path: Path) -> None:
        """Clean up file when an item is deleted"""
        if self._is_file_in_storage(file_path):
            FileManager.delete_file(file_path)

    def _is_file_in_storage(self, file_path: Path) -> bool:
        """Check if a file is in our organized storage directory"""
        try:
            files_dir = get_files_dir()
            return files_dir in file_path.parents
        except Exception:
            return False

    def _load_reference_documents_data(self) -> None:
        """Load existing reference documents from database into the table."""
        try:
            with DatabaseSession() as session:
                db_documents = session.query(DBReferenceDocument).order_by(DBReferenceDocument.priority_rank.asc()).all()

                for db_doc in db_documents:
                    # Parse tags from JSON string
                    tags = []
                    if db_doc.tags:
                        try:
                            tags = json.loads(db_doc.tags)
                        except (json.JSONDecodeError, TypeError):
                            tags = []

                    # Convert database model to dataclass
                    document = ReferenceDocument(
                        file_path=Path(db_doc.file_path),
                        title=db_doc.title,
                        description=db_doc.description or "",
                        category=db_doc.category or "",
                        tags=tags,
                        upload_date=db_doc.upload_date,
                        file_size=db_doc.file_size,
                        is_screenshot=db_doc.is_screenshot
                    )

                    self._documents.append(document)
                    self._append_row(document)

                _LOGGER.info(f"Loaded {len(db_documents)} reference documents from database")

        except Exception as e:
            _LOGGER.error(f"Failed to load reference documents data: {e}")

    def _save_reference_documents_data(self) -> None:
        """Save current reference documents list to database."""
        try:
            with DatabaseSession() as session:
                # Clear existing reference documents
                deleted_count = session.query(DBReferenceDocument).count()
                session.query(DBReferenceDocument).delete()
                _LOGGER.info(f"Deleted {deleted_count} existing reference documents")

                # Save each document with priority rank based on order
                for rank, doc in enumerate(self._documents, 1):
                    # Serialize tags as JSON
                    tags_json = json.dumps(doc.tags) if doc.tags else "[]"

                    db_document = DBReferenceDocument(
                        priority_rank=rank,
                        file_path=str(doc.file_path),
                        title=doc.title,
                        description=doc.description,
                        category=doc.category,
                        tags=tags_json,
                        upload_date=doc.upload_date,
                        file_size=doc.file_size,
                        is_screenshot=doc.is_screenshot
                    )
                    session.add(db_document)
                    session.flush()  # Get the ID for file management

                    # CRITICAL: Copy file to storage if needed
                    new_path = self._copy_attachments_to_storage(
                        db_document.id, doc.file_path, doc.is_screenshot
                    )

                    if new_path and new_path != doc.file_path:
                        # Update the document and database with new path
                        doc.file_path = new_path
                        db_document.file_path = str(new_path)

                    _LOGGER.info(f"Added reference document: {doc.title}")

                _LOGGER.info(f"Saved {len(self._documents)} reference documents to database")

        except Exception as e:
            _LOGGER.error(f"Failed to save reference documents data: {e}")

    def clear_fields(self) -> None:
        """Clear all reference documents."""
        # Clear the table
        self.table.setRowCount(0)

        # Clean up all files for this section
        section = self._get_section_name()
        deleted_files = FileManager.cleanup_section_files(section)
        _LOGGER.info(f"Cleaned up {deleted_files} files during clear")

        # Clear the documents list
        self._documents.clear()

        _LOGGER.info("Cleared all reference documents")

    # ------------- Drag-drop handling -------------

    def _handle_row_reorder(self, old_index: int, new_index: int):
        """Handle when rows are reordered via drag-and-drop"""
        if 0 <= old_index < len(self._documents) and 0 <= new_index < len(self._documents):
            item = self._documents.pop(old_index)
            self._documents.insert(new_index, item)

            # Save to database after reordering
            self._save_reference_documents_data()

            # Refresh table
            self._repopulate_table()

            # Select the moved row
            self.table.selectRow(new_index)

    # ------------- Scrollbar style -------------

    def _set_scrollbar_stealth(self, stealth: bool):
        sb = self._scroller.verticalScrollBar()
        sb.style().unpolish(sb)
        sb.style().polish(sb)
        sb.update()

    # ------------- Document management -------------

    def _upload_document(self):
        """Open document upload dialog"""
        dialog = DocumentUploadDialog(self)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            document = dialog.get_document()
            if document:
                self._documents.append(document)
                self._save_reference_documents_data()
                self._repopulate_table()

                # Select the new document
                row = len(self._documents) - 1
                self.table.selectRow(row)

    def _edit_selected_document(self):
        """Edit the selected document's metadata"""
        row = self._selected_row()
        if row < 0 or row >= len(self._documents):
            return

        document = self._documents[row]
        dialog = DocumentUploadDialog(self, document)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            updated_document = dialog.get_document()
            if updated_document:
                self._documents[row] = updated_document
                self._save_reference_documents_data()
                self._repopulate_table()

                # Select the updated document
                self.table.selectRow(row)

    def _delete_selected(self):
        """Delete the selected document"""
        row = self._selected_row()
        if row < 0 or row >= len(self._documents):
            return

        document = self._documents[row]

        reply = QtWidgets.QMessageBox.question(
            self,
            "Delete Reference Document",
            f"Are you sure you want to remove '{document.display_name}' from the reference library?\n\nThis will delete the file from storage.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )

        if reply == QtWidgets.QMessageBox.Yes:
            # Clean up the file before removing from database
            self._cleanup_item_files(document.file_path)

            self._documents.pop(row)
            self._save_reference_documents_data()
            self._repopulate_table()

    def _open_selected_file(self):
        """Open the selected file with the default application"""
        row = self._selected_row()
        if row < 0 or row >= len(self._documents):
            return

        document = self._documents[row]

        if not document.file_path.exists():
            QtWidgets.QMessageBox.warning(
                self,
                "File Not Found",
                f"The file '{document.file_path}' could not be found.\n\nIt may have been moved or deleted."
            )
            return

        # Open with default application
        try:
            import subprocess
            import sys

            if sys.platform == "darwin":  # macOS
                subprocess.run(["open", str(document.file_path)])
            elif sys.platform.startswith("win"):  # Windows
                subprocess.run(["start", str(document.file_path)], shell=True)
            else:  # Linux
                subprocess.run(["xdg-open", str(document.file_path)])
        except Exception as e:
            QtWidgets.QMessageBox.warning(
                self,
                "Cannot Open File",
                f"Unable to open the file:\n{e}"
            )

    def _capture_screenshot(self):
        """Capture a screenshot to add to the library"""
        self.requestScreenshot.emit(-1)  # -1 indicates new screenshot

    @QtCore.Slot(int)
    def _launch_screenshot_for_row(self, row_idx: int):
        """Launch screenshot tool"""
        self._pending_row_idx = row_idx
        self._shot_tool.start()

    @QtCore.Slot(str, dict)
    def _on_screenshot_saved(self, file_path: str, metadata: dict):
        """Handle screenshot saved event"""
        screenshot_path = Path(file_path)

        if not screenshot_path.exists():
            return

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

        # Create document
        document = ReferenceDocument(
            file_path=screenshot_path,
            title=title,
            description=notes_text,
            category="Other",  # Default category for screenshots
            tags=["screenshot"],
            is_screenshot=True
        )

        self._documents.append(document)
        self._save_reference_documents_data()
        self._repopulate_table()

        # Select the new screenshot
        row = len(self._documents) - 1
        self.table.selectRow(row)

    # ------------- Table helpers -------------

    def _repopulate_table(self):
        """Refresh table display"""
        self.table.setRowCount(0)
        for doc in self._documents:
            self._append_row(doc)

    def _append_row(self, document: ReferenceDocument):
        """Add a row to the table"""
        row = self.table.rowCount()
        self.table.insertRow(row)
        self._populate_table_row(row, document)

    def _populate_table_row(self, row: int, document: ReferenceDocument):
        """Populate a table row with document data"""

        def _cell(text: str) -> QtWidgets.QTableWidgetItem:
            item = QtWidgets.QTableWidgetItem(text)
            item.setFlags(item.flags() ^ QtCore.Qt.ItemIsEditable)
            return item

        # Format tags
        tags_text = ", ".join(document.tags) if document.tags else ""

        # Format upload date
        date_text = document.upload_date.strftime("%Y-%m-%d %H:%M")

        # Truncate description for display
        desc_preview = (document.description[:80] + "…") if len(document.description) > 80 else document.description

        self.table.setItem(row, 0, _cell(document.display_name))
        self.table.setItem(row, 1, _cell(document.category))
        self.table.setItem(row, 2, _cell(desc_preview))
        self.table.setItem(row, 3, _cell(tags_text))
        self.table.setItem(row, 4, _cell(document.formatted_file_size))
        self.table.setItem(row, 5, _cell(date_text))

    def _selected_row(self) -> int:
        """Get the currently selected row index"""
        sel = self.table.selectionModel().selectedRows()
        return sel[0].row() if sel else -1

    def _table_context_menu(self, pos: QtCore.QPoint):
        """Show context menu for table"""
        row = self.table.indexAt(pos).row()
        if row < 0:
            return

        menu = QtWidgets.QMenu(self)
        act_open = menu.addAction("Open File")
        act_edit = menu.addAction("Edit Details")
        menu.addSeparator()
        act_delete = menu.addAction("Delete")

        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action == act_open:
            self._open_selected_file()
        elif action == act_edit:
            self._edit_selected_document()
        elif action == act_delete:
            self._delete_selected()

    # ------------- Data access methods -------------

    def get_reference_documents(self) -> List[ReferenceDocument]:
        """Get all reference documents"""
        return self._documents.copy()

    def set_reference_documents(self, documents: List[ReferenceDocument]):
        """Set reference documents (for loading from storage)"""
        self._documents = documents.copy()
        self._repopulate_table()

    def add_reference_document(self, document: ReferenceDocument):
        """Add a single reference document"""
        self._documents.append(document)
        self._save_reference_documents_data()
        self._repopulate_table()
