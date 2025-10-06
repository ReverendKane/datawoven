"""
Instructions Tab - Always first tab in navigation
Displays boilerplate introduction + admin messages based on policy settings
"""

from typing import Optional
from pathlib import Path
from PySide6 import QtWidgets, QtCore, QtGui
from discovery_assistant.baselogger import logging
from discovery_assistant.ui.widgets.info import InfoSection
from discovery_assistant.ui.info_text import INSTRUCTIONS_INFO

_LOGGER = logging.getLogger("DISCOVERY.ui.tabs.instructions_tab")

# Boilerplate text options
BOILERPLATE_TEXT = {
    "formal": (
        "This Discovery Assistant is designed to identify opportunities where AI and automation "
        "can improve your daily work. By documenting your processes, pain points, and data sources, "
        "you're helping us build tailored solutions—from AI-powered search tools trained on your "
        "company data to intelligent agents that automate repetitive tasks. Complete, accurate "
        "responses lead to better recommendations and faster implementation."
    ),
    "conversational": (
        "Think of this tool as your first step toward getting AI help with the work that bogs you down. "
        "We're looking for the processes that eat up your time, the frustrations that slow you down, "
        "and the data scattered across different systems. Your input helps us create custom solutions—"
        "whether that's an AI assistant that knows your company's information inside and out, automated "
        "workflows that handle routine tasks, or a smart document system that finds what you need instantly."
    ),
    "concise": (
        "This tool captures how you work today to identify where AI can help tomorrow. Document your "
        "processes, pain points, and data sources honestly—these insights drive real solutions like "
        "AI search trained on your data, task automation agents, and intelligent document retrieval. "
        "The more complete your responses, the better the recommendations."
    )
}


class InstructionsTab(QtWidgets.QWidget):
    """First tab displaying introduction and administrative messages"""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None, policy_enforcer=None) -> None:
        super().__init__(parent)
        self._policy_enforcer = policy_enforcer
        self._policy = policy_enforcer._policy if policy_enforcer else None

        _LOGGER.info("InstructionsTab initialized")
        self._setup_ui()

        # Start with stealth scrollbar (hidden)
        self._set_scrollbar_stealth(True)

    def _setup_ui(self):
        """Build the instructions interface"""
        # Main scroll area
        scroller = QtWidgets.QScrollArea(self)
        scroller.setObjectName("InstructionsScroll")
        scroller.setWidgetResizable(True)
        scroller.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroller.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        scroller.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        # Store reference for scrollbar control
        self._scroller = scroller

        root = QtWidgets.QWidget()
        root.setStyleSheet("background:#F3F4F6;")
        scroller.setWidget(root)

        page = QtWidgets.QVBoxLayout(root)
        page.setContentsMargins(12, 10, 12, 12)
        page.setSpacing(12)

        # Main card
        card = QtWidgets.QFrame(root)
        card.setObjectName("InstructionsCard")
        card.setStyleSheet("""
            QFrame#InstructionsCard {
                background:#FFFFFF;
                border:1px solid #E5E7EB;
                border-radius:12px;
            }
        """)
        page.addWidget(card)

        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(10)

        # Header
        section = InfoSection(
            title="Welcome to Discovery Assistant",
            subtitle="Identifying AI and Automation Opportunities",
            info_html=INSTRUCTIONS_INFO,
            icon_size_px=28,
            parent=card,
        )
        card_layout.addWidget(section)
        section.bind_scrollarea(self._scroller)
        section.toggled.connect(lambda open_: self._set_scrollbar_stealth(not open_))

        # Boilerplate introduction
        self._add_boilerplate(card_layout)

        # Admin messages (if multi-user mode)
        self._add_admin_messages(card_layout)

        # External wiki link
        # self._add_wiki_link(card_layout)

        # Get started button
        self._add_get_started_button(card_layout)

        card_layout.addStretch(1)

        # Mount scroller
        root_layout = QtWidgets.QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(scroller)


    def _add_boilerplate(self, layout: QtWidgets.QVBoxLayout):
        """Add boilerplate introduction text"""
        # Get tone from policy
        tone = "formal"  # Default
        if self._policy:
            admin_instructions = self._policy.get("data", {}).get("administrative_instructions", {})
            tone = admin_instructions.get("instruction_tone", "formal")

        boilerplate_text = BOILERPLATE_TEXT.get(tone, BOILERPLATE_TEXT["formal"])

        intro_frame = QtWidgets.QFrame()
        intro_frame.setStyleSheet("""
            QFrame {
                background: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 20px;
            }
        """)
        intro_layout = QtWidgets.QVBoxLayout(intro_frame)
        intro_layout.setContentsMargins(20, 20, 20, 20)

        intro_label = QtWidgets.QLabel(boilerplate_text)
        intro_label.setWordWrap(True)
        intro_label.setStyleSheet("""
            border: none;
            font-size: 15px;
            color: #334155;
            line-height: 1.6;
        """)
        intro_layout.addWidget(intro_label)

        layout.addWidget(intro_frame)

    def _add_admin_messages(self, layout: QtWidgets.QVBoxLayout):
        """Add admin messages section if multi-user mode"""
        if not self._policy:
            return

        # Check if multi-user mode
        meta = self._policy.get("meta", {})
        multi_user = meta.get("multi_user_mode", True)

        if not multi_user:
            return  # Skip admin messages in solo mode

        # Get messages
        admin_instructions = self._policy.get("data", {}).get("administrative_instructions", {})
        messages = admin_instructions.get("messages", [])

        if not messages:
            return  # No messages to display

        # Section header
        messages_header = QtWidgets.QLabel("Important Information from Your Administrator")
        messages_header.setStyleSheet("""
            font-size: 20px;
            font-weight: 600;
            color: #0F172A;
            margin-top: 10px;
            margin-bottom: 10px;
        """)
        layout.addWidget(messages_header)

        # Display each message (excluding critical ones - those are in modal)
        for msg in messages:
            if msg.get("priority") == "critical":
                continue  # Critical messages shown in modal, not here

            self._add_message_card(layout, msg)

    def _add_message_card(self, layout: QtWidgets.QVBoxLayout, message: dict):
        """Add a single message card"""
        priority = message.get("priority", "informational")
        msg_type = message.get("type", "reminder")
        title = message.get("title", "")
        content = message.get("content", "")

        # Color coding by priority
        border_colors = {
            "important": "#3B82F6",
            "informational": "#6B7280"
        }
        border_color = border_colors.get(priority, "#6B7280")

        msg_frame = QtWidgets.QFrame()
        msg_frame.setStyleSheet(f"""
            QFrame {{
                background: #FFFFFF;
                border-left: 4px solid {border_color};
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                padding: 16px;
            }}
        """)

        msg_layout = QtWidgets.QVBoxLayout(msg_frame)
        msg_layout.setContentsMargins(16, 16, 16, 16)
        msg_layout.setSpacing(10)

        # Title
        title_label = QtWidgets.QLabel(title)
        title_label.setStyleSheet("""
            font-size: 16px;
            font-weight: 600;
            color: #0F172A;
        """)
        title_label.setWordWrap(True)
        msg_layout.addWidget(title_label)

        # Content
        content_label = QtWidgets.QLabel(content)
        content_label.setWordWrap(True)
        content_label.setStyleSheet("""
            font-size: 14px;
            color: #475569;
            line-height: 1.5;
        """)
        msg_layout.addWidget(content_label)

        layout.addWidget(msg_frame)

    def _add_wiki_link(self, layout: QtWidgets.QVBoxLayout):
        """Add external wiki link"""
        wiki_frame = QtWidgets.QFrame()
        wiki_frame.setStyleSheet("""
            QFrame {
                background: white;
                # border: 1px solid #DBEAFE;
                # border-radius: 6px;
                # padding: 16px;
            }
        """)

        wiki_layout = QtWidgets.QHBoxLayout(wiki_frame)
        wiki_layout.setContentsMargins(16, 16, 16, 16)

        info_label = QtWidgets.QLabel("For detailed guidance and best practices:")
        info_label.setStyleSheet("font-size: 14px; color: #1E40AF; border: none;")

        wiki_link = QtWidgets.QLabel(
            '<a href="https://yourwebsite.com/docs" style="color: #2563EB; border: none; text-decoration: none;">Visit our Complete Documentation →</a>')
        wiki_link.setOpenExternalLinks(True)
        wiki_link.setStyleSheet("font-size: 14px; border: none; font-weight: 500;")

        wiki_layout.addWidget(info_label)
        wiki_layout.addWidget(wiki_link)
        wiki_layout.addStretch()

        layout.addWidget(wiki_frame)

    def _add_get_started_button(self, layout: QtWidgets.QVBoxLayout):
        """Add get started button"""
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()

        get_started_btn = QtWidgets.QPushButton("Get Started →")
        get_started_btn.setObjectName("getStartedBtn")
        get_started_btn.setCursor(QtCore.Qt.PointingHandCursor)
        get_started_btn.setStyleSheet("""
            QPushButton#getStartedBtn {
                background: #0F172A;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 12px 32px;
                font-size: 16px;
                font-weight: 600;
            }
            QPushButton#getStartedBtn:hover {
                background: #1E293B;
            }
        """)
        get_started_btn.clicked.connect(self._advance_to_respondent_tab)

        button_layout.addWidget(get_started_btn)
        button_layout.addStretch()

        layout.addLayout(button_layout)

    def _advance_to_respondent_tab(self):
        """Navigate to Respondent tab when Get Started clicked"""
        # Find parent ContentContainer
        parent = self.parent()
        while parent and not hasattr(parent, 'navbar'):
            parent = parent.parent()

        if parent and hasattr(parent, 'navbar'):
            # Get the navigation buttons from the navbar
            navbar = parent.navbar

            # Find and trigger the Respondent button directly
            # This ensures the navbar's internal state updates
            for button in navbar.findChildren(QtWidgets.QPushButton):
                if button.text() == "Respondent":
                    button.click()  # Simulates user clicking the button
                    break

    def clear_fields(self) -> None:
        """No fields to clear in instructions tab"""
        pass

    def _set_scrollbar_stealth(self, stealth: bool):
        """Apply stealth or visible scrollbar styling"""
        if not hasattr(self, '_scroller'):
            return

        sb = self._scroller.verticalScrollBar()
        if sb is None:
            return

        if stealth:
            # Stealth: match page background (#F3F4F6)
            sb.setStyleSheet("""
                QScrollBar:vertical {
                    background: #F3F4F6;
                    width: 12px;
                    margin: 8px 2px 8px 0;
                }
                QScrollBar::handle:vertical {
                    background: #F3F4F6;
                    border-radius: 6px;
                    min-height: 24px;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; width: 0; }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: #F3F4F6; }
            """)
        else:
            # Visible: gray handle
            sb.setStyleSheet("""
                QScrollBar:vertical {
                    background: transparent;
                    width: 12px;
                    margin: 8px 2px 8px 0;
                }
                QScrollBar::handle:vertical {
                    background: #D1D5DB;
                    border-radius: 6px;
                    min-height: 24px;
                }
                QScrollBar::handle:vertical:hover { background: #9CA3AF; }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; width: 0; }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
            """)

        sb.style().unpolish(sb)
        sb.style().polish(sb)
        sb.update()
