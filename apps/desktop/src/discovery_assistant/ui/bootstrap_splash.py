from pathlib import Path
from PySide6 import QtCore, QtGui, QtWidgets

class BootstrapSplash(QtWidgets.QWidget):
    configDropped = QtCore.Signal(str)          # emits absolute path to dropped file
    adminPasswordEntered = QtCore.Signal(str)   # emits the entered password

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setWindowTitle("Discovery Assistant — Setup")
        self.setMinimumSize(720, 420)
        self.resize(900, 520)
        self.setObjectName("root")
        # Base style now includes a transparent 5px border that we toggle to white on drag-over
        self.setStyleSheet("""
            QWidget#root { background: #000; border: 5px solid transparent; border-radius: 14px; }
            QLabel#appname { color: #fff; font-size: 11pt; font-weight: 600; font-family: 'Montserrat'; }
            QLabel#title { color: #fff; font-size: 22px; font-weight: 600; }
            QLabel#subtitle { color: #9CA3AF; font-size: 14px; }
            QLineEdit#pwd { background:#111; color:#fff; border:1px solid #333;
                            border-radius:8px; padding:10px; }
            QPushButton#admin { background:#1A415E; color:#fff; border:1px solid #374151;
                                border-radius:10px; padding:10px 14px; }
            QPushButton#admin:hover { background:#0BE5F5; color:#000; }
        """)

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(32, 32, 32, 32)

        center = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(center)
        v.setSpacing(13)
        v.setAlignment(QtCore.Qt.AlignCenter)

        # --- Logo from assets (SVG) ---
        from PySide6.QtSvgWidgets import QSvgWidget  # keep your in-function import
        # assets_root = Path(__file__).resolve().parents[1] / "assets" / "images"
        # svg_path = assets_root / "splash_logo.svg"
        svg = QSvgWidget(":/splash_logo.svg")
        if svg:
            svg.setFixedWidth(100)  # your width cap
            svg.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
            v.addWidget(svg, 0, QtCore.Qt.AlignHCenter)
        else:
            # Optional: fallback text so you can see when the path is wrong
            missing = QtWidgets.QLabel(f"Logo missing: {svg_path}")
            missing.setStyleSheet("color:#ef4444;")
            missing.setAlignment(QtCore.Qt.AlignCenter)
            v.addWidget(missing)

        # App name under logo
        appname = QtWidgets.QLabel("DISCOVERY ASSISTANT")
        appname.setObjectName("appname")
        appname.setAlignment(QtCore.Qt.AlignCenter)
        v.addWidget(appname)
        v.addSpacing(20)

        # Instructions
        t = QtWidgets.QLabel("Please drag and drop your configuration file onto this window")
        t.setObjectName("title")
        t.setAlignment(QtCore.Qt.AlignCenter)
        v.addWidget(t)

        st = QtWidgets.QLabel("…or enter the admin password to start Administrative Setup")
        st.setObjectName("subtitle")
        st.setAlignment(QtCore.Qt.AlignCenter)
        v.addWidget(st)

        # Password row
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(12)
        self.pwd = QtWidgets.QLineEdit(objectName="pwd")
        self.pwd.setEchoMode(QtWidgets.QLineEdit.Password)
        self.pwd.setPlaceholderText("Admin password")
        self.pwd.returnPressed.connect(self._emit_pwd)
        btn = QtWidgets.QPushButton("Enter Admin Setup", objectName="admin")
        btn.clicked.connect(self._emit_pwd)
        row.addWidget(self.pwd, 1)
        row.addWidget(btn, 0)
        v.addLayout(row)

        outer.addStretch(1)
        outer.addWidget(center)
        outer.addStretch(1)

        hint = QtWidgets.QLabel("Press Esc to quit")
        hint.setStyleSheet("color:#4B5563; font-size:12px;")
        hint.setAlignment(QtCore.Qt.AlignRight)
        outer.addWidget(hint)

        # state for border highlight
        self._drag_active = False

    # ----- helpers -----
    def _set_drag_highlight(self, on: bool):
        if on == self._drag_active:
            return
        self._drag_active = on
        base = self.styleSheet()
        if on:
            self.setStyleSheet(base.replace("border: 5px solid transparent;", "border: 5px solid #FFFFFF;"))
        else:
            self.setStyleSheet(base.replace("border: 5px solid #FFFFFF;", "border: 5px solid transparent;"))

    def _emit_pwd(self):
        txt = self.pwd.text().strip()
        if txt:
            self.adminPasswordEntered.emit(txt)

    # ----- Drag & drop: whole-window target with .pol filtering -----
    @staticmethod
    def _is_acceptable_urls(mimedata: QtCore.QMimeData) -> bool:
        if not mimedata.hasUrls():
            return False
        for u in mimedata.urls():
            if u.isLocalFile() and u.toLocalFile().lower().endswith(".pol"):
                return True
        return False

    def dragEnterEvent(self, e: QtGui.QDragEnterEvent) -> None:
        if self._is_acceptable_urls(e.mimeData()):
            self._set_drag_highlight(True)
            e.acceptProposedAction()
        else:
            self._set_drag_highlight(False)
            e.ignore()

    def dragMoveEvent(self, e: QtGui.QDragMoveEvent) -> None:
        if self._is_acceptable_urls(e.mimeData()):
            if not self._drag_active:
                self._set_drag_highlight(True)
            e.acceptProposedAction()
        else:
            if self._drag_active:
                self._set_drag_highlight(False)
            e.ignore()

    def dragLeaveEvent(self, e: QtGui.QDragLeaveEvent) -> None:
        self._set_drag_highlight(False)
        e.accept()

    def dropEvent(self, e: QtGui.QDropEvent) -> None:
        self._set_drag_highlight(False)
        for u in e.mimeData().urls():
            if u.isLocalFile() and u.toLocalFile().lower().endswith(".pol"):
                self.configDropped.emit(u.toLocalFile())
                break

    def keyPressEvent(self, ev: QtGui.QKeyEvent) -> None:
        if ev.key() == QtCore.Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(ev)
