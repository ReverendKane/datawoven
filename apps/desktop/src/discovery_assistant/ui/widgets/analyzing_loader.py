from PySide6 import QtCore, QtGui, QtWidgets


class AnalyzingLoader(QtWidgets.QWidget):
    """Animated loader widget with three dots and 'Analyzing...' text"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("analyzingLoader")
        self.setFixedHeight(32)  # Match button height

        # Animation state
        self.current_dot = 0
        self.opacity_values = [0.3, 0.3, 0.3]  # Start with all dots semi-transparent

        # Create timer for animation
        self.animation_timer = QtCore.QTimer()
        self.animation_timer.timeout.connect(self._animate_next_dot)

        self._setup_ui()
        self._setup_styling()

        # Hide by default
        self.hide()

    def _setup_ui(self):
        """Create the layout with dots and text"""
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(3)  # Slightly increased from 2 to 3

        # Create three dot labels
        self.dots = []
        for i in range(3):
            dot = QtWidgets.QLabel("●")
            dot.setObjectName(f"dot_{i}")
            dot.setFixedSize(8, 12)
            dot.setAlignment(QtCore.Qt.AlignCenter)
            self.dots.append(dot)
            layout.addWidget(dot, 0, QtCore.Qt.AlignVCenter)  # Added vertical center alignment

        # Add spacing between dots and text
        layout.addSpacing(4)  # Increased from 2 to 4

        # Analyzing text with margin adjustment for visual centering
        self.text_label = QtWidgets.QLabel("Analyzing...")
        self.text_label.setObjectName("analyzingText")
        self.text_label.setContentsMargins(0, 2, 0, 0)  # Add 2px top margin to nudge down
        layout.addWidget(self.text_label, 0, QtCore.Qt.AlignVCenter)  # Added vertical center alignment

        # Add stretch to center content
        layout.addStretch()

    def _setup_styling(self):
        """Apply styling to the loader"""
        self.setStyleSheet("""
            #analyzingLoader {
                background-color: transparent;
            }

            #dot_0, #dot_1, #dot_2 {
                color: #8B7DD8;
                font-size: 16px;
                font-weight: bold;
            }

            #analyzingText {
                color: #FFFFFF;
                font-size: 12px;
                font-weight: normal;
            }
        """)

    def _animate_next_dot(self):
        """Animate to the next dot in sequence"""
        # Reset all dots to semi-transparent
        for i, dot in enumerate(self.dots):
            self.opacity_values[i] = 0.3

        # Make current dot fully opaque
        self.opacity_values[self.current_dot] = 1.0

        # Update dot appearances
        self._update_dot_opacity()

        # Move to next dot
        self.current_dot += 1

        # If we've animated all dots, fade all to transparent and restart
        if self.current_dot >= 3:
            QtCore.QTimer.singleShot(500, self._fade_all_dots)
            self.current_dot = 0

    def _fade_all_dots(self):
        """Fade all dots to transparent before restarting cycle"""
        for i in range(3):
            self.opacity_values[i] = 0.3
        self._update_dot_opacity()

    def _update_dot_opacity(self):
        """Update the visual opacity of all dots"""
        for i, dot in enumerate(self.dots):
            opacity = self.opacity_values[i]
            # Convert opacity to alpha value for color
            alpha = int(255 * opacity)
            dot.setStyleSheet(f"""
                color: rgba(139, 125, 216, {alpha});
                font-size: 16px;
                font-weight: bold;
            """)

    def start_animation(self):
        """Start the analyzing animation"""
        self.show()
        self.current_dot = 0
        for i in range(3):
            self.opacity_values[i] = 0.3
        self._update_dot_opacity()
        self.animation_timer.start(500)  # 500ms between each dot

    def stop_animation(self):
        """Stop the animation and hide the widget"""
        self.animation_timer.stop()
        self.hide()

    def is_animating(self):
        """Check if animation is currently running"""
        return self.animation_timer.isActive()
