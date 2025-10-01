from PySide6 import QtCore, QtGui, QtWidgets
import discovery_assistant.constants as constants
from discovery_assistant.ui.widgets.splitter import IconSplitter
from discovery_assistant.ui.widgets.navigation import Navigation
from discovery_assistant.baselogger import logging
from discovery_assistant.ui.widgets.status import StatusWidget
from discovery_assistant.ui.widgets.settings import SettingsWidget
from discovery_assistant.storage import initialize_database, reset_database
from importlib import import_module
from PySide6.QtCore import QResource

# --- Storage imports ---
from discovery_assistant.storage import (
    get_policy_dir,
    get_policy_path,
    initialize_file_structure,
    get_files_dir,
    FileManager
)
from pathlib import Path
import shutil

SIDEBAR_MIN = 280
SIDEBAR_DEFAULT = 340
BREAKPOINT = 1100
_LOGGER = logging.getLogger('DISCOVERY.main')

print(f"Resource exists: {QResource(':/aiAdvisor_active_icon.svg').isValid()}")

# ============== Policy helper functions ==============
APP_NAME = "Discovery Assistant"

def _open_policy_folder(parent: QtWidgets.QWidget | None = None) -> None:
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtCore import QUrl
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(get_policy_dir())))

def _install_policy_from(src: Path) -> Path:
    """Copy a policy file into the canonical location and make it read-only (best-effort)."""
    dst = get_policy_path()
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    try:
        dst.chmod(0o444)  # deter casual edits (not security)
    except Exception:
        pass
    return dst

def _remove_policy() -> None:
    p = get_policy_path()
    if p.exists():
        try:
            p.chmod(0o666)
        except Exception:
            pass
        p.unlink()

# ===============================================----->>
# Main Window (owns menubar, statusbar, actions) ------->>
# ===============================================----->>

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QtGui.QIcon(str(constants.ICON_PATH)))

        # Calculate responsive sizing before other initialization
        self._setup_responsive_sizing()

        # Initialize database on startup
        if not initialize_database():
            QtWidgets.QMessageBox.critical(
                self, "Database Error",
                "Failed to initialize database. The application may not function correctly."
            )
            _LOGGER.error("Database initialization failed during startup")

        # ====== Status bar (distinct footer with optional progress) ======
        sb = QtWidgets.QStatusBar(self)
        sb.setObjectName("footer")
        sb.setSizeGripEnabled(True)  # turn on native size grip (if supported by OS/theme)

        sb.setStyleSheet("""
        QStatusBar#footer {
            background: #D7DDE5;              /* darker gray */
            border-top: 1px solid #C0C7D0;
            color: #000;                       /* message text color */
            padding: 6px 10px;                 /* extra vertical height */
        }
        QStatusBar#footer QLabel {             /* label used by showMessage(...) */
            color: #000;
        }
        QStatusBar::item { border: 0; }
        """)
        self.setStatusBar(sb)

        base_h = sb.sizeHint().height()
        sb.setMinimumHeight(base_h + 10)

        # Progress bar widget
        self.progress = QtWidgets.QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(16)  # was 14; small bump looks nicer
        self.progress.setFixedWidth(220)
        self.progress.setStyleSheet("QProgressBar { margin: 0 8px; }")
        self.progress.hide()
        self.statusBar().addPermanentWidget(self.progress)

        # Central content widget
        self.content = ContentContainer()
        self.setCentralWidget(self.content)

        # Build menus on the QMainWindow
        self._make_actions()

        # Create file directories
        initialize_file_structure()

        # Sync QAction <-> content sidebar state
        self.content.sidebarToggled.connect(self.toggleSidebarAct.setChecked)
        self.showMaximized()
        self.statusBar().showMessage("Ready")
        _LOGGER.info(f'Main window initialized')

        QtCore.QTimer.singleShot(0, self._resize_to_screen)


    def _setup_responsive_sizing(self):
        """Calculate responsive window dimensions for restore behavior."""
        screen = QtWidgets.QApplication.primaryScreen().geometry()
        screen_width = screen.width()
        screen_height = screen.height()

        # Calculate appropriate sizes based on screen resolution
        if screen_height >= 1440:
            self._normal_size = QtCore.QSize(1200, 900)
            self.setMinimumSize(1000, 750)
        elif screen_height >= 1080:
            self._normal_size = QtCore.QSize(1100, 750)
            self.setMinimumSize(900, 650)
        else:
            self._normal_size = QtCore.QSize(1000, 650)
            self.setMinimumSize(850, 600)

        # Center position for when restored
        self._normal_position = QtCore.QPoint(
            (screen_width - self._normal_size.width()) // 2,
            (screen_height - self._normal_size.height()) // 2
        )

    def _resize_to_screen(self):
        """Resize to fill screen with maximum dimensions, centered if screen is larger."""
        screen = QtWidgets.QApplication.screenAt(self.pos())
        if screen is None:
            screen = QtWidgets.QApplication.primaryScreen()

        available = screen.availableGeometry()

        # Define maximum dimensions
        max_width = 1600
        max_height = 1000

        # Calculate actual dimensions
        actual_width = min(available.width(), max_width)
        actual_height = min(available.height() - 100, max_height)

        # Center the window on screen
        x = available.x() + (available.width() - actual_width) // 2
        y = available.y() + (available.height() - actual_height) // 2

        self.setGeometry(x, y, actual_width, actual_height)

    def changeEvent(self, event):
        """Handle window state changes to apply responsive sizing on restore."""
        if event.type() == QtCore.QEvent.WindowStateChange:
            if not self.isMaximized() and not self.isMinimized():
                # User restored from maximized - apply responsive size
                self.resize(self._normal_size)
                self.move(self._normal_position)
        super().changeEvent(event)

    # ======= Progress helpers you can call from controllers/workers =======
    def begin_busy(self, message="Working…"):
        """Indeterminate/busy spinner in the footer."""
        self.statusBar().showMessage(message)
        self.progress.setRange(0, 0)    # busy mode
        self.progress.show()

    def end_busy(self):
        self.progress.hide()
        # restore determinate range so later use is clean
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.statusBar().clearMessage()

    def start_progress(self, total_steps: int, message="Working…"):
        self.statusBar().showMessage(message)
        self.progress.setRange(0, max(1, total_steps))
        self.progress.setValue(0)
        self.progress.show()

    def advance_progress(self, step_value: int | None = None, *, inc: int | None = None):
        if inc is not None:
            self.progress.setValue(min(self.progress.maximum(), self.progress.value() + inc))
        elif step_value is not None:
            self.progress.setValue(min(self.progress.maximum(), step_value))
        if self.progress.value() >= self.progress.maximum():
            self.end_busy()

    # ===== Menus & actions (LIVE ON QMainWindow) =====
    def _make_actions(self):
        # File
        self.newSessionAct = QtGui.QAction("&New Session…", self)
        self.newSessionAct.setShortcut(QtGui.QKeySequence.New)
        self.newSessionAct.triggered.connect(self._new_session)

        self.saveDraftAct = QtGui.QAction("&Save Draft", self)
        self.saveDraftAct.setShortcut(QtGui.QKeySequence.Save)
        self.saveDraftAct.triggered.connect(self._save_draft)

        self.submitPackageAct = QtGui.QAction("&Submit Package…", self)
        self.submitPackageAct.setShortcut("Ctrl+Enter")
        self.submitPackageAct.triggered.connect(self._submit_package)

        self.exportJsonAct = QtGui.QAction("Export &JSON…", self)
        self.exportJsonAct.setShortcut("Ctrl+E")
        self.exportJsonAct.triggered.connect(self._export_json)

        self.exitAct = QtGui.QAction("E&xit", self)
        self.exitAct.setShortcut(QtGui.QKeySequence.Quit)
        self.exitAct.triggered.connect(self.close)

        # Database actions (development)
        self.resetDatabaseAct = QtGui.QAction("&Reset Database...", self)
        self.resetDatabaseAct.triggered.connect(self._reset_database)

        # Database actions (development)
        self.resetDatabaseAct = QtGui.QAction("&Reset Database...", self)
        self.resetDatabaseAct.triggered.connect(self._reset_database)

        # ADD THESE NEW FILE MANAGEMENT ACTIONS:
        self.showFilesDirAct = QtGui.QAction("Show &Files Directory...", self)
        self.showFilesDirAct.triggered.connect(self._show_files_directory)

        self.showStorageStatsAct = QtGui.QAction("Storage &Statistics...", self)
        self.showStorageStatsAct.triggered.connect(self._show_storage_stats)

        # Edit
        self.undoAct = QtGui.QAction("&Undo", self)
        self.undoAct.setShortcut(QtGui.QKeySequence.Undo)
        self.undoAct.triggered.connect(self._route_undo)

        self.redoAct = QtGui.QAction("&Redo", self)
        self.redoAct.setShortcut(QtGui.QKeySequence.Redo)
        self.redoAct.triggered.connect(self._route_redo)

        self.cutAct = QtGui.QAction("Cu&t", self)
        self.cutAct.setShortcut(QtGui.QKeySequence.Cut)
        self.cutAct.triggered.connect(self._route_cut)

        self.copyAct = QtGui.QAction("&Copy", self)
        self.copyAct.setShortcut(QtGui.QKeySequence.Copy)
        self.copyAct.triggered.connect(self._route_copy)

        self.pasteAct = QtGui.QAction("&Paste", self)
        self.pasteAct.setShortcut(QtGui.QKeySequence.Paste)
        self.pasteAct.triggered.connect(self._route_paste)

        # View
        self.toggleSidebarAct = QtGui.QAction("&Sidebar", self, checkable=True)
        self.toggleSidebarAct.setShortcut("Ctrl+B")
        self.toggleSidebarAct.setChecked(True)
        self.toggleSidebarAct.toggled.connect(self.content.toggle_sidebar)

        # Policy (NEW)
        self.showPolicyFolderAct = QtGui.QAction("Show &Installed Policy Folder", self)
        self.showPolicyFolderAct.triggered.connect(lambda: _open_policy_folder(self))

        self.replacePolicyAct = QtGui.QAction("&Replace Policy…", self)
        self.replacePolicyAct.triggered.connect(self._replace_policy)

        self.deletePolicyAct = QtGui.QAction("&Delete Policy…", self)
        self.deletePolicyAct.triggered.connect(self._delete_policy)

        # Help
        self.aboutAct = QtGui.QAction("&About", self)
        self.aboutAct.triggered.connect(self._about)

        # Menubar + styling
        mb = self.menuBar()
        mb.setStyleSheet(""" QMenuBar::item { padding: 2px 12px; } """)

        file_menu = mb.addMenu("&File")
        file_menu.addAction(self.newSessionAct)
        file_menu.addSeparator()
        file_menu.addAction(self.saveDraftAct)
        file_menu.addAction(self.submitPackageAct)
        file_menu.addAction(self.exportJsonAct)
        file_menu.addSeparator()

        file_menu.addAction(self.showFilesDirAct)
        file_menu.addAction(self.showStorageStatsAct)
        file_menu.addSeparator()

        file_menu.addAction(self.exitAct)
        file_menu.addSeparator()
        file_menu.addAction(self.resetDatabaseAct)

        edit_menu = mb.addMenu("&Edit")
        edit_menu.addAction(self.undoAct)
        edit_menu.addAction(self.redoAct)
        edit_menu.addSeparator()
        edit_menu.addAction(self.cutAct)
        edit_menu.addAction(self.copyAct)
        edit_menu.addAction(self.pasteAct)

        view_menu = mb.addMenu("&View")
        view_menu.addAction(self.toggleSidebarAct)

        # NEW: Policy menu
        policy_menu = mb.addMenu("&Policy")
        policy_menu.addAction(self.showPolicyFolderAct)
        policy_menu.addAction(self.replacePolicyAct)
        policy_menu.addSeparator()
        policy_menu.addAction(self.deletePolicyAct)

        help_menu = mb.addMenu("&Help")
        help_menu.addAction(self.aboutAct)

        # Style each popup menu (avoid bleed/extra gutters)
        popup_css = """
            QMenu { margin: 0; padding: 0; border: 1px solid rgba(0,0,0,0.20); background: palette(base); }
            QMenu::item { padding: 4px 20px 4px 12px; margin: 0; border: none; }
            QMenu::item:selected { background: palette(highlight); color: palette(highlighted-text); }
            QMenu::item:disabled { color: palette(disabled, text); }
            QMenu::separator { height: 1px; margin: 4px 0; background: rgba(0,0,0,0.15); }
            QMenu::icon { width: 0px; }
            QMenu::indicator { width: 0px; }
            QMenu::right-arrow { margin-right: 6px; }
        """
        for m in (file_menu, edit_menu, view_menu, policy_menu, help_menu):
            m.setStyleSheet(popup_css)
            m.setSeparatorsCollapsible(False)

    def _show_files_directory(self):
        """Open the files directory with a warning dialog"""
        # Show warning first
        reply = QtWidgets.QMessageBox.warning(
            self,
            "Files Directory Access",
            "You are about to open the application's file storage directory.\n\n"
            "⚠️ WARNING: Do not modify, move, or delete any files in this directory. "
            "Doing so may cause application instability and data loss.\n\n"
            "This directory is provided for read-only viewing of your attached files.\n\n"
            "Continue?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )

        if reply == QtWidgets.QMessageBox.Yes:
            files_dir = get_files_dir()
            files_dir.mkdir(parents=True, exist_ok=True)
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(files_dir)))

    def _show_storage_stats(self):
        """Show storage statistics dialog"""
        stats = FileManager.get_storage_stats()

        # Format file size
        def format_bytes(bytes_val):
            for unit in ['B', 'KB', 'MB', 'GB']:
                if bytes_val < 1024:
                    return f"{bytes_val:.1f} {unit}"
                bytes_val /= 1024
            return f"{bytes_val:.1f} TB"

        message = f"File Storage Statistics\n\n"
        message += f"Total Files: {stats['total_files']}\n"
        message += f"Total Size: {format_bytes(stats['total_size_bytes'])}\n\n"

        if stats['sections']:
            message += "By Section:\n"
            for section, section_stats in stats['sections'].items():
                message += f"\n{section.replace('_', ' ').title()}:\n"
                message += f"  • Attachments: {section_stats['attachments']}\n"
                message += f"  • Screenshots: {section_stats['screenshots']}\n"
                message += f"  • Size: {format_bytes(section_stats['size_bytes'])}\n"
        else:
            message += "No files stored yet."

        QtWidgets.QMessageBox.information(self, "Storage Statistics", message)

    # ===== Edit menu routing to the focused widget =====
    def _focused_widget(self):
        return self.focusWidget()

    def _route_undo(self):
        w = self._focused_widget()
        if hasattr(w, "undo"): w.undo()

    def _route_redo(self):
        w = self._focused_widget()
        if hasattr(w, "redo"): w.redo()

    def _route_cut(self):
        w = self._focused_widget()
        if hasattr(w, "cut"): w.cut()

    def _route_copy(self):
        w = self._focused_widget()
        if hasattr(w, "copy"): w.copy()

    def _route_paste(self):
        w = self._focused_widget()
        if hasattr(w, "paste"): w.paste()


    # ===== File / Help stubs =====
    def _new_session(self):
        self.statusBar().showMessage("New session…", 2000)

    def _save_draft(self):
        self.statusBar().showMessage("Draft saved", 2000)

    def _submit_package(self):
        # Example long task hook:
        # self.begin_busy("Submitting package…")
        self.statusBar().showMessage("Submitting package…", 2000)

    def _export_json(self):
        # Example long task hook:
        # self.begin_busy("Exporting JSON…")
        self.statusBar().showMessage("Exported JSON", 2000)

    def _about(self):
        QtWidgets.QMessageBox.about(self, "About", "Discovery — Desktop Discovery Tool\n© YourCo")

    # ===== Policy menu handlers =====
    def _replace_policy(self):
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Choose new policy (.pol)", str(Path.home()),
            "Policy Files (*.pol);;All Files (*)"
        )
        if not fn:
            return
        src = Path(fn)
        if src.suffix.lower() != ".pol":
            QtWidgets.QMessageBox.warning(self, "Invalid file", "Please select a .pol configuration file.")
            return
        try:
            dst = _install_policy_from(src)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Replace failed", f"Could not replace policy:\n{e}")
            return
        QtWidgets.QMessageBox.information(
            self, "Policy replaced",
            f"Installed at:\n{dst}\n\nPlease restart the app for changes to take full effect."
        )

    def _delete_policy(self):
        p = get_policy_path()
        if not p.exists():
            QtWidgets.QMessageBox.information(self, "No policy installed", "No installed policy was found.")
            return
        if QtWidgets.QMessageBox.question(
            self, "Delete Policy",
            "Delete the installed policy?\nThe app will require admin setup on next launch.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        ) == QtWidgets.QMessageBox.Yes:
            try:
                _remove_policy()
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Delete failed", f"Could not delete policy:\n{e}")
                return
            QtWidgets.QMessageBox.information(self, "Deleted", "Policy deleted. Please restart the app.")

    def _reset_database(self):
        """Handle database reset with confirmation dialog and file cleanup."""
        reply = QtWidgets.QMessageBox.question(
            self, "Reset Database",
            "This will permanently delete ALL data and files in the database.\n\n"
            "This includes:\n"
            "• All form data and entries\n"
            "• All attached documents and screenshots\n"
            "• All application files\n\n"
            "Are you sure you want to continue?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )

        if reply == QtWidgets.QMessageBox.Yes:
            self.begin_busy("Resetting database and cleaning up files...")

            try:
                # Clean up all files first
                deleted_files = FileManager.cleanup_all_files()

                # Then reset database
                success = reset_database()

                if success:
                    # Clear UI fields after successful reset
                    self._clear_all_tab_fields()

                    QtWidgets.QMessageBox.information(
                        self, "Database Reset",
                        f"Database has been reset successfully.\n"
                        f"Cleaned up {deleted_files} files."
                    )
                    self.statusBar().showMessage("Database reset completed", 3000)
                else:
                    QtWidgets.QMessageBox.critical(
                        self, "Reset Failed",
                        "Failed to reset database. Check logs for details."
                    )
            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self, "Reset Error",
                    f"An error occurred while resetting the database:\n{e}"
                )
                _LOGGER.error(f"Database reset error: {e}")
            finally:
                self.end_busy()

    def _clear_all_tab_fields(self):
        """Clear fields in all loaded tabs after database reset."""
        # Clear RespondentTab if it exists
        if hasattr(self.content, '_pages') and 'Respondent' in self.content._pages:
            respondent_tab = self.content._pages['Respondent']
            if hasattr(respondent_tab, 'clear_fields'):
                respondent_tab.clear_fields()

        # Clear OrgMapTab if it exists
        if hasattr(self.content, '_pages') and 'Org Map' in self.content._pages:
            orgmap_tab = self.content._pages['Org Map']
            if hasattr(orgmap_tab, 'clear_fields'):
                orgmap_tab.clear_fields()

        # Clear ProcessesTab if it exists
        if hasattr(self.content, '_pages') and 'Processes' in self.content._pages:
            processes_tab = self.content._pages['Processes']
            if hasattr(processes_tab, 'clear_fields'):
                processes_tab.clear_fields()

        # Clear PainPointsTab if it exists
        if hasattr(self.content, '_pages') and 'Pain Points' in self.content._pages:
            painpoints_tab = self.content._pages['Pain Points']
            if hasattr(painpoints_tab, 'clear_fields'):
                painpoints_tab.clear_fields()

        # Clear DataSourcesTab if it exists
        if hasattr(self.content, '_pages') and 'Data Sources' in self.content._pages:
            datasources_tab = self.content._pages['Data Sources']
            if hasattr(datasources_tab, 'clear_fields'):
                datasources_tab.clear_fields()

        # Clear ComplianceTab if it exists
        if hasattr(self.content, '_pages') and 'Compliance' in self.content._pages:
            compliance_tab = self.content._pages['Compliance']
            if hasattr(compliance_tab, 'clear_fields'):
                compliance_tab.clear_fields()

        # Clear FeatureIdeasTab if it exists
        if hasattr(self.content, '_pages') and 'Feature Ideas' in self.content._pages:
            feature_ideas_tab = self.content._pages['Feature Ideas']
            if hasattr(feature_ideas_tab, 'clear_fields'):
                feature_ideas_tab.clear_fields()

        # Clear ReferenceLibraryTab if it exists
        if hasattr(self.content, '_pages') and 'Reference Library' in self.content._pages:
            reference_library_tab = self.content._pages['Reference Library']
            if hasattr(reference_library_tab, 'clear_fields'):
                reference_library_tab.clear_fields()

        # Clear TimeResourceManagementTab if it exists
        if hasattr(self.content, '_pages') and 'Time & Resource Management' in self.content._pages:
            time_resource_tab = self.content._pages['Time & Resource Management']
            if hasattr(time_resource_tab, 'clear_fields'):
                time_resource_tab.clear_fields()


class ContentContainer(QtWidgets.QWidget):
    sidebarToggled = QtCore.Signal(bool)  # inform MainWindow to sync QAction

    def __init__(self):
        super().__init__()

        # Check AI Advisor policy first, before building UI
        self.ai_advisor_enabled = self._check_ai_advisor_policy()
        self._original_sidebar_width = SIDEBAR_DEFAULT
        self._ai_advisor_active = False

        self.settings = QtCore.QSettings("YourCo", "RAGDiscovery")

        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Header
        self.header_frame = QtWidgets.QFrame(self)
        self.header_frame.setObjectName("header")
        self.header_frame.setFixedHeight(70)
        self.header_frame.setStyleSheet("""
            background: #FFFFFF;
            border-bottom: 1px solid #C0C7D0; 
        """)

        self.header_layout = QtWidgets.QHBoxLayout(self.header_frame)
        self.header_layout.setContentsMargins(12, 8, 12, 8)
        self.header_layout.setSpacing(10)

        # Logo
        self.logo = QtWidgets.QLabel(self.header_frame)
        self.logo.setObjectName("logo")
        self.logo.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)

        pm = QtGui.QPixmap(str(constants.LOGO_PATH))
        if not pm.isNull():
            self.logo.setPixmap(pm)
            self.logo.setScaledContents(False)
            self.logo.setFixedSize(pm.size())

        self.header_layout.addWidget(self.logo, 0, QtCore.Qt.AlignVCenter)

        family_name = None
        fid = QtGui.QFontDatabase.addApplicationFont(str(constants.FONT_MONTSERRAT_SEMIBOLD))
        if fid != -1:
            fams = QtGui.QFontDatabase.applicationFontFamilies(fid)
            if fams:
                family_name = fams[0]

        self.tool_title = QtWidgets.QLabel("DISCOVERY ASSISTANT", self.header_frame)
        self.tool_title.setObjectName("toolTitle")
        self.tool_title.setFrameShape(QtWidgets.QFrame.NoFrame)
        title_font = QtGui.QFont(family_name or "Segoe UI", 12)
        title_font.setWeight(QtGui.QFont.DemiBold)
        title_font.setHintingPreference(QtGui.QFont.PreferFullHinting)
        self.tool_title.setFont(title_font)
        self.tool_title.setStyleSheet("""
        #toolTitle {
            color: #111;
            border: none;
            background: transparent;
            padding: 0; margin: 0;
        }
        """)

        self.header_layout.addWidget(self.tool_title, 0, QtCore.Qt.AlignVCenter)
        self.header_layout.addStretch(1)

        # AI Advisor button - only add if enabled in policy
        if self.ai_advisor_enabled:
            self.powerButton = self._create_power_button()
            self.header_layout.addWidget(self.powerButton, 0, QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        # Export button anchored right
        self.export_button = QtWidgets.QPushButton("Export", self.header_frame)
        self.export_button.setAttribute(QtCore.Qt.WA_AlwaysShowToolTips, True)
        self.export_button.setAttribute(QtCore.Qt.WA_Hover, True)
        self.export_button.installEventFilter(self)

        self.export_button.setObjectName("exportBtn")
        self.export_button.setCursor(QtCore.Qt.PointingHandCursor)
        self.export_button.setToolTip("Fill required fields to enable export")
        self.export_button.setFixedHeight(32)
        self.export_button.setMinimumWidth(60)
        self.export_button.setStyleSheet("""
                QPushButton {
                background-color: black;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #FF4136; 
            }
            QPushButton:pressed {
                background-color: #555555; 
            }
            QPushButton#exportBtn:disabled {
            background: #E9ECEF;  
            color: #8A8F98;   
            border-color: #D0D7DE;       
        }
        """)
        self.export_button.setEnabled(False)
        self._set_export_tooltip_for_state(disabled=True)
        self.header_layout.addWidget(self.export_button, 0,
                                     QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.main_layout.addWidget(self.header_frame)

        self.shadowStrip = QtWidgets.QWidget(self)
        self.shadowStrip.setFixedHeight(12)  # make taller/thinner to taste (8–16)
        self.shadowStrip.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.shadowStrip.setStyleSheet("""
            background: qlineargradient(x1:0,y1:0, x2:0,y2:1,
                stop:0 rgba(0,0,0,20),   /* top opacity */
                stop:1 rgba(0,0,0,0));   /* fade to transparent */
        """)
        self.shadowStrip.raise_()

        # Splitter: main (left) + sidebar (right)
        self.splitter = IconSplitter(QtCore.Qt.Horizontal)
        self.splitter.setHandleWidth(10)

        # Handle chrome + hover/pressed states
        self.splitter.setStyleSheet("""
        QSplitter::handle {
            background-color: rgba(245,250,255,0.88);
        }
        QSplitter::handle:hover {
            background-color: rgba(245,250,255,0.28);
        }
        QSplitter::handle:pressed {
            background-color: rgba(245,250,255,0.65);
        }
        QSplitter::handle:horizontal {
            border-left: 1px solid rgba(200,200,200,0.35);
            border-right: 1px solid rgba(255,255,255,0.05);
        }
        QSplitter::handle:vertical {
            border-top: 1px solid rgba(0,0,0,0.35);
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        """)

        left_pane = self._build_mainstack()  # now returns the container (nav + stack)
        self.sidebar = self._build_sidebar()
        self.splitter.addWidget(left_pane)
        self.splitter.addWidget(self.sidebar)
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, True)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        self.sidebar.setMinimumWidth(SIDEBAR_MIN)
        self.sidebar.setMaximumWidth(520)
        self.main_layout.addWidget(self.splitter, 1)

        # Layout restore + auto-collapse
        self._restore_layout()
        self.installEventFilter(self)

    def _position_shadow(self):
        y = self.header_frame.geometry().bottom()
        self.shadowStrip.setGeometry(0, y, self.width(), self.shadowStrip.height())
        self.shadowStrip.raise_()  # <- keep it under the header so tooltips work

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._position_shadow()

    def showEvent(self, ev):
        super().showEvent(ev)
        # ensure we reposition after the first layout pass
        QtCore.QTimer.singleShot(0, self._position_shadow)

    # ----- content-only helpers -----
    def _build_mainstack(self):
        # ---- left column container ----
        left = QtWidgets.QWidget()
        left.setObjectName("leftPane")
        col = QtWidgets.QVBoxLayout(left)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)

        # ---- navigation bar (your Navigation widget) ----
        self.navbar = Navigation(constants.SECTIONS, left)
        self.navbar.setMinimumHeight(34)
        self.navbar.setMaximumHeight(40)
        self.navbar.setObjectName("NavBar")
        self.navbar.setStyleSheet("""
            #NavBar { background: #F1F5F9; }
            QScrollArea { background: transparent; border: none; }
            QWidget#NavHost { background: #F1F5F9; }
        """)
        col.addWidget(self.navbar)
        col.addSpacing(-6)

        # ---- stacked content area (unchanged look) ----
        self.mainStack = QtWidgets.QStackedWidget()
        self.mainStack.setObjectName("mainStack")
        self.mainStack.setStyleSheet("""
            QStackedWidget#mainStack { background: #F3F4F6; }  /* left panel */
        """)

        # Example placeholder page (keep what you already had)
        page = QtWidgets.QWidget()
        page.setObjectName("mainRoot")
        v = QtWidgets.QVBoxLayout(page)
        v.addWidget(QtWidgets.QLabel("Main content area"))
        self.mainStack.addWidget(page)

        # Add the stack under the nav; stretch=1 so it uses the space
        col.addWidget(self.mainStack, 1)

        # ---- hook up nav → loader and select first tab ----
        self._pages = getattr(self, "_pages", {})  # keep existing dict if present
        self.navbar.tabSelected.connect(self._activate_section)
        QtCore.QTimer.singleShot(0, self.navbar.select_first)

        # Return the container to be added to the splitter
        return left

    def _build_sidebar(self):
        root = QtWidgets.QWidget()
        root.setObjectName("sidebarRoot")
        root.setStyleSheet("""
            #sidebarRoot { background-color: rgb(199,209,218); }
            #sidebarRoot, #sidebarRoot * { color: #EEE; }
            QGroupBox {
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 8px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 2px 6px;
                color: #FFF;
            }
        """)

        # Use a stacked widget to switch between normal sidebar and AI Advisor
        self.sidebar_stack = QtWidgets.QStackedWidget(root)

        # Create normal sidebar content
        normal_sidebar = QtWidgets.QWidget()
        normal_layout = QtWidgets.QVBoxLayout(normal_sidebar)
        normal_layout.setContentsMargins(8, 8, 8, 8)
        normal_layout.setSpacing(8)

        status = StatusWidget(normal_sidebar)
        normal_layout.addWidget(status)

        settings = SettingsWidget(normal_sidebar)
        settings.editRequested.connect(self._show_preferences_page)
        self._settings_card = settings
        normal_layout.addWidget(settings)
        normal_layout.addStretch(1)

        self.sidebar_stack.addWidget(normal_sidebar)

        # AI Advisor will be added when first needed
        self._normal_sidebar_widget = normal_sidebar

        # Layout for the root
        root_layout = QtWidgets.QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(self.sidebar_stack)

        return root

    def _check_ai_advisor_policy(self) -> bool:
        """Check if AI Advisor is enabled in the installed policy"""
        try:
            policy_file = get_policy_path()
            if not policy_file.exists():
                return False  # No policy installed, default to disabled

            with open(policy_file, 'r', encoding='utf-8') as f:
                import json
                policy = json.load(f)

            # Navigate to the AI advisor setting
            data_section = policy.get('data', {})
            ai_advisor_setting = data_section.get('ai_advisor_enabled', {})
            return ai_advisor_setting.get('value', False)

        except Exception as e:
            _LOGGER.warning(f"Could not read AI advisor policy setting: {e}")
            return False  # Default to disabled if we can't read the policy

    def _create_power_button(self) -> QtWidgets.QPushButton:
        """Create a circular power button with three states"""
        btn = QtWidgets.QPushButton()
        btn.setFixedSize(36, 36)
        btn.setCheckable(True)
        btn.setCursor(QtCore.Qt.PointingHandCursor)

        # Store references to the three icons
        btn._inactive_icon = QtGui.QIcon("assets/svg/aiAdvisor_inactive_icon.svg")
        btn._hover_icon = QtGui.QIcon("assets/svg/aiAdvisor_hover_icon.svg")
        btn._active_icon = QtGui.QIcon("assets/svg/aiAdvisor_active_icon.svg")

        # Start with inactive icon
        btn.setIcon(btn._inactive_icon)
        btn.setIconSize(QtCore.QSize(30, 30))

        # Track hover state
        btn._is_hovering = False

        # Connect state change events
        btn.toggled.connect(lambda checked: self._on_ai_advisor_toggled(checked))

        # Override enter/leave events for hover detection
        original_enter = btn.enterEvent
        original_leave = btn.leaveEvent

        def enter_event(event):
            btn._is_hovering = True
            self._update_power_button_icon(btn)
            if original_enter:
                original_enter(event)

        def leave_event(event):
            btn._is_hovering = False
            self._update_power_button_icon(btn)
            if original_leave:
                original_leave(event)

        btn.enterEvent = enter_event
        btn.leaveEvent = leave_event

        btn.setStyleSheet("""
            QPushButton {
                border-radius: 18px;
                background-color: #E9ECEF;             /* Inactive state - light gray */
                border: none;                          /* Remove all borders/outlines */
                outline: none;                         /* Remove focus outline */
            }
            QPushButton:hover {
                background-color: #DBE0E4;             /* Hover state - slightly darker gray */
            }
            QPushButton:checked {
                background-color: #000000;             /* Active state - black */
            }
            QPushButton:checked:hover {
                background-color: #000000;             /* Active + hover state - keep black */
            }
            QPushButton:focus {
                outline: none;                         /* Remove focus outline */
            }
        """)

        # Only show the button if AI Advisor is enabled in policy
        btn.setVisible(self.ai_advisor_enabled)

        return btn

    def _on_ai_advisor_toggled(self, checked: bool):
        """Handle AI Advisor button toggle"""
        self._ai_advisor_active = checked
        self._update_power_button_icon(self.powerButton)
        self._update_sidebar_for_ai_advisor(checked)

    def _update_sidebar_for_ai_advisor(self, ai_advisor_active: bool):
        """Update sidebar content and size based on AI Advisor state"""
        if ai_advisor_active:
            # Store current sidebar width before expanding
            current_sizes = self.splitter.sizes()
            if len(current_sizes) >= 2 and current_sizes[1] > 0:
                self._original_sidebar_width = current_sizes[1]

            # Remove width constraints for AI Advisor mode
            self.sidebar.setMaximumWidth(16777215)  # Qt's QWIDGETSIZE_MAX

            # Hide the normal sidebar widgets
            self._hide_normal_sidebar_widgets()

            # Show AI Advisor content (empty for now)
            self._show_ai_advisor_content()

            # Expand sidebar to 1/3 of screen width
            total_width = sum(self.splitter.sizes()) or self.width()
            ai_advisor_width = int(total_width / 3)
            main_content_width = total_width - ai_advisor_width
            self.splitter.setSizes([main_content_width, ai_advisor_width])

        else:
            # Hide AI Advisor content
            self._hide_ai_advisor_content()

            # Show normal sidebar widgets
            self._show_normal_sidebar_widgets()

            # Restore original width constraints
            self.sidebar.setMaximumWidth(520)

            # Return to original sidebar size
            total_width = sum(self.splitter.sizes()) or self.width()
            restored_width = min(self._original_sidebar_width, int(total_width * 0.45))
            main_content_width = total_width - restored_width
            self.splitter.setSizes([main_content_width, restored_width])

    def _hide_normal_sidebar_widgets(self):
        """Hide the Session Status and Settings widgets"""
        # Find the status and settings widgets in the sidebar
        sidebar_layout = self.sidebar.layout()
        if sidebar_layout:
            for i in range(sidebar_layout.count()):
                item = sidebar_layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    # Hide Status and Settings widgets specifically
                    if isinstance(widget, (StatusWidget, SettingsWidget)):
                        widget.hide()

    def _show_normal_sidebar_widgets(self):
        """Show the Session Status and Settings widgets"""
        sidebar_layout = self.sidebar.layout()
        if sidebar_layout:
            for i in range(sidebar_layout.count()):
                item = sidebar_layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    # Show Status and Settings widgets specifically
                    if isinstance(widget, (StatusWidget, SettingsWidget)):
                        widget.show()

    def _show_ai_advisor_content(self):
        """Show AI Advisor content area"""
        # Create AI Advisor content widget if it doesn't exist
        if not hasattr(self, '_ai_advisor_widget'):
            from discovery_assistant.ui.widgets.ai_advisor_widget import AIAdvisorWidget
            self._ai_advisor_widget = AIAdvisorWidget()
            self.sidebar_stack.addWidget(self._ai_advisor_widget)

        # Switch to AI Advisor
        self.sidebar_stack.setCurrentWidget(self._ai_advisor_widget)

    def _hide_ai_advisor_content(self):
        """Hide AI Advisor content area and return to normal sidebar"""
        # Switch back to normal sidebar
        self.sidebar_stack.setCurrentWidget(self._normal_sidebar_widget)

    def _hide_normal_sidebar_widgets(self):
        """Hide the normal sidebar (handled by stacked widget)"""
        pass  # No longer needed since we use stacked widget

    def _show_normal_sidebar_widgets(self):
        """Show the normal sidebar (handled by stacked widget)"""
        pass  # No longer needed since we use stacked widget

    def _update_power_button_icon(self, btn):
        """Update the power button icon based on current state"""
        if btn.isChecked():
            # Active state - use active icon regardless of hover
            btn.setIcon(btn._active_icon)
        elif btn._is_hovering:
            # Hover state (but not active)
            btn.setIcon(btn._hover_icon)
        else:
            # Inactive state
            btn.setIcon(btn._inactive_icon)

    def _activate_section(self, name: str):
        """Load the section widget on first use, then switch to it."""
        if not hasattr(self, "_pages"):
            self._pages = {}
        if name in self._pages:
            self.mainStack.setCurrentWidget(self._pages[name])
            return

        widget = self._load_section_widget(name)
        if widget is None:
            widget = self._placeholder_page(f"Missing tab: {name}")

        self._pages[name] = widget
        self.mainStack.addWidget(widget)
        self.mainStack.setCurrentWidget(widget)

    def _load_section_widget(self, name: str):
        """
        Dynamically import discovery_assistant.ui.tabs.<module> based on constants.SECTIONS[name].
        Convention: class is <NameWithoutSpaces>Tab, e.g., 'Respondent' -> RespondentTab.
        """
        module_filename = constants.SECTIONS.get(name)
        if not module_filename:
            return None

        mod_name = module_filename.rsplit(".", 1)[0]  # strip .py
        import_path = f"discovery_assistant.ui.tabs.{mod_name}"

        try:
            mod = import_module(import_path)
            class_name = "".join(ch for ch in name.title() if ch.isalnum()) + "Tab"
            if hasattr(mod, class_name):
                cls = getattr(mod, class_name)
                return cls(self)  # parent = ContentContainer
            # fallbacks if you prefer factories
            if hasattr(mod, "build"):
                return mod.build(self)
            if hasattr(mod, "WIDGET"):
                return getattr(mod, "WIDGET")
        except Exception as e:
            _LOGGER.exception("Failed to load tab '%s' from %s: %s", name, import_path, e)
            return None

    def _placeholder_page(self, text: str):
        page = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(page)
        v.setContentsMargins(24, 24, 24, 24)
        v.addStretch(1)
        lbl = QtWidgets.QLabel(text)
        f = lbl.font();
        f.setPointSize(f.pointSize() + 2);
        lbl.setFont(f)
        v.addWidget(lbl, 0, QtCore.Qt.AlignCenter)
        v.addStretch(1)
        return page

    def _card(self, title: str, body: str):
        g = QtWidgets.QGroupBox(title)
        v = QtWidgets.QVBoxLayout(g)
        v.addWidget(QtWidgets.QLabel(body))
        return g

    def _can_export(self) -> bool:
        """
        TODO: replace with your real checks, e.g.:
          - required text fields non-empty
          - selections made
          - validations pass
        """
        return bool(getattr(self, "projectNameEdit", None) and self.projectNameEdit.text().strip()) \
            and bool(getattr(self, "clientEdit", None) and self.clientEdit.text().strip())

    def _start_export(self):
        self.export_button.setEnabled(False)
        mw = self.window()
        if hasattr(mw, "begin_busy"): mw.begin_busy("Exporting…")
        # ... launch worker / thread ...
        # on finish:
        if hasattr(mw, "end_busy"): mw.end_busy()
        self._update_export_button()

    def _set_export_tooltip_for_state(self, *, disabled: bool):
        if disabled:
            # Force tooltip to show on a disabled button
            self.export_button.setAttribute(QtCore.Qt.WA_AlwaysShowToolTips, True)
            self.export_button.setToolTip("Fill required fields to enable export")
        else:
            # Back to normal tooltip behavior (hidden unless you set one)
            self.export_button.setAttribute(QtCore.Qt.WA_AlwaysShowToolTips, False)
            self.export_button.setToolTip("")  # or remove the line entirely

    def _update_export_button(self):
        enabled = self._can_export()
        self.export_button.setEnabled(enabled)
        self._set_export_tooltip_for_state(disabled=not enabled)

        # (optional) keep a menu action in sync
        mw = self.window()
        if hasattr(mw, "exportJsonAct"):
            mw.exportJsonAct.setEnabled(enabled)

    # inside ContentContainer
    def _show_preferences_page(self):
        # create once
        if not hasattr(self, "_prefsPage"):
            from discovery_assistant.ui.preferences_page import PreferencesPage
            self._prefsPage = PreferencesPage(self)
            self._prefsPage.closeRequested.connect(self._close_preferences_page)
            self.mainStack.addWidget(self._prefsPage)

        # lock Org controls for non-admin users
        is_admin = getattr(self, "_is_admin", False)  # <-- set this flag wherever you authenticate
        self._prefsPage.set_admin_mode(is_admin)

        # remember current page and UI state
        self._prevPage = self.mainStack.currentWidget()
        self._prev_nav_visible = self.navbar.isVisible()

        # switch
        self.mainStack.setCurrentWidget(self._prefsPage)
        self.toggle_sidebar(False)  # hide right sidebar
        self.navbar.setVisible(False)  # hide the tab row

    def _close_preferences_page(self):
        if hasattr(self, "_prevPage") and self._prevPage is not None:
            self.mainStack.setCurrentWidget(self._prevPage)
        self.toggle_sidebar(True)
        self.navbar.setVisible(getattr(self, "_prev_nav_visible", True))

    # ----- Sidebar API called by MainWindow QAction -----
    @QtCore.Slot(bool)
    def toggle_sidebar(self, checked: bool):
        sizes = self.splitter.sizes()
        total = sum(sizes) if sum(sizes) > 0 else max(self.width(), 1)
        if checked:
            prev = int(self.settings.value("sidebarWidth", SIDEBAR_DEFAULT))
            prev = max(SIDEBAR_MIN, prev)
            self.splitter.setSizes([max(1, total - prev), prev])
        else:
            self.settings.setValue("sidebarWidth", sizes[1])
            self.splitter.setSizes([total, 0])
        self.sidebarToggled.emit(checked)

    # ----- window behavior (no reference to QAction here) -----
    def eventFilter(self, obj, ev):
        if obj is self.export_button:
            if not obj.isEnabled():
                if ev.type() in (
                        QtCore.QEvent.Enter,
                        QtCore.QEvent.HoverEnter,
                        QtCore.QEvent.HoverMove,
                        QtCore.QEvent.MouseMove,
                ):
                    gpos = QtGui.QCursor.pos()  # global cursor pos
                    host = self  # enabled parent (not the disabled button)
                    lpos = host.mapFromGlobal(gpos)  # parent-local
                    # 2x2 rect at cursor in parent coords → forces relocate
                    rect = QtCore.QRect(lpos.x() - 1, lpos.y() - 1, 2, 2)
                    QtWidgets.QToolTip.hideText()  # important: reset position
                    QtWidgets.QToolTip.showText(gpos, obj.toolTip(), host, rect)
                elif ev.type() in (QtCore.QEvent.Leave, QtCore.QEvent.HoverLeave):
                    QtWidgets.QToolTip.hideText()
            return False

        # keep your other handlers (resize, etc.)
        return super().eventFilter(obj, ev)

    def _auto_collapse(self):
        w = self.width()
        sizes = self.splitter.sizes()
        is_open = sizes[1] > 0
        should_close = w < BREAKPOINT
        if should_close and is_open:
            self.toggle_sidebar(False)
        elif not should_close and not is_open:
            self.toggle_sidebar(True)

    def _restore_layout(self):
        stored = int(self.settings.value("sidebarWidth", SIDEBAR_DEFAULT))
        total = max(self.width(), 1)
        stored = max(SIDEBAR_MIN, min(stored, int(total * 0.45)))
        self.splitter.setSizes([max(1, total - stored), stored])
        self.sidebarToggled.emit(True)
