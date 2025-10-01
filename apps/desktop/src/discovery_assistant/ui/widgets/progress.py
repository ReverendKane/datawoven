from PySide6 import QtWidgets, QtCore
from discovery_assistant.baselogger import logging

_LOGGER = logging.getLogger('DISCOVERY.ui.widgets.progress')

class Progress(QtWidgets.QWidget):
    valueChanged = QtCore.Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.label = QtWidgets.QLabel("Completion")
        self.label.setStyleSheet("font-size:12px; color:#64748B; background:transparent;")

        self.percent = QtWidgets.QLabel("0%")
        self.percent.setStyleSheet("font-size:12px; color:#0F172A; background:transparent;")
        self.percent.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.bar = QtWidgets.QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setTextVisible(False)  # we show % in a separate label
        self.bar.setFixedHeight(8)     # slim line like the screenshot
        self.bar.setStyleSheet("""
            QProgressBar {
                border: 0;
                background: #E5E7EB;      /* light gray track */
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background: #111827;      /* dark fill (adjust to taste) */
                border-radius: 4px;
            }
        """)

        top = QtWidgets.QHBoxLayout()
        top.setContentsMargins(0,0,0,0)
        top.addWidget(self.label)
        top.addStretch(1)
        top.addWidget(self.percent)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0,0,0,0)
        root.setSpacing(6)
        root.addLayout(top)
        root.addWidget(self.bar)

    @QtCore.Slot(int)
    def set_value(self, v: int):
        v = max(0, min(100, v))
        self.bar.setValue(v)
        self.percent.setText(f"{v}%")
        self.valueChanged.emit(v)
