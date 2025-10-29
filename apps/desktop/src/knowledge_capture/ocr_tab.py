# ocr_tab.py
"""
OCR Mode Tab - Screenshot capture and OCR processing
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QSplitter, QGroupBox, QFormLayout, QCheckBox, QProgressBar
)
from PySide6.QtCore import Qt
from pathlib import Path
import tempfile
import os
from datetime import datetime


class OCRTab(QWidget):
    """OCR Mode - Screenshot capture and text extraction"""

    def __init__(self, parent, shared_components, metadata_panel):
        super().__init__(parent)
        self.parent = parent
        self.shared_components = shared_components
        self.metadata_panel = metadata_panel
        self.current_image_path = None
        self.ocr_thread = None

        self.init_ui()

    def init_ui(self):
        """Initialize the OCR mode interface"""
        layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # Left panel - OCR controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # Screenshot capture section
        capture_group = QGroupBox("Screenshot Capture")
        capture_layout = QVBoxLayout(capture_group)

        self.capture_btn = QPushButton("Capture Screenshot (Ctrl+Shift+S)")
        self.capture_btn.setCursor(Qt.PointingHandCursor)
        self.capture_btn.clicked.connect(self.start_screenshot_capture)
        capture_layout.addWidget(self.capture_btn)

        self.fullscreen_btn = QPushButton("Capture Full Screen")
        self.fullscreen_btn.setCursor(Qt.PointingHandCursor)
        self.fullscreen_btn.clicked.connect(self.capture_fullscreen)
        capture_layout.addWidget(self.fullscreen_btn)

        left_layout.addWidget(capture_group)

        # OCR Settings
        ocr_group = QGroupBox("OCR Settings")
        ocr_layout = QFormLayout(ocr_group)
        ocr_layout.setContentsMargins(12, 12, 12, 12)
        self.preprocess_checkbox = QCheckBox("Preprocess image")
        self.preprocess_checkbox.setChecked(True)
        ocr_layout.addRow("Enhancement:", self.preprocess_checkbox)

        left_layout.addWidget(ocr_group)

        # Shared components - summarization only (no output group)
        summary_group, self.ai_provider, self.summary_style, self.summary_length, self.auto_summarize, self.ai_status = self.shared_components.create_summarization_group()
        left_layout.addWidget(summary_group)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        left_layout.addWidget(self.progress_bar)

        left_layout.addStretch()
        splitter.addWidget(left_panel)

        # Right panel - OCR text processing
        right_panel = self.create_ocr_text_panel()
        splitter.addWidget(right_panel)

        splitter.setSizes([400, 1000])

    def create_ocr_text_panel(self):
        """Create the OCR text processing panel"""
        from PySide6.QtWidgets import QTabWidget

        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Tab widget for different views
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Raw OCR text tab
        self.raw_text_edit = QTextEdit()
        self.raw_text_edit.setPlaceholderText("Raw OCR text will appear here...")
        self.tab_widget.addTab(self.raw_text_edit, "Raw OCR")

        # Summary tab
        self.summary_text_edit = QTextEdit()
        self.summary_text_edit.setPlaceholderText("Summarized content will appear here...")
        self.tab_widget.addTab(self.summary_text_edit, "Summary")

        # Final markdown tab
        self.markdown_edit = QTextEdit()
        self.markdown_edit.setPlaceholderText("Final markdown content for export...")
        self.tab_widget.addTab(self.markdown_edit, "Final Markdown")

        # Processing buttons
        button_layout = QHBoxLayout()

        self.process_ocr_btn = QPushButton("Process OCR")
        self.process_ocr_btn.setCursor(Qt.PointingHandCursor)
        self.process_ocr_btn.clicked.connect(self.process_ocr)
        self.process_ocr_btn.setEnabled(False)
        self.process_ocr_btn.setFixedHeight(40)
        button_layout.addWidget(self.process_ocr_btn)

        self.summarize_btn = QPushButton("Summarize")
        self.summarize_btn.setCursor(Qt.PointingHandCursor)
        self.summarize_btn.clicked.connect(lambda: self.parent.summarize_text('ocr'))
        self.summarize_btn.setEnabled(False)
        self.summarize_btn.setFixedHeight(40)
        button_layout.addWidget(self.summarize_btn)

        self.generate_markdown_btn = QPushButton("Generate Markdown")
        self.generate_markdown_btn.setCursor(Qt.PointingHandCursor)
        self.generate_markdown_btn.clicked.connect(lambda: self.parent.generate_final_markdown('ocr'))
        self.generate_markdown_btn.setEnabled(False)
        self.generate_markdown_btn.setFixedHeight(40)
        button_layout.addWidget(self.generate_markdown_btn)

        self.save_btn = QPushButton("Save Content Bundle")
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.clicked.connect(lambda: self.parent.save_markdown('ocr'))
        self.save_btn.setEnabled(False)
        self.save_btn.setFixedHeight(40)
        button_layout.addWidget(self.save_btn)

        layout.addLayout(button_layout)

        return panel

    def start_screenshot_capture(self):
        """Start the screenshot capture process"""
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QRect
        from PySide6.QtGui import QPainter, QPixmap

        # Import ScreenshotCapture from parent's module
        ScreenshotCapture = self.parent.ScreenshotCapture

        self.capture_overlay = ScreenshotCapture()
        self.capture_overlay.screenshot_taken.connect(self.handle_screenshot)
        self.capture_overlay.show()

    def handle_screenshot(self, pixmap):
        """Handle captured screenshot"""
        from PySide6.QtGui import QPixmap

        # Save screenshot to temp file
        temp_dir = tempfile.gettempdir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_image_path = os.path.join(temp_dir, f"screenshot_{timestamp}.png")

        pixmap.save(self.current_image_path)
        self.parent.statusBar().showMessage(f"Screenshot captured: {self.current_image_path}")

        # Enable processing button
        self.process_ocr_btn.setEnabled(True)

        # Auto-process if enabled
        if self.auto_summarize.isChecked():
            self.process_ocr()

    def capture_fullscreen(self):
        """Capture full screen using the enhanced system"""
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QRect, Qt
        from PySide6.QtGui import QPainter, QPixmap

        app = QApplication.instance()
        screens = app.screens()

        if len(screens) > 1:
            # Multi-monitor setup - capture virtual desktop
            virtual_geometry = QRect()
            for screen in screens:
                virtual_geometry = virtual_geometry.united(screen.geometry())

            # Create a pixmap that covers all screens
            total_width = virtual_geometry.width()
            total_height = virtual_geometry.height()
            full_pixmap = QPixmap(total_width, total_height)
            full_pixmap.fill(Qt.black)

            painter = QPainter(full_pixmap)
            for screen in screens:
                screen_geometry = screen.geometry()
                screen_pixmap = screen.grabWindow(0)
                # Calculate offset from virtual desktop origin
                offset_x = screen_geometry.x() - virtual_geometry.x()
                offset_y = screen_geometry.y() - virtual_geometry.y()
                painter.drawPixmap(offset_x, offset_y, screen_pixmap)
            painter.end()

            self.handle_screenshot(full_pixmap)
        else:
            # Single monitor
            screen = QApplication.primaryScreen()
            pixmap = screen.grabWindow(0)
            self.handle_screenshot(pixmap)

    def process_ocr(self):
        """Process OCR on the current image"""
        if not self.current_image_path:
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.parent.statusBar().showMessage("Processing OCR...")

        # Get OCRProcessor from parent
        OCRProcessor = self.parent.OCRProcessor

        # Start OCR thread
        self.ocr_thread = OCRProcessor(
            self.current_image_path,
            self.preprocess_checkbox.isChecked()
        )
        self.ocr_thread.ocr_completed.connect(self.handle_ocr_result)
        self.ocr_thread.ocr_failed.connect(self.handle_ocr_error)
        self.ocr_thread.start()

    def handle_ocr_result(self, text):
        """Handle OCR completion"""
        self.progress_bar.setVisible(False)
        self.raw_text_edit.setText(text)
        self.parent.statusBar().showMessage("OCR completed successfully")

        self.summarize_btn.setEnabled(True)

        # Auto-summarize if enabled
        if self.auto_summarize.isChecked():
            self.parent.summarize_text('ocr')

    def handle_ocr_error(self, error):
        """Handle OCR error"""
        from PySide6.QtWidgets import QMessageBox

        self.progress_bar.setVisible(False)
        self.parent.statusBar().showMessage("OCR failed")
        QMessageBox.warning(self, "OCR Error", f"OCR processing failed: {error}")

    def reset_fields(self):
        """Reset all fields and content"""
        # Clear text areas
        self.raw_text_edit.clear()
        self.summary_text_edit.clear()
        self.markdown_edit.clear()

        # Reset buttons
        self.process_ocr_btn.setEnabled(False)
        self.summarize_btn.setEnabled(False)
        self.generate_markdown_btn.setEnabled(False)
        self.save_btn.setEnabled(False)

        # Switch back to first tab
        self.tab_widget.setCurrentIndex(0)

        # Clear current image path
        self.current_image_path = None

        self.parent.statusBar().showMessage("OCR mode reset - ready for new content")
