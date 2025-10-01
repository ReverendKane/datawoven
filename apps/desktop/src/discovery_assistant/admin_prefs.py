from pathlib import Path
import os, sys, json, shutil

from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl, QStandardPaths

from discovery_assistant.admin_auth import change_admin_password

# ---------- helpers for canonical install ----------
APP_NAME = "Discovery Assistant"

def _policy_dir() -> Path:
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / APP_NAME / "policy"
    elif sys.platform.startswith("win"):
        base = Path.home() / "AppData" / "Local" / APP_NAME / "policy"
    else:
        base = Path.home() / f".{APP_NAME.lower().replace(' ', '_')}" / "policy"
    base.mkdir(parents=True, exist_ok=True)
    return base

def _policy_path() -> Path:
    return _policy_dir() / "governance.pol"

def _open_folder(path: Path) -> None:
    folder = path if path.is_dir() else path.parent
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

def _qt_desktop_path() -> Path | None:
    p = QStandardPaths.writableLocation(QStandardPaths.DesktopLocation)
    return Path(p) if p else None


# ---------- password change dialog ----------
class SetPasswordDialog(QtWidgets.QDialog):
    """Shown when verify_admin_password() returns OK_MUST_CHANGE."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set New Admin Password")
        self.setObjectName("setPwdDlg")
        self.setStyleSheet("""
            #setPwdDlg QPushButton {
                padding: 6px 12px;
                min-height: 30px;
            }
        """)
        self.setModal(True)
        self.resize(420, 220)

        form = QtWidgets.QFormLayout()
        self.old = QtWidgets.QLineEdit(); self.old.setEchoMode(QtWidgets.QLineEdit.Password)
        self.new1 = QtWidgets.QLineEdit(); self.new1.setEchoMode(QtWidgets.QLineEdit.Password)
        self.new2 = QtWidgets.QLineEdit(); self.new2.setEchoMode(QtWidgets.QLineEdit.Password)
        form.addRow("Current temp password:", self.old)
        form.addRow("New password:", self.new1)
        form.addRow("Confirm new password:", self.new2)

        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        btns.accepted.connect(self._accept)
        btns.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(btns)

        self._ok = False
        _set_hand_cursor_for_buttons(self, include_checkables=False)

    def _accept(self):
        if self.new1.text() != self.new2.text():
            QtWidgets.QMessageBox.warning(self, "Mismatch", "New passwords do not match.")
            return
        if not self.new1.text():
            QtWidgets.QMessageBox.warning(self, "Empty", "New password cannot be empty.")
            return
        if not change_admin_password(self.old.text(), self.new1.text()):
            QtWidgets.QMessageBox.warning(self, "Invalid", "Current temp password is incorrect.")
            return
        self._ok = True
        self.accept()

    def success(self) -> bool:
        return self._ok


# ---------- additional helpers ----------
def _set_hand_cursor_for_buttons(root: QtWidgets.QWidget, include_checkables=False):
    """Apply pointing-hand cursor to buttons under 'root'."""
    for w in root.findChildren(QtWidgets.QAbstractButton):
        if include_checkables:
            w.setCursor(QtCore.Qt.PointingHandCursor)
        else:
            if isinstance(w, (QtWidgets.QPushButton, QtWidgets.QToolButton)):
                w.setCursor(QtCore.Qt.PointingHandCursor)


# ---------- admin preferences ----------
class AdminPreferencesWindow(QtWidgets.QWidget):
    """
    ADMIN PREFERENCES
    -----------------
    - Installs the admin's local license to a consistent user-scope path.
    - Optionally saves a separate distribution copy for respondents.
    - Provides buttons to open the installed policy folder and to save a distribution copy later.
    """
    policyInstalled = QtCore.Signal()  # emit when a policy is successfully installed locally

    def __init__(self, parent=None, force_password_change: bool = False):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.setObjectName("adminPrefsRoot")  # scope styles to this window only

        # CHANGED: scoped styles for buttons AND the distribution QLineEdit
        self.setStyleSheet("""
            #adminPrefsRoot QPushButton {
                padding: 6px 12px;
                min-height: 25px;
            }
            /* NEW: style only the dist path field to remove dark bottom line and restore rounded corners */
            #adminPrefsRoot QLineEdit#distPathEdit {
                padding: 6px 10px;
                min-height: 25px;
                border: 1px solid #3A3F4A;       /* uniform border (dark theme friendly) */
                border-radius: 8px;               /* subtle rounding */
                background: palette(base);
                color: palette(text);
            }
            #adminPrefsRoot QLineEdit#distPathEdit:focus {
                border-color: #4C82F7;            /* focus accent */
            }
        """)

        self.resize(840, 620)

        self._last_distribution_target: Path | None = None  # remember last dist path
        self._build_ui()
        _set_hand_cursor_for_buttons(self, include_checkables=False)

        if force_password_change:
            dlg = SetPasswordDialog(self)
            if not dlg.exec() or not dlg.success():
                QtWidgets.QMessageBox.information(
                    self, "Reminder",
                    "You will need to set a new Admin password before deploying."
                )

        self.setStyleSheet("""
            #adminPrefsRoot QPushButton {
                padding: 6px 12px;
                min-height: 25px;
            }
            /* NEW: style only the dist path field to remove dark bottom line and restore rounded corners */
            #adminPrefsRoot QLineEdit#distPathEdit {
                padding: 6px 10px;
                min-height: 25px;
                border: 1px solid #3A3F4A;       /* uniform border (dark theme friendly) */
                border-radius: 8px;               /* subtle rounding */
                background: palette(base);
                color: palette(text);
            }
            #adminPrefsRoot QLineEdit#distPathEdit:focus {
                border-color: #4C82F7;            /* focus accent */
            }
            /* NEW: Checkbox background color only */
            #adminPrefsRoot QCheckBox::indicator {
                background-color: #2A2F3A;        /* Dark gray - darker than tab content, lighter than window background */
            }
            #adminPrefsRoot QCheckBox::indicator:checked {
                background-color: palette(highlight);  /* Use system highlight color when checked */
            }
        """)

    # ---------------- UI ----------------
    def _build_ui(self):
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(10)

        # Title + helpful directions (kept minimal; delete the next two widgets if you prefer just a title)
        title = QtWidgets.QLabel("Administrative Setup")
        title.setStyleSheet("color:#FFFFFF; font-size:18px; font-weight:600;")
        outer.addWidget(title)

        # NEW: short directions paragraph (muted, wrapped)
        helptext = QtWidgets.QLabel(
            "Choose your governance settings, then click “Generate & Install Policy”. "
            "We’ll install your local license to a standard, user-scope location. "
            "Use “Save Distribution Copy…” to create a copy you can share with respondents."
        )
        helptext.setWordWrap(True)
        helptext.setStyleSheet("color:#9AA3B2; font-size:12px;")
        outer.addWidget(helptext)
        outer.addSpacing(10)

        tabs = QtWidgets.QTabWidget()
        tabs.addTab(self._build_privacy_tab(), "Privacy")
        tabs.addTab(self._build_data_tab(), "Data")
        tabs.addTab(self._build_export_tab(), "Export Policy")
        outer.addWidget(tabs, 1)

        # Distribution default (optional)
        distRow = QtWidgets.QHBoxLayout()
        self.outPath = QtWidgets.QLineEdit()
        self.outPath.setObjectName("distPathEdit")            # NEW: target for styles
        self.outPath.setPlaceholderText("Optional default folder for your distribution copy")
        self.outPath.setText(str(self._default_output_folder()))
        btnBrowse = QtWidgets.QPushButton("Browse…")
        btnBrowse.clicked.connect(self._choose_output_folder)
        distRow.addWidget(QtWidgets.QLabel("Distribution folder (optional):"))
        distRow.addWidget(self.outPath, 1)
        distRow.addWidget(btnBrowse)
        outer.addLayout(distRow)

        # Footer buttons
        btns = QtWidgets.QHBoxLayout()
        btns.addStretch(1)

        self.btnGenerate = QtWidgets.QPushButton("Generate & Install Policy")
        self.btnGenerate.setDefault(True)
        self.btnGenerate.clicked.connect(self._on_generate)

        self.btnOpenInstalled = QtWidgets.QPushButton("Open Installed Policy Folder")
        self.btnOpenInstalled.setEnabled(False)
        self.btnOpenInstalled.clicked.connect(lambda: _open_folder(_policy_dir()))

        self.btnSaveDist = QtWidgets.QPushButton("Save Distribution Copy…")
        self.btnSaveDist.setEnabled(False)
        self.btnSaveDist.clicked.connect(self._save_distribution_copy)

        self.btnClose = QtWidgets.QPushButton("Close")
        self.btnClose.clicked.connect(self.close)

        btns.addWidget(self.btnGenerate)
        btns.addWidget(self.btnOpenInstalled)
        btns.addWidget(self.btnSaveDist)
        btns.addWidget(self.btnClose)
        outer.addLayout(btns)

    def _build_privacy_tab(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        lay = QtWidgets.QFormLayout(w)
        lay.setLabelAlignment(QtCore.Qt.AlignRight)
        self.chkScreens = QtWidgets.QCheckBox("Allow screenshots"); self.chkScreens.setChecked(False)
        self.chkAnon = QtWidgets.QCheckBox("Anonymize respondent in export"); self.chkAnon.setChecked(True)
        lay.addRow("Screenshots:", self.chkScreens)
        lay.addRow("Anonymization:", self.chkAnon)
        return w

    def _build_data_tab(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        lay = QtWidgets.QFormLayout(w)
        lay.setLabelAlignment(QtCore.Qt.AlignRight)

        # Existing autosave settings
        self.chkAutosave = QtWidgets.QCheckBox("Autosave enabled")
        self.chkAutosave.setChecked(True)

        self.spinAutosave = QtWidgets.QSpinBox()
        self.spinAutosave.setRange(15, 3600)
        self.spinAutosave.setSingleStep(15)
        self.spinAutosave.setSuffix(" sec")
        self.spinAutosave.setValue(120)

        self.editAutosaveLoc = QtWidgets.QLineEdit()
        self.editAutosaveLoc.setPlaceholderText(r"%USERPROFILE%/Documents/DiscoveryAutosaves")

        self.chkAIAdvisor = QtWidgets.QCheckBox("Enable remote LLM-driven assistant")
        self.chkAIAdvisor.setChecked(True)  # Default to enabled

        # Add all form rows
        lay.addRow("Autosave:", self.chkAutosave)
        lay.addRow("Autosave interval:", self.spinAutosave)
        lay.addRow("Autosave location:", self.editAutosaveLoc)
        lay.addRow("AI Advisor:", self.chkAIAdvisor)  # NEW row

        return w

    def _build_export_tab(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        lay = QtWidgets.QFormLayout(w)
        lay.setLabelAlignment(QtCore.Qt.AlignRight)
        self.chkExportGate = QtWidgets.QCheckBox("Require progress threshold to enable Export"); self.chkExportGate.setChecked(True)
        self.spinThreshold = QtWidgets.QSpinBox(); self.spinThreshold.setRange(0, 100); self.spinThreshold.setSuffix(" %"); self.spinThreshold.setValue(60); self.spinThreshold.setEnabled(self.chkExportGate.isChecked())
        self.chkExportGate.toggled.connect(self.spinThreshold.setEnabled)
        lay.addRow("Gate Export:", self.chkExportGate)
        lay.addRow("Threshold:", self.spinThreshold)
        return w

    # ------------- Helpers -------------
    def _default_output_folder(self) -> Path:
        # Prefer Qt's Desktop path (works with OneDrive/Desktop redirection), fallback to home.
        qdesk = _qt_desktop_path()
        if qdesk and qdesk.exists():
            return qdesk
        return Path.home()

    def _choose_output_folder(self):
        start = str(Path(self.outPath.text()).expanduser()) if self.outPath.text() else str(self._default_output_folder())
        d = QtWidgets.QFileDialog.getExistingDirectory(self, "Choose distribution folder", start)
        if d:
            self.outPath.setText(d)

    def _collect_policy(self) -> dict:
        # Simple, readable structure (MVP). We'll convert to signed/binary later.
        return {
            "meta": {"project_name": "Discovery Assistant", "version": 1},
            "privacy": {
                "allow_screenshots": {"value": bool(self.chkScreens.isChecked()), "locked": True},
                "anonymize_respondent": {"value": bool(self.chkAnon.isChecked()), "locked": True}
            },
            "data": {
                "autosave_enabled": {"value": bool(self.chkAutosave.isChecked()), "locked": True},
                "autosave_interval_sec": {"value": int(self.spinAutosave.value()), "locked": False},
                "autosave_location": {
                    "value": self.editAutosaveLoc.text().strip() or r"%USERPROFILE%/Documents/DiscoveryAutosaves",
                    "locked": False},
                "ai_advisor_enabled": {"value": bool(self.chkAIAdvisor.isChecked()), "locked": True}  # NEW setting
            },
            "export_policy": {
                "require_threshold_for_export": {"value": bool(self.chkExportGate.isChecked()), "locked": True},
                "threshold_percent": {"value": int(self.spinThreshold.value()), "locked": True}
            }
        }

    # ------------- Actions -------------
    def _on_generate(self):
        """Install policy to canonical user-scope path; then optionally save a distribution copy."""
        policy = self._collect_policy()
        policy_json = json.dumps(policy, indent=2)

        # 1) Install to canonical location
        dst = _policy_path()
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(policy_json, encoding="utf-8")
            try:
                dst.chmod(0o444)  # best-effort: deter casual edits
            except Exception:
                pass
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Install error", f"Failed to install policy:\n{e}")
            return

        # Enable convenience buttons
        self.btnOpenInstalled.setEnabled(True)
        self.btnSaveDist.setEnabled(True)

        # 2) Offer to save a distribution copy now
        msg = QtWidgets.QMessageBox(self)
        msg.setWindowTitle("Configuration Complete")
        msg.setText(
            "Your local license has been installed. This device will follow these settings.\n\n"
            f"Installed at:\n{dst}\n\n"
            "Would you like to save a distribution copy now?"
        )
        save_btn = msg.addButton("Save Distribution Copy…", QtWidgets.QMessageBox.ActionRole)
        open_btn = msg.addButton("Open Installed Policy Folder", QtWidgets.QMessageBox.ActionRole)
        msg.addButton(QtWidgets.QMessageBox.Ok)
        msg.exec()

        if msg.clickedButton() is save_btn:
            self._save_distribution_copy(policy_json)
        elif msg.clickedButton() is open_btn:
            _open_folder(dst)

        self.policyInstalled.emit()

    def _save_distribution_copy(self, policy_json: str | None = None):
        base = Path(self.outPath.text()).expanduser() if self.outPath.text().strip() else self._default_output_folder()
        default_name = "governance.pol"
        dest_str, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save distribution copy", str(base / default_name),
            "Policy Files (*.pol);;All Files (*)"
        )
        if not dest_str:
            return

        dest = Path(dest_str)
        try:
            if policy_json is None:
                policy_json = _policy_path().read_text(encoding="utf-8")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(policy_json, encoding="utf-8")
            self._last_distribution_target = dest
            QtWidgets.QMessageBox.information(self, "Saved", f"Distribution copy saved:\n{dest}")
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Copy failed", f"Could not save distribution copy:\n{e}")
