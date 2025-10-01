import sys, shutil, os


# Set Qt plugin path before importing PySide6
if hasattr(sys, 'frozen'):
    # When running as PyInstaller bundle
    plugin_path = os.path.join(sys._MEIPASS, 'PySide6', 'plugins')
else:
    # When running as script
    from PySide6 import QtCore
    plugin_path = os.path.join(os.path.dirname(QtCore.__file__), 'plugins')

os.environ['QT_PLUGIN_PATH'] = plugin_path

from pathlib import Path
from PySide6 import QtCore, QtGui, QtWidgets
from bootstrap.fonts import load_app_fonts, apply_default_font
from discovery_assistant.baselogger import BaseLogger, logging
from ui.main_window import MainWindow
from discovery_assistant.ui.bootstrap_splash import BootstrapSplash
from discovery_assistant.admin_auth import verify_admin_password, VerifyResult
from discovery_assistant.admin_wizard import AdminSetupWizard
from discovery_assistant.policy_store import install_policy_from
import discovery_assistant.constants as constants
from discovery_assistant.ui.launch_card import LaunchCard
import discovery_assistant.resources as resources


APP_NAME = "Discovery Assistant"
APP_VERSION = "0.1.0"
DISPLAY_VERSION = "v0.1"


class _NoWheelOnInputs(QtCore.QObject):
    """
    Block accidental mouse-wheel changes on:
      - QComboBox (unless popup is open)
      - QAbstractSpinBox family (QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit, QDateTimeEdit, etc.)
        unless the widget has keyboard focus.

    Works even when the wheel event lands on child widgets (e.g. the internal QLineEdit),
    or when Qt routes by cursor position.
    """

    @staticmethod
    def _ancestor_of_types(w: QtWidgets.QWidget, types):
        while isinstance(w, QtWidgets.QWidget) and w is not None:
            if isinstance(w, types):
                return w
            w = w.parent()
        return None

    def eventFilter(self, obj, ev):
        if ev.type() != QtCore.QEvent.Wheel:
            return super().eventFilter(obj, ev)

        # 1) Check target via parent chain of the receiver (obj)
        combo = self._ancestor_of_types(obj, QtWidgets.QComboBox)
        spin = self._ancestor_of_types(obj, QtWidgets.QAbstractSpinBox)

        # 2) If not found, also check the widget under the mouse cursor
        if combo is None and spin is None:
            # Qt6: globalPosition() -> QPointF ; Qt5: globalPos() -> QPoint
            try:
                gp = ev.globalPosition().toPoint()
            except AttributeError:
                gp = ev.globalPos()
            under = QtWidgets.QApplication.widgetAt(gp)
            if under is not None:
                if combo is None:
                    combo = self._ancestor_of_types(under, QtWidgets.QComboBox)
                if spin is None:
                    spin = self._ancestor_of_types(under, QtWidgets.QAbstractSpinBox)

        # --- Rules ---
        # Combobox: only allow wheel when popup is visible (so the list can scroll)
        if combo is not None:
            if not combo.view().isVisible():
                ev.ignore()
                return True
            return super().eventFilter(obj, ev)

        # Spinbox family (includes QDateEdit/QTimeEdit/QDateTimeEdit):
        # only allow wheel when the widget has keyboard focus
        if spin is not None:
            if not spin.hasFocus():
                ev.ignore()
                return True
            return super().eventFilter(obj, ev)

        return super().eventFilter(obj, ev)


# -------- Policy paths & helpers (portable user-scope; easy for SMBs) --------
def canonical_policy_path() -> Path:
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / APP_NAME / "policy"
    elif sys.platform.startswith("win"):
        base = Path.home() / "AppData" / "Local" / APP_NAME / "policy"
    else:
        base = Path.home() / f".{APP_NAME.lower().replace(' ', '_')}" / "policy"
    base.mkdir(parents=True, exist_ok=True)
    return base / "governance.pol"


def policy_installed_and_valid() -> bool:
    pol = canonical_policy_path()
    if not pol.exists():
        return False
    # TODO: replace with your real signature verification
    # from policy_loader import verify_and_load_policy, PolicyError
    # try:
    #     verify_and_load_policy(str(pol), PUBLIC_KEY_BYTES)
    #     return True
    # except PolicyError as e:
    #     logging.error(f"Policy invalid: {e}")
    #     return False
    return True  # TEMP while wiring up


def install_policy_from(src_path: str) -> tuple[bool, str]:
    """Copy dropped file to canonical path, keep a .bak, set read-only."""
    try:
        src = Path(src_path)
        if not src.exists():
            return False, "File does not exist."
        # TODO: verify signature BEFORE installing; if invalid, return False with reason.
        dst = canonical_policy_path()
        shutil.copy2(src, dst)
        shutil.copy2(src, dst.with_suffix(".bak"))
        try:
            dst.chmod(0o444)
            dst.with_suffix(".bak").chmod(0o444)
        except Exception:
            pass
        return True, "Policy installed."
    except Exception as e:
        return False, f"Failed to install policy: {e}"


def bootstrap_override_active() -> bool:
    """
    Force Admin (bootstrap) mode at startup if:
      - '--bootstrap' flag is present, OR
      - APP_FORCE_BOOTSTRAP=1 in env, OR
      - Shift key held at launch
    """
    if "--bootstrap" in sys.argv:
        return True
    if os.getenv("APP_FORCE_BOOTSTRAP") == "1":
        return True
    mods = QtGui.QGuiApplication.queryKeyboardModifiers()
    return bool(mods & QtCore.Qt.ShiftModifier)


# -------- Launchers --------
def launch_main_window(app: QtWidgets.QApplication) -> None:
    # If already created, focus it
    existing = getattr(app, "_main_window", None)
    if existing is not None and existing.isVisible():
        existing.raise_()
        existing.activateWindow()
        return

    win = MainWindow()
    win.setWindowTitle(f"{APP_NAME} [{DISPLAY_VERSION}]")
    win.setWindowIcon(QtGui.QIcon(str(constants.ICON_PATH)))  # global icon already set, but safe

    # Size & center (keep your existing sizing logic if you have one)
    screen = app.primaryScreen()
    avail = screen.availableGeometry()
    target_w = max(960, min(int(avail.width() * 0.75), 1440))
    target_h = max(640, min(int(avail.height() * 0.80), 900))
    win.resize(target_w, target_h)
    win.setMinimumSize(QtCore.QSize(960, 640))
    frame = win.frameGeometry()
    frame.moveCenter(avail.center())
    win.move(frame.topLeft())

    win.show()
    app._main_window = win


def show_bootstrap(app: QtWidgets.QApplication) -> None:
    print("DEBUG: show_bootstrap() called")

    from discovery_assistant.ui.bootstrap_splash import BootstrapSplash
    splash = BootstrapSplash()
    splash.setWindowIcon(QtGui.QIcon(str(constants.ICON_PATH)))

    # Position on the same screen as the cursor
    cursor_pos = QtGui.QCursor.pos()
    screen = QtWidgets.QApplication.screenAt(cursor_pos)
    if screen is None:
        screen = QtWidgets.QApplication.primaryScreen()

    screen_geometry = screen.geometry()
    x = screen_geometry.x() + (screen_geometry.width() - splash.width()) // 2
    y = screen_geometry.y() + (screen_geometry.height() - splash.height()) // 2
    splash.move(x, y)

    print("DEBUG: BootstrapSplash created and positioned")
    splash.show()
    print("DEBUG: BootstrapSplash.show() called")

    # Force the window to be visible and on top
    splash.raise_()
    splash.activateWindow()
    print("DEBUG: Window raised and activated")

    # Rest of your existing code...
    def on_drop(path: str):
        p = QtCore.QDir.toNativeSeparators(path)
        if not p.lower().endswith(".pol"):
            QtWidgets.QMessageBox.warning(splash, "Invalid file", "Please drop a .pol configuration file.")
            return
        try:
            install_policy_from(Path(p))
        except Exception as e:
            QtWidgets.QMessageBox.critical(splash, "Policy Error", f"Could not install policy:\n{e}")
            return
        splash.close()
        launch_main_window(app)

    def on_admin(pwd: str):
        result = verify_admin_password(pwd)
        if result == VerifyResult.FAIL:
            QtWidgets.QMessageBox.warning(splash, "Admin", "Incorrect password.")
            return

        splash.close()

        wizard = AdminSetupWizard(force_password_change=(result == VerifyResult.OK_MUST_CHANGE))
        wizard.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        wizard.policyGenerated.connect(lambda: launch_main_window(app))

        # Position wizard on cursor screen too
        cursor_pos = QtGui.QCursor.pos()
        screen = QtWidgets.QApplication.screenAt(cursor_pos)
        if screen is None:
            screen = app.primaryScreen()

        screen_geometry = screen.geometry()
        if screen_geometry.width() >= 1920 and screen_geometry.height() >= 1080:
            wizard.show()
            # Center wizard on cursor screen
            wizard_x = screen_geometry.x() + (screen_geometry.width() - wizard.width()) // 2
            wizard_y = screen_geometry.y() + (screen_geometry.height() - wizard.height()) // 2
            wizard.move(wizard_x, wizard_y)
        else:
            wizard.showMaximized()

        result = wizard.exec()
        if result == QtWidgets.QDialog.Accepted:
            pass
        else:
            logging.info("Admin setup wizard cancelled")

        app._admin_wizard = wizard

    splash.configDropped.connect(on_drop)
    splash.adminPasswordEntered.connect(on_admin)
    print("DEBUG: Signals connected, bootstrap should be visible")


def make_app():
    app = QtWidgets.QApplication(sys.argv)
    app.installEventFilter(_NoWheelOnInputs(app))
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setWindowIcon(QtGui.QIcon(str(constants.ICON_PATH)))
    app.setStyle('Fusion')
    app.setStyleSheet("""
        QToolTip {
            background-color: #000000;
            color: #F9FAFB;
            border: 1px solid #374151;
            padding: 6px 8px;
            font-size: 11px;
        }
    """)

    # Logging
    BaseLogger().set_logging_configuration(
        log_level=logging.INFO,
        file_config=None,
        file_log_level=logging.ERROR
    )
    logging.info("✅ Logger is running!")

    # HiDPI handling
    app.setHighDpiScaleFactorRoundingPolicy(
        QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # Fonts (best-effort)
    try:
        load_app_fonts()
        apply_default_font(app)
    except Exception as e:
        logging.warning(f"Font init skipped: {e}")

    # Show launch card first
    launch_card = LaunchCard()
    launch_card.show_with_animation()
    result = launch_card.exec()  # Wait for launch card to complete

    print("DEBUG: Launch card completed")

    # After launch card, proceed with normal flow
    try:
        force_bootstrap = bootstrap_override_active()
    except Exception as e:
        logging.warning(f"bootstrap_override_active() failed: {e}")
        force_bootstrap = False

    if force_bootstrap or not policy_installed_and_valid():
        logging.info("Launching in ADMIN/BOOTSTRAP mode.")
        print("DEBUG: About to call show_bootstrap")
        show_bootstrap(app)
    else:
        logging.info("Launching in RESPONDENT mode.")
        launch_main_window(app)

    return app


if __name__ == "__main__":
    app = make_app()
    sys.exit(app.exec())
