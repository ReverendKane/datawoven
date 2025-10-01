from PySide6 import QtCore, QtGui, QtWidgets


class QuickMenuWidget(QtWidgets.QWidget):
    """Quick menu with export, dictate, and clear buttons"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("quickMenuWidget")
        self.setFixedHeight(32)  # Match button height

        self._setup_ui()
        self._setup_styling()

    def _setup_ui(self):
        """Create the layout with three icon buttons in a gray outlined container"""
        # Main layout for the widget
        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create container with gray outline
        container = QtWidgets.QWidget()
        container.setObjectName("quickMenuContainer")

        # Layout inside the container
        layout = QtWidgets.QHBoxLayout(container)
        layout.setContentsMargins(6, 4, 6, 4)  # Internal padding
        layout.setSpacing(4)

        # Export button (hover only) - 12x17
        self.export_btn = self._create_icon_button(
            "export",
            ":/export_inactive_icon.svg",
            ":/export_hover_icon.svg",
            icon_size=(12, 17)
        )

        # Dictate button (toggleable) - 10x14
        self.dictate_btn = self._create_icon_button(
            "dictate",
            ":/dictate_inactive_icon.svg",
            ":/dictate_hover_icon.svg",
            ":/dictate_active_icon.svg",
            checkable=True,
            icon_size=(10, 14)
        )

        # Clear button (hover only) - 11x13
        self.clear_btn = self._create_icon_button(
            "clear",
            ":/clear_inactive_icon.svg",
            ":/clear_hover_icon.svg",
            icon_size=(11, 13)
        )

        layout.addWidget(self.export_btn)
        layout.addWidget(self.dictate_btn)
        layout.addWidget(self.clear_btn)

        main_layout.addWidget(container)
        main_layout.addSpacing(15)

    def _create_icon_button(self, name, inactive_icon, hover_icon, active_icon=None, checkable=False,
                            icon_size=(20, 20)):
        """Create an icon button with hover states"""
        btn = QtWidgets.QPushButton()
        btn.setObjectName(f"{name}Button")
        btn.setFixedSize(24, 24)  # Smaller button size to fit in container
        btn.setCursor(QtCore.Qt.PointingHandCursor)
        btn.setCheckable(checkable)

        # Store icon references
        btn._inactive_icon = QtGui.QIcon(inactive_icon)
        btn._hover_icon = QtGui.QIcon(hover_icon)
        if active_icon:
            btn._active_icon = QtGui.QIcon(active_icon)

        # Set initial icon with custom size
        btn.setIcon(btn._inactive_icon)
        btn.setIconSize(QtCore.QSize(icon_size[0], icon_size[1]))

        # Track hover state
        btn._is_hovering = False

        # Override enter/leave events for hover detection
        original_enter = btn.enterEvent
        original_leave = btn.leaveEvent

        def enter_event(event):
            btn._is_hovering = True
            self._update_button_icon(btn)
            if original_enter:
                original_enter(event)

        def leave_event(event):
            btn._is_hovering = False
            self._update_button_icon(btn)
            if original_leave:
                original_leave(event)

        btn.enterEvent = enter_event
        btn.leaveEvent = leave_event

        # Handle clicked for checkable buttons
        if checkable:
            btn.clicked.connect(lambda: self._update_button_icon(btn))

        return btn

    def _update_button_icon(self, btn):
        """Update button icon based on current state"""
        if btn.isCheckable() and btn.isChecked():
            # Active state (for dictate button)
            btn.setIcon(btn._active_icon)
        elif btn._is_hovering:
            # Hover state
            btn.setIcon(btn._hover_icon)
        else:
            # Inactive state
            btn.setIcon(btn._inactive_icon)

    def _setup_styling(self):
        """Apply styling - gray outlined container with transparent buttons"""
        self.setStyleSheet("""
            #quickMenuWidget {
                background-color: transparent;
            }

            #quickMenuContainer {
                background-color: #333333;
                border: 1px solid #3E3E3E;
                border-radius: 4px;
            }

            #exportButton, #dictateButton, #clearButton {
                background-color: transparent;
                border: none;
                outline: none;
                padding: 0px;
            }

            #exportButton:hover, #dictateButton:hover, #clearButton:hover {
                background-color: transparent;
            }

            #exportButton:pressed, #dictateButton:pressed, #clearButton:pressed {
                background-color: transparent;
            }

            #exportButton:focus, #dictateButton:focus, #clearButton:focus {
                outline: none;
                border: none;
            }

            #dictateButton:checked {
                background-color: transparent;
            }
        """)

    # Public methods to access button states
    def is_dictate_active(self):
        """Check if dictate button is in active state"""
        return self.dictate_btn.isChecked()

    def set_dictate_active(self, active):
        """Set dictate button active state"""
        self.dictate_btn.setChecked(active)
        self._update_button_icon(self.dictate_btn)

    def connect_export_clicked(self, callback):
        """Connect export button clicked signal"""
        self.export_btn.clicked.connect(callback)

    def connect_dictate_toggled(self, callback):
        """Connect dictate button toggled signal"""
        self.dictate_btn.toggled.connect(callback)

    def connect_clear_clicked(self, callback):
        """Connect clear button clicked signal"""
        self.clear_btn.clicked.connect(callback)
