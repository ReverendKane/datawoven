"""
Data Sources Configuration Page - Step 3 of Admin Setup Wizard
Allows admins to define organizational data sources with categories.
"""

from typing import Dict, Any, Tuple, List
from PySide6 import QtWidgets, QtCore, QtGui
from discovery_assistant.wizard_base import WizardPage
from discovery_assistant.ui.modals.data_source_modal import DataSourceModal, DataSource
from discovery_assistant.ui.widgets.warning_widget import WarningWidget

class DataSourcesPage(WizardPage):
    """Step 3: Configure organizational data sources"""

    # Template definitions (category, generic_name)
    TEMPLATES = [
        ("email", "Company Email"),
        ("crm", "Customer Database"),
        ("storage", "Document Storage"),
        ("financial", "Financial/Accounting System"),
        ("project_mgmt", "Project Management System"),
        ("communication", "Team Chat Platform")
    ]

    def __init__(self, parent=None):
        super().__init__("Configure Data Sources", parent)
        self.data_sources: List[DataSource] = []
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

        # Validation warning
        self.warning_widget = WarningWidget(
            "At least one data source is required to proceed.",
            icon_path=":/warning_icon.svg"
        )
        layout.addWidget(self.warning_widget)

        # Main content
        content_widget = self._create_content_area()
        layout.addWidget(content_widget, 1)

    def _create_header(self) -> QtWidgets.QVBoxLayout:
        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(10)

        title = QtWidgets.QLabel("Configure Data Sources")
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
            "<b>Define the data sources your team uses daily.</b> As respondents complete the form, "
            "they'll connect each work task or challenge to the company systems they use—such as email, "
            "your CRM, spreadsheets, or internal databases. By listing these sources now, you ensure "
            "everyone selects from the same master list, preventing duplicate entries that require cleanup later.<br><br>"
            "You only need to provide source names at this stage—connection details will be handled during "
            "final review. However, it's critical to add as many known sources as possible. Respondents can "
            "add custom sources if needed, but each person who enters the same missing source will create "
            "their own entry, requiring manual consolidation."
        )
        description.setTextFormat(QtCore.Qt.RichText)
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
        widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)

        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        # Template buttons
        templates_group = self._create_templates_section()
        layout.addWidget(templates_group)

        # Data sources list
        list_group = self._create_sources_list()
        layout.addWidget(list_group)

        layout.addStretch(1)

        return widget

    def _create_templates_section(self) -> QtWidgets.QGroupBox:
        """Create quick-add template buttons section"""
        group = QtWidgets.QGroupBox("Quick Add Templates")
        layout = QtWidgets.QVBoxLayout(group)
        layout.setContentsMargins(18, 15, 18, 15)
        layout.setSpacing(12)
        self._apply_group_style(group)

        group.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        help_text = QtWidgets.QLabel(
            "Click to quickly add common business data sources:"
        )
        help_text.setStyleSheet("color: #9CA3AF; font-size: 13px;")
        layout.addWidget(help_text)

        # Create grid of template buttons (3 columns)
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(10)

        for idx, (category, display_name) in enumerate(self.TEMPLATES):
            btn = QtWidgets.QPushButton(display_name)
            btn.setObjectName("templateBtn")
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            btn.setFixedHeight(40)
            btn.clicked.connect(lambda checked, cat=category, name=display_name:
                                self._open_template_modal(cat, name))

            row = idx // 3
            col = idx % 3
            grid.addWidget(btn, row, col)

        layout.addLayout(grid)

        # Add Custom button (full width, below templates)
        self.add_custom_btn = QtWidgets.QPushButton("+ Add Custom Source")
        self.add_custom_btn.setObjectName("addCustomBtn")
        self.add_custom_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.add_custom_btn.setFixedHeight(40)
        self.add_custom_btn.clicked.connect(self._open_add_modal)
        layout.addWidget(self.add_custom_btn)

        return group

    def _create_sources_list(self) -> QtWidgets.QGroupBox:
        """Create data sources table"""
        group = QtWidgets.QGroupBox("Your Data Sources")
        layout = QtWidgets.QVBoxLayout(group)
        layout.setContentsMargins(18, 15, 18, 15)
        layout.setSpacing(0)
        self._apply_group_style(group)

        group.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        # Table
        self.sources_table = QtWidgets.QTableWidget()
        self.sources_table.setColumnCount(4)
        self.sources_table.setHorizontalHeaderLabels(["Type", "Specific Name", "Description", "Actions"])
        self.sources_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        # Row selection
        self.sources_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.sources_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.sources_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.sources_table.setFocusPolicy(QtCore.Qt.NoFocus)

        self.sources_table.setAlternatingRowColors(True)
        self.sources_table.setWordWrap(False)

        hh = self.sources_table.horizontalHeader()
        hh.setStretchLastSection(False)
        hh.setDefaultAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        hh.setMinimumSectionSize(60)

        # Column sizing
        hh.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)  # Type (fixed)
        hh.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)  # Name (flex)
        hh.setSectionResizeMode(2, QtWidgets.QHeaderView.Fixed)  # Description (fixed)
        hh.setSectionResizeMode(3, QtWidgets.QHeaderView.Fixed)  # Actions (fixed)

        vh = self.sources_table.verticalHeader()
        vh.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        vh.setDefaultSectionSize(34)
        vh.setMinimumSectionSize(30)

        self.sources_table.setStyleSheet("""
            QTableWidget {
                background-color: #383838;
                border: 1px solid #404040;
                color: #F9FAFB;
                alternate-background-color: #444444;
                gridline-color: #404040;
            }
            QTableWidget::item {
                padding: 6px 10px;
                border-bottom: 1px solid #404040;
            }
            QTableWidget::item:selected { background-color: #606060; }
            QTableView::item:focus { outline: none; }

            QHeaderView::section {
                background-color: #2D2D2D;
                color: #F9FAFB;
                padding: 8px 10px;
                min-height: 30px;
                border: none;
                border-bottom: 1px solid #404040;
                font-weight: 600;
            }
        """)

        self.sources_table.setFixedHeight(350)
        self.sources_table.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        # Empty state
        self.empty_label = QtWidgets.QLabel(
            "No data sources configured yet.\n"
            "Use templates above or add manually below."
        )
        self.empty_label.setAlignment(QtCore.Qt.AlignCenter)
        self.empty_label.setFixedHeight(350)
        self.empty_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.empty_label.setStyleSheet("""
            color: #6B7280;
            font-style: italic;
            padding: 40px;
            border: 2px dashed #444444;
            border-radius: 8px;
            background-color: #101010;
        """)

        layout.addWidget(self.sources_table)
        layout.addWidget(self.empty_label)

        self.sources_table.setVisible(False)
        self.empty_label.setVisible(True)

        # Set fixed column widths
        hh.resizeSection(0, self._compute_type_col_width())
        hh.resizeSection(2, self._compute_description_col_width())
        hh.resizeSection(3, self._compute_actions_col_width())

        return group

    def _apply_group_style(self, group: QtWidgets.QGroupBox):
        """Apply consistent group box styling"""
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
        """Connect signals - intentionally empty as buttons connect in creation"""
        pass

    def _open_template_modal(self, category: str, generic_name: str):
        """Open modal with template preset"""
        modal = DataSourceModal(self, preset_category=category, preset_name=generic_name)
        if modal.exec() == QtWidgets.QDialog.Accepted:
            source = modal.get_source()
            source.id = len(self.data_sources) + 1
            self.data_sources.append(source)
            self._refresh_sources_table()
            self._validate_form()

    def _open_add_modal(self):
        """Open modal for custom source"""
        modal = DataSourceModal(self)
        if modal.exec() == QtWidgets.QDialog.Accepted:
            source = modal.get_source()
            source.id = len(self.data_sources) + 1
            self.data_sources.append(source)
            self._refresh_sources_table()
            self._validate_form()

    def _open_edit_modal(self, row: int):
        """Open modal to edit existing source"""
        if row < 0 or row >= len(self.data_sources):
            return

        source = self.data_sources[row]
        modal = DataSourceModal(self, source=source)
        if modal.exec() == QtWidgets.QDialog.Accepted:
            # Source was modified in place
            self._refresh_sources_table()

    def _refresh_sources_table(self):
        """Refresh the sources table display"""
        tbl = self.sources_table
        tbl.setRowCount(0)

        if not self.data_sources:
            tbl.setVisible(False)
            self.empty_label.setVisible(True)
            return

        tbl.setVisible(True)
        self.empty_label.setVisible(False)

        # Sort sources by category for grouped display
        sorted_sources = sorted(self.data_sources, key=lambda s: s.category)

        PADDING_H = 10
        GAP = 8

        for row, source in enumerate(sorted_sources):
            tbl.insertRow(row)

            category_key = source.category
            name = source.name
            description = source.description

            # Get display name and color for category
            category_display = next((disp for key, disp in DataSource.CATEGORIES if key == category_key), category_key)
            category_color = DataSource.CATEGORY_COLORS.get(category_key, "#777777")

            # --- Type cell (color bar + label) ---
            type_widget = QtWidgets.QWidget()
            type_layout = QtWidgets.QHBoxLayout(type_widget)
            type_layout.setContentsMargins(PADDING_H, 0, PADDING_H, 0)
            type_layout.setSpacing(GAP)

            color_indicator = QtWidgets.QLabel()
            color_indicator.setFixedSize(4, 20)
            color_indicator.setStyleSheet(f"background:{category_color}; border-radius:1px;")

            type_label = QtWidgets.QLabel(category_display)
            type_label.setStyleSheet("color: #F9FAFB;")

            type_layout.addWidget(color_indicator, 0, QtCore.Qt.AlignVCenter)
            type_layout.addWidget(type_label, 0, QtCore.Qt.AlignVCenter)
            type_layout.addStretch()

            type_widget.setMinimumHeight(max(type_label.sizeHint().height(), 20) + 6)
            type_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
            tbl.setCellWidget(row, 0, type_widget)

            # --- Specific Name ---
            name_item = QtWidgets.QTableWidgetItem(name)
            name_item.setFlags(name_item.flags() & ~QtCore.Qt.ItemIsEditable)
            tbl.setItem(row, 1, name_item)

            # --- Description (truncated) ---
            truncated_desc = self._truncate_description(description)
            desc_item = QtWidgets.QTableWidgetItem(truncated_desc)
            desc_item.setFlags(desc_item.flags() & ~QtCore.Qt.ItemIsEditable)
            desc_item.setToolTip(description)  # Full text on hover
            tbl.setItem(row, 2, desc_item)

            # --- Actions (Edit + Delete) ---
            actions_widget = QtWidgets.QWidget()
            h = QtWidgets.QHBoxLayout(actions_widget)
            h.setContentsMargins(10, 4, 10, 4)
            h.setSpacing(6)
            h.setAlignment(QtCore.Qt.AlignCenter)

            edit_btn = QtWidgets.QPushButton("Edit")
            edit_btn.setObjectName("editBtn")
            edit_btn.setCursor(QtCore.Qt.PointingHandCursor)
            edit_btn.clicked.connect(lambda _, r=row: self._open_edit_modal(r))

            delete_btn = QtWidgets.QPushButton("Delete")
            delete_btn.setObjectName("removeBtn")
            delete_btn.setCursor(QtCore.Qt.PointingHandCursor)
            delete_btn.clicked.connect(lambda _, r=row: self._delete_source(r))

            h.addWidget(edit_btn)
            h.addWidget(delete_btn)

            actions_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
            tbl.setCellWidget(row, 3, actions_widget)

        # Resize rows to fit content
        tbl.resizeRowsToContents()

        # Reassert fixed widths
        hh = tbl.horizontalHeader()
        hh.resizeSection(0, self._compute_type_col_width())
        hh.resizeSection(2, self._compute_description_col_width())
        hh.resizeSection(3, self._compute_actions_col_width())

        # Adjust table height to content
        header_h = hh.height()
        rows_h = sum(tbl.rowHeight(r) for r in range(tbl.rowCount()))
        hbar_h = tbl.horizontalScrollBar().height() if tbl.horizontalScrollBar().isVisible() else 0
        frame = 2 * tbl.frameWidth()
        required = header_h + rows_h + hbar_h + frame
        tbl.setFixedHeight(max(350, required))

    def _truncate_description(self, text: str, max_chars: int = 45) -> str:
        """Truncate description with ellipsis"""
        if not text:
            return ""
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "..."

    def _compute_type_col_width(self) -> int:
        """Fixed width for Type column"""
        PADDING_H = 10
        GAP = 8
        BAR_W = 4
        EXTRA = 6
        fm = QtGui.QFontMetrics(self.sources_table.font())
        widest_label = "Project Management System"
        text_w = fm.horizontalAdvance(widest_label)
        return PADDING_H + BAR_W + GAP + text_w + PADDING_H + EXTRA

    def _compute_description_col_width(self) -> int:
        """Fixed width for Description column (45 chars + ellipsis)"""
        fm = QtGui.QFontMetrics(self.sources_table.font())
        sample = "X" * 45 + "..."
        text_w = fm.horizontalAdvance(sample)
        PADDING = 20
        return text_w + PADDING

    def _compute_actions_col_width(self) -> int:
        """Fixed width for Actions column (Edit + Delete buttons)"""
        # Create temp buttons to measure
        edit_btn = QtWidgets.QPushButton("Edit")
        delete_btn = QtWidgets.QPushButton("Delete")
        edit_btn.setFont(self.sources_table.font())
        delete_btn.setFont(self.sources_table.font())

        edit_w = edit_btn.sizeHint().width()
        delete_w = delete_btn.sizeHint().width()

        GAP = 6  # spacing between buttons
        LEFT_RIGHT = 10  # margins
        EXTRA = 6

        return edit_w + delete_w + GAP + (LEFT_RIGHT * 2) + EXTRA

    def _delete_source(self, row: int):
        """Delete a data source with confirmation"""
        if row < 0 or row >= len(self.data_sources):
            return

        source_name = self.data_sources[row].name

        confirm = QtWidgets.QMessageBox.question(
            self,
            "Delete Data Source?",
            f"Are you sure you want to delete '{source_name}'?\nThis action cannot be undone.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )

        if confirm != QtWidgets.QMessageBox.Yes:
            return

        # Store scroll position and selection
        tbl = self.sources_table
        vsb = tbl.verticalScrollBar()
        scroll_pos = vsb.value() if vsb else 0
        next_select = min(row, tbl.rowCount() - 2)

        # Delete source
        del self.data_sources[row]

        # Refresh table
        self._refresh_sources_table()

        # Restore scroll and selection
        if vsb:
            vsb.setValue(scroll_pos)
        if 0 <= next_select < tbl.rowCount():
            tbl.setCurrentCell(next_select, 0)

        self._validate_form()

    def _validate_form(self):
        """Validate that at least one source exists"""
        is_valid = len(self.data_sources) > 0
        self.warning_widget.setVisible(not is_valid)
        self.canProceed.emit(is_valid)

    def showEvent(self, event):
        """Apply input styles when page becomes visible"""
        super().showEvent(event)
        self._apply_input_styles()

    def _apply_input_styles(self):
        """Apply consistent button styling"""
        button_style = """
            QPushButton#templateBtn {
                background-color: #606060;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
                font-size: 14px;
            }
            QPushButton#templateBtn:hover {
                background-color: #808080;
            }
            QPushButton#addCustomBtn {
                background-color: #404040;
                color: #F9FAFB;
                border: 2px dashed #606060;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
                font-size: 14px;
            }
            QPushButton#addCustomBtn:hover {
                background-color: #606060;
                border-style: solid;
            }
            QPushButton#editBtn {
                background-color: #606060;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 500;
            }
            QPushButton#editBtn:hover {
                background-color: #808080;
            }
            QPushButton#removeBtn {
                background-color: #808080;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 500;
            }
            QPushButton#removeBtn:hover {
                background-color: #606060;
            }
        """
        self.setStyleSheet(self.styleSheet() + button_style)

    # WizardPage interface implementation
    def validate_page(self) -> Tuple[bool, str]:
        if len(self.data_sources) == 0:
            return False, "At least one data source is required to proceed."
        return True, ""

    def collect_data(self) -> Dict[str, Any]:
        return {
            "data_sources": [source.to_dict() for source in self.data_sources],
            "total_count": len(self.data_sources)
        }

    def load_data(self, data: Dict[str, Any]) -> None:
        sources_data = data.get("data_sources", [])
        self.data_sources = [DataSource.from_dict(s) for s in sources_data]
        self._refresh_sources_table()
        self._validate_form()
