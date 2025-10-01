# discovery_assistant/ui/widgets/info_section.py
from pathlib import Path
from PySide6 import QtCore, QtGui, QtWidgets

# Reuse your existing button (with tooltip + follow behavior)
from discovery_assistant.ui.widgets.info_button import InfoButton

def _assets_dir() -> Path:
    # discovery_assistant/ui/widgets/ -> up 2 -> assets/images
    return Path(__file__).resolve().parents[2] / "assets" / "images"

def _default_icons():
    d = _assets_dir()
    return (
        QtGui.QIcon(str(d / "info_off.svg")),
        QtGui.QIcon(str(d / "info_hover.svg")),
        QtGui.QIcon(str(d / "info_on.svg")),
    )

class InfoSection(QtWidgets.QFrame):
    """
    A reusable 'info section' block:
      - Header (title, subtitle, InfoButton)
      - Collapsible info panel (rich text)
      - Exposes `content_layout` for consumer content
      - Optional scrollbar-stealth binding via `bind_scrollarea()`
    """
    toggled = QtCore.Signal(bool)

    def __init__(
        self,
        title: str,
        subtitle: str,
        info_html: str,
        *,
        off_icon: QtGui.QIcon | None = None,
        hover_icon: QtGui.QIcon | None = None,
        on_icon: QtGui.QIcon | None = None,
        icon_size_px: int = 28,
        parent: QtWidgets.QWidget | None = None,
    ):
        super().__init__(parent)
        self.setObjectName("InfoSection")
        self.setStyleSheet("""
            QFrame#InfoSection { background: transparent; border: none; }  /* was white + 1px border */
            QFrame#InfoSection QLabel { background: transparent; }
        """)

        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)

        # --- Header (title/subtitle + info button)
        hdr = QtWidgets.QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 0)
        hdr.setSpacing(8)

        title_col = QtWidgets.QVBoxLayout()
        title_col.setContentsMargins(0, 0, 0, 0)
        title_col.setSpacing(2)

        lbl_title = QtWidgets.QLabel(title)
        lbl_title.setStyleSheet("font-size:16px; font-weight:600; color:#0F172A;")
        lbl_sub = QtWidgets.QLabel(subtitle)
        lbl_sub.setStyleSheet("font-size:12px; color:#64748B;")
        lbl_sub.setWordWrap(True)
        title_col.addWidget(lbl_title)
        title_col.addWidget(lbl_sub)

        hdr.addLayout(title_col, 1)

        if not (off_icon and hover_icon and on_icon):
            off_icon, hover_icon, on_icon = _default_icons()

        self.info_btn = InfoButton(parent=self, off_icon=off_icon, hover_icon=hover_icon, on_icon=on_icon, size_px=icon_size_px)
        hdr.addWidget(self.info_btn, 0, QtCore.Qt.AlignTop)

        v.addLayout(hdr)
        v.addSpacing(8)

        # --- Collapsible info panel
        self.info_panel = QtWidgets.QFrame(self)
        self.info_panel.setObjectName("InfoPanel")
        self.info_panel.setVisible(False)
        self.info_panel.setStyleSheet("""
            QFrame#InfoPanel { background:#F9FAFB; border:1px solid #E5E7EB; border-radius:12px; }
            QFrame#InfoPanel QLabel { color:#374151; font-size:13px; }
        """)
        pnl = QtWidgets.QVBoxLayout(self.info_panel)
        pnl.setContentsMargins(12, 10, 12, 12)
        pnl.setSpacing(6)

        info_lbl = QtWidgets.QLabel(self.info_panel)
        info_lbl.setWordWrap(True)
        info_lbl.setTextFormat(QtCore.Qt.RichText)
        info_lbl.setText(info_html)
        pnl.addWidget(info_lbl)

        v.addWidget(self.info_panel)

        # --- Consumer content goes here
        self.content_layout = QtWidgets.QVBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(10)
        v.addLayout(self.content_layout)

        # wiring
        self.info_btn.toggled.connect(self.info_panel.setVisible)
        self.info_btn.toggled.connect(self.toggled)

        # optional (set via bind_scrollarea)
        self._bound_scrollbar: QtWidgets.QScrollBar | None = None

    # -------- Optional: bind to a scroll area to toggle 'stealth' scrollbar
    def bind_scrollarea(self, scrollarea: QtWidgets.QScrollArea):
        if not isinstance(scrollarea, QtWidgets.QScrollArea):
            return
        self._bound_scrollbar = scrollarea.verticalScrollBar()
        self.toggled.connect(lambda checked: self._set_scrollbar_stealth(not checked))
        # start hidden panel -> stealth on
        self._set_scrollbar_stealth(True)

    def _set_scrollbar_stealth(self, stealth: bool):
        sb = self._bound_scrollbar
        if not sb:
            return
        if stealth:
            sb.setStyleSheet("""
                QScrollBar:vertical {
                    background: #F3F4F6; width: 12px; margin: 8px 2px 8px 0;
                }
                QScrollBar::handle:vertical {
                    background: #F3F4F6; border-radius: 6px; min-height: 24px;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; width: 0; }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: #F3F4F6; }
            """)
        else:
            sb.setStyleSheet("""
                QScrollBar:vertical {
                    background: transparent; width: 12px; margin: 8px 2px 8px 0;
                }
                QScrollBar::handle:vertical {
                    background: #D1D5DB; border-radius: 6px; min-height: 24px;
                }
                QScrollBar::handle:vertical:hover { background: #9CA3AF; }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; width: 0; }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
            """)
        sb.style().unpolish(sb); sb.style().polish(sb); sb.update()
