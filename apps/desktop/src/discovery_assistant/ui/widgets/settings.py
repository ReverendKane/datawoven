from PySide6 import QtWidgets, QtCore, QtGui
from discovery_assistant.ui.widgets.rounded_container import RoundedContainer
from discovery_assistant.baselogger import logging

_LOGGER = logging.getLogger("DISCOVERY.ui.widgets.settings")


class SettingsWidget(QtWidgets.QWidget):
    """
    Right-rail Settings card (summary view only):
      - Header row: 'Settings' (left) + black 'Edit' button (right)
      - Two outlined groups: Organization (locked) and Personal
      - Plain rows (label left, muted value right). Editing happens in the full Preferences window.
    """
    editRequested = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        card = RoundedContainer(self)
        card_layout = card.layout()
        card_layout.setSpacing(12)

        # ---------------- Header row ----------------
        header = QtWidgets.QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)

        title = QtWidgets.QLabel("Settings")
        title.setStyleSheet("font-size:14px; font-weight:600; color:#0F172A;")
        header.addWidget(title, 0, QtCore.Qt.AlignLeft)

        header.addStretch(1)

        edit_btn = QtWidgets.QPushButton("Edit")
        edit_btn.setCursor(QtCore.Qt.PointingHandCursor)
        edit_btn.clicked.connect(self.editRequested.emit)
        edit_btn.setStyleSheet("""
            QPushButton {
                background: #111827;  /* near-black */
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding: 3px 6px;
                font-weight: 600;
            }
            QPushButton:hover { background: #0B1220; }
            QPushButton:pressed { background: #090f1a; }
        """)
        header.addWidget(edit_btn, 0, QtCore.Qt.AlignRight)

        card_layout.addLayout(header)

        # ---------------- Personal (outlined) ----------------
        self.personal_group = _OutlinedGroup(title="Personal", locked=False,
                                             tooltip="Your device-level settings. Some limits may come from policy.")
        self.personal_group.add_row("Autosave", "On")
        self.personal_group.add_row("Autosave interval", "120 s")
        self.personal_group.add_row("App Lock (this device)", "Status: Off")
        card_layout.addWidget(self.personal_group)

        # ---------------- Organization (outlined) ----------------
        self.org_group = _OutlinedGroup(title="Organization", locked=True,
                                        tooltip="Set by your organization.")
        # Example placeholders; replace via apply_policy()
        self.org_group.add_row("Screenshots", "Allowed")
        self.org_group.add_row("Redaction review", "Required")
        self.org_group.add_row("Export gate", "60%")
        self.org_group.add_row("Required sections", "2")
        self.org_group.add_row("Cloud submit", "On")
        self.org_group.add_row("Auto-delete after upload", "On")
        self.org_group.add_row("Retention", "30 days")
        self.org_group.add_row("Export protection", "PDF pwd + ZIP AES-256")
        self.org_group.add_row("PII", "Mask on screen • Redact in exports")
        card_layout.addWidget(self.org_group)

        card_layout.addStretch(1)
        outer.addWidget(card)

    # --------- Public API ---------
    def apply_policy(self, policy_summary: dict):
        """Update Organization group from dict of label -> value."""
        self.org_group.clear_rows()
        for k, v in policy_summary.items():
            self.org_group.add_row(k, v)

    def set_personal(self, autosave_on: bool, interval_label: str, lock_status: str):
        """Update Personal group summary."""
        self.personal_group.clear_rows()
        self.personal_group.add_row("Autosave", "On" if autosave_on else "Off")
        self.personal_group.add_row("Autosave interval", interval_label)
        self.personal_group.add_row("App Lock (this device)", f"Status: {lock_status}")


# ---------------- Helpers ----------------

class _OutlinedGroup(QtWidgets.QWidget):
    """
    Outlined group box with a minimal header (title + optional lock + info tooltip)
    and a vertical list of plain key/value rows.
    """
    def __init__(self, title: str, locked: bool = False, tooltip: str = ""):
        super().__init__()
        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)

        frame = QtWidgets.QFrame()
        frame.setObjectName("OutlinedGroupFrame")
        frame.setStyleSheet("""
            #OutlinedGroupFrame {
                border: 1px solid #E5E7EB;    /* thin light gray outline */
                border-radius: 10px;
                background: transparent;
            }
        """)
        v.addWidget(frame)

        inner = QtWidgets.QVBoxLayout(frame)
        inner.setContentsMargins(12, 10, 12, 10)
        inner.setSpacing(6)

        # Header row inside the frame
        hdr = QtWidgets.QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 0)
        hdr.setSpacing(6)

        lbl = QtWidgets.QLabel(title)
        lbl.setStyleSheet("font-size:12px; font-weight:600; color:#0F172A;")
        hdr.addWidget(lbl)

        if locked:
            lock = QtWidgets.QLabel("🔒")
            lock.setToolTip("Admin-controlled")
            lock.setAccessibleName("Admin-controlled")
            lock.setStyleSheet("font-size:12px;")
            hdr.addWidget(lock)

        info = QtWidgets.QToolButton()
        info.setText("i")
        info.setCursor(QtCore.Qt.PointingHandCursor)
        info.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        info.setAutoRaise(True)
        if tooltip:
            info.setToolTip(tooltip)
        info.setFixedWidth(18)
        hdr.addWidget(info)

        hdr.addStretch(1)
        inner.addLayout(hdr)

        # List of rows
        self._rows_container = QtWidgets.QVBoxLayout()
        self._rows_container.setContentsMargins(0, 0, 0, 0)
        self._rows_container.setSpacing(4)
        inner.addLayout(self._rows_container)

    def clear_rows(self):
        while self._rows_container.count():
            item = self._rows_container.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def add_row(self, key: str, value: str):
        row = QtWidgets.QWidget()
        h = QtWidgets.QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)

        key_lbl = QtWidgets.QLabel(key)
        key_lbl.setStyleSheet("color:#0F172A;")
        h.addWidget(key_lbl, 0, QtCore.Qt.AlignLeft)

        h.addStretch(1)

        val_lbl = QtWidgets.QLabel(value)
        val_lbl.setStyleSheet("color:#64748B;")  # muted value
        val_lbl.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        h.addWidget(val_lbl, 0, QtCore.Qt.AlignRight)

        self._rows_container.addWidget(row)
