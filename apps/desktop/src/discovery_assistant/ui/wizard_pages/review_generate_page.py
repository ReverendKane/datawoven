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

        self.sections_section = self._create_review_section("Section && Field Configuration", 4)
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
        layout.setContentsMargins(18, 7, 18, 18)
        layout.setSpacing(0)
        self._apply_group_style(group)

        # Container widget with gray background that holds both content and button
        content_container = QtWidgets.QWidget()
        content_container.setObjectName("contentContainer")
        content_container.setStyleSheet("""
            #contentContainer {
                background-color: #2A2A2A;
                border-radius: 6px;
            }
        """)

        # Horizontal layout inside the gray container
        container_layout = QtWidgets.QHBoxLayout(content_container)
        container_layout.setContentsMargins(20, 20, 20, 20)
        container_layout.setSpacing(15)

        # Content label - expands to fill available space
        content_label = QtWidgets.QLabel("Configuration details will appear here")
        content_label.setObjectName("sectionContent")
        content_label.setWordWrap(True)
        content_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        content_label.setStyleSheet("""
            #sectionContent {
                color: #D1D5DB;
                font-size: 13px;
                line-height: 1.6;
                background: transparent;
                border: none;
            }
        """)
        container_layout.addWidget(content_label)

        # Edit button inside the gray container
        edit_btn = QtWidgets.QPushButton("Edit")
        edit_btn.setObjectName("editBtn")
        edit_btn.setFixedSize(60, 35)
        edit_btn.setCursor(QtCore.Qt.PointingHandCursor)
        edit_btn.clicked.connect(lambda: self._navigate_to_step(step_number))

        container_layout.addWidget(edit_btn, 0, QtCore.Qt.AlignTop)

        # Add the container to the main layout
        layout.addWidget(content_container)

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

        project_desc = project_data.get("project_description", "")
        if project_desc:
            lines.append(f"<b>Project Description:</b> {project_desc[:100]}...")

        org_context = project_data.get("organizational_context", "")
        if org_context:
            lines.append(f"<b>Organizational Context:</b> {org_context[:100]}...")

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

        for i, source in enumerate(sources, 1):
            source_name = source.get("name", "Unknown")
            source_category = source.get("category", "other")
            source_description = source.get("description", "")

            # Get display name for category
            from discovery_assistant.ui.modals.data_source_modal import DataSource
            category_display = next((disp for key, disp in DataSource.CATEGORIES if key == source_category),
                                    source_category)

            lines.append(f"<b>{i}. {source_name}</b> ({category_display})")
            if source_description:
                lines.append(f"   {source_description}")
            lines.append("")  # Blank line between entries

        return "<br>".join(lines)

    def _format_sections_summary(self, consolidated_data: Dict[str, Any]) -> str:
        """Format section and field configuration summary"""
        summary = consolidated_data.get("summary", {})
        sections = consolidated_data.get("sections", {})
        field_groups = consolidated_data.get("field_groups", {})

        enabled_sections = summary.get("enabled_sections", 0)
        total_sections = summary.get("total_sections", 0)
        enabled_fields = summary.get("enabled_field_groups", 0)
        total_fields = summary.get("total_field_groups", 0)

        # Build HTML with proper structure
        html_parts = []
        html_parts.append(f"<b>Sections Enabled:</b> {enabled_sections} of {total_sections}<br>")
        html_parts.append(f"<b>Field Groups Enabled:</b> {enabled_fields} of {total_fields}<br><br><br><br>")

        # # Add horizontal separator line with constrained width
        # html_parts.append(
        #     "<div style='width: 235px;'><hr style='border: none; border-top: 1px solid #FFFFFF; margin: 3px 0 5px 0;'></div>")
        #
        # Map section names to their field prefixes
        section_prefix_map = {
            "Respondent Info": "respondent",
            "Org Map": "org_map",
            "Processes": "processes",
            "Pain Points": "pain_points",
            "Data Sources": "data_sources",
            "Compliance": "compliance",
            "Feature Ideas": "feature_ideas",
            "Reference Library": "reference_library",
            "Time & Resource Management": "time_resource"
        }

        # Group disabled fields by section prefix
        disabled_by_section = {}
        for field_key, is_enabled in field_groups.items():
            if not is_enabled and "_" in field_key:
                section_prefix = field_key.split("_", 1)[0]
                # Handle multi-word prefixes like "pain_points"
                if section_prefix in ["pain", "org", "data", "feature", "reference", "time"]:
                    parts = field_key.split("_")
                    if len(parts) >= 3:
                        section_prefix = f"{parts[0]}_{parts[1]}"
                        field_name = "_".join(parts[2:]).replace("_", " ").title()
                    else:
                        field_name = field_key.split("_", 1)[1].replace("_", " ").title()
                else:
                    field_name = field_key.split("_", 1)[1].replace("_", " ").title()

                if section_prefix not in disabled_by_section:
                    disabled_by_section[section_prefix] = []
                disabled_by_section[section_prefix].append(field_name)

        # Display each section with its status and disabled fields together
        for section_name, section_info in sections.items():
            is_enabled = section_info.get("enabled", False)
            is_required = section_info.get("required", False)

            # Section header with status in parentheses
            if is_required:
                status_text = "<span style='color: #0BE5F5;'>REQUIRED</span>"
            elif is_enabled:
                status_text = "Enabled"
            else:
                status_text = "<span style='color: #6B7280;'>Disabled</span>"

            html_parts.append(f"<b>{section_name}</b> ({status_text})<br>")

            # If section is enabled, show any disabled fields with indent and tight spacing
            if is_enabled:
                section_prefix = section_prefix_map.get(section_name, section_name.lower().replace(" ", "_"))
                if section_prefix in disabled_by_section:
                    for field_name in disabled_by_section[section_prefix]:
                        html_parts.append(
                            f"<span style='color: #EF4444;'>&nbsp;&nbsp;&nbsp;&nbsp;- {field_name} [disabled]</span><br>")

            html_parts.append("<br>")  # Extra spacing between sections

        return "".join(html_parts)

    def _format_instructions_summary(self, instructions_data: Dict[str, Any]) -> str:
        """Format administrative instructions summary"""
        messages = instructions_data.get("messages", [])
        count = len(messages)

        if count == 0:
            return "No administrative instructions configured"

        critical_count = sum(1 for m in messages if m.get("priority") == "critical")
        important_count = sum(1 for m in messages if m.get("priority") == "important")
        info_count = sum(1 for m in messages if m.get("priority") == "informational")

        lines = [
            f"<b>Total Messages:</b> {count}",
            f"<b>Must Acknowledge (Critical):</b> {critical_count}",
            f"<b>Should Read (Important):</b> {important_count}",
            f"<b>Reference Only (Informational):</b> {info_count}",
            ""
        ]

        if messages:
            lines.append("<b>Message List:</b>")
            for i, msg in enumerate(messages, 1):
                title = msg.get("title", "Untitled")
                msg_type = msg.get("type", "reminder")
                priority = msg.get("priority", "informational")

                # Format type display
                type_map = {
                    "security_warning": "Security Warning",
                    "requirement": "Process Requirement",
                    "guideline": "Data Guideline",
                    "steps": "Step-by-Step Instructions",
                    "reminder": "General Reminder"
                }
                type_display = type_map.get(msg_type, msg_type)

                # Priority badge
                priority_map = {
                    "critical": "<span style='color: #EF4444;'>[CRITICAL]</span>",
                    "important": "<span style='color: #F59E0B;'>[IMPORTANT]</span>",
                    "informational": "<span style='color: #6B7280;'>[INFO]</span>"
                }
                priority_badge = priority_map.get(priority, "")

                lines.append(f"{i}. <b>{title}</b> {priority_badge}")
                lines.append(f"   <i>{type_display}</i><br>")

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
