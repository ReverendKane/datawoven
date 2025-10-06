from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any
import json
from datetime import datetime, date
from discovery_assistant import resources

from PySide6 import QtWidgets, QtCore, QtGui
from discovery_assistant.storage import DatabaseSession, ComplianceRequirement as DBComplianceRequirement, Compliance
from discovery_assistant.storage import FileManager, get_files_dir
from discovery_assistant.ui.widgets.draggable_table import DraggableTableWidget
from discovery_assistant.baselogger import logging
from discovery_assistant.ui.widgets.info import InfoSection
from discovery_assistant.ui.info_text import COMPLIANCE_INFO
from discovery_assistant.ui.widgets.screenshot_tool import ScreenshotTool

_LOGGER = logging.getLogger("DISCOVERY.ui.tabs.compliance_tab")


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
class ComplianceRequirement:
    """Individual compliance requirement or regulation"""
    name: str
    regulation_type: str
    authority: str = ""
    description: str = ""
    current_status: str = "not_assessed"
    risk_level: str = "medium"
    compliance_deadline: Optional[date] = None
    review_frequency: str = "annual"
    responsible_person: str = ""
    evidence_required: List[str] = field(default_factory=list)
    automated_monitoring: bool = False
    documentation_location: str = ""
    notes: str = ""
    attachments: List[AttachmentMetadata] = field(default_factory=list)

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

@dataclass
class ComplianceFramework:
    """Overall compliance framework for the organization"""
    framework_name: str = ""
    industry_sector: str = ""
    company_size: str = "small"  # "micro", "small", "medium", "large", "enterprise"
    geographic_scope: List[str] = field(default_factory=list)  # Countries/regions
    business_activities: List[str] = field(default_factory=list)
    data_types_handled: List[str] = field(default_factory=list)
    third_party_vendors: List[str] = field(default_factory=list)
    compliance_budget: str = ""
    compliance_software: List[str] = field(default_factory=list)
    audit_schedule: str = ""
    last_assessment_date: Optional[date] = None
    next_assessment_date: Optional[date] = None


# -------------------------
# Compliance type templates
# -------------------------

COMPLIANCE_TYPES = {
    "financial": {
        "display_name": "Financial & Banking",
        "common_regulations": [
            "SOX (Sarbanes-Oxley)",
            "PCI DSS",
            "FFIEC Guidelines",
            "Dodd-Frank",
            "Basel III",
            "MiFID II",
            "SEC Regulations",
            "FINRA Rules"
        ],
        "typical_requirements": [
            "Financial reporting accuracy",
            "Internal controls testing",
            "Payment card security",
            "Customer data protection",
            "Anti-money laundering (AML)",
            "Know your customer (KYC)"
        ],
        "evidence_types": [
            "Audit reports",
            "Control matrices",
            "Security assessments",
            "Transaction logs",
            "Risk assessments"
        ]
    },
    "healthcare": {
        "display_name": "Healthcare & Life Sciences",
        "common_regulations": [
            "HIPAA",
            "FDA 21 CFR Part 11",
            "HITECH",
            "GDPR (EU patients)",
            "State privacy laws",
            "Clinical trial regulations",
            "Medical device regulations"
        ],
        "typical_requirements": [
            "Patient data privacy",
            "Electronic signature validation",
            "Audit trails",
            "Access controls",
            "Data retention policies",
            "Breach notification procedures"
        ],
        "evidence_types": [
            "Risk assessments",
            "Policies and procedures",
            "Training records",
            "Access logs",
            "Validation documentation"
        ]
    },
    "data_privacy": {
        "display_name": "Data Privacy & Protection",
        "common_regulations": [
            "GDPR",
            "CCPA/CPRA",
            "PIPEDA (Canada)",
            "LGPD (Brazil)",
            "PDPA (Singapore)",
            "SOC 2",
            "ISO 27001",
            "NIST Privacy Framework"
        ],
        "typical_requirements": [
            "Data subject rights",
            "Consent management",
            "Data breach procedures",
            "Privacy by design",
            "Data retention schedules",
            "Third-party agreements"
        ],
        "evidence_types": [
            "Privacy policies",
            "Data mapping documents",
            "Consent records",
            "DPIAs",
            "Breach logs"
        ]
    },
    "industry_specific": {
        "display_name": "Industry-Specific",
        "common_regulations": [
            "FTC Act (Advertising)",
            "COPPA (Children's privacy)",
            "FERPA (Education)",
            "GLBA (Financial privacy)",
            "CAN-SPAM Act",
            "TCPA (Telemarketing)",
            "FDA regulations",
            "USDA regulations"
        ],
        "typical_requirements": [
            "Industry-specific disclosures",
            "Advertising compliance",
            "Age verification",
            "Educational record privacy",
            "Email marketing compliance"
        ],
        "evidence_types": [
            "Compliance checklists",
            "Marketing approvals",
            "Age verification records",
            "Disclosure documents"
        ]
    },
    "environmental": {
        "display_name": "Environmental & Sustainability",
        "common_regulations": [
            "EPA regulations",
            "OSHA environmental standards",
            "State environmental laws",
            "ISO 14001",
            "Carbon reporting requirements",
            "Waste disposal regulations",
            "Water quality standards"
        ],
        "typical_requirements": [
            "Environmental impact assessments",
            "Waste management procedures",
            "Emissions monitoring",
            "Sustainability reporting",
            "Chemical handling protocols"
        ],
        "evidence_types": [
            "Environmental assessments",
            "Monitoring reports",
            "Waste disposal records",
            "Sustainability reports"
        ]
    },
    "safety": {
        "display_name": "Workplace Safety & Security",
        "common_regulations": [
            "OSHA standards",
            "ISO 45001",
            "NIST Cybersecurity Framework",
            "State safety regulations",
            "Industry safety standards",
            "Emergency response requirements"
        ],
        "typical_requirements": [
            "Safety training programs",
            "Incident reporting procedures",
            "Emergency response plans",
            "Personal protective equipment",
            "Safety inspections"
        ],
        "evidence_types": [
            "Training records",
            "Incident reports",
            "Safety inspection reports",
            "Emergency drill records"
        ]
    },
    "employment": {
        "display_name": "Employment & Labor",
        "common_regulations": [
            "FLSA (Fair Labor Standards)",
            "FMLA (Family Medical Leave)",
            "ADA (Americans with Disabilities)",
            "EEOC guidelines",
            "State labor laws",
            "COBRA",
            "ERISA"
        ],
        "typical_requirements": [
            "Equal employment opportunity",
            "Wage and hour compliance",
            "Leave management",
            "Disability accommodations",
            "Benefits administration"
        ],
        "evidence_types": [
            "Employment policies",
            "Training documentation",
            "Accommodation records",
            "Wage and hour records"
        ]
    },
    "custom": {
        "display_name": "Custom/Other",
        "common_regulations": [
            "Local ordinances",
            "Professional licensing",
            "Trade association standards",
            "Contractual requirements",
            "International standards"
        ],
        "typical_requirements": [
            "Custom compliance requirements",
            "Professional standards",
            "Contractual obligations",
            "Certification maintenance"
        ],
        "evidence_types": [
            "Custom documentation",
            "Certification records",
            "Contract compliance evidence"
        ]
    }
}


# -------------------------
# Reusable style helpers (same as other tabs)
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
        lbl.setStyleSheet("font-size:13px; color:#334155; background:transparent;")
        row.addWidget(lbl)
        row.addWidget(field)
        self.addLayout(row)


# -------------------------
# Compliance form widget
# -------------------------

class ComplianceRequirementForm(QtWidgets.QWidget):
    """Form for entering individual compliance requirements"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._attachments: List[AttachmentMetadata] = []
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Container frame
        self.container = QtWidgets.QFrame()
        self.container.setObjectName("ComplianceFormContainer")
        self.container.setStyleSheet("""
            QFrame#ComplianceFormContainer {
                background: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 12px;
            }
        """)

        self.form_layout = QtWidgets.QVBoxLayout(self.container)
        self.form_layout.setContentsMargins(6,6,6,6)
        self.form_layout.setSpacing(16)

        # Basic information section
        self._add_basic_info_section()

        # Status and risk section
        self._add_status_section()

        # Timeline section
        self._add_timeline_section()

        # Details section
        self._add_details_section()

        self.main_layout.addWidget(self.container)

    def _add_basic_info_section(self):
        """Add basic requirement information fields"""
        # Requirement name
        self.name_edit = QtWidgets.QLineEdit()
        self.name_edit.setPlaceholderText("e.g., GDPR Article 32 - Security of Processing")
        _force_dark_text(self.name_edit)
        self.form_layout.addWidget(self._create_labeled_field("Requirement/Regulation Name *", self.name_edit))

        # Row for type and authority
        type_authority_row = QtWidgets.QHBoxLayout()
        type_authority_row.setSpacing(12)

        # Regulation type
        self.type_combo = QtWidgets.QComboBox()
        self.type_combo.addItems([
            "Financial & Banking",
            "Healthcare & Life Sciences",
            "Data Privacy & Protection",
            "Industry-Specific",
            "Environmental & Sustainability",
            "Workplace Safety & Security",
            "Employment & Labor",
            "Custom/Other"
        ])
        self.type_combo.setStyleSheet("""
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

        # Authority/regulator
        self.authority_edit = QtWidgets.QLineEdit()
        self.authority_edit.setPlaceholderText("e.g., GDPR, SEC, FDA, OSHA")
        _force_dark_text(self.authority_edit)

        type_authority_row.addWidget(self._create_labeled_field("Regulation Type", self.type_combo))
        type_authority_row.addWidget(self._create_labeled_field("Regulatory Authority", self.authority_edit))

        self.form_layout.addLayout(type_authority_row)

        # Description
        self.description_edit = QtWidgets.QTextEdit()
        self.description_edit.setPlaceholderText(
            "Describe the specific requirement, what it covers, and why it applies to your organization...")
        self.description_edit.setMaximumHeight(100)
        _force_dark_text(self.description_edit)
        self.form_layout.addWidget(self._create_labeled_field("Description", self.description_edit))

    def _add_status_section(self):
        """Add status and risk assessment fields"""
        status_risk_row = QtWidgets.QHBoxLayout()
        status_risk_row.setSpacing(12)

        # Current status
        self.status_combo = QtWidgets.QComboBox()
        self.status_combo.addItems([
            "Not Assessed",
            "Compliant",
            "Non-Compliant",
            "In Progress",
            "Not Applicable"
        ])

        self.status_combo.setStyleSheet("""
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

        # Risk level
        self.risk_combo = QtWidgets.QComboBox()
        self.risk_combo.addItems(["Low", "Medium", "High", "Critical"])
        self.risk_combo.setCurrentText("Medium")

        self.risk_combo.setStyleSheet("""
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

        status_risk_row.addWidget(self._create_labeled_field("Current Status", self.status_combo))
        status_risk_row.addWidget(self._create_labeled_field("Risk Level", self.risk_combo))

        self.form_layout.addLayout(status_risk_row)

    def _add_timeline_section(self):
        """Add timeline and review frequency fields"""
        timeline_row = QtWidgets.QHBoxLayout()
        timeline_row.setSpacing(12)

        # Compliance deadline
        self.deadline_edit = QtWidgets.QDateEdit()
        self.deadline_edit.setCalendarPopup(True)
        self.deadline_edit.setDate(QtCore.QDate.currentDate().addMonths(3))
        self.deadline_edit.setStyleSheet("""
            QDateEdit {
                background: white;
                color: black;
                padding: 4px 8px;
            }
            QDateEdit::down-arrow {
                background: white;
                image: url(:/images/three_dots.png);
                width: 10px;
                height: 10px;
            }
            QDateEdit QAbstractItemView {
                background: white;
                color: black;
            }
            QCalendarWidget {
                background: white;
                color: black;
            }
            QCalendarWidget QAbstractItemView {
                background: white;
                color: black;
                selection-background-color: rgb(100, 100, 100);
            }
        """)
        self.deadline_edit.update()

        # Review frequency
        self.frequency_combo = QtWidgets.QComboBox()
        self.frequency_combo.addItems([
            "As Needed",
            "Monthly",
            "Quarterly",
            "Semi-Annual",
            "Annual",
            "Biennial"
        ])
        self.frequency_combo.setCurrentText("Annual")
        self.frequency_combo.setStyleSheet("""
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

        timeline_row.addWidget(self._create_labeled_field("Compliance Deadline", self.deadline_edit))
        timeline_row.addWidget(self._create_labeled_field("Review Frequency", self.frequency_combo))

        self.form_layout.addLayout(timeline_row)

    def _add_details_section(self):
        """Add detailed fields for compliance management"""
        # Responsible person
        self.responsible_edit = QtWidgets.QLineEdit()
        self.responsible_edit.setPlaceholderText("Name or role of person responsible for this compliance area")
        _force_dark_text(self.responsible_edit)
        self.form_layout.addWidget(self._create_labeled_field("Responsible Person", self.responsible_edit))

        # Evidence required (multi-line for list)
        self.evidence_edit = QtWidgets.QTextEdit()
        self.evidence_edit.setPlaceholderText(
            "List required evidence/documentation (one per line):\n• Policies and procedures\n• Risk assessments\n• Training records\n• Audit reports")
        self.evidence_edit.setMaximumHeight(120)
        _force_dark_text(self.evidence_edit)
        self.form_layout.addWidget(self._create_labeled_field("Evidence Required", self.evidence_edit))

        # Row for documentation location and automation
        doc_automation_row = QtWidgets.QHBoxLayout()
        doc_automation_row.setSpacing(12)

        # Documentation location
        self.documentation_edit = QtWidgets.QLineEdit()
        self.documentation_edit.setPlaceholderText("e.g., SharePoint folder, compliance software, file server location")
        _force_dark_text(self.documentation_edit)

        # Automated monitoring checkbox
        self.automation_checkbox = QtWidgets.QCheckBox("Automated monitoring available")
        self.automation_checkbox.setStyleSheet("""
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

        doc_automation_row.addWidget(self._create_labeled_field("Documentation Location", self.documentation_edit))
        doc_automation_row.addWidget(self._create_labeled_field("Automation", self.automation_checkbox))

        self.form_layout.addLayout(doc_automation_row)

        # Additional notes
        self.notes_edit = QtWidgets.QTextEdit()
        self.notes_edit.setPlaceholderText(
            "Additional notes, special considerations, implementation challenges, or other relevant information...")
        self.notes_edit.setMaximumHeight(100)
        _force_dark_text(self.notes_edit)
        self.form_layout.addWidget(self._create_labeled_field("Notes", self.notes_edit))
        self.form_layout.addWidget(self._create_attachment_section())

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

    def _connect_signals(self):
        """Connect form signals for dynamic updates"""
        self.type_combo.currentTextChanged.connect(self._on_type_changed)

    def _on_type_changed(self, type_text: str):
        """Update form suggestions based on selected compliance type"""
        # Map display names to internal keys
        type_map = {
            "Financial & Banking": "financial",
            "Healthcare & Life Sciences": "healthcare",
            "Data Privacy & Protection": "data_privacy",
            "Industry-Specific": "industry_specific",
            "Environmental & Sustainability": "environmental",
            "Workplace Safety & Security": "safety",
            "Employment & Labor": "employment",
            "Custom/Other": "custom"
        }

        compliance_type = type_map.get(type_text, "custom")
        type_config = COMPLIANCE_TYPES.get(compliance_type, {})

        # Update authority placeholder with common examples
        common_regs = type_config.get("common_regulations", [])
        if common_regs:
            authority_examples = ", ".join(common_regs[:3]) + ("..." if len(common_regs) > 3 else "")
            self.authority_edit.setPlaceholderText(f"e.g., {authority_examples}")

        # Update evidence placeholder with typical requirements
        evidence_types = type_config.get("evidence_types", [])
        if evidence_types:
            evidence_text = "Typical evidence for this category:\n" + "\n".join(f"• {ev}" for ev in evidence_types[:4])
            self.evidence_edit.setPlaceholderText(evidence_text)

    def get_form_data(self) -> Dict[str, Any]:
        """Extract data from form fields"""
        # Parse evidence list from text
        evidence_text = self.evidence_edit.toPlainText().strip()
        evidence_list = []
        if evidence_text:
            for line in evidence_text.split('\n'):
                line = line.strip()
                if line:
                    # Remove bullet points if present
                    line = line.lstrip('•-*').strip()
                    if line:
                        evidence_list.append(line)

        return {
            "name": self.name_edit.text().strip(),
            "regulation_type": self.type_combo.currentText().lower().replace(" & ", "_").replace(" ", "_"),
            "authority": self.authority_edit.text().strip(),
            "description": self.description_edit.toPlainText().strip(),
            "current_status": self.status_combo.currentText().lower().replace(" ", "_"),
            "risk_level": self.risk_combo.currentText().lower(),
            "compliance_deadline": self.deadline_edit.date().toPython(),
            "review_frequency": self.frequency_combo.currentText().lower().replace("-", "_"),
            "responsible_person": self.responsible_edit.text().strip(),
            "evidence_required": evidence_list,
            "automated_monitoring": self.automation_checkbox.isChecked(),
            "documentation_location": self.documentation_edit.text().strip(),
            "notes": self.notes_edit.toPlainText().strip(),
            "attachments": self._attachments.copy()
        }

    def set_form_data(self, data: Dict[str, Any]):
        """Populate form with data"""
        self.name_edit.setText(data.get("name", ""))

        # Map internal type back to display name
        type_map = {
            "financial": "Financial & Banking",
            "healthcare": "Healthcare & Life Sciences",
            "data_privacy": "Data Privacy & Protection",
            "industry_specific": "Industry-Specific",
            "environmental": "Environmental & Sustainability",
            "safety": "Workplace Safety & Security",
            "employment": "Employment & Labor",
            "custom": "Custom/Other"
        }
        display_type = type_map.get(data.get("regulation_type", ""), "Custom/Other")
        type_index = self.type_combo.findText(display_type)
        if type_index >= 0:
            self.type_combo.setCurrentIndex(type_index)

        self.authority_edit.setText(data.get("authority", ""))
        self.description_edit.setText(data.get("description", ""))

        # Set status
        status_map = {
            "not_assessed": "Not Assessed",
            "compliant": "Compliant",
            "non_compliant": "Non-Compliant",
            "in_progress": "In Progress",
            "not_applicable": "Not Applicable"
        }
        display_status = status_map.get(data.get("current_status", ""), "Not Assessed")
        status_index = self.status_combo.findText(display_status)
        if status_index >= 0:
            self.status_combo.setCurrentIndex(status_index)

        # Set risk level
        risk_level = data.get("risk_level", "medium").title()
        risk_index = self.risk_combo.findText(risk_level)
        if risk_index >= 0:
            self.risk_combo.setCurrentIndex(risk_index)

        # Set deadline
        deadline = data.get("compliance_deadline")
        if isinstance(deadline, date):
            self.deadline_edit.setDate(QtCore.QDate(deadline))

        # Set frequency
        freq_map = {
            "as_needed": "As Needed",
            "monthly": "Monthly",
            "quarterly": "Quarterly",
            "semi_annual": "Semi-Annual",
            "annual": "Annual",
            "biennial": "Biennial"
        }
        display_freq = freq_map.get(data.get("review_frequency", ""), "Annual")
        freq_index = self.frequency_combo.findText(display_freq)
        if freq_index >= 0:
            self.frequency_combo.setCurrentIndex(freq_index)

        self.responsible_edit.setText(data.get("responsible_person", ""))

        # Set evidence list
        evidence_list = data.get("evidence_required", [])
        if evidence_list:
            evidence_text = "\n".join(f"• {item}" for item in evidence_list)
            self.evidence_edit.setText(evidence_text)

        self.automation_checkbox.setChecked(data.get("automated_monitoring", False))
        self.documentation_edit.setText(data.get("documentation_location", ""))
        self.notes_edit.setText(data.get("notes", ""))

        attachments = data.get("attachments", [])
        for attachment in attachments:
            if FileManager.validate_file_exists(attachment.file_path):
                self._add_attachment_chip(attachment)

    def clear_form(self):
        """Clear all form fields"""
        self.name_edit.clear()
        self.type_combo.setCurrentIndex(0)
        self.authority_edit.clear()
        self.description_edit.clear()
        self.status_combo.setCurrentIndex(0)
        self.risk_combo.setCurrentIndex(1)
        self.deadline_edit.setDate(QtCore.QDate.currentDate().addMonths(3))

        annual_index = self.frequency_combo.findText("Annual")
        if annual_index >= 0:
            self.frequency_combo.setCurrentIndex(annual_index)

        self.responsible_edit.clear()
        self.evidence_edit.clear()
        self.automation_checkbox.setChecked(False)
        self.documentation_edit.clear()
        self.notes_edit.clear()

        if hasattr(self, 'chips_flow'):
            for i in reversed(range(self.chips_flow.count())):
                item = self.chips_flow.itemAt(i)
                w = item.widget() if item else None
                self.chips_flow.takeAt(i)
                if w:
                    w.deleteLater()
            self._attachments.clear()

    def _create_attachment_section(self) -> QtWidgets.QWidget:
        """Create attachment management section"""
        section = QtWidgets.QWidget()
        section.setStyleSheet("background: transparent;")
        layout = QtWidgets.QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Attachment controls
        controls_row = QtWidgets.QHBoxLayout()
        controls_row.setSpacing(8)

        self.btn_attach = QtWidgets.QPushButton("Attach...")
        self.btn_attach.setFixedHeight(30)
        self.btn_attach.setStyleSheet("""
            QPushButton {
                background:#A5BBCF;
                color:#FFFFFF;
                border:1px solid #A5BBCF;
                border-radius:6px;
                padding:4px 8px;
                font-size:12px;
            }
            QPushButton:hover { background:#1f2937; border-color:#1f2937; }
        """)
        self.btn_attach.clicked.connect(self._attach_files)

        self.btn_capture = QtWidgets.QPushButton("Capture Screenshot")
        self.btn_capture.setFixedHeight(30)
        self.btn_capture.setStyleSheet("""
            QPushButton {
                background:#A5BBCF;
                color:#FFFFFF;
                border:1px solid #A5BBCF;
                border-radius:6px;
                padding:4px 8px;
                font-size:12px;
            }
            QPushButton:hover { background:#1f2937; border-color:#1f2937; }
        """)
        # Screenshot functionality will be connected by parent tab

        controls_row.addWidget(self.btn_attach)
        controls_row.addWidget(self.btn_capture)
        controls_row.addStretch()

        self.chips_area = QtWidgets.QWidget()
        self.chips_area.setStyleSheet("background: transparent;")
        self.chips_flow = FlowLayout(self.chips_area, margin=0, hspacing=6, vspacing=6)

        layout.addLayout(controls_row)
        layout.addWidget(self.chips_area)

        return self._create_labeled_field("Attachments", section)

    def _attach_files(self):
        """Open attachment dialog"""
        dialog = AttachmentDialog(self)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            attachment = dialog.get_attachment()
            if attachment and attachment not in self._attachments:
                self._add_attachment_chip(attachment)

    def _add_attachment_chip(self, attachment: AttachmentMetadata):
        """Add attachment chip to UI"""
        chip = AttachmentChip(attachment)
        chip.removed.connect(self._remove_attachment_chip)
        chip.edit_requested.connect(self._edit_attachment)
        self.chips_flow.addWidget(chip)
        self._attachments.append(attachment)

    def _remove_attachment_chip(self, attachment: AttachmentMetadata):
        """Remove attachment chip and data"""
        for i in reversed(range(self.chips_flow.count())):
            item = self.chips_flow.itemAt(i)
            w = item.widget()
            if isinstance(w, AttachmentChip) and w.attachment == attachment:
                self.chips_flow.takeAt(i)
                w.deleteLater()
                break
        self._attachments = [att for att in self._attachments if att != attachment]

    def _edit_attachment(self, attachment: AttachmentMetadata):
        """Edit attachment metadata"""
        dialog = AttachmentDialog(self, attachment)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            updated_attachment = dialog.get_attachment()
            if updated_attachment:
                # Update attachment in list
                for i, att in enumerate(self._attachments):
                    if att == attachment:
                        self._attachments[i] = updated_attachment
                        break

                # Update chip
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


# -------------------------
# Main Compliance Tab
# -------------------------

class ComplianceTab(QtWidgets.QWidget):
    requestScreenshot = QtCore.Signal(int)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None, policy_enforcer=None) -> None:
        super().__init__(parent)
        self._policy_enforcer = policy_enforcer
        _LOGGER.info("ComplianceTab initialized")

        # ---- scroller ----
        scroller = QtWidgets.QScrollArea(self)
        scroller.setObjectName("ComplianceScroll")
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
        card.setObjectName("ComplianceCard")
        card.setStyleSheet("""
            QFrame#ComplianceCard {
                background:#FFFFFF;
                border:1px solid #E5E7EB;
                border-radius:12px;
            }
            QFrame#ComplianceCard QLabel { background: transparent; }
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
            title="Compliance Requirements",
            subtitle="Document regulatory requirements, compliance status, and evidence management for your organization.",
            info_html=COMPLIANCE_INFO,
            icon_size_px=28,
            parent=card,
        )
        card_layout.addWidget(section)
        section.bind_scrollarea(self._scroller)

        # ---- organization overview section ----
        org_frame = QtWidgets.QFrame()
        org_frame.setObjectName("OrgOverview")
        org_frame.setStyleSheet("""
            QFrame#OrgOverview {
                background: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        card_layout.addWidget(org_frame)

        org_layout = QtWidgets.QVBoxLayout(org_frame)
        org_layout.setContentsMargins(6,6,6,6)
        org_layout.setSpacing(12)

        # Organization overview header
        org_header = QtWidgets.QLabel("Organization Overview")
        org_header.setStyleSheet("font-size:14px; color:#1F2937; font-weight:600; background:transparent;")
        org_layout.addWidget(org_header)

        # Organization overview form
        org_form_host = QtWidgets.QWidget()
        org_form_host.setStyleSheet("""background:transparent;""")
        org_form = _StackedLabelForm(org_form_host)

        # Industry and company size row
        industry_size_row = QtWidgets.QHBoxLayout()
        industry_size_row.setSpacing(12)

        self.industry_edit = QtWidgets.QLineEdit()
        self.industry_edit.setPlaceholderText("e.g., Healthcare, Financial Services, Manufacturing, Technology")
        _force_dark_text(self.industry_edit)

        self.company_size_combo = QtWidgets.QComboBox()
        self.company_size_combo.addItems(
            ["Micro (1-9 employees)", "Small (10-49 employees)", "Medium (50-249 employees)",
             "Large (250-999 employees)", "Enterprise (1000+ employees)"])
        self.company_size_combo.setCurrentText("Small (10-49 employees)")
        self.company_size_combo.setStyleSheet("""
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

        industry_size_row.addWidget(self._create_labeled_field("Industry Sector", self.industry_edit))
        industry_size_row.addWidget(self._create_labeled_field("Company Size", self.company_size_combo))
        org_form.addLayout(industry_size_row)

        # Geographic scope and business activities
        self.geographic_edit = QtWidgets.QLineEdit()
        self.geographic_edit.setPlaceholderText("Countries/regions where you operate (e.g., US, EU, Canada, Global)")
        _force_dark_text(self.geographic_edit)
        org_form.add_row("Geographic Scope", self.geographic_edit)

        self.activities_edit = QtWidgets.QTextEdit()
        self.activities_edit.setPlaceholderText(
            "Key business activities that may trigger compliance requirements:\n• Customer data processing\n• Financial transactions\n• Healthcare services\n• Manufacturing operations")
        self.activities_edit.setMaximumHeight(120)
        _force_dark_text(self.activities_edit)
        org_form.add_row("Business Activities", self.activities_edit)

        # Data types and third parties
        self.data_types_edit = QtWidgets.QTextEdit()
        self.data_types_edit.setPlaceholderText(
            "Types of data you collect/process:\n• Personal information (PII)\n• Payment data\n• Health records\n• Employee data\n• Proprietary business data")
        self.data_types_edit.setMaximumHeight(125)
        _force_dark_text(self.data_types_edit)
        org_form.add_row("Data Types Handled", self.data_types_edit)

        self.vendors_edit = QtWidgets.QTextEdit()
        self.vendors_edit.setPlaceholderText(
            "Key third-party vendors, processors, or service providers that may impact compliance:\n• Cloud providers\n• Payment processors\n• Software vendors\n• Consultants")
        self.vendors_edit.setMaximumHeight(120)
        _force_dark_text(self.vendors_edit)
        org_form.add_row("Third-Party Vendors", self.vendors_edit)

        org_layout.addWidget(org_form_host)

        # ---- compliance requirement form ----
        self.requirement_form = ComplianceRequirementForm()
        card_layout.addWidget(self.requirement_form)

        # ---- action buttons ----
        actions_row = QtWidgets.QHBoxLayout()
        actions_row.setSpacing(8)

        self.btn_quick_setup = QtWidgets.QPushButton("Quick Setup...")
        self.btn_quick_setup.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_quick_setup.setToolTip("Set up common requirements for your industry")

        self.btn_import = QtWidgets.QPushButton("Import...")
        self.btn_import.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_import.setToolTip("Import compliance requirements from file")

        actions_row.addWidget(self.btn_quick_setup, 0, QtCore.Qt.AlignLeft)
        actions_row.addWidget(self.btn_import, 0, QtCore.Qt.AlignLeft)
        actions_row.addStretch(1)

        # Cancel button (hidden by default)
        self.btn_cancel = QtWidgets.QPushButton("Cancel Edit")
        self.btn_cancel.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_cancel.setVisible(False)
        actions_row.addWidget(self.btn_cancel, 0, QtCore.Qt.AlignRight)

        self.btn_add = QtWidgets.QPushButton("Add Requirement")
        self.btn_add.setCursor(QtCore.Qt.PointingHandCursor)
        actions_row.addWidget(self.btn_add, 0, QtCore.Qt.AlignRight)

        card_layout.addLayout(actions_row)

        # ---- requirements table ----
        self.table = DraggableTableWidget(0, 8, card)
        self.table.setObjectName("ComplianceTable")
        self.table.setHorizontalHeaderLabels([
            "Requirement Name",
            "Type",
            "Authority",
            "Status",
            "Risk Level",
            "Deadline",
            "Responsible Person",
            "Attached Files"
        ])

        for c in range(self.table.columnCount()):
            item = self.table.horizontalHeaderItem(c)
            if item:
                item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        hdr = self.table.horizontalHeader()
        hdr.setStretchLastSection(False)
        hdr.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)  # Requirement name
        hdr.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)  # Type
        hdr.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)  # Authority
        hdr.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)  # Status
        hdr.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)  # Risk
        hdr.setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeToContents)  # Deadline
        hdr.setSectionResizeMode(6, QtWidgets.QHeaderView.Stretch)  # Responsible person
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
                border-top-left-radius: 6px;
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
        pal.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor("#F8FAFC"))
        pal.setColor(QtGui.QPalette.Text, QtGui.QColor("#0F172A"))
        pal.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor("#0F172A"))
        self.table.setPalette(pal)
        card_layout.addWidget(self.table)

        # Table action buttons
        table_actions = QtWidgets.QHBoxLayout()
        table_actions.addStretch(1)

        self.btn_edit = QtWidgets.QPushButton("Edit Requirement")
        self.btn_edit.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_duplicate = QtWidgets.QPushButton("Duplicate")
        self.btn_duplicate.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_delete = QtWidgets.QPushButton("Delete")
        self.btn_delete.setCursor(QtCore.Qt.PointingHandCursor)

        table_actions.addWidget(self.btn_edit)
        table_actions.addWidget(self.btn_duplicate)
        table_actions.addWidget(self.btn_delete)
        card_layout.addLayout(table_actions)

        # Mount scroller
        root_layout = QtWidgets.QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(scroller)

        # State management
        self._requirements: List[ComplianceRequirement] = []
        self._editing_index: Optional[int] = None
        self._original_requirement: Optional[ComplianceRequirement] = None

        # Initial scrollbar mode
        self._set_scrollbar_stealth(True)
        section.toggled.connect(lambda open_: self._set_scrollbar_stealth(not open_))

        # Connect signals
        self._connect_signals()

        self._load_compliance_data()
        # Setup drag-drop and screenshot functionality
        self.table.rowsReordered.connect(self._handle_row_reorder)

        # Screenshot tool setup
        self._shot_tool = ScreenshotTool(self)
        self.requestScreenshot.connect(self._launch_screenshot_for_row)
        self._shot_tool.screenshotSaved.connect(self._on_screenshot_saved)

        # Connect screenshot button in form
        self.requirement_form.btn_capture.clicked.connect(self._capture_new_screenshot)

    def _get_section_name(self) -> str:
        return "compliance"

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

    def _handle_row_reorder(self, old_index: int, new_index: int):
        """Handle when rows are reordered via drag-and-drop"""
        if 0 <= old_index < len(self._requirements) and 0 <= new_index < len(self._requirements):
            requirement = self._requirements.pop(old_index)
            self._requirements.insert(new_index, requirement)

            # Save to database after reordering
            self._save_compliance_data()

            # Refresh table
            self._repopulate_table()

            # Select the moved row
            self.table.selectRow(new_index)

    def _repopulate_table(self):
        """Refresh table display after drag-and-drop reordering"""
        self.table.setRowCount(0)
        for requirement in self._requirements:
            self._append_table_row(requirement)

    def _capture_new_screenshot(self):
        """Capture a screenshot for the current entry"""
        idx = self._selected_row()
        if idx < 0:
            idx = -1
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

        # Create screenshot attachment with metadata
        title = metadata.get('title', '') or f"Screenshot {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        description = metadata.get('description', '')
        markers = metadata.get('markers', [])

        notes_parts = []
        if description.strip():
            notes_parts.append(description.strip())

        for marker in markers:
            if isinstance(marker, dict) and marker.get('text', '').strip():
                marker_type = "Pin" if marker.get('kind') == 'pin' else "Arrow"
                marker_num = f" {marker.get('number', '')}" if marker.get('kind') == 'pin' else ""
                notes_parts.append(f"{marker_type}{marker_num}: {marker['text'].strip()}")

        notes_text = "\n".join(notes_parts)

        screenshot_attachment = AttachmentMetadata(
            file_path=screenshot_path,
            title=title,
            notes=notes_text,
            is_screenshot=True
        )

        if idx < 0:
            # Screenshot for entry form
            self.requirement_form._add_attachment_chip(screenshot_attachment)
        else:
            # Screenshot for existing requirement
            if 0 <= idx < len(self._requirements):
                self._requirements[idx].attachments.append(screenshot_attachment)
                self._populate_table_row(idx, self._requirements[idx])

    def _load_organization_overview(self) -> None:
        """Load organization overview data from database."""
        try:
            with DatabaseSession() as session:
                org_data = session.query(Compliance).first()

                if org_data:
                    # Load data into form fields
                    self.industry_edit.setText(org_data.industry_sector or "")

                    # Handle company size - extract just the first part before the parentheses
                    if org_data.geographic_scope:  # We'll repurpose this field temporarily
                        # For now, just set to first option if we have data
                        self.company_size_combo.setCurrentIndex(0)

                    self.geographic_edit.setText(org_data.geographic_scope or "")
                    self.activities_edit.setText(org_data.business_activities or "")
                    self.data_types_edit.setText(org_data.data_types_handled or "")
                    self.vendors_edit.setText(org_data.third_party_vendors or "")

                    _LOGGER.info("Loaded organization overview from database")
                else:
                    _LOGGER.info("No organization overview data found")

        except Exception as e:
            _LOGGER.error(f"Failed to load organization overview: {e}")

    def _save_organization_overview(self) -> None:
        """Save organization overview data to database."""
        try:
            with DatabaseSession() as session:
                # Get or create the single compliance record
                org_data = session.query(Compliance).first()
                if not org_data:
                    org_data = Compliance()
                    session.add(org_data)

                # Update fields
                org_data.industry_sector = self.industry_edit.text().strip()
                org_data.geographic_scope = self.geographic_edit.text().strip()
                org_data.business_activities = self.activities_edit.toPlainText().strip()
                org_data.data_types_handled = self.data_types_edit.toPlainText().strip()
                org_data.third_party_vendors = self.vendors_edit.toPlainText().strip()

                # Session context manager will automatically commit
                _LOGGER.info("Saved organization overview to database")

        except Exception as e:
            _LOGGER.error(f"Failed to save organization overview: {e}")

    def _load_compliance_data(self) -> None:
        """Load existing compliance requirements from database into the table."""
        self._load_organization_overview()
        try:
            with DatabaseSession() as session:
                db_requirements = session.query(DBComplianceRequirement).order_by(
                    DBComplianceRequirement.priority_rank.asc()
                ).all()

                for db_req in db_requirements:
                    # Initialize variables
                    deadline_date = None
                    evidence_list = []

                    # Parse evidence_required from JSON
                    if db_req.evidence_required:
                        try:
                            evidence_list = json.loads(db_req.evidence_required)
                        except (json.JSONDecodeError, TypeError):
                            evidence_list = []

                    # Parse compliance_deadline from string
                    if db_req.compliance_deadline:
                        try:
                            deadline_date = date.fromisoformat(db_req.compliance_deadline)
                        except (ValueError, TypeError):
                            pass  # deadline_date remains None

                    # Parse attachments from notes field
                    attachments = []
                    description_notes = db_req.notes or ""
                    if "__ATTACHMENTS__:" in description_notes:
                        try:
                            notes_part, attachments_json = description_notes.split("__ATTACHMENTS__:", 1)
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

                            # Clean the notes field
                            description_notes = notes_part.strip()
                        except Exception as e:
                            _LOGGER.error(f"Error parsing attachments: {e}")

                    requirement = ComplianceRequirement(
                        name=db_req.requirement_name,
                        regulation_type=db_req.regulation_type or "custom",
                        authority=db_req.authority or "",
                        description=db_req.description or "",
                        current_status=db_req.current_status or "not_assessed",
                        risk_level=db_req.risk_level or "medium",
                        compliance_deadline=deadline_date,
                        review_frequency=db_req.review_frequency or "annual",
                        responsible_person=db_req.responsible_person or "",
                        evidence_required=evidence_list,
                        automated_monitoring=db_req.automated_monitoring or False,
                        documentation_location=db_req.documentation_location or "",
                        notes=description_notes,  # Use cleaned notes
                        attachments=attachments  # Use parsed attachments
                    )

                    self._requirements.append(requirement)
                    self._append_table_row(requirement)

                _LOGGER.info(f"Loaded {len(db_requirements)} compliance requirements from database")

        except Exception as e:
            _LOGGER.error(f"Failed to load compliance requirements data: {e}")

    def _save_compliance_data(self) -> None:
        """Save current compliance requirements list to database."""
        _LOGGER.info(f"=== SAVE START: Attempting to save {len(self._requirements)} requirements ===")

        # Save organization overview first
        self._save_organization_overview()

        try:
            with DatabaseSession() as session:
                _LOGGER.info("Database session opened successfully")

                # Check if table exists
                from sqlalchemy import inspect, text
                inspector = inspect(session.bind)
                tables = inspector.get_table_names()
                _LOGGER.info(f"Available tables: {tables}")

                if 'compliance_requirements' not in tables:
                    _LOGGER.error("compliance_requirements table does not exist!")
                    return

                # Check current count before deletion
                current_count = session.execute(text("SELECT COUNT(*) FROM compliance_requirements")).scalar()
                _LOGGER.info(f"Current records in database before deletion: {current_count}")

                # Clear existing requirements
                deleted_count = session.query(DBComplianceRequirement).count()
                session.query(DBComplianceRequirement).delete()
                _LOGGER.info(f"Deleted {deleted_count} existing compliance requirements")

                # Save each requirement with priority rank based on order
                for rank, requirement in enumerate(self._requirements, 1):
                    _LOGGER.info(f"Processing requirement {rank}: {requirement.name}")

                    # Serialize evidence_required to JSON
                    evidence_json = ""
                    if requirement.evidence_required:
                        try:
                            evidence_json = json.dumps(requirement.evidence_required)
                            _LOGGER.info(f"Serialized evidence: {evidence_json}")
                        except (TypeError, ValueError) as e:
                            _LOGGER.warning(f"Failed to serialize evidence list: {e}")
                            evidence_json = "[]"

                    # Convert date to ISO string
                    deadline_str = ""
                    if requirement.compliance_deadline:
                        try:
                            deadline_str = requirement.compliance_deadline.isoformat()
                            _LOGGER.info(f"Deadline converted: {deadline_str}")
                        except AttributeError:
                            _LOGGER.warning(f"Failed to convert deadline: {requirement.compliance_deadline}")
                            deadline_str = ""

                    db_requirement = DBComplianceRequirement(
                        requirement_name=requirement.name,
                        priority_rank=rank,
                        regulation_type=requirement.regulation_type,
                        authority=requirement.authority,
                        description=requirement.description,
                        current_status=requirement.current_status,
                        risk_level=requirement.risk_level,
                        compliance_deadline=deadline_str,
                        review_frequency=requirement.review_frequency,
                        responsible_person=requirement.responsible_person,
                        evidence_required=evidence_json,
                        automated_monitoring=int(requirement.automated_monitoring),
                        documentation_location=requirement.documentation_location,
                        notes=requirement.notes
                    )
                    session.add(db_requirement)
                    _LOGGER.info(f"Added requirement to session: {requirement.name}")

                    session.flush()  # Get the ID for file management

                    # CRITICAL: Copy attachments to storage and update paths
                    if requirement.attachments:
                        updated_attachments = self._copy_attachments_to_storage(
                            db_requirement.id, requirement.attachments
                        )
                        # Update the requirement with new paths
                        requirement.attachments = updated_attachments

                        # Save attachment metadata as JSON in notes field
                        attachment_data = []
                        for att in requirement.attachments:
                            attachment_data.append({
                                'file_path': str(att.file_path),
                                'title': att.title,
                                'notes': att.notes,
                                'is_screenshot': att.is_screenshot
                            })

                        # Store attachment metadata in notes field
                        if db_requirement.notes:
                            db_requirement.notes += f"\n\n__ATTACHMENTS__:{json.dumps(attachment_data)}"
                        else:
                            db_requirement.notes = f"__ATTACHMENTS__:{json.dumps(attachment_data)}"

                # Verify session has pending changes
                _LOGGER.info(f"Session dirty objects: {len(session.dirty)}")
                _LOGGER.info(f"Session new objects: {len(session.new)}")

                # Session context manager will automatically commit
                _LOGGER.info("Exiting session context - should auto-commit")

            # Check if data was actually saved (outside the session)
            with DatabaseSession() as verify_session:
                final_count = verify_session.execute(text("SELECT COUNT(*) FROM compliance_requirements")).scalar()
                _LOGGER.info(f"Final count after save: {final_count}")

            _LOGGER.info(f"=== SAVE COMPLETE: Saved {len(self._requirements)} compliance requirements ===")

        except Exception as e:
            _LOGGER.error(f"Failed to save compliance requirements data: {e}")
            import traceback
            _LOGGER.error(f"Full traceback: {traceback.format_exc()}")

        except Exception as e:
            _LOGGER.error(f"Failed to save compliance requirements data: {e}")

    def clear_fields(self) -> None:
        """Clear all compliance requirements and form fields."""
        # Clear the table
        self.table.setRowCount(0)

        # Clear the requirements list
        self._requirements.clear()

        # Clean up all files for this section
        section = self._get_section_name()
        deleted_files = FileManager.cleanup_section_files(section)
        _LOGGER.info(f"Cleaned up {deleted_files} files during clear")

        # Clear the requirement form
        self._clear_requirement_form()

        # Clear organization overview fields
        self.industry_edit.clear()
        self.company_size_combo.setCurrentIndex(0)
        self.geographic_edit.clear()
        self.activities_edit.clear()
        self.data_types_edit.clear()
        self.vendors_edit.clear()

        # Reset editing state
        self._editing_index = None
        self._original_requirement = None
        self.btn_add.setText("Add Requirement")
        self.btn_cancel.setVisible(False)

        _LOGGER.info("Cleared all compliance requirements and form fields")

    def _create_labeled_field(self, label: str, field: QtWidgets.QWidget) -> QtWidgets.QWidget:
        """Create a labeled field widget"""
        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        lbl = QtWidgets.QLabel(label)
        lbl.setStyleSheet("font-size:13px; color:#334155; background:transparent;")
        layout.addWidget(lbl)
        layout.addWidget(field)

        return container

    def _connect_signals(self):
        """Connect all UI signals"""
        self.btn_add.clicked.connect(self._add_requirement)
        self.btn_edit.clicked.connect(self._edit_requirement)
        self.btn_duplicate.clicked.connect(self._duplicate_requirement)
        self.btn_delete.clicked.connect(self._delete_requirement)
        self.btn_cancel.clicked.connect(self._cancel_edit)
        self.btn_quick_setup.clicked.connect(self._show_quick_setup)
        self.btn_import.clicked.connect(self._import_requirements)

        self.table.itemDoubleClicked.connect(lambda *_: self._edit_requirement())
        self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._table_context_menu)

        # Add auto-save connections for Organization Overview fields
        self.industry_edit.textChanged.connect(self._save_organization_overview)
        self.company_size_combo.currentTextChanged.connect(self._save_organization_overview)
        self.geographic_edit.textChanged.connect(self._save_organization_overview)
        self.activities_edit.textChanged.connect(self._save_organization_overview)
        self.data_types_edit.textChanged.connect(self._save_organization_overview)
        self.vendors_edit.textChanged.connect(self._save_organization_overview)

    def _set_scrollbar_stealth(self, stealth: bool):
        """Toggle scrollbar visibility styling"""
        sb = self._scroller.verticalScrollBar()
        # if stealth:
        #     sb.setStyleSheet("""
        #         QScrollBar:vertical {
        #             background: #F3F4F6;
        #             width: 12px;
        #             margin: 8px 2px 8px 0;
        #         }
        #         QScrollBar::handle:vertical {
        #             background: #F3F4F6;
        #             border-radius: 6px;
        #             min-height: 24px;
        #         }
        #         QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; width: 0; }
        #         QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: #F3F4F6; }
        #     """)
        # else:
        #     sb.setStyleSheet("""
        #         QScrollBar:vertical {
        #             background: transparent;
        #             width: 12px;
        #             margin: 8px 2px 8px 0;
        #         }
        #         QScrollBar::handle:vertical {
        #             background: #D1D5DB;
        #             border-radius: 6px;
        #             min-height: 24px;
        #         }
        #         QScrollBar::handle:vertical:hover { background: #9CA3AF; }
        #         QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; width: 0; }
        #         QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
        #     """)
        sb.style().unpolish(sb)
        sb.style().polish(sb)
        sb.update()

    # ---- Core CRUD operations ----

    def _add_requirement(self):
        """Add or update a compliance requirement with database saving"""
        form_data = self.requirement_form.get_form_data()

        if not form_data["name"].strip():
            form_data["name"] = f"Untitled Requirement — {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        # Create requirement object
        requirement = ComplianceRequirement(
            name=form_data["name"],
            regulation_type=form_data["regulation_type"],
            authority=form_data["authority"],
            description=form_data["description"],
            current_status=form_data["current_status"],
            risk_level=form_data["risk_level"],
            compliance_deadline=form_data["compliance_deadline"],
            review_frequency=form_data["review_frequency"],
            responsible_person=form_data["responsible_person"],
            evidence_required=form_data["evidence_required"],
            automated_monitoring=form_data["automated_monitoring"],
            documentation_location=form_data["documentation_location"],
            notes=form_data["notes"]
        )

        if self._editing_index is not None:
            # Update existing requirement
            insert_pos = min(self._editing_index, len(self._requirements))
            self._requirements.insert(insert_pos, requirement)
            self.table.insertRow(insert_pos)
            self._populate_table_row(insert_pos, requirement)

            self.table.selectRow(insert_pos)
            self.table.scrollToItem(self.table.item(insert_pos, 0), QtWidgets.QAbstractItemView.PositionAtCenter)

            self._editing_index = None
            self._original_requirement = None
            self.btn_add.setText("Add Requirement")
            self.btn_cancel.setVisible(False)
        else:
            # Add new requirement
            self._requirements.append(requirement)
            self._append_table_row(requirement)

            new_row = self.table.rowCount() - 1
            if new_row >= 0:
                self.table.selectRow(new_row)
                self.table.scrollToItem(self.table.item(new_row, 0), QtWidgets.QAbstractItemView.PositionAtCenter)

        # Save to database after any add/update
        self._save_compliance_data()

        self._clear_requirement_form()

    def _edit_requirement(self):
        """Load selected requirement for editing"""
        idx = self._selected_row()
        if idx < 0:
            return

        if self._has_unsaved_changes():
            reply = QtWidgets.QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Load the selected requirement anyway?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            if reply != QtWidgets.QMessageBox.Yes:
                return

        requirement = self._requirements[idx]

        # Clear form and load data
        self._clear_requirement_form()
        self._load_requirement_into_form(requirement)

        # Set editing mode
        self._editing_index = idx
        self._original_requirement = self._copy_requirement(requirement)

        # Remove from table
        self.table.removeRow(idx)
        del self._requirements[idx]

        # Update UI
        self.btn_add.setText("Update Requirement")
        self.btn_cancel.setVisible(True)

    def _duplicate_requirement(self):
        """Duplicate selected requirement"""
        idx = self._selected_row()
        if idx < 0:
            return

        original = self._requirements[idx]
        duplicate = self._copy_requirement(original)
        duplicate.name = f"Copy of {duplicate.name}"

        self._requirements.append(duplicate)
        self._append_table_row(duplicate)

        new_row = self.table.rowCount() - 1
        if new_row >= 0:
            self.table.selectRow(new_row)

    def _delete_requirement(self):
        """Delete selected requirement and save to database"""
        idx = self._selected_row()
        if idx < 0:
            return

        reply = QtWidgets.QMessageBox.question(
            self,
            "Delete Requirement",
            "Remove the selected compliance requirement?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )

        if reply == QtWidgets.QMessageBox.Yes:
            # Clean up files before removing from database
            requirement = self._requirements[idx]
            self._cleanup_item_files(requirement.attachments)

            self.table.removeRow(idx)
            del self._requirements[idx]

            # Save to database after deletion
            self._save_compliance_data()

    def _cancel_edit(self):
        """Cancel current editing"""
        if self._editing_index is None or self._original_requirement is None:
            return

        if self._has_unsaved_changes():
            reply = QtWidgets.QMessageBox.question(
                self,
                "Cancel Edit",
                "Are you sure? Any changes will be lost.",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            if reply != QtWidgets.QMessageBox.Yes:
                return

        # Restore original requirement
        insert_pos = min(self._editing_index, len(self._requirements))
        self._requirements.insert(insert_pos, self._original_requirement)
        self.table.insertRow(insert_pos)
        self._populate_table_row(insert_pos, self._original_requirement)

        self.table.selectRow(insert_pos)
        self.table.scrollToItem(self.table.item(insert_pos, 0), QtWidgets.QAbstractItemView.PositionAtCenter)

        # Clear form and reset state
        self._clear_requirement_form()
        self._editing_index = None
        self._original_requirement = None
        self.btn_add.setText("Add Requirement")
        self.btn_cancel.setVisible(False)

    # ---- Table management ----

    def _append_table_row(self, requirement: ComplianceRequirement):
        """Add a new row to the table"""
        row = self.table.rowCount()
        self.table.insertRow(row)
        self._populate_table_row(row, requirement)

    def _populate_table_row(self, row: int, requirement: ComplianceRequirement):
        """Populate table row with requirement data"""

        def _cell(text: str) -> QtWidgets.QTableWidgetItem:
            item = QtWidgets.QTableWidgetItem(text)
            item.setFlags(item.flags() ^ QtCore.Qt.ItemIsEditable)
            return item

        # Format display values
        type_display = requirement.regulation_type.replace("_", " ").title()
        status_display = requirement.current_status.replace("_", " ").title()
        risk_display = requirement.risk_level.title()

        # Fix the deadline display - handle both date objects and strings
        deadline_display = "Not Set"
        if requirement.compliance_deadline:
            if isinstance(requirement.compliance_deadline, str):
                deadline_display = requirement.compliance_deadline
            else:
                deadline_display = requirement.compliance_deadline.strftime("%Y-%m-%d")

        self.table.setItem(row, 0, _cell(requirement.name))
        self.table.setItem(row, 1, _cell(type_display))
        self.table.setItem(row, 2, _cell(requirement.authority))
        self.table.setItem(row, 3, _cell(status_display))
        self.table.setItem(row, 4, _cell(risk_display))
        self.table.setItem(row, 5, _cell(deadline_display))
        self.table.setItem(row, 6, _cell(requirement.responsible_person))
        files_text = ", ".join(att.display_name for att in requirement.attachments) if requirement.attachments else ""
        self.table.setItem(row, 7, _cell(files_text))

    def _selected_row(self) -> int:
        """Get selected row index"""
        selection = self.table.selectionModel().selectedRows()
        return selection[0].row() if selection else -1

    def _table_context_menu(self, pos: QtCore.QPoint):
        """Show context menu for table"""
        idx = self.table.indexAt(pos).row()
        if idx < 0:
            return

        menu = QtWidgets.QMenu(self)
        edit_action = menu.addAction("Edit Requirement")
        duplicate_action = menu.addAction("Duplicate")
        menu.addSeparator()
        delete_action = menu.addAction("Delete")

        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action == edit_action:
            self._edit_requirement()
        elif action == duplicate_action:
            self._duplicate_requirement()
        elif action == delete_action:
            self._delete_requirement()

    # ---- Form management ----

    def _load_requirement_into_form(self, requirement: ComplianceRequirement):
        """Load requirement data into form fields"""
        form_data = {
            "name": requirement.name,
            "regulation_type": requirement.regulation_type,
            "authority": requirement.authority,
            "description": requirement.description,
            "current_status": requirement.current_status,
            "risk_level": requirement.risk_level,
            "compliance_deadline": requirement.compliance_deadline,
            "review_frequency": requirement.review_frequency,
            "responsible_person": requirement.responsible_person,
            "evidence_required": requirement.evidence_required,
            "automated_monitoring": requirement.automated_monitoring,
            "documentation_location": requirement.documentation_location,
            "notes": requirement.notes,
            "attachments": requirement.attachments
        }
        self.requirement_form.set_form_data(form_data)

    def _clear_requirement_form(self):
        """Clear the requirement form"""
        self.requirement_form.clear_form()

    def _has_unsaved_changes(self) -> bool:
        """Check if form has unsaved changes"""
        form_data = self.requirement_form.get_form_data()
        return any(str(v).strip() for k, v in form_data.items()
                   if k != "compliance_deadline" and v) or \
            (form_data.get("compliance_deadline") != date.today() + QtCore.QDate(0, 3, 0).toPython())

    def _copy_requirement(self, requirement: ComplianceRequirement) -> ComplianceRequirement:
        """Create a deep copy of a requirement"""
        return ComplianceRequirement(
            name=requirement.name,
            regulation_type=requirement.regulation_type,
            authority=requirement.authority,
            description=requirement.description,
            current_status=requirement.current_status,
            risk_level=requirement.risk_level,
            compliance_deadline=requirement.compliance_deadline,
            review_frequency=requirement.review_frequency,
            responsible_person=requirement.responsible_person,
            evidence_required=requirement.evidence_required.copy(),
            automated_monitoring=requirement.automated_monitoring,
            documentation_location=requirement.documentation_location,
            notes=requirement.notes,
            attachments=requirement.attachments.copy()
        )

    # ---- Quick setup and import ----

    def _show_quick_setup(self):
        """Show quick setup dialog for common industry requirements"""
        dialog = ComplianceQuickSetupDialog(self)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            selected_requirements = dialog.get_selected_requirements()
            for req_data in selected_requirements:
                requirement = ComplianceRequirement(**req_data)
                self._requirements.append(requirement)
                self._append_table_row(requirement)

    def _import_requirements(self):
        """Import requirements from file"""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Import Compliance Requirements",
            "",
            "JSON Files (*.json);;CSV Files (*.csv);;All Files (*)"
        )

        if file_path:
            try:
                # Implementation would handle JSON/CSV import
                QtWidgets.QMessageBox.information(
                    self,
                    "Import",
                    f"Import functionality would process: {file_path}"
                )
            except Exception as e:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Import Error",
                    f"Failed to import file: {str(e)}"
                )


# -------------------------
# Quick Setup Dialog
# -------------------------

class ComplianceQuickSetupDialog(QtWidgets.QDialog):
    """Dialog for quickly setting up common compliance requirements"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Compliance Quick Setup")
        self.setModal(True)
        self.resize(700, 500)
        # self.setStyleSheet("background-color: rgb(255, 255, 255);")

        self.setStyleSheet("""
            QDialog {
                background-color: rgb(255, 255, 255);
            }
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
        self._setup_ui()

    def _setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        header = QtWidgets.QLabel("Select Industry-Common Requirements")
        header.setStyleSheet("font-size:16px; color:#1F2937; font-weight:600;")
        layout.addWidget(header)

        desc = QtWidgets.QLabel(
            "Choose from pre-configured compliance requirements commonly found in your industry sector.")
        desc.setStyleSheet("font-size:13px; color:#6B7280; margin-bottom:8px;")
        layout.addWidget(desc)

        # Industry selector
        industry_row = QtWidgets.QHBoxLayout()
        industry_label = QtWidgets.QLabel("Industry:")
        industry_label.setStyleSheet("font-size:13px; color:#374151; font-weight:500;")

        self.industry_combo = QtWidgets.QComboBox()
        self.industry_combo.setStyleSheet("""
                    QComboBox {
                        background: white;
                        color: black;
                        padding: 4px 8px;
                    }
                """)
        self.industry_combo.addItems([
            "Financial & Banking",
            "Healthcare & Life Sciences",
            "Data Privacy & Protection",
            "Technology/SaaS",
            "Manufacturing",
            "Retail/E-commerce",
            "Education",
            "Government/Public Sector"
        ])
        self.industry_combo.currentTextChanged.connect(self._update_requirements_list)

        industry_row.addWidget(industry_label)
        industry_row.addWidget(self.industry_combo)
        industry_row.addStretch(1)
        layout.addLayout(industry_row)

        # Requirements checklist
        self.requirements_list = QtWidgets.QListWidget()
        self.requirements_list.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        self.requirements_list.setStyleSheet("""
            QListWidget {
                background: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                padding: 8px;
            }
            QListWidget::item {
                padding: 8px;
                margin: 2px;
                border-radius: 4px;
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
            }
            QListWidget::item:selected {
                background: #EBF4FF;
                border: 1px solid #3B82F6;
                color: #1E40AF;
            }
            QListWidget::item:hover {
                background: #F0F9FF;
            }
        """)
        layout.addWidget(self.requirements_list)

        # Selection controls
        select_row = QtWidgets.QHBoxLayout()
        self.btn_select_all = QtWidgets.QPushButton("Select All")
        self.btn_select_none = QtWidgets.QPushButton("Select None")

        self.btn_select_all.clicked.connect(self._select_all)
        self.btn_select_none.clicked.connect(self._select_none)

        select_row.addWidget(self.btn_select_all)
        select_row.addWidget(self.btn_select_none)
        select_row.addStretch(1)
        layout.addLayout(select_row)

        # Dialog buttons
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch(1)

        cancel_btn = QtWidgets.QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        import_btn = QtWidgets.QPushButton("Add Selected Requirements")
        import_btn.clicked.connect(self.accept)

        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(import_btn)
        layout.addLayout(button_layout)

        # Initialize with first industry
        self._update_requirements_list()

    def _select_all(self):
        """Select all requirements"""
        for i in range(self.requirements_list.count()):
            self.requirements_list.item(i).setSelected(True)

    def _select_none(self):
        """Deselect all requirements"""
        self.requirements_list.clearSelection()

    def _update_requirements_list(self):
        """Update requirements list based on selected industry"""
        industry = self.industry_combo.currentText()
        self.requirements_list.clear()

        # Sample requirements by industry
        industry_requirements = {
            "Financial & Banking": [
                ("SOX Compliance - Internal Controls", "financial", "SEC"),
                ("PCI DSS - Payment Card Security", "financial", "PCI SSC"),
                ("Anti-Money Laundering (AML)", "financial", "FinCEN"),
                ("FFIEC Cybersecurity Guidelines", "financial", "FFIEC"),
                ("Customer Due Diligence (CDD)", "financial", "FinCEN")
            ],
            "Healthcare & Life Sciences": [
                ("HIPAA Privacy Rule", "healthcare", "HHS OCR"),
                ("HIPAA Security Rule", "healthcare", "HHS OCR"),
                ("HITECH Breach Notification", "healthcare", "HHS OCR"),
                ("FDA 21 CFR Part 11 - Electronic Records", "healthcare", "FDA"),
                ("Clinical Trial Regulations - GCP", "healthcare", "FDA")
            ],
            "Data Privacy & Protection": [
                ("GDPR - Data Processing", "data_privacy", "EU DPAs"),
                ("CCPA - Consumer Privacy Rights", "data_privacy", "California AG"),
                ("Data Breach Notification", "data_privacy", "Various"),
                ("Privacy Policy Requirements", "data_privacy", "FTC"),
                ("Cookie Consent Management", "data_privacy", "Various")
            ],
            "Technology/SaaS": [
                ("SOC 2 Type II - Security Controls", "industry_specific", "AICPA"),
                ("ISO 27001 - Information Security", "industry_specific", "ISO"),
                ("Software License Compliance", "industry_specific", "Various"),
                ("API Security Standards", "industry_specific", "OWASP"),
                ("Cloud Security Compliance", "industry_specific", "CSA")
            ],
            "Manufacturing": [
                ("OSHA Workplace Safety", "safety", "OSHA"),
                ("EPA Environmental Compliance", "environmental", "EPA"),
                ("Quality Management - ISO 9001", "industry_specific", "ISO"),
                ("Product Safety Standards", "safety", "CPSC"),
                ("Hazardous Materials Handling", "safety", "DOT/EPA")
            ],
            "Retail/E-commerce": [
                ("PCI DSS - Payment Processing", "financial", "PCI SSC"),
                ("FTC Fair Credit Reporting", "employment", "FTC"),
                ("Consumer Protection Laws", "industry_specific", "FTC"),
                ("Product Labeling Requirements", "industry_specific", "FDA/FTC"),
                ("Accessibility Compliance - ADA", "employment", "DOJ")
            ],
            "Education": [
                ("FERPA - Student Privacy", "data_privacy", "ED"),
                ("COPPA - Children's Online Privacy", "data_privacy", "FTC"),
                ("Title IX - Nondiscrimination", "employment", "ED OCR"),
                ("Campus Security - Clery Act", "safety", "ED"),
                ("Accessibility - Section 504", "employment", "ED OCR")
            ],
            "Government/Public Sector": [
                ("FISMA - Federal Information Security", "safety", "NIST"),
                ("Freedom of Information Act (FOIA)", "data_privacy", "DOJ"),
                ("Government Ethics Rules", "employment", "OGE"),
                ("Public Records Management", "industry_specific", "NARA"),
                ("Procurement Regulations - FAR", "industry_specific", "GSA")
            ]
        }

        requirements = industry_requirements.get(industry, [])
        for req_name, req_type, authority in requirements:
            item = QtWidgets.QListWidgetItem(f"{req_name} ({authority})")
            item.setData(QtCore.Qt.UserRole, {
                "name": req_name,
                "regulation_type": req_type,
                "authority": authority
            })
            self.requirements_list.addItem(item)

    def get_selected_requirements(self) -> List[Dict[str, Any]]:
        """Get selected requirements as data dictionaries"""
        selected_reqs = []
        for item in self.requirements_list.selectedItems():
            req_data = item.data(QtCore.Qt.UserRole)
            if req_data:
                # Create complete requirement data with defaults
                full_req = {
                    "name": req_data["name"],
                    "regulation_type": req_data["regulation_type"],
                    "authority": req_data["authority"],
                    "description": f"Standard {req_data['name']} compliance requirement.",
                    "current_status": "not_assessed",
                    "risk_level": "medium",
                    "compliance_deadline": date.today() + QtCore.QDate(0, 6, 0).toPython(),  # 6 months from now
                    "review_frequency": "annual",
                    "responsible_person": "",
                    "evidence_required": [],
                    "automated_monitoring": False,
                    "documentation_location": "",
                    "notes": f"Auto-generated requirement for {req_data['name']}. Please review and customize as needed.",
                    "attachments": []
                }
                selected_reqs.append(full_req)
        return selected_reqs
