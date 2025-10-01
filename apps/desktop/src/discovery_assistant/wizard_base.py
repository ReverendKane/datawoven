"""
Base classes for the Admin Setup Wizard.
Separated to avoid circular imports.
"""

from typing import Dict, Any
from PySide6 import QtWidgets, QtCore


class WizardPage(QtWidgets.QWidget):
    """Base class for wizard pages"""

    # Signals for navigation control
    canProceed = QtCore.Signal(bool)  # Enable/disable Next button
    proceedRequested = QtCore.Signal()  # Request to go to next page

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self._is_valid = False

    def validate_page(self) -> tuple[bool, str]:
        """Override in subclasses. Returns (is_valid, error_message)"""
        return True, ""

    def collect_data(self) -> Dict[str, Any]:
        """Override in subclasses to return page data"""
        return {}

    def load_data(self, data: Dict[str, Any]) -> None:
        """Override in subclasses to load existing data"""
        pass
