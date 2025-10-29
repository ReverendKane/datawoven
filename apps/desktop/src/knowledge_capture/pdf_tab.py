"""
PDF Batch Processing Tab for Knowledge Capture Tool
Handles single and batch PDF processing with automatic chapter detection
"""

import logging
import json
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QRadioButton, QLineEdit, QCheckBox, QProgressBar,
    QTextEdit, QFileDialog, QMessageBox, QSplitter, QTabWidget
)
from PySide6.QtCore import Qt, QThread, Signal
import fitz  # PyMuPDF
import re

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
LOG_CTX = "PDFTab"
log = logging.LoggerAdapter(logging.getLogger(__name__), {"ctx": LOG_CTX})
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


@dataclass
class PDFProcessingResult:
    """Result from PDF processing"""
    file_path: Path
    success: bool
    chapters: List[Dict] = field(default_factory=list)
    content: str = ""
    error: Optional[str] = None
    failed_pages: List[int] = field(default_factory=list)
    total_pages: int = 0


class PDFProcessor(QThread):
    """Background thread for PDF processing"""
    processing_progress = Signal(str, int, int)  # message, current, total
    processing_completed = Signal(list)  # List of PDFProcessingResult
    processing_failed = Signal(str)

    def __init__(self, files: List[Path], detect_chapters: bool, use_ocr: bool):
        super().__init__()
        self.files = files
        self.detect_chapters = detect_chapters
        self.use_ocr = use_ocr

    def run(self):
        """Process PDF files"""
        results = []
        total_files = len(self.files)

        for idx, pdf_path in enumerate(self.files, 1):
            self.processing_progress.emit(
                f"Processing {pdf_path.name}...",
                idx,
                total_files
            )

            try:
                result = self.process_single_pdf(pdf_path)
                results.append(result)
            except Exception as e:
                _LOGGER.error(f"Failed to process {pdf_path}: {e}")
                results.append(PDFProcessingResult(
                    file_path=pdf_path,
                    success=False,
                    error=str(e)
                ))

        self.processing_completed.emit(results)

    def process_single_pdf(self, pdf_path: Path) -> PDFProcessingResult:
        """Process a single PDF file"""
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)

            if self.detect_chapters:
                chapters = self.detect_chapters_in_pdf(doc)
                if len(chapters) > 1:
                    # Successfully detected multiple chapters
                    return PDFProcessingResult(
                        file_path=pdf_path,
                        success=True,
                        chapters=chapters,
                        total_pages=total_pages
                    )

            # Process as single document
            content, failed_pages = self.extract_text_from_pdf(doc)

            return PDFProcessingResult(
                file_path=pdf_path,
                success=True,
                content=content,
                failed_pages=failed_pages if failed_pages else [],
                total_pages=total_pages
            )

        except Exception as e:
            return PDFProcessingResult(
                file_path=pdf_path,
                success=False,
                error=str(e)
            )

    def detect_chapters_in_pdf(self, doc: fitz.Document) -> List[Dict]:
        """Detect chapters in PDF based on font size and structure"""
        chapters = []
        current_chapter = {"title": "Introduction", "start_page": 0, "content": ""}

        # Analyze document for chapter markers
        for page_num in range(len(doc)):
            page = doc[page_num]
            blocks = page.get_text("dict")["blocks"]

            for block in blocks:
                if block.get("type") == 0:  # Text block
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text = span.get("text", "").strip()
                            font_size = span.get("size", 0)

                            # Check for chapter indicators
                            if self.is_chapter_heading(text, font_size):
                                # Save previous chapter
                                if current_chapter["content"].strip():
                                    current_chapter["end_page"] = page_num - 1
                                    chapters.append(current_chapter.copy())

                                # Start new chapter
                                current_chapter = {
                                    "title": text,
                                    "start_page": page_num,
                                    "content": ""
                                }

        # Add final chapter
        if current_chapter["content"].strip() or not chapters:
            current_chapter["end_page"] = len(doc) - 1
            # Extract content for final chapter
            content, _ = self.extract_text_from_pages(doc, current_chapter["start_page"], current_chapter["end_page"])
            current_chapter["content"] = content
            chapters.append(current_chapter)

        # If only one chapter detected, treat as single document
        if len(chapters) == 1:
            return []

        # Extract content for all chapters
        for chapter in chapters:
            if not chapter["content"]:
                content, _ = self.extract_text_from_pages(
                    doc,
                    chapter["start_page"],
                    chapter.get("end_page", len(doc) - 1)
                )
                chapter["content"] = content

        return chapters

    def is_chapter_heading(self, text: str, font_size: float) -> bool:
        """Determine if text is likely a chapter heading"""
        # Check for common chapter patterns
        chapter_patterns = [
            r'^Chapter\s+\d+',
            r'^CHAPTER\s+\d+',
            r'^\d+\.\s+[A-Z]',
            r'^[A-Z][A-Z\s]{10,}$',
        ]

        for pattern in chapter_patterns:
            if re.match(pattern, text):
                return True

        # Check font size (chapters usually have larger fonts)
        if font_size > 14 and len(text) < 100:
            return True

        return False

    def extract_text_from_pdf(self, doc: fitz.Document) -> Tuple[str, List[int]]:
        """Extract text from entire PDF"""
        return self.extract_text_from_pages(doc, 0, len(doc) - 1)

    def clean_extracted_text(self, text: str) -> str:
        """Clean up PDF extracted text by joining broken lines"""
        lines = text.split('\n')
        cleaned_lines = []
        current_paragraph = []

        for line in lines:
            line = line.strip()

            # Empty line indicates paragraph break
            if not line:
                if current_paragraph:
                    cleaned_lines.append(' '.join(current_paragraph))
                    current_paragraph = []
                cleaned_lines.append('')  # Preserve paragraph break
                continue

            # Check if line ends with sentence-ending punctuation
            if line.endswith(('.', '!', '?', ':', ';')):
                current_paragraph.append(line)
                cleaned_lines.append(' '.join(current_paragraph))
                current_paragraph = []
            else:
                # Line continues to next line
                current_paragraph.append(line)

        # Add any remaining text
        if current_paragraph:
            cleaned_lines.append(' '.join(current_paragraph))

        return '\n'.join(cleaned_lines)

    def extract_text_from_pages(self, doc: fitz.Document, start_page: int, end_page: int) -> Tuple[str, List[int]]:
        """Extract text from a range of pages"""
        content = []
        failed_pages = []

        for page_num in range(start_page, end_page + 1):
            try:
                page = doc[page_num]
                text = page.get_text()

                # Check if page has text or is image-based
                if not text.strip() and self.use_ocr:
                    # Try OCR on image-based page
                    try:
                        text = self.ocr_page(page)
                    except Exception as e:
                        _LOGGER.warning(f"OCR failed for page {page_num + 1}: {e}")
                        failed_pages.append(page_num + 1)
                        continue

                if text.strip():
                    cleaned_text = self.clean_extracted_text(text)
                    content.append(f"--- Page {page_num + 1} ---\n{cleaned_text}")
                else:
                    failed_pages.append(page_num + 1)

            except Exception as e:
                _LOGGER.error(f"Failed to extract page {page_num + 1}: {e}")
                failed_pages.append(page_num + 1)

        return "\n\n".join(content), failed_pages

    def ocr_page(self, page: fitz.Page) -> str:
        """Perform OCR on a PDF page using Tesseract"""
        import pytesseract
        from PIL import Image
        import io

        # Convert page to image
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better OCR
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))

        # Perform OCR
        text = pytesseract.image_to_string(img)
        return text


class PDFTab(QWidget):
    """PDF Batch Processing Tab"""

    def __init__(self, parent, shared_components, metadata_panel):
        super().__init__(parent)
        self.parent = parent
        self.shared_components = shared_components
        self.metadata_panel = metadata_panel

        _LOGGER.info("PDFTab initialized")

        self._processing = False
        self._pdf_processor = None
        self._processing_results = []

        self.init_ui()

    def init_ui(self):
        """Initialize the PDF processing interface"""

        layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        ############################
        # Left panel - OCR controls
        ############################

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # Instructions
        info_group = QGroupBox("PDF Batch Processing")
        info_layout = QVBoxLayout(info_group)
        info_layout.setContentsMargins(12, 12, 12, 12)
        info_label = QLabel(
            "Process single PDFs or batch process multiple PDFs from a folder. "
            "Automatic chapter detection and OCR support for image-based PDFs."
        )
        info_label.setWordWrap(True)
        info_layout.addWidget(info_label)
        info_layout.addSpacing(8)

        # File/folder selection area
        self.file_selection_widget = self._create_file_selection()
        info_layout.addWidget(self.file_selection_widget)
        left_layout.addWidget(info_group)

        # Mode selection
        mode_group = self._create_mode_selection()
        left_layout.addWidget(mode_group)

        # Processing options
        options_group = self._create_processing_options()
        left_layout.addWidget(options_group)

        # Shared components - summarization only (no output group)
        summary_group, self.ai_provider, self.summary_style, self.summary_length, self.auto_summarize, self.ai_status = self.shared_components.create_summarization_group()
        left_layout.addWidget(summary_group)

        # Progress area
        self.progress_widget = self._create_progress_area()
        self.progress_widget.setVisible(False)
        left_layout.addWidget(self.progress_widget)
        left_layout.addStretch()

        ############################
        # Right panel - Results
        ############################

        right_panel = self.create_results_panel()

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 1000])

    def create_results_panel(self):
        """Create the OCR text processing panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Tab widget for different views
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Raw OCR text tab
        self.raw_text_edit = QTextEdit()
        self.raw_text_edit.setPlaceholderText("Raw captured PDF text will appear here...")
        self.tab_widget.addTab(self.raw_text_edit, "Raw PDF")

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

        self.process_pdf_btn = QPushButton("Process PDF")
        self.process_pdf_btn.setCursor(Qt.PointingHandCursor)
        self.process_pdf_btn.clicked.connect(self.start_processing)
        self.process_pdf_btn.setEnabled(False)
        self.process_pdf_btn.setFixedHeight(40)
        button_layout.addWidget(self.process_pdf_btn)

        self.summarize_btn = QPushButton("Summarize")
        self.summarize_btn.setCursor(Qt.PointingHandCursor)
        self.summarize_btn.clicked.connect(lambda: self.parent.summarize_text('pdf'))
        self.summarize_btn.setEnabled(False)
        self.summarize_btn.setFixedHeight(40)
        button_layout.addWidget(self.summarize_btn)

        self.generate_markdown_btn = QPushButton("Generate Markdown")
        self.generate_markdown_btn.setCursor(Qt.PointingHandCursor)
        self.generate_markdown_btn.clicked.connect(lambda: self.parent.generate_final_markdown('pdf'))
        self.generate_markdown_btn.setEnabled(False)
        self.generate_markdown_btn.setFixedHeight(40)
        button_layout.addWidget(self.generate_markdown_btn)

        self.save_btn = QPushButton("Save Content Bundle")
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.clicked.connect(lambda: self.parent.save_markdown('pdf'))
        self.save_btn.setEnabled(False)
        self.save_btn.setFixedHeight(40)
        button_layout.addWidget(self.save_btn)

        layout.addLayout(button_layout)

        return panel

    def _create_mode_selection(self):
        """Create processing mode selection"""
        group = QGroupBox("Processing Mode")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: 600;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 6px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
            }
        """)

        layout = QVBoxLayout(group)
        layout.setContentsMargins(12, 12, 12, 12)
        self.single_mode_radio = QRadioButton("Single PDF")
        self.single_mode_radio.setChecked(True)
        self.single_mode_radio.toggled.connect(self.on_mode_changed)

        self.batch_mode_radio = QRadioButton("Batch Process (Folder)")

        layout.addWidget(self.single_mode_radio)
        layout.addWidget(self.batch_mode_radio)

        return group

    def _create_file_selection(self):
        """Create file/folder selection area"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Single file selection
        self.single_file_widget = QWidget()
        single_layout = QHBoxLayout(self.single_file_widget)
        single_layout.setContentsMargins(0, 0, 0, 0)

        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Select a PDF file...")
        self.file_path_edit.setFixedHeight(30)
        self.file_path_edit.setReadOnly(True)

        browse_file_btn = QPushButton("Browse File")
        browse_file_btn.setCursor(Qt.PointingHandCursor)
        browse_file_btn.clicked.connect(self.browse_single_file)

        single_layout.addWidget(self.file_path_edit, 1)
        single_layout.addWidget(browse_file_btn)

        # Batch folder selection
        self.batch_folder_widget = QWidget()
        batch_layout = QHBoxLayout(self.batch_folder_widget)
        batch_layout.setContentsMargins(0, 0, 0, 0)

        self.folder_path_edit = QLineEdit()
        self.folder_path_edit.setPlaceholderText("Select a folder containing PDFs...")
        self.folder_path_edit.setReadOnly(True)

        browse_folder_btn = QPushButton("Browse Folder")
        browse_folder_btn.setCursor(Qt.PointingHandCursor)
        browse_folder_btn.clicked.connect(self.browse_folder)

        batch_layout.addWidget(self.folder_path_edit, 1)
        batch_layout.addWidget(browse_folder_btn)

        self.batch_folder_widget.setVisible(False)

        layout.addWidget(self.single_file_widget)
        layout.addWidget(self.batch_folder_widget)

        return widget

    def _create_processing_options(self):
        """Create processing options"""
        group = QGroupBox("Processing Options")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: 600;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 6px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
            }
        """)

        layout = QVBoxLayout(group)
        layout.setContentsMargins(12, 12, 12, 12)
        # Chapter detection option
        self.detect_chapters_check = QCheckBox(
            "Automatically detect and split chapters"
        )
        self.detect_chapters_check.setChecked(True)
        self.detect_chapters_check.setStyleSheet("font-size: 13px;")

        layout.addWidget(self.detect_chapters_check)

        # OCR option
        self.use_ocr_check = QCheckBox(
            "Use OCR for image-based pages (slower, higher accuracy)"
        )
        self.use_ocr_check.setChecked(True)
        self.use_ocr_check.setStyleSheet("font-size: 13px;")

        layout.addWidget(self.use_ocr_check)

        return group

    def _create_progress_area(self):
        """Create progress display area"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #E2E8F0;
                border-radius: 4px;
                text-align: center;
                height: 24px;
            }
            QProgressBar::chunk {
                background: #8B5CF6;
                border-radius: 3px;
            }
        """)

        self.progress_label = QLabel("Processing...")
        self.progress_label.setStyleSheet("color: #64748b; font-size: 13px;")

        layout.addWidget(self.progress_bar)
        layout.addWidget(self.progress_label)

        return widget

    # Event handlers
    def on_mode_changed(self, checked):
        """Handle mode change"""
        is_single = self.single_mode_radio.isChecked()
        self.single_file_widget.setVisible(is_single)
        self.batch_folder_widget.setVisible(not is_single)
        self.update_process_button()

    def browse_single_file(self):
        """Browse for single PDF file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select PDF File",
            "",
            "PDF Files (*.pdf)"
        )
        if file_path:
            self.file_path_edit.setText(file_path)
            self.update_process_button()

    def browse_folder(self):
        """Browse for folder containing PDFs"""
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Folder Containing PDFs"
        )
        if folder_path:
            self.folder_path_edit.setText(folder_path)
            self.update_process_button()

    def update_process_button(self):
        """Enable/disable process button based on selections"""
        if self.single_mode_radio.isChecked():
            enabled = bool(self.file_path_edit.text())
        else:
            enabled = bool(self.folder_path_edit.text())
        self.process_pdf_btn.setEnabled(enabled)

    def start_processing(self):
        """Start PDF processing"""
        _LOGGER.info("Starting PDF processing")

        # Collect PDF files to process
        pdf_files = []
        if self.single_mode_radio.isChecked():
            pdf_path = Path(self.file_path_edit.text())
            if pdf_path.exists():
                pdf_files = [pdf_path]
        else:
            folder_path = Path(self.folder_path_edit.text())
            if folder_path.exists():
                pdf_files = list(folder_path.glob("*.pdf"))

        if not pdf_files:
            QMessageBox.warning(self, "No Files", "No PDF files found to process.")
            return

        # Show progress bar
        self.progress_widget.setVisible(True)
        self.progress_bar.setRange(0, len(pdf_files))
        self.progress_bar.setValue(0)
        self.progress_label.setText(f"Processing 0/{len(pdf_files)} files...")

        # Disable process button during processing
        self.process_pdf_btn.setEnabled(False)

        # Clear previous results
        self.raw_text_edit.clear()
        self._processing_results = []

        # Show status in parent status bar
        if hasattr(self.parent, 'statusBar'):
            self.parent.statusBar().showMessage(f"Processing {len(pdf_files)} PDF(s)...")

        # Start PDF processor thread
        self._pdf_processor = PDFProcessor(
            files=pdf_files,
            detect_chapters=self.detect_chapters_check.isChecked(),
            use_ocr=self.use_ocr_check.isChecked()
        )
        self._pdf_processor.processing_progress.connect(self.handle_processing_progress)
        self._pdf_processor.processing_completed.connect(self.handle_processing_completed)
        self._pdf_processor.processing_failed.connect(self.handle_processing_failed)
        self._pdf_processor.start()

    def handle_processing_progress(self, message: str, current: int, total: int):
        """Handle processing progress updates"""
        self.progress_bar.setValue(current)
        self.progress_label.setText(f"{message} ({current}/{total})")

    def handle_processing_completed(self, results: List[PDFProcessingResult]):
        """Handle processing completion"""
        self.progress_widget.setVisible(False)
        self.process_pdf_btn.setEnabled(True)
        self._processing_results = results

        # Build text output from results
        output_text = []
        successful_count = 0
        failed_count = 0

        for result in results:
            if result.success:
                successful_count += 1
                output_text.append(f"{'=' * 80}")
                output_text.append(f"File: {result.file_path.name}")
                output_text.append(f"Total Pages: {result.total_pages}")

                if result.chapters:
                    # Multiple chapters detected
                    output_text.append(f"Chapters Detected: {len(result.chapters)}")
                    output_text.append(f"{'=' * 80}\n")

                    for idx, chapter in enumerate(result.chapters, 1):
                        output_text.append(f"\n--- Chapter {idx}: {chapter['title']} ---")
                        output_text.append(f"Pages: {chapter['start_page'] + 1}-{chapter['end_page'] + 1}")
                        output_text.append(f"\n{chapter['content']}\n")
                else:
                    # Single document
                    if result.failed_pages:
                        output_text.append(f"Failed Pages: {', '.join(map(str, result.failed_pages))}")
                    output_text.append(f"{'=' * 80}\n")
                    output_text.append(result.content)
            else:
                failed_count += 1
                output_text.append(f"{'=' * 80}")
                output_text.append(f"File: {result.file_path.name}")
                output_text.append(f"Status: FAILED")
                output_text.append(f"Error: {result.error}")
                output_text.append(f"{'=' * 80}\n")

        # Set the text in the raw text edit widget
        self.raw_text_edit.setText("\n".join(output_text))

        # Update status bar
        if hasattr(self.parent, 'statusBar'):
            status_msg = f"Processed {len(results)} file(s): {successful_count} successful, {failed_count} failed"
            self.parent.statusBar().showMessage(status_msg)

        # Enable summarize button if we have content
        if successful_count > 0:
            self.summarize_btn.setEnabled(True)

        # Show completion message
        QMessageBox.information(
            self,
            "Processing Complete",
            f"Processed {len(results)} PDF file(s)\n\n"
            f"Successful: {successful_count}\n"
            f"Failed: {failed_count}"
        )

    def handle_processing_failed(self, error: str):
        """Handle processing failure"""
        self.progress_widget.setVisible(False)
        self.process_pdf_btn.setEnabled(True)

        self.raw_text_edit.setText(f"Processing failed:\n\n{error}")

        if hasattr(self.parent, 'statusBar'):
            self.parent.statusBar().showMessage("PDF processing failed")

        QMessageBox.warning(self, "Processing Error", f"PDF processing failed:\n\n{error}")

    def save_all_results(self):
        """Save all processed PDF results as markdown files"""
        successful_results = [r for r in self._processing_results if r.success]

        if not successful_results:
            QMessageBox.information(self, "No Results", "No successful results to save.")
            return

        saved_count = 0
        errors = []

        for result in successful_results:
            try:
                if result.chapters:
                    # Save each chapter as separate file
                    for chapter in result.chapters:
                        self.save_chapter_to_markdown(result, chapter)
                        saved_count += 1
                else:
                    # Save as single document
                    self.save_document_to_markdown(result)
                    saved_count += 1
            except Exception as e:
                errors.append(f"{result.file_path.name}: {str(e)}")

        # Show completion message
        if errors:
            error_msg = "\n".join(errors)
            QMessageBox.warning(
                self,
                "Partial Success",
                f"Saved {saved_count} files successfully.\n\nErrors:\n{error_msg}"
            )
        else:
            QMessageBox.information(
                self,
                "Success",
                f"Successfully saved {saved_count} markdown files!"
            )

        if hasattr(self.parent, 'statusBar'):
            self.parent.statusBar().showMessage(f"Saved {saved_count} markdown files")

    def save_chapter_to_markdown(self, result: PDFProcessingResult, chapter: Dict):
        """Save a single chapter as markdown + metadata"""
        # Generate filename from chapter title
        title = chapter['title']
        filename = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        filename = filename.replace(' ', '_')[:50]  # Limit length

        if not filename:
            filename = f"{result.file_path.stem}_ch{chapter['start_page']}"

        # Get metadata from panel
        metadata = self.metadata_panel.get_metadata(
            'pdf',
            f"pdf_chapter_{chapter['start_page']}_{chapter['end_page']}",
            "none",
            "none"
        )

        # Update metadata with chapter-specific info
        metadata["title"] = title
        metadata["original_source"] = str(result.file_path)
        metadata["page_numbers"] = f"{chapter['start_page'] + 1}-{chapter['end_page'] + 1}"
        metadata["pdf_processing"] = {
            "is_chapter": True,
            "chapter_number": result.chapters.index(chapter) + 1,
            "total_chapters": len(result.chapters)
        }

        # Create markdown content
        markdown_content = f"# {title}\n\n"
        markdown_content += f"**Source:** {result.file_path.name}\n"
        markdown_content += f"**Pages:** {chapter['start_page'] + 1}-{chapter['end_page'] + 1}\n\n"
        markdown_content += chapter['content']

        # Save files
        self.save_markdown_and_metadata(filename, markdown_content, metadata)

    def save_document_to_markdown(self, result: PDFProcessingResult):
        """Save entire document as markdown + metadata"""
        filename = result.file_path.stem

        # Get metadata from panel
        metadata = self.metadata_panel.get_metadata(
            'pdf',
            "pdf_full_document",
            "none",
            "none"
        )

        # Update metadata
        metadata["title"] = self.metadata_panel.title_input.text().strip() or result.file_path.stem
        metadata["original_source"] = str(result.file_path)
        metadata["page_numbers"] = f"1-{result.total_pages}"
        metadata["pdf_processing"] = {
            "is_chapter": False,
            "total_pages": result.total_pages,
            "failed_pages": result.failed_pages
        }

        # Create markdown content
        title = metadata["title"]
        markdown_content = f"# {title}\n\n"
        markdown_content += f"**Source:** {result.file_path.name}\n"
        markdown_content += f"**Total Pages:** {result.total_pages}\n\n"
        markdown_content += result.content

        # Save files
        self.save_markdown_and_metadata(filename, markdown_content, metadata)

    def save_markdown_and_metadata(self, filename: str, markdown_content: str, metadata: dict):
        """Save markdown and metadata JSON files"""
        output_folder = self.parent.get_output_folder()
        output_dir = Path(output_folder)
        output_dir.mkdir(parents=True, exist_ok=True)

        md_path = output_dir / f"{filename}.md"
        json_path = output_dir / f"{filename}.json"

        # Save markdown
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

        # Save metadata
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        _LOGGER.info(f"Saved: {md_path} and {json_path}")

    def reset_fields(self):
        """Reset all fields and content"""
        # Clear text areas
        self.raw_text_edit.clear()
        self.summary_text_edit.clear()
        self.markdown_edit.clear()

        # Reset buttons
        self.process_pdf_btn.setEnabled(False)
        self.summarize_btn.setEnabled(False)
        self.generate_markdown_btn.setEnabled(False)
        self.save_btn.setEnabled(False)

        # Switch back to first tab
        self.tab_widget.setCurrentIndex(0)

        # Clear current image path
        self.current_image_path = None

        self.parent.statusBar().showMessage("PDF mode reset - ready for new content")
