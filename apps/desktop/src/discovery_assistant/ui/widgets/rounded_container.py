from PySide6 import QtWidgets

class RoundedContainer(QtWidgets.QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("RoundedContainer")

        # Rounded, light background, subtle border
        self.setStyleSheet("""
            #RoundedContainer {
                background: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 12px;
            }
        """)

        # Give it an internal layout with padding
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)  # spacing inside
        layout.setSpacing(2)
        self.setLayout(layout)

    def addWidget(self, widget: QtWidgets.QWidget):
        """Helper to add children easily"""
        self.layout().addWidget(widget)

    def addLayout(self, layout: QtWidgets.QLayout):
        self.layout().addLayout(layout)
