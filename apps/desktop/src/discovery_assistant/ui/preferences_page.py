from PySide6 import QtCore, QtGui, QtWidgets
import sys
from pathlib import Path
from discovery_assistant.baselogger import logging
log = logging.getLogger("DISCOVERY.ui.preferences")

def get_asset_path(name: str) -> str | None:
    """
    Resolve discovery_assistant/assets/images/<name> in dev and in a PyInstaller build.
    Logs what it tries so you can see why it failed if it does.
    """
    tries = [
        Path(__file__).resolve().parents[1] / "assets" / "images" / name,             # src/discovery_assistant/assets/images
        Path.cwd() / "discovery_assistant" / "assets" / "images" / name,              # cwd fallback
        Path.cwd() / "assets" / "images" / name,                                      # another cwd fallback
        Path(getattr(sys, "_MEIPASS", "")) / "assets" / "images" / name,              # PyInstaller layout A
        Path(getattr(sys, "_MEIPASS", "")) / "discovery_assistant" / "assets" / "images" / name,  # layout B
    ]
    for p in tries:
        if p.exists():
            log.info(f"[Preferences] Using asset: {p}")
            return str(p)
    log.warning("[Preferences] Asset NOT found: %s  (tried: %s)", name, " | ".join(str(t) for t in tries))
    return None

def style_secondary_button(btn: QtWidgets.QPushButton):
    btn.setCursor(QtCore.Qt.PointingHandCursor)
    btn.setStyleSheet("""
        QPushButton {
            background: #3C3C3C;
            color: #E5E7EB;
            border: 1px solid #4A4A4A;
            border-radius: 4px;
            padding: 4px 10px;
            font-weight: 600;
        }
        QPushButton:hover  { background: #4E4D4D; }
        QPushButton:pressed{ background: #000000; }
        QPushButton:disabled {
            background: #1F2937; color:#9CA3AF; border-color:#F3F4F6;
        }
    """)


class InfoButton(QtWidgets.QToolButton):
    """Icon-only info button; tooltip shows immediately and follows the mouse."""
    def __init__(self, tooltip: str = "", icon_path: str | None = None, parent=None):
        super().__init__(parent)
        self._tooltip_text = tooltip or ""
        self._last_tip_pos: QtCore.QPoint | None = None

        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setAutoRaise(False)                 # no hover glow
        self.setMouseTracking(True)              # get mouseMoveEvent without press
        self.setStyleSheet(
            "QToolButton{background:transparent;border:none;padding:0;}"
            "QToolButton:hover{background:transparent;}"
            "QToolButton:pressed{background:transparent;}"
            "QToolButton:focus{outline:none;border:none;}"
        )

        if icon_path and Path(icon_path).exists():
            self.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
            self.setIcon(QtGui.QIcon(icon_path))
            self.setIconSize(QtCore.QSize(24, 24))  # adjust if you like

        if self._tooltip_text:
            self.setToolTip(self._tooltip_text)  # keep for accessibility

        self.clicked.connect(self._show_click_bubble)

    # ---------- Tooltip helpers ----------
    def _show_following_tooltip(self, global_pos: QtCore.QPoint):
        if not self._tooltip_text:
            return
        # Only update if the mouse moved a little to avoid flicker
        if self._last_tip_pos and (global_pos - self._last_tip_pos).manhattanLength() < 2:
            return
        self._last_tip_pos = global_pos

        # Offset so the tooltip isn't under the cursor
        pos = global_pos + QtCore.QPoint(12, 12)

        # IMPORTANT: give a small moving rect; Qt keeps tooltip visible while the cursor stays in this rect.
        local = self.mapFromGlobal(global_pos)
        rect = QtCore.QRect(local - QtCore.QPoint(8, 8), QtCore.QSize(16, 16))

        QtWidgets.QToolTip.showText(pos, self._tooltip_text, self, rect, 10000)

    def _show_click_bubble(self):
        self._show_following_tooltip(QtGui.QCursor.pos())

    # ---------- Events ----------
    def enterEvent(self, e: QtCore.QEvent) -> None:
        self._show_following_tooltip(QtGui.QCursor.pos())
        super().enterEvent(e)

    def mouseMoveEvent(self, e: QtGui.QMouseEvent) -> None:
        self._show_following_tooltip(self.mapToGlobal(e.pos()))
        super().mouseMoveEvent(e)

    def leaveEvent(self, e: QtCore.QEvent) -> None:
        self._last_tip_pos = None
        QtWidgets.QToolTip.hideText()
        super().leaveEvent(e)

class PreferencesPage(QtWidgets.QWidget):
    closeRequested = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ---- BLACK header so the "Close" button is inverted (white) ----
        header = QtWidgets.QFrame()
        header.setStyleSheet("background:#000000; border:none;")
        h = QtWidgets.QHBoxLayout(header)
        h.setContentsMargins(16, 10, 16, 10)

        title = QtWidgets.QLabel("Preferences")
        # readable on black
        title.setStyleSheet("font-size:16px; font-weight:600; color:#F9FAFB;")
        h.addWidget(title)
        h.addStretch(1)

        close_btn = QtWidgets.QPushButton("Close")
        close_btn.setCursor(QtCore.Qt.PointingHandCursor)
        style_secondary_button(close_btn)
        close_btn.clicked.connect(self.closeRequested.emit)
        h.addWidget(close_btn)
        outer.addWidget(header)

        # ---- scrollable body (dark track + handle, no white anywhere) ----
        scroll = QtWidgets.QScrollArea()
        scroll.setObjectName("PrefsScroll")
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setWidgetResizable(True)

        # Scroll area + scrollbar skin (local to this widget via objectName)
        scroll.setStyleSheet("""
            /* Make the scroll area itself and its viewport dark */
            #PrefsScroll {
                background: #111827;             /* container bg */
                border: none;
            }
            #PrefsScroll QWidget#qt_scrollarea_viewport {
                background: #111827;             /* the actual viewport behind content */
            }

            /* The little square where H/V scrollbars meet */
            #PrefsScroll QAbstractScrollArea::corner {
                background: #111827;
            }

            /* -------- Vertical scrollbar -------- */
            #PrefsScroll QScrollBar:vertical {
                background: #111827;             /* track */
                width: 12px;
                margin: 0;
            }
            #PrefsScroll QScrollBar::handle:vertical {
                background: #4B5563;             /* handle */
                border-radius: 6px;
                min-height: 30px;
            }
            #PrefsScroll QScrollBar::handle:vertical:hover { background: #6B7280; }
            #PrefsScroll QScrollBar::add-line:vertical,
            #PrefsScroll QScrollBar::sub-line:vertical {
                height: 0;                       /* no arrow buttons */
            }
            #PrefsScroll QScrollBar::add-page:vertical,
            #PrefsScroll QScrollBar::sub-page:vertical {
                background: #111827;             /* fill the track behind the handle */
            }

            /* -------- Horizontal scrollbar (if shown) -------- */
            #PrefsScroll QScrollBar:horizontal {
                background: #111827;
                height: 12px;
                margin: 0;
            }
            #PrefsScroll QScrollBar::handle:horizontal {
                background: #4B5563;
                border-radius: 6px;
                min-width: 30px;
            }
            #PrefsScroll QScrollBar::handle:horizontal:hover { background: #6B7280; }
            #PrefsScroll QScrollBar::add-line:horizontal,
            #PrefsScroll QScrollBar::sub-line:horizontal {
                width: 0;
            }
            #PrefsScroll QScrollBar::add-page:horizontal,
            #PrefsScroll QScrollBar::sub-page:horizontal {
                background: #111827;
            }
        """)

        # also set the viewport palette (belt & suspenders; kills any white flash)
        vp = scroll.viewport()
        vp.setAutoFillBackground(True)

        base = self.palette().window().color()  # use the app/window background
        pal = vp.palette()
        pal.setColor(QtGui.QPalette.Window, base)
        vp.setPalette(pal)

        outer.addWidget(scroll, 1)

        body = QtWidgets.QWidget()
        scroll.setWidget(body)
        body_v = QtWidgets.QVBoxLayout(body)
        body_v.setContentsMargins(16, 16, 16, 16)
        body_v.setSpacing(16)

        # ---------------- Personal ----------------
        personal = _OutlinedGroupBox("Personal", tooltip="Your device-level settings.")
        body_v.addWidget(personal)

        per_form = QtWidgets.QFormLayout()
        per_form.setLabelAlignment(QtCore.Qt.AlignLeft)
        per_form.setFormAlignment(QtCore.Qt.AlignTop)
        per_form.setHorizontalSpacing(12)
        per_form.setVerticalSpacing(8)
        personal.inner_layout.addLayout(per_form)

        self.chk_autosave = QtWidgets.QCheckBox("Enable autosave")
        per_form.addRow("Autosave", self.chk_autosave)

        self.cmb_autosave_interval = QtWidgets.QComboBox()
        self.cmb_autosave_interval.addItems(["30 s", "60 s", "120 s", "300 s"])
        per_form.addRow("Autosave interval", self.cmb_autosave_interval)

        self.lbl_lock_status = QtWidgets.QLabel("Status: Off")
        self.btn_lock = QtWidgets.QPushButton("Set / Change…")
        style_secondary_button(self.btn_lock)
        self.btn_lock.setCursor(QtCore.Qt.PointingHandCursor)
        lock_row = QtWidgets.QWidget();
        lh = QtWidgets.QHBoxLayout(lock_row);
        lh.setContentsMargins(0, 0, 0, 0);
        lh.setSpacing(8)
        lh.addWidget(self.lbl_lock_status);
        lh.addStretch(1);
        lh.addWidget(self.btn_lock)
        per_form.addRow("App Lock (this device)", lock_row)

        body_v.addStretch(1)

        # ---------------- Organization ----------------
        self.org_group = _OutlinedGroupBox("Organization", locked=True, tooltip="Set by your organization.")
        body_v.addWidget(self.org_group)

        org_form = QtWidgets.QFormLayout()
        org_form.setLabelAlignment(QtCore.Qt.AlignLeft)
        org_form.setFormAlignment(QtCore.Qt.AlignTop)
        org_form.setHorizontalSpacing(12)
        org_form.setVerticalSpacing(8)
        self.org_group.inner_layout.addLayout(org_form)

        self.cmb_review = QtWidgets.QComboBox(); self.cmb_review.addItems(["None","Single approver","Dual approval"])
        org_form.addRow("Review before submission", self.cmb_review)

        gate_row = QtWidgets.QWidget()
        gate_h = QtWidgets.QHBoxLayout(gate_row); gate_h.setContentsMargins(0,0,0,0); gate_h.setSpacing(8)
        self.sbx_gate = QtWidgets.QSpinBox(); self.sbx_gate.setRange(0,100); self.sbx_gate.setSuffix(" %"); self.sbx_gate.setValue(60)
        gate_h.addWidget(self.sbx_gate)
        org_form.addRow("Export gating threshold", gate_row)

        self.btn_required = QtWidgets.QPushButton("Configure…")
        self.btn_required.setCursor(QtCore.Qt.PointingHandCursor)
        org_form.addRow("Required sections before export", self.btn_required)

        self.chk_cloud = QtWidgets.QCheckBox("Enable")
        org_form.addRow("Cloud submit", self.chk_cloud)
        self.chk_autodel = QtWidgets.QCheckBox("Auto-delete after verified upload")
        org_form.addRow("", self.chk_autodel)

        self.chk_shots = QtWidgets.QCheckBox("Enable screenshots")
        org_form.addRow("Screenshots", self.chk_shots)
        self.chk_redact_review = QtWidgets.QCheckBox("Redaction review required")
        org_form.addRow("", self.chk_redact_review)
        self.chk_external = QtWidgets.QCheckBox("Allow screenshots of external apps")
        org_form.addRow("", self.chk_external)

        self.chk_audit = QtWidgets.QCheckBox("Save audit log (events only; no contents)")
        org_form.addRow("Audit logging", self.chk_audit)
        self.chk_backups = QtWidgets.QCheckBox("Save backups")
        org_form.addRow("Backups", self.chk_backups)
        self.cmb_backup_freq = QtWidgets.QComboBox(); self.cmb_backup_freq.addItems(["1 min","2 min","5 min","10 min"])
        org_form.addRow("Backup frequency", self.cmb_backup_freq)

        self.cmb_idle = QtWidgets.QComboBox(); self.cmb_idle.addItems(["Off","5 min","10 min","15 min","30 min"])
        org_form.addRow("Session idle timeout", self.cmb_idle)

        self.chk_consent = QtWidgets.QCheckBox("Require consent screen (v1)")
        org_form.addRow("Consent", self.chk_consent)

        exp_box = QtWidgets.QWidget()
        exp_l = QtWidgets.QVBoxLayout(exp_box); exp_l.setContentsMargins(0,0,0,0); exp_l.setSpacing(4)
        self.chk_pdf_pwd = QtWidgets.QCheckBox("Require PDF/DOCX password")
        self.chk_zip_aes = QtWidgets.QCheckBox("Require ZIP/7z (AES-256) for bundles")
        self.cmb_pwd_by  = QtWidgets.QComboBox(); self.cmb_pwd_by.addItems(["Admin","Respondent","Per delivery"])
        exp_l.addWidget(self.chk_pdf_pwd); exp_l.addWidget(self.chk_zip_aes)
        row_pwd = QtWidgets.QWidget(); rhl = QtWidgets.QHBoxLayout(row_pwd); rhl.setContentsMargins(0,0,0,0); rhl.setSpacing(8)
        rhl.addWidget(QtWidgets.QLabel("Password set by")); rhl.addWidget(self.cmb_pwd_by); rhl.addStretch(1)
        exp_l.addWidget(row_pwd)
        org_form.addRow("Export protection policy", exp_box)

        self.cmb_retention_drafts = QtWidgets.QComboBox(); self.cmb_retention_drafts.addItems(["7 days","14 days","30 days","90 days"])
        self.cmb_retention_logs   = QtWidgets.QComboBox(); self.cmb_retention_logs.addItems(["30 days","90 days","180 days","365 days"])
        retention_row = QtWidgets.QWidget(); rh = QtWidgets.QHBoxLayout(retention_row); rh.setContentsMargins(0,0,0,0); rh.setSpacing(8)
        rh.addWidget(QtWidgets.QLabel("Drafts/Backups")); rh.addWidget(self.cmb_retention_drafts)
        rh.addSpacing(12)
        rh.addWidget(QtWidgets.QLabel("Audit logs")); rh.addWidget(self.cmb_retention_logs)
        rh.addStretch(1)
        org_form.addRow("Retention window", retention_row)

        pii_row = QtWidgets.QWidget()
        ph = QtWidgets.QHBoxLayout(pii_row); ph.setContentsMargins(0,0,0,0); ph.setSpacing(12)
        self.chk_mask_ui = QtWidgets.QCheckBox("Mask on screen")
        self.chk_redact_exports = QtWidgets.QCheckBox("Redact in exports")
        self.chk_anonymize = QtWidgets.QCheckBox("Anonymize respondent in export")
        for w in (self.chk_mask_ui, self.chk_redact_exports, self.chk_anonymize): ph.addWidget(w)
        ph.addStretch(1)
        org_form.addRow("PII handling", pii_row)



        # gather org controls for locking
        self._org_controls = [
            self.cmb_review, self.sbx_gate, self.btn_required, self.chk_cloud, self.chk_autodel,
            self.chk_shots, self.chk_redact_review, self.chk_external, self.chk_audit, self.chk_backups,
            self.cmb_backup_freq, self.cmb_idle, self.chk_consent, self.chk_pdf_pwd, self.chk_zip_aes,
            self.cmb_pwd_by, self.cmb_retention_drafts, self.cmb_retention_logs,
            self.chk_mask_ui, self.chk_redact_exports, self.chk_anonymize
        ]

    def set_admin_mode(self, is_admin: bool):
        for w in self._org_controls:
            w.setEnabled(is_admin)
        self.org_group.set_locked(not is_admin)




class _OutlinedGroupBox(QtWidgets.QFrame):
    """Outlined block with small header row and light tint; auto-contrasts title color."""
    def __init__(self, title: str, locked: bool=False, tooltip: str=""):
        super().__init__()
        self._locked = locked
        self.setObjectName("OutlinedGroup")
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)

        base = self.palette().window().color()
        is_dark = base.lightnessF() < 0.5
        outline = "#374151" if is_dark else "#E5E7EB"
        bg      = "rgba(255,255,255,0.04)" if is_dark else "rgba(0,0,0,0.03)"
        title_c = "#E5E7EB" if is_dark else "#0F172A"

        self.setStyleSheet(f"""
            #OutlinedGroup {{
                border: 1px solid {outline};
                border-radius: 10px;
                background-color: {bg};
            }}
        """)

        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(12, 10, 12, 12)
        v.setSpacing(8)

        hdr = QtWidgets.QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 0)
        hdr.setSpacing(6)

        self._title_lbl = QtWidgets.QLabel(title)
        self._title_lbl.setStyleSheet(f"font-size:12px; font-weight:600; color:{title_c};")
        hdr.addWidget(self._title_lbl)

        self._lock_lbl = QtWidgets.QLabel("🔒")
        self._lock_lbl.setToolTip("Admin-controlled")
        self._lock_lbl.setStyleSheet("font-size:12px;")
        self._lock_lbl.setVisible(locked)
        hdr.addWidget(self._lock_lbl)

        # Info button (SVG icon + tooltip on hover/click)
        INFO_ICON_PATH = get_asset_path("info_off.svg")  # or "info_hover.svg" if that’s the file you want
        info = InfoButton(tooltip=tooltip, icon_path=INFO_ICON_PATH)

        # make the icon larger and keep a bigger hit target
        info.setIconSize(QtCore.QSize(20, 20))  # <- icon size
        info.setFixedSize(30, 30)  # <- button size

        # kill hover/pressed background and outlines
        info.setAutoRaise(False)  # prevents style from auto-highlighting
        info.setStyleSheet("""
            QToolButton { background: transparent; border: none; padding: 0; }
            QToolButton:hover { background: transparent; }
            QToolButton:pressed { background: transparent; }
            QToolButton:focus { outline: none; border: none; }
        """)

        # be explicit about tooltip + keep it visible longer
        info.setToolTip(tooltip)
        info.setToolTipDuration(6000)  # ms
        hdr.addWidget(info)

        hdr.addStretch(1)
        v.addLayout(hdr)

        self.inner_layout = QtWidgets.QVBoxLayout()
        self.inner_layout.setContentsMargins(0, 0, 0, 0)
        self.inner_layout.setSpacing(6)
        v.addLayout(self.inner_layout)

    def set_locked(self, locked: bool):
        self._locked = locked
        self._lock_lbl.setVisible(locked)
