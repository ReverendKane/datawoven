from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any
import json

from PySide6 import QtWidgets, QtCore, QtGui

from discovery_assistant.baselogger import logging
from discovery_assistant.ui.widgets.info import InfoSection
from discovery_assistant.ui.info_text import DATA_SOURCES_INFO
from discovery_assistant.ui.widgets.screenshot_tool import ScreenshotTool
from discovery_assistant.storage import DatabaseSession, DataSource, get_attachments_dir, get_screenshots_dir, FileManager, get_files_dir
from discovery_assistant.ui.widgets.draggable_table import DraggableTableWidget

_LOGGER = logging.getLogger("DISCOVERY.ui.tabs.data_sources_tab")


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
class DataSourceItem:
    name: str
    source_type: str  # "database", "api", "file_system", "cloud_service", "custom"
    connection_metadata: Dict[str, Any] = field(default_factory=dict)
    credentials_required: List[str] = field(default_factory=list)
    description: str = ""
    test_connection_status: str = "not_tested"  # "not_tested", "success", "failed"
    attachments: List[AttachmentMetadata] = field(default_factory=list)

    @property
    def connection_summary(self) -> str:
        """Generate a summary of connection details for table display"""
        if self.source_type == "database":
            server = self.connection_metadata.get("server", "")
            database = self.connection_metadata.get("database", "")
            return f"{server}/{database}" if server and database else server or database
        elif self.source_type == "api":
            return self.connection_metadata.get("base_url", "")
        elif self.source_type == "file_system":
            return self.connection_metadata.get("path", "")
        elif self.source_type == "cloud_service":
            provider = self.connection_metadata.get("provider", "")
            service = self.connection_metadata.get("service_type", "")
            return f"{provider} {service}".strip()
        else:
            return self.connection_metadata.get("summary", "Custom configuration")


# -------------------------
# Connection type templates
# -------------------------

CONNECTION_TYPES = {
    "database": {
        "display_name": "Database",
        "fields": [
            {"name": "server", "label": "Server/Host", "type": "text", "required": True, "placeholder": "localhost or server.company.com"},
            {"name": "port", "label": "Port", "type": "number", "required": False, "placeholder": "3306, 5432, 1433, etc."},
            {"name": "database", "label": "Database Name", "type": "text", "required": True, "placeholder": "database_name"},
            {"name": "schema", "label": "Schema", "type": "text", "required": False, "placeholder": "public, dbo, etc."},
            {"name": "db_type", "label": "Database Type", "type": "combo", "required": True, "options": ["MySQL", "PostgreSQL", "SQL Server", "Oracle", "MongoDB", "SQLite", "Other"]},
            {"name": "ssl_required", "label": "SSL/TLS Required", "type": "checkbox", "required": False},
            {"name": "connection_string", "label": "Custom Connection String", "type": "text", "required": False, "placeholder": "Optional: override with custom connection string"},
        ],
        "credentials": ["username", "password"],
        "description": "Relational or NoSQL database connection"
    },
    "api": {
        "display_name": "API/Web Service",
        "fields": [
            {"name": "base_url", "label": "Base URL", "type": "text", "required": True, "placeholder": "https://api.company.com"},
            {"name": "auth_type", "label": "Authentication Type", "type": "combo", "required": True, "options": ["API Key", "Bearer Token", "OAuth 2.0", "Basic Auth", "Custom Headers"]},
            {"name": "api_version", "label": "API Version", "type": "text", "required": False, "placeholder": "v1, v2, etc."},
            {"name": "rate_limit", "label": "Rate Limit (requests/minute)", "type": "number", "required": False, "placeholder": "60"},
            {"name": "timeout", "label": "Timeout (seconds)", "type": "number", "required": False, "placeholder": "30"},
            {"name": "custom_headers", "label": "Custom Headers (JSON)", "type": "multiline", "required": False, "placeholder": '{"X-Custom-Header": "value"}'},
        ],
        "credentials": ["api_key", "client_id", "client_secret", "access_token"],
        "description": "REST API, GraphQL, or web service endpoint"
    },
    "file_system": {
        "display_name": "File System/Network Share",
        "fields": [
            {"name": "path", "label": "Path", "type": "text", "required": True, "placeholder": "/path/to/data or \\\\server\\share"},
            {"name": "access_type", "label": "Access Type", "type": "combo", "required": True, "options": ["Local Filesystem", "SMB/CIFS Share", "NFS", "FTP/SFTP", "S3 Compatible"]},
            {"name": "protocol", "label": "Protocol", "type": "combo", "required": False, "options": ["SMB", "NFS", "FTP", "SFTP", "S3"]},
            {"name": "port", "label": "Port", "type": "number", "required": False, "placeholder": "21, 22, 445, etc."},
            {"name": "passive_mode", "label": "Passive Mode (FTP)", "type": "checkbox", "required": False},
            {"name": "encryption", "label": "Encryption Required", "type": "checkbox", "required": False},
        ],
        "credentials": ["username", "password", "private_key"],
        "description": "Local files, network shares, or file transfer protocols"
    },
    "cloud_service": {
        "display_name": "Cloud Service",
        "fields": [
            {"name": "provider", "label": "Cloud Provider", "type": "combo", "required": True, "options": ["AWS", "Azure", "Google Cloud", "Salesforce", "Microsoft 365", "Other"]},
            {"name": "service_type", "label": "Service Type", "type": "text", "required": True, "placeholder": "RDS, S3, Blob Storage, BigQuery, etc."},
            {"name": "region", "label": "Region", "type": "text", "required": False, "placeholder": "us-east-1, westus2, etc."},
            {"name": "resource_id", "label": "Resource ID/Name", "type": "text", "required": True, "placeholder": "bucket-name, database-instance-id"},
            {"name": "account_id", "label": "Account/Subscription ID", "type": "text", "required": False, "placeholder": "AWS Account ID, Azure Subscription"},
            {"name": "endpoint_url", "label": "Custom Endpoint", "type": "text", "required": False, "placeholder": "For private/custom endpoints"},
        ],
        "credentials": ["access_key", "secret_key", "tenant_id", "client_id", "client_secret"],
        "description": "Cloud-hosted databases, storage, and services"
    },
    "custom": {
        "display_name": "Custom Configuration",
        "fields": [
            {"name": "connection_type", "label": "Connection Type", "type": "text", "required": True, "placeholder": "Describe the type of system"},
            {"name": "endpoint", "label": "Endpoint/Location", "type": "text", "required": True, "placeholder": "URL, server, or connection point"},
            {"name": "configuration", "label": "Configuration (JSON)", "type": "multiline", "required": False, "placeholder": '{"key": "value", "setting": "option"}'},
            {"name": "additional_params", "label": "Additional Parameters", "type": "multiline", "required": False, "placeholder": "Any other connection parameters or notes"},
        ],
        "credentials": ["username", "password", "token", "certificate"],
        "description": "Custom connection that doesn't fit standard templates"
    }
}


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
# Dynamic connection form widget
# -------------------------

class ConnectionFormWidget(QtWidgets.QWidget):
    """Dynamic form that adapts based on selected connection type"""

    def __init__(self, parent=None):
        super().__init__(parent)
        # self.setStyleSheet("background: transparent;")
        self._current_type = None
        self._form_widgets = {}

        # Main layout
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Container frame for visual definition
        self.container = QtWidgets.QFrame()
        self.container.setObjectName("ConnectionFormContainer")
        self.container.setStyleSheet("""
            QFrame#ConnectionFormContainer {
                background: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 12px;
            }
        """)

        # Form layout inside container
        self.form_layout = QtWidgets.QVBoxLayout(self.container)
        self.form_layout.setContentsMargins(0, 0, 0, 0)
        self.form_layout.setSpacing(12)

        # Add container to main layout
        self.main_layout.addWidget(self.container)

        # Initialize with database form
        self.set_connection_type("database")

    def set_connection_type(self, connection_type: str):
        """Update the form fields based on the selected connection type"""
        if connection_type == self._current_type:
            return

        # Clear existing widgets
        self._clear_form()

        self._current_type = connection_type
        self._form_widgets = {}

        if connection_type not in CONNECTION_TYPES:
            return

        type_config = CONNECTION_TYPES[connection_type]

        for field_config in type_config["fields"]:
            self._add_form_field(field_config)

    def _clear_form(self):
        """Remove all existing form widgets"""
        while self.form_layout.count():
            item = self.form_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                # Handle nested layouts
                self._clear_layout(item.layout())

        # Clear the widgets dictionary
        self._form_widgets.clear()

    def _clear_layout(self, layout):
        """Recursively clear a layout"""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def _add_form_field(self, field_config: Dict[str, Any]):
        """Add a single form field based on configuration"""
        field_name = field_config["name"]
        field_label = field_config["label"]
        field_type = field_config["type"]
        required = field_config.get("required", False)
        placeholder = field_config.get("placeholder", "")

        # Create field layout
        field_layout = QtWidgets.QVBoxLayout()
        field_layout.setContentsMargins(0, 0, 0, 0)
        field_layout.setSpacing(6)

        # Label
        label_text = f"{field_label}{'*' if required else ''}"
        label = QtWidgets.QLabel(label_text)
        label.setStyleSheet("font-size:13px; color:#334155; background:transparent;")
        field_layout.addWidget(label)

        # Create appropriate widget based on field type
        if field_type == "text":
            widget = QtWidgets.QLineEdit()
            widget.setPlaceholderText(placeholder)
            _force_dark_text(widget)
        elif field_type == "number":
            widget = QtWidgets.QSpinBox()
            widget.setRange(0, 99999)
            if placeholder and placeholder.replace(',', '').replace('.', '').isdigit():
                widget.setValue(int(placeholder.replace(',', '').split('.')[0]))
            widget.setStyleSheet("""
                QSpinBox {
                    background: white;
                    color: black;
                    padding: 4px 8px;
                }
            """)
        elif field_type == "multiline":
            widget = QtWidgets.QTextEdit()
            widget.setPlaceholderText(placeholder)
            widget.setMaximumHeight(80)
            _force_dark_text(widget)
        elif field_type == "combo":
            widget = QtWidgets.QComboBox()
            options = field_config.get("options", [])
            widget.addItems(options)
            widget.setStyleSheet("""
                QComboBox {
                    background: white;
                    color: black;
                    padding: 4px 8px;
                }
            """)
        elif field_type == "checkbox":
            widget = QtWidgets.QCheckBox()
            # widget.setStyleSheet("background-color: transparent;")
            widget.setStyleSheet("""
                QCheckBox {
                    color: #374151;
                    font-size: 13px;
                    spacing: 6px;
                    background: transparent;
                }
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                }
                QCheckBox::indicator:unchecked {
                    border: 2px solid #D1D5DB;
                    border-radius: 4px;
                    background: #FFFFFF;
                }
                QCheckBox::indicator:checked {
                    border: 2px solid #A5BBCF;
                    border-radius: 4px;
                    background: #000000;
                }
            """)
        else:
            widget = QtWidgets.QLineEdit()
            widget.setPlaceholderText(placeholder)
            _force_dark_text(widget)

        field_layout.addWidget(widget)
        self.form_layout.addLayout(field_layout)

        # Store widget for later retrieval
        self._form_widgets[field_name] = widget

    def get_form_data(self) -> Dict[str, Any]:
        """Extract data from all form fields"""
        data = {}
        for field_name, widget in self._form_widgets.items():
            if isinstance(widget, QtWidgets.QLineEdit):
                data[field_name] = widget.text().strip()
            elif isinstance(widget, QtWidgets.QTextEdit):
                data[field_name] = widget.toPlainText().strip()
            elif isinstance(widget, QtWidgets.QComboBox):
                data[field_name] = widget.currentText()
            elif isinstance(widget, QtWidgets.QSpinBox):
                data[field_name] = widget.value()
            elif isinstance(widget, QtWidgets.QCheckBox):
                data[field_name] = widget.isChecked()
        return data

    def set_form_data(self, data: Dict[str, Any]):
        """Populate form fields with data"""
        for field_name, value in data.items():
            if field_name in self._form_widgets:
                widget = self._form_widgets[field_name]
                if isinstance(widget, QtWidgets.QLineEdit):
                    widget.setText(str(value))
                elif isinstance(widget, QtWidgets.QTextEdit):
                    widget.setText(str(value))
                elif isinstance(widget, QtWidgets.QComboBox):
                    index = widget.findText(str(value))
                    if index >= 0:
                        widget.setCurrentIndex(index)
                elif isinstance(widget, QtWidgets.QSpinBox):
                    widget.setValue(int(value) if isinstance(value, (int, float)) else 0)
                elif isinstance(widget, QtWidgets.QCheckBox):
                    widget.setChecked(bool(value))

    def clear_form(self):
        """Clear all form fields"""
        for widget in self._form_widgets.values():
            if isinstance(widget, QtWidgets.QLineEdit):
                widget.clear()
            elif isinstance(widget, QtWidgets.QTextEdit):
                widget.clear()
            elif isinstance(widget, QtWidgets.QComboBox):
                widget.setCurrentIndex(0)
            elif isinstance(widget, QtWidgets.QSpinBox):
                widget.setValue(0)
            elif isinstance(widget, QtWidgets.QCheckBox):
                widget.setChecked(False)


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
# Main Data Sources Tab
# -------------------------

class DataSourcesTab(QtWidgets.QWidget):
    requestScreenshot = QtCore.Signal(int)  # row index

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None, policy_enforcer=None) -> None:
        super().__init__(parent)
        self._policy_enforcer = policy_enforcer
        _LOGGER.info("DataSourcesTab initialized")

        # ---- scroller ----
        scroller = QtWidgets.QScrollArea(self)
        scroller.setObjectName("DataSourcesScroll")
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
        card.setObjectName("DataSourcesCard")
        card.setStyleSheet("""
            QFrame#DataSourcesCard {
                background:#FFFFFF;
                border:1px solid #E5E7EB;
                border-radius:12px;
            }
            QFrame#DataSourcesCard QLabel { background: transparent; }
            QFrame#DataSourcesCard QWidget#DataSourcesForm { background: transparent; }
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
            title="Data Sources",
            subtitle="Configure connection details for databases, APIs, and other data systems. Credentials will be collected securely after export.",
            info_html=DATA_SOURCES_INFO,
            icon_size_px=28,
            parent=card,
        )
        card_layout.addWidget(section)
        section.bind_scrollarea(self._scroller)

        # ---- form ----
        form_host = QtWidgets.QWidget(card)
        form_host.setObjectName("DataSourcesForm")
        form = _StackedLabelForm(form_host)

        # Data source name
        self.name_edit = QtWidgets.QLineEdit()
        self.name_edit.setPlaceholderText("Descriptive name for this data source (e.g., Customer Database)")
        _force_dark_text(self.name_edit)
        self._apply_field_policy(self.name_edit, "Source Name")
        form.add_row("Source Name", self.name_edit)

        # Connection type selector
        combo_container = QtWidgets.QWidget()
        combo_container_layout = QtWidgets.QHBoxLayout(combo_container)
        combo_container_layout.setContentsMargins(0, 0, 0, 0)

        self.type_combo = QtWidgets.QComboBox()
        self._apply_field_policy(self.type_combo, "Connection Type")
        self.type_combo.addItems([
            "Database",
            "API/Web Service",
            "File System/Network Share",
            "Cloud Service",
            "Custom Configuration"
        ])
        self.type_combo.setStyleSheet("""
            QComboBox {
                background: white;
                color: black;
                padding: 4px 8px;
            }
        """)
        form.add_row("Connection Type", self.type_combo)

        card_layout.addWidget(form_host)

        # ---- dynamic connection form ----
        self.connection_form = ConnectionFormWidget()
        card_layout.addWidget(self.connection_form)

        # ---- description ----
        desc_form_host = QtWidgets.QWidget(card)
        desc_form_host.setObjectName("DataSourcesForm")
        desc_form = _StackedLabelForm(desc_form_host)

        self.description_edit = QtWidgets.QTextEdit()
        self.description_edit.setPlaceholderText("Describe what data this source contains and how it will be used...")
        self.description_edit.setMinimumHeight(80)
        _force_dark_text(self.description_edit)
        self._apply_field_policy(self.description_edit, "Description")
        desc_form.add_row("Description", self.description_edit)

        card_layout.addWidget(desc_form_host)

        # ---- test connection section ----
        test_section = QtWidgets.QHBoxLayout()
        test_section.setSpacing(8)

        self.btn_test = QtWidgets.QPushButton("Test Connection")
        self.btn_test.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_test.setToolTip("Test connection without storing credentials")

        self.connection_status = QtWidgets.QLabel("Connection not tested")
        # self.connection_status.setStyleSheet("font-size:13px; color:#6B7280; background:transparent;")

        test_section.addWidget(self.btn_test, 0, QtCore.Qt.AlignLeft)
        test_section.addWidget(self.connection_status, 0, QtCore.Qt.AlignLeft)
        test_section.addStretch(1)

        card_layout.addLayout(test_section)

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

        # Apply policy to attachment functionality
        if self._policy_enforcer and not self._policy_enforcer.is_field_enabled("Data Sources",
                                                                                "Screenshots/Attachments"):
            self.btn_attach.setEnabled(False)
            self.btn_attach.setToolTip("Attachments have been disabled by your organization's discovery policy.")
            self.btn_capture.setEnabled(False)
            self.btn_capture.setToolTip("Screenshots have been disabled by your organization's discovery policy.")

        # Cancel button (hidden by default)
        self.btn_cancel = QtWidgets.QPushButton("Cancel Edit")
        self.btn_cancel.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_cancel.setVisible(False)
        actions_row.addWidget(self.btn_cancel, 0, QtCore.Qt.AlignRight)

        self.btn_add = QtWidgets.QPushButton("Add Data Source")
        self.btn_add.setCursor(QtCore.Qt.PointingHandCursor)
        actions_row.addWidget(self.btn_add, 0, QtCore.Qt.AlignRight)

        card_layout.addLayout(actions_row)

        # ---- attachment chips strip ----
        chips_box = QtWidgets.QFrame(card)
        chips_box.setObjectName("ChipsBox")
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
        self.table = DraggableTableWidget(0, 5, card)
        self.table.setObjectName("DataSourcesTable")
        self.table.setHorizontalHeaderLabels(["Source Name", "Type", "Connection", "Status", "Attached Files"])

        for c in range(self.table.columnCount()):
            item = self.table.horizontalHeaderItem(c)
            if item:
                item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        hdr = self.table.horizontalHeader()
        hdr.setStretchLastSection(False)
        hdr.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        hdr.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        hdr.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)
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
        self.btn_open_doc = QtWidgets.QPushButton("Edit Data Source")
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
        self._items: list[DataSourceItem] = []
        self._entry_attachments: list[AttachmentMetadata] = []
        self._editing_index: Optional[int] = None
        self._original_item: Optional[DataSourceItem] = None

        # initial scrollbar mode
        self._set_scrollbar_stealth(True)
        section.toggled.connect(lambda open_: self._set_scrollbar_stealth(not open_))

        # wire up
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        self.btn_attach.clicked.connect(self._attach_files)
        self.btn_capture.clicked.connect(self._capture_new_screenshot)
        self.btn_test.clicked.connect(self._test_connection)
        self.btn_add.clicked.connect(self._add_data_source)

        self.btn_open_doc.clicked.connect(self._load_data_source_for_editing)
        self.btn_delete.clicked.connect(self._delete_selected)
        self.btn_cancel.clicked.connect(self._cancel_editing)

        self.table.itemDoubleClicked.connect(lambda *_: self._load_data_source_for_editing())
        self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._table_context_menu)

        # Screenshot tool
        self._shot_tool = ScreenshotTool(self)
        self.requestScreenshot.connect(self._launch_screenshot_for_row)
        self._shot_tool.screenshotSaved.connect(self._on_screenshot_saved)

        # Initialize with database form
        self._on_type_changed("Database")

        # Load existing data after all UI setup is complete
        self._load_data_sources_data()

    def _handle_row_reorder(self, old_index: int, new_index: int):
        """Handle when rows are reordered via drag-and-drop"""
        if 0 <= old_index < len(self._items) and 0 <= new_index < len(self._items):
            item = self._items.pop(old_index)
            self._items.insert(new_index, item)

            # Save to database after reordering
            self._save_data_sources_data()

            # Refresh table
            self._repopulate_table()

            # Select the moved row
            self.table.selectRow(new_index)

    def _repopulate_table(self):
        """Refresh table display after drag-and-drop reordering"""
        self.table.setRowCount(0)
        for item in self._items:
            self._append_row(item)

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

    def _apply_field_policy(self, widget: QtWidgets.QWidget, field_name: str) -> None:
        """Apply policy governance to a field widget"""
        if not self._policy_enforcer or not self._policy_enforcer.has_policy():
            return

        section_name = "Data Sources"

        if not self._policy_enforcer.is_field_enabled(section_name, field_name):
            widget.setEnabled(False)
            if isinstance(widget, (QtWidgets.QLineEdit, QtWidgets.QTextEdit)):
                widget.setStyleSheet(widget.styleSheet() + """
                    QLineEdit:disabled, QTextEdit:disabled {
                        background: #F3F4F6;
                        color: #9CA3AF;
                        border: 1px solid #E5E7EB;
                    }
                """)
            elif isinstance(widget, QtWidgets.QComboBox):
                widget.setStyleSheet(widget.styleSheet() + """
                    QComboBox:disabled {
                        background: #F3F4F6;
                        color: #9CA3AF;
                    }
                """)
            widget.setToolTip(
                f"This field has been disabled by your organization's discovery policy.\n"
                f"This configuration was set by your administrator."
            )

    def _get_section_name(self) -> str:
        return "data_sources"

    def _load_data_sources_data(self) -> None:
        """Load existing data sources from database with file validation."""
        try:
            with DatabaseSession() as session:
                data_sources = session.query(DataSource).order_by(DataSource.priority_rank.asc()).all()

                for db_data_source in data_sources:
                    attachments = []
                    description = db_data_source.description or ""

                    # Extract attachment metadata from description
                    if "__ATTACHMENTS__:" in description:
                        try:
                            desc_part, attachments_json = description.split("__ATTACHMENTS__:", 1)
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

                            description = desc_part.strip()
                        except Exception as e:
                            _LOGGER.error(f"Error parsing attachments: {e}")

                    # Parse connection metadata from JSON
                    connection_metadata = {}
                    if db_data_source.configuration:
                        try:
                            connection_metadata = json.loads(db_data_source.configuration)
                        except (json.JSONDecodeError, TypeError):
                            connection_metadata = {}

                    # Get credentials required from connection type
                    credentials_required = CONNECTION_TYPES.get(db_data_source.connection_type, {}).get("credentials",
                                                                                                        [])

                    data_source_item = DataSourceItem(
                        name=db_data_source.source_name,
                        source_type=db_data_source.connection_type or "database",
                        connection_metadata=connection_metadata,
                        credentials_required=credentials_required,
                        description=description,
                        test_connection_status="not_tested",
                        attachments=attachments
                    )

                    self._items.append(data_source_item)
                    self._append_row(data_source_item)

                _LOGGER.info(f"Loaded {len(data_sources)} data sources from database")

        except Exception as e:
            _LOGGER.error(f"Failed to load data sources data: {e}")

    def _save_data_sources_data(self) -> None:
        """Save current data sources list to database with file management."""
        try:
            with DatabaseSession() as session:
                # Clear existing data sources
                session.query(DataSource).delete()

                # Save each data source with file management
                for rank, item in enumerate(self._items, 1):
                    # First save to get ID
                    db_data_source = DataSource(
                        source_name=item.name,
                        priority_rank=rank,
                        connection_type=item.source_type,
                        description=item.description,
                        configuration=json.dumps(item.connection_metadata) if item.connection_metadata else "{}"
                    )
                    session.add(db_data_source)
                    session.flush()  # Get the ID

                    # CRITICAL: Copy attachments to storage and update paths
                    if item.attachments:
                        updated_attachments = self._copy_attachments_to_storage(
                            db_data_source.id, item.attachments
                        )
                        # Update the item with new paths
                        item.attachments = updated_attachments

                    # Save attachment metadata as JSON in description
                    if item.attachments:
                        attachment_data = []
                        for att in item.attachments:
                            attachment_data.append({
                                'file_path': str(att.file_path),
                                'title': att.title,
                                'notes': att.notes,
                                'is_screenshot': att.is_screenshot
                            })

                        # Store attachment metadata
                        db_data_source.description += f"\n\n__ATTACHMENTS__:{json.dumps(attachment_data)}"

                _LOGGER.info(f"Saved {len(self._items)} data sources to database")

        except Exception as e:
            _LOGGER.error(f"Failed to save data sources data: {e}")

    def clear_fields(self) -> None:
        """Clear all data sources and clean up all files."""
        # Clean up all files for this section
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
        self.btn_add.setText("Add Data Source")
        self.btn_cancel.setVisible(False)

        _LOGGER.info("Cleared all data sources and form fields")

    # ------------- Connection type handling -------------

    def _on_type_changed(self, type_text: str):
        """Handle connection type selection change"""
        type_map = {
            "Database": "database",
            "API/Web Service": "api",
            "File System/Network Share": "file_system",
            "Cloud Service": "cloud_service",
            "Custom Configuration": "custom"
        }

        connection_type = type_map.get(type_text, "database")
        self.connection_form.set_connection_type(connection_type)

        # Update connection status
        self.connection_status.setText("Connection not tested")
        # self.connection_status.setStyleSheet("font-size:13px; color:#6B7280; background:transparent;")

    def _test_connection(self):
        """Test connection without storing credentials"""
        # This would implement actual connection testing
        # For now, simulate the test
        QtWidgets.QMessageBox.information(
            self,
            "Test Connection",
            "Connection testing is not implemented in this demo.\n\n"
            "In the full version, this would validate connection parameters "
            "without storing credentials."
        )
        self.connection_status.setText("Test not implemented")
        # self.connection_status.setStyleSheet("font-size:13px; color:#F59E0B; background:transparent;")



    # ------------- Scrollbar style -------------

    def _set_scrollbar_stealth(self, stealth: bool):
        sb = self._scroller.verticalScrollBar()
        # if stealth:
            # sb.setStyleSheet("""
            #     QScrollBar:vertical {
            #         background: #F3F4F6;
            #         width: 12px;
            #         margin: 8px 2px 8px 0;
            #     }
            #     QScrollBar::handle:vertical {
            #         background: #F3F4F6;
            #         border-radius: 6px;
            #         min-height: 24px;
            #     }
            #     QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; width: 0; }
            #     QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: #F3F4F6; }
            # """)
        # else:
            # sb.setStyleSheet("""
            #     QScrollBar:vertical {
            #         background: transparent;
            #         width: 12px;
            #         margin: 8px 2px 8px 0;
            #     }
            #     QScrollBar::handle:vertical {
            #         background: #D1D5DB;
            #         border-radius: 6px;
            #         min-height: 24px;
            #     }
            #     QScrollBar::handle:vertical:hover { background: #9CA3AF; }
            #     QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; width: 0; }
            #     QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
            # """)
        sb.style().unpolish(sb);
        sb.style().polish(sb);
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

    def _add_data_source(self):
        """Add or update a data source with database saving"""
        name = self.name_edit.text().strip()
        if not name:
            name = f"Untitled Data Source — {QtCore.QDateTime.currentDateTime().toString('yyyy-MM-dd hh:mm')}"

        # Get connection type
        type_map = {
            "Database": "database",
            "API/Web Service": "api",
            "File System/Network Share": "file_system",
            "Cloud Service": "cloud_service",
            "Custom Configuration": "custom"
        }
        source_type = type_map.get(self.type_combo.currentText(), "database")

        # Get connection metadata from dynamic form
        connection_metadata = self.connection_form.get_form_data()

        description = self.description_edit.toPlainText().strip()

        # Get credentials required list from connection type
        credentials_required = CONNECTION_TYPES.get(source_type, {}).get("credentials", [])

        item = DataSourceItem(
            name=name,
            source_type=source_type,
            connection_metadata=connection_metadata,
            credentials_required=credentials_required,
            description=description,
            test_connection_status="not_tested",
            attachments=self._entry_attachments.copy()
        )

        if self._editing_index is not None:
            # We're updating an existing item
            insert_pos = min(self._editing_index, len(self._items))
            self._items.insert(insert_pos, item)
            self.table.insertRow(insert_pos)
            self._populate_table_row(insert_pos, item)

            self.table.selectRow(insert_pos)
            self.table.scrollToItem(self.table.item(insert_pos, 0), QtWidgets.QAbstractItemView.PositionAtCenter)

            self._editing_index = None
            self._original_item = None
            self.btn_add.setText("Add Data Source")
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
        self._save_data_sources_data()

        self._clear_entry_form()

    # ------------- Table helpers -------------

    def _append_row(self, item: DataSourceItem):
        """Add a row to the table"""
        row = self.table.rowCount()
        self.table.insertRow(row)
        self._populate_table_row(row, item)

    def _populate_table_row(self, row: int, item: DataSourceItem):
        """Populate a table row with data source item data"""

        def _cell(text: str) -> QtWidgets.QTableWidgetItem:
            it = QtWidgets.QTableWidgetItem(text)
            it.setFlags(it.flags() ^ QtCore.Qt.ItemIsEditable)
            return it

        type_display = CONNECTION_TYPES.get(item.source_type, {}).get("display_name", item.source_type.title())
        connection_summary = item.connection_summary
        status_text = item.test_connection_status.replace("_", " ").title()
        files_text = ", ".join(att.display_name for att in item.attachments) if item.attachments else ""

        self.table.setItem(row, 0, _cell(item.name))
        self.table.setItem(row, 1, _cell(type_display))
        self.table.setItem(row, 2, _cell(connection_summary))
        self.table.setItem(row, 3, _cell(status_text))
        self.table.setItem(row, 4, _cell(files_text))

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
        self.btn_add.setText("Add Data Source")
        self.btn_cancel.setVisible(False)

    def _delete_selected(self):
        """Delete the selected data source and clean up files"""
        idx = self._selected_row()
        if idx < 0:
            return

        if QtWidgets.QMessageBox.question(self, "Delete Data Source",
                                          "Remove the selected data source?") == QtWidgets.QMessageBox.Yes:

            # Clean up files before removing from database
            item = self._items[idx]
            self._cleanup_item_files(item.attachments)

            self.table.removeRow(idx)
            del self._items[idx]

            # Save to database after deletion
            self._save_data_sources_data()

            # Handle editing state adjustments
            if self._editing_index is not None and self._editing_index >= idx:
                if self._editing_index == idx:
                    self._editing_index = None
                    self._original_item = None
                    self.btn_add.setText("Add Data Source")
                    self.btn_cancel.setVisible(False)
                else:
                    self._editing_index -= 1

    def _load_data_source_for_editing(self):
        """Load selected data source into entry form and remove from table for editing"""
        idx = self._selected_row()
        if idx < 0:
            return

        if self._has_unsaved_changes():
            reply = QtWidgets.QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes in the entry form. Load the selected data source anyway?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            if reply != QtWidgets.QMessageBox.Yes:
                return

        item = self._items[idx]

        # Clear current form state
        self._clear_entry_form()

        # Load item data into form
        self.name_edit.setText(item.name)

        # Set connection type
        type_map = {
            "database": "Database",
            "api": "API/Web Service",
            "file_system": "File System/Network Share",
            "cloud_service": "Cloud Service",
            "custom": "Custom Configuration"
        }
        type_display = type_map.get(item.source_type, "Database")
        type_index = self.type_combo.findText(type_display)
        if type_index >= 0:
            self.type_combo.setCurrentIndex(type_index)

        # Set connection form data
        self.connection_form.set_form_data(item.connection_metadata)
        self.description_edit.setText(item.description)

        # Load attachments and recreate chips
        for attachment in item.attachments:
            if attachment.file_path.exists():
                self._add_attachment_chip(attachment)

        # Set editing mode and store original
        self._editing_index = idx
        self._original_item = DataSourceItem(
            name=item.name,
            source_type=item.source_type,
            connection_metadata=item.connection_metadata.copy(),
            credentials_required=item.credentials_required.copy(),
            description=item.description,
            test_connection_status=item.test_connection_status,
            attachments=item.attachments.copy()
        )

        # Remove from table and items list
        self.table.removeRow(idx)
        del self._items[idx]

        # Update UI for editing mode
        self.btn_add.setText("Update Data Source")
        self.btn_cancel.setVisible(True)

    def _has_unsaved_changes(self) -> bool:
        """Check if the entry form has unsaved data"""
        form_data = self.connection_form.get_form_data()
        has_form_data = any(str(v).strip() for v in form_data.values() if v)

        return (
            bool(self.name_edit.text().strip()) or
            bool(self.description_edit.toPlainText().strip()) or
            has_form_data or
            bool(self._entry_attachments)
        )

    def _clear_entry_form(self):
        """Clear all entry form fields and state"""
        self.name_edit.clear()
        self.type_combo.setCurrentIndex(0)
        self.connection_form.clear_form()
        self.description_edit.clear()

        # Reset connection status
        self.connection_status.setText("Connection not tested")

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
        act_open = menu.addAction("Edit Data Source")
        act_del = menu.addAction("Delete")
        act = menu.exec(self.table.viewport().mapToGlobal(pos))
        if act == act_open:
            self._load_data_source_for_editing()
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

            if screenshot_attachment not in self._entry_attachments:
                self._add_attachment_chip(screenshot_attachment)

        else:
            # Screenshot for existing data source
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
