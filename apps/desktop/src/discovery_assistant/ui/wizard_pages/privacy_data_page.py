"""
Privacy & Data Settings Page - Step 6 of Admin Setup Wizard
Configures AI credits, privacy options, and service engagement preferences.
"""

from typing import Dict, Any, Tuple
from PySide6 import QtWidgets, QtCore, QtGui
from discovery_assistant.wizard_base import WizardPage
from discovery_assistant.ui.widgets.warning_widget import WarningWidget
from discovery_assistant.ui.widgets.styled_checkbox import StyledCheckBox

class PrivacyDataPage(WizardPage):
    """Step 6: Privacy, AI credits, and service configuration"""

    CREDIT_PACKAGES = [
        (0, "No additional credits"),
        (25, "$25 - ~12-50 additional interactions"),
        (50, "$50 - ~25-100 additional interactions"),
        (100, "$100 - ~50-200 additional interactions"),
        (250, "$250 - ~125-500 additional interactions"),
    ]

    ADVISOR_ACCESS_OPTIONS = [
        ("all", "All respondents (during form completion)"),
        ("admin", "Admin only (for review and analysis)"),
        ("disabled", "Disable interactive AI (save credits for final report only)"),
    ]

    DEPLETION_POLICIES = [
        ("pause", "Pause AI features until credits are added (Recommended)"),
        ("overage", "Allow credit overage with post-session billing"),
        ("disable", "Disable AI features for remainder of session"),
    ]

    SERVICE_INTEREST = [
        ("yes", "Yes - Contact me with formal implementation estimate"),
        ("maybe", "Maybe - I'll review the report and decide"),
        ("no", "No - Internal planning only"),
    ]

    COMPANY_SIZES = [
        "1-10 employees",
        "11-50 employees",
        "51-200 employees",
        "200+ employees",
    ]

    def __init__(self, parent=None):
        super().__init__("Privacy & Data Settings", parent)
        self._setup_ui()
        self._connect_signals()
        self._validate_form()

    def _setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)

        # Header
        header_layout = self._create_header()
        layout.addLayout(header_layout)

        # Main content
        content_widget = self._create_content_area()
        layout.addWidget(content_widget, 1)
        layout.addStretch(1)

    def _create_header(self) -> QtWidgets.QVBoxLayout:
        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(10)

        title = QtWidgets.QLabel("Privacy & Data Settings")
        title.setObjectName("pageTitle")
        title.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        title.setStyleSheet("""
            #pageTitle {
                font-size: 24px;
                font-weight: 600;
                color: #F9FAFB;
                margin-bottom: 8px;
            }
        """)

        description = QtWidgets.QLabel(
            "Configure AI analysis credits, advisor availability, and privacy options. "
            "These settings control how AI assists during discovery and what information "
            "is included in your final report."
        )
        description.setWordWrap(True)
        description.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
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
        widget = QtWidgets.QWidget()
        widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        # Section 1: AI Configuration
        ai_config_group = self._create_ai_config_section()
        layout.addWidget(ai_config_group)

        # Section 2: AI Advisor Access
        advisor_group = self._create_advisor_access_section()
        layout.addWidget(advisor_group)

        # Section 3: Credit Depletion
        depletion_group = self._create_depletion_policy_section()
        layout.addWidget(depletion_group)

        # Section 4: Service Engagement
        service_group = self._create_service_engagement_section()
        layout.addWidget(service_group)

        # Section 5: Privacy Options
        privacy_group = self._create_privacy_options_section()
        layout.addWidget(privacy_group)

        return widget

    def _create_ai_config_section(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("AI Analysis && Credit System")
        layout = QtWidgets.QVBoxLayout(group)
        layout.setContentsMargins(18, 15, 18, 15)
        layout.setSpacing(12)
        self._apply_group_style(group)

        # Description
        desc = QtWidgets.QLabel(
            "Your organization will have access to AI assistance throughout the discovery "
            "process and for final report generation.\n\n"
            "AI Services Included:\n"
            "• Real-time AI Advisor guidance during data entry\n"
            "• Process and pain point validation as respondents work\n"
            "• Data source connection recommendations\n"
            "• Final report generation with automation opportunity analysis"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #D1D5DB; font-size: 13px; line-height: 1.4;")
        layout.addWidget(desc)

        layout.addSpacing(8)

        # Credit info
        credit_info = QtWidgets.QLabel(
            "Initial credit allocation: $50 (estimated for 5-10 respondents)\n\n"
            "Usage estimates:\n"
            "• AI Advisor interaction: ~$0.50-2.00 per query\n"
            "• Real-time validation: ~$0.10-0.50 per analysis\n"
            "• Final report generation: ~$5-15 (depending on data volume)"
        )
        credit_info.setWordWrap(True)
        credit_info.setStyleSheet("color: #9CA3AF; font-size: 12px; font-family: 'Courier New';")
        layout.addWidget(credit_info)

        layout.addSpacing(8)

        # Additional credits dropdown
        credits_layout = QtWidgets.QHBoxLayout()
        credits_label = QtWidgets.QLabel("Purchase additional credits now:")
        credits_label.setStyleSheet("color: #F9FAFB; font-weight: 500;")

        self.credits_combo = QtWidgets.QComboBox()
        self.credits_combo.setFixedHeight(35)
        for amount, desc in self.CREDIT_PACKAGES:
            self.credits_combo.addItem(desc, amount)
        self.credits_combo.setMinimumWidth(300)

        credits_layout.addWidget(credits_label)
        credits_layout.addWidget(self.credits_combo)
        credits_layout.addStretch()
        layout.addLayout(credits_layout)

        # Info note
        info_note = QtWidgets.QLabel(
            "(Credits can also be added during discovery if needed)"
        )
        info_note.setStyleSheet("color: #6B7280; font-size: 11px; font-style: italic; margin-left: 10px;")
        layout.addWidget(info_note)

        layout.addSpacing(8)

        # Expandable info about security
        security_info = QtWidgets.QLabel(
            "All AI processing uses AWS Bedrock AgentCore with complete session isolation. "
            "Your data is processed in secure, isolated environments and never retained after analysis."
        )
        security_info.setWordWrap(True)
        security_info.setStyleSheet("""
            background-color: #2A2A2A;
            border: 1px solid #404040;
            border-radius: 6px;
            padding: 10px;
            color: #9CA3AF;
            font-size: 12px;
        """)
        layout.addWidget(security_info)

        return group

    def _create_advisor_access_section(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("AI Advisor Availability")
        layout = QtWidgets.QVBoxLayout(group)
        layout.setContentsMargins(18, 15, 18, 15)
        layout.setSpacing(10)
        self._apply_group_style(group)

        desc = QtWidgets.QLabel("Who can access AI Advisor during discovery?")
        desc.setStyleSheet("color: #D1D5DB; font-weight: 500; margin-bottom: 8px;")
        layout.addWidget(desc)

        # Radio buttons
        self.advisor_buttons = {}
        for value, display in self.ADVISOR_ACCESS_OPTIONS:
            radio = QtWidgets.QRadioButton(display)
            radio.setStyleSheet("color: #F9FAFB; padding: 4px;")
            self.advisor_buttons[value] = radio
            layout.addWidget(radio)

        # Default to "all"
        self.advisor_buttons["all"].setChecked(True)

        # Note
        note = QtWidgets.QLabel(
            "Note: Enabling AI Advisor for respondents improves data quality through "
            "real-time feedback but increases credit usage."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #9CA3AF; font-size: 12px; font-style: italic; margin-top: 8px;")
        layout.addWidget(note)

        return group

    def _create_depletion_policy_section(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("Credit Depletion Policy")
        layout = QtWidgets.QVBoxLayout(group)
        layout.setContentsMargins(18, 15, 18, 15)
        layout.setSpacing(10)
        self._apply_group_style(group)

        desc = QtWidgets.QLabel("What happens when credits run out during discovery?")
        desc.setStyleSheet("color: #D1D5DB; font-weight: 500; margin-bottom: 8px;")
        layout.addWidget(desc)

        # Radio buttons
        self.depletion_buttons = {}
        for value, display in self.DEPLETION_POLICIES:
            radio = QtWidgets.QRadioButton(display)
            radio.setStyleSheet("color: #F9FAFB; padding: 4px;")
            self.depletion_buttons[value] = radio
            layout.addWidget(radio)

        # Default to "pause"
        self.depletion_buttons["pause"].setChecked(True)

        # Warning
        warning = WarningWidget(
            "If AI is disabled mid-session, final report generation may be incomplete or require manual review (additional fees apply).",
            icon_path=":/warning_icon.svg"
        )
        layout.addWidget(warning)

        return group

    def _create_service_engagement_section(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("DataWoven RAG && Agentic System Implementation")
        layout = QtWidgets.QVBoxLayout(group)
        layout.setContentsMargins(18, 15, 18, 15)
        layout.setSpacing(12)
        self._apply_group_style(group)

        desc = QtWidgets.QLabel(
            "After reviewing your AI-generated report, would you like to discuss "
            "custom implementation services?"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #D1D5DB; margin-bottom: 8px;")
        layout.addWidget(desc)

        # Radio buttons
        self.service_buttons = {}
        for value, display in self.SERVICE_INTEREST:
            radio = QtWidgets.QRadioButton(display)
            radio.setStyleSheet("color: #F9FAFB; padding: 4px;")
            self.service_buttons[value] = radio
            layout.addWidget(radio)

        # Default to "maybe"
        self.service_buttons["maybe"].setChecked(True)

        layout.addSpacing(8)

        # Contact form (conditional)
        self.contact_widget = QtWidgets.QWidget()
        contact_layout = QtWidgets.QVBoxLayout(self.contact_widget)
        contact_layout.setContentsMargins(20, 10, 0, 0)
        contact_layout.setSpacing(10)

        form = QtWidgets.QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.contact_email = QtWidgets.QLineEdit()
        self.contact_email.setPlaceholderText("contact@company.com")
        self.contact_email.setFixedHeight(35)
        form.addRow("Primary contact email:", self.contact_email)

        self.contact_phone = QtWidgets.QLineEdit()
        self.contact_phone.setPlaceholderText("Optional")
        self.contact_phone.setFixedHeight(35)
        form.addRow("Phone (optional):", self.contact_phone)

        self.company_size_combo = QtWidgets.QComboBox()
        self.company_size_combo.setFixedHeight(35)
        self.company_size_combo.addItems(self.COMPANY_SIZES)
        form.addRow("Company size:", self.company_size_combo)

        contact_layout.addLayout(form)

        # Requirements note
        req_note = QtWidgets.QLabel(
            "For accurate estimates, DataWoven will need:\n"
            "• Your generated discovery report\n"
            "• Access to review data source configurations\n"
            "• Brief technical consultation call"
        )
        req_note.setWordWrap(True)
        req_note.setStyleSheet("color: #9CA3AF; font-size: 12px; margin-top: 8px;")
        contact_layout.addWidget(req_note)

        layout.addWidget(self.contact_widget)

        # Initially show contact form (since "maybe" is default)
        self._update_contact_visibility()

        return group

    def _create_privacy_options_section(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("Export Privacy Options")
        layout = QtWidgets.QVBoxLayout(group)
        layout.setContentsMargins(18, 15, 18, 15)
        layout.setSpacing(12)
        self._apply_group_style(group)

        self.anonymize_check = StyledCheckBox(
            "Anonymize respondent identities in final report",
            bg_color="#666666",  # unchecked background
            bg_color_checked="#000000",  # checked background
            indicator_size=16  # or whatever size you want
        )
        layout.addWidget(self.anonymize_check)

        anon_desc = QtWidgets.QLabel(
            "(Replaces names, emails, departments with role identifiers)"
        )
        anon_desc.setStyleSheet("color: #9CA3AF; font-size: 12px; margin-left: 25px;")
        layout.addWidget(anon_desc)

        layout.addSpacing(8)

        # Exclusion field
        excl_label = QtWidgets.QLabel("Exclude sensitive information from AI analysis:")
        excl_label.setStyleSheet("color: #F9FAFB; font-weight: 500;")
        layout.addWidget(excl_label)

        self.exclusion_text = QtWidgets.QTextEdit()
        self.exclusion_text.setPlaceholderText(
            "Examples: Client names, Project codenames, Revenue figures\n\n"
            "Enter one item per line or comma-separated"
        )
        self.exclusion_text.setFixedHeight(100)
        layout.addWidget(self.exclusion_text)

        # Exclusions warning
        warning = WarningWidget(
            "Excluded information will not be analyzed for automation opportunities and may reduce recommendation accuracy.",
            icon_path=":/warning_icon.svg"
        )
        layout.addWidget(warning)

        return group

    def _apply_group_style(self, group: QtWidgets.QGroupBox):
        """Apply consistent styling matching other wizard pages"""
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
        """Connect UI signals"""
        # Service interest radio buttons
        for radio in self.service_buttons.values():
            radio.toggled.connect(self._update_contact_visibility)
            radio.toggled.connect(self._validate_form)

        # Contact email for validation
        self.contact_email.textChanged.connect(self._validate_form)

    def _update_contact_visibility(self):
        """Show/hide contact form based on service interest"""
        show_contact = (
            self.service_buttons["yes"].isChecked() or
            self.service_buttons["maybe"].isChecked()
        )
        self.contact_widget.setVisible(show_contact)

    def _validate_form(self):
        """Validate form and emit canProceed signal"""
        # Check if service interest requires email
        needs_email = (
            self.service_buttons["yes"].isChecked() or
            self.service_buttons["maybe"].isChecked()
        )

        if needs_email:
            has_email = bool(self.contact_email.text().strip())
            self.canProceed.emit(has_email)
        else:
            # No email required if they selected "No"
            self.canProceed.emit(True)

    def showEvent(self, event):
        """Apply input styles when page becomes visible"""
        super().showEvent(event)
        self._apply_input_styles()

    def _apply_input_styles(self):
        """Apply consistent input styling"""
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
            QComboBox {
                padding: 8px 12px;
            }
            QRadioButton {
                color: #F9FAFB;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
                border-radius: 10px;
                border: 2px solid #606060;
                background-color: #404040;
            }
            QRadioButton::indicator:checked {
                border: 2px solid #0BE5F5;  /* Blue border when selected */
                background-color: #0BE5F5;  /* Blue fill when selected */
            }
            QRadioButton::indicator:unchecked {
                border: 2px solid #606060;  /* Gray border when not selected */
                background-color: #404040;  /* Dark gray fill when not selected */
            }
            QRadioButton::indicator:hover {
                border-color: #808080;
            }
        """
        self.setStyleSheet(self.styleSheet() + input_style)

    # WizardPage interface implementation
    def validate_page(self) -> Tuple[bool, str]:
        """Validate the page data"""
        # Check if email is required and provided
        needs_email = (
            self.service_buttons["yes"].isChecked() or
            self.service_buttons["maybe"].isChecked()
        )

        if needs_email and not self.contact_email.text().strip():
            return False, "Contact email is required when requesting implementation services."

        # Basic email validation
        if needs_email:
            email = self.contact_email.text().strip()
            if '@' not in email or '.' not in email:
                return False, "Please enter a valid email address."

        return True, ""

    def collect_data(self) -> Dict[str, Any]:
        """Collect page data for wizard"""
        # Get selected advisor access
        advisor_access = "all"
        for value, radio in self.advisor_buttons.items():
            if radio.isChecked():
                advisor_access = value
                break

        # Get selected depletion policy
        depletion_policy = "pause"
        for value, radio in self.depletion_buttons.items():
            if radio.isChecked():
                depletion_policy = value
                break

        # Get selected service interest
        service_interest = "no"
        for value, radio in self.service_buttons.items():
            if radio.isChecked():
                service_interest = value
                break

        # Parse exclusion text
        exclusion_text = self.exclusion_text.toPlainText().strip()
        exclusions = []
        if exclusion_text:
            # Split by newline or comma
            for line in exclusion_text.split('\n'):
                items = [item.strip() for item in line.split(',') if item.strip()]
                exclusions.extend(items)

        return {
            "ai_configuration": {
                "enabled": True,  # Always enabled in this design
                "initial_credits": 50.0,
                "additional_credits_purchased": self.credits_combo.currentData(),
                "advisor_access": advisor_access,
                "depletion_policy": depletion_policy,
            },
            "service_engagement": {
                "interested": service_interest,
                "contact_email": self.contact_email.text().strip() if service_interest != "no" else "",
                "contact_phone": self.contact_phone.text().strip() if service_interest != "no" else "",
                "company_size": self.company_size_combo.currentText() if service_interest != "no" else "",
            },
            "privacy": {
                "anonymize_respondents": self.anonymize_check.isChecked(),
                "excluded_terms": exclusions,
            }
        }

    def load_data(self, data: Dict[str, Any]) -> None:
        """Load existing data into the page"""
        ai_config = data.get("ai_configuration", {})
        service = data.get("service_engagement", {})
        privacy = data.get("privacy", {})

        # Load AI configuration
        additional_credits = ai_config.get("additional_credits_purchased", 0)
        for i in range(self.credits_combo.count()):
            if self.credits_combo.itemData(i) == additional_credits:
                self.credits_combo.setCurrentIndex(i)
                break

        advisor_access = ai_config.get("advisor_access", "all")
        if advisor_access in self.advisor_buttons:
            self.advisor_buttons[advisor_access].setChecked(True)

        depletion = ai_config.get("depletion_policy", "pause")
        if depletion in self.depletion_buttons:
            self.depletion_buttons[depletion].setChecked(True)

        # Load service engagement
        interest = service.get("interested", "maybe")
        if interest in self.service_buttons:
            self.service_buttons[interest].setChecked(True)

        self.contact_email.setText(service.get("contact_email", ""))
        self.contact_phone.setText(service.get("contact_phone", ""))

        company_size = service.get("company_size", "")
        if company_size:
            index = self.company_size_combo.findText(company_size)
            if index >= 0:
                self.company_size_combo.setCurrentIndex(index)

        # Load privacy options
        self.anonymize_check.setChecked(privacy.get("anonymize_respondents", False))

        exclusions = privacy.get("excluded_terms", [])
        if exclusions:
            self.exclusion_text.setPlainText("\n".join(exclusions))

        self._update_contact_visibility()
        self._validate_form()
