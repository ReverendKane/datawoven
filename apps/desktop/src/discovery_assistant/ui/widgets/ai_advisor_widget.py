from PySide6 import QtCore, QtGui, QtWidgets
import discovery_assistant.constants as constants
from typing import List, Dict
from .chat_input_widget import ChatInputWidget


class AIAdvisorWidget(QtWidgets.QWidget):
    """Main AI Advisor widget with tabbed interface and chat functionality"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("aiAdvisorWidget")
        self._setup_ui()
        self._setup_styling()

    def _setup_ui(self):
        """Create the main UI structure with overlay"""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(0)

        # Header
        self.header = self._create_header()
        main_layout.addWidget(self.header)

        # Tab buttons
        self.tab_buttons = self._create_tab_buttons()
        main_layout.addWidget(self.tab_buttons)

        # Chat area fills remaining space
        self.chat_area = self._create_chat_area()
        main_layout.addWidget(self.chat_area, 1)

        # Create ChatInputWidget as overlay (not in main layout)
        self.chat_input = ChatInputWidget(self)  # Pass self as parent for overlay positioning


    def resizeEvent(self, event):
        """Position the chat input as overlay with scrollbar clearance"""
        super().resizeEvent(event)
        if hasattr(self, 'chat_input'):
            self._position_chat_overlay()

    def _position_chat_overlay(self):
        """Position chat input as overlay at bottom with scrollbar clearance"""
        # Check if scrollbar is visible
        scrollbar_visible = self.scroll_area.verticalScrollBar().isVisible()
        scrollbar_width = 8 if scrollbar_visible else 0

        # Position the chat input widget at bottom
        overlay_height = self.chat_input.height()
        self.chat_input.setGeometry(
            8,  # x position
            self.height() - overlay_height - 8,  # y position
            self.width() - 16 - scrollbar_width,  # width (with scrollbar clearance)
            overlay_height  # height
        )

    def showEvent(self, event):
        """Handle initial positioning"""
        super().showEvent(event)
        QtCore.QTimer.singleShot(0, self._position_chat_overlay)

    def _create_header(self) -> QtWidgets.QWidget:
        """Create the header with AI ADVISOR title"""
        header = QtWidgets.QWidget()
        header.setObjectName("aiAdvisorHeader")
        header.setFixedHeight(35)

        layout = QtWidgets.QVBoxLayout(header)
        layout.setContentsMargins(12, 8, 12, 0)
        layout.setSpacing(5)

        # Title
        title = QtWidgets.QLabel("AI ADVISOR")
        title.setObjectName("aiAdvisorTitle")
        layout.addSpacing(-6)
        layout.addWidget(title)

        # Font setup
        family_name = None
        fid = QtGui.QFontDatabase.addApplicationFont(str(constants.FONT_MONTSERRAT_SEMIBOLD))
        if fid != -1:
            fams = QtGui.QFontDatabase.applicationFontFamilies(fid)
            if fams:
                family_name = fams[0]

        title_font = QtGui.QFont(family_name or "Segoe UI", 10)
        title_font.setWeight(QtGui.QFont.DemiBold)
        title_font.setHintingPreference(QtGui.QFont.PreferFullHinting)
        title.setFont(title_font)

        return header

    def _create_tab_buttons(self) -> QtWidgets.QWidget:
        """Create tab buttons"""
        tab_buttons = QtWidgets.QWidget()
        tab_buttons.setObjectName("aiAdvisorTabButtons")
        tab_buttons.setFixedHeight(38)

        layout = QtWidgets.QHBoxLayout(tab_buttons)
        layout.setContentsMargins(3, 0, 3, 0)
        layout.setSpacing(0)

        # Selected tab button
        self.selected_tab = QtWidgets.QPushButton("Selected")
        self.selected_tab.setObjectName("selectedTab")
        self.selected_tab.setCheckable(True)
        self.selected_tab.setChecked(True)
        self.selected_tab.setCursor(QtCore.Qt.PointingHandCursor)
        self.selected_tab.clicked.connect(lambda: self._switch_tab("selected"))

        # General tab button
        self.general_tab = QtWidgets.QPushButton("General")
        self.general_tab.setObjectName("generalTab")
        self.general_tab.setCheckable(True)
        self.general_tab.setCursor(QtCore.Qt.PointingHandCursor)
        self.general_tab.clicked.connect(lambda: self._switch_tab("general"))

        layout.addWidget(self.selected_tab, 1)
        layout.addWidget(self.general_tab, 1)

        return tab_buttons

    def _create_chat_area(self) -> QtWidgets.QWidget:
        """Create the scrollable chat message area"""
        chat_container = QtWidgets.QWidget()
        chat_container.setObjectName("chatContainer")

        layout = QtWidgets.QVBoxLayout(chat_container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Scroll area for messages
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setObjectName("chatScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)

        # Messages widget inside scroll area
        self.messages_widget = QtWidgets.QWidget()
        self.messages_widget.setObjectName("messagesWidget")
        self.messages_layout = QtWidgets.QVBoxLayout(self.messages_widget)
        self.messages_layout.setContentsMargins(16, 16, 16, 170)
        self.messages_layout.setSpacing(12)
        self.messages_layout.addStretch()

        self.scroll_area.setWidget(self.messages_widget)
        layout.addWidget(self.scroll_area)

        # Add sample messages
        # self._add_sample_messages()

        return chat_container

    def _add_sample_messages(self):
        """Add sample messages to demonstrate the interface"""
        # AI message
        ai_msg = self._create_message(
            "If you look at the purple context window, there are a few \"quick\" icon buttons that satisfy what you added as Input Area Enhancements- there actually IS an X, the three soundwaves (highlighted purple) are to indicate Lorem ipsum dolor sit amet, consectetur adipiscing.",
            is_user=False
        )
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, ai_msg)

        # User message
        user_msg = self._create_message(
            "What's Working Well:",
            is_user=True
        )
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, user_msg)

        # AI response
        ai_response = self._create_message(
            "The \"filler\" text we know today has been altered over the years (in fact \"Lorem\" isn't actually a Latin word. It is suggested that the reason that the text starts with \"Lorem\" is because there was a page break spanning the word \"Do-lorem\". If you a re looking for a translation of the text, it's meaningless. The original text talks about the pain and love involved in the pursuit of pleasure or something like that.",
            is_user=False
        )
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, ai_response)

    def _create_message(self, text: str, is_user: bool = False) -> QtWidgets.QWidget:
        """Create a message bubble widget"""
        message_widget = QtWidgets.QWidget()
        message_widget.setObjectName("messageWidget")

        layout = QtWidgets.QHBoxLayout(message_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        message_bubble = QtWidgets.QLabel(text)
        message_bubble.setWordWrap(True)
        message_bubble.setObjectName("userMessage" if is_user else "aiMessage")
        message_bubble.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)

        if is_user:
            layout.addStretch()
            layout.addWidget(message_bubble)
        else:
            layout.addWidget(message_bubble)
            layout.addStretch()

        return message_widget

    def _setup_styling(self):
        """Apply styling to the main widget - input styling now handled by ChatInputWidget"""
        self.setStyleSheet("""
            #aiAdvisorWidget {
                background-color: #2A2A2A;
                color: #FFFFFF;
                border-radius: 4px;
            }

            #aiAdvisorHeader {
                background-color: #8B7DD8;
                color: #FFFFFF;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }

            #aiAdvisorTitle {
                font-size: 14px;
                font-weight: bold;
                color: #FFFFFF;
            }

            #aiAdvisorTabButtons {
                background-color: #2A2A2A;
            }

            #selectedTab, #generalTab {
                background-color: rgba(255, 255, 255, 0.1);
                border: none;
                padding: 8px 16px;
                color: #FFFFFF;
                font-size: 12px;
                font-weight: normal;
            }

            #selectedTab:checked {
                background-color: #FFFFFF;
                color: #2A2A2A;
                font-weight: 500;
            }

            #generalTab:checked {
                background-color: #FFFFFF;
                color: #2A2A2A;
                font-weight: 500;
            }

            #selectedTab:hover:!checked, #generalTab:hover:!checked {
                background-color: rgba(255, 255, 255, 0.2);
            }

            #chatScrollArea {
                background-color: #2A2A2A;
                border: none;
            }

            #chatScrollArea QScrollBar:vertical {
                background: #2A2A2A;
                width: 8px;
                border: none;
                border-radius: 4px;
            }

            #chatScrollArea QScrollBar::handle:vertical {
                background: #555555;
                border-radius: 4px;
                min-height: 20px;
            }

            #chatScrollArea QScrollBar::handle:vertical:hover {
                background: #666666;
            }

            #chatScrollArea QScrollBar::add-line:vertical,
            #chatScrollArea QScrollBar::sub-line:vertical {
                height: 0px;
            }

            #chatScrollArea QScrollBar::add-page:vertical,
            #chatScrollArea QScrollBar::sub-page:vertical {
                background: none;
            }

            #messagesWidget {
                background-color: #2A2A2A;
            }

            #aiMessage {
                background-color: #3A3A3A;
                padding: 12px;
                border-radius: 8px;
                max-width: 300px;
                color: #FFFFFF;
                font-size: 13px;
                line-height: 1.4;
            }

            #userMessage {
                background-color: #8B7DD8;
                padding: 12px;
                border-radius: 8px;
                max-width: 300px;
                color: #FFFFFF;
                font-size: 13px;
                line-height: 1.4;
            }
        """)

    def _switch_tab(self, tab_name: str):
        """Handle tab switching"""
        if tab_name == "selected":
            self.selected_tab.setChecked(True)
            self.general_tab.setChecked(False)
        else:
            self.selected_tab.setChecked(False)
            self.general_tab.setChecked(True)

    def _on_send_message_from_input(self, text: str):
        """Handle message sent from ChatInputWidget"""
        # Add user message
        user_msg = self._create_message(text, is_user=True)
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, user_msg)

        # Scroll to bottom
        QtCore.QTimer.singleShot(100, self._scroll_to_bottom)

        # Simulate AI response after delay
        QtCore.QTimer.singleShot(2000, self._simulate_ai_response)

    def _simulate_ai_response(self):
        """Simulate an AI response"""
        ai_msg = self._create_message(
            "I understand your question. Let me analyze that for you...",
            is_user=False
        )
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, ai_msg)
        QtCore.QTimer.singleShot(100, self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        """Scroll chat area to bottom"""
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
