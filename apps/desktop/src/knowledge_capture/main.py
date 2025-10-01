import sys
import os
from dotenv import load_dotenv
import openai
import anthropic
import google.generativeai as genai
import json
import uuid
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import requests
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

        # Capture all screens for multi-monitor support
        screens = app.screens()
        if len(screens) > 1:
            # Multi-monitor setup - capture virtual desktop
            virtual_geometry = QRect()
            for screen in screens:
                virtual_geometry = virtual_geometry.united(screen.geometry())

            # Create a pixmap that covers all screens
            total_width = virtual_geometry.width()
            total_height = virtual_geometry.height()
            self._full_pix = QPixmap(total_width, total_height)
            self._full_pix.fill(Qt.black)

            painter = QPainter(self._full_pix)
            for screen in screens:
                screen_geometry = screen.geometry()
                screen_pixmap = screen.grabWindow(0)
                # Calculate offset from virtual desktop origin
                offset_x = screen_geometry.x() - virtual_geometry.x()
                offset_y = screen_geometry.y() - virtual_geometry.y()
                painter.drawPixmap(offset_x, offset_y, screen_pixmap)
            painter.end()

            # Position the overlay to cover the virtual desktop
            self.setGeometry(virtual_geometry)
        else:
            # Single monitor - use original approach
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

        # Draw the full screenshot first
        painter.drawPixmap(0, 0, self._full_pix)

        # Then apply semi-transparent overlay everywhere
        overlay_color = QColor(0, 0, 0, 153)  # 60% opacity
        painter.fillRect(self.rect(), overlay_color)

        if not self._rubber.isNull():
            # Clear the overlay in the selection area by drawing the original image again
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            painter.drawPixmap(self._rubber.topLeft(), self._full_pix.copy(self._rubber))

            # Selection border
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

            # Crop the selected area
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
            # Load and preprocess image
            image = cv2.imread(self.image_path)

            if self.preprocess:
                image = self.preprocess_image(image)

            # Convert to PIL Image for tesseract
            pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

            # Try multiple OCR configurations for best results
            configs = [
                r'--oem 3 --psm 6 -c preserve_interword_spaces=1',  # Preserve spaces
                r'--oem 3 --psm 4 -c preserve_interword_spaces=1',  # Single column with spaces
                r'--oem 3 --psm 3',  # Fully automatic page segmentation
                r'--oem 3 --psm 11',  # Sparse text
                r'--oem 3 --psm 6'  # Default fallback
            ]

            best_text = ""
            best_confidence = 0

            for config in configs:
                try:
                    # Get text with confidence data
                    data = pytesseract.image_to_data(pil_image, config=config, output_type=pytesseract.Output.DICT)

                    # Calculate average confidence for words with confidence > 0
                    confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                    avg_confidence = sum(confidences) / len(confidences) if confidences else 0

                    # Get the text
                    text = pytesseract.image_to_string(pil_image, config=config)

                    # Use this result if it has better confidence and reasonable length
                    if avg_confidence > best_confidence and len(text.strip()) > 10:
                        best_confidence = avg_confidence
                        best_text = text

                except Exception:
                    continue

            # Fallback to simple OCR if no good result found
            if not best_text.strip():
                best_text = pytesseract.image_to_string(pil_image, config=r'--oem 3 --psm 6')

            # Post-process the text to fix common issues
            processed_text = self.post_process_text(best_text)

            self.ocr_completed.emit(processed_text)

        except Exception as e:
            self.ocr_failed.emit(str(e))

    def preprocess_image(self, image):
        """Enhanced image preprocessing for better OCR results"""
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Increase image size for better OCR (tesseract works better on larger images)
        height, width = gray.shape
        if height < 300 or width < 300:
            scale_factor = max(2.0, 300 / min(height, width))
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)

        # Noise reduction
        denoised = cv2.fastNlMeansDenoising(gray)

        # Improve contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)

        # Apply slight Gaussian blur to smooth text
        blurred = cv2.GaussianBlur(enhanced, (1, 1), 0)

        # Apply binary threshold - try both methods and pick the best
        # Method 1: Otsu's thresholding
        _, thresh1 = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Method 2: Adaptive threshold
        thresh2 = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

        # Choose the threshold method that produces more white pixels (usually better for text)
        white_pixels_1 = cv2.countNonZero(thresh1)
        white_pixels_2 = cv2.countNonZero(thresh2)

        if white_pixels_1 > white_pixels_2:
            thresh = thresh1
        else:
            thresh = thresh2

        # Morphological operations to clean up the image
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))

        # Remove small noise
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)

        return cleaned

    def post_process_text(self, text: str) -> str:
        """Post-process OCR text to fix common issues"""
        import re

        # First, let's add spaces where they're clearly missing
        # Add space before capital letters that follow lowercase letters
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)

        # Add space between numbers and letters
        text = re.sub(r'(\d)([A-Za-z])', r'\1 \2', text)
        text = re.sub(r'([A-Za-z])(\d)', r'\1 \2', text)

        # Add space after periods followed by capital letters (sentence breaks)
        text = re.sub(r'\.([A-Z])', r'. \1', text)

        # Add space after common word endings before capital letters
        text = re.sub(r'(ing|tion|ness|ment|able|ible)([A-Z])', r'\1 \2', text)

        # Remove excessive whitespace and normalize line breaks
        text = re.sub(r'\n\s*\n', '\n\n', text)  # Multiple newlines to double newline
        text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces/tabs to single space

        # Fix common OCR character mistakes
        replacements = {
            r'[|]': 'I',  # Pipe to I
            r"[`''']": "'",  # Various quotes to standard apostrophe
            r'["""]': '"',  # Various quotes to standard quote
            r'Ã¢â‚¬"': '-',  # Em dash to regular dash
            r'Ã¢â‚¬"': '-',  # En dash to regular dash
            r'Ã¢â‚¬Â¦': '...',  # Ellipsis to three dots
        }

        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text)

        # Fix spacing around punctuation
        text = re.sub(r'\s+([,.!?;:])', r'\1', text)  # Remove space before punctuation
        text = re.sub(r'([,.!?;:])\s*', r'\1 ', text)  # Ensure space after punctuation

        # Clean up the final result
        text = text.strip()

        return text


class MultiProviderSummarizationProcessor(QThread):
    """Background thread for AI summarization using multiple providers"""
    summarization_completed = Signal(str)
    summarization_failed = Signal(str)

    def __init__(self, text: str, summary_style: str = "comprehensive", summary_length: str = "Detailed (100%)",
                 provider: str = "ollama"):
        super().__init__()
        self.text = text
        self.summary_style = summary_style
        self.summary_length = summary_length
        self.provider = provider
        self.ollama_url = "http://localhost:11434/api/generate"

        # Load environment variables
        load_dotenv()

        # API clients
        self.openai_client = None
        self.anthropic_client = None
        self.genai_client = None

        self.setup_api_clients()

    def setup_api_clients(self):
        """Initialize API clients using environment variables"""
        try:
            # OpenAI
            openai_key = os.getenv('OPENAI_API_KEY')
            if openai_key:
                self.openai_client = openai.OpenAI(api_key=openai_key)

            # Anthropic
            anthropic_key = os.getenv('ANTHROPIC_API_KEY')
            if anthropic_key:
                self.anthropic_client = anthropic.Anthropic(api_key=anthropic_key)

            # Google Gemini
            google_key = os.getenv('GOOGLE_API_KEY')
            if google_key:
                genai.configure(api_key=google_key)
                self.genai_client = genai

        except Exception as e:
            print(f"API setup error: {e}")

    def run(self):
        try:
            provider_used = "none"
            summary = ""

            if self.provider == "ollama" and self.is_ollama_available():
                provider_used = "ollama"
                summary = self.llama3_summarize(self.text)
            elif self.provider == "openai" and self.openai_client:
                provider_used = "openai"
                summary = self.openai_summarize(self.text)
            elif self.provider == "claude" and self.anthropic_client:
                provider_used = "claude"
                summary = self.claude_summarize(self.text)
            elif self.provider == "gemini" and self.genai_client:
                provider_used = "gemini"
                summary = self.gemini_summarize(self.text)
            else:
                # Log why we're falling back to extractive
                print(f"Falling back to extractive summarization. Provider: {self.provider}")
                print(f"OpenAI client available: {self.openai_client is not None}")
                print(f"Anthropic client available: {self.anthropic_client is not None}")
                print(f"Gemini client available: {self.genai_client is not None}")
                print(f"Ollama available: {self.is_ollama_available()}")

                provider_used = "extractive"
                summary = self.extractive_summarize(self.text)

            self.summarization_completed.emit(summary)

        except Exception as e:
            print(f"Summarization error with {self.provider}: {str(e)}")
            # Always fallback to extractive on failure
            try:
                summary = self.extractive_summarize(self.text)
                debug_info = f"<!-- Fallback to extractive due to error: {str(e)} -->\n"
                final_summary = debug_info + summary
                self.summarization_completed.emit(final_summary)
            except Exception as fallback_error:
                self.summarization_failed.emit(f"Primary error: {str(e)}, Fallback error: {str(fallback_error)}")

    def get_base_prompt(self) -> str:
        """Get base prompt based on style and length"""
        length_ratios = {"Detailed (100%)": 0.95, "Moderate (75%)": 0.85, "Concise (50%)": 0.70}
        target_ratio = length_ratios.get(self.summary_length, 0.80)

        input_token_estimate = len(self.text.split()) * 1.3
        target_tokens = int(input_token_estimate * target_ratio)

        style_prompts = {
            "comprehensive": f"""Transform the following text into a comprehensive knowledge base entry that preserves all important information while removing only source meta-commentary.

CRITICAL FILTERING - REMOVE ONLY:
- Book/chapter/document references ("this book", "this chapter", "our exploration", "we will cover")
- Author/reader interaction ("we intend", "let's get started", "you will understand") 
- Document navigation ("by the end of this chapter", "in the next section", "as mentioned")
- Visual element references (figures, tables, charts, images)

PRESERVE ALL:
- Technical definitions and explanations
- Examples and use cases
- Advantages and disadvantages
- Implementation details
- Context and background information
- Specific data and statistics
- Comparative information

TRANSFORM APPROACH:
- Convert source references to direct statements about the subject matter
- Maintain the logical flow and organization of information
- Keep all substantive content, examples, and technical details
- Present as authoritative knowledge about the topic

Target length: {target_tokens} tokens (preserving comprehensive detail).

BEGIN IMMEDIATELY with the transformed content:

""",

            "bullet_points": f"""Extract the key information from the text below and present as focused bullet points. Remove all source meta-commentary and focus only on the actual concepts and insights.

CRITICAL FILTERING RULES:
- Remove references to figures, images, charts, tables
- Remove meta-commentary about the source material itself
- Remove document structure references
- Present information as direct knowledge points, not as "the text explains"
- Focus on actionable insights and core concepts only

Target: {target_tokens} tokens maximum with essential information only.

CRITICAL: Begin immediately with bullet points. No introductory text.

Text to process:
""",

            "key_quotes": f"""Extract the most important concepts and insights from the text below, removing all source meta-commentary and structural references.

CRITICAL FILTERING RULES:
- Remove ALL references to the source material itself
- Remove document navigation language
- Remove visual element references
- Present core concepts as direct knowledge statements
- Focus on practical insights and key technical information

Target: {target_tokens} tokens maximum of pure subject matter content.

CRITICAL: Begin immediately with the extracted knowledge. No introductory phrases.

Text to process:
"""
        }

        return style_prompts.get(self.summary_style, style_prompts["comprehensive"])

    def openai_summarize(self, text: str) -> str:
        """Summarize using OpenAI GPT-4"""
        prompt = self.get_base_prompt() + text

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Using a more current and cost-effective model
                messages=[
                    {"role": "system",
                     "content": "You are an expert at creating focused, concise summaries for knowledge bases. Follow the filtering instructions precisely to remove redundant content and visual references."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4000,  # Reduced to encourage more concise output
                temperature=0.2  # Lower temperature for more focused output
            )

            result = response.choices[0].message.content.strip()
            return self.clean_intro_text(result)

        except Exception as e:
            print(f"OpenAI API error: {str(e)}")
            raise e

    def claude_summarize(self, text: str) -> str:
        """Summarize using Claude"""
        prompt = self.get_base_prompt() + text

        response = self.anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=8000,
            temperature=0.3,
            system="You are an expert at creating comprehensive, detailed summaries for knowledge bases. Follow the instructions precisely.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        result = response.content[0].text.strip()
        return self.clean_intro_text(result)

    def gemini_summarize(self, text: str) -> str:
        """Summarize using Gemini"""
        prompt = self.get_base_prompt() + text

        model = self.genai_client.GenerativeModel('gemini-1.5-pro')

        generation_config = genai.types.GenerationConfig(
            max_output_tokens=8000,
            temperature=0.3,
        )

        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )

        result = response.text.strip()
        return self.clean_intro_text(result)

    def clean_intro_text(self, text: str) -> str:
        """Remove introductory phrases and source references from the response"""
        import re

        # Remove introductory phrases
        intro_patterns = [
            r'^Here is a comprehensive summary.*?:',
            r'^Here is a detailed summary.*?:',
            r'^Here is a summary.*?:',
            r'^This summary.*?:',
            r'^The following.*?:',
            r'^Here are.*?:',
            r'^This text.*?:',
            r'^Summary:',
            r'^Based on the text.*?:',
            r'^The text describes.*?:',
            r'^According to the.*?:',
        ]

        for pattern in intro_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE).strip()

        # Remove source meta-commentary patterns (more aggressive matching)
        source_patterns = [
            r'[Tt]his book[^\.]*?\.?\s*',  # "This book covers..." (with optional period)
            r'[Tt]his chapter[^\.]*?\.?\s*',  # "This chapter discusses..."
            r'[Tt]he book[^\.]*?\.?\s*',  # "The book focuses on..."
            r'[Tt]he author[^\.]*?\.?\s*',  # "The author explains..."
            r'[Aa]s this book[^\.]*?\.?\s*',  # "As this book progresses..."
            r'[Ii]n this chapter[^\.]*?\.?\s*',  # "In this chapter, we will..."
            r'[Ww]e will[^\.]*?\.?\s*',  # "We will cover..."
            r'[Ww]e intend[^\.]*?\.?\s*',  # "We intend to give..."
            r'[Oo]ur exploration[^\.]*?\.?\s*',  # "Our exploration of RAG..."
            r'[Tt]he text[^\.]*?\.?\s*',  # "The text explains..."
            r'[Aa]ccording to the text[^\.]*?\.?\s*',  # "According to the text..."
            r'[Tt]he following section[^\.]*?\.?\s*',  # "The following section..."
            r'[Ii]n the next[^\.]*?\.?\s*',  # "In the next section..."
            r'[Aa]s mentioned[^\.]*?\.?\s*',  # "As mentioned earlier..."
            r'[Ll]ater in this[^\.]*?\.?\s*',  # "Later in this book..."
            r'[Tt]he document[^\.]*?\.?\s*',  # "The document states..."
            r'[Tt]his material[^\.]*?\.?\s*',  # "This material covers..."
            r'[Bb]y the end of this chapter[^\.]*?\.?\s*',  # "By the end of this chapter..."
            r'[Ll]et\'s get started[^\.]*?\.?\s*',  # "Let's get started!"
            r'[Ll]et\'s take a closer look[^\.]*?\.?\s*',  # "Let's take a closer look"
            r'[Nn]ow that you understand[^\.]*?\.?\s*',  # "Now that you understand..."
        ]

        # First pass - remove complete sentences with source references
        for pattern in source_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        # Second pass - remove specific embedded phrases (more targeted)
        embedded_patterns = [
            r'\b[Tt]his book focuses on\b[^\.]*',  # "This book focuses on numerous aspects"
            r'\b[Aa]s this book progresses\b[^\.]*',  # "As this book progresses, we will"
            r'\b[Oo]ur exploration of [^\.]*will encourage you\b[^\.]*',  # "Our exploration of RAG will encourage you"
            r'\b[Ii]n this chapter, we will cover\b[^\.]*',  # "In this chapter, we will cover"
            r'\b[Bb]y the end of this chapter\b[^\.]*',  # "By the end of this chapter, you will"
            r'\b[Ww]e intend to give you\b[^\.]*',  # "We intend to give you an in-depth"
            r'\b[Ll]et\'s get started!\s*',  # "Let's get started!"
            r'\b[Ll]et\'s take a closer look:\s*',  # "Let's take a closer look:"
            r'\b[Nn]ow that you understand[^\.]*let\'s\b[^\.]*',  # "Now that you understand...let's"
        ]

        for pattern in embedded_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        # Remove image/figure references and related content
        image_patterns = [
            r'Figure \d+[\.\d]*[^\.\n]*[\.]*[^\n]*\n?',  # Figure references with descriptions
            r'Table \d+[\.\d]*[^\.\n]*[\.]*[^\n]*\n?',  # Table references with descriptions
            r'Chart \d+[\.\d]*[^\.\n]*[\.]*[^\n]*\n?',  # Chart references
            r'Image \d+[\.\d]*[^\.\n]*[\.]*[^\n]*\n?',  # Image references
            r'see Figure \d+[\.\d]*',  # "see Figure X" references
            r'see Table \d+[\.\d]*',  # "see Table X" references
            r'as shown in Figure \d+[\.\d]*',  # "as shown in Figure X"
            r'as shown in Table \d+[\.\d]*',  # "as shown in Table X"
            r'refer to Figure \d+[\.\d]*',  # "refer to Figure X"
            r'refer to Table \d+[\.\d]*',  # "refer to Table X"
            r'based on Figure \d+[\.\d]*',  # "based on Figure X"
            r'based on Table \d+[\.\d]*',  # "based on Table X"
            r'￼[^\n]*\n?',  # Unicode object replacement characters
            r'\[image[^\]]*\]',  # [image...] markers
            r'\[figure[^\]]*\]',  # [figure...] markers
            r'\[chart[^\]]*\]',  # [chart...] markers
            r'Copy\s*Explain\s*',  # "Copy Explain" text from code blocks
        ]

        for pattern in image_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        # Clean up excessive whitespace created by removals
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Multiple newlines to double
        text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces to single
        text = re.sub(r'^\s+', '', text, flags=re.MULTILINE)  # Leading spaces on lines
        text = text.strip()

        return text

    def is_ollama_available(self) -> bool:
        """Check if Ollama is running and has Llama3"""
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                models = response.json().get('models', [])
                return any('llama3' in model.get('name', '').lower() for model in models)
        except:
            pass
        return False

    def llama3_summarize(self, text: str) -> str:
        """Summarize using Llama3 via Ollama"""
        import re

        # Calculate dynamic max_tokens based on input length
        length_ratios = {"Detailed (100%)": 0.80, "Moderate (75%)": 0.60, "Concise (50%)": 0.40}
        target_summary_ratio = length_ratios.get(self.summary_length, 0.80)

        # Calculate dynamic max_tokens based on input length
        input_token_estimate = len(text.split()) * 1.3
        max_tokens = max(1000, min(8000, int(input_token_estimate * target_summary_ratio)))

        prompt = self.get_base_prompt() + text

        payload = {
            "model": "llama3",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "top_p": 0.9,
                "max_tokens": max_tokens,
                "repeat_penalty": 1.1
            }
        }

        response = requests.post(
            self.ollama_url,
            json=payload,
            timeout=60,
            headers={'Content-Type': 'application/json'}
        )

        if response.status_code == 200:
            result = response.json()
            result_text = result.get('response', '').strip()
            return self.clean_intro_text(result_text)
        else:
            raise Exception(f"Ollama request failed: {response.status_code}")

    def extractive_summarize(self, text: str) -> str:
        """Enhanced fallback extractive summarization"""
        # Split into sentences more intelligently
        import re

        # Better sentence splitting that handles various punctuation
        sentences = re.split(r'[.!?]+\s+', text.replace('\n', ' '))
        sentences = [s.strip() for s in sentences if s.strip()]

        # Always try to summarize, even short texts
        if len(sentences) <= 3:
            # For very short texts, just return a condensed version
            words = text.split()
            if len(words) <= 50:
                return text  # Too short to meaningfully summarize
            # For longer single-sentence texts, try to extract key phrases
            return text[:len(text) // 2] + "..."

        # Get the target ratio - use more aggressive ratios for extractive
        length_ratios = {"Detailed (100%)": 0.70, "Moderate (75%)": 0.50, "Concise (50%)": 0.30}
        target_ratio = length_ratios.get(self.summary_length, 0.70)

        # Score sentences by word frequency and position
        word_freq = {}
        words = text.lower().split()

        for word in words:
            if len(word) > 3:
                word_freq[word] = word_freq.get(word, 0) + 1

        sentence_scores = {}
        for i, sentence in enumerate(sentences):
            sentence_words = sentence.lower().split()
            score = sum(word_freq.get(word, 0) for word in sentence_words)

            # Boost important sentences
            if i < 5 or i >= len(sentences) - 5:
                score *= 1.2
            if any(keyword in sentence.lower() for keyword in
                   ['advantage', 'benefit', 'challenge', 'limitation', 'important', 'key', 'critical']):
                score *= 1.3
            if any(keyword in sentence.lower() for keyword in
                   ['hallucination', 'accuracy', 'customization', 'flexibility']):
                score *= 1.5

            sentence_scores[sentence] = score

        # Select sentences based on target ratio
        num_sentences = max(5, int(len(sentences) * target_ratio))
        top_sentences = sorted(sentence_scores.items(), key=lambda x: x[1], reverse=True)[:num_sentences]

        # Rebuild summary maintaining original order
        summary_sentences = []
        for sentence in sentences:
            if any(sentence == top[0] for top in top_sentences):
                summary_sentences.append(sentence)

        return '. '.join(summary_sentences) + '.'


class SharedComponents:
    """Shared UI components and functionality between modes"""

    @staticmethod
    def create_summarization_group():
        """Create the summarization settings group"""
        summary_group = QGroupBox("Summarization")
        summary_layout = QFormLayout(summary_group)

        # Add provider selection
        ai_provider = QComboBox()
        ai_provider.addItems(["openai", "claude", "ollama", "gemini"])
        summary_layout.addRow("AI Provider:", ai_provider)

        summary_style = QComboBox()
        summary_style.addItems(["comprehensive", "bullet_points", "key_quotes"])
        summary_layout.addRow("Style:", summary_style)

        summary_length = QComboBox()
        summary_length.addItems(["Detailed (100%)", "Moderate (75%)", "Concise (50%)"])
        summary_layout.addRow("Length:", summary_length)

        auto_summarize = QCheckBox("Auto-summarize")
        auto_summarize.setChecked(False)
        summary_layout.addRow("", auto_summarize)

        # Add AI status indicator
        ai_status = QLabel("Checking AI providers...")
        summary_layout.addRow("AI Status:", ai_status)

        return summary_group, ai_provider, summary_style, summary_length, auto_summarize, ai_status

    @staticmethod
    def create_metadata_group():
        """Create the metadata input group"""
        metadata_group = QGroupBox("Metadata")
        metadata_layout = QFormLayout(metadata_group)

        title_input = QLineEdit()
        title_input.setPlaceholderText("Optional title...")
        metadata_layout.addRow("Title:", title_input)

        source_input = QLineEdit()
        source_input.setPlaceholderText("Source URL, book, etc...")
        metadata_layout.addRow("Source:", source_input)

        tags_input = QLineEdit()
        tags_input.setPlaceholderText("tag1, tag2, tag3...")
        metadata_layout.addRow("Tags:", tags_input)

        return metadata_group, title_input, source_input, tags_input

    @staticmethod
    def create_output_group():
        """Create the output controls group"""
        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout(output_group)

        output_folder_input = QLineEdit()
        output_folder_input.setText(str(Path.home() / "Documents" / "KnowledgeBase"))

        folder_layout = QHBoxLayout()
        folder_layout.addWidget(output_folder_input)

        browse_btn = QPushButton("Browse")
        browse_btn.setCursor(Qt.PointingHandCursor)
        folder_layout.addWidget(browse_btn)

        output_layout.addLayout(folder_layout)

        save_btn = QPushButton("Save as Markdown")
        save_btn.setEnabled(False)
        output_layout.addWidget(save_btn)

        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.setEnabled(False)
        output_layout.addWidget(copy_btn)

        return output_group, output_folder_input, browse_btn, save_btn, copy_btn


class KnowledgeCaptureApp(QMainWindow):
    """Main application window with dual-mode interface"""

    def __init__(self):
        super().__init__()
        self.settings = QSettings('KnowledgeCapture', 'ScreenshotTool')
        self.current_image_path = None
        self.ocr_thread = None
        self.summarization_thread = None
        self._text_timer = None

        self.init_ui()
        self.setup_shortcuts()
        self.load_settings()
        self.check_ai_status()
        self.ocr_ai_provider.currentTextChanged.connect(self.sync_ai_providers)
        self.text_ai_provider.currentTextChanged.connect(self.sync_ai_providers)

    def sync_ai_providers(self, provider):
        """Sync AI provider selection between modes"""
        # Update both dropdowns when one changes
        self.ocr_ai_provider.blockSignals(True)
        self.text_ai_provider.blockSignals(True)

        self.ocr_ai_provider.setCurrentText(provider)
        self.text_ai_provider.setCurrentText(provider)

        self.ocr_ai_provider.blockSignals(False)
        self.text_ai_provider.blockSignals(False)

    def init_ui(self):
        """Initialize the dual-mode user interface"""
        self.setWindowTitle("Knowledge Capture")
        self.setGeometry(100, 100, 1400, 900)

        self.setStyleSheet("""
                QPushButton {
                    cursor: pointer;
                    padding: 6px 12px;
                    border: 1px solid #555555;
                    border-radius: 4px;
                    background-color: #404040;
                    color: #ffffff;
                }
                QPushButton:hover {
                    cursor: pointer;
                    background-color: #000000;
                    border: none;
                    color: #ffffff;
                }
                QPushButton:pressed {
                    background-color: #222222;
                    border: none;
                }
                QPushButton:disabled {
                    cursor: default;
                    background-color: #2a2a2a;
                    color: #666666;
                    border-color: #333333;
                }
            """)

        # Main mode tabs at the top level
        self.mode_tabs = QTabWidget()
        self.setCentralWidget(self.mode_tabs)

        # OCR Mode
        ocr_widget = self.create_ocr_mode()
        self.mode_tabs.addTab(ocr_widget, "Screenshot OCR")

        # Text Input Mode
        text_widget = self.create_text_mode()
        self.mode_tabs.addTab(text_widget, "Text Input")

        # Status bar
        self.statusBar().showMessage("Ready for knowledge capture")

    def create_ocr_mode(self):
        """Create the OCR mode interface"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
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

        self.preprocess_checkbox = QCheckBox("Preprocess image")
        self.preprocess_checkbox.setChecked(True)
        ocr_layout.addRow("Enhancement:", self.preprocess_checkbox)

        left_layout.addWidget(ocr_group)

        # Shared components
        summary_group, self.ocr_ai_provider, self.ocr_summary_style, self.ocr_summary_length, self.ocr_auto_summarize, self.ocr_ai_status = SharedComponents.create_summarization_group()
        left_layout.addWidget(summary_group)

        metadata_group, self.ocr_title_input, self.ocr_source_input, self.ocr_tags_input = SharedComponents.create_metadata_group()
        left_layout.addWidget(metadata_group)

        output_group, self.ocr_output_folder_input, ocr_browse_btn, self.ocr_save_btn, self.ocr_copy_btn = SharedComponents.create_output_group()
        left_layout.addWidget(output_group)

        # Progress bar
        self.ocr_progress_bar = QProgressBar()
        self.ocr_progress_bar.setVisible(False)
        left_layout.addWidget(self.ocr_progress_bar)

        left_layout.addStretch()
        splitter.addWidget(left_panel)

        # Right panel - OCR text processing
        right_panel = self.create_ocr_text_panel()
        splitter.addWidget(right_panel)

        splitter.setSizes([400, 1000])

        # Connect signals
        ocr_browse_btn.clicked.connect(lambda: self.browse_output_folder(self.ocr_output_folder_input))
        self.ocr_save_btn.clicked.connect(lambda: self.save_markdown('ocr'))
        self.ocr_copy_btn.clicked.connect(lambda: self.copy_to_clipboard('ocr'))

        return widget

    def create_text_mode(self):
        """Create the text input mode interface"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # Left panel - Text mode controls (reduced)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # Text input instructions
        info_group = QGroupBox("Text Input")
        info_layout = QVBoxLayout(info_group)
        info_label = QLabel(
            "Paste or type text content from web pages, documents, or other sources for processing and summarization.")
        info_label.setWordWrap(True)
        info_layout.addWidget(info_label)
        left_layout.addWidget(info_group)

        # Shared components
        summary_group, self.text_ai_provider, self.text_summary_style, self.text_summary_length, self.text_auto_summarize, self.text_ai_status = SharedComponents.create_summarization_group()
        left_layout.addWidget(summary_group)

        metadata_group, self.text_title_input, self.text_source_input, self.text_tags_input = SharedComponents.create_metadata_group()
        left_layout.addWidget(metadata_group)

        output_group, self.text_output_folder_input, text_browse_btn, self.text_save_btn, self.text_copy_btn = SharedComponents.create_output_group()
        left_layout.addWidget(output_group)

        # Progress bar
        self.text_progress_bar = QProgressBar()
        self.text_progress_bar.setVisible(False)
        left_layout.addWidget(self.text_progress_bar)

        left_layout.addStretch()
        splitter.addWidget(left_panel)

        # Right panel - Text input and processing
        right_panel = self.create_text_input_panel()
        splitter.addWidget(right_panel)

        splitter.setSizes([400, 1000])

        # Connect signals
        text_browse_btn.clicked.connect(lambda: self.browse_output_folder(self.text_output_folder_input))
        self.text_save_btn.clicked.connect(lambda: self.save_markdown('text'))
        self.text_copy_btn.clicked.connect(lambda: self.copy_to_clipboard('text'))

        return widget

    def create_ocr_text_panel(self):
        """Create the OCR text processing panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Tab widget for different views
        self.ocr_tab_widget = QTabWidget()
        layout.addWidget(self.ocr_tab_widget)

        # Raw OCR text tab
        self.raw_text_edit = QTextEdit()
        self.raw_text_edit.setPlaceholderText("Raw OCR text will appear here...")
        self.ocr_tab_widget.addTab(self.raw_text_edit, "Raw OCR")

        # Summary tab
        self.ocr_summary_text_edit = QTextEdit()
        self.ocr_summary_text_edit.setPlaceholderText("Summarized content will appear here...")
        self.ocr_tab_widget.addTab(self.ocr_summary_text_edit, "Summary")

        # Final markdown tab
        self.ocr_markdown_edit = QTextEdit()
        self.ocr_markdown_edit.setPlaceholderText("Final markdown content for export...")
        self.ocr_tab_widget.addTab(self.ocr_markdown_edit, "Final Markdown")

        # Processing buttons
        button_layout = QHBoxLayout()

        self.process_ocr_btn = QPushButton("Process OCR")
        self.process_ocr_btn.setCursor(Qt.PointingHandCursor)
        self.process_ocr_btn.clicked.connect(self.process_ocr)
        self.process_ocr_btn.setEnabled(False)
        self.process_ocr_btn.setFixedHeight(40)
        button_layout.addWidget(self.process_ocr_btn)

        self.ocr_summarize_btn = QPushButton("Summarize")
        self.ocr_summarize_btn.setCursor(Qt.PointingHandCursor)
        self.ocr_summarize_btn.clicked.connect(lambda: self.summarize_text('ocr'))
        self.ocr_summarize_btn.setEnabled(False)
        self.ocr_summarize_btn.setFixedHeight(40)
        button_layout.addWidget(self.ocr_summarize_btn)

        self.ocr_generate_markdown_btn = QPushButton("Generate Markdown")
        self.ocr_generate_markdown_btn.setCursor(Qt.PointingHandCursor)
        self.ocr_generate_markdown_btn.clicked.connect(lambda: self.generate_final_markdown('ocr'))
        self.ocr_generate_markdown_btn.setEnabled(False)
        self.ocr_generate_markdown_btn.setFixedHeight(40)
        button_layout.addWidget(self.ocr_generate_markdown_btn)

        layout.addLayout(button_layout)

        return panel

    def create_text_input_panel(self):
        """Create the text input and processing panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Tab widget for different views
        self.text_tab_widget = QTabWidget()
        layout.addWidget(self.text_tab_widget)

        # Raw text input tab
        self.text_input_edit = QTextEdit()
        self.text_input_edit.setPlaceholderText("Paste or type your text content here...")
        self.text_input_edit.textChanged.connect(self.on_text_input_changed)
        self.text_tab_widget.addTab(self.text_input_edit, "Raw Text")

        # Summary tab
        self.text_summary_text_edit = QTextEdit()
        self.text_summary_text_edit.setPlaceholderText("Summarized content will appear here...")
        self.text_tab_widget.addTab(self.text_summary_text_edit, "Summary")

        # Final markdown tab
        self.text_markdown_edit = QTextEdit()
        self.text_markdown_edit.setPlaceholderText("Final markdown content for export...")
        self.text_tab_widget.addTab(self.text_markdown_edit, "Final Markdown")

        # Processing buttons
        button_layout = QHBoxLayout()

        self.text_summarize_btn = QPushButton("Summarize")
        self.text_summarize_btn.setCursor(Qt.PointingHandCursor)
        self.text_summarize_btn.setFixedHeight(40)
        self.text_summarize_btn.clicked.connect(lambda: self.summarize_text('text'))
        self.text_summarize_btn.setEnabled(False)
        button_layout.addWidget(self.text_summarize_btn)

        self.text_generate_markdown_btn = QPushButton("Generate Markdown")
        self.text_generate_markdown_btn.setCursor(Qt.PointingHandCursor)
        self.text_generate_markdown_btn.setFixedHeight(40)
        self.text_generate_markdown_btn.clicked.connect(lambda: self.generate_final_markdown('text'))
        self.text_generate_markdown_btn.setEnabled(False)
        button_layout.addWidget(self.text_generate_markdown_btn)

        layout.addLayout(button_layout)

        return panel

    def on_text_input_changed(self):
        """Handle text input changes"""
        has_text = bool(self.text_input_edit.toPlainText().strip())
        self.text_summarize_btn.setEnabled(has_text)

        # Only auto-summarize if enabled, has content, and not already processing
        if (has_text and
            self.text_auto_summarize.isChecked() and
            (not hasattr(self, 'summarization_thread') or
             self.summarization_thread is None or
             not self.summarization_thread.isRunning())):

            # Cancel any existing timer
            if hasattr(self, '_text_timer') and self._text_timer is not None:
                self._text_timer.stop()

            # Create new timer
            self._text_timer = QTimer()
            self._text_timer.setSingleShot(True)
            self._text_timer.timeout.connect(lambda: self.summarize_text('text'))
            self._text_timer.start(1000)

    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        capture_shortcut = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        capture_shortcut.activated.connect(self.start_screenshot_capture)

    def load_settings(self):
        """Load application settings"""
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

        output_folder = self.settings.value("output_folder", str(Path.home() / "Documents" / "KnowledgeBase"))
        self.ocr_output_folder_input.setText(output_folder)
        self.text_output_folder_input.setText(output_folder)

    def save_settings(self):
        """Save application settings"""
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("output_folder", self.ocr_output_folder_input.text())

    def check_ai_status(self):
        """Check AI provider availability and update UI"""

        def update_status():
            status_messages = []

            # Check Ollama
            try:
                response = requests.get("http://localhost:11434/api/tags", timeout=2)
                if response.status_code == 200:
                    models = response.json().get('models', [])
                    has_llama = any('llama3' in model.get('name', '').lower() for model in models)
                    if has_llama:
                        status_messages.append("Ollama: Available")
                    else:
                        status_messages.append("Ollama: No Llama3")
                else:
                    status_messages.append("Ollama: Not Running")
            except:
                status_messages.append("Ollama: Unavailable")

            # Check API keys
            load_dotenv()

            openai_key = os.getenv('OPENAI_API_KEY')
            if openai_key:
                status_messages.append("OpenAI: Ready")
                print(f"OpenAI API key found: {openai_key[:8]}...")
            else:
                status_messages.append("OpenAI: No Key")
                print("OpenAI API key not found")

            anthropic_key = os.getenv('ANTHROPIC_API_KEY')
            if anthropic_key:
                status_messages.append("Claude: Ready")
                print(f"Anthropic API key found: {anthropic_key[:8]}...")
            else:
                status_messages.append("Claude: No Key")
                print("Anthropic API key not found")

            google_key = os.getenv('GOOGLE_API_KEY')
            if google_key:
                status_messages.append("Gemini: Ready")
                print(f"Google API key found: {google_key[:8]}...")
            else:
                status_messages.append("Gemini: No Key")
                print("Google API key not found")

            status_text = " | ".join(status_messages)

            # Update both mode status labels
            self.ocr_ai_status.setText(status_text)
            self.text_ai_status.setText(status_text)

        # Run in a separate thread to avoid blocking UI
        QTimer.singleShot(100, update_status)

    # OCR Mode Methods
    def start_screenshot_capture(self):
        """Start the screenshot capture process"""
        self.capture_overlay = ScreenshotCapture()
        self.capture_overlay.screenshot_taken.connect(self.handle_screenshot)
        self.capture_overlay.show()

    def handle_screenshot(self, pixmap: QPixmap):
        """Handle captured screenshot"""
        # Save screenshot to temp file
        temp_dir = tempfile.gettempdir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_image_path = os.path.join(temp_dir, f"screenshot_{timestamp}.png")

        pixmap.save(self.current_image_path)
        self.statusBar().showMessage(f"Screenshot captured: {self.current_image_path}")

        # Enable processing button
        self.process_ocr_btn.setEnabled(True)

        # Auto-process if enabled
        if self.ocr_auto_summarize.isChecked():
            self.process_ocr()

    def capture_fullscreen(self):
        """Capture full screen using the enhanced system"""
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

        self.ocr_progress_bar.setVisible(True)
        self.ocr_progress_bar.setRange(0, 0)  # Indeterminate
        self.statusBar().showMessage("Processing OCR...")

        # Start OCR thread
        self.ocr_thread = OCRProcessor(
            self.current_image_path,
            self.preprocess_checkbox.isChecked()
        )
        self.ocr_thread.ocr_completed.connect(self.handle_ocr_result)
        self.ocr_thread.ocr_failed.connect(self.handle_ocr_error)
        self.ocr_thread.start()

    def handle_ocr_result(self, text: str):
        """Handle OCR completion"""
        self.ocr_progress_bar.setVisible(False)
        self.raw_text_edit.setText(text)
        self.statusBar().showMessage("OCR completed successfully")

        self.ocr_summarize_btn.setEnabled(True)

        # Auto-summarize if enabled
        if self.ocr_auto_summarize.isChecked():
            self.summarize_text('ocr')

    def handle_ocr_error(self, error: str):
        """Handle OCR error"""
        self.ocr_progress_bar.setVisible(False)
        self.statusBar().showMessage("OCR failed")
        QMessageBox.warning(self, "OCR Error", f"OCR processing failed: {error}")

    def reset_fields(self, mode: str):
        """Reset all fields and content for the specified mode"""
        if mode == 'ocr':
            # Clear text areas
            self.raw_text_edit.clear()
            self.ocr_summary_text_edit.clear()
            self.ocr_markdown_edit.clear()

            # Clear metadata fields
            self.ocr_title_input.clear()
            self.ocr_source_input.clear()
            self.ocr_tags_input.clear()

            # Reset buttons
            self.process_ocr_btn.setEnabled(False)
            self.ocr_summarize_btn.setEnabled(False)
            self.ocr_generate_markdown_btn.setEnabled(False)
            self.ocr_save_btn.setEnabled(False)
            self.ocr_copy_btn.setEnabled(False)

            # Switch back to first tab
            self.ocr_tab_widget.setCurrentIndex(0)

            # Clear current image path
            self.current_image_path = None

        else:  # text mode
            # Clear text areas
            self.text_input_edit.clear()
            self.text_summary_text_edit.clear()
            self.text_markdown_edit.clear()

            # Clear metadata fields
            self.text_title_input.clear()
            self.text_source_input.clear()
            self.text_tags_input.clear()

            # Reset buttons
            self.text_summarize_btn.setEnabled(False)
            self.text_generate_markdown_btn.setEnabled(False)
            self.text_save_btn.setEnabled(False)
            self.text_copy_btn.setEnabled(False)

            # Switch back to first tab
            self.text_tab_widget.setCurrentIndex(0)

        self.statusBar().showMessage(f"{mode.upper()} mode reset - ready for new content")

    # Shared Processing Methods
    def summarize_text(self, mode: str):
        """Summarize text for the specified mode"""
        # Get the appropriate text source and settings
        if mode == 'ocr':
            text = self.raw_text_edit.toPlainText()
            provider = self.ocr_ai_provider.currentText()
            style = self.ocr_summary_style.currentText()
            length = self.ocr_summary_length.currentText()
            progress_bar = self.ocr_progress_bar
        else:  # text mode
            text = self.text_input_edit.toPlainText()
            provider = self.text_ai_provider.currentText()
            style = self.text_summary_style.currentText()
            length = self.text_summary_length.currentText()
            progress_bar = self.text_progress_bar

        if not text.strip():
            return

        progress_bar.setVisible(True)
        progress_bar.setRange(0, 0)
        self.statusBar().showMessage(f"Generating summary using {provider}...")

        # Start summarization thread with provider selection
        self.summarization_thread = MultiProviderSummarizationProcessor(text, style, length, provider)
        self.summarization_thread.summarization_completed.connect(
            lambda summary: self.handle_summary_result(summary, mode)
        )
        self.summarization_thread.summarization_failed.connect(
            lambda error: self.handle_summary_error(error, mode)
        )
        self.summarization_thread.start()

    def handle_summary_result(self, summary: str, mode: str):
        """Handle summarization completion"""
        if mode == 'ocr':
            self.ocr_progress_bar.setVisible(False)
            self.ocr_summary_text_edit.setText(summary)
            self.ocr_generate_markdown_btn.setEnabled(True)
            # Switch to summary tab to show results
            self.ocr_tab_widget.setCurrentIndex(1)
            # Auto-generate markdown after a brief delay to ensure UI updates
            QTimer.singleShot(100, lambda: self.generate_final_markdown('ocr'))
        else:  # text mode
            self.text_progress_bar.setVisible(False)
            self.text_summary_text_edit.setText(summary)
            self.text_generate_markdown_btn.setEnabled(True)
            # Switch to summary tab to show results
            self.text_tab_widget.setCurrentIndex(1)
            # Auto-generate markdown after a brief delay to ensure UI updates
            QTimer.singleShot(100, lambda: self.generate_final_markdown('text'))

        self.statusBar().showMessage("Summarization completed")

    def handle_summary_error(self, error: str, mode: str):
        """Handle summarization error"""
        if mode == 'ocr':
            self.ocr_progress_bar.setVisible(False)
        else:
            self.text_progress_bar.setVisible(False)

        self.statusBar().showMessage("Summarization failed")
        QMessageBox.warning(self, "Summarization Error", f"Summarization failed: {error}")

    def generate_final_markdown(self, mode: str):
        """Generate the final markdown output for the specified mode"""
        # Get content based on mode
        if mode == 'ocr':
            summary = self.ocr_summary_text_edit.toPlainText()
            title = self.ocr_title_input.text().strip()
            source = self.ocr_source_input.text().strip()
            tags = self.ocr_tags_input.text().strip()
            markdown_edit = self.ocr_markdown_edit
            save_btn = self.ocr_save_btn
            copy_btn = self.ocr_copy_btn
            tab_widget = self.ocr_tab_widget
        else:  # text mode
            summary = self.text_summary_text_edit.toPlainText()
            title = self.text_title_input.text().strip()
            source = self.text_source_input.text().strip()
            tags = self.text_tags_input.text().strip()
            markdown_edit = self.text_markdown_edit
            save_btn = self.text_save_btn
            copy_btn = self.text_copy_btn
            tab_widget = self.text_tab_widget

        if not summary.strip():
            self.statusBar().showMessage("No summary content available for markdown generation")
            return

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
        markdown_edit.setText(final_markdown)

        # Enable export buttons
        save_btn.setEnabled(True)
        copy_btn.setEnabled(True)

        # Switch to the Final Markdown tab (index 2)
        tab_widget.setCurrentIndex(2)

        self.statusBar().showMessage("Markdown generated successfully")

    # File Operations
    def browse_output_folder(self, folder_input: QLineEdit):
        """Browse for output folder"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Output Folder",
            folder_input.text()
        )
        if folder:
            folder_input.setText(folder)
            # Sync both folder inputs
            self.ocr_output_folder_input.setText(folder)
            self.text_output_folder_input.setText(folder)

    def save_markdown(self, mode: str):
        """Save the markdown content to file"""
        if mode == 'ocr':
            content = self.ocr_markdown_edit.toPlainText()
            title = self.ocr_title_input.text().strip()
            output_folder = self.ocr_output_folder_input.text()
        else:  # text mode
            content = self.text_markdown_edit.toPlainText()
            title = self.text_title_input.text().strip()
            output_folder = self.text_output_folder_input.text()

        if not content:
            return

        # Generate filename
        if title:
            # Sanitize title for filename
            filename = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            filename = filename.replace(' ', '_') + '.md'
        else:
            # Random filename
            filename = f"capture_{uuid.uuid4().hex[:8]}.md"

        # Get output directory
        output_dir = Path(output_folder)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save file
        output_path = output_dir / filename
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)

            self.statusBar().showMessage(f"Saved: {output_path}")
            QMessageBox.information(self, "Saved", f"Content saved to:\n{output_path}")

        except Exception as e:
            QMessageBox.warning(self, "Save Error", f"Failed to save file: {e}")

    def copy_to_clipboard(self, mode: str):
        """Copy markdown content to clipboard"""
        if mode == 'ocr':
            content = self.ocr_markdown_edit.toPlainText()
        else:  # text mode
            content = self.text_markdown_edit.toPlainText()

        if content:
            clipboard = QApplication.clipboard()
            clipboard.setText(content)
            self.statusBar().showMessage("Content copied to clipboard")

    def closeEvent(self, event):
        """Handle application close"""
        self.save_settings()
        event.accept()
        QApplication.quit()


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)

    # Check for required dependencies
    try:
        import pytesseract
        import cv2
        import PIL
    except ImportError as e:
        QMessageBox.critical(
            None,
            "Missing Dependencies",
            f"Required dependency missing: {e}\n\n"
            "Please install: pip install pytesseract opencv-python pillow"
        )
        sys.exit(1)

    # Set application properties
    app.setApplicationName("Knowledge Capture Tool")
    app.setOrganizationName("DataWoven")

    # Create and show main window
    window = KnowledgeCaptureApp()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
