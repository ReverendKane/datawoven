"""
Project Setup Page - Step 2 of Admin Setup Wizard
Collects basic organizational information and project configuration.
"""

import re
from typing import Dict, Any, Tuple
from PySide6 import QtWidgets, QtCore, QtGui
from discovery_assistant.wizard_base import WizardPage
from discovery_assistant.ui.widgets.styled_checkbox import StyledCheckBox

class ProjectSetupPage(WizardPage):
    """
    Step 2: Project Setup page for collecting organizational context and project configuration.
    Matches the styling and architecture of existing wizard pages.
    """

    def __init__(self, parent=None):
        super().__init__("Project Setup", parent)
        self._setup_ui()
        self._connect_signals()

        # Initial validation check
        self._validate_form()

    def _setup_ui(self):
        """Set up the user interface components matching established patterns."""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)

        # Header section
        header_layout = self._create_header()
        layout.addLayout(header_layout)

        # Main content area
        content_widget = self._create_content_area()
        layout.addWidget(content_widget, 1)

    def _create_header(self) -> QtWidgets.QVBoxLayout:
        """Create page header with title and description."""
        layout = QtWidgets.QVBoxLayout()

        # Title
        title = QtWidgets.QLabel("Project Setup")
        title.setObjectName("pageTitle")
        title.setStyleSheet("""
            #pageTitle {
                font-size: 24px;
                font-weight: 600;
                color: #F9FAFB;
                margin-bottom: 8px;
            }
        """)

        # Description
        description = QtWidgets.QLabel(
            "Configure basic information about your organization and discovery project. "
            "This information will be used to contextualize the data collection process and "
            "provide support contact details to respondents throughout their discovery experience.\n\n"
            "Required fields are marked with an asterisk (*). This information helps ensure "
            "respondents have proper context and support during the discovery process."
        )
        description.setWordWrap(True)
        description.setObjectName("pageDescription")
        description.setStyleSheet("""
            #pageDescription {
                font-size: 14px;
                color: #D1D5DB;
                line-height: 1.5;
                margin-bottom: 10px;
            }
        """)

        layout.addWidget(title)
        layout.addWidget(description)

        return layout

    def _create_content_area(self) -> QtWidgets.QWidget:
        """Create the main content area with form sections."""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)

        # Organization information section
        org_group = self._create_organization_section()
        layout.addWidget(org_group)

        # Add spacing to match welcome screen
        layout.addSpacing(25)

        # Administrator contact section
        admin_group = self._create_administrator_section()
        layout.addWidget(admin_group)

        # Add spacing to match welcome screen
        layout.addSpacing(25)

        # Project configuration section
        project_group = self._create_project_section()
        layout.addWidget(project_group)

        # Add spacer to prevent stretching
        layout.addStretch()

        return widget

    def _create_organization_section(self) -> QtWidgets.QGroupBox:
        """Create organization information section."""
        group = QtWidgets.QGroupBox("Organization Information")
        group.setObjectName("orgGroup")
        layout = QtWidgets.QVBoxLayout(group)
        layout.setContentsMargins(18, 15, 18, 15)
        layout.setSpacing(5)

        # Organization name (required)
        org_label = QtWidgets.QLabel("Organization Name *")
        org_label.setStyleSheet("color: #F9FAFB; font-weight: 500; margin-bottom: 3px;")
        layout.addWidget(org_label)

        self.org_name_input = QtWidgets.QLineEdit()
        self.org_name_input.setPlaceholderText("Enter your organization or company name")
        layout.addWidget(self.org_name_input)

        layout.addSpacing(12)  # Space between field groups

        # Project description (optional)
        desc_label = QtWidgets.QLabel("Project Description")
        desc_label.setStyleSheet("color: #F9FAFB; font-weight: 500; margin-bottom: 3px;")
        layout.addWidget(desc_label)

        self.project_desc_input = QtWidgets.QTextEdit()
        self.project_desc_input.setPlaceholderText("Brief description of what this discovery project aims to accomplish (optional)")
        self.project_desc_input.setMaximumHeight(80)
        self.project_desc_input.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        layout.addWidget(self.project_desc_input)

        self._apply_group_style(group)
        return group

    def _create_administrator_section(self) -> QtWidgets.QGroupBox:
        """Create administrator contact section."""
        group = QtWidgets.QGroupBox("Administrator Contact")
        group.setObjectName("adminGroup")
        layout = QtWidgets.QVBoxLayout(group)
        layout.setContentsMargins(18, 15, 18, 15)
        layout.setSpacing(5)

        # Administrator name (required)
        admin_name_label = QtWidgets.QLabel("Administrator Name *")
        admin_name_label.setStyleSheet("color: #F9FAFB; font-weight: 500; margin-bottom: 3px; margin-left: 0px;")
        layout.addWidget(admin_name_label)

        self.admin_name_input = QtWidgets.QLineEdit()
        self.admin_name_input.setPlaceholderText("Full name of the administrator")
        layout.addWidget(self.admin_name_input)

        layout.addSpacing(12)  # Space between field groups

        # Administrator email (required)
        admin_email_label = QtWidgets.QLabel("Administrator Email *")
        admin_email_label.setStyleSheet("color: #F9FAFB; font-weight: 500; margin-bottom: 3px; margin-left: 0px;")
        layout.addWidget(admin_email_label)

        self.admin_email_input = QtWidgets.QLineEdit()
        self.admin_email_input.setPlaceholderText("Email address for respondent support")
        layout.addWidget(self.admin_email_input)

        # Email validation indicator
        self.email_status_label = QtWidgets.QLabel()
        self.email_status_label.setFixedHeight(20)
        layout.addWidget(self.email_status_label)

        layout.addSpacing(8)  # Small space before note

        # Contact note
        contact_note = QtWidgets.QLabel("This contact information will be displayed to respondents for support.")
        contact_note.setStyleSheet("color: #9CA3AF; font-size: 12px; font-style: italic;")
        contact_note.setWordWrap(True)
        layout.addWidget(contact_note)

        self._apply_group_style(group)
        return group

    def _create_project_section(self) -> QtWidgets.QGroupBox:
        """Create project configuration section."""
        group = QtWidgets.QGroupBox("Project Configuration")
        group.setObjectName("projectGroup")
        layout = QtWidgets.QVBoxLayout(group)
        layout.setContentsMargins(18, 15, 18, 15)  # Match title left margin
        layout.setSpacing(15)

        # Timeline checkbox
        self.timeline_checkbox = StyledCheckBox(
            "Set completion timeline for this project",
            bg_color="#666666",  # unchecked background
            bg_color_checked="#000000",  # checked background
            indicator_size=16  # or whatever size you want
        )
        layout.addWidget(self.timeline_checkbox)

        # Timeline date picker (initially hidden)
        timeline_layout = QtWidgets.QFormLayout()
        timeline_layout.setSpacing(10)

        timeline_label = QtWidgets.QLabel("Target Completion Date")
        timeline_label.setStyleSheet("color: #F9FAFB; font-weight: 500; margin-left: 25px;")

        self.timeline_date = QtWidgets.QDateEdit()
        self.timeline_date.setDate(QtCore.QDate.currentDate().addDays(30))  # Default to 30 days from now
        self.timeline_date.setCalendarPopup(True)
        self.timeline_date.setFixedWidth(150)

        timeline_layout.addRow(timeline_label, self.timeline_date)

        self.timeline_widget = QtWidgets.QWidget()
        self.timeline_widget.setLayout(timeline_layout)
        self.timeline_widget.setVisible(False)

        layout.addWidget(self.timeline_widget)

        # Organizational context (optional)
        context_label = QtWidgets.QLabel("Organizational Context / Notes")
        context_label.setStyleSheet("color: #F9FAFB; font-weight: 500;")
        layout.addWidget(context_label)

        self.context_input = QtWidgets.QTextEdit()
        self.context_input.setPlaceholderText("Any specific focus areas, constraints, or context that respondents should be aware of (optional)")
        self.context_input.setMaximumHeight(100)
        self.context_input.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        layout.addWidget(self.context_input)

        self._apply_group_style(group)
        return group

    def _apply_group_style(self, group: QtWidgets.QGroupBox):
        """Apply consistent styling to group boxes."""
        group.setStyleSheet("""
            QGroupBox {
                font-weight: 500;
                border: 2px solid #404040;
                border-radius: 8px;
                margin-top: 16px;
                padding-top: 15px;
                font-size: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #F9FAFB;
                font-size: 16px;
                font-weight: bold;
            }
        """)

    def _connect_signals(self):
        """Connect UI signals for real-time validation."""
        # Form validation triggers
        self.org_name_input.textChanged.connect(self._validate_form)
        self.admin_name_input.textChanged.connect(self._validate_form)
        self.admin_email_input.textChanged.connect(self._validate_email)

        # Timeline checkbox toggle
        self.timeline_checkbox.toggled.connect(self._toggle_timeline)

    def _validate_email(self):
        """Validate email format and update status indicator."""
        email = self.admin_email_input.text().strip()

        if not email:
            self.email_status_label.setText("")
            self.email_status_label.setStyleSheet("")
        else:
            # Simple email validation regex
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            is_valid = re.match(email_pattern, email) is not None

            if is_valid:
                self.email_status_label.setText("✓ Valid email format")
                self.email_status_label.setStyleSheet("color: #10B981; font-size: 12px;")
            else:
                self.email_status_label.setText("✗ Invalid email format")
                self.email_status_label.setStyleSheet("color: #EF4444; font-size: 12px;")

        self._validate_form()

    def _toggle_timeline(self, checked: bool):
        """Toggle visibility of timeline date picker."""
        self.timeline_widget.setVisible(checked)

    def _validate_form(self):
        """Validate all required form fields."""
        org_name = self.org_name_input.text().strip()
        admin_name = self.admin_name_input.text().strip()
        admin_email = self.admin_email_input.text().strip()

        # Check if all required fields are filled
        has_required = bool(org_name and admin_name and admin_email)

        # Check email validity if provided
        email_valid = True
        if admin_email:
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            email_valid = re.match(email_pattern, admin_email) is not None

        can_proceed = has_required and email_valid
        self.canProceed.emit(can_proceed)

    def showEvent(self, event):
        """Handle page show event to apply input styling."""
        super().showEvent(event)
        self._apply_input_styles()

    def _apply_input_styles(self):
        """Apply styling to form inputs with minimal custom heights."""
        input_style = """
            QLineEdit {
                background-color: #404040;
                border: 1px solid #606060;
                border-radius: 6px;
                padding: 8px 12px;
                color: #F9FAFB;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #808080;
                background-color: #606060;
            }
            QTextEdit {
                background-color: #404040;
                border: 1px solid #606060;
                border-radius: 6px;
                padding: 8px 12px;
                color: #F9FAFB;
                font-size: 14px;
            }
            QTextEdit:focus {
                border-color: #808080;
                background-color: #606060;
            }
        """
        self.setStyleSheet(self.styleSheet() + input_style)

    # WizardPage interface implementation
    def validate_page(self) -> Tuple[bool, str]:
        """Validate the page data."""
        org_name = self.org_name_input.text().strip()
        admin_name = self.admin_name_input.text().strip()
        admin_email = self.admin_email_input.text().strip()

        # Check required fields
        if not org_name:
            return False, "Organization name is required."

        if not admin_name:
            return False, "Administrator name is required."

        if not admin_email:
            return False, "Administrator email is required."

        # Validate email format
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, admin_email):
            return False, "Please enter a valid email address."

        return True, ""

    def collect_data(self) -> Dict[str, Any]:
        """Collect page data for wizard."""
        data = {
            "organization_name": self.org_name_input.text().strip(),
            "project_description": self.project_desc_input.toPlainText().strip(),
            "administrator_name": self.admin_name_input.text().strip(),
            "administrator_email": self.admin_email_input.text().strip(),
            "has_timeline": self.timeline_checkbox.isChecked(),
            "organizational_context": self.context_input.toPlainText().strip()
        }

        # Add timeline date if enabled
        if self.timeline_checkbox.isChecked():
            data["timeline_date"] = self.timeline_date.date().toString("yyyy-MM-dd")

        return data

    def load_data(self, data: Dict[str, Any]) -> None:
        """Load existing data into the page."""
        # Load organization information
        self.org_name_input.setText(data.get("organization_name", ""))
        self.project_desc_input.setPlainText(data.get("project_description", ""))

        # Load administrator information
        self.admin_name_input.setText(data.get("administrator_name", ""))
        self.admin_email_input.setText(data.get("administrator_email", ""))

        # Load project configuration
        has_timeline = data.get("has_timeline", False)
        self.timeline_checkbox.setChecked(has_timeline)
        self._toggle_timeline(has_timeline)

        if "timeline_date" in data:
            date = QtCore.QDate.fromString(data["timeline_date"], "yyyy-MM-dd")
            if date.isValid():
                self.timeline_date.setDate(date)

        self.context_input.setPlainText(data.get("organizational_context", ""))

        # Trigger validation
        self._validate_email()
        self._validate_form()
