from PySide6 import QtWidgets, QtCore, QtGui
from discovery_assistant.baselogger import logging
from discovery_assistant.ui.info_text import RESPONDENT_INFO
from discovery_assistant.ui.widgets.info import InfoSection
from discovery_assistant.storage import DatabaseSession, Respondent

_LOGGER = logging.getLogger("DISCOVERY.ui.tabs.respondent_tab")


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


# ===============----->>
# Respondent Tab ------->>
# ===============----->>

class RespondentTab(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        _LOGGER.info("RespondentTab initialized")

        # ---- OUTER SCROLL AREA (child of this tab) ----
        scroller = QtWidgets.QScrollArea(self)
        scroller.setObjectName("RespondentScroll")
        scroller.setWidgetResizable(True)
        scroller.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroller.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)   # reserve width → no shift
        scroller.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroller.setStyleSheet("""
            QScrollArea#RespondentScroll { background: transparent; border: none; }

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
        card.setObjectName("RespondentCard")
        card.setStyleSheet("""
            QFrame#RespondentCard {
                background:#FFFFFF;
                border:1px solid #E5E7EB;
                border-radius:12px;
            }
            QFrame#RespondentCard QLabel { background: transparent; }
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
            title="Respondent Profile",
            subtitle="Please enter basic information about who you are.",
            info_html=RESPONDENT_INFO,
            icon_size_px=28,
            parent=card,
        )
        card_layout.addWidget(section)
        section.bind_scrollarea(self._scroller)

        # ---- FORM ----
        form = _StackedLabelForm(card)

        full_name = QtWidgets.QLineEdit()
        full_name.setPlaceholderText("e.g., Dana Rivera")  # Keep this - it's just example text
        full_name.setObjectName("fullName")
        _force_dark_text(full_name)
        form.add_row("Full Name", full_name)

        work_email = QtWidgets.QLineEdit()
        work_email.setPlaceholderText("dana@company.com")  # Keep this - it's just example text
        work_email.setObjectName("workEmail")
        _force_dark_text(work_email)
        form.add_row("Work Email", work_email)

        dept = QtWidgets.QLineEdit()
        dept.setPlaceholderText("e.g., Support")  # Keep this - it's just example text
        dept.setObjectName("department")
        _force_dark_text(dept)
        form.add_row("Department", dept)

        role = QtWidgets.QLineEdit()
        role.setPlaceholderText("Customer Support Lead")  # Keep this - it's just example text
        role.setObjectName("roleTitle")
        _force_dark_text(role)
        form.add_row("Role / Title", role)

        responsibilities = QtWidgets.QTextEdit()
        responsibilities.setPlaceholderText("Summarize duties & metrics")  # Keep this - it's just example text
        responsibilities.setObjectName("primaryResponsibilities")
        responsibilities.setMinimumHeight(140)
        _force_dark_text(responsibilities)
        form.add_row("Primary Responsibilities", responsibilities)

        card_layout.addLayout(form)

        # ---- mount scroller ----
        root_layout = QtWidgets.QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(scroller)

        # ---- INITIAL SCROLLBAR MODE + TOGGLES (InfoSection-driven) ----
        self._set_scrollbar_stealth(True)  # start stealth (panel hidden)
        section.toggled.connect(lambda open_: self._set_scrollbar_stealth(not open_))

        # Store references to form fields for database operations
        self.full_name_field = full_name
        self.work_email_field = work_email
        self.department_field = dept
        self.role_title_field = role
        self.responsibilities_field = responsibilities

        # Load existing data first
        self._load_respondent_data()

        # Then connect autosave signals (after loading data)
        self._connect_autosave_signals()

    def _get_section_name(self) -> str:
        return "respondent"

    def _load_respondent_data(self) -> None:
        """Load existing respondent data from database into form fields."""
        try:
            with DatabaseSession() as session:
                respondent = session.query(Respondent).first()
                if respondent:
                    # Populate fields (no need to disconnect since signals aren't connected yet)
                    if respondent.full_name:
                        self.full_name_field.setText(respondent.full_name)
                    if respondent.work_email:
                        self.work_email_field.setText(respondent.work_email)
                    if respondent.department:
                        self.department_field.setText(respondent.department)
                    if respondent.role_title:
                        self.role_title_field.setText(respondent.role_title)
                    if respondent.primary_responsibilities:
                        self.responsibilities_field.setPlainText(respondent.primary_responsibilities)

                    _LOGGER.info("Loaded existing respondent data")
                else:
                    _LOGGER.info("No existing respondent data found")

        except Exception as e:
            _LOGGER.error(f"Failed to load respondent data: {e}")

    def _save_respondent_data(self) -> None:
        """Save current form data to database."""
        try:
            with DatabaseSession() as session:
                # Get existing record or create new one
                respondent = session.query(Respondent).first()
                if not respondent:
                    respondent = Respondent()
                    session.add(respondent)

                # Update fields with current form values
                respondent.full_name = self.full_name_field.text().strip() or None
                respondent.work_email = self.work_email_field.text().strip() or None
                respondent.department = self.department_field.text().strip() or None
                respondent.role_title = self.role_title_field.text().strip() or None
                respondent.primary_responsibilities = self.responsibilities_field.toPlainText().strip() or None

                # Session context manager will automatically commit

        except Exception as e:
            _LOGGER.error(f"Failed to save respondent data: {e}")

    def clear_fields(self) -> None:
        """Clear all form fields."""
        # Temporarily disconnect autosave to avoid saving empty values
        try:
            self.full_name_field.textChanged.disconnect()
            self.work_email_field.textChanged.disconnect()
            self.department_field.textChanged.disconnect()
            self.role_title_field.textChanged.disconnect()
            self.responsibilities_field.textChanged.disconnect()
        except:
            pass  # Ignore if already disconnected

        # Clear all fields
        self.full_name_field.clear()
        self.work_email_field.clear()
        self.department_field.clear()
        self.role_title_field.clear()
        self.responsibilities_field.clear()

        # Reconnect autosave signals
        self._connect_autosave_signals()

        _LOGGER.info("Cleared all respondent fields")

    def _connect_autosave_signals(self) -> None:
        """Connect autosave signals."""
        self.full_name_field.textChanged.connect(self._save_respondent_data)
        self.work_email_field.textChanged.connect(self._save_respondent_data)
        self.department_field.textChanged.connect(self._save_respondent_data)
        self.role_title_field.textChanged.connect(self._save_respondent_data)
        self.responsibilities_field.textChanged.connect(self._save_respondent_data)

    def _disconnect_autosave_signals(self) -> None:
        """Temporarily disconnect autosave signals."""
        self.full_name_field.textChanged.disconnect()
        self.work_email_field.textChanged.disconnect()
        self.department_field.textChanged.disconnect()
        self.role_title_field.textChanged.disconnect()
        self.responsibilities_field.textChanged.disconnect()

    def _connect_autosave_signals(self) -> None:
        """Connect autosave signals."""
        self.full_name_field.textChanged.connect(self._save_respondent_data)
        self.work_email_field.textChanged.connect(self._save_respondent_data)
        self.department_field.textChanged.connect(self._save_respondent_data)
        self.role_title_field.textChanged.connect(self._save_respondent_data)
        self.responsibilities_field.textChanged.connect(self._save_respondent_data)

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
