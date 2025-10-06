import json
import time
from typing import Dict, Any, Optional
from PySide6 import QtWidgets, QtCore, QtGui
from discovery_assistant.wizard_base import WizardPage
from discovery_assistant.ui.wizard_pages.project_setup_page import ProjectSetupPage
from discovery_assistant.policy_utils import normalize_field_key, normalize_section_key

class ResizableStackedWidget(QtWidgets.QStackedWidget):
    """QStackedWidget that resizes to fit the current page instead of the largest page"""

    def sizeHint(self):
        # Return the size hint of the current widget only
        current = self.currentWidget()
        if current:
            return current.sizeHint()
        return super().sizeHint()

    def minimumSizeHint(self):
        # Return the minimum size hint of the current widget only
        current = self.currentWidget()
        if current:
            return current.minimumSizeHint()
        return super().minimumSizeHint()


class AdminSetupWizard(QtWidgets.QDialog):
    """
    Complete replacement for AdminPreferencesWindow.
    Implements immutable 9-step wizard flow with mandatory data sources.
    """

    # Signal emitted when policy is successfully generated
    policyGenerated = QtCore.Signal()

    def __init__(self, force_password_change: bool = False, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Administrative Setup Wizard")
        self.setObjectName("adminSetupWizard")
        self.setModal(True)

        # Responsive window sizing
        self._setup_responsive_sizing()

        # Core wizard state
        self.current_step = 0
        self.wizard_data = {}
        self.pages = []
        self.force_password_change = force_password_change

        self._setup_ui()
        self._create_pages()
        self._setup_navigation()
        self._setup_styles()
        self._update_page()

        # Handle password change requirement
        if force_password_change:
            self._handle_password_change()

        # Maximize after everything is set up
        QtCore.QTimer.singleShot(0, self._resize_to_screen)

    def _resize_to_screen(self):
        """Resize to fill screen with maximum dimensions, centered if screen is larger."""
        screen = QtWidgets.QApplication.screenAt(self.pos())
        if screen is None:
            screen = QtWidgets.QApplication.primaryScreen()

        available = screen.availableGeometry()

        # Define maximum dimensions you want
        max_width = 1600
        max_height = 1000

        # Calculate actual dimensions (smaller of screen size or max size)
        actual_width = min(available.width(), max_width)
        actual_height = min(available.height() - 100, max_height)  # Still subtract 100 for safety

        # Center the window on screen
        x = available.x() + (available.width() - actual_width) // 2
        y = available.y() + (available.height() - actual_height) // 2

        self.setGeometry(x, y, actual_width, actual_height)

    def _setup_responsive_sizing(self):
        """Set up responsive window sizing with restore behavior."""
        screen = QtWidgets.QApplication.primaryScreen().geometry()
        screen_width = screen.width()
        screen_height = screen.height()

        # Calculate appropriate sizes based on screen resolution
        if screen_height >= 1440:  # 4K or large monitors
            self._normal_size = QtCore.QSize(1000, 800)
            self.setMinimumSize(900, 700)
        elif screen_height >= 1080:  # 1080p displays
            self._normal_size = QtCore.QSize(900, 650)
            self.setMinimumSize(800, 600)
        else:  # Smaller displays
            self._normal_size = QtCore.QSize(800, 580)
            self.setMinimumSize(750, 550)

        # Center position for when restored
        self._normal_position = QtCore.QPoint(
            (screen_width - self._normal_size.width()) // 2,
            (screen_height - self._normal_size.height()) // 2
        )

        # Set initial size and position (will maximize after show)
        self.resize(self._normal_size)
        self.move(self._normal_position)


    def changeEvent(self, event):
        """Handle window state changes to apply responsive sizing on restore."""
        if event.type() == QtCore.QEvent.WindowStateChange:
            if not self.isMaximized() and not self.isMinimized():
                # User restored from maximized - apply responsive size
                self.resize(self._normal_size)
                self.move(self._normal_position)
        super().changeEvent(event)

    def _setup_ui(self):
        """Create the main wizard UI structure with scrolling support."""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header with progress indicator (fixed)
        self.header = self._create_header()
        layout.addWidget(self.header)

        # Scrollable main content area
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setObjectName("wizardScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)

        # Content stack inside scroll area
        self.content_stack = ResizableStackedWidget()
        self.content_stack.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)

        self.scroll_area.setWidget(self.content_stack)

        layout.addWidget(self.scroll_area, 1)

        # Navigation footer (fixed)
        self.footer = self._create_footer()
        layout.addWidget(self.footer)

    def _create_header(self) -> QtWidgets.QWidget:
        """Create wizard header with progress indicators"""
        header = QtWidgets.QWidget()
        header.setObjectName("wizardHeader")
        header.setFixedHeight(80)

        layout = QtWidgets.QHBoxLayout(header)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(10)  # Match main window header spacing

        # Logo - matching main window layout
        self.logo = QtWidgets.QLabel()
        self.logo.setObjectName("wizardLogo")
        self.logo.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)

        # Load the white banner logo SVG
        pm = QtGui.QPixmap(":/datawoven_bannerLogo_white.svg")
        if not pm.isNull():
            self.logo.setPixmap(pm)
            self.logo.setScaledContents(False)
            self.logo.setFixedSize(70, 43)  # Use the provided dimensions

        layout.addWidget(self.logo, 0, QtCore.Qt.AlignVCenter)

        # Title with matching font from main window
        self.title_label = QtWidgets.QLabel("ADMINISTRATIVE SETUP")
        self.title_label.setObjectName("wizardTitle")
        self.title_label.setFrameShape(QtWidgets.QFrame.NoFrame)

        # Load the same Montserrat SemiBold font used in main window
        family_name = None
        import discovery_assistant.constants as constants
        fid = QtGui.QFontDatabase.addApplicationFont(str(constants.FONT_MONTSERRAT_SEMIBOLD))
        if fid != -1:
            fams = QtGui.QFontDatabase.applicationFontFamilies(fid)
            if fams:
                family_name = fams[0]

        # Apply the same font styling as main window
        title_font = QtGui.QFont(family_name or "Segoe UI", 12)
        title_font.setWeight(QtGui.QFont.DemiBold)
        title_font.setHintingPreference(QtGui.QFont.PreferFullHinting)
        self.title_label.setFont(title_font)

        layout.addWidget(self.title_label, 0, QtCore.Qt.AlignVCenter)

        # Progress indicator (step counter)
        self.progress_label = QtWidgets.QLabel("Step 1 of 7")
        self.progress_label.setObjectName("wizardProgress")

        layout.addStretch()
        layout.addWidget(self.progress_label)

        return header

    def _create_footer(self) -> QtWidgets.QWidget:
        """Create navigation buttons footer"""
        footer = QtWidgets.QWidget()
        footer.setObjectName("wizardFooter")
        footer.setFixedHeight(70)

        layout = QtWidgets.QHBoxLayout(footer)
        layout.setContentsMargins(30, 15, 30, 15)

        # Navigation buttons
        self.btn_back = QtWidgets.QPushButton("← Back")
        self.btn_next = QtWidgets.QPushButton("Next →")
        self.btn_cancel = QtWidgets.QPushButton("Cancel")

        self.btn_back.setEnabled(False)  # Disabled on first page
        self.btn_next.setDefault(True)

        # Button styling
        for btn in [self.btn_back, self.btn_next, self.btn_cancel]:
            btn.setMinimumSize(100, 35)
            btn.setCursor(QtCore.Qt.PointingHandCursor)

        layout.addWidget(self.btn_cancel)
        layout.addStretch()
        layout.addWidget(self.btn_back)
        layout.addWidget(self.btn_next)

        return footer

    def _create_pages(self):
        """Create all wizard pages"""
        global PrivacyDataPage
        try:
            from discovery_assistant.ui.wizard_pages.data_sources_page import DataSourcesPage
            from discovery_assistant.ui.wizard_pages.welcome_page import WelcomePage
            from discovery_assistant.ui.wizard_pages.review_generate_page import ReviewGeneratePage
            from discovery_assistant.ui.wizard_pages.consolidated_field_section_page import ConsolidatedFieldSectionPage
            from discovery_assistant.ui.wizard_pages.admin_instructions_page import AdminInstructionsPage
            from discovery_assistant.ui.wizard_pages.privacy_data_page import PrivacyDataPage
        except ImportError as e:
            print(f"Import error: {e}")
            # Fallback to placeholder for development
            DataSourcesPage = PlaceholderPage
            WelcomePage = PlaceholderPage
            ReviewGeneratePage = PlaceholderPage
            ConsolidatedFieldSectionPage = PlaceholderPage
            AdminInstructionsPage = PlaceholderPage

        self.pages = [
            WelcomePage(self),  # Step 1
            ProjectSetupPage(self),  # Step 2
            DataSourcesPage(self),  # Step 3
            ConsolidatedFieldSectionPage(self),  # Step 4
            AdminInstructionsPage(self),  # Step 5
            PrivacyDataPage(self),  # Step 6
            ReviewGeneratePage(self),  # Step 7
        ]

        # Add pages to stack
        for page in self.pages:
            self.content_stack.addWidget(page)
            # Connect page validation to navigation
            page.canProceed.connect(self._update_navigation)

    def _setup_navigation(self):
        """Connect navigation button signals"""
        self.btn_next.clicked.connect(self._next_page)
        self.btn_back.clicked.connect(self._prev_page)
        self.btn_cancel.clicked.connect(self._cancel_wizard)

    def _setup_styles(self):
        """Apply wizard-specific styles including scroll area styling."""
        self.setStyleSheet("""
            #adminSetupWizard {
                background-color: #1a1a1a;
                color: #F9FAFB;
            }

            #wizardHeader {
                background-color: #000000;
                border-bottom: 2px solid #404040;
            }

            #wizardTitle {
                font-size: 18px;
                font-weight: 600;
                color: #F9FAFB;
            }

            #wizardProgress {
                font-size: 12px;
                font-weight: bold;
                color: #F9FAFB;
            }

            #wizardScrollArea {
                background-color: #1a1a1a;
                border: none;
            }

            #wizardScrollArea QScrollBar:vertical {
                background-color: #0C0C0C;
                width: 12px;
                border-radius: 6px;
            }

            #wizardScrollArea QScrollBar::handle:vertical {
                background-color: #606060;
                border-radius: 6px;
                min-height: 20px;
            }

            #wizardScrollArea QScrollBar::handle:vertical:hover {
                background-color: #808080;
            }

            #wizardScrollArea QScrollBar::add-line:vertical,
            #wizardScrollArea QScrollBar::sub-line:vertical {
                height: 0px;
            }

            #wizardFooter {
                background-color: #000000;
                border-top: 1px solid #404040;
            }

            QPushButton {
                background-color: #606060;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 500;
            }

            QPushButton:hover {
                background-color: #808080;
            }

            QPushButton:pressed {
                background-color: #404040;
            }

            QPushButton:disabled {
                background-color: #404040;
                color: #6B7280;
            }

            QPushButton#cancelBtn {
                background-color: #404040;
                color: #F9FAFB;
            }

            QPushButton#cancelBtn:hover {
                background-color: #606060;
            }
        """)

        self.btn_cancel.setObjectName("cancelBtn")

    def _handle_password_change(self):
        """Handle mandatory password change requirement"""
        from discovery_assistant.admin_prefs import SetPasswordDialog

        dlg = SetPasswordDialog(self)
        if not dlg.exec() or not dlg.success():
            QtWidgets.QMessageBox.information(
                self, "Password Required",
                "Admin password must be changed before continuing setup."
            )

    # Navigation methods
    def _next_page(self):
        """Navigate to next page"""
        current_page = self.pages[self.current_step]

        # Validate current page
        is_valid, error_msg = current_page.validate_page()
        if not is_valid:
            QtWidgets.QMessageBox.warning(self, "Validation Error", error_msg)
            return

        # Collect and store page data
        page_data = current_page.collect_data()
        self.wizard_data[f"step_{self.current_step + 1}"] = page_data

        # Move to next page
        if self.current_step < len(self.pages) - 1:
            self.current_step += 1
            self._update_page()
        else:
            # Final step - generate policy
            self._generate_policy()

    def _prev_page(self):
        """Navigate to previous page"""
        if self.current_step > 0:
            self.current_step -= 1
            self._update_page()

    def _update_page(self):
        """Update UI for current page"""
        # Update content
        current_page = self.pages[self.current_step]
        self.content_stack.setCurrentIndex(self.current_step)

        # Reset scroll position to top
        self.scroll_area.verticalScrollBar().setValue(0)

        # Load existing data if available
        step_key = f"step_{self.current_step + 1}"
        if step_key in self.wizard_data:
            current_page.load_data(self.wizard_data[step_key])

        # Update header
        self.progress_label.setText(f"Step {self.current_step + 1} of {len(self.pages)}")

        # Update navigation buttons
        if self.current_step == 0:
            self.btn_back.setVisible(False)
        else:
            self.btn_back.setVisible(True)
            self.btn_back.setEnabled(True)

        # Update next button text
        if self.current_step == 0:
            self.btn_next.setText("Begin Setup →")
        elif self.current_step == len(self.pages) - 1:
            self.btn_next.setText("Generate Policy")
        else:
            self.btn_next.setText("Next →")

        # FORCE SIZE RECALCULATION - This is the critical part

        current_page.updateGeometry()
        self.content_stack.updateGeometry()
        QtCore.QTimer.singleShot(0, lambda: self.content_stack.adjustSize())

        # Validate current page
        is_valid, _ = current_page.validate_page()
        self.btn_next.setEnabled(is_valid)

    def _force_layout_update(self):
        """Force a complete layout update to fix sizing issues"""
        current_page = self.pages[self.current_step]

        # Force layout calculations on the current page
        current_page.layout().invalidate()
        current_page.layout().activate()

        # Force the wizard itself to recalculate its size
        current_size = self.size()
        self.resize(current_size.width() + 1, current_size.height() + 1)

        # Process events to let Qt handle the resize
        QtWidgets.QApplication.processEvents()

        # Return to original size
        self.resize(current_size)

        # Process events again
        QtWidgets.QApplication.processEvents()

        # Final updates
        current_page.updateGeometry()
        self.updateGeometry()

    def _update_navigation(self, can_proceed: bool):
        """Update navigation based on page validation"""
        self.btn_next.setEnabled(can_proceed)

    def _cancel_wizard(self):
        """Handle wizard cancellation"""
        reply = QtWidgets.QMessageBox.question(
            self, "Cancel Setup",
            "Are you sure you want to cancel the administrative setup?\n\n"
            "No policy will be generated and the application cannot be used by respondents.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )

        if reply == QtWidgets.QMessageBox.Yes:
            self.reject()

    def _generate_policy(self):
        """Generate final policy from collected wizard data"""
        try:
            policy = self._build_policy_from_wizard_data()
            self._save_policy(policy)

            # Show success dialog
            self._show_completion_dialog()

            # Emit signal for main.py integration
            self.policyGenerated.emit()
            self.accept()

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "Policy Generation Failed",
                f"Failed to generate policy:\n{str(e)}"
            )

    def _build_policy_from_wizard_data(self) -> Dict[str, Any]:
        """Convert wizard data into production-grade policy structure with nested field groups"""
        from discovery_assistant.ui.wizard_pages.consolidated_field_section_page import ConsolidatedFieldSectionPage

        # Get data from wizard steps
        project_data = self.wizard_data.get("step_2", {})
        sources_data = self.wizard_data.get("step_3", {})
        consolidated_data = self.wizard_data.get("step_4", {})
        instructions_data = self.wizard_data.get("step_6", {})  # Changed from step_5 to step_6
        privacy_data = self.wizard_data.get("step_7", {})  # Changed from step_6 to step_7

        policy = {
            "meta": {
                "project_name": project_data.get("organization_name", "Discovery Assistant Policy"),
                "version": 1,
                "generated_by_wizard": True,
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "immutable": True,
                "multi_user_mode": instructions_data.get("multi_user_mode", True)  # NEW
            },
            "data": {
                # Project setup information
                "organization_name": {"value": project_data.get("organization_name", "")},
                "administrator_name": {"value": project_data.get("administrator_name", "")},
                "administrator_email": {"value": project_data.get("administrator_email", "")},
                "session_description": {"value": project_data.get("session_description", "")},
                "organizational_context": {"value": project_data.get("organizational_context", "")},

                # Timeline if enabled
                "has_timeline": {"value": project_data.get("has_timeline", False)},
                "timeline_date": {"value": project_data.get("timeline_date", "")},

                # Data sources
                "data_sources": {
                    "admin_defined": sources_data.get("data_sources", [])
                },

                # Section configuration with nested field groups
                "sections": self._build_sections_with_fields(consolidated_data),

                # Admin instructions
                "administrative_instructions": {
                    "enabled": len(instructions_data.get("messages", [])) > 0,
                    "instruction_tone": instructions_data.get("instruction_tone", "formal"),  # NEW
                    "messages": instructions_data.get("messages", [])
                },

                # AI Configuration (from step 7)
                "ai_configuration": privacy_data.get("ai_configuration", {
                    "enabled": True,
                    "initial_credits": 50.0,
                    "additional_credits_purchased": 0,
                    "advisor_access": "all",
                    "depletion_policy": "pause"
                }),

                # Service Engagement (from step 7)
                "service_engagement": privacy_data.get("service_engagement", {
                    "interested": "no",
                    "contact_email": "",
                    "contact_phone": "",
                    "company_size": ""
                }),

                # Privacy settings (from step 7)
                "privacy": {
                    "allow_screenshots": {"value": True},
                    "anonymize_respondent": {
                        "value": privacy_data.get("privacy", {}).get("anonymize_respondents", False)
                    },
                    "excluded_terms": privacy_data.get("privacy", {}).get("excluded_terms", [])
                },

                # Export settings
                "export": {
                    "format": {"value": "pdf"},
                    "include_attachments": {"value": True}
                },

                # AI Advisor compatibility flag
                "ai_advisor_enabled": {"value": True}
            }
        }

        return policy

    def _build_sections_with_fields(self, consolidated_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build production-grade section configuration with nested field groups.
        Structure: sections -> field_groups -> fields

        This preserves the logical grouping from the UI while maintaining clean key names.
        """
        from discovery_assistant.ui.wizard_pages.consolidated_field_section_page import ConsolidatedFieldSectionPage

        # Get the section definitions from the consolidated page
        temp_page = ConsolidatedFieldSectionPage()
        section_definitions = {**temp_page.sections["core_sections"], **temp_page.sections["optional_sections"]}

        sections_data = consolidated_data.get("sections", {})
        field_states = consolidated_data.get("field_groups", {})

        sections_config = {}

        for section_name, section_enabled_data in sections_data.items():
            # Convert display name to policy key using shared utility
            policy_key = normalize_section_key(section_name)

            # Get the section definition to access field group structure
            section_def = section_definitions.get(section_name, {})

            sections_config[policy_key] = {
                "enabled": section_enabled_data.get("enabled", False),
                "required": section_enabled_data.get("required", False),
                "configurable": not section_enabled_data.get("required", False),
                "field_groups": {}
            }

            # Process field groups for this section
            field_groups = section_def.get("fields", [])
            for field_group_def in field_groups:
                group_name = field_group_def.get("group", "")
                group_required = field_group_def.get("required", False)
                field_names = field_group_def.get("names", [])

                # Initialize field group in policy
                sections_config[policy_key]["field_groups"][group_name] = {
                    "required": group_required,
                    "fields": {}
                }

                # Process each field in the group
                for field_display_name in field_names:
                    # Normalize field display name using shared utility
                    field_key = normalize_field_key(field_display_name)

                    # Build the full field state key as it appears in field_states
                    full_field_key = f"{policy_key}_{field_key}"

                    # Get the enabled state from collected data
                    field_enabled = field_states.get(full_field_key, True)

                    # Store in policy structure
                    sections_config[policy_key]["field_groups"][group_name]["fields"][field_key] = {
                        "enabled": field_enabled,
                        "required": group_required,
                        "display_name": field_display_name
                    }

        return sections_config

    def _normalize_field_key(self, field_name: str) -> str:
        """
        Convert field display names to consistent policy keys.

        Examples:
            "Full Name" -> "full_name"
            "Role / Title" -> "role_title"
            "Screenshots/Attachments" -> "screenshots_attachments"
        """
        # Replace common separators with underscores
        normalized = field_name.lower()
        normalized = normalized.replace(" / ", "_")
        normalized = normalized.replace("/", "_")
        normalized = normalized.replace(" ", "_")

        # Remove any duplicate underscores that might have been created
        while "__" in normalized:
            normalized = normalized.replace("__", "_")

        # Remove leading/trailing underscores
        normalized = normalized.strip("_")

        return normalized

    def _save_policy(self, policy: Dict[str, Any]):
        """Save policy to the canonical location"""
        from discovery_assistant.storage import get_policy_path

        policy_path = get_policy_path()
        policy_path.parent.mkdir(parents=True, exist_ok=True)

        with open(policy_path, 'w', encoding='utf-8') as f:
            json.dump(policy, f, indent=2)

        # Make read-only to prevent accidental modification
        try:
            policy_path.chmod(0o444)
        except Exception:
            pass  # Ignore permission errors

    def _show_completion_dialog(self):
        """Show setup completion dialog"""
        msg = QtWidgets.QMessageBox(self)
        msg.setWindowTitle("Policy Generated Successfully")
        msg.setText(
            "Policy generated successfully!\n\n"
            "Share the generated policy file with respondents. They can drag and drop "
            "it onto their Discovery Assistant application to load your configured settings.\n\n"
            "Settings are now immutable and cannot be changed."
        )
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.exec()


# Placeholder for page imports - we'll create wizard_pages.py next


class FieldCustomizationPage(WizardPage):
    def __init__(self, parent):
        super().__init__("Field Customization", parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Field customization placeholder"))


class AdminInstructionsPage(WizardPage):
    def __init__(self, parent):
        super().__init__("Admin Instructions", parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Admin instructions placeholder"))


class PrivacyDataPage(WizardPage):
    def __init__(self, parent):
        super().__init__("Privacy & Data", parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Privacy & data placeholder"))


class ExportCompletionPage(WizardPage):
    def __init__(self, parent):
        super().__init__("Export & Completion", parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Export & completion placeholder"))


class PlaceholderPage(WizardPage):
    def __init__(self, parent):
        super().__init__("Placeholder", parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Page placeholder"))
