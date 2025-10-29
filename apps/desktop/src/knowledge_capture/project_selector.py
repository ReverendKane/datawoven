# project_selector.py
"""
Project Selector Widget - Manages project selection and paths
"""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QMessageBox, QInputDialog, QFileDialog, QFrame
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor
from pathlib import Path
import os
from dotenv import load_dotenv
import logging

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
LOG_CTX = "ProjectSelector"
log = logging.LoggerAdapter(logging.getLogger(__name__), {"ctx": LOG_CTX})
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


class ProjectSelector(QFrame):
    """
    Project selector widget with combobox and create a button
    Reads projects from D:\\DATA\\ directory
    """
    project_changed = Signal(str, str)  # (project_name, project_path)

    def __init__(self, parent=None):
        super().__init__(parent)
        load_dotenv()

        # Get base data directory from environment or use default
        self.base_data_dir = Path("D:/DATA")

        self.init_ui()
        self.load_projects()
        self.set_default_project()
        QTimer.singleShot(0, lambda: self.on_project_changed(self.project_combo.currentText()))

    def init_ui(self):
        """Initialize the UI"""
        # Use QFrame features for better background control
        self.setFrameShape(QFrame.StyledPanel)
        self.setAutoFillBackground(True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)

        # Set black background with border
        self.setStyleSheet("""
            ProjectSelector {
                background-color: #000000;
                border-bottom: 1px solid #333333;
            }
            QLabel {
                color: #cccccc;
                font-size: 13px;
                font-weight: normal;
                background: transparent;
            }
            QComboBox {padding: 4px 8px;}
            QComboBox QAbstractItemView::item {min-height: 30px; padding: 6px 8px;}
            QPushButton {
                background-color: #2d8659;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 6px 15px;
                font-size: 12px;
                font-weight: normal;
            }
            QPushButton:hover {
                background-color: #36a06a;
            }
            QPushButton:pressed {
                background-color: #236b47;
            }
        """)

        # Project label
        label = QLabel("Current Project:")
        layout.addWidget(label)

        # Project combobox
        self.project_combo = QComboBox()
        self.project_combo.setFixedHeight(30)
        self.project_combo.setMinimumWidth(250)
        self.project_combo.currentTextChanged.connect(self.on_project_changed)
        layout.addWidget(self.project_combo)

        # Create new button
        self.create_btn = QPushButton("Create New")
        self.create_btn.setCursor(Qt.PointingHandCursor)
        self.create_btn.clicked.connect(self.create_new_project)
        layout.addWidget(self.create_btn)

        # Spacer
        layout.addStretch()

        # Current paths display (small, subtle)
        self.paths_label = QLabel("")
        self.paths_label.setStyleSheet("""
            color: #666666;
            font-size: 10px;
            font-weight: normal;
            background: transparent;
        """)
        layout.addWidget(self.paths_label)

    def load_projects(self):
        """Load available projects from base data directory"""
        self.project_combo.clear()

        if not self.base_data_dir.exists():
            # Base directory doesn't exist - create it
            try:
                self.base_data_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Directory Error",
                    f"Could not create base directory:\n{self.base_data_dir}\n\nError: {e}"
                )
                return

        # Get all subdirectories in base data dir
        try:
            projects = [d.name for d in self.base_data_dir.iterdir() if d.is_dir()]
            projects.sort()

            if projects:
                self.project_combo.addItems(projects)
            else:
                self.project_combo.addItem("(No projects found)")
                self.create_btn.setEnabled(True)

        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"Could not read projects directory:\n{e}"
            )

    def set_default_project(self):
        """Set the default project from environment variable"""
        default_project = os.getenv("DEFAULT_PROJECT", "")

        if default_project:
            # Try to find and select the default project
            index = self.project_combo.findText(default_project)
            if index >= 0:
                self.project_combo.setCurrentIndex(index)
            else:
                # Default project not found in list
                if self.project_combo.count() > 0 and self.project_combo.currentText() != "(No projects found)":
                    # Just use first available project
                    self.project_combo.setCurrentIndex(0)
        else:
            # No default set, use first available
            if self.project_combo.count() > 0 and self.project_combo.currentText() != "(No projects found)":
                self.project_combo.setCurrentIndex(0)

    def on_project_changed(self, project_name):
        """Handle project selection change"""
        if not project_name or project_name == "(No projects found)":
            return

        project_path = self.base_data_dir / project_name

        # Update paths display
        raw_output = project_path / "raw-output"
        tracking = project_path / "tracking"

        self.paths_label.setText(
            f'<span style="color: #A6A6A6;">Output:</span> {raw_output}      |      '
            f'<span style="color: #A6A6A6;">Tracking:</span> {tracking}'
        )

        # Emit signal with project info
        self.project_changed.emit(project_name, str(project_path))

    def create_new_project(self):
        """Create a new project directory"""
        # Get project name from user
        project_name, ok = QInputDialog.getText(
            self,
            "Create New Project",
            "Enter project name:\n(Directory will be created at D:\\DATA\\<name>)",
            text=""
        )

        if not ok or not project_name:
            return

        # Validate project name (basic validation)
        project_name = project_name.strip()
        if not project_name:
            QMessageBox.warning(self, "Invalid Name", "Project name cannot be empty.")
            return

        # Check for invalid characters
        invalid_chars = '<>:"|?*\\'
        if any(char in project_name for char in invalid_chars):
            QMessageBox.warning(
                self,
                "Invalid Name",
                f"Project name cannot contain: {invalid_chars}"
            )
            return

        # Create project directory
        project_path = self.base_data_dir / project_name

        if project_path.exists():
            QMessageBox.warning(
                self,
                "Project Exists",
                f"A project named '{project_name}' already exists."
            )
            return

        try:
            # Create project directory and subdirectories
            project_path.mkdir(parents=True, exist_ok=True)

            # Create main directories
            raw_output = project_path / "raw-output"
            raw_output.mkdir(exist_ok=True)

            # Create subdirectories for each source type
            (raw_output / "pdf").mkdir(exist_ok=True)
            (raw_output / "ocr").mkdir(exist_ok=True)
            (raw_output / "database").mkdir(exist_ok=True)
            (raw_output / "web").mkdir(exist_ok=True)
            (raw_output / "text").mkdir(exist_ok=True)

            # Create tracking directory
            tracking_dir = project_path / "tracking"
            tracking_dir.mkdir(exist_ok=True)

            # Create automation-configs directory
            (project_path / "automation-configs").mkdir(exist_ok=True)

            # Initialize cost tracking database
            from cost_tracker import CostTracker
            db_path = tracking_dir / "project_tracking.db"
            cost_tracker = CostTracker(db_path=str(db_path))
            # Database is initialized automatically by CostTracker.__init__()

            # Reload projects list
            self.load_projects()

            # Select the new project
            index = self.project_combo.findText(project_name)
            if index >= 0:
                self.project_combo.setCurrentIndex(index)

            QMessageBox.information(
                self,
                "Success",
                f"Project '{project_name}' created successfully!\n\n"
                f"Location: {project_path}\n\n"
                f"Directories created:\n"
                f"  • raw-output/pdf\n"
                f"  • raw-output/ocr\n"
                f"  • raw-output/database\n"
                f"  • raw-output/web\n"
                f"  • raw-output/text\n"
                f"  • tracking/ (with project_tracking.db)\n"
                f"  • automation-configs/"
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to create project:\n{e}"
            )

    def get_current_project(self):
        """Get current project name"""
        project = self.project_combo.currentText()
        if project == "(No projects found)":
            return None
        return project

    def get_current_project_path(self):
        """Get current project path"""
        project = self.get_current_project()
        if not project:
            return None
        return str(self.base_data_dir / project)

    def get_raw_output_path(self):
        """Get raw-output path for current project"""
        project_path = self.get_current_project_path()
        if not project_path:
            return None
        return str(Path(project_path) / "raw-output")

    def get_tracking_path(self):
        """Get tracking path for current project"""
        project_path = self.get_current_project_path()
        if not project_path:
            return None
        return str(Path(project_path) / "tracking")

    def get_database_path(self):
        """Get database path for current project"""
        tracking_path = self.get_tracking_path()
        if not tracking_path:
            return None
        return str(Path(tracking_path) / "project_tracking.db")

    def get_output_path_for_type(self, source_type: str):
        """
        Get the appropriate output path for a given source type

        Args:
            source_type: One of 'pdf', 'ocr', 'database', 'web', 'text'

        Returns:
            Path to the appropriate raw-output subdirectory, or None if no project selected
        """
        raw_output = self.get_raw_output_path()
        if not raw_output:
            return None

        valid_types = ['pdf', 'ocr', 'database', 'web', 'text']
        if source_type not in valid_types:
            raise ValueError(f"Invalid source_type: {source_type}. Must be one of {valid_types}")

        output_path = Path(raw_output) / source_type

        # Ensure directory exists
        output_path.mkdir(parents=True, exist_ok=True)

        return str(output_path)

    def get_automation_configs_path(self):
        """Get automation-configs path for current project"""
        project_path = self.get_current_project_path()
        if not project_path:
            return None
        return str(Path(project_path) / "automation-configs")

    def get_output_path_for_type(self, source_type: str) -> str:
        """
        Get the appropriate output path for a given source type

        Args:
            source_type: One of 'pdf', 'ocr', 'database', 'web', 'text'

        Returns:
            Full path to the output directory for that type, or None if no project selected
        """
        raw_output = self.get_raw_output_path()
        if not raw_output:
            return None

        valid_types = ['pdf', 'ocr', 'database', 'web', 'text']
        if source_type.lower() not in valid_types:
            return raw_output  # Default to base raw-output if type unknown

        return str(Path(raw_output) / source_type.lower())

    def get_automation_configs_path(self):
        """Get automation-configs path for current project"""
        project_path = self.get_current_project_path()
        if not project_path:
            return None
        return str(Path(project_path) / "automation-configs")
