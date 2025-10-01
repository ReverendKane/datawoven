from PySide6 import QtWidgets, QtCore, QtGui
from discovery_assistant.baselogger import logging
from discovery_assistant.ui.widgets.info import InfoSection
from discovery_assistant.ui.info_text import ORG_INFO
from discovery_assistant.storage import DatabaseSession, OrgMap

_LOGGER = logging.getLogger("DISCOVERY.ui.tabs.org_map_tab")


# ==========----->>
# Utilities ------->>
# ==========----->>

def _force_dark_text(widget: QtWidgets.QWidget,
                     text_hex: str = "#000000",
                     placeholder_hex: str = "#94A3B8") -> None:
    """Apply dark text + softer placeholder to inputs."""
    if isinstance(widget, (QtWidgets.QLineEdit, QtWidgets.QTextEdit, QtWidgets.QPlainTextEdit)):
        base = (
            f"color:{text_hex};"
            "background:#FFFFFF;"
            "border:1px solid #E2E8F0;"
            "border-radius:8px;"
            "padding:8px 10px;"
            "selection-background-color:#0F172A;"
        )
        focus = "border:1.5px solid #0F172A;"
        cls = widget.metaObject().className()
        widget.setStyleSheet(f"{cls}{{{base}}}{cls}:focus{{{focus}}}")
        if isinstance(widget, QtWidgets.QLineEdit):
            pal = widget.palette()
            pal.setColor(QtGui.QPalette.PlaceholderText, QtGui.QColor(placeholder_hex))
            widget.setPalette(pal)


class _StackedLabelForm(QtWidgets.QVBoxLayout):
    """Label above field layout."""
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(12)

    def add_row(self, label: str, field: QtWidgets.QWidget) -> None:
        row = QtWidgets.QVBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        lbl = QtWidgets.QLabel(label)
        lbl.setStyleSheet("font-size:13px; color:#334155; background:transparent;")
        row.addWidget(lbl)
        row.addWidget(field)
        self.addLayout(row)


# ============----->>
# Org Map Tab ------->>
# ============----->>

class OrgMapTab(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        _LOGGER.info("OrgTab initialized")

        # ---- OUTER SCROLL AREA (child of this tab) ----
        scroller = QtWidgets.QScrollArea(self)
        scroller.setObjectName("OrgScroll")
        scroller.setWidgetResizable(True)
        scroller.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroller.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)   # reserve width → no shift
        scroller.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroller.setStyleSheet("""
            QScrollArea#OrgScroll { background: transparent; border: none; }

            /* Base (active) vertical scrollbar look */
            QScrollBar:vertical {
                background: transparent;
                width: 12px;
                margin: 8px 2px 8px 0px;
            }
            QScrollBar::handle:vertical {
                background: #D1D5DB;       /* gray-300 */
                min-height: 24px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover { background: #9CA3AF; }  /* gray-400 */
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
        """)

        # Keep a handle to this tab's own scroller (IMPORTANT)
        self._scroller: QtWidgets.QScrollArea = scroller

        root = QtWidgets.QWidget()
        root.setStyleSheet("background:#F3F4F6;")  # light page bg
        scroller.setWidget(root)

        page = QtWidgets.QVBoxLayout(root)
        page.setContentsMargins(12, 10, 12, 12)
        page.setSpacing(12)

        # ---- CARD ----
        card = QtWidgets.QFrame(root)
        card.setObjectName("OrgCard")
        card.setStyleSheet("""
            QFrame#OrgCard {
                background:#FFFFFF;
                border:1px solid #E5E7EB;
                border-radius:12px;
            }
            QFrame#OrgCard QLabel { background: transparent; }
            QLineEdit, QTextEdit {
                background:#FFFFFF;
                border:1px solid #E2E8F0;
                border-radius:8px;
                padding:8px 10px;
                color:#000000;
                selection-background-color:#0F172A;
            }
            QLineEdit:focus, QTextEdit:focus { border:1.5px solid #0F172A; }
        """)
        page.addWidget(card)

        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(10)

        # ---- HEADER AND INFO BAR ----
        section = InfoSection(
            title="Org Context",
            subtitle="Please describe where your role is positioned, and your collaborators.",
            info_html=ORG_INFO,
            icon_size_px=28,
            parent=card,
        )
        card_layout.addWidget(section)
        section.bind_scrollarea(self._scroller)

        # ---- FORM ----
        form = _StackedLabelForm(card)

        reportsTo = QtWidgets.QLineEdit()
        reportsTo.setPlaceholderText("Manager name/title")
        reportsTo.setObjectName("reportsTo")
        _force_dark_text(reportsTo)
        form.add_row("Reports To", reportsTo)

        peer_teams = QtWidgets.QLineEdit()
        peer_teams.setPlaceholderText("e.g. Sales Ops, QA")
        peer_teams.setObjectName("peerTeams")
        _force_dark_text(peer_teams)
        form.add_row("Peer Teams", peer_teams)

        downstream_consumers = QtWidgets.QLineEdit()
        downstream_consumers.setPlaceholderText("e.g., Support")
        downstream_consumers.setObjectName("downstreamConsumers")
        _force_dark_text(downstream_consumers)
        form.add_row("Downstream Consumers", downstream_consumers)

        org_notes = QtWidgets.QTextEdit()
        org_notes.setPlaceholderText("Key handoffs, dependencies, SLAs")
        org_notes.setObjectName("orgNotes")
        _force_dark_text(org_notes)
        form.add_row("Org Notes", org_notes)

        card_layout.addLayout(form)

        # ---- mount scroller ----
        root_layout = QtWidgets.QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(scroller)

        # ---- INITIAL SCROLLBAR MODE + TOGGLES (InfoSection-driven) ----
        self._set_scrollbar_stealth(True)  # start stealth (panel hidden)
        section.toggled.connect(lambda open_: self._set_scrollbar_stealth(not open_))

        # Store references to form fields for database operations
        self.reports_to_field = reportsTo
        self.peer_teams_field = peer_teams
        self.downstream_consumers_field = downstream_consumers
        self.org_notes_field = org_notes

        # Load existing data first
        self._load_orgmap_data()

        # Then connect autosave signals (after loading data)
        self._connect_autosave_signals()

    def _get_section_name(self) -> str:
        return "org_map"

    # ---------- handle entered data ----------
    def _load_orgmap_data(self) -> None:
        """Load existing org map data from database into form fields."""
        try:
            with DatabaseSession() as session:
                org_map = session.query(OrgMap).first()
                if org_map:
                    # Populate fields
                    if org_map.reports_to:
                        self.reports_to_field.setText(org_map.reports_to)
                    if org_map.peer_teams:
                        self.peer_teams_field.setText(org_map.peer_teams)
                    if org_map.downstream_consumers:
                        self.downstream_consumers_field.setText(org_map.downstream_consumers)
                    if org_map.org_notes:
                        self.org_notes_field.setPlainText(org_map.org_notes)

                    _LOGGER.info("Loaded existing org map data")
                else:
                    _LOGGER.info("No existing org map data found")

        except Exception as e:
            _LOGGER.error(f"Failed to load org map data: {e}")

    def _save_orgmap_data(self) -> None:
        """Save current form data to database."""
        try:
            with DatabaseSession() as session:
                # Get existing record or create new one
                org_map = session.query(OrgMap).first()
                if not org_map:
                    org_map = OrgMap()
                    session.add(org_map)

                # Update fields with current form values
                org_map.reports_to = self.reports_to_field.text().strip() or None
                org_map.peer_teams = self.peer_teams_field.text().strip() or None
                org_map.downstream_consumers = self.downstream_consumers_field.text().strip() or None
                org_map.org_notes = self.org_notes_field.toPlainText().strip() or None

                # Session context manager will automatically commit

        except Exception as e:
            _LOGGER.error(f"Failed to save org map data: {e}")

    def _connect_autosave_signals(self) -> None:
        """Connect autosave signals."""
        self.reports_to_field.textChanged.connect(self._save_orgmap_data)
        self.peer_teams_field.textChanged.connect(self._save_orgmap_data)
        self.downstream_consumers_field.textChanged.connect(self._save_orgmap_data)
        self.org_notes_field.textChanged.connect(self._save_orgmap_data)

    def clear_fields(self) -> None:
        """Clear all form fields."""
        # Temporarily disconnect autosave to avoid saving empty values
        try:
            self.reports_to_field.textChanged.disconnect()
            self.peer_teams_field.textChanged.disconnect()
            self.downstream_consumers_field.textChanged.disconnect()
            self.org_notes_field.textChanged.disconnect()
        except:
            pass  # Ignore if already disconnected

        # Clear all fields
        self.reports_to_field.clear()
        self.peer_teams_field.clear()
        self.downstream_consumers_field.clear()
        self.org_notes_field.clear()

        # Reconnect autosave signals
        self._connect_autosave_signals()

        _LOGGER.info("Cleared all org map fields")

    # ---------- helpers ----------
    def _find_parent_scrollbar(self):
        """(fallback) Return the vertical scrollbar of the nearest parent QAbstractScrollArea, or None."""
        p = self.parent()
        from PySide6.QtWidgets import QAbstractScrollArea
        while p and not isinstance(p, QAbstractScrollArea):
            p = p.parent()
        return p.verticalScrollBar() if p else None

    def _set_scrollbar_stealth(self, stealth: bool):
        """
        Apply an 'invisible' look when stealth=True; normal when False.
        IMPORTANT: Prefer this tab's own scroller; fall back to parent if needed.
        """
        # Use this tab's child scroller if present
        sb = None
        if hasattr(self, "_scroller") and isinstance(self._scroller, QtWidgets.QScrollArea):
            sb = self._scroller.verticalScrollBar()
        if sb is None:
            sb = self._find_parent_scrollbar()
        if sb is None:
            return

        if stealth:
            # Stealth: track/handle match the page background (F3F4F6)
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
            # Active: subtle gray handle on transparent track
            sb.setStyleSheet("""
                QScrollBar:vertical {
                    background: transparent;
                    width: 12px;
                    margin: 8px 2px 8px 0;
                }
                QScrollBar::handle:vertical {
                    background: #D1D5DB;    /* gray-300 */
                    border-radius: 6px;
                    min-height: 24px;
                }
                QScrollBar::handle:vertical:hover { background: #9CA3AF; } /* gray-400 */
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; width: 0; }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
            """)
        # Ensure repaint
        sb.style().unpolish(sb)
        sb.style().polish(sb)
        sb.update()
