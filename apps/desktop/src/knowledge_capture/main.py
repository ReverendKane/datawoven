# --- Windows Qt DLL path fix (must run before importing PySide6) ---
import os, sys, pathlib

env_root = sys.prefix
qt_bin = pathlib.Path(env_root, "Library", "bin")
if qt_bin.exists():
    os.add_dll_directory(str(qt_bin))

pyside_path = pathlib.Path(env_root, "Lib", "site-packages", "PySide6")
if pyside_path.exists():
    os.environ.pop("QT_PLUGIN_PATH", None)
    os.environ.pop("QT_QPA_PLATFORM_PLUGIN_PATH", None)
    os.environ["QT_PLUGIN_PATH"] = str(pyside_path / "plugins")
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(pyside_path / "plugins")
    os.environ["PATH"] = str(pyside_path) + os.pathsep + os.environ.get("PATH", "")
    if (pyside_path / "Qt6WebEngineCore.dll").exists():
        os.add_dll_directory(str(pyside_path))
    os.environ["QTWEBENGINEPROCESS_PATH"] = str(pyside_path / "QtWebEngineProcess.exe")
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu"
# -------------------------------------------------------------------

# SET UP LOGGING
import logging
import logging.config

class ExtraContextFilter(logging.Filter):
    """
    Ensures every LogRecord has a 'ctx' attribute so %(ctx)s in the formatter
    never fails. If a module didn't provide 'ctx', fall back to the logger name.
    """
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "ctx"):
            record.ctx = record.name
        return True

def setup_logging(level: str = "INFO") -> None:
    """
    Configure console logging with a contextual field [%(ctx)s].
    """
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "add_ctx": {"()": ExtraContextFilter},
        },
        "formatters": {
            "console": {
                "format": "%(asctime)s | %(levelname)-8s | [%(ctx)s] %(name)s:%(lineno)d - %(message)s",
                "datefmt": "%H:%M:%S",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "DEBUG",
                "formatter": "console",
                "filters": ["add_ctx"],
                "stream": "ext://sys.stdout",
            }
        },
        "root": {
            "level": level,
            "handlers": ["console"],
        },
        # Optional: quiet down noisy third-party loggers here
        "loggers": {
            "urllib3": {"level": "WARNING"},
            "botocore": {"level": "WARNING"},
            "PySide6": {"level": "WARNING"},
        },
    }
    logging.config.dictConfig(config)


setup_logging(level="DEBUG")   # or "INFO" in production

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
LOG_CTX = "Main"
log = logging.LoggerAdapter(logging.getLogger(__name__), {"ctx": LOG_CTX})
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


from PySide6.QtWidgets import QApplication, QWidget, QSizePolicy
import sys, os, json, uuid, tempfile, requests
from dotenv import load_dotenv
import openai, anthropic
import google.generativeai as genai
from pathlib import Path
from datetime import datetime
import json, gzip, hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import cv2, numpy as np, pytesseract
from PIL import Image, ImageEnhance, ImageFilter
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QLabel, QPushButton, QFileDialog, QMessageBox,
    QTabWidget, QScrollArea, QFrame, QSplitter, QGroupBox, QFormLayout,
    QCheckBox, QSpinBox, QComboBox, QProgressBar
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSettings, QPoint, QRect
from PySide6.QtGui import (
    QPixmap, QScreen, QPainter, QPen, QColor, QFont, QAction,
    QKeySequence, QShortcut, QIcon, QTextCharFormat, QTextCursor
)
from markdown_dialog import MarkdownDialog

# Import modular tabs
from ocr_tab import OCRTab
from text_input_tab import TextInputTab
from markdown_import_tab import MarkdownImportTab
from pdf_tab import PDFTab
from web_scraping_tab import WebScrapingTab
from post_processing_tab import PostProcessingTab
from auto_tab import AutoTab
from project_selector import ProjectSelector

import pytesseract

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


class ScreenshotCapture(QWidget):
    """Enhanced full-screen overlay for screenshot selection with multi-monitor support"""
    screenshot_taken = Signal(QPixmap)

    def __init__(self):
        super().__init__()
        self.setWindowFlag(Qt.FramelessWindowHint, True)
        self.setWindowState(Qt.WindowFullScreen)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setCursor(Qt.CrossCursor)

        app = QApplication.instance()
        screens = app.screens()
        if len(screens) > 1:
            virtual_geometry = QRect()
            for screen in screens:
                virtual_geometry = virtual_geometry.united(screen.geometry())
            total_width = virtual_geometry.width()
            total_height = virtual_geometry.height()
            self._full_pix = QPixmap(total_width, total_height)
            self._full_pix.fill(Qt.black)
            painter = QPainter(self._full_pix)
            for screen in screens:
                screen_geometry = screen.geometry()
                screen_pixmap = screen.grabWindow(0)
                offset_x = screen_geometry.x() - virtual_geometry.x()
                offset_y = screen_geometry.y() - virtual_geometry.y()
                painter.drawPixmap(offset_x, offset_y, screen_pixmap)
            painter.end()
            self.setGeometry(virtual_geometry)
        else:
            desktop = app.primaryScreen()
            self._full_pix = desktop.grabWindow(0)

        self._dragging = False
        self._origin = QPoint()
        self._current = QPoint()
        self._rubber = QRect()
        self._dpr = self._full_pix.devicePixelRatio()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.drawPixmap(0, 0, self._full_pix)
        overlay_color = QColor(0, 0, 0, 153)
        painter.fillRect(self.rect(), overlay_color)
        if not self._rubber.isNull():
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            painter.drawPixmap(self._rubber.topLeft(), self._full_pix.copy(self._rubber))
            pen = QPen(QColor("#60A5FA"))
            pen.setWidth(3)
            pen.setStyle(Qt.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self._rubber)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._origin = event.position().toPoint()
            self._current = self._origin
            self._rubber = QRect(self._origin, self._current)
            self.update()
        elif event.button() == Qt.RightButton:
            self.close()

    def mouseMoveEvent(self, event):
        if self._dragging:
            self._current = event.position().toPoint()
            self._rubber = QRect(self._origin, self._current).normalized()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._dragging:
            self._dragging = False
            if self._rubber.isNull() or self._rubber.width() < 5 or self._rubber.height() < 5:
                self.close()
                return
            cropped = self._full_pix.copy(self._rubber)
            self.screenshot_taken.emit(cropped)
            self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class OCRProcessor(QThread):
    """Background thread for OCR processing"""
    ocr_completed = Signal(str)
    ocr_failed = Signal(str)

    def __init__(self, image_path: str, preprocess: bool = True):
        super().__init__()
        self.image_path = image_path
        self.preprocess = preprocess

    def run(self):
        try:
            image = cv2.imread(self.image_path)
            if self.preprocess:
                image = self.preprocess_image(image)
            pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            configs = [
                r'--oem 3 --psm 6 -c preserve_interword_spaces=1',
                r'--oem 3 --psm 4 -c preserve_interword_spaces=1',
                r'--oem 3 --psm 3',
                r'--oem 3 --psm 11',
                r'--oem 3 --psm 6'
            ]
            best_text = ""
            best_confidence = 0
            for config in configs:
                try:
                    data = pytesseract.image_to_data(pil_image, config=config, output_type=pytesseract.Output.DICT)
                    confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                    text = pytesseract.image_to_string(pil_image, config=config)
                    if avg_confidence > best_confidence and len(text.strip()) > 10:
                        best_confidence = avg_confidence
                        best_text = text
                except Exception:
                    continue
            if not best_text.strip():
                best_text = pytesseract.image_to_string(pil_image, config=r'--oem 3 --psm 6')
            processed_text = self.post_process_text(best_text)
            self.ocr_completed.emit(processed_text)
        except Exception as e:
            self.ocr_failed.emit(str(e))

    def preprocess_image(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        height, width = gray.shape
        if height < 300 or width < 300:
            scale_factor = max(2.0, 300 / min(height, width))
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        denoised = cv2.fastNlMeansDenoising(gray)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
        blurred = cv2.GaussianBlur(enhanced, (1, 1), 0)
        _, thresh1 = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        thresh2 = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        white_pixels_1 = cv2.countNonZero(thresh1)
        white_pixels_2 = cv2.countNonZero(thresh2)
        thresh = thresh1 if white_pixels_1 > white_pixels_2 else thresh2
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)
        return cleaned

    def post_process_text(self, text: str) -> str:
        import re
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
        text = re.sub(r'(\d)([A-Za-z])', r'\1 \2', text)
        text = re.sub(r'([A-Za-z])(\d)', r'\1 \2', text)
        text = re.sub(r'\.([A-Z])', r'. \1', text)
        text = re.sub(r'(ing|tion|ness|ment|able|ible)([A-Z])', r'\1 \2', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        replacements = {
            r'[|]': 'I', r"[`''']": "'", r'["""]': '"',
            r'ÃƒÂ¢Ã¢â€šÂ¬"': '-', r'ÃƒÂ¢Ã¢â€šÂ¬"': '-', r'ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦': '...'
        }
        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text)
        text = re.sub(r'\s+([,.!?;:])', r'\1', text)
        text = re.sub(r'([,.!?;:])\s*', r'\1 ', text)
        return text.strip()


class MultiProviderSummarizationProcessor(QThread):
    """Background thread for AI summarization using multiple providers"""
    summarization_completed = Signal(str)
    summarization_failed = Signal(str)

    def __init__(self, text: str, summary_style: str = "comprehensive",
                 summary_length: str = "Detailed (100%)", provider: str = "ollama"):
        super().__init__()
        self.text = text
        self.summary_style = summary_style
        self.summary_length = summary_length
        self.provider = provider
        self.ollama_url = "http://localhost:11434/api/generate"
        load_dotenv()
        self.openai_client = None
        self.anthropic_client = None
        self.genai_client = None
        self.setup_api_clients()

    def setup_api_clients(self):
        try:
            openai_key = os.getenv('OPENAI_API_KEY')
            if openai_key:
                self.openai_client = openai.OpenAI(api_key=openai_key)
            anthropic_key = os.getenv('ANTHROPIC_API_KEY')
            if anthropic_key:
                self.anthropic_client = anthropic.Anthropic(api_key=anthropic_key)
            google_key = os.getenv('GOOGLE_API_KEY')
            if google_key:
                genai.configure(api_key=google_key)
                self.genai_client = genai
        except Exception as e:
            log.info(f"API setup error: {e}")

    def run(self):
        try:
            if self.provider == "ollama" and self.is_ollama_available():
                summary = self.llama3_summarize(self.text)
            elif self.provider == "openai" and self.openai_client:
                summary = self.openai_summarize(self.text)
            elif self.provider == "claude" and self.anthropic_client:
                summary = self.claude_summarize(self.text)
            elif self.provider == "gemini" and self.genai_client:
                summary = self.gemini_summarize(self.text)
            else:
                summary = self.extractive_summarize(self.text)
            self.summarization_completed.emit(summary)
        except Exception as e:
            try:
                summary = self.extractive_summarize(self.text)
                self.summarization_completed.emit(f"<!-- Fallback: {str(e)} -->\n{summary}")
            except Exception as fallback_error:
                self.summarization_failed.emit(f"Primary: {str(e)}, Fallback: {str(fallback_error)}")

    def get_base_prompt(self) -> str:
        length_ratios = {"Detailed (100%)": 0.95, "Moderate (75%)": 0.85, "Concise (50%)": 0.70}
        target_ratio = length_ratios.get(self.summary_length, 0.80)
        input_token_estimate = len(self.text.split()) * 1.3
        target_tokens = int(input_token_estimate * target_ratio)

        # Shortened prompts to save tokens
        if self.summary_style == "comprehensive":
            return f"Transform text into knowledge base entry. Remove book/chapter references, author interaction, navigation, visual references. Preserve technical content, examples, details. Target: {target_tokens} tokens.\n\n"
        elif self.summary_style == "bullet_points":
            return f"Extract key points as bullets. Remove figures, meta-commentary. Target: {target_tokens} tokens max.\n\n"
        else:
            return f"Extract core concepts. Remove source references. Target: {target_tokens} tokens max.\n\n"

    def openai_summarize(self, text: str) -> str:
        prompt = self.get_base_prompt() + text
        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "Create focused knowledge base summaries."},
                      {"role": "user", "content": prompt}],
            max_tokens=4000, temperature=0.2
        )
        return self.clean_intro_text(response.choices[0].message.content.strip())

    def claude_summarize(self, text: str) -> str:
        prompt = self.get_base_prompt() + text
        response = self.anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022", max_tokens=8000, temperature=0.3,
            system="Create comprehensive knowledge base summaries.",
            messages=[{"role": "user", "content": prompt}]
        )
        return self.clean_intro_text(response.content[0].text.strip())

    def gemini_summarize(self, text: str) -> str:
        prompt = self.get_base_prompt() + text
        model = self.genai_client.GenerativeModel('gemini-1.5-pro')
        config = genai.types.GenerationConfig(max_output_tokens=8000, temperature=0.3)
        response = model.generate_content(prompt, generation_config=config)
        return self.clean_intro_text(response.text.strip())

    def clean_intro_text(self, text: str) -> str:
        import re
        for p in [r'^Here is.*?:', r'^This.*?:', r'^The.*?:', r'^Summary:', r'^Based on.*?:']:
            text = re.sub(p, '', text, flags=re.IGNORECASE).strip()
        for p in [r'[Tt]his (book|chapter)[^\.]*?\.?\s*', r'[Ww]e (will|intend)[^\.]*?\.?\s*',
                  r'Figure \d+[^\n]*\n?', r'Table \d+[^\n]*\n?']:
            text = re.sub(p, '', text, flags=re.IGNORECASE)
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        return text.strip()

    def is_ollama_available(self) -> bool:
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                models = response.json().get('models', [])
                return any('llama3' in m.get('name', '').lower() for m in models)
        except:
            pass
        return False

    def llama3_summarize(self, text: str) -> str:
        length_ratios = {"Detailed (100%)": 0.80, "Moderate (75%)": 0.60, "Concise (50%)": 0.40}
        target_ratio = length_ratios.get(self.summary_length, 0.80)
        input_tokens = len(text.split()) * 1.3
        max_tokens = max(1000, min(8000, int(input_tokens * target_ratio)))
        prompt = self.get_base_prompt() + text
        payload = {"model": "llama3", "prompt": prompt, "stream": False,
                   "options": {"temperature": 0.3, "top_p": 0.9, "max_tokens": max_tokens, "repeat_penalty": 1.1}}
        response = requests.post(self.ollama_url, json=payload, timeout=60,
                                 headers={'Content-Type': 'application/json'})
        if response.status_code == 200:
            return self.clean_intro_text(response.json().get('response', '').strip())
        raise Exception(f"Ollama failed: {response.status_code}")

    def extractive_summarize(self, text: str) -> str:
        import re
        sentences = re.split(r'[.!?]+\s+', text.replace('\n', ' '))
        sentences = [s.strip() for s in sentences if s.strip()]
        if len(sentences) <= 3:
            return text[:len(text) // 2] + "..." if len(text.split()) > 50 else text
        length_ratios = {"Detailed (100%)": 0.70, "Moderate (75%)": 0.50, "Concise (50%)": 0.30}
        target_ratio = length_ratios.get(self.summary_length, 0.70)
        word_freq = {}
        for word in text.lower().split():
            if len(word) > 3:
                word_freq[word] = word_freq.get(word, 0) + 1
        sentence_scores = {}
        for i, s in enumerate(sentences):
            score = sum(word_freq.get(w, 0) for w in s.lower().split())
            if i < 5 or i >= len(sentences) - 5:
                score *= 1.2
            sentence_scores[s] = score
        num_sentences = max(5, int(len(sentences) * target_ratio))
        top = sorted(sentence_scores.items(), key=lambda x: x[1], reverse=True)[:num_sentences]
        summary = [s for s in sentences if any(s == t[0] for t in top)]
        return '. '.join(summary) + '.'


class AIMetadataGenerator(QThread):
    """Background thread for AI-powered metadata generation"""
    generation_completed = Signal(dict)
    generation_failed = Signal(str)

    def __init__(self, markdown_content: str):
        super().__init__()
        self.markdown_content = markdown_content
        load_dotenv()
        openai_key = os.getenv('OPENAI_API_KEY')
        self.openai_client = openai.OpenAI(api_key=openai_key) if openai_key else None

    def run(self):
        try:
            if not self.openai_client:
                self.generation_failed.emit("OpenAI API key not found")
                return
            words = self.markdown_content.split()
            content = ' '.join(words[:3000]) + "\n[truncated]" if len(words) > 3000 else self.markdown_content
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system",
                     "content": "Generate metadata: 3-5 lowercase tags, 2-sentence notes. Return JSON: {\"tags\": [...], \"notes\": \"...\"}"},
                    {"role": "user", "content": f"Analyze:\n\n{content}"}
                ],
                temperature=0.3, max_tokens=500, response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content.strip())
            result["tags"] = [t.strip().lower() for t in result.get("tags", []) if t.strip()]
            result["notes"] = result.get("notes", "")
            self.generation_completed.emit(result)
        except Exception as e:
            self.generation_failed.emit(f"AI generation failed: {e}")


class SharedComponents:
    """Shared UI components"""

    @staticmethod
    def create_summarization_group():
        group = QGroupBox("Summarization")
        layout = QFormLayout(group)
        layout.setContentsMargins(12, 12, 12, 12)
        provider = QComboBox()
        provider.addItems(["openai", "claude", "ollama", "gemini"])
        layout.addRow("AI Provider:", provider)
        style = QComboBox()
        style.addItems(["comprehensive", "bullet_points", "key_quotes"])
        layout.addRow("Style:", style)
        length = QComboBox()
        length.addItems(["Detailed (100%)", "Moderate (75%)", "Concise (50%)"])
        layout.addRow("Length:", length)
        auto = QCheckBox("Auto-summarize")
        layout.addRow("", auto)
        status = QLabel("Checking AI providers...")
        layout.addRow("AI Status:", status)
        return group, provider, style, length, auto, status

    @staticmethod
    def create_metadata_group():
        group = QGroupBox("Metadata")
        layout = QFormLayout(group)
        title = QLineEdit()
        title.setPlaceholderText("Optional title...")
        layout.addRow("Title:", title)
        source = QLineEdit()
        source.setPlaceholderText("Source URL, book, etc...")
        layout.addRow("Source:", source)
        tags = QLineEdit()
        tags.setPlaceholderText("tag1, tag2, tag3...")
        layout.addRow("Tags:", tags)
        return group, title, source, tags

    @staticmethod
    def create_output_group():
        group = QGroupBox("Output")
        layout = QVBoxLayout(group)
        folder_input = QLineEdit()
        folder_input.setText(str(Path.home() / "Documents" / "KnowledgeBase"))
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(folder_input)
        browse = QPushButton("Browse")
        browse.setCursor(Qt.PointingHandCursor)
        folder_layout.addWidget(browse)
        layout.addLayout(folder_layout)
        save = QPushButton("Save as Markdown")
        save.setEnabled(False)
        layout.addWidget(save)
        copy = QPushButton("Copy to Clipboard")
        copy.setEnabled(False)
        layout.addWidget(copy)
        return group, folder_input, browse, save, copy


class MetadataPanel(QWidget):
    """Shared metadata panel"""

    def __init__(self, output_folder_callback, tab_widget_callback):
        super().__init__()
        self.output_folder_callback = output_folder_callback
        self.tab_widget_callback = tab_widget_callback
        self.current_metadata = {}
        self.init_ui()
        self.setFixedHeight(500)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        header = QHBoxLayout()
        label = QLabel("Set Metadata")
        label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header.addWidget(label)
        header.addStretch()
        self.clear_btn = QPushButton("Clear Fields")
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.clicked.connect(self.clear_fields)
        header.addWidget(self.clear_btn)
        self.load_existing_btn = QPushButton("Load Existing")
        self.load_existing_btn.setCursor(Qt.PointingHandCursor)
        self.load_existing_btn.clicked.connect(self.load_existing_document)
        self.load_existing_btn.setEnabled(False)
        header.addWidget(self.load_existing_btn)
        self.quick_fill_btn = QPushButton("Quick Fill")
        self.quick_fill_btn.setCursor(Qt.PointingHandCursor)
        self.quick_fill_btn.clicked.connect(self.show_quick_fill_menu)
        header.addWidget(self.quick_fill_btn)
        layout.addLayout(header)

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.source_type = QComboBox()
        self.source_type.setFixedHeight(30)
        self.source_type.addItems(
            ["Auto-detect", "book", "screenshot", "web_scrape", "manual_notes", "document", "pre-formatted", "other"])
        form.addRow("Source Type:", self.source_type)
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Document title...")
        form.addRow("Title:", self.title_input)
        self.original_source = QLineEdit()
        self.original_source.setPlaceholderText("Book title, URL, etc...")
        form.addRow("Original Source:", self.original_source)
        self.author_input = QLineEdit()
        self.author_input.setPlaceholderText("Author name(s)...")
        form.addRow("Author:", self.author_input)
        self.page_numbers = QLineEdit()
        self.page_numbers.setPlaceholderText("e.g., 45-52")
        form.addRow("Page Numbers:", self.page_numbers)
        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("comma, separated, tags")
        form.addRow("Tags:", self.tags_input)
        self.priority = QComboBox()
        self.priority.setFixedHeight(30)
        self.priority.addItems(["medium", "high", "low"])
        form.addRow("Priority:", self.priority)
        self.ready_checkbox = QCheckBox("Ready for Pipeline 2 processing")
        self.ready_checkbox.setChecked(True)
        form.addRow("", self.ready_checkbox)
        self.quality = QComboBox()
        self.quality.setFixedHeight(30)
        self.quality.addItems(["good", "excellent", "needs_review", "poor"])
        form.addRow("Quality:", self.quality)
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Additional notes...")
        self.notes_input.setMaximumHeight(80)
        form.addRow("Notes:", self.notes_input)

        # Save To field removed - auto-routing based on tab/project handles all paths
        # Paths are deterministic: /DATA/project-name/raw-output/{source-type}/

        layout.addLayout(form)

        self.setStyleSheet("""
            QPushButton {padding: 6px 12px; border: 1px solid #555; border-radius: 4px; background: #404040; color: #fff;}
            QPushButton:hover {background: #000; border: none;}
            QPushButton:pressed {background: #222; border: none;}
            QPushButton:disabled {background: #2a2a2a; color: #666; border-color: #333;}
            QLineEdit {border: 1px solid #555; border-radius: 4px; padding: 4px 8px; background: #2d2d2d; color: #fff;}
            QLineEdit:focus {border: 1px solid #60A5FA; background: #353535;}
            QTextEdit {border: 1px solid #555; border-radius: 4px; padding: 4px 8px; background: #2d2d2d; color: #fff;}
            QTextEdit:focus {border: 1px solid #60A5FA; background: #353535;}
            QComboBox {padding: 4px 8px;}
            QComboBox QAbstractItemView::item {min-height: 30px; padding: 6px 8px;}
        """)

    def auto_detect_source_type(self, mode, has_page_numbers, has_url, has_screenshot):
        if self.source_type.currentText() != "Auto-detect":
            return self.source_type.currentText()
        if mode == "ocr" and has_screenshot:
            return "book" if has_page_numbers else "screenshot"
        elif mode == "text":
            if has_url:
                return "web_scrape"
            elif has_page_numbers:
                return "book"
            return "manual_notes"
        return "document"

    def update_load_button_state(self, tab_index):
        self.load_existing_btn.setEnabled(tab_index == 2)

    def load_existing_document(self):
        start_path = self.output_folder_callback() or ""
        json_path, _ = QFileDialog.getOpenFileName(self, "Select JSON", start_path,
                                                   "JSON Files (*.json)")
        if not json_path: return
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            md_path = Path(json_path).with_suffix('.md')
            if not md_path.exists():
                QMessageBox.warning(self, "Not Found", f"Markdown file not found:\n{md_path}")
                return
            with open(md_path, 'r', encoding='utf-8') as f:
                markdown_content = f.read()
            self.populate_from_metadata(metadata)
            self.loaded_markdown_content = markdown_content
            self.loaded_metadata = metadata
            QMessageBox.information(self, "Loaded", f"Loaded:\n{md_path.name}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed: {e}")

    def populate_from_metadata(self, metadata):
        idx = self.source_type.findText(metadata.get("source_type", "Auto-detect"))
        if idx >= 0: self.source_type.setCurrentIndex(idx)
        self.title_input.setText(metadata.get("title", ""))
        self.original_source.setText(metadata.get("original_source", ""))
        self.author_input.setText(metadata.get("author", ""))
        self.page_numbers.setText(metadata.get("page_numbers", ""))
        tags = metadata.get("tags", [])
        self.tags_input.setText(", ".join(tags) if isinstance(tags, list) else str(tags))
        idx = self.priority.findText(metadata.get("processing_priority", "medium"))
        if idx >= 0: self.priority.setCurrentIndex(idx)
        self.ready_checkbox.setChecked(metadata.get("ready_for_processing", True))
        idx = self.quality.findText(metadata.get("quality_assessment", "good"))
        if idx >= 0: self.quality.setCurrentIndex(idx)
        self.notes_input.setPlainText(metadata.get("notes", ""))

    def get_metadata(self, mode, processing_method, ai_provider, summary_style):
        has_page_numbers = bool(self.page_numbers.text().strip())
        has_url = "http://" in self.original_source.text() or "https://" in self.original_source.text()
        has_screenshot = mode == "ocr"
        detected_type = self.auto_detect_source_type(mode, has_page_numbers, has_url, has_screenshot)
        tags_text = self.tags_input.text().strip()
        tags = [t.strip() for t in tags_text.split(",") if t.strip()] if tags_text else []
        metadata = {
            "document_id": str(uuid.uuid4()), "source_type": detected_type,
            "original_source": self.original_source.text().strip(),
            "capture_date": datetime.now().isoformat(), "processing_method": processing_method,
            "tags": tags, "notes": self.notes_input.toPlainText().strip(),
            "title": self.title_input.text().strip(), "page_numbers": self.page_numbers.text().strip(),
            "author": self.author_input.text().strip(), "ready_for_processing": self.ready_checkbox.isChecked(),
            "processing_priority": self.priority.currentText(), "ai_provider_used": ai_provider,
            "summary_style": summary_style, "quality_assessment": self.quality.currentText(),
            "storage_location": self.output_folder_callback()
        }
        self.current_metadata = metadata
        return metadata

    def save_as_defaults(self):
        try:
            defaults_path = Path(self.output_folder_callback()) / "metadata_defaults.json"
            defaults = {"source_type": self.source_type.currentText(), "author": self.author_input.text().strip(),
                        "tags": self.tags_input.text().strip(), "priority": self.priority.currentText(),
                        "ready_for_processing": self.ready_checkbox.isChecked(), "quality": self.quality.currentText()}
            with open(defaults_path, 'w', encoding='utf-8') as f:
                json.dump(defaults, f, indent=2)
        except Exception as e:
            log.info(f"Failed to save defaults: {e}")

    def clear_fields(self):
        self.source_type.setCurrentIndex(0)
        self.title_input.clear()
        self.original_source.clear()
        self.author_input.clear()
        self.page_numbers.clear()
        self.tags_input.clear()
        self.priority.setCurrentIndex(0)
        self.ready_checkbox.setChecked(True)
        self.quality.setCurrentIndex(0)
        self.notes_input.clear()

    def show_quick_fill_menu(self):
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        menu.addAction("Book Chapter").triggered.connect(self.quick_fill_book)
        menu.addAction("Web Article").triggered.connect(self.quick_fill_web)
        menu.addAction("Technical Documentation").triggered.connect(self.quick_fill_docs)
        menu.exec(self.quick_fill_btn.mapToGlobal(self.quick_fill_btn.rect().bottomLeft()))

    def quick_fill_book(self):
        self.source_type.setCurrentText("book")
        self.tags_input.setText("data_engineering, rag_implementation")
        self.priority.setCurrentText("high")
        self.quality.setCurrentText("excellent")

    def quick_fill_web(self):
        self.source_type.setCurrentText("web_scrape")
        self.tags_input.setText("web_content")
        self.priority.setCurrentText("medium")

    def quick_fill_docs(self):
        self.source_type.setCurrentText("document")
        self.tags_input.setText("technical_docs, reference")
        self.priority.setCurrentText("high")
        self.quality.setCurrentText("excellent")

    def log_metadata(self, metadata):
        log.info("\n" + "=" * 60 + "\nCAPTURE METADATA\n" + "=" * 60)
        log.info(json.dumps(metadata, indent=2))
        log.info("=" * 60 + "\n")


class KnowledgeCaptureApp(QMainWindow):
    """Main application"""

    def __init__(self):
        super().__init__()
        self.settings = QSettings('KnowledgeCapture', 'ScreenshotTool')
        self.summarization_thread = None
        self.ScreenshotCapture = ScreenshotCapture
        self.OCRProcessor = OCRProcessor
        self.AIMetadataGenerator = AIMetadataGenerator

        # Project management
        self.current_project_name = None
        self.current_project_path = None

        self.init_ui()
        self.setup_shortcuts()
        self.load_settings()
        self.check_ai_status()

    def init_ui(self):
        self.setWindowTitle("Knowledge Capture")
        self.setGeometry(100, 100, 1400, 900)
        self.setStyleSheet("""
            QPushButton {padding: 6px 12px; border: 1px solid #555; border-radius: 4px; background: #404040; color: #fff;}
            QPushButton:hover {background: #000; border: none;}
            QPushButton:pressed {background: #222; border: none;}
            QPushButton:disabled {background: #2a2a2a; color: #666; border-color: #333;}
        """)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setCentralWidget(scroll)
        main_widget = QWidget()
        main_widget.setMinimumHeight(1200)
        scroll.setWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Add project selector at the top
        self.project_selector = ProjectSelector(self)
        self.project_selector.project_changed.connect(self.on_project_changed)
        layout.addWidget(self.project_selector)

        self.metadata_panel = MetadataPanel(self.get_output_folder, lambda: self.mode_tabs.currentIndex())
        layout.addWidget(self.metadata_panel)

        self.mode_tabs = QTabWidget()
        self.mode_tabs.setMinimumHeight(600)
        self.mode_tabs.currentChanged.connect(self.on_tab_changed)
        layout.addWidget(self.mode_tabs, 1)

        shared = SharedComponents()
        self.ocr_tab = OCRTab(self, shared, self.metadata_panel)
        self.mode_tabs.addTab(self.ocr_tab, "Screenshot OCR")
        self.text_tab = TextInputTab(self, shared, self.metadata_panel)
        self.mode_tabs.addTab(self.text_tab, "Text Input")
        self.markdown_tab = MarkdownImportTab(self, self.metadata_panel)
        self.mode_tabs.addTab(self.markdown_tab, "Markdown Import")
        self.pdf_tab = PDFTab(self, shared, self.metadata_panel)
        self.mode_tabs.addTab(self.pdf_tab, "PDF Import")
        self.web_tab = WebScrapingTab(self, shared, self.metadata_panel)
        self.mode_tabs.addTab(self.web_tab, "Web Scraping")
        self.post_processing_tab = PostProcessingTab(self, shared, self.metadata_panel)
        self.mode_tabs.addTab(self.post_processing_tab, "Post-Processing")

        self.auto_tab = AutoTab(self, shared, self.metadata_panel)
        self.mode_tabs.addTab(self.auto_tab, "Auto")

        self.statusBar().showMessage("Ready for knowledge capture")
        self.ocr_tab.ai_provider.currentTextChanged.connect(self.sync_ai_providers)
        self.text_tab.ai_provider.currentTextChanged.connect(self.sync_ai_providers)
        self.pdf_tab.ai_provider.currentTextChanged.connect(self.sync_ai_providers)

    def sync_ai_providers(self, provider):
        self.ocr_tab.ai_provider.blockSignals(True)
        self.text_tab.ai_provider.blockSignals(True)
        self.pdf_tab.ai_provider.blockSignals(True)
        self.web_tab.ai_provider.blockSignals(True)
        self.ocr_tab.ai_provider.setCurrentText(provider)
        self.text_tab.ai_provider.setCurrentText(provider)
        self.pdf_tab.ai_provider.setCurrentText(provider)
        self.web_tab.ai_provider.setCurrentText(provider)
        self.ocr_tab.ai_provider.blockSignals(False)
        self.text_tab.ai_provider.blockSignals(False)
        self.pdf_tab.ai_provider.blockSignals(False)
        self.web_tab.ai_provider.blockSignals(False)

    def get_output_folder(self) -> str:
        """Helper to get current output folder based on active tab and project"""
        if not hasattr(self, 'project_selector'):
            return ""

        current_tab = self.mode_tabs.currentIndex()

        # Map tab index to source type
        tab_to_source_type = {
            0: 'ocr',
            1: 'text',
            3: 'pdf',
            4: 'web'
        }

        source_type = tab_to_source_type.get(current_tab)
        if source_type:
            return self.project_selector.get_output_path_for_type(source_type) or ""
        else:
            # For tabs without specific routing, use base raw-output
            return self.project_selector.get_raw_output_path() or ""

    def on_project_changed(self, project_name: str, project_path: str):
        """Handle project selection change"""
        log.info(f"Project changed: {project_name} ({project_path})")
        self.current_project_name = project_name
        self.current_project_path = project_path
        self.metadata_panel.update_load_button_state(self.mode_tabs.currentIndex())
        self.metadata_panel.save_as_defaults()
        self.current_project_name = project_name
        self.current_project_path = project_path

        # Update auto tab with new database path
        if hasattr(self, 'auto_tab'):
            db_path = self.project_selector.get_database_path()
            if db_path:
                self.auto_tab.set_database_path(db_path)

        self.statusBar().showMessage(f"Project switched to: {project_name}")

    def on_tab_changed(self, index):
        """Handle tab changes - paths auto-routed via get_output_folder()"""
        self.metadata_panel.update_load_button_state(index)

        if index == 2 and hasattr(self.metadata_panel, 'loaded_markdown_content'):
            self.markdown_tab.populate_loaded_content()

    def setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+Shift+S"), self).activated.connect(self.ocr_tab.start_screenshot_capture)

    def load_settings(self):
        """Load application settings"""
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

    def save_settings(self):
        """Save application settings"""
        self.settings.setValue("geometry", self.saveGeometry())

    def check_ai_status(self):
        def update():
            msgs = []
            try:
                r = requests.get("http://localhost:11434/api/tags", timeout=2)
                if r.status_code == 200:
                    has_llama = any('llama3' in m.get('name', '').lower() for m in r.json().get('models', []))
                    msgs.append("Ollama: Available" if has_llama else "Ollama: No Llama3")
                else:
                    msgs.append("Ollama: Not Running")
            except:
                msgs.append("Ollama: Unavailable")
            load_dotenv()
            msgs.append("OpenAI: Ready" if os.getenv('OPENAI_API_KEY') else "OpenAI: No Key")
            msgs.append("Claude: Ready" if os.getenv('ANTHROPIC_API_KEY') else "Claude: No Key")
            msgs.append("Gemini: Ready" if os.getenv('GOOGLE_API_KEY') else "Gemini: No Key")
            status = " | ".join(msgs)
            self.ocr_tab.ai_status.setText(status)
            self.text_tab.ai_status.setText(status)

        QTimer.singleShot(100, update)

    def summarize_text(self, mode):
        if mode == 'ocr':
            text = self.ocr_tab.raw_text_edit.toPlainText()
            provider = self.ocr_tab.ai_provider.currentText()
            style = self.ocr_tab.summary_style.currentText()
            length = self.ocr_tab.summary_length.currentText()
            progress = self.ocr_tab.progress_bar
        elif mode == "pdf":
            text = self.pdf_tab.raw_text_edit.toPlainText()
            provider = self.pdf_tab.ai_provider.currentText()
            style = self.pdf_tab.summary_style.currentText()
            length = self.pdf_tab.summary_length.currentText()
            progress = self.pdf_tab.progress_bar
        elif mode == "web":
            text = self.web_tab.raw_text_edit.toPlainText()
            provider = self.web_tab.ai_provider.currentText()
            style = self.web_tab.summary_style.currentText()
            length = self.web_tab.summary_length.currentText()
            progress = self.web_tab.progress_bar
        else:
            text = self.text_tab.input_edit.toPlainText()
            provider = self.text_tab.ai_provider.currentText()
            style = self.text_tab.summary_style.currentText()
            length = self.text_tab.summary_length.currentText()
            progress = self.text_tab.progress_bar
        if not text.strip(): return
        progress.setVisible(True)
        progress.setRange(0, 0)
        self.statusBar().showMessage(f"Summarizing with {provider}...")
        self.summarization_thread = MultiProviderSummarizationProcessor(text, style, length, provider)
        self.summarization_thread.summarization_completed.connect(lambda s: self.handle_summary_result(s, mode))
        self.summarization_thread.summarization_failed.connect(lambda e: self.handle_summary_error(e, mode))
        self.summarization_thread.start()

    def handle_summary_result(self, summary, mode):
        if mode == 'ocr':
            self.ocr_tab.progress_bar.setVisible(False)
            self.ocr_tab.summary_text_edit.setText(summary)
            self.ocr_tab.generate_markdown_btn.setEnabled(True)
            self.ocr_tab.tab_widget.setCurrentIndex(1)
            # Auto-generate tags from summary
            self.generate_metadata_from_summary(summary)
            QTimer.singleShot(100, lambda: self.generate_final_markdown('ocr'))
        elif mode == 'pdf':
            self.pdf_tab.progress_bar.setVisible(False)
            self.pdf_tab.summary_text_edit.setText(summary)
            self.pdf_tab.generate_markdown_btn.setEnabled(True)
            self.pdf_tab.tab_widget.setCurrentIndex(1)
            # Auto-generate tags from summary
            self.generate_metadata_from_summary(summary)
            QTimer.singleShot(100, lambda: self.generate_final_markdown('pdf'))
        elif mode == 'web':
            self.web_tab.progress_bar.setVisible(False)
            self.web_tab.summary_text_edit.setText(summary)
            self.web_tab.generate_markdown_btn.setEnabled(True)
            self.web_tab.tab_widget.setCurrentIndex(1)
            self.generate_metadata_from_summary(summary)
            QTimer.singleShot(100, lambda: self.generate_final_markdown('web'))
        else:
            self.text_tab.progress_bar.setVisible(False)
            self.text_tab.summary_text_edit.setText(summary)
            self.text_tab.generate_markdown_btn.setEnabled(True)
            self.text_tab.tab_widget.setCurrentIndex(1)
            # Auto-generate tags from summary
            self.generate_metadata_from_summary(summary)
            QTimer.singleShot(100, lambda: self.generate_final_markdown('text'))
        self.statusBar().showMessage("Summarization completed")

    def handle_summary_error(self, error, mode):
        if mode == 'ocr':
            self.ocr_tab.progress_bar.setVisible(False)
        elif mode == 'pdf':
            self.pdf_tab.progress_bar.setVisible(False)
        elif mode == 'web':
            self.web_tab.progress_bar.setVisible(False)
        else:
            self.text_tab.progress_bar.setVisible(False)
        self.statusBar().showMessage("Summarization failed")
        QMessageBox.warning(self, "Error", f"Summarization failed: {error}")

    def generate_metadata_from_summary(self, summary):
        """Auto-generate tags and notes from summary content"""
        if not summary.strip():
            return

        # Start AI metadata generation thread
        self.ai_metadata_thread = self.AIMetadataGenerator(summary)
        self.ai_metadata_thread.generation_completed.connect(self.handle_metadata_generation_result)
        self.ai_metadata_thread.generation_failed.connect(self.handle_metadata_generation_error)
        self.ai_metadata_thread.start()

    def handle_metadata_generation_result(self, result):
        """Handle AI metadata generation completion"""
        # Get existing tags from metadata panel
        existing_tags_text = self.metadata_panel.tags_input.text().strip()
        if existing_tags_text:
            existing_tags = set(tag.strip().lower() for tag in existing_tags_text.split(',') if tag.strip())
        else:
            existing_tags = set()

        # Get generated tags
        generated_tags = set(result.get("tags", []))

        # Combine: existing tags first, then new generated tags (avoiding duplicates)
        all_tags = sorted(existing_tags) + sorted(generated_tags - existing_tags)

        # Update metadata panel with combined tags
        self.metadata_panel.tags_input.setText(", ".join(all_tags))

        # Update notes (append to existing notes if any)
        generated_notes = result.get("notes", "")
        if generated_notes:
            existing_notes = self.metadata_panel.notes_input.toPlainText().strip()
            if existing_notes:
                # Append AI notes to existing notes
                combined_notes = f"{existing_notes}\n\n{generated_notes}"
                self.metadata_panel.notes_input.setPlainText(combined_notes)
            else:
                # No existing notes, just set the AI-generated ones
                self.metadata_panel.notes_input.setPlainText(generated_notes)

    def handle_metadata_generation_error(self, error):
        """Handle AI metadata generation error silently"""
        # Don't show error to user - metadata generation is optional/automatic
        log.info(f"Metadata generation failed (silent): {error}")

    def generate_final_markdown(self, mode: str):
        """Generate the final markdown output for the specified mode"""
        if mode == 'ocr':
            summary = self.ocr_tab.summary_text_edit.toPlainText()
            md_edit = self.ocr_tab.markdown_edit
            save_btn = self.ocr_tab.save_btn
            tab_widget = self.ocr_tab.tab_widget
        elif mode == 'pdf':
            summary = self.pdf_tab.summary_text_edit.toPlainText()
            md_edit = self.pdf_tab.markdown_edit
            save_btn = self.pdf_tab.save_btn
            tab_widget = self.pdf_tab.tab_widget
        elif mode == 'web':
            summary = self.web_tab.summary_text_edit.toPlainText()
            md_edit = self.web_tab.markdown_edit
            save_btn = self.web_tab.save_btn
            tab_widget = self.web_tab.tab_widget
        else:  # text mode
            summary = self.text_tab.summary_text_edit.toPlainText()
            md_edit = self.text_tab.markdown_edit
            save_btn = self.text_tab.save_btn
            tab_widget = self.text_tab.tab_widget

        if not summary.strip():
            self.statusBar().showMessage("No summary content available for markdown generation")
            return

        # Get metadata from the MetadataPanel (single source of truth)
        title = self.metadata_panel.title_input.text().strip()
        source = self.metadata_panel.original_source.text().strip()
        tags = self.metadata_panel.tags_input.text().strip()

        # Generate markdown
        markdown_content = []

        if title:
            markdown_content.append(f"# {title}")
            markdown_content.append("")

        # Metadata section
        if source or tags:
            markdown_content.append("## Metadata")
            markdown_content.append("")

            if source:
                markdown_content.append(f"**Source:** {source}")

            if tags:
                markdown_content.append(f"**Tags:** {tags}")

            markdown_content.append(f"**Captured:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            markdown_content.append("")

        # Summary content
        if summary:
            markdown_content.append(summary)

        final_markdown = "\n".join(markdown_content)
        md_edit.setText(final_markdown)

        # Enable save button only
        save_btn.setEnabled(True)

        # Switch to the Final Markdown tab (index 2)
        tab_widget.setCurrentIndex(2)

        self.statusBar().showMessage("Markdown generated successfully")

    def safe_stem(self, title: str, metadata: dict) -> str:
        """
        Make a filesystem-safe filename stem and append a short hash for stability.
        Hash prefers a stable document_id; falls back to title+timestamp.
        """
        # Human part
        stem = "".join(ch if ch.isalnum() or ch in "-_ " else "_" for ch in (title or "untitled")).strip()
        stem = "_".join(stem.split())[:80] or "untitled"

        # Stable-ish hash
        base = metadata.get("document_id") or metadata.get("url") or f"{title}-{datetime.now().isoformat()}"
        h = hashlib.sha1(str(base).encode("utf-8", errors="ignore")).hexdigest()[:8]
        return f"{stem}-{h}"

    def write_text(self, path: Path, text: str, gzip_file: bool = False) -> Path:
        """
        Write UTF-8 text to a file. If gzip_file=True, writes <name>.gz using gzip.
        Returns the final Path written.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        if gzip_file:
            path = path.with_suffix(path.suffix + ".gz")
            with gzip.open(path, "wt", encoding="utf-8") as f:
                f.write(text or "")
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text or "")
        return path

    def save_markdown(self, mode):
        # Gather raw, summary markdown, provider/style, and method label
        if mode == 'ocr':
            raw = self.ocr_tab.raw_text_edit.toPlainText()
            content = self.ocr_tab.markdown_edit.toPlainText()
            provider = self.ocr_tab.ai_provider.currentText()
            style = self.ocr_tab.summary_style.currentText()
            method = f"ocr_summary_{style}"
        elif mode == 'pdf':
            raw = self.pdf_tab.raw_text_edit.toPlainText()
            content = self.pdf_tab.markdown_edit.toPlainText()
            provider = self.pdf_tab.ai_provider.currentText()
            style = self.pdf_tab.summary_style.currentText()
            method = f"pdf_summary_{style}"
        elif mode == 'web':
            raw = self.web_tab.raw_text_edit.toPlainText()
            content = self.web_tab.markdown_edit.toPlainText()
            provider = self.web_tab.ai_provider.currentText()
            style = self.web_tab.summary_style.currentText()
            method = f"web_summary_{style}"
        else:
            raw = self.text_tab.input_edit.toPlainText()
            content = self.text_tab.markdown_edit.toPlainText()
            provider = self.text_tab.ai_provider.currentText()
            style = self.text_tab.summary_style.currentText()
            method = f"text_input_summary_{style}"

        if not content:
            return

        # Where to save + metadata
        folder = self.metadata_panel.output_folder.text()
        metadata = self.metadata_panel.get_metadata(mode, method, provider, style)
        self.metadata_panel.log_metadata(metadata)

        # Filename stem (safe + short hash to avoid collisions)
        title = metadata.get("title", "") or ""
        stem = self.safe_stem(title, metadata)

        # Paths
        output_dir = Path(folder)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Keep your existing layout; just compress raw
        raw_path = output_dir / f"{stem}.txt"  # will become .txt.gz
        md_path = output_dir / f"{stem}.md"  # leave markdown uncompressed (nicer for editors)
        json_path = output_dir / f"{stem}.json"

        # Optional: add a timestamp suffix to avoid accidental overwrites across runs with same title
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        if (md_path.exists() or json_path.exists()):
            raw_path = output_dir / f"{stem}__{ts}.txt"
            md_path = output_dir / f"{stem}__{ts}.md"
            json_path = output_dir / f"{stem}__{ts}.json"

        try:
            # RAW as gzipped archive
            written_raw = self.write_text(raw_path, raw, gzip_file=True)

            # Summary markdown (plain .md for easy editing)
            written_md = self.write_text(md_path, content, gzip_file=False)

            # Metadata (augment with hashes + pointers)
            meta_out = dict(metadata)  # shallow copy
            # Hashes help with integrity + provenance
            if raw:
                meta_out["raw_sha256"] = hashlib.sha256(raw.encode("utf-8")).hexdigest()
            if content:
                meta_out["summary_sha256"] = hashlib.sha256(content.encode("utf-8")).hexdigest()
            meta_out["saved_paths"] = {
                "raw": str(written_raw),
                "markdown": str(written_md),
                "metadata": str(json_path),
            }

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(meta_out, f, indent=2, ensure_ascii=False)

            # Persist current metadata defaults as you already do
            self.metadata_panel.save_as_defaults()

            self.statusBar().showMessage(f"Saved: {written_md}")
            QMessageBox.information(self, "Saved",
                                    "Saved bundle:\n"
                                    f"- raw: {written_raw}\n"
                                    f"- markdown: {written_md}\n"
                                    f"- metadata: {json_path}")

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Save failed: {e}")

    def closeEvent(self, event):
        self.save_settings()
        event.accept()
        QApplication.quit()


def main():
    app = QApplication(sys.argv)
    try:
        from PySide6.QtWebEngineCore import QWebEngineSettings
        QWebEngineSettings.globalSettings().setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, False)
    except Exception as e:
        log.info(f"WebEngine warning: {e}")
    try:
        import pytesseract, cv2, PIL
    except ImportError as e:
        QMessageBox.critical(None, "Missing Dependencies",
                             f"Missing: {e}\n\nInstall: pip install pytesseract opencv-python pillow")
        sys.exit(1)
    app.setApplicationName("Knowledge Capture Tool")
    app.setOrganizationName("DataWoven")
    window = KnowledgeCaptureApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
