from PySide6 import QtCore, QtGui, QtWidgets
from .analyzing_loader import AnalyzingLoader
from .quick_menu_widget import QuickMenuWidget
import discovery_assistant.constants as constants
from typing import List, Dict


class ChatInputWidget(QtWidgets.QWidget):
    """Separate chat input widget with better layout structure"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("chatInputWidget")

        # Force the widget to have an opaque background
        self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent, True)
        self.setAutoFillBackground(True)

        # Configuration variables for easy adjustment
        self.window_height = 200
        self.max_window_height = 400
        self.action_buttons_height = 33

        self._setup_ui()
        self._setup_styling()

    def paintEvent(self, event):
        """Force paint the background"""
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), QtGui.QColor("#2A2A2A"))
        super().paintEvent(event)

    def _setup_ui(self):
        """Create the main structure with proper layouts"""
        # Main vertical container
        main_layout = QtWidgets.QVBoxLayout(self)
        # main_layout.setContentsMargins(10, 10, 10, 8)  # Added 8px bottom margin
        # main_layout.setSpacing(4)  # Reduced spacing between containers

        # 1. Input area container (gray rounded box)
        self.input_container = self._create_input_container()
        main_layout.addWidget(self.input_container, 1)  # Takes available space

        # 2. Action buttons container (fixed height)
        self.action_buttons = self._create_action_buttons()
        main_layout.addWidget(self.action_buttons, 0)  # Fixed size, no stretch

        # Set widget size constraints
        self.setMinimumHeight(self.window_height)
        self.setMaximumHeight(self.max_window_height)

    def _create_input_container(self) -> QtWidgets.QWidget:
        """Create the gray rounded container with text input and chat buttons"""
        container = QtWidgets.QWidget()
        container.setObjectName("inputContainer")

        # Vertical layout for input container
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(8,0,8,12)
        layout.setSpacing(0)
        layout.setSpacing(8)

        # 1. Text input area (top section)
        text_input_layout = QtWidgets.QHBoxLayout()
        text_input_layout.setContentsMargins(0, 0, 0, 0)

        self.text_input = QtWidgets.QTextEdit()
        self.text_input.setObjectName("textInput")
        self.text_input.setPlaceholderText("Ask a question...")
        self.text_input.setMinimumHeight(40)

        text_input_layout.addWidget(self.text_input)
        layout.addLayout(text_input_layout)

        # Add stretch to push chat buttons to bottom
        layout.addStretch(1)

        # 2. Chat buttons (anchored to bottom)
        chat_buttons_layout = QtWidgets.QHBoxLayout()
        chat_buttons_layout.setContentsMargins(0, 0, 0, 0)
        chat_buttons_layout.setSpacing(6)

        # Create chat buttons
        self.add_btn = QtWidgets.QPushButton("+")
        self.add_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.add_btn.setObjectName("chatButton")
        self.add_btn.setFixedSize(32, 32)

        self.analyzing_loader = AnalyzingLoader(self)
        self.start_analyzing()

        self.quick_menu = QuickMenuWidget(self)
        self._setup_quick_menu_connections()

        self.send_btn = self._create_send_button()
        self.send_btn.setObjectName("sendButton")
        self.send_btn.setFixedSize(32, 32)

        chat_buttons_layout.addWidget(self.add_btn)
        chat_buttons_layout.addWidget(self.analyzing_loader)
        chat_buttons_layout.addStretch()
        chat_buttons_layout.addWidget(self.quick_menu)
        chat_buttons_layout.addWidget(self.send_btn)

        layout.addLayout(chat_buttons_layout)

        return container

    def _setup_quick_menu_connections(self):
        """Setup callbacks for quick menu buttons"""
        self.quick_menu.connect_export_clicked(self._on_export_clicked)
        self.quick_menu.connect_dictate_toggled(self._on_dictate_toggled)
        self.quick_menu.connect_clear_clicked(self._on_clear_clicked)

    def _on_export_clicked(self):
        """Handle export button clicked"""
        print("Export clicked")
        # TODO: Implement export functionality

    def _on_dictate_toggled(self, active):
        """Handle dictate button toggled"""
        if active:
            print("Dictate activated - start recording")
            # TODO: Start microphone recording
        else:
            print("Dictate deactivated - stop recording")
            # TODO: Stop recording and process audio

    def _on_clear_clicked(self):
        """Handle clear button clicked"""
        print("Clear clicked")
        # Clear the text input
        self.text_input.clear()
        # TODO: Add any other clearing logic

    def _update_send_button_icon(self, btn):
        """Update the power button icon based on current state"""
        if btn._is_hovering:
            # Active state - use active icon regardless of hover
            btn.setIcon(btn._hover_icon)
        else:
            # Inactive state
            btn.setIcon(btn._inactive_icon)

    def start_analyzing(self):
        """Start the analyzing animation"""
        self.analyzing_loader.start_animation()

    def stop_analyzing(self):
        """Stop the analyzing animation"""
        self.analyzing_loader.stop_animation()

    def is_analyzing(self):
        """Check if currently analyzing"""
        return self.analyzing_loader.is_animating()

    def _create_send_button(self) -> QtWidgets.QPushButton:
        """Create a circular power button with three states"""
        btn = QtWidgets.QPushButton()
        btn.setFixedSize(32, 32)
        btn.setCursor(QtCore.Qt.PointingHandCursor)

        # Store references to the three icons
        btn._inactive_icon = QtGui.QIcon("assets/svg/send_inactive_icon.svg")
        btn._hover_icon = QtGui.QIcon("assets/svg/send_inactive_icon.svg")
        btn._active_icon = QtGui.QIcon("assets/svg/send_active_icon.svg")

        # Start with inactive icon
        btn.setIcon(btn._inactive_icon)
        btn.setIconSize(QtCore.QSize(17, 17))

        # Track hover state
        btn._is_hovering = False

        # Override enter/leave events for hover detection
        original_enter = btn.enterEvent
        original_leave = btn.leaveEvent

        def enter_event(event):
            btn._is_hovering = True
            self._update_send_button_icon(btn)
            if original_enter:
                original_enter(event)

        def leave_event(event):
            btn._is_hovering = False
            self._update_send_button_icon(btn)
            if original_leave:
                original_leave(event)

        btn.enterEvent = enter_event
        btn.leaveEvent = leave_event

        # btn.setStyleSheet("""
        #     QPushButton {
        #         border-radius: 18px;
        #         background-color: #E9ECEF;             /* Inactive state - light gray */
        #         border: none;                          /* Remove all borders/outlines */
        #         outline: none;                         /* Remove focus outline */
        #     }
        #     QPushButton:hover {
        #         background-color: #DBE0E4;             /* Hover state - slightly darker gray */
        #     }
        #     QPushButton:checked {
        #         background-color: #000000;             /* Active state - black */
        #     }
        #     QPushButton:checked:hover {
        #         background-color: #000000;             /* Active + hover state - keep black */
        #     }
        #     QPushButton:focus {
        #         outline: none;                         /* Remove focus outline */
        #     }
        # """)
        #
        # # Only show the button if AI Advisor is enabled in policy
        # btn.setVisible(self.ai_advisor_enabled)

        return btn

    def _create_action_buttons(self) -> QtWidgets.QWidget:
        """Create the bottom action buttons with fixed height"""
        container = QtWidgets.QWidget()
        container.setObjectName("actionContainer")
        container.setFixedHeight(self.action_buttons_height)

        layout = QtWidgets.QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        # layout.setSpacing(6)

        # Action buttons
        self.analyze_button = QtWidgets.QPushButton("Analyze field")
        self.analyze_button.setCursor(QtCore.Qt.PointingHandCursor)
        self.analyze_button.setObjectName("actionButton")

        self.best_practices_button = QtWidgets.QPushButton("Best Practices")
        self.best_practices_button.setCursor(QtCore.Qt.PointingHandCursor)
        self.best_practices_button.setObjectName("actionButton")

        self.toggle_fields_button = QtWidgets.QPushButton("Toggle Fields")
        self.toggle_fields_button.setCursor(QtCore.Qt.PointingHandCursor)
        self.toggle_fields_button.setObjectName("actionButton")

        layout.addWidget(self.analyze_button)
        layout.addWidget(self.best_practices_button)
        layout.addWidget(self.toggle_fields_button)
        layout.addStretch()

        return container

    def _setup_styling(self):
        """Apply styling to the chat input widget"""
        self.setStyleSheet("""
            #chatInputWidget {
                background-color: #2A2A2A;
            }

            #inputContainer {
                background-color: #404040;
                border-radius: 12px;
                margin-bottom: 4px;
            }

            #textInput {
                background-color: transparent;
                border: none;
                border-radius: 8px;
                padding: 4px 4px;
                color: #FFFFFF;
                font-size: 14px;
            }

            #textInput:focus {
                background-color:transparent;
                outline: none;
            }

            #chatButton {
                background-color: #555555;
                border: 1px solid #666666;
                border-radius: 4px;
                color: #FFFFFF;
                font-size: 24px;
                padding: 0px;
                font-family: "Arial", sans-serif;
                text-align: center;
            }

            #chatButton:hover {
                background-color: #8B7DD8;
            }
            
            #sendButton {
                background-color: #555555;
                border: 1px solid #666666;
                border-radius: 4px;
                color: #FFFFFF;
                font-size: 24px;
                padding: 0px;
                font-family: "Arial", sans-serif;
                text-align: center;
            }

            #sendButton:hover {
                background-color: #8B7DD8;
            }

            #actionContainer {
                background-color: transparent;
            }

            #actionButton {
                background-color: #404040;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px 6px;
                color: #FFFFFF;
                font-size: 12px;
            }

            #actionButton:hover {
                background-color: #8B7DD8;
            }
        """)

    def _on_send_message(self):
        """Handle sending a message"""
        text = self.text_input.text().strip()
        if text:
            print(f"Message sent: {text}")
            self.text_input.clear()


