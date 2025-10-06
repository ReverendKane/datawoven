"""
Critical Message Dialog
Blocking modal that displays "Must Acknowledge" administrative messages
before user can access the main application.
"""

from typing import List, Dict, Any, Optional
from PySide6 import QtWidgets, QtCore, QtGui
from discovery_assistant.baselogger import logging

_LOGGER = logging.getLogger("DISCOVERY.ui.widgets.critical_message_dialog")


class CriticalMessageDialog(QtWidgets.QDialog):
    """
    Modal dialog for critical administrative messages.
    Blocks application access until all messages are acknowledged.
    """

    def __init__(self, messages: List[Dict[str, Any]], parent=None):
        super().__init__(parent)
        self.messages = messages
        self.current_index = 0

        self.setWindowTitle("Important Message")
        self.setModal(True)
        self.setMinimumSize(600, 400)
        self.resize(700, 500)

        # Prevent closing with Esc or X button
        self.setWindowFlags(
            QtCore.Qt.Dialog |
            QtCore.Qt.CustomizeWindowHint |
            QtCore.Qt.WindowTitleHint
        )

        self._setup_ui()
        self._show_current_message()

        _LOGGER.info(f"Critical message dialog initialized with {len(messages)} messages")

    def _setup_ui(self):
        """Build the dialog interface"""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        self.setStyleSheet("""
            QDialog {
                background: #FFFFFF;
            }
        """)

        # Progress indicator
        self.progress_label = QtWidgets.QLabel()
        self.progress_label.setAlignment(QtCore.Qt.AlignCenter)
        self.progress_label.setStyleSheet("""
            font-size: 12px;
            color: #64748B;
            margin-bottom: 10px;
        """)
        layout.addWidget(self.progress_label)

        # Warning icon
        icon_label = QtWidgets.QLabel()
        icon_label.setAlignment(QtCore.Qt.AlignCenter)
        icon_label.setStyleSheet("margin-bottom: 10px;")

        # Use standard warning icon
        warning_icon = self.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxWarning)
        icon_pixmap = warning_icon.pixmap(48, 48)
        icon_label.setPixmap(icon_pixmap)
        layout.addWidget(icon_label)

        # Message content area (scrollable)
        content_scroll = QtWidgets.QScrollArea()
        content_scroll.setWidgetResizable(True)
        content_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        content_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        content_scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
        """)

        content_widget = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 10, 0)
        content_layout.setSpacing(15)

        # Title
        self.title_label = QtWidgets.QLabel()
        self.title_label.setWordWrap(True)
        self.title_label.setAlignment(QtCore.Qt.AlignCenter)
        self.title_label.setStyleSheet("""
            font-size: 20px;
            font-weight: 600;
            color: #0F172A;
            margin-bottom: 10px;
        """)
        content_layout.addWidget(self.title_label)

        # Content
        self.content_label = QtWidgets.QLabel()
        self.content_label.setWordWrap(True)
        self.content_label.setStyleSheet("""
            font-size: 15px;
            color: #334155;
            line-height: 1.6;
            padding: 20px;
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
        """)
        content_layout.addWidget(self.content_label)

        content_layout.addStretch()
        content_scroll.setWidget(content_widget)
        layout.addWidget(content_scroll, 1)

        # Checkbox for acknowledgment
        self.acknowledge_checkbox = QtWidgets.QCheckBox(
            "I have read and understand this message"
        )
        self.acknowledge_checkbox.setStyleSheet("""
            QCheckBox {
                font-size: 14px;
                color: #0F172A;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #D1D5DB;
                border-radius: 4px;
                background: #FFFFFF;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #0F172A;
                border-radius: 4px;
                background: #0F172A;
                image: url(none);
            }
        """)
        self.acknowledge_checkbox.stateChanged.connect(self._on_checkbox_changed)
        layout.addWidget(self.acknowledge_checkbox, 0, QtCore.Qt.AlignCenter)

        # Button
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()

        self.continue_btn = QtWidgets.QPushButton()
        self.continue_btn.setObjectName("continueBtn")
        self.continue_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.continue_btn.setEnabled(False)
        self.continue_btn.setMinimumWidth(180)
        self.continue_btn.setStyleSheet("""
            QPushButton#continueBtn {
                background: #0F172A;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 15px;
                font-weight: 600;
            }
            QPushButton#continueBtn:hover:enabled {
                background: #1E293B;
            }
            QPushButton#continueBtn:disabled {
                background: #E5E7EB;
                color: #9CA3AF;
            }
        """)
        self.continue_btn.clicked.connect(self._on_continue_clicked)

        button_layout.addWidget(self.continue_btn)
        button_layout.addStretch()

        layout.addLayout(button_layout)

    def _show_current_message(self):
        """Display the current message"""
        if self.current_index >= len(self.messages):
            return

        msg = self.messages[self.current_index]
        total = len(self.messages)

        # Update progress
        self.progress_label.setText(f"Critical Message {self.current_index + 1} of {total}")

        # Update content
        self.title_label.setText(msg.get("title", "Important Message"))
        self.content_label.setText(msg.get("content", ""))

        # Reset checkbox
        self.acknowledge_checkbox.setChecked(False)

        # Update button text
        if self.current_index < len(self.messages) - 1:
            self.continue_btn.setText("Next Message →")
        else:
            self.continue_btn.setText("I Acknowledge - Continue to Application")

    def _on_checkbox_changed(self, state):
        """Enable/disable continue button based on checkbox"""
        self.continue_btn.setEnabled(state == QtCore.Qt.Checked)

    def _on_continue_clicked(self):
        """Handle continue button click"""
        self.current_index += 1

        if self.current_index >= len(self.messages):
            # All messages acknowledged
            _LOGGER.info("All critical messages acknowledged")
            self.accept()
        else:
            # Show next message
            self._show_current_message()

    def closeEvent(self, event):
        """Prevent closing the dialog without acknowledging"""
        event.ignore()

    def keyPressEvent(self, event):
        """Prevent Esc key from closing dialog"""
        if event.key() == QtCore.Qt.Key_Escape:
            event.ignore()
        else:
            super().keyPressEvent(event)
