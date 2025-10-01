from PySide6 import QtWidgets, QtCore, QtGui


class WarningWidget(QtWidgets.QWidget):
    """Reusable warning/info box with icon and message"""

    def __init__(self, message: str, icon_path: str = None, parent=None):
        super().__init__(parent)

        # Main container with background
        self.container = QtWidgets.QFrame(self)
        self.container.setStyleSheet("""
            QFrame {
                background-color: #1A415E;
                border: .5px solid #0BE5F5;
                border-radius: 6px;
            }
        """)

        # Horizontal layout for icon + message
        content_layout = QtWidgets.QHBoxLayout(self.container)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(20)

        # Icon widget on the left
        self.icon_widget = QtWidgets.QLabel()
        self.icon_widget.setFixedSize(35, 35)
        self.icon_widget.setScaledContents(True)
        self.icon_widget.setStyleSheet("background: transparent; border: none;")

        if icon_path:
            pixmap = QtGui.QPixmap(icon_path)
            if not pixmap.isNull():
                self.icon_widget.setPixmap(pixmap)
            else:
                self.icon_widget.setText("⚠️")
                self.icon_widget.setAlignment(QtCore.Qt.AlignCenter)
        else:
            self.icon_widget.setText("⚠️")
            self.icon_widget.setAlignment(QtCore.Qt.AlignCenter)
            self.icon_widget.setStyleSheet("background: transparent; border: none; font-size: 24px;")

        # Message widget on the right
        self.message_widget = QtWidgets.QLabel(message)
        self.message_widget.setWordWrap(True)
        self.message_widget.setStyleSheet("""
            color: #FFFFFF;
            font-size: 12px;
            background: transparent;
            border: none;
        """)

        content_layout.addWidget(self.icon_widget, 0, QtCore.Qt.AlignTop)
        content_layout.addWidget(self.message_widget, 1)

        # Outer layout to contain the frame
        outer_layout = QtWidgets.QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(self.container)

    def set_message(self, message: str):
        """Update the message text"""
        self.message_widget.setText(message)

    def set_icon(self, icon_path: str):
        """Update the icon"""
        pixmap = QtGui.QPixmap(icon_path)
        if not pixmap.isNull():
            self.icon_widget.setPixmap(pixmap)
