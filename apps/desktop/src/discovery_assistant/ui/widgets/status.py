from discovery_assistant.ui.widgets.rounded_container import RoundedContainer
from discovery_assistant.baselogger import logging
from discovery_assistant.ui.widgets.progress import Progress
from PySide6 import QtWidgets

_LOGGER = logging.getLogger("DISCOVERY.ui.widgets.status_widget")

class StatusWidget(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        _LOGGER.info("Status widget initialized")

        # Outer layout for this widget
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        card = RoundedContainer(self)  # DO NOT change its objectName
        card_layout = card.layout()

        title = QtWidgets.QLabel("Session Status")
        title.setStyleSheet("font-size:14px; font-weight:600; color:#0F172A; background:transparent;")
        card_layout.addWidget(title)

        self.progress = Progress(self)
        card_layout.addWidget(self.progress)

        outer.addWidget(card)
