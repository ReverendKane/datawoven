"""
Administrative Instructions Page - Step 5 of Admin Setup Wizard
Allows admins to create structured messages for respondents.
"""

from typing import Dict, Any, Tuple, List
from PySide6 import QtWidgets, QtCore, QtGui
from discovery_assistant.wizard_base import WizardPage


class AdminMessage:
    """Represents a single administrative message"""

    MESSAGE_TYPES = [
        ("security_warning", "Security Warning"),
        ("requirement", "Process Requirement"),
        ("guideline", "Data Guideline"),
        ("steps", "Step-by-Step Instructions"),
        ("reminder", "General Reminder")
    ]

    # Color coding for message types
    TYPE_COLORS = {
        "security_warning": "#EF4444",    # Red
        "requirement": "#3B82F6",         # Blue
        "guideline": "#10B981",           # Green
        "steps": "#8B5CF6",               # Purple
        "reminder": "#6B7280"             # Gray
    }

    PRIORITY_LEVELS = [
        ("critical", "Must Acknowledge - Respondent must read and confirm before starting"),
        ("important", "Should Read - Displayed prominently but can be skipped"),
        ("informational", "Reference Only - Available but not emphasized")
    ]

    def __init__(self):
        self.id = None
        self.message_type = "reminder"
        self.title = ""
        self.priority = "informational"
        self.content = ""
        self.applies_to = ["all"]
        self.priority_rank = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.message_type,
            "title": self.title,
            "priority": self.priority,
            "content": self.content,
            "applies_to": self.applies_to,
            "priority_rank": self.priority_rank
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AdminMessage':
        msg = cls()
        msg.id = data.get("id")
        msg.message_type = data.get("type", "reminder")
        msg.title = data.get("title", "")
        msg.priority = data.get("priority", "informational")
        msg.content = data.get("content", "")
        msg.applies_to = data.get("applies_to", ["all"])
        msg.priority_rank = data.get("priority_rank", 0)
        return msg


class AdminInstructionsPage(WizardPage):
    """Step 5: Create administrative messages for respondents"""

    def __init__(self, parent=None):
        super().__init__("Administrative Instructions", parent)
        self.messages: List[AdminMessage] = []
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

        # Footer with add button
        footer_layout = self._create_footer()
        layout.addLayout(footer_layout)

    def _create_header(self) -> QtWidgets.QVBoxLayout:
        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(10)

        title = QtWidgets.QLabel("Administrative Instructions")
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
            "Create messages for respondents before they begin the discovery process.<br><br>"

            "<b>Priority Levels:</b><br><br>"
            "<span style='color: #9CA3AF;'>• Must Acknowledge: Respondent cannot proceed until they've read and confirmed "
            "each message individually. Use for critical compliance requirements, legal disclaimers, "
            "or mandatory company policies.</span><br><br>"

            "<span style='color: #9CA3AF;'>• Should Read: Displayed in a summary view at start. Respondent can proceed after "
            "viewing the list. Use for important guidelines and recommendations.</span><br><br>"

            "<span style='color: #9CA3AF;'>• Reference Only: Available in a help panel during discovery. Use for optional tips "
            "and supplementary information.</span><br><br>"

            "<span style='color: #0BE5F5;'>Recommendation:</span> Limit 'Must Acknowledge' to 2-3 messages maximum to avoid "
            "respondent fatigue before they even begin."
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
        # Set size policy so it doesn't stretch unnecessarily
        widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)

        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Set size constraint on the layout itself
        layout.setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)

        # Message entry form
        form_group = self._create_message_form()
        layout.addWidget(form_group)

        layout.addSpacing(20)

        # Color legend (centered, between the two group boxes)
        legend_container = QtWidgets.QWidget()
        legend_container.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        legend_container_layout = QtWidgets.QHBoxLayout(legend_container)
        legend_container_layout.setContentsMargins(0, 0, 0, 0)
        legend_container_layout.addStretch()
        legend_widget = self._create_color_legend()
        legend_container_layout.addWidget(legend_widget)
        legend_container_layout.addStretch()
        layout.addWidget(legend_container)

        layout.addSpacing(20)

        # Messages list/table
        list_group = self._create_messages_list()
        layout.addWidget(list_group)
        layout.addStretch(1)

        return widget

    def _create_color_legend(self) -> QtWidgets.QWidget:
        """Create color legend for message types in a styled container"""
        # Container with gray background and padding
        container = QtWidgets.QFrame()
        container.setStyleSheet("""
            QFrame {
                background-color: #2A2A2A;
                border: 1px solid #404040;
                border-radius: 6px;
                padding: 10px;
            }
        """)

        layout = QtWidgets.QHBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        for msg_type, display_name in AdminMessage.MESSAGE_TYPES:
            color = AdminMessage.TYPE_COLORS[msg_type]

            item_widget = QtWidgets.QWidget()
            item_layout = QtWidgets.QHBoxLayout(item_widget)
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(5)

            # Color box
            color_box = QtWidgets.QLabel()
            color_box.setFixedSize(12, 12)
            color_box.setStyleSheet(f"background-color: {color}; border-radius: 2px;")

            # Label
            label = QtWidgets.QLabel(display_name)
            label.setStyleSheet("color: #D1D5DB; font-size: 11px; border: none")

            item_layout.addWidget(color_box)
            item_layout.addWidget(label)

            layout.addWidget(item_widget)

        return container

    def _create_message_form(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("Add New Message")
        layout = QtWidgets.QVBoxLayout(group)
        layout.setContentsMargins(18, 15, 18, 15)
        layout.setSpacing(10)
        self._apply_group_style(group)

        # Set size policy to fit content snugly
        group.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        form = QtWidgets.QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        # Message type dropdown
        self.type_combo = QtWidgets.QComboBox()
        for value, display in AdminMessage.MESSAGE_TYPES:
            self.type_combo.addItem(display, value)
        form.addRow("Message Type:", self.type_combo)

        # Priority dropdown
        self.priority_combo = QtWidgets.QComboBox()
        self.priority_combo.setFixedHeight(35)
        for value, display in AdminMessage.PRIORITY_LEVELS:
            self.priority_combo.addItem(display, value)
        form.addRow("Priority:", self.priority_combo)

        # Title field
        self.title_input = QtWidgets.QLineEdit()
        self.title_input.setPlaceholderText("Brief title for this message")
        self.title_input.setFixedHeight(35)
        form.addRow("Title:", self.title_input)

        # Content field
        self.content_input = QtWidgets.QTextEdit()
        self.content_input.setPlaceholderText("Message content (use clear, concise language)")
        self.content_input.setFixedHeight(150)
        form.addRow("Content:", self.content_input)

        layout.addLayout(form)

        # Add button aligned right inside the group box
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        self.add_btn = QtWidgets.QPushButton("Add Message")
        self.add_btn.setObjectName("addBtn")
        self.add_btn.setEnabled(False)
        self.add_btn.setCursor(QtCore.Qt.PointingHandCursor)
        button_layout.addWidget(self.add_btn)
        layout.addLayout(button_layout)

        return group

    def _create_messages_list(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("Your Messages")
        layout = QtWidgets.QVBoxLayout(group)
        layout.setContentsMargins(18, 15, 18, 15)
        layout.setSpacing(0)
        self._apply_group_style(group)

        group.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        # Table
        self.messages_table = QtWidgets.QTableWidget()
        self.messages_table.setColumnCount(4)
        self.messages_table.setHorizontalHeaderLabels(["Type", "Title", "Priority", "Actions"])
        self.messages_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        # Row selection only, no per-cell focus
        self.messages_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.messages_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.messages_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.messages_table.setFocusPolicy(QtCore.Qt.NoFocus)

        self.messages_table.setAlternatingRowColors(True)
        self.messages_table.setWordWrap(False)

        hh = self.messages_table.horizontalHeader()
        hh.setStretchLastSection(False)
        hh.setDefaultAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        hh.setMinimumSectionSize(60)

        # Fixed Type and Actions widths
        hh.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)  # Type (fixed)
        hh.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)  # Title (flex)
        hh.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)  # Priority (auto)
        hh.setSectionResizeMode(3, QtWidgets.QHeaderView.Fixed)  # Actions (fixed)

        vh = self.messages_table.verticalHeader()
        vh.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        vh.setDefaultSectionSize(34)
        vh.setMinimumSectionSize(30)

        self.messages_table.setStyleSheet("""
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

        # Fixed block height
        self.messages_table.setFixedHeight(350)
        self.messages_table.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        # Empty state
        self.empty_label = QtWidgets.QLabel("No messages added yet. Add your first message above.")
        self.empty_label.setAlignment(QtCore.Qt.AlignCenter)
        self.empty_label.setFixedHeight(350)
        self.empty_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.empty_label.setStyleSheet("""
            color: #444444;
            font-style: italic;
            padding: 40px;
            border: 2px dashed #444444;
            border-radius: 8px;
            background-color: #101010;
        """)

        layout.addWidget(self.messages_table)
        layout.addWidget(self.empty_label)

        self.messages_table.setVisible(False)
        self.empty_label.setVisible(True)

        # Apply precise fixed widths now that the table exists
        hh.resizeSection(0, self._compute_type_col_width())
        hh.resizeSection(3, self._compute_actions_col_width())

        return group

    def _create_footer(self) -> QtWidgets.QHBoxLayout:
        # Footer is no longer needed - button moved to content area
        layout = QtWidgets.QHBoxLayout()
        return layout

    def _apply_group_style(self, group: QtWidgets.QGroupBox):
        """Apply consistent styling matching Data Sources page"""
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
        self.add_btn.clicked.connect(self._add_message)
        self.title_input.textChanged.connect(self._validate_add_button)
        self.content_input.textChanged.connect(self._validate_add_button)

    def _validate_add_button(self):
        has_title = bool(self.title_input.text().strip())
        has_content = bool(self.content_input.toPlainText().strip())
        self.add_btn.setEnabled(has_title and has_content)

    def _add_message(self):
        msg = AdminMessage()
        msg.id = len(self.messages) + 1
        msg.message_type = self.type_combo.currentData()
        msg.priority = self.priority_combo.currentData()
        msg.title = self.title_input.text().strip()
        msg.content = self.content_input.toPlainText().strip()
        msg.priority_rank = len(self.messages) + 1

        self.messages.append(msg)
        self._refresh_messages_table()

        # Clear form
        self.title_input.clear()
        self.content_input.clear()

        self._validate_form()

    def _refresh_messages_table(self):
        tbl = self.messages_table
        tbl.setRowCount(0)
        messages = getattr(self, "messages", [])

        if not messages:
            tbl.setVisible(False)
            self.empty_label.setVisible(True)
            return

        tbl.setVisible(True)
        self.empty_label.setVisible(False)

        # Constants used inside the Type cell
        PADDING_H = 10
        GAP = 8

        for row, msg in enumerate(messages):
            tbl.insertRow(row)

            # AdminMessage fields
            type_key = getattr(msg, "message_type", "reminder")
            title = getattr(msg, "title", "")
            priority_key = getattr(msg, "priority", "informational")

            # Lookups -> display strings
            type_display = next((disp for key, disp in AdminMessage.MESSAGE_TYPES if key == type_key), type_key)
            type_color = AdminMessage.TYPE_COLORS.get(type_key, "#777777")
            priority_txt = next((disp for key, disp in AdminMessage.PRIORITY_LEVELS if key == priority_key),
                                priority_key)

            # --- Type cell (padding + color bar + label) ---
            type_widget = QtWidgets.QWidget()
            type_layout = QtWidgets.QHBoxLayout(type_widget)
            type_layout.setContentsMargins(PADDING_H, 0, PADDING_H, 0)
            type_layout.setSpacing(GAP)

            color_indicator = QtWidgets.QLabel()
            color_indicator.setFixedSize(4, 20)
            color_indicator.setStyleSheet(f"background:{type_color}; border-radius:1px;")

            type_label = QtWidgets.QLabel(type_display)
            type_label.setStyleSheet("color: #F9FAFB;")

            type_layout.addWidget(color_indicator, 0, QtCore.Qt.AlignVCenter)
            type_layout.addWidget(type_label, 0, QtCore.Qt.AlignVCenter)
            type_layout.addStretch()

            # Height hint only; width is fixed at the header
            type_widget.setMinimumHeight(max(type_label.sizeHint().height(), 20) + 6)
            type_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
            tbl.setCellWidget(row, 0, type_widget)

            # --- Title ---
            title_item = QtWidgets.QTableWidgetItem(title)
            title_item.setFlags(title_item.flags() & ~QtCore.Qt.ItemIsEditable)
            tbl.setItem(row, 1, title_item)

            # --- Priority ---
            pr_item = QtWidgets.QTableWidgetItem(priority_txt)
            pr_item.setFlags(pr_item.flags() & ~QtCore.Qt.ItemIsEditable)
            tbl.setItem(row, 2, pr_item)

            # --- Actions: truly centered Delete button ---
            actions_widget = QtWidgets.QWidget()
            h = QtWidgets.QHBoxLayout(actions_widget)
            h.setContentsMargins(10, 4, 10, 4)
            h.setSpacing(6)
            h.setAlignment(QtCore.Qt.AlignCenter)  # centers within fixed-width column

            btn = QtWidgets.QPushButton("Delete")
            btn.setObjectName("removeBtn")
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, r=row: self._delete_message(r))

            h.addWidget(btn)

            actions_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
            tbl.setCellWidget(row, 3, actions_widget)

        # Let Qt compute row heights from content
        tbl.resizeRowsToContents()

        # Reassert fixed widths (in case the header recalculated)
        hh = tbl.horizontalHeader()
        hh.resizeSection(0, self._compute_type_col_width())
        hh.resizeSection(3, self._compute_actions_col_width())

        # Fit table height to content
        header_h = hh.height()
        rows_h = sum(tbl.rowHeight(r) for r in range(tbl.rowCount()))
        hbar_h = tbl.horizontalScrollBar().height() if tbl.horizontalScrollBar().isVisible() else 0
        frame = 2 * tbl.frameWidth()
        required = header_h + rows_h + hbar_h + frame
        tbl.setFixedHeight(max(350, required))

    def _create_action_buttons(self, row: int) -> QtWidgets.QWidget:
            widget = QtWidgets.QWidget()
            layout = QtWidgets.QHBoxLayout(widget)
            layout.setContentsMargins(4, 4, 4, 4)

            delete_btn = QtWidgets.QPushButton("Delete")
            # delete_btn.setFixedSize(50,25)
            delete_btn.setObjectName("removeBtn")
            delete_btn.setCursor(QtCore.Qt.PointingHandCursor)
            delete_btn.clicked.connect(lambda: self._delete_message(row))

            layout.addWidget(delete_btn)
            return widget

    def _compute_type_col_width(self) -> int:
        """Constant width for 'Type' column (fits 'Step-by-Step Instructions' + bar + padding)."""
        PADDING_H = 10
        GAP = 8
        BAR_W = 4
        EXTRA = 6
        fm = QtGui.QFontMetrics(self.messages_table.font())
        widest_label = "Step-by-Step Instructions"
        text_w = fm.horizontalAdvance(widest_label)
        return PADDING_H + BAR_W + GAP + text_w + PADDING_H + EXTRA

    def _compute_actions_col_width(self) -> int:
        """Constant width for 'Actions' column to snugly fit a 'Delete' button with margins."""
        # Create a temp button to ask for its sizeHint using the table's font
        btn = QtWidgets.QPushButton("Delete")
        btn.setFont(self.messages_table.font())
        hint = btn.sizeHint()
        # Match the margins used in the cell wrapper
        LEFT_RIGHT = 10  # h.setContentsMargins(10, 4, 10, 4)
        EXTRA = 6  # breathing room
        return hint.width() + (LEFT_RIGHT * 2) + EXTRA

    def _delete_message(self, row: int):
        """Delete a message with confirmation, then refresh UI and re-validate the page."""
        # Defensive bounds check
        if not hasattr(self, "messages") or row < 0 or row >= len(self.messages):
            return

        # Confirmation dialog
        confirm = QtWidgets.QMessageBox.question(
            self,
            "Delete message?",
            "Are you sure you want to delete this message?\nThis action cannot be undone.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if confirm != QtWidgets.QMessageBox.Yes:
            return

        # Preserve table scroll + a sensible selection target after delete
        tbl = self.messages_table
        vsb = tbl.verticalScrollBar()
        scroll_pos = vsb.value() if vsb else 0
        next_select = min(row, tbl.rowCount() - 2)  # select same row index, or previous if last row

        # Mutate model
        try:
            del self.messages[row]
        except Exception:
            return

        # Refresh table (rebuilds rows and rebinds action buttons)
        self._refresh_messages_table()

        # Restore scroll position and selection (if rows remain)
        if vsb:
            vsb.setValue(scroll_pos)
        if 0 <= next_select < tbl.rowCount():
            tbl.setCurrentCell(next_select, 0)

        # Re-validate current page so Next button reflects new state
        is_valid = True
        try:
            current_page = self.pages[self.current_step]
            if hasattr(current_page, "validate_page"):
                is_valid, _ = current_page.validate_page()
        except Exception:
            is_valid = True
        self.btn_next.setEnabled(is_valid)


    def _validate_form(self):
        # This step is optional, so always valid
        self.canProceed.emit(True)

    def showEvent(self, event):
        """Apply input styles when page becomes visible"""
        super().showEvent(event)
        self._apply_input_styles()

    def _apply_input_styles(self):
        """Apply consistent input styling matching Data Sources page"""
        input_style = """
            QLineEdit {
                background-color: #404040;
                border: 1px solid #606060;
                border-radius: 6px;
                padding-left: 8px;
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
                padding: 6px 12px;
                font-weight: 500;
            }
            QPushButton#removeBtn:hover {
                background-color: #606060;
            }
        """
        self.setStyleSheet(self.styleSheet() + input_style)

    def _type_display_and_color(self, type_key: str) -> tuple[str, str]:
        """Return (display_name, color_hex) for a message_type key."""
        # Look up display name
        display = next((disp for key, disp in AdminMessage.MESSAGE_TYPES if key == type_key), type_key)
        # Look up color
        color = AdminMessage.TYPE_COLORS.get(type_key, "#777777")
        return display, color

    def _priority_display(self, priority_key: str) -> str:
        """Return display name for a priority key."""
        return next((disp for key, disp in AdminMessage.PRIORITY_LEVELS if key == priority_key), priority_key)

    # WizardPage interface implementation
    def validate_page(self) -> Tuple[bool, str]:
        return True, ""

    def collect_data(self) -> Dict[str, Any]:
        return {
            "messages": [msg.to_dict() for msg in self.messages],
            "total_messages": len(self.messages),
            "critical_count": sum(1 for m in self.messages if m.priority == "critical")
        }

    def load_data(self, data: Dict[str, Any]) -> None:
        messages_data = data.get("messages", [])
        self.messages = [AdminMessage.from_dict(m) for m in messages_data]
        self._refresh_messages_table()
        self._validate_form()
