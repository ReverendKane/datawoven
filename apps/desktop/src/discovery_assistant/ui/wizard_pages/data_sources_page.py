from typing import Dict, Any, List, Tuple
from PySide6 import QtWidgets, QtCore, QtGui
from discovery_assistant.wizard_base import WizardPage
from discovery_assistant.ui.widgets.warning_widget import WarningWidget

class DataSourceEntry:
    """Represents a single data source entry"""

    def __init__(self, name: str = "", source_type: str = "database"):
        self.name = name
        self.source_type = source_type
        self.id = id(self)  # Simple unique identifier

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.source_type,
            "id": self.id
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DataSourceEntry':
        entry = cls(data.get("name", ""), data.get("type", "database"))
        entry.id = data.get("id", id(entry))
        return entry


class DataSourcesPage(WizardPage):
    """
    Step 3: Mandatory Data Sources Configuration

    This is the critical validation point for the entire wizard.
    At least one data source is required to proceed.
    """

    # Data source type options
    SOURCE_TYPES = [
        ("database", "Database"),
        ("api", "API/Web Service"),
        ("file_system", "File System/Network Share"),
        ("cloud_service", "Cloud Service"),
        ("custom", "Custom Configuration")
    ]

    def __init__(self, parent):
        super().__init__("Data Sources", parent)
        self.data_sources: List[DataSourceEntry] = []
        self._setup_ui()
        self._connect_signals()

        # Start with validation check
        self._validate_sources()

    def _setup_ui(self):
        """Create the data sources configuration UI"""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)

        # Header section
        header_layout = self._create_header()
        layout.addLayout(header_layout)

        # Main content area
        content_widget = self._create_content_area()
        layout.addWidget(content_widget)

        # Footer with add button
        footer_layout = self._create_footer()
        layout.addLayout(footer_layout)
        layout.addStretch(1)

    def _create_header(self) -> QtWidgets.QVBoxLayout:
        """Create page header with title and description"""
        layout = QtWidgets.QVBoxLayout()

        # Title
        title = QtWidgets.QLabel("Configure Data Sources")
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
            "Define the data sources in your organization that may contain automation opportunities. "
            "These sources will be available for respondents to connect with their pain points and processes.\n\n"
            "You only need to provide source names at this stage—connection details will be handled during final review. "
            "However, it's critical to add as many known sources as possible. Respondents can enter custom sources "
            "if they don't see their intended option listed, but each respondent who uses the same missing source "
            "will create their own entry, resulting in duplicate entries that require manual consolidation.\n\n"
        )
        description.setWordWrap(True)
        description.setObjectName("pageDescription")
        description.setStyleSheet("""
            #pageDescription {
                font-size: 14px;
                color: #D1D5DB;
                line-height: 1.5;
            }
        """)

        layout.addWidget(title)
        layout.addWidget(description)

        warning = WarningWidget(
            "At least one data source is required to proceed.",
            icon_path=":/warning_icon.svg"
        )
        layout.addWidget(warning)

        return layout

    def _create_content_area(self) -> QtWidgets.QWidget:
        """Create the main content area with data source list"""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)

        # Templates section
        templates_group = self._create_templates_section()
        layout.addWidget(templates_group)

        layout.addSpacing(25)

        # Current sources section
        sources_group = self._create_sources_section()
        layout.addWidget(sources_group)

        return widget

    def _create_templates_section(self) -> QtWidgets.QGroupBox:
        """Create quick-add templates section"""
        group = QtWidgets.QGroupBox("Quick Add Templates")
        group.setObjectName("templatesGroup")
        layout = QtWidgets.QVBoxLayout(group)
        self._apply_group_style(group)

        # Template description
        desc = QtWidgets.QLabel("Click to quickly add common business data sources:")
        desc.setStyleSheet("color: #9CA3AF; font-size: 12px; margin-left: 10px; margin-bottom: 10px;")
        layout.addWidget(desc)

        # Template buttons in a grid with explicit sizing
        buttons_widget = QtWidgets.QWidget()
        buttons_layout = QtWidgets.QGridLayout(buttons_widget)
        buttons_layout.setSpacing(8)

        templates = [
            ("Company Email System", "api"),
            ("Customer Database/CRM", "database"),
            ("Document Storage", "file_system"),
            ("Financial/Accounting System", "database"),
            ("Project Management System", "api"),
            ("Team Chat Platform", "api"),
        ]

        for i, (name, source_type) in enumerate(templates):
            btn = QtWidgets.QPushButton(name)
            btn.setObjectName("templateBtn")
            btn.clicked.connect(lambda checked, n=name, t=source_type: self._add_template_source(n, t))
            btn.setCursor(QtCore.Qt.PointingHandCursor)

            # Set explicit minimum size to prevent compression
            btn.setMinimumSize(180, 40)
            btn.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

            row = i // 3
            col = i % 3
            buttons_layout.addWidget(btn, row, col)

        # Set explicit size for the buttons widget to prevent initial compression
        buttons_widget.setMinimumHeight(100)  # Ensure space for 2 rows of buttons

        layout.addWidget(buttons_widget)

        return group

    def _create_sources_section(self) -> QtWidgets.QGroupBox:
        """Create current data sources list section"""
        group = QtWidgets.QGroupBox("Your Data Sources")
        group.setObjectName("sourcesGroup")
        layout = QtWidgets.QVBoxLayout(group)
        layout.setContentsMargins(18, 15, 18, 15)
        self._apply_group_style(group)

        # Sources list widget
        self.sources_list = QtWidgets.QListWidget()
        self.sources_list.setObjectName("sourcesList")
        self.sources_list.setAlternatingRowColors(True)
        self.sources_list.setMinimumHeight(200)

        # IMPORTANT: Start hidden since we have no sources initially
        self.sources_list.setVisible(False)

        # Empty state label
        self.empty_label = QtWidgets.QLabel(
            "No data sources configured yet.\nUse templates above or add manually below.")
        self.empty_label.setObjectName("emptyLabel")
        self.empty_label.setAlignment(QtCore.Qt.AlignCenter)
        self.empty_label.setStyleSheet("""
            #emptyLabel {
                color: #444444;
                font-style: italic;
                padding: 40px;
                border: 2px dashed #444444;
                border-radius: 8px;
                background-color: #101010;
            }
        """)
        self.empty_label.setFixedHeight(350)

        # IMPORTANT: Start visible since we have no sources initially
        self.empty_label.setVisible(True)

        layout.addWidget(self.sources_list)
        layout.addWidget(self.empty_label)

        # Sources list styling - remove rounded corners as you mentioned
        self.sources_list.setStyleSheet("""
            QListWidget#sourcesList {
                background-color: #383838;
                border: 1px solid #404040;
                color: #F9FAFB;
                selection-background-color: #606060;
                alternate-background-color: #444444;
                outline: none;
            }
            QListWidget#sourcesList::item {
                padding: 12px;
                border-bottom: 1px solid #404040;
                background-color: #4D4D4D;
            }
            QListWidget#sourcesList::item:alternate {
                background-color: #676767;
            }
            QListWidget#sourcesList::item:selected {
                background-color: #606060;
                color: #F9FAFB;
            }
            QListWidget#sourcesList::item:hover {
                background-color: #404040;
            }
        """)

        return group

    def _create_footer(self) -> QtWidgets.QHBoxLayout:
        """Create footer with manual add controls"""
        layout = QtWidgets.QHBoxLayout()

        # Manual add section
        add_label = QtWidgets.QLabel("Add Custom:")
        add_label.setStyleSheet("color: #D1D5DB; font-weight: 500;")

        self.name_input = QtWidgets.QLineEdit()
        self.name_input.setPlaceholderText("Data source name (e.g., 'Inventory System')")
        self.name_input.setMinimumWidth(250)
        self.name_input.setFixedHeight(35)

        self.type_combo = QtWidgets.QComboBox()
        for value, display in self.SOURCE_TYPES:
            self.type_combo.addItem(display, value)

        self.add_btn = QtWidgets.QPushButton("Add Source")
        self.add_btn.setObjectName("addBtn")

        self.remove_btn = QtWidgets.QPushButton("Remove Selected")
        self.remove_btn.setObjectName("removeBtn")
        self.remove_btn.setEnabled(False)

        # Layout
        layout.addWidget(add_label)
        layout.addWidget(self.name_input)
        layout.addWidget(self.type_combo)
        layout.addWidget(self.add_btn)
        layout.addStretch()
        layout.addWidget(self.remove_btn)

        # Footer styling
        self.setStyleSheet(self.styleSheet() + """
            QLineEdit {
                background-color: #404040;
                border: 1px solid #606060;
                border-radius: 6px;
                padding-left: 8px;
                color: #F9FAFB;
                font-size: 14px;
                min-width: 200px;
            }
            QLineEdit:focus {
                border-color: #808080;
                background-color: #606060;
            }
            QComboBox {
                padding: 8px 12px;
            }
            QPushButton#addBtn {
                background-color: #606060;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
            }
            QPushButton#addBtn:hover {
                background-color: #808080;
            }
            QPushButton#addBtn:disabled {
                background-color: #404040;
                color: #6B7280;
            }
            QPushButton#removeBtn {
                background-color: #808080;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
            }
            QPushButton#removeBtn:hover {
                background-color: #606060;
            }
            QPushButton#removeBtn:disabled {
                background-color: #404040;
                color: #6B7280;
            }
        """)

        return layout

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
        """Connect UI signals"""
        self.add_btn.clicked.connect(self._add_manual_source)
        self.remove_btn.clicked.connect(self._remove_selected_source)
        self.sources_list.itemSelectionChanged.connect(self._on_selection_changed)
        self.name_input.textChanged.connect(self._validate_add_button)
        self.name_input.returnPressed.connect(self._add_manual_source)

    def _add_template_source(self, name: str, source_type: str):
        """Add a data source from template"""
        # Check for duplicates
        if any(source.name == name for source in self.data_sources):
            QtWidgets.QMessageBox.information(
                self, "Duplicate Source",
                f"'{name}' is already in your data sources list."
            )
            return

        entry = DataSourceEntry(name, source_type)
        self.data_sources.append(entry)
        self._refresh_sources_list()
        self._validate_sources()

    def _add_manual_source(self):
        """Add a manually entered data source"""
        name = self.name_input.text().strip()
        if not name:
            return

        # Check for duplicates
        if any(source.name == name for source in self.data_sources):
            QtWidgets.QMessageBox.information(
                self, "Duplicate Source",
                f"'{name}' is already in your data sources list."
            )
            return

        source_type = self.type_combo.currentData()
        entry = DataSourceEntry(name, source_type)
        self.data_sources.append(entry)

        # Clear input
        self.name_input.clear()

        self._refresh_sources_list()
        self._validate_sources()

    def _remove_selected_source(self):
        """Remove the currently selected data source"""
        current_row = self.sources_list.currentRow()
        if current_row >= 0 and current_row < len(self.data_sources):
            source = self.data_sources[current_row]

            reply = QtWidgets.QMessageBox.question(
                self, "Confirm Removal",
                f"Remove '{source.name}' from data sources?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )

            if reply == QtWidgets.QMessageBox.Yes:
                del self.data_sources[current_row]
                self._refresh_sources_list()
                self._validate_sources()

    def _refresh_sources_list(self):
        """Refresh the sources list widget"""
        self.sources_list.clear()

        for source in self.data_sources:
            type_display = next(display for value, display in self.SOURCE_TYPES if value == source.source_type)
            item_text = f"{source.name}\n{type_display}"

            item = QtWidgets.QListWidgetItem(item_text)
            item.setData(QtCore.Qt.UserRole, source.id)
            self.sources_list.addItem(item)

        # Show/hide empty state
        has_sources = len(self.data_sources) > 0
        self.sources_list.setVisible(has_sources)
        self.empty_label.setVisible(not has_sources)

    def _on_selection_changed(self):
        """Handle list selection changes"""
        has_selection = self.sources_list.currentRow() >= 0
        self.remove_btn.setEnabled(has_selection)

    def _validate_add_button(self):
        """Enable/disable add button based on input"""
        has_name = bool(self.name_input.text().strip())
        self.add_btn.setEnabled(has_name)

    def _validate_sources(self):
        """Validate that at least one data source exists"""
        has_sources = len(self.data_sources) > 0
        self.canProceed.emit(has_sources)

    def showEvent(self, event):
        """Override showEvent to force proper layout when page becomes visible"""
        super().showEvent(event)
        # Force layout refresh when page is shown
        QtCore.QTimer.singleShot(10, self._force_template_layout)

    def _force_template_layout(self):
        """Force template buttons to layout properly"""
        # Find the templates group box and force its layout
        for child in self.findChildren(QtWidgets.QGroupBox):
            if "Quick Add Templates" in child.title():
                child.layout().invalidate()
                child.layout().activate()
                child.updateGeometry()
                break

    # WizardPage interface implementation
    def validate_page(self) -> Tuple[bool, str]:
        """Validate the page data"""
        if len(self.data_sources) == 0:
            return False, "At least one data source is required to proceed.\n\nData sources are essential for connecting pain points to automation opportunities."
        return True, ""

    def collect_data(self) -> Dict[str, Any]:
        """Collect page data for wizard"""
        return {
            "data_sources": [source.to_dict() for source in self.data_sources],
            "total_count": len(self.data_sources)
        }

    def load_data(self, data: Dict[str, Any]) -> None:
        """Load existing data into the page"""
        sources_data = data.get("data_sources", [])
        self.data_sources = [DataSourceEntry.from_dict(source_data) for source_data in sources_data]
        self._refresh_sources_list()
        self._validate_sources()
