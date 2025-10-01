from PySide6 import QtWidgets, QtCore
from discovery_assistant.baselogger import logging

_LOGGER = logging.getLogger('DISCOVERY.ui.widgets.settings')

class Settings(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.label = QtWidgets.QLabel("Settings")
        self.label.setStyleSheet("font-size:12px; color:#64748B; background:transparent;")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.label)
        layout.addStretch(1)


