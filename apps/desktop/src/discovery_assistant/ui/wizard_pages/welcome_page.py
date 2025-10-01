"""
Welcome Page - Step 1 of Admin Setup Wizard
Explains the importance of proper data source configuration for automation discovery.
"""

from typing import Dict, Any, Tuple
from PySide6 import QtWidgets, QtCore, QtGui
from discovery_assistant.wizard_base import WizardPage


class WelcomePage(WizardPage):
    """
    Step 1: Welcome page explaining the importance of data source setup.
    Matches the styling and architecture of the existing DataSourcesPage.
    """

    def __init__(self, parent=None):
        super().__init__("Welcome", parent)
        self._setup_ui()
        self._apply_styles()

        # Welcome page can always proceed (no validation required)
        self.canProceed.emit(True)

    def _setup_ui(self):
        """Set up the user interface components matching DataSourcesPage structure."""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)

        # Header section (matches DataSourcesPage pattern)
        header_layout = self._create_header()
        layout.addLayout(header_layout)

        # Main content area
        content_widget = self._create_content_area()
        layout.addWidget(content_widget, 1)

        # Footer section (informational only)
        footer_layout = self._create_footer()
        layout.addLayout(footer_layout)

    def _create_header(self) -> QtWidgets.QVBoxLayout:
        """Create page header with title and description matching DataSourcesPage style."""
        layout = QtWidgets.QVBoxLayout()

        # Title
        title = QtWidgets.QLabel("Welcome to Discovery Assistant Setup")
        title.setObjectName("pageTitle")
        title.setStyleSheet("""
            #pageTitle {
                font-size: 24px;
                font-weight: 600;
                color: #F9FAFB;
                margin-bottom: 8px;
            }
        """)

        # Description - FIXED: Removed line breaks for continuous text
        description = QtWidgets.QLabel(
            "This setup wizard will guide you through configuring Discovery Assistant for your organization. "
            "Proper configuration ensures accurate automation discovery and prevents confusion during data collection. "
            "The setup process consists of 6 steps that will help you define data sources, customize sections, "
            "configure privacy settings, and prepare your discovery environment for deployment.<br><br>"
            "<b>Once setup is complete, settings become locked and cannot be edited. If you need "
            "to make changes after generation, you can delete the policy and restart the setup "
            "process. However, respondents will need to reload the new policy file and any " 
            "discovery data they've entered will be lost.</b>"
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
        """Create the main content area with setup information."""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)

        # Why proper setup matters section
        benefits_group = self._create_benefits_section()
        layout.addWidget(benefits_group)

        # FIXED: Add more spacing between group boxes
        layout.addSpacing(25)

        # Setup process overview section
        process_group = self._create_process_section()
        layout.addWidget(process_group)

        # FIXED: Add spacer to prevent stretching when window grows
        layout.addStretch()

        return widget

    def _create_benefits_section(self) -> QtWidgets.QGroupBox:
        """Create benefits section explaining why proper setup matters."""
        group = QtWidgets.QGroupBox("Why Proper Setup Matters")
        group.setObjectName("benefitsGroup")
        layout = QtWidgets.QVBoxLayout(group)

        # Benefits description
        desc = QtWidgets.QLabel(
            "Taking time to properly configure Discovery Assistant provides significant benefits:"
        )
        desc.setStyleSheet("color: #9CA3AF; font-size: 12px; margin-left: 10px; margin-bottom: 15px;")
        layout.addWidget(desc)

        # Benefits list
        benefits = [
            ("Accurate Data Collection", "Well-configured data sources ensure comprehensive automation discovery"),
            ("Reduced Confusion", "Clear source definitions help respondents provide better information"),
            ("Improved Consolidation", "Consistent data structure enables better analysis and reporting"),
            ("Time Savings", "Proper setup reduces the need for data cleanup and manual corrections"),
            ("Better Insights", "Comprehensive configuration leads to more actionable automation recommendations")
        ]

        for title, description in benefits:
            benefit_widget = self._create_benefit_item(title, description)
            layout.addWidget(benefit_widget)

        layout.addSpacing(15)

        group.setStyleSheet("""
            QGroupBox#benefitsGroup {
                font-weight: 500;
                border: 2px solid #404040;
                border-radius: 8px;
                margin-top: 16px;
                padding-top: 15px;
                font-size: 20px;
            }
            QGroupBox#benefitsGroup::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #F9FAFB;
                font-size: 20px;
                font-weight: bold;
            }
        """)

        return group

    def _create_benefit_item(self, title: str, description: str) -> QtWidgets.QWidget:
        """Create an individual benefit item with title and description."""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(2)

        # Benefit title
        title_label = QtWidgets.QLabel(f"• {title}")
        title_label.setObjectName("benefitTitle")
        title_label.setStyleSheet("""
            #benefitTitle {
                font-size: 14px;
                font-weight: 500;
                color: #F9FAFB;
            }
        """)

        # Benefit description
        desc_label = QtWidgets.QLabel(description)
        desc_label.setObjectName("benefitDescription")
        desc_label.setWordWrap(True)
        desc_label.setIndent(15)
        desc_label.setStyleSheet("""
            #benefitDescription {
                font-size: 12px;
                color: #D1D5DB;
                line-height: 1.4;
            }
        """)

        layout.addWidget(title_label)
        layout.addWidget(desc_label)

        return widget

    def _create_process_section(self) -> QtWidgets.QGroupBox:
        """Create setup process overview section."""
        group = QtWidgets.QGroupBox("Setup Process Overview")
        group.setObjectName("processGroup")
        layout = QtWidgets.QVBoxLayout(group)

        # Process description
        desc = QtWidgets.QLabel(
            "The wizard will guide you through these key configuration areas:"
        )
        desc.setStyleSheet("color: #9CA3AF; font-size: 12px; margin-left: 10px; margin-bottom: 15px;")
        layout.addWidget(desc)

        # Setup steps overview
        steps = [
            ("Project Setup", "Configure organizational details and administrator contact information"),
            ("Data Sources", "Configure available data sources for automation discovery"),
            ("Section & Field Configuration", "Choose sections and customize fields for discovery"),
            ("Administrative Instructions", "Provide custom guidance and instructions for respondents"),
            ("Privacy & Data Settings", "Configure AI credits, privacy options, and service engagement"),
            ("Review & Generate", "Review all configurations and generate the project policy")
        ]

        for i, (step_title, step_description) in enumerate(steps, 1):  # Start at 2 since this is step 1
            step_widget = self._create_step_item(i, step_title, step_description)
            layout.addWidget(step_widget)

        layout.addSpacing(15)

        group.setStyleSheet("""
            QGroupBox#processGroup {
                font-weight: 500;
                border: 2px solid #404040;
                border-radius: 8px;
                margin-top: 16px;
                padding-top: 15px;
                font-size: 20px;
            }
            QGroupBox#processGroup::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #F9FAFB;
                font-size: 20px;
                font-weight: bold;
            }
        """)

        return group

    def _create_step_item(self, step_num: int, title: str, description: str) -> QtWidgets.QWidget:
        """Create an individual setup step item."""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(widget)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)

        # Step number
        step_label = QtWidgets.QLabel(f"{step_num}")
        step_label.setObjectName("stepNumber")
        step_label.setFixedSize(24, 24)
        step_label.setAlignment(QtCore.Qt.AlignCenter)
        step_label.setStyleSheet("""
            #stepNumber {
                background-color: #1A415E;
                color: #F9FAFB;
                border: 1px solid #606060;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 600;
            }
        """)

        # Step content
        content_layout = QtWidgets.QVBoxLayout()
        content_layout.setSpacing(2)

        # Step title
        title_label = QtWidgets.QLabel(title)
        title_label.setObjectName("stepTitle")
        title_label.setStyleSheet("""
            #stepTitle {
                font-size: 13px;
                font-weight: 500;
                color: #F9FAFB;
            }
        """)

        # Step description
        desc_label = QtWidgets.QLabel(description)
        desc_label.setObjectName("stepDescription")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("""
            #stepDescription {
                font-size: 11px;
                color: #D1D5DB;
                line-height: 1.3;
            }
        """)

        content_layout.addWidget(title_label)
        content_layout.addWidget(desc_label)

        layout.addWidget(step_label)
        layout.addLayout(content_layout)

        return widget

    def _create_footer(self) -> QtWidgets.QHBoxLayout:
        """Create footer section with preparation guidance message."""
        layout = QtWidgets.QHBoxLayout()

        # Preparation guidance message with hyperlink
        guidance_label = QtWidgets.QLabel(
            'Still have questions? Click <a href="#" style="color: #3B82F6; text-decoration: underline;">here</a> to view the setup guide, or click "Begin Setup" below to start.'
        )
        guidance_label.setStyleSheet("""
            color: #9CA3AF; 
            font-size: 14px; 
            font-weight: 500;
            font-style: italic;
        """)
        guidance_label.setOpenExternalLinks(False)  # Handle internally
        guidance_label.linkActivated.connect(self._open_preparation_guide)

        layout.addStretch()
        layout.addWidget(guidance_label)
        layout.addStretch()

        return layout

    def _open_preparation_guide(self, link: str):
        """Handle preparation guide link click."""
        # TODO: Replace with actual preparation guide URL when website is ready
        preparation_url = "https://datawoven.com/resources/setup-guide"

        # For now, show a placeholder dialog
        QtWidgets.QMessageBox.information(
            self, "Setup Guide",
            "The setup preparation guide will be available at:\n"
            f"{preparation_url}\n\n"
            "This guide will include:\n"
            "• Pre-setup checklist and data source inventory\n"
            "• Expected time requirements (45-60 minutes)\n"
            "• Step-by-step preparation instructions\n"
            "• Common setup mistakes to avoid"
        )

        # Uncomment this when the website is ready:
        # QtGui.QDesktopServices.openUrl(QtCore.QUrl(preparation_url))

    def _apply_styles(self):
        """Apply any additional page-level styles if needed."""
        # The individual component styles are already applied in their creation methods
        # This method exists for consistency with the base architecture
        pass

    def validate_page(self) -> Tuple[bool, str]:
        """
        Validate the current page data.
        Welcome page has no validation requirements.

        Returns:
            tuple: (True, "") - Always valid
        """
        return True, ""

    def collect_data(self) -> Dict[str, Any]:
        """
        Collect data from the current page.
        Welcome page has no data to collect.

        Returns:
            dict: Empty dictionary as no data is collected
        """
        return {
            "page_completed": True,
            "timestamp": QtCore.QDateTime.currentDateTime().toString()
        }

    def load_data(self, data: Dict[str, Any]) -> None:
        """
        Load data into the page components.
        Welcome page has no data to load.

        Args:
            data (dict): Configuration data (unused for welcome page)
        """
        pass
