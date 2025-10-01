"""
Review & Generate Page - Step 7 of Admin Setup Wizard
Final review of all configurations before generating immutable policy.
"""

from typing import Dict, Any, Tuple
from PySide6 import QtWidgets, QtCore, QtGui
from discovery_assistant.wizard_base import WizardPage
from discovery_assistant.ui.widgets.warning_widget import WarningWidget

class ReviewGeneratePage(WizardPage):
    """Step 7: Review all configurations and generate policy"""

    def __init__(self, parent=None):
        super().__init__("Review & Generate", parent)
        self.wizard_data = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)

        # Header
        header_layout = self._create_header()
        layout.addLayout(header_layout)

        # Immutability warning (prominent)
        warning = WarningWidget(
            "<b>Settings cannot be changed after policy generation.</b> "
            "Please review all configurations carefully before proceeding.",
            icon_path=":/warning_icon.svg"
        )
        layout.addWidget(warning)

        # Main content - scrollable review sections
        content_widget = self._create_content_area()
        layout.addWidget(content_widget, 1)

    def _create_header(self) -> QtWidgets.QVBoxLayout:
        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(10)

        title = QtWidgets.QLabel("Review Configuration")
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
            "Review all configuration settings before generating your immutable policy. "
            "You can click 'Edit' next to any section to return to that step and make changes."
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
        widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        # Create review sections for each wizard step
        self.project_section = self._create_review_section("Project Setup", 2)
        layout.addWidget(self.project_section)

        self.sources_section = self._create_review_section("Data Sources", 3)
        layout.addWidget(self.sources_section)

        self.sections_section = self._create_review_section("Section & Field Configuration", 4)
        layout.addWidget(self.sections_section)

        self.instructions_section = self._create_review_section("Administrative Instructions", 5)
        layout.addWidget(self.instructions_section)

        self.privacy_section = self._create_review_section("Privacy & Data Settings", 6)
        layout.addWidget(self.privacy_section)

        layout.addStretch(1)

        return widget

    def _create_review_section(self, title: str, step_number: int) -> QtWidgets.QGroupBox:
        """Create a collapsible review section for a wizard step"""
        group = QtWidgets.QGroupBox(title)
        layout = QtWidgets.QVBoxLayout(group)
        layout.setContentsMargins(18, 15, 18, 15)
        layout.setSpacing(10)
        self._apply_group_style(group)

        # Header with edit button only (no checkmark)
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.addStretch()

        edit_btn = QtWidgets.QPushButton("Edit")
        edit_btn.setObjectName("editBtn")
        edit_btn.setCursor(QtCore.Qt.PointingHandCursor)
        edit_btn.clicked.connect(lambda: self._navigate_to_step(step_number))
        header_layout.addWidget(edit_btn)

        layout.addLayout(header_layout)

        # Content area (will be populated with actual data)
        content_label = QtWidgets.QLabel("Configuration details will appear here")
        content_label.setObjectName("sectionContent")
        content_label.setWordWrap(True)
        content_label.setStyleSheet("""
            #sectionContent {
                color: #D1D5DB;
                font-size: 13px;
                line-height: 1.6;
                padding: 10px;
                background-color: #2A2A2A;
                border-radius: 6px;
            }
        """)
        layout.addWidget(content_label)

        # Store reference to content label for updates
        group.setProperty("contentLabel", content_label)

        return group

    def _apply_group_style(self, group: QtWidgets.QGroupBox):
        """Apply consistent styling to group boxes"""
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
            QPushButton#editBtn {
                background-color: #606060;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                font-weight: 500;
                font-size: 13px;
            }
            QPushButton#editBtn:hover {
                background-color: #808080;
            }
        """)

    def _get_wizard(self):
        """Helper to traverse parent hierarchy and find the wizard"""
        # Hierarchy: AdminSetupWizard > QScrollArea > ResizableStackedWidget > ReviewGeneratePage
        widget = self
        attempts = 0
        while widget and attempts < 10:  # Safety limit
            widget = widget.parent()
            attempts += 1
            if widget is None:
                print(f"DEBUG: Reached None at level {attempts}")
                return None
            print(f"DEBUG: Level {attempts}: {widget.__class__.__name__}")
            # Check if this is the wizard by looking for both attributes
            if (hasattr(widget, 'wizard_data') and
                hasattr(widget, 'current_step') and
                hasattr(widget, 'pages')):
                print(f"DEBUG: Found wizard at level {attempts}")
                return widget
        print(f"DEBUG: Could not find wizard after {attempts} attempts")
        return None

    def _navigate_to_step(self, step_number: int):
        """Navigate back to a specific wizard step for editing"""
        wizard = self._get_wizard()
        if wizard:
            # Save current page data first
            current_data = self.collect_data()
            wizard.wizard_data[f"step_{wizard.current_step + 1}"] = current_data

            # Navigate to requested step (step_number is 1-indexed, current_step is 0-indexed)
            wizard.current_step = step_number - 1
            wizard._update_page()

    def _update_section_content(self, section: QtWidgets.QGroupBox, content_html: str):
        """Update the content of a review section"""
        content_label = section.property("contentLabel")
        if content_label:
            content_label.setText(content_html)

    def _format_project_summary(self, project_data: Dict[str, Any]) -> str:
        """Format project setup data for display"""
        lines = []

        org_name = project_data.get("organization_name", "Not specified")
        lines.append(f"<b>Organization:</b> {org_name}")

        admin_name = project_data.get("administrator_name", "Not specified")
        lines.append(f"<b>Administrator:</b> {admin_name}")

        admin_email = project_data.get("administrator_email", "Not specified")
        lines.append(f"<b>Contact Email:</b> {admin_email}")

        session_desc = project_data.get("session_description", "")
        if session_desc:
            lines.append(f"<b>Session Description:</b> {session_desc[:100]}...")

        has_timeline = project_data.get("has_timeline", False)
        if has_timeline:
            timeline_date = project_data.get("timeline_date", "Not set")
            lines.append(f"<b>Project Deadline:</b> {timeline_date}")
        else:
            lines.append("<b>Project Deadline:</b> Not set")

        return "<br>".join(lines)

    def _format_sources_summary(self, sources_data: Dict[str, Any]) -> str:
        """Format data sources summary"""
        sources = sources_data.get("data_sources", [])
        count = len(sources)

        if count == 0:
            return "<span style='color: #EF4444;'>⚠️ No data sources configured</span>"

        lines = [f"<b>Total Data Sources:</b> {count}"]
        lines.append("")

        for i, source in enumerate(sources[:5], 1):  # Show first 5
            source_name = source.get("name", "Unknown")
            source_type = source.get("type", "unknown")
            lines.append(f"{i}. {source_name} ({source_type})")

        if count > 5:
            lines.append(f"<i>... and {count - 5} more</i>")

        return "<br>".join(lines)

    def _format_sections_summary(self, consolidated_data: Dict[str, Any]) -> str:
        """Format section and field configuration summary"""
        summary = consolidated_data.get("summary", {})

        enabled_sections = summary.get("enabled_sections", 0)
        total_sections = summary.get("total_sections", 0)
        enabled_fields = summary.get("enabled_field_groups", 0)
        total_fields = summary.get("total_field_groups", 0)

        lines = [
            f"<b>Sections Enabled:</b> {enabled_sections} of {total_sections}",
            f"<b>Field Groups Enabled:</b> {enabled_fields} of {total_fields}"
        ]

        # List enabled sections
        sections = consolidated_data.get("sections", {})
        enabled_list = [name for name, info in sections.items() if info.get("enabled", False)]

        if enabled_list:
            lines.append("")
            lines.append("<b>Enabled Sections:</b>")
            for section_name in enabled_list[:8]:  # Show first 8
                lines.append(f"• {section_name}")
            if len(enabled_list) > 8:
                lines.append(f"<i>... and {len(enabled_list) - 8} more</i>")

        return "<br>".join(lines)

    def _format_instructions_summary(self, instructions_data: Dict[str, Any]) -> str:
        """Format administrative instructions summary"""
        messages = instructions_data.get("messages", [])
        count = len(messages)

        if count == 0:
            return "No administrative instructions configured"

        critical_count = sum(1 for m in messages if m.get("priority") == "critical")

        lines = [
            f"<b>Total Messages:</b> {count}",
            f"<b>Critical Messages:</b> {critical_count}"
        ]

        if messages:
            lines.append("")
            lines.append("<b>Messages:</b>")
            for i, msg in enumerate(messages[:3], 1):
                title = msg.get("title", "Untitled")
                msg_type = msg.get("type", "reminder")
                lines.append(f"{i}. {title} ({msg_type})")

            if count > 3:
                lines.append(f"<i>... and {count - 3} more</i>")

        return "<br>".join(lines)

    def _format_privacy_summary(self, privacy_data: Dict[str, Any]) -> str:
        """Format privacy and AI configuration summary"""
        ai_config = privacy_data.get("ai_configuration", {})
        service = privacy_data.get("service_engagement", {})
        privacy = privacy_data.get("privacy", {})

        lines = []

        # AI Configuration
        lines.append("<b>AI Configuration:</b>")
        initial_credits = ai_config.get("initial_credits", 50)
        additional = ai_config.get("additional_credits_purchased", 0)
        total_credits = initial_credits + additional
        lines.append(f"• Total Credits: ${total_credits}")

        advisor_access = ai_config.get("advisor_access", "all")
        access_map = {"all": "All respondents", "admin": "Admin only", "disabled": "Disabled"}
        lines.append(f"• AI Advisor Access: {access_map.get(advisor_access, advisor_access)}")

        depletion = ai_config.get("depletion_policy", "pause")
        depletion_map = {"pause": "Pause on depletion", "overage": "Allow overage", "disable": "Disable AI"}
        lines.append(f"• Depletion Policy: {depletion_map.get(depletion, depletion)}")

        lines.append("")

        # Service Engagement
        lines.append("<b>Service Engagement:</b>")
        interested = service.get("interested", "no")
        interest_map = {"yes": "Yes - Formal estimate requested", "maybe": "Maybe - Will review first", "no": "No"}
        lines.append(f"• Implementation Interest: {interest_map.get(interested, interested)}")

        if interested != "no":
            contact_email = service.get("contact_email", "Not provided")
            lines.append(f"• Contact: {contact_email}")

        lines.append("")

        # Privacy Options
        lines.append("<b>Privacy Options:</b>")
        anonymize = privacy.get("anonymize_respondents", False)
        lines.append(f"• Anonymize Respondents: {'Yes' if anonymize else 'No'}")

        excluded = privacy.get("excluded_terms", [])
        if excluded:
            lines.append(f"• Excluded Terms: {len(excluded)} items")

        return "<br>".join(lines)

    def showEvent(self, event):
        """Update summaries when page becomes visible"""
        super().showEvent(event)
        self._refresh_summaries()

    def _refresh_summaries(self):
        """Refresh all summary sections with current wizard data"""
        wizard = self._get_wizard()
        if not wizard:
            print("DEBUG: Could not find wizard parent")
            return

        print(f"DEBUG: Found wizard with {len(wizard.wizard_data)} steps of data")

        # Update each section with formatted data
        project_data = wizard.wizard_data.get("step_2", {})
        if project_data:
            print(f"DEBUG: Loading project data: {list(project_data.keys())}")
            content = self._format_project_summary(project_data)
            self._update_section_content(self.project_section, content)

        sources_data = wizard.wizard_data.get("step_3", {})
        if sources_data:
            print(f"DEBUG: Loading sources data: {sources_data.get('total_count', 0)} sources")
            content = self._format_sources_summary(sources_data)
            self._update_section_content(self.sources_section, content)

        consolidated_data = wizard.wizard_data.get("step_4", {})
        if consolidated_data:
            print(f"DEBUG: Loading consolidated data")
            content = self._format_sections_summary(consolidated_data)
            self._update_section_content(self.sections_section, content)

        instructions_data = wizard.wizard_data.get("step_5", {})
        if instructions_data:
            print(f"DEBUG: Loading instructions data")
            content = self._format_instructions_summary(instructions_data)
            self._update_section_content(self.instructions_section, content)

        privacy_data = wizard.wizard_data.get("step_6", {})
        if privacy_data:
            print(f"DEBUG: Loading privacy data")
            content = self._format_privacy_summary(privacy_data)
            self._update_section_content(self.privacy_section, content)

    # WizardPage interface implementation
    def validate_page(self) -> Tuple[bool, str]:
        """Validate that all required configurations are complete"""
        wizard = self._get_wizard()
        if not wizard:
            return False, "Cannot access wizard data"

        # Check for required data sources
        sources_data = wizard.wizard_data.get("step_3", {})
        if not sources_data.get("data_sources"):
            return False, "At least one data source is required before generating policy."

        return True, ""

    def collect_data(self) -> Dict[str, Any]:
        """Collect page data - review page doesn't add new data"""
        return {
            "reviewed": True,
            "review_timestamp": QtCore.QDateTime.currentDateTime().toString(QtCore.Qt.ISODate)
        }

    def load_data(self, data: Dict[str, Any]) -> None:
        """Load existing data - triggers summary refresh"""
        self._refresh_summaries()
