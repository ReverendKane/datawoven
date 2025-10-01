"""
Consolidated Field & Section Configuration Page - Step 4 of Admin Setup Wizard
Combines section selection and field customization in a single, intuitive interface.
"""

from typing import Dict, Any, Tuple, List
from PySide6 import QtWidgets, QtCore, QtGui
from discovery_assistant.wizard_base import WizardPage


class FieldToggleSwitch(QtWidgets.QWidget):
    """Custom toggle switch for section enable/disable"""

    toggled = QtCore.Signal(bool)

    def __init__(self, enabled=True, parent=None):
        super().__init__(parent)
        self._enabled = enabled
        self.__internal_position = 26 if enabled else 2
        self.setFixedSize(50, 24)
        self.setCursor(QtCore.Qt.PointingHandCursor)

        self._animation = QtCore.QPropertyAnimation(self, b"position")
        self._animation.setDuration(150)
        self._animation.setEasingCurve(QtCore.QEasingCurve.InOutCubic)

    def _get_position(self):
        return self.__internal_position

    def _set_position(self, pos):
        self.__internal_position = pos
        self.update()

    position = QtCore.Property(int, _get_position, _set_position)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        rect = self.rect()

        track_rect = rect.adjusted(2, 2, -2, -2)
        track_color = QtGui.QColor("#0BE5F5" if self._enabled else "#252525")
        painter.setBrush(QtGui.QBrush(track_color))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(track_rect, 10, 10)

        thumb_rect = QtCore.QRect(self.__internal_position, 2, 20, 20)
        thumb_color = QtGui.QColor("#FFFFFF")
        painter.setBrush(QtGui.QBrush(thumb_color))
        painter.drawEllipse(thumb_rect)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.toggle()

    def toggle(self):
        self._enabled = not self._enabled
        start_pos = 2 if self._enabled else 26
        end_pos = 26 if self._enabled else 2
        self._animation.setStartValue(start_pos)
        self._animation.setEndValue(end_pos)
        self._animation.start()
        self.toggled.emit(self._enabled)

    def setChecked(self, checked):
        if self._enabled != checked:
            self._enabled = checked
            self.__internal_position = 26 if checked else 2
            self.update()

    def isChecked(self):
        return self._enabled


class FieldGroupWidget(QtWidgets.QWidget):
    """Widget representing a single field that can be toggled"""

    toggled = QtCore.Signal(str, bool)

    def __init__(self, field_key, field_name, enabled=True, required=False, parent=None):
        super().__init__(parent)
        self.field_key = field_key
        self.field_name = field_name
        self.enabled = enabled
        self.required = required
        self.hovered = False
        cursor = QtCore.Qt.ForbiddenCursor if required else QtCore.Qt.PointingHandCursor
        self.setCursor(cursor)
        self.setMouseTracking(True)

    def enterEvent(self, event):
        if not self.required:
            self.hovered = True
            self.update()

    def leaveEvent(self, event):
        self.hovered = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and not self.required:
            self.enabled = not self.enabled
            self.toggled.emit(self.field_key, self.enabled)
            self._update_field_state()

    def _update_field_state(self):
        if hasattr(self, 'field_label'):
            if self.enabled:
                self.field_label.setStyleSheet("""
                    font-size: 13px; color: #334155; background: transparent;
                    border: none; margin: 0px; padding: 0px;
                """)
            else:
                self.field_label.setStyleSheet("""
                    font-size: 13px; color: #9CA3AF; background: transparent;
                    border: none; margin: 0px; padding: 0px;
                """)

        if hasattr(self, 'field_input'):
            if self.enabled:
                self.field_input.setStyleSheet("""
                    background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px;
                    padding: 8px 10px; color: #9CA3AF; margin: 0px;
                """)
                if hasattr(self, 'placeholder_text'):
                    self.field_input.setText(self.placeholder_text)
            else:
                self.field_input.setStyleSheet("""
                    background: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 8px;
                    padding: 8px 10px; color: #9CA3AF; margin: 0px;
                """)
                self.field_input.setText("Not applicable for this project")

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        if self.hovered and not self.required:
            painter.setPen(QtGui.QPen(QtGui.QColor("#EF4444"), 2))
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 4, 4)


class ConsolidatedFieldSectionPage(WizardPage):
    def __init__(self, parent=None):
        super().__init__("Field & Section Configuration", parent)

        self.sections = {
            "core_sections": {
                "Respondent Info": {
                    "description": "Essential information about who the respondent is, their role, and primary responsibilities. This data provides crucial context for all automation recommendations and ensures personalized insights.",
                    "enabled": True,
                    "required": True,
                    "fields": [
                        {"group": "identity", "names": ["Full Name", "Work Email"], "required": True},
                        {"group": "role_context", "names": ["Department", "Role / Title"], "required": False},
                        {"group": "responsibilities", "names": ["Primary Responsibilities"], "required": False}
                    ]
                },
                "Org Map": {
                    "description": "Organizational context and reporting relationships that help identify collaboration patterns and automation opportunities across team boundaries.",
                    "enabled": True,
                    "required": True,
                    "fields": [
                        {"group": "hierarchy", "names": ["Reports To"], "required": False},
                        {"group": "collaboration", "names": ["Peer Teams", "Downstream Consumers", "Org Notes"], "required": False}
                    ]
                },
                "Processes": {
                    "description": "Business processes and workflows that form the foundation for automation discovery. Critical for identifying repetitive tasks and efficiency opportunities.",
                    "enabled": True,
                    "required": True,
                    "fields": [
                        {"group": "process_basics", "names": ["Process Name", "Process Description"], "required": False},
                        {"group": "process_metrics", "names": ["Frequency", "Time Investment"], "required": False},
                        {"group": "process_documentation", "names": ["Screenshots/Attachments"], "required": False}
                    ]
                },
                "Pain Points": {
                    "description": "Problems and inefficiencies that require automation solutions. This section directly drives ROI calculations and prioritization recommendations.",
                    "enabled": True,
                    "required": True,
                    "fields": [
                        {"group": "pain_basics", "names": ["Pain Point Title", "Description"], "required": False},
                        {"group": "pain_impact", "names": ["Impact Level", "Frequency"], "required": False},
                        {"group": "pain_context", "names": ["Related Process"], "required": False}
                    ]
                },
            },
            "optional_sections": {
                "Data Sources": {
                    "description": "Available data sources and systems that can be leveraged for automation. Essential for technical feasibility assessment and integration planning.",
                    "enabled": False,  # Default to disabled
                    "required": False,
                    "fields": [
                        {"group": "source_basics", "names": ["Source Name", "Connection Type"], "required": True},
                        {"group": "source_details", "names": ["Description"], "required": True},
                        {"group": "source_documentation", "names": ["Screenshots/Attachments"], "required": False}
                    ]
                },
                "Compliance": {
                    "description": "Regulatory requirements and compliance obligations that must be considered in automation design. Important for regulated industries and data-sensitive environments.",
                    "enabled": False,
                    "required": False,
                    "fields": [
                        {"group": "compliance_framework", "names": ["Regulatory Framework"], "required": False},
                        {"group": "compliance_requirements", "names": ["Compliance Requirements", "Audit Frequency"], "required": False},
                        {"group": "compliance_documentation", "names": ["Documentation Requirements"], "required": False}
                    ]
                },
                "Feature Ideas": {
                    "description": "Innovation opportunities and enhancement suggestions that extend beyond basic automation. Captures creative solutions and strategic improvement ideas.",
                    "enabled": False,
                    "required": False,
                    "fields": [
                        {"group": "feature_basics", "names": ["Feature Title", "Feature Description"], "required": False},
                        {"group": "feature_value", "names": ["Business Value", "Implementation Priority"], "required": False}
                    ]
                },
                "Reference Library": {
                    "description": "Document repository and knowledge management section for uploading relevant files, procedures, and reference materials that inform automation decisions.",
                    "enabled": False,
                    "required": False,
                    "fields": [
                        {"group": "document_basics", "names": ["Document Title", "Document Type"], "required": False},
                        {"group": "document_relevance", "names": ["Relevance to Automation"], "required": False},
                        {"group": "document_file", "names": ["File Attachment"], "required": False}
                    ]
                },
                "Time & Resource Management": {
                    "description": "Time allocation tracking and resource constraint analysis. Provides quantitative data for ROI calculations and helps prioritize automation efforts by impact.",
                    "enabled": False,
                    "required": False,
                    "fields": [
                        {"group": "time_tracking", "names": ["Task Category", "Time Allocation"], "required": False},
                        {"group": "resource_analysis", "names": ["Resource Constraints", "Optimization Opportunities"], "required": False}
                    ]
                }
            }
        }

        self.section_widgets = {}
        self.field_group_states = {}
        self.section_switches = {}

        self._setup_ui()
        self._connect_signals()
        self._validate_form()

    def _setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)

        header_layout = self._create_header()
        layout.addLayout(header_layout)

        self.content_layout = QtWidgets.QVBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(15)

        self._create_all_sections()
        self.content_layout.addStretch()
        layout.addLayout(self.content_layout, 1)

    def _create_header(self) -> QtWidgets.QVBoxLayout:
        layout = QtWidgets.QVBoxLayout()

        title = QtWidgets.QLabel("Field & Section Configuration")
        title.setObjectName("pageTitle")
        title.setStyleSheet("""
            #pageTitle {
                font-size: 24px;
                font-weight: 600;
                color: #F9FAFB;
                margin-bottom: 8px;
            }
        """)

        description = QtWidgets.QLabel(
            "Configure which sections respondents will complete and customize individual fields within each section. "
            "Core sections are always enabled as they provide essential automation discovery data. Optional sections can be "
            "enabled based on your organization's specific needs.\n\n"
            "Use the section toggles to enable/disable entire sections. When sections are enabled, hover over individual fields "
            "to see a red outline, then click to disable/enable that specific field. Required fields (marked with *) cannot be disabled."
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

    def _create_all_sections(self):
        for section_name, section_data in self.sections["core_sections"].items():
            section_widget = self._create_section_widget(section_name, section_data)
            self.content_layout.addWidget(section_widget)
            self.section_widgets[section_name] = section_widget

        for section_name, section_data in self.sections["optional_sections"].items():
            section_widget = self._create_section_widget(section_name, section_data)
            self.content_layout.addWidget(section_widget)
            self.section_widgets[section_name] = section_widget

    def _create_section_widget(self, section_name, section_data) -> QtWidgets.QWidget:
        container = QtWidgets.QWidget()
        container.setObjectName(f"{section_name.replace(' ', '')}Container")
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 10)
        layout.setSpacing(0)

        title_bar = self._create_section_title_bar(section_name, section_data)
        layout.addWidget(title_bar)

        content_widget = self._create_section_content(section_name, section_data)
        layout.addWidget(content_widget)

        content_widget.setVisible(section_data["enabled"] or section_data["required"])
        return container

    def _create_section_title_bar(self, section_name, section_data) -> QtWidgets.QWidget:
        title_bar = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(title_bar)
        layout.setContentsMargins(18, 15, 18, 15)
        layout.setSpacing(15)

        name_label = QtWidgets.QLabel(section_name)
        name_label.setStyleSheet("""
            font-size: 18px;
            font-weight: 600;
            color: #F9FAFB;
            background: transparent;
            border: none;
        """)
        layout.addWidget(name_label, 1)

        if not section_data["required"]:
            toggle = FieldToggleSwitch(enabled=section_data["enabled"])
            toggle.toggled.connect(lambda enabled, name=section_name: self._on_section_toggled(name, enabled))
            layout.addWidget(toggle)
            self.section_switches[section_name] = toggle
        else:
            required_label = QtWidgets.QLabel("REQUIRED")
            required_label.setStyleSheet("""
                color: #0BE5F5;
                font-size: 12px;
                font-weight: bold;
                background-color: rgba(11, 229, 245, 0.1);
                padding: 4px 8px;
                border-radius: 4px;
                border: none;
            """)
            layout.addWidget(required_label)

        if section_data["required"]:
            title_bar.setStyleSheet("""
                background-color: #1A415E;
                border: none;
                border-radius: 8px;
                margin-bottom: 0px;
            """)
        else:
            title_bar.setStyleSheet("""
                background-color: #1A415E;
                border-radius: 8px;
                margin-bottom: 0px;
            """)

        return title_bar

    def _create_section_content(self, section_name, section_data) -> QtWidgets.QWidget:
        content = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        desc_widget = self._create_description_column(section_data["description"])
        layout.addWidget(desc_widget, 1)

        if section_name == "Respondent Info":
            form_widget = self._create_respondent_form_preview(section_data)
        elif section_name == "Org Map":
            form_widget = self._create_org_map_form_preview(section_data)
        elif section_name == "Processes":
            form_widget = self._create_processes_form_preview(section_data)
        elif section_name == "Pain Points":
            form_widget = self._create_pain_points_form_preview(section_data)
        elif section_name == "Data Sources":
            form_widget = self._create_data_sources_form_preview(section_data)
        elif section_name == "Compliance":
            form_widget = self._create_compliance_form_preview(section_data)
        elif section_name == "Feature Ideas":
            form_widget = self._create_feature_ideas_form_preview(section_data)
        elif section_name == "Reference Library":
            form_widget = self._create_reference_library_form_preview(section_data)
        elif section_name == "Time & Resource Management":
            form_widget = self._create_time_resource_form_preview(section_data)
        else:
            form_widget = self._create_generic_form_preview(section_name, section_data)

        layout.addWidget(form_widget, 1)

        content.setStyleSheet("""
            background-color: #1a1a1a;
            margin-bottom: 15px;
        """)

        return content

    def _create_description_column(self, description) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)

        purpose_label = QtWidgets.QLabel("Purpose:")
        purpose_label.setStyleSheet("""
            color: #F9FAFB;
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 8px;
            background: transparent;
            border: none;
        """)
        layout.addWidget(purpose_label)

        desc_label = QtWidgets.QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("""
            color: #D1D5DB;
            font-size: 14px;
            line-height: 1.5;
            background: transparent;
            border: none;
        """)
        layout.addWidget(desc_label)
        layout.addStretch()

        widget.setStyleSheet("""
            QWidget {
                background: transparent;
                border: none;
            }
        """)

        return widget

    def _create_respondent_form_preview(self, section_data) -> QtWidgets.QWidget:
        card = QtWidgets.QFrame()
        card.setStyleSheet("""
            background: #FFFFFF;
            border: 1px solid #E5E7EB;
            border-radius: 12px;
            margin: 20px 20px 35px 20px;
        """)

        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(8)

        form_layout = QtWidgets.QVBoxLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.addLayout(form_layout)
        card_layout.setAlignment(form_layout, QtCore.Qt.AlignmentFlag.AlignTop)

        title = QtWidgets.QLabel("Respondent Profile")
        title.setStyleSheet("""
            font-size: 16px;
            font-weight: 600;
            color: #1F2937;
            background: transparent;
            border: none;
            margin: 0; padding: 0;
        """)
        form_layout.addWidget(title)

        subtitle = QtWidgets.QLabel("Please enter basic information about who you are.")
        subtitle.setStyleSheet("""
            color: #6B7280;
            font-size: 12px;
            background: transparent;
            border: none;
            margin: 0; padding: 0;
        """)
        form_layout.addSpacing(-3)
        form_layout.addWidget(subtitle)
        form_layout.addSpacing(15)

        fields = [
            {"name": "Full Name", "key": "full_name", "placeholder": "e.g., Dana Rivera", "required": True},
            {"name": "Work Email", "key": "work_email", "placeholder": "dana@company.com", "required": True},
            {"name": "Department", "key": "department", "placeholder": "e.g., Support", "required": False},
            {"name": "Role / Title", "key": "role_title", "placeholder": "Customer Support Lead", "required": False},
            {"name": "Primary Responsibilities", "key": "responsibilities", "placeholder": "Summarize duties & metrics", "required": False, "type": "textarea"}
        ]

        for field_info in fields:
            field_widget = self._create_individual_field(field_info)
            form_layout.addWidget(field_widget)

        return card

    def _create_individual_field(self, field_info):
        field_key = f"respondent_{field_info['key']}"
        self.field_group_states[field_key] = True

        field_widget = FieldGroupWidget(
            field_key,
            field_info["name"],
            enabled=True,
            required=field_info["required"]
        )
        field_widget.toggled.connect(self._on_field_group_toggled)

        field_layout = QtWidgets.QVBoxLayout(field_widget)
        field_layout.setContentsMargins(8, 8, 8, 8)
        field_layout.setSpacing(6)

        label_text = field_info["name"]
        if field_info["required"]:
            label_text += " *"

        field_label = QtWidgets.QLabel(label_text)
        field_label.setStyleSheet("""
            font-size: 13px; 
            color: #334155; 
            background: transparent;
            border: none;
            margin: 0px;
            padding: 0px;
        """)
        cursor = QtCore.Qt.ForbiddenCursor if field_info["required"] else QtCore.Qt.PointingHandCursor
        field_label.setCursor(cursor)
        field_layout.addWidget(field_label)

        field_input = QtWidgets.QLabel()
        field_input.setText(field_info["placeholder"])

        if field_info.get("type") == "textarea":
            field_input.setMinimumHeight(80)
            field_input.setMaximumHeight(80)
            field_input.setWordWrap(True)
            field_input.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        else:
            field_input.setMinimumHeight(38)
            field_input.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)

        field_input.setStyleSheet("""
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 8px 10px;
            color: #9CA3AF;
            margin: 0px;
        """)

        field_input.setCursor(cursor)
        field_layout.addWidget(field_input)

        field_widget.field_label = field_label
        field_widget.field_input = field_input
        field_widget.placeholder_text = field_info["placeholder"]

        return field_widget

    def _create_processes_form_preview(self, section_data) -> QtWidgets.QWidget:
        card = QtWidgets.QFrame()
        card.setStyleSheet("""
            background: #FFFFFF;
            border: 1px solid #E5E7EB;
            border-radius: 12px;
            margin: 20px 20px 35px 20px;
        """)

        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(8)

        form_layout = QtWidgets.QVBoxLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.addLayout(form_layout)
        card_layout.setAlignment(form_layout, QtCore.Qt.AlignmentFlag.AlignTop)

        title = QtWidgets.QLabel("Business Processes")
        title.setStyleSheet("""
            font-size: 16px;
            font-weight: 600;
            color: #1F2937;
            background: transparent;
            border: none;
            margin: 0; padding: 0;
        """)
        form_layout.addWidget(title)

        subtitle = QtWidgets.QLabel("Describe the business processes you regularly perform.")
        subtitle.setStyleSheet("""
            color: #6B7280;
            font-size: 12px;
            background: transparent;
            border: none;
            margin: 0; padding: 0;
        """)
        form_layout.addSpacing(-3)
        form_layout.addWidget(subtitle)
        form_layout.addSpacing(15)

        fields = [
            {"name": "Process Name", "key": "process_name", "placeholder": "e.g., Weekly Sales Report",
             "required": False},
            {"name": "Process Description", "key": "process_description", "placeholder": "Describe the steps involved",
             "required": False, "type": "textarea"},
            {"name": "Frequency", "key": "frequency", "placeholder": "Daily, Weekly, Monthly, etc.", "required": False},
            {"name": "Time Investment", "key": "time_investment", "placeholder": "How long does this take?",
             "required": False},
            {"name": "Screenshots/Attachments", "key": "attachments", "placeholder": "Supporting documentation",
             "required": False}
        ]

        for field_info in fields:
            field_widget = self._create_individual_field_processes(field_info)
            form_layout.addWidget(field_widget)

        return card

    def _create_feature_ideas_form_preview(self, section_data) -> QtWidgets.QWidget:
        """Create Feature Ideas form preview"""
        card = QtWidgets.QFrame()
        card.setStyleSheet("""
            background: #FFFFFF;
            border: 1px solid #E5E7EB;
            border-radius: 12px;
            margin: 20px 20px 35px 20px;
        """)

        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(8)

        form_layout = QtWidgets.QVBoxLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.addLayout(form_layout)
        card_layout.setAlignment(form_layout, QtCore.Qt.AlignmentFlag.AlignTop)

        title = QtWidgets.QLabel("Feature Ideas")
        title.setStyleSheet("""
            font-size: 16px;
            font-weight: 600;
            color: #1F2937;
            background: transparent;
            border: none;
            margin: 0; padding: 0;
        """)
        form_layout.addWidget(title)

        subtitle = QtWidgets.QLabel(
            "Describe automation opportunities by outlining step-by-step implementation processes.")
        subtitle.setStyleSheet("""
            color: #6B7280;
            font-size: 12px;
            background: transparent;
            border: none;
            margin: 0; padding: 0;
        """)
        form_layout.addSpacing(-3)
        form_layout.addWidget(subtitle)
        form_layout.addSpacing(15)

        fields = [
            {"name": "Feature Title", "key": "feature_title",
             "placeholder": "e.g., Automated Email Response System", "required": True},
            {"name": "Problem Description", "key": "problem_description",
             "placeholder": "What specific problem does this solve?", "required": True, "type": "textarea"},
            {"name": "Expected Outcome", "key": "expected_outcome",
             "placeholder": "How would you know this automation is working successfully?", "required": True,
             "type": "textarea"},
            {"name": "Implementation Steps", "key": "implementation_steps",
             "placeholder": "Multi-step process editor with data dependency tracking", "required": False},
            {"name": "Screenshots/Attachments", "key": "attachments",
             "placeholder": "Supporting documentation", "required": False}
        ]

        for field_info in fields:
            field_widget = self._create_individual_field_feature_ideas(field_info)
            form_layout.addWidget(field_widget)

        return card

    def _create_individual_field_feature_ideas(self, field_info):
        """Create individual Feature Ideas field with proper styling"""
        field_key = f"feature_ideas_{field_info['key']}"
        self.field_group_states[field_key] = True

        field_widget = FieldGroupWidget(
            field_key,
            field_info["name"],
            enabled=True,
            required=field_info["required"]
        )
        field_widget.toggled.connect(self._on_field_group_toggled)

        field_layout = QtWidgets.QVBoxLayout(field_widget)
        field_layout.setContentsMargins(8, 8, 8, 8)
        field_layout.setSpacing(6)

        label_text = field_info["name"]
        if field_info["required"]:
            label_text += " *"

        field_label = QtWidgets.QLabel(label_text)
        field_label.setStyleSheet("""
            font-size: 13px; 
            color: #334155; 
            background: transparent;
            border: none;
            margin: 0px;
            padding: 0px;
        """)
        cursor = QtCore.Qt.ForbiddenCursor if field_info["required"] else QtCore.Qt.PointingHandCursor
        field_label.setCursor(cursor)
        field_layout.addWidget(field_label)

        field_input = QtWidgets.QLabel()
        field_input.setText(field_info["placeholder"])

        if field_info.get("type") == "textarea":
            field_input.setMinimumHeight(80)
            field_input.setMaximumHeight(80)
            field_input.setWordWrap(True)
            field_input.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        else:
            field_input.setMinimumHeight(38)
            field_input.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)

        field_input.setStyleSheet("""
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 8px 10px;
            color: #9CA3AF;
            margin: 0px;
        """)

        field_input.setCursor(cursor)
        field_layout.addWidget(field_input)

        field_widget.field_label = field_label
        field_widget.field_input = field_input
        field_widget.placeholder_text = field_info["placeholder"]

        return field_widget

    def _create_individual_field_processes(self, field_info):
        field_key = f"processes_{field_info['key']}"
        self.field_group_states[field_key] = True

        field_widget = FieldGroupWidget(
            field_key,
            field_info["name"],
            enabled=True,
            required=field_info["required"]
        )
        field_widget.toggled.connect(self._on_field_group_toggled)

        field_layout = QtWidgets.QVBoxLayout(field_widget)
        field_layout.setContentsMargins(8, 8, 8, 8)
        field_layout.setSpacing(6)

        label_text = field_info["name"]
        if field_info["required"]:
            label_text += " *"

        field_label = QtWidgets.QLabel(label_text)
        field_label.setStyleSheet("""
            font-size: 13px; 
            color: #334155; 
            background: transparent;
            border: none;
            margin: 0px;
            padding: 0px;
        """)
        cursor = QtCore.Qt.ForbiddenCursor if field_info["required"] else QtCore.Qt.PointingHandCursor
        field_label.setCursor(cursor)
        field_layout.addWidget(field_label)

        field_input = QtWidgets.QLabel()
        field_input.setText(field_info["placeholder"])

        if field_info.get("type") == "textarea":
            field_input.setMinimumHeight(80)
            field_input.setMaximumHeight(80)
            field_input.setWordWrap(True)
            field_input.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        else:
            field_input.setMinimumHeight(38)
            field_input.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)

        field_input.setStyleSheet("""
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 8px 10px;
            color: #9CA3AF;
            margin: 0px;
        """)

        field_input.setCursor(cursor)
        field_layout.addWidget(field_input)

        field_widget.field_label = field_label
        field_widget.field_input = field_input
        field_widget.placeholder_text = field_info["placeholder"]

        return field_widget

    def _create_org_map_form_preview(self, section_data) -> QtWidgets.QWidget:
        card = QtWidgets.QFrame()
        card.setStyleSheet("""
            background: #FFFFFF;
            border: 1px solid #E5E7EB;
            border-radius: 12px;
            margin: 20px 20px 35px 20px;
        """)

        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(8)

        form_layout = QtWidgets.QVBoxLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.addLayout(form_layout)
        card_layout.setAlignment(form_layout, QtCore.Qt.AlignmentFlag.AlignTop)

        title = QtWidgets.QLabel("Org Context")
        title.setStyleSheet("""
            font-size: 16px;
            font-weight: 600;
            color: #1F2937;
            background: transparent;
            border: none;
            margin: 0; padding: 0;
        """)
        form_layout.addWidget(title)

        subtitle = QtWidgets.QLabel("Please describe where your role is positioned, and your collaborators.")
        subtitle.setStyleSheet("""
            color: #6B7280;
            font-size: 12px;
            background: transparent;
            border: none;
            margin: 0; padding: 0;
        """)
        form_layout.addSpacing(-3)
        form_layout.addWidget(subtitle)
        form_layout.addSpacing(15)

        fields = [
            {"name": "Reports To", "key": "reports_to", "placeholder": "Manager name/title", "required": False},
            {"name": "Peer Teams", "key": "peer_teams", "placeholder": "e.g. Sales Ops, QA", "required": False},
            {"name": "Downstream Consumers", "key": "downstream_consumers", "placeholder": "e.g., Support", "required": False},
            {"name": "Org Notes", "key": "org_notes", "placeholder": "Key handoffs, dependencies, SLAs", "required": False, "type": "textarea"}
        ]

        for field_info in fields:
            field_widget = self._create_individual_field_org_map(field_info)
            form_layout.addWidget(field_widget)

        return card

    def _create_pain_points_form_preview(self, section_data) -> QtWidgets.QWidget:
        card = QtWidgets.QFrame()
        card.setStyleSheet("""
            background: #FFFFFF;
            border: 1px solid #E5E7EB;
            border-radius: 12px;
            margin: 20px 20px 35px 20px;
        """)

        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(8)

        form_layout = QtWidgets.QVBoxLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.addLayout(form_layout)
        card_layout.setAlignment(form_layout, QtCore.Qt.AlignmentFlag.AlignTop)

        title = QtWidgets.QLabel("Pain Points")
        title.setStyleSheet("""
            font-size: 16px;
            font-weight: 600;
            color: #1F2937;
            background: transparent;
            border: none;
            margin: 0; padding: 0;
        """)
        form_layout.addWidget(title)

        subtitle = QtWidgets.QLabel(
            "Identify areas where time is wasted or errors occur. Add attachments and screenshots for context.")
        subtitle.setStyleSheet("""
            color: #6B7280;
            font-size: 12px;
            background: transparent;
            border: none;
            margin: 0; padding: 0;
        """)
        form_layout.addSpacing(-3)
        form_layout.addWidget(subtitle)
        form_layout.addSpacing(15)

        fields = [
            {"name": "Pain Name", "key": "pain_name",
             "placeholder": "Brief name for this pain point (e.g., Manual data entry delays)", "required": True},
            {"name": "Impact", "key": "impact", "placeholder": "Very Low, Low, Medium, High, Very High",
             "required": True},
            {"name": "Frequency", "key": "frequency", "placeholder": "Randomly, Daily, Weekly, Monthly, Yearly",
             "required": True},
            {"name": "Notes", "key": "notes",
             "placeholder": "Describe the issue, downstream effects, and potential workarounds...", "required": True,
             "type": "textarea"},
            {"name": "Screenshots/Attachments", "key": "attachments", "placeholder": "Supporting documentation",
             "required": False}
        ]

        for field_info in fields:
            field_widget = self._create_individual_field_pain_points(field_info)
            form_layout.addWidget(field_widget)

        return card

    def _create_data_sources_form_preview(self, section_data) -> QtWidgets.QWidget:
        card = QtWidgets.QFrame()
        card.setStyleSheet("""
            background: #FFFFFF;
            border: 1px solid #E5E7EB;
            border-radius: 12px;
            margin: 20px 20px 35px 20px;
        """)

        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(8)

        form_layout = QtWidgets.QVBoxLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.addLayout(form_layout)
        card_layout.setAlignment(form_layout, QtCore.Qt.AlignmentFlag.AlignTop)

        title = QtWidgets.QLabel("Data Sources")
        title.setStyleSheet("""
            font-size: 16px;
            font-weight: 600;
            color: #1F2937;
            background: transparent;
            border: none;
            margin: 0; padding: 0;
        """)
        form_layout.addWidget(title)

        subtitle = QtWidgets.QLabel(
            "Configure connection details for databases, APIs, and other data systems. Credentials will be collected securely after export.")
        subtitle.setStyleSheet("""
            color: #6B7280;
            font-size: 12px;
            background: transparent;
            border: none;
            margin: 0; padding: 0;
        """)
        form_layout.addSpacing(-3)
        form_layout.addWidget(subtitle)
        form_layout.addSpacing(15)

        fields = [
            {"name": "Source Name", "key": "source_name",
             "placeholder": "Descriptive name for this data source (e.g., Customer Database)", "required": True},
            {"name": "Connection Type", "key": "connection_type",
             "placeholder": "Database, API/Web Service, File System, Cloud Service, etc.", "required": True},
            {"name": "Description", "key": "description",
             "placeholder": "Describe what data this source contains and how it will be used...", "required": True,
             "type": "textarea"},
            {"name": "Screenshots/Attachments", "key": "attachments", "placeholder": "Supporting documentation",
             "required": False}
        ]

        for field_info in fields:
            field_widget = self._create_individual_field_data_sources(field_info)
            form_layout.addWidget(field_widget)

        return card

    def _create_compliance_form_preview(self, section_data) -> QtWidgets.QWidget:
        card = QtWidgets.QFrame()
        card.setStyleSheet("""
            background: #FFFFFF;
            border: 1px solid #E5E7EB;
            border-radius: 12px;
            margin: 20px 20px 35px 20px;
        """)

        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(8)

        form_layout = QtWidgets.QVBoxLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.addLayout(form_layout)
        card_layout.setAlignment(form_layout, QtCore.Qt.AlignmentFlag.AlignTop)

        title = QtWidgets.QLabel("Compliance Requirements")
        title.setStyleSheet("""
            font-size: 16px;
            font-weight: 600;
            color: #1F2937;
            background: transparent;
            border: none;
            margin: 0; padding: 0;
        """)
        form_layout.addWidget(title)

        subtitle = QtWidgets.QLabel(
            "Document regulatory requirements, compliance status, and evidence management for your organization.")
        subtitle.setStyleSheet("""
            color: #6B7280;
            font-size: 12px;
            background: transparent;
            border: none;
            margin: 0; padding: 0;
        """)
        form_layout.addSpacing(-3)
        form_layout.addWidget(subtitle)
        form_layout.addSpacing(15)

        fields = [
            # Organization Context (Required)
            {"name": "Industry Sector", "key": "industry",
             "placeholder": "e.g., Healthcare, Financial Services, Manufacturing, Technology", "required": True},
            {"name": "Company Size", "key": "company_size", "placeholder": "Micro, Small, Medium, Large, Enterprise",
             "required": True},
            {"name": "Geographic Scope", "key": "geographic_scope",
             "placeholder": "Countries/regions where you operate (e.g., US, EU, Canada, Global)", "required": True},
            {"name": "Business Activities", "key": "business_activities",
             "placeholder": "Key business activities that may trigger compliance requirements", "required": True,
             "type": "textarea"},

            # Individual Requirements (Required)
            {"name": "Requirement Name", "key": "requirement_name",
             "placeholder": "e.g., GDPR Article 32 - Security of Processing", "required": True},
            {"name": "Authority/Regulator", "key": "authority", "placeholder": "e.g., GDPR, SEC, FDA, OSHA",
             "required": True},

            # Optional fields for admin control
            {"name": "Data Types Handled", "key": "data_types", "placeholder": "Types of data you collect/process",
             "required": False, "type": "textarea"},
            {"name": "Third-Party Vendors", "key": "vendors", "placeholder": "Key vendors that may impact compliance",
             "required": False, "type": "textarea"},
            {"name": "Responsible Person", "key": "responsible",
             "placeholder": "Name or role responsible for this requirement", "required": False},
            {"name": "Evidence Required", "key": "evidence", "placeholder": "Required documentation and evidence",
             "required": False, "type": "textarea"},
            {"name": "Status", "key": "status", "placeholder": "Not Assessed, Compliant, Non-Compliant, In Progress",
             "required": False},
            {"name": "Risk Level", "key": "risk", "placeholder": "Low, Medium, High, Critical", "required": False},
            {"name": "Notes", "key": "notes",
             "placeholder": "Additional compliance notes, requirements, and considerations...", "required": False,
             "type": "textarea"},
            {"name": "Screenshots/Attachments", "key": "attachments", "placeholder": "Supporting documentation",
             "required": False}
        ]

        for field_info in fields:
            field_widget = self._create_individual_field_compliance(field_info)
            form_layout.addWidget(field_widget)

        return card

    def _create_individual_field_compliance(self, field_info):
        field_key = f"compliance_{field_info['key']}"
        self.field_group_states[field_key] = True

        field_widget = FieldGroupWidget(
            field_key,
            field_info["name"],
            enabled=True,
            required=field_info["required"]
        )
        field_widget.toggled.connect(self._on_field_group_toggled)

        field_layout = QtWidgets.QVBoxLayout(field_widget)
        field_layout.setContentsMargins(8, 8, 8, 8)
        field_layout.setSpacing(6)

        label_text = field_info["name"]
        if field_info["required"]:
            label_text += " *"

        field_label = QtWidgets.QLabel(label_text)
        field_label.setStyleSheet("""
            font-size: 13px; 
            color: #334155; 
            background: transparent;
            border: none;
            margin: 0px;
            padding: 0px;
        """)
        cursor = QtCore.Qt.ForbiddenCursor if field_info["required"] else QtCore.Qt.PointingHandCursor
        field_label.setCursor(cursor)
        field_layout.addWidget(field_label)

        field_input = QtWidgets.QLabel()
        field_input.setText(field_info["placeholder"])

        if field_info.get("type") == "textarea":
            field_input.setMinimumHeight(80)
            field_input.setMaximumHeight(80)
            field_input.setWordWrap(True)
            field_input.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        else:
            field_input.setMinimumHeight(38)
            field_input.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)

        field_input.setStyleSheet("""
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 8px 10px;
            color: #9CA3AF;
            margin: 0px;
        """)

        field_input.setCursor(cursor)
        field_layout.addWidget(field_input)

        field_widget.field_label = field_label
        field_widget.field_input = field_input
        field_widget.placeholder_text = field_info["placeholder"]

        return field_widget

    def _create_individual_field_pain_points(self, field_info):
        field_key = f"pain_points_{field_info['key']}"
        self.field_group_states[field_key] = True

        field_widget = FieldGroupWidget(
            field_key,
            field_info["name"],
            enabled=True,
            required=field_info["required"]
        )
        field_widget.toggled.connect(self._on_field_group_toggled)

        field_layout = QtWidgets.QVBoxLayout(field_widget)
        field_layout.setContentsMargins(8, 8, 8, 8)
        field_layout.setSpacing(6)

        label_text = field_info["name"]
        if field_info["required"]:
            label_text += " *"

        field_label = QtWidgets.QLabel(label_text)
        field_label.setStyleSheet("""
            font-size: 13px; 
            color: #334155; 
            background: transparent;
            border: none;
            margin: 0px;
            padding: 0px;
        """)
        cursor = QtCore.Qt.ForbiddenCursor if field_info["required"] else QtCore.Qt.PointingHandCursor
        field_label.setCursor(cursor)
        field_layout.addWidget(field_label)

        field_input = QtWidgets.QLabel()
        field_input.setText(field_info["placeholder"])

        if field_info.get("type") == "textarea":
            field_input.setMinimumHeight(80)
            field_input.setMaximumHeight(80)
            field_input.setWordWrap(True)
            field_input.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        else:
            field_input.setMinimumHeight(38)
            field_input.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)

        field_input.setStyleSheet("""
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 8px 10px;
            color: #9CA3AF;
            margin: 0px;
        """)

        field_input.setCursor(cursor)
        field_layout.addWidget(field_input)

        field_widget.field_label = field_label
        field_widget.field_input = field_input
        field_widget.placeholder_text = field_info["placeholder"]

        return field_widget

    def _create_individual_field_data_sources(self, field_info):
        field_key = f"data_sources_{field_info['key']}"
        self.field_group_states[field_key] = True

        field_widget = FieldGroupWidget(
            field_key,
            field_info["name"],
            enabled=True,
            required=field_info["required"]
        )
        field_widget.toggled.connect(self._on_field_group_toggled)

        field_layout = QtWidgets.QVBoxLayout(field_widget)
        field_layout.setContentsMargins(8, 8, 8, 8)
        field_layout.setSpacing(6)

        label_text = field_info["name"]
        if field_info["required"]:
            label_text += " *"

        field_label = QtWidgets.QLabel(label_text)
        field_label.setStyleSheet("""
            font-size: 13px; 
            color: #334155; 
            background: transparent;
            border: none;
            margin: 0px;
            padding: 0px;
        """)
        cursor = QtCore.Qt.ForbiddenCursor if field_info["required"] else QtCore.Qt.PointingHandCursor
        field_label.setCursor(cursor)
        field_layout.addWidget(field_label)

        field_input = QtWidgets.QLabel()
        field_input.setText(field_info["placeholder"])

        if field_info.get("type") == "textarea":
            field_input.setMinimumHeight(80)
            field_input.setMaximumHeight(80)
            field_input.setWordWrap(True)
            field_input.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        else:
            field_input.setMinimumHeight(38)
            field_input.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)

        field_input.setStyleSheet("""
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 8px 10px;
            color: #9CA3AF;
            margin: 0px;
        """)

        field_input.setCursor(cursor)
        field_layout.addWidget(field_input)

        field_widget.field_label = field_label
        field_widget.field_input = field_input
        field_widget.placeholder_text = field_info["placeholder"]

        return field_widget

    def _create_individual_field_org_map(self, field_info):
        field_key = f"org_map_{field_info['key']}"
        self.field_group_states[field_key] = True

        field_widget = FieldGroupWidget(
            field_key,
            field_info["name"],
            enabled=True,
            required=field_info["required"]
        )
        field_widget.toggled.connect(self._on_field_group_toggled)

        field_layout = QtWidgets.QVBoxLayout(field_widget)
        field_layout.setContentsMargins(8, 8, 8, 8)
        field_layout.setSpacing(6)

        label_text = field_info["name"]
        if field_info["required"]:
            label_text += " *"

        field_label = QtWidgets.QLabel(label_text)
        field_label.setStyleSheet("""
            font-size: 13px; 
            color: #334155; 
            background: transparent;
            border: none;
            margin: 0px;
            padding: 0px;
        """)
        cursor = QtCore.Qt.ForbiddenCursor if field_info["required"] else QtCore.Qt.PointingHandCursor
        field_label.setCursor(cursor)
        field_layout.addWidget(field_label)

        field_input = QtWidgets.QLabel()
        field_input.setText(field_info["placeholder"])

        if field_info.get("type") == "textarea":
            field_input.setMinimumHeight(80)
            field_input.setMaximumHeight(80)
            field_input.setWordWrap(True)
            field_input.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        else:
            field_input.setMinimumHeight(38)
            field_input.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)

        field_input.setStyleSheet("""
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 8px 10px;
            color: #9CA3AF;
            margin: 0px;
        """)

        field_input.setCursor(cursor)
        field_layout.addWidget(field_input)

        field_widget.field_label = field_label
        field_widget.field_input = field_input
        field_widget.placeholder_text = field_info["placeholder"]

        return field_widget

    def _create_processes_form_preview(self, section_data) -> QtWidgets.QWidget:
        card = QtWidgets.QFrame()
        card.setStyleSheet("""
            background: #FFFFFF;
            border: 1px solid #E5E7EB;
            border-radius: 12px;
            margin: 20px 20px 35px 20px;
        """)

        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(8)

        form_layout = QtWidgets.QVBoxLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.addLayout(form_layout)
        card_layout.setAlignment(form_layout, QtCore.Qt.AlignmentFlag.AlignTop)

        title = QtWidgets.QLabel("Core Processes")
        title.setStyleSheet("""
            font-size: 16px;
            font-weight: 600;
            color: #1F2937;
            background: transparent;
            border: none;
            margin: 0; padding: 0;
        """)
        form_layout.addWidget(title)

        subtitle = QtWidgets.QLabel("Add one process per entry. You can attach documents and capture screenshots.")
        subtitle.setStyleSheet("""
            color: #6B7280;
            font-size: 12px;
            background: transparent;
            border: none;
            margin: 0; padding: 0;
        """)
        form_layout.addSpacing(-3)
        form_layout.addWidget(subtitle)
        form_layout.addSpacing(15)

        fields = [
            {"name": "Title", "key": "title", "placeholder": "Process title (e.g., Client Onboarding Workflow)",
             "required": True},
            {"name": "Notes", "key": "notes",
             "placeholder": "Briefly describe the steps, systems involved, and expected outcomes.", "required": True,
             "type": "textarea"},
            {"name": "Screenshots/Attachments", "key": "attachments", "placeholder": "Supporting documentation",
             "required": False}
        ]

        for field_info in fields:
            field_widget = self._create_individual_field_processes(field_info)
            form_layout.addWidget(field_widget)

        return card

    def _create_individual_field_processes(self, field_info):
        field_key = f"processes_{field_info['key']}"
        self.field_group_states[field_key] = True

        field_widget = FieldGroupWidget(
            field_key,
            field_info["name"],
            enabled=True,
            required=field_info["required"]
        )
        field_widget.toggled.connect(self._on_field_group_toggled)

        field_layout = QtWidgets.QVBoxLayout(field_widget)
        field_layout.setContentsMargins(8, 8, 8, 8)
        field_layout.setSpacing(6)

        label_text = field_info["name"]
        if field_info["required"]:
            label_text += " *"

        field_label = QtWidgets.QLabel(label_text)
        field_label.setStyleSheet("""
            font-size: 13px; 
            color: #334155; 
            background: transparent;
            border: none;
            margin: 0px;
            padding: 0px;
        """)
        cursor = QtCore.Qt.ForbiddenCursor if field_info["required"] else QtCore.Qt.PointingHandCursor
        field_label.setCursor(cursor)
        field_layout.addWidget(field_label)

        field_input = QtWidgets.QLabel()
        field_input.setText(field_info["placeholder"])

        if field_info.get("type") == "textarea":
            field_input.setMinimumHeight(80)
            field_input.setMaximumHeight(80)
            field_input.setWordWrap(True)
            field_input.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        else:
            field_input.setMinimumHeight(38)
            field_input.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)

        field_input.setStyleSheet("""
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 8px 10px;
            color: #9CA3AF;
            margin: 0px;
        """)

        field_input.setCursor(cursor)
        field_layout.addWidget(field_input)

        field_widget.field_label = field_label
        field_widget.field_input = field_input
        field_widget.placeholder_text = field_info["placeholder"]

        return field_widget

    def _create_reference_library_form_preview(self, section_data) -> QtWidgets.QWidget:
        """Create Reference Library form preview"""
        card = QtWidgets.QFrame()
        card.setStyleSheet("""
            background: #FFFFFF;
            border: 1px solid #E5E7EB;
            border-radius: 12px;
            margin: 20px 20px 35px 20px;
        """)

        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(8)

        form_layout = QtWidgets.QVBoxLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.addLayout(form_layout)
        card_layout.setAlignment(form_layout, QtCore.Qt.AlignmentFlag.AlignTop)

        title = QtWidgets.QLabel("Reference Library")
        title.setStyleSheet("""
            font-size: 16px;
            font-weight: 600;
            color: #1F2937;
            background: transparent;
            border: none;
            margin: 0; padding: 0;
        """)
        form_layout.addWidget(title)

        subtitle = QtWidgets.QLabel(
            "Central repository for organizational documents, policies, and reference materials.")
        subtitle.setStyleSheet("""
            color: #6B7280;
            font-size: 12px;
            background: transparent;
            border: none;
            margin: 0; padding: 0;
        """)
        form_layout.addSpacing(-3)
        form_layout.addWidget(subtitle)
        form_layout.addSpacing(15)

        fields = [
            {"name": "Document Title", "key": "document_title",
             "placeholder": "Descriptive title for this document", "required": True},
            {"name": "File Attachment", "key": "file_attachment",
             "placeholder": "Upload document or capture screenshot", "required": True},
            {"name": "Category", "key": "category",
             "placeholder": "Organizational, Process Documentation, Policies & Procedures, etc.", "required": False},
            {"name": "Description", "key": "description",
             "placeholder": "Brief description of the document's content and purpose", "required": False,
             "type": "textarea"},
            {"name": "Tags", "key": "tags",
             "placeholder": "Keywords for organization and searchability", "required": False}
        ]

        for field_info in fields:
            field_widget = self._create_individual_field_reference_library(field_info)
            form_layout.addWidget(field_widget)

        return card

    def _create_time_resource_form_preview(self, section_data) -> QtWidgets.QWidget:
        """Create Time & Resource Management form preview"""
        card = QtWidgets.QFrame()
        card.setStyleSheet("""
            background: #FFFFFF;
            border: 1px solid #E5E7EB;
            border-radius: 12px;
            margin: 20px 20px 35px 20px;
        """)

        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(8)

        form_layout = QtWidgets.QVBoxLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.addLayout(form_layout)
        card_layout.setAlignment(form_layout, QtCore.Qt.AlignmentFlag.AlignTop)

        title = QtWidgets.QLabel("Time & Resource Management")
        title.setStyleSheet("""
            font-size: 16px;
            font-weight: 600;
            color: #1F2937;
            background: transparent;
            border: none;
            margin: 0; padding: 0;
        """)
        form_layout.addWidget(title)

        subtitle = QtWidgets.QLabel(
            "Track how you spend your time and identify resource constraints that impact productivity.")
        subtitle.setStyleSheet("""
            color: #6B7280;
            font-size: 12px;
            background: transparent;
            border: none;
            margin: 0; padding: 0;
        """)
        form_layout.addSpacing(-3)
        form_layout.addWidget(subtitle)
        form_layout.addSpacing(15)

        # Overview Analysis section (required)
        overview_fields = [
            {"name": "Primary Activities", "key": "primary_activities",
             "placeholder": "Describe your main work activities and responsibilities", "required": True,
             "type": "textarea"},
            {"name": "Peak Workload Periods", "key": "peak_workload_periods",
             "placeholder": "When is your workload most intense? (daily, weekly, monthly patterns)", "required": True,
             "type": "textarea"},
            {"name": "Resource Constraints", "key": "resource_constraints",
             "placeholder": "What limits your productivity? (tools, information, approvals, etc.)", "required": True,
             "type": "textarea"},
            {"name": "Waiting Time", "key": "waiting_time",
             "placeholder": "Time spent waiting for approvals, information, responses, etc.", "required": True,
             "type": "textarea"},
            {"name": "Overtime Patterns", "key": "overtime_patterns",
             "placeholder": "When and why do you work overtime?", "required": True, "type": "textarea"},
            {"name": "Additional Notes", "key": "notes",
             "placeholder": "Any other time management or resource-related observations", "required": True,
             "type": "textarea"}
        ]

        # Add section header for overview
        overview_header = QtWidgets.QLabel("Overview Analysis")
        overview_header.setStyleSheet("""
            font-size: 14px;
            font-weight: 600;
            color: #374151;
            background: transparent;
            border: none;
            margin: 8px 0px 4px 0px;
            padding: 0px;
        """)
        form_layout.addWidget(overview_header)

        for field_info in overview_fields:
            field_widget = self._create_individual_field_time_resource(field_info)
            form_layout.addWidget(field_widget)

        # Time Allocation Tracking section (optional)
        form_layout.addSpacing(10)

        tracking_header = QtWidgets.QLabel("Time Allocation Tracking")
        tracking_header.setStyleSheet("""
            font-size: 14px;
            font-weight: 600;
            color: #374151;
            background: transparent;
            border: none;
            margin: 8px 0px 4px 0px;
            padding: 0px;
        """)
        form_layout.addWidget(tracking_header)

        tracking_fields = [
            {"name": "Activity Name", "key": "activity_name",
             "placeholder": "e.g., Email processing, Report generation", "required": False},
            {"name": "Hours per Week", "key": "hours_per_week",
             "placeholder": "Numeric input with spinner control", "required": False},
            {"name": "Priority Level", "key": "priority_level",
             "placeholder": "High, Medium, Low", "required": False},
            {"name": "Activity Notes", "key": "activity_notes",
             "placeholder": "Additional details about this activity", "required": False, "type": "textarea"},
            {"name": "Screenshots/Attachments", "key": "attachments",
             "placeholder": "Supporting documentation", "required": False}
        ]

        for field_info in tracking_fields:
            field_widget = self._create_individual_field_time_resource(field_info)
            form_layout.addWidget(field_widget)

        return card

    def _create_individual_field_time_resource(self, field_info):
        """Create individual Time & Resource Management field with proper styling"""
        field_key = f"time_resource_{field_info['key']}"
        self.field_group_states[field_key] = True

        field_widget = FieldGroupWidget(
            field_key,
            field_info["name"],
            enabled=True,
            required=field_info["required"]
        )
        field_widget.toggled.connect(self._on_field_group_toggled)

        field_layout = QtWidgets.QVBoxLayout(field_widget)
        field_layout.setContentsMargins(8, 8, 8, 8)
        field_layout.setSpacing(6)

        label_text = field_info["name"]
        if field_info["required"]:
            label_text += " *"

        field_label = QtWidgets.QLabel(label_text)
        field_label.setStyleSheet("""
            font-size: 13px; 
            color: #334155; 
            background: transparent;
            border: none;
            margin: 0px;
            padding: 0px;
        """)
        cursor = QtCore.Qt.ForbiddenCursor if field_info["required"] else QtCore.Qt.PointingHandCursor
        field_label.setCursor(cursor)
        field_layout.addWidget(field_label)

        field_input = QtWidgets.QLabel()
        field_input.setText(field_info["placeholder"])

        if field_info.get("type") == "textarea":
            field_input.setMinimumHeight(80)
            field_input.setMaximumHeight(80)
            field_input.setWordWrap(True)
            field_input.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        else:
            field_input.setMinimumHeight(38)
            field_input.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)

        field_input.setStyleSheet("""
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 8px 10px;
            color: #9CA3AF;
            margin: 0px;
        """)

        field_input.setCursor(cursor)
        field_layout.addWidget(field_input)

        field_widget.field_label = field_label
        field_widget.field_input = field_input
        field_widget.placeholder_text = field_info["placeholder"]

        return field_widget

    def _create_individual_field_reference_library(self, field_info):
        """Create individual Reference Library field with proper styling"""
        field_key = f"reference_library_{field_info['key']}"
        self.field_group_states[field_key] = True

        field_widget = FieldGroupWidget(
            field_key,
            field_info["name"],
            enabled=True,
            required=field_info["required"]
        )
        field_widget.toggled.connect(self._on_field_group_toggled)

        field_layout = QtWidgets.QVBoxLayout(field_widget)
        field_layout.setContentsMargins(8, 8, 8, 8)
        field_layout.setSpacing(6)

        label_text = field_info["name"]
        if field_info["required"]:
            label_text += " *"

        field_label = QtWidgets.QLabel(label_text)
        field_label.setStyleSheet("""
            font-size: 13px; 
            color: #334155; 
            background: transparent;
            border: none;
            margin: 0px;
            padding: 0px;
        """)
        cursor = QtCore.Qt.ForbiddenCursor if field_info["required"] else QtCore.Qt.PointingHandCursor
        field_label.setCursor(cursor)
        field_layout.addWidget(field_label)

        field_input = QtWidgets.QLabel()
        field_input.setText(field_info["placeholder"])

        if field_info.get("type") == "textarea":
            field_input.setMinimumHeight(80)
            field_input.setMaximumHeight(80)
            field_input.setWordWrap(True)
            field_input.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        else:
            field_input.setMinimumHeight(38)
            field_input.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)

        field_input.setStyleSheet("""
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 8px 10px;
            color: #9CA3AF;
            margin: 0px;
        """)

        field_input.setCursor(cursor)
        field_layout.addWidget(field_input)

        field_widget.field_label = field_label
        field_widget.field_input = field_input
        field_widget.placeholder_text = field_info["placeholder"]

        return field_widget

    def _create_generic_form_preview(self, section_name, section_data) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)

        placeholder = QtWidgets.QLabel(f"{section_name} form preview\n(To be implemented)")
        placeholder.setAlignment(QtCore.Qt.AlignCenter)
        placeholder.setStyleSheet("""
            color: #6B7280;
            font-style: italic;
            font-size: 14px;
            background: #F9FAFB;
            border: 2px dashed #E5E7EB;
            border-radius: 8px;
            padding: 40px;
            margin: 20px;
        """)
        layout.addWidget(placeholder)
        return widget

    def _connect_signals(self):
        pass

    def _on_section_toggled(self, section_name, enabled):
        container = self.section_widgets.get(section_name)
        if container:
            content_widget = container.layout().itemAt(1).widget()
            content_widget.setVisible(enabled)

        if section_name in self.sections["optional_sections"]:
            self.sections["optional_sections"][section_name]["enabled"] = enabled

        self._validate_form()

    def _on_field_group_toggled(self, field_group_key, enabled):
        self.field_group_states[field_group_key] = enabled
        self._validate_form()

    def _validate_form(self):
        self.canProceed.emit(True)

    def validate_page(self) -> Tuple[bool, str]:
        return True, ""

    def collect_data(self) -> Dict[str, Any]:
        data = {
            "sections": {},
            "field_groups": self.field_group_states.copy()
        }

        all_sections = {**self.sections["core_sections"], **self.sections["optional_sections"]}
        for section_name, section_config in all_sections.items():
            data["sections"][section_name] = {
                "enabled": section_config["enabled"] or section_config["required"],
                "required": section_config["required"]
            }

        enabled_sections = sum(1 for s in data["sections"].values() if s["enabled"])
        enabled_field_groups = sum(1 for enabled in self.field_group_states.values() if enabled)

        data["summary"] = {
            "total_sections": len(data["sections"]),
            "enabled_sections": enabled_sections,
            "total_field_groups": len(self.field_group_states),
            "enabled_field_groups": enabled_field_groups
        }

        return data

    def load_data(self, data: Dict[str, Any]) -> None:
        sections_data = data.get("sections", {})
        for section_name, section_config in sections_data.items():
            if section_name in self.sections["optional_sections"]:
                enabled = section_config.get("enabled", False)
                self.sections["optional_sections"][section_name]["enabled"] = enabled

                if section_name in self.section_switches:
                    self.section_switches[section_name].setChecked(enabled)

                container = self.section_widgets.get(section_name)
                if container:
                    content_widget = container.layout().itemAt(1).widget()
                    content_widget.setVisible(enabled)

        field_groups_data = data.get("field_groups", {})
        self.field_group_states.update(field_groups_data)

        self._validate_form()
