"""
Data Source Modal Dialog
Modal for adding/editing data sources with category, name, and description.
"""

from typing import Optional, Dict, Any
from PySide6 import QtWidgets, QtCore, QtGui


class DataSource:
    """Represents a single data source"""

    CATEGORIES = [
        ("email", "Email System"),
        ("crm", "CRM/Customer Database"),
        ("storage", "Document Storage"),
        ("financial", "Financial/Accounting System"),
        ("project_mgmt", "Project Management System"),
        ("communication", "Team Communication"),
        ("inventory", "Inventory Management"),
        ("other", "Other")
    ]

    # Color coding for categories (matching Admin Instructions pattern)
    CATEGORY_COLORS = {
        "email": "#F59E0B",  # Amber
        "crm": "#06B6D4",  # Cyan
        "storage": "#8B5CF6",  # Purple
        "financial": "#10B981",  # Green
        "project_mgmt": "#EC4899",  # Pink
        "communication": "#3B82F6",  # Blue
        "inventory": "#6366F1",  # Indigo
        "other": "#6B7280"  # Gray
    }

    def __init__(self):
        self.id = None
        self.category = "other"
        self.name = ""
        self.description = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "name": self.name,
            "description": self.description
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DataSource':
        source = cls()
        source.id = data.get("id")
        source.category = data.get("category", "other")
        source.name = data.get("name", "")
        source.description = data.get("description", "")
        return source


class DataSourceModal(QtWidgets.QDialog):
    """Modal dialog for adding or editing a data source"""

    def __init__(self, parent=None, source: Optional[DataSource] = None,
                 preset_category: Optional[str] = None, preset_name: Optional[str] = None):
        super().__init__(parent)

        self.source = source if source else DataSource()
        self.preset_category = preset_category
        self.preset_name = preset_name
        self.is_edit_mode = source is not None

        self._setup_ui()
        self._apply_styles()
        self._connect_signals()

        # Pre-populate fields if editing or using template
        if self.is_edit_mode:
            self._populate_fields()
        elif preset_category or preset_name:
            self._apply_preset()

    def _setup_ui(self):
        """Setup the modal UI"""
        self.setWindowTitle("Edit Data Source" if self.is_edit_mode else "Add Data Source")
        self.setModal(True)
        self.setMinimumWidth(500)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Form fields
        form = QtWidgets.QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(12)

        # Category dropdown
        self.category_combo = QtWidgets.QComboBox()
        self.category_combo.setFixedHeight(35)
        for value, display in DataSource.CATEGORIES:
            self.category_combo.addItem(display, value)

        # Only set default to "Other" if no preset category was provided
        if not self.preset_category and not self.is_edit_mode:
            self.category_combo.setCurrentIndex(len(DataSource.CATEGORIES) - 1)

        form.addRow("Category:", self.category_combo)

        # Specific name input
        self.name_input = QtWidgets.QLineEdit()
        self.name_input.setPlaceholderText("e.g., Gmail, Outlook, Salesforce")
        self.name_input.setFixedHeight(35)
        form.addRow("Specific Name:", self.name_input)

        # Description textarea
        self.description_input = QtWidgets.QTextEdit()
        self.description_input.setPlaceholderText("Brief description of what this system is used for (optional)")
        self.description_input.setFixedHeight(100)
        form.addRow("Description:", self.description_input)

        layout.addLayout(form)

        # Button bar
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()

        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        self.cancel_btn.setObjectName("cancelBtn")
        self.cancel_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.cancel_btn.setFixedHeight(35)

        self.save_btn = QtWidgets.QPushButton("Save Source")
        self.save_btn.setObjectName("saveBtn")
        self.save_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.save_btn.setEnabled(False)  # Disabled until name is entered
        self.save_btn.setFixedHeight(35)

        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.save_btn)

        layout.addLayout(button_layout)

    def _apply_styles(self):
        """Apply consistent styling"""
        self.setStyleSheet("""
            QDialog {
                background-color: #1F1F1F;
            }
            QLabel {
                color: #F9FAFB;
                font-size: 14px;
            }
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
            QPushButton#cancelBtn {
                background-color: #404040;
                color: #F9FAFB;
                border: 1px solid #606060;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: 500;
            }
            QPushButton#cancelBtn:hover {
                background-color: #606060;
            }
            QPushButton#saveBtn {
                background-color: #606060;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: 500;
            }
            QPushButton#saveBtn:hover {
                background-color: #808080;
            }
            QPushButton#saveBtn:disabled {
                background-color: #404040;
                color: #6B7280;
            }
        """)

    def _connect_signals(self):
        """Connect UI signals"""
        self.name_input.textChanged.connect(self._validate_form)
        self.cancel_btn.clicked.connect(self.reject)
        self.save_btn.clicked.connect(self._save_and_close)

    def _populate_fields(self):
        """Populate fields when editing existing source"""
        # Set category
        for i in range(self.category_combo.count()):
            if self.category_combo.itemData(i) == self.source.category:
                self.category_combo.setCurrentIndex(i)
                break

        # Set name and description
        self.name_input.setText(self.source.name)
        self.description_input.setPlainText(self.source.description)

    def _apply_preset(self):
        """Apply preset values from template"""
        if self.preset_category:
            for i in range(self.category_combo.count()):
                if self.category_combo.itemData(i) == self.preset_category:
                    self.category_combo.setCurrentIndex(i)
                    break

        if self.preset_name:
            self.name_input.setText(self.preset_name)
            # Select all text so user can immediately type to replace
            self.name_input.selectAll()
            self.name_input.setFocus()

    def _validate_form(self):
        """Enable save button only if name is provided"""
        has_name = bool(self.name_input.text().strip())
        self.save_btn.setEnabled(has_name)

    def _save_and_close(self):
        """Save the data source and close dialog"""
        self.source.category = self.category_combo.currentData()
        self.source.name = self.name_input.text().strip()
        self.source.description = self.description_input.toPlainText().strip()

        self.accept()

    def get_source(self) -> DataSource:
        """Return the configured data source"""
        return self.source
