# Create this new file: src/discovery_assistant/ui/launch_card.py

"""
Launch Card - Initial branded screen shown before the main wizard opens.
Displays for 3 seconds then automatically transitions to the main application.
"""

from PySide6 import QtWidgets, QtCore, QtGui
from pathlib import Path


class LaunchCard(QtWidgets.QDialog):
    """
    500x500 branded launch card that displays before the main wizard.
    Auto-closes after 3 seconds and signals the main application to launch.
    """

    # Signal emitted when launch card completes and main app should open
    launchComplete = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Discovery Assistant")
        self.setFixedSize(500, 500)
        self.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        # Center on screen
        self._center_on_screen()

        # Setup UI
        self._setup_ui()
        self._apply_styles()

        # Setup auto-close timer
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self._launch_main_app)
        self.timer.setSingleShot(True)

        # Show with fade-in effect
        self.setWindowOpacity(0.0)
        self.fade_in_animation = QtCore.QPropertyAnimation(self, b"windowOpacity")
        self.fade_in_animation.setDuration(500)  # 500ms fade in
        self.fade_in_animation.setStartValue(0.0)
        self.fade_in_animation.setEndValue(1.0)
        self.fade_in_animation.finished.connect(self._start_timer)

    def _center_on_screen(self):
        """Center the launch card on the screen containing the mouse cursor."""
        # Get current cursor position
        cursor_pos = QtGui.QCursor.pos()

        # Find which screen contains the cursor
        screen = QtWidgets.QApplication.screenAt(cursor_pos)
        if screen is None:
            # Fallback to primary screen if cursor detection fails
            screen = QtWidgets.QApplication.primaryScreen()

        screen_geometry = screen.geometry()

        # Center on the detected screen
        x = screen_geometry.x() + (screen_geometry.width() - self.width()) // 2
        y = screen_geometry.y() + (screen_geometry.height() - self.height()) // 2
        self.move(x, y)

    def _setup_ui(self):
        """Create the launch card UI with branding elements."""
        # Main container with rounded corners
        self.container = QtWidgets.QFrame(self)
        self.container.setObjectName("launchContainer")
        self.container.setGeometry(0, 0, 500, 500)

        layout = QtWidgets.QVBoxLayout(self.container)
        layout.setContentsMargins(40, 40, 40, 40)
        # layout.setSpacing(10)

        # Top spacer
        layout.addStretch(2)

        # Logo area
        logo_container = self._create_logo_section()
        layout.addWidget(logo_container)

        # Title and branding
        title_container = self._create_title_section()
        layout.addSpacing(-20)
        layout.addWidget(title_container)

        # Middle spacer
        layout.addStretch(1)

        # Subtitle/tagline
        tagline_container = self._create_tagline_section()
        layout.addWidget(tagline_container)

        # Loading indicator
        loading_container = self._create_loading_section()
        layout.addWidget(loading_container)

        # Bottom spacer
        layout.addStretch(2)

    def _create_logo_section(self) -> QtWidgets.QWidget:
        """Create the logo display area."""
        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.setAlignment(QtCore.Qt.AlignCenter)

        # Logo placeholder - you can replace this with your actual logo
        logo_label = QtWidgets.QLabel()
        logo_label.setObjectName("logoLabel")
        logo_label.setAlignment(QtCore.Qt.AlignCenter)
        logo_label.setFixedSize(120, 120)

        # Try to load your actual logo
        pixmap = QtGui.QPixmap(":/datawoven_splashLogo_white.svg")
        if pixmap:
            if not pixmap.isNull():
                # Scale pixmap to fit while maintaining aspect ratio
                scaled_pixmap = pixmap.scaled(120, 120, QtCore.Qt.KeepAspectRatio,
                                              QtCore.Qt.SmoothTransformation)
                logo_label.setPixmap(scaled_pixmap)
            else:
                # Fallback to text logo
                logo_label.setText("DW")
                logo_label.setStyleSheet("""
                    font-size: 48px;
                    font-weight: bold;
                    color: #F9FAFB;
                    background-color: #404040;
                    border-radius: 60px;
                """)
        else:
            # Fallback to text logo if no image found
            logo_label.setText("DA")
            logo_label.setStyleSheet("""
                font-size: 48px;
                font-weight: bold;
                color: #F9FAFB;
                background-color: #404040;
                border-radius: 60px;
                border: 3px solid #606060;
            """)

        layout.addWidget(logo_label)
        return container

    def _create_title_section(self) -> QtWidgets.QWidget:
        """Create the main title section."""
        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.setAlignment(QtCore.Qt.AlignCenter)
        # layout.setSpacing(8)

        # Main title
        title = QtWidgets.QLabel("DISCOVERY ASSISTANT")
        title.setObjectName("mainTitle")
        title.setAlignment(QtCore.Qt.AlignCenter)

        # Load the same Montserrat SemiBold font used in main window
        family_name = None
        import discovery_assistant.constants as constants
        fid = QtGui.QFontDatabase.addApplicationFont(str(constants.FONT_MONTSERRAT_SEMIBOLD))
        if fid != -1:
            fams = QtGui.QFontDatabase.applicationFontFamilies(fid)
            if fams:
                family_name = fams[0]

        # Apply the same font styling as main window
        title_font = QtGui.QFont(family_name or "Segoe UI", 12)
        title_font.setWeight(QtGui.QFont.DemiBold)
        title_font.setHintingPreference(QtGui.QFont.PreferFullHinting)
        title.setFont(title_font)

        # Subtitle
        subtitle = QtWidgets.QLabel("Administrative Setup")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(QtCore.Qt.AlignCenter)

        layout.addWidget(title)
        layout.addWidget(subtitle)

        return container

    def _create_tagline_section(self) -> QtWidgets.QWidget:
        """Create the tagline/description section."""
        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.setAlignment(QtCore.Qt.AlignCenter)

        tagline = QtWidgets.QLabel("Streamlining automation discovery\nfor your organization")
        tagline.setObjectName("tagline")
        tagline.setAlignment(QtCore.Qt.AlignCenter)

        layout.addWidget(tagline)
        return container

    def _create_loading_section(self) -> QtWidgets.QWidget:
        """Create the loading indicator section."""
        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.setAlignment(QtCore.Qt.AlignCenter)
        layout.setSpacing(15)

        # Loading text
        loading_text = QtWidgets.QLabel("Initializing setup wizard...")
        loading_text.setObjectName("loadingText")
        loading_text.setAlignment(QtCore.Qt.AlignCenter)

        layout.addWidget(loading_text)

        return container

    def _animate_dots(self):
        """Animate the loading dots."""
        dot_patterns = ["●○○", "○●○", "○○●", "●●○", "●●●"]
        self.progress_dots.setText(dot_patterns[self.dot_state])
        self.dot_state = (self.dot_state + 1) % len(dot_patterns)

    def _apply_styles(self):
        """Apply styling to the launch card."""
        self.setStyleSheet("""
            #launchContainer {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #353535, stop:1 #000000);
                border: 2px solid #404040;
                border-radius: 20px;
            }

            #mainTitle {
                font-family: 'Montserrat', sans-serif;
                font-size: 24px;
                font-weight: 600;
                color: #F9FAFB;
                margin: 0;
            }

            #subtitle {
                font-family: 'Montserrat', sans-serif;
                font-size: 17px;
                font-weight: 400;
                color: #808080;
                margin: 0;
            }

            #tagline {
                font-family: 'Montserrat', sans-serif;
                font-size: 14px;
                font-weight: 400;
                color: #D1D5DB;
                line-height: 1.4;
                margin: 0;
            }

            #loadingText {
                font-family: 'Montserrat', sans-serif;
                font-size: 12px;
                font-weight: 400;
                color: #9CA3AF;
                margin: 0;
            }

            #progressDots {
                font-size: 20px;
                color: #606060;
                margin: 0;
            }
        """)

    def _start_timer(self):
        """Start the 3-second timer after fade-in completes."""
        self.timer.start(3000)  # 3 seconds

    def _launch_main_app(self):
        """Launch the main application with fade-out effect."""

        # Fade out animation
        self.fade_out_animation = QtCore.QPropertyAnimation(self, b"windowOpacity")
        self.fade_out_animation.setDuration(300)  # 300ms fade out
        self.fade_out_animation.setStartValue(1.0)
        self.fade_out_animation.setEndValue(0.0)
        self.fade_out_animation.finished.connect(self._complete_launch)
        self.fade_out_animation.start()

    def _complete_launch(self):
        """Complete the launch sequence and emit signal."""
        self.launchComplete.emit()
        self.accept()

    def show_with_animation(self):
        """Show the launch card with fade-in animation."""
        self.show()
        self.fade_in_animation.start()

    def mousePressEvent(self, event):
        """Allow clicking to skip the wait and launch immediately."""
        if event.button() == QtCore.Qt.LeftButton:
            self.timer.stop()
            self._launch_main_app()


# Update your main.py to use the launch card system:

def launch_admin_setup_with_card():
    """Launch the admin setup with branded launch card."""
    app = QtWidgets.QApplication.instance()

    # Create and show launch card
    launch_card = LaunchCard()

    def on_launch_complete():
        # Launch card finished, now show the main wizard
        wizard = AdminSetupWizard()

        # Determine window mode based on screen size
        screen = app.primaryScreen().geometry()
        if screen.width() >= 1920 and screen.height() >= 1080:
            wizard.show()  # Normal windowed mode for large screens
        else:
            wizard.showMaximized()  # Maximized for smaller screens

        # Return result when wizard closes
        return wizard.exec()

    # Connect the launch completion signal
    launch_card.launchComplete.connect(on_launch_complete)

    # Show launch card with animation
    launch_card.show_with_animation()

    return launch_card.exec()

# In your main.py bootstrap section, replace the direct wizard call with:
# result = launch_admin_setup_with_card()
