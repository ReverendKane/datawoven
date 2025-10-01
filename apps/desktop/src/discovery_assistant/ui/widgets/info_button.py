# info_button.py  (drop-in)
from PySide6 import QtCore, QtGui, QtWidgets

class InfoButton(QtWidgets.QToolButton):
    """
    Round 'i' icon button that supports off / hover / on states via images.
    Emits toggled(bool). Use setCheckable(True) to make it sticky.
    """
    toggled = QtCore.Signal(bool)  # re-emit for convenience

    def __init__(self, parent=None,
                 off_icon: QtGui.QIcon | None = None,
                 hover_icon: QtGui.QIcon | None = None,
                 on_icon: QtGui.QIcon | None = None,
                 size_px: int = 28):
        super().__init__(parent)
        self.setObjectName("InfoButton")
        self.setCheckable(True)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setAutoRaise(False)                 # keep flat, we'll style explicitly
        self.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
        self.setFocusPolicy(QtCore.Qt.NoFocus)   # avoid focus rect shifting visuals
        self.setAutoFillBackground(False)
        self.setFixedSize(size_px, size_px)
        self.setIconSize(QtCore.QSize(size_px - 8, size_px - 8))  # 4px padding each side

        # ---- enforce transparent, no-shift look for ALL states ----
        self.setStyleSheet(f"""
            QToolButton#InfoButton,
            QToolButton#InfoButton:hover,
            QToolButton#InfoButton:pressed,
            QToolButton#InfoButton:checked,
            QToolButton#InfoButton:checked:hover,
            QToolButton#InfoButton:!hover {{
                background: transparent;
                border: none;
                padding: 0;
                margin: 0;
            }}
            /* kill menu indicator spacing if style adds one */
            QToolButton#InfoButton::menu-indicator {{ image: none; width: 0; height: 0; }}
        """)

        # icons
        self._icon_off = off_icon or QtGui.QIcon()
        self._icon_hover = hover_icon or self._icon_off
        self._icon_on = on_icon or self._icon_off

        self._update_icon()
        self.toggled.connect(self._on_toggled)

    # ------- icon swapping -------
    def enterEvent(self, e: QtGui.QEnterEvent) -> None:
        if not self.isChecked():
            self.setIcon(self._icon_hover)
        return super().enterEvent(e)

    def leaveEvent(self, e: QtCore.QEvent) -> None:
        if not self.isChecked():
            self.setIcon(self._icon_off)
        return super().leaveEvent(e)

    def _on_toggled(self, checked: bool) -> None:
        self._update_icon()

    def _update_icon(self):
        self.setIcon(self._icon_on if self.isChecked() else self._icon_off)

    # allow external hookup to Qt's toggled
    def setChecked(self, checked: bool) -> None:  # noqa: F811 (override)
        super().setChecked(checked)
        self._update_icon()
