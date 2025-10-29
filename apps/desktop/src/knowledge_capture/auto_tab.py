# auto_tab.py
"""
Auto Mode Tab - Batch processing and automation
Contains three sub-tabs: Assignment Builder, Queue, and Cost Analytics
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel,
    QSplitter, QGroupBox, QPushButton, QTreeWidget, QTreeWidgetItem,
    QComboBox, QLineEdit, QCheckBox, QSpinBox, QTextEdit, QFormLayout,
    QFileDialog, QMessageBox, QDialog, QDialogButtonBox, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QIcon
from pathlib import Path
from datetime import datetime
import json
import uuid


class QueueProcessorThread(QThread):
    """Background thread for processing queue assignments"""
    log_signal = Signal(str)
    progress_signal = Signal(int, int)  # current, total
    finished_signal = Signal()
    cost_update_signal = Signal(dict)  # Real-time cost updates
    paused = False

    def __init__(self, assignments, assignment_data, output_folder, database_path=None):
        super().__init__()
        self.assignments = assignments
        self.assignment_data = assignment_data
        self.output_folder = output_folder

        # Initialize cost tracker with custom database path
        from cost_tracker import CostTracker
        self.cost_tracker = CostTracker(db_path=database_path)
        self.current_batch_id = None

    def run(self):
        """Execute all assignments in background thread"""
        self.log_signal.emit("=" * 60)
        self.log_signal.emit("STARTING QUEUE PROCESSING")
        self.log_signal.emit("=" * 60)

        # Start batch tracking
        batch_name = f"Queue Run {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        assignment_type = "Mixed" if len(self.assignments) > 1 else self.assignment_data.get(0, {}).get("type",
                                                                                                        "Unknown")
        self.current_batch_id = self.cost_tracker.start_batch(
            batch_name=batch_name,
            assignment_type=assignment_type,
            items_total=len(self.assignments)
        )

        self.log_signal.emit(f"Batch ID: {self.current_batch_id}")
        self.log_signal.emit("")

        # Process each assignment
        for i in range(len(self.assignments)):
            if i not in self.assignment_data:
                continue

            assignment = self.assignment_data[i]
            assignment_name = assignment.get("name", f"Assignment {i + 1}")
            assignment_type = assignment.get("type", "")

            self.log_signal.emit(f"\n▶ Processing: {assignment_name}")
            self.log_signal.emit(f"  Type: {assignment_type}")

            # Process based on type
            if assignment_type == "Folder of Files - OCR":
                self.process_ocr_assignment(assignment, self.output_folder)
            elif assignment_type == "Folder of Files - Text":
                self.process_text_assignment(assignment, self.output_folder)
            elif assignment_type == "Folder of Files - PDF":
                self.process_pdf_assignment(assignment, self.output_folder)
            else:
                self.log_signal.emit(f"  ⚠ Type not yet implemented: {assignment_type}")

            # Update progress
            self.cost_tracker.update_batch(
                self.current_batch_id,
                items_processed=i + 1
            )

            # Emit current cost stats
            stats = self.cost_tracker.get_total_stats()
            self.cost_update_signal.emit(stats)

        # Complete batch
        self.cost_tracker.complete_batch(self.current_batch_id, status='completed')

        self.log_signal.emit("\n" + "=" * 60)
        self.log_signal.emit("QUEUE PROCESSING COMPLETE")

        # Get final stats
        final_stats = self.cost_tracker.get_total_stats()
        self.log_signal.emit(f"Total Tokens Used: {final_stats.get('total_tokens', 0):,}")
        self.log_signal.emit(f"Estimated Cost: ${final_stats.get('total_cost', 0):.4f}")
        self.log_signal.emit("=" * 60)

        self.finished_signal.emit()

    def process_ocr_assignment(self, assignment, base_output_folder):
        """Process OCR assignment - same logic as before but with signals"""
        source_folder = assignment.get("source_folder", "")
        file_pattern = assignment.get("file_pattern", "*.png, *.jpg, *.jpeg")
        preprocess = assignment.get("preprocess", True)
        enable_summarization = assignment.get("enable_summarization", True)

        if not source_folder or not Path(source_folder).exists():
            self.log_signal.emit(f"  ✗ Source folder not found: {source_folder}")
            return

        # Create OCR subfolder
        ocr_output = Path(base_output_folder) / "ocr"
        ocr_output.mkdir(exist_ok=True)

        self.log_signal.emit(f"  Source: {source_folder}")
        self.log_signal.emit(f"  Output: {ocr_output}")

        source = Path(source_folder)
        patterns = [p.strip() for p in file_pattern.split(',')]

        # Separate subdirectories and root-level files
        all_items = list(source.iterdir())
        subdirectories = [d for d in all_items if d.is_dir()]

        root_files = []
        for pattern in patterns:
            matches = [f for f in source.glob(pattern) if f.is_file() and f.parent == source]
            root_files.extend(matches)

        root_files = sorted(root_files, key=lambda x: x.name.lower())
        subdirectories = sorted(subdirectories, key=lambda x: x.name.lower())

        total_items = len(subdirectories) + len(root_files)

        if total_items == 0:
            self.log_signal.emit(f"  ⚠ No matching files or folders found")
            return

        self.log_signal.emit(f"  Found {len(subdirectories)} subdirectories and {len(root_files)} root files\n")

        current_item = 0

        # Process subdirectories first
        for subdir in subdirectories:
            current_item += 1
            self.log_signal.emit(f"  [{current_item}/{total_items}] Processing subdirectory: {subdir.name}")

            try:
                self.process_subdirectory(subdir, patterns, ocr_output, preprocess, enable_summarization, assignment)
            except Exception as e:
                self.log_signal.emit(f"    ✗ Error processing subdirectory: {e}\n")

        # Process root-level files
        for idx, file_path in enumerate(root_files, current_item + 1):
            self.log_signal.emit(f"  [{idx}/{total_items}] Processing: {file_path.name}")

            try:
                self.process_single_file(file_path, source, ocr_output, preprocess, enable_summarization, assignment)
            except Exception as e:
                self.log_signal.emit(f"    ✗ Error: {e}\n")

        self.log_signal.emit(f"\n  ✓ Completed: {total_items} items processed")

    def process_subdirectory(self, subdir, patterns, ocr_output, preprocess, enable_summarization, assignment):
        """Process subdirectory in thread"""
        # Collect files
        files = []
        for pattern in patterns:
            files.extend(subdir.glob(pattern))

        files = sorted(files, key=lambda x: x.name.lower())

        if not files:
            self.log_signal.emit(f"    ⚠ No matching files in subdirectory")
            return

        self.log_signal.emit(f"    Found {len(files)} files in subdirectory")

        # Process each file and collect OCR text
        all_ocr_text = []

        for file_idx, file_path in enumerate(files, 1):
            self.log_signal.emit(f"      [{file_idx}/{len(files)}] OCR: {file_path.name}")

            ocr_text = self.run_ocr_sync(file_path, preprocess)

            if ocr_text:
                all_ocr_text.append(f"--- {file_path.name} ---\n{ocr_text}")
                self.log_signal.emit(f"        ✓ {len(ocr_text)} chars")
            else:
                self.log_signal.emit(f"        ✗ No text extracted")

        if not all_ocr_text:
            self.log_signal.emit(f"    ✗ No text extracted from any files")
            return

        # Combine all OCR text
        combined_ocr = "\n\n".join(all_ocr_text)
        self.log_signal.emit(f"    ✓ Combined OCR: {len(combined_ocr)} chars total")

        # Load folder metadata
        folder_name = subdir.name
        metadata_file = subdir.parent / f"{folder_name}_metadata.json"
        user_metadata = {}

        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    user_metadata = json.load(f)
                self.log_signal.emit(f"    ✓ Loaded folder metadata")
            except:
                pass

        # Run summarization
        summary = combined_ocr
        ai_tags = ""
        ai_notes = ""
        input_tokens = 0
        output_tokens = 0

        if enable_summarization:
            self.log_signal.emit(f"    ► Summarizing combined content...")
            provider = assignment.get("ai_provider", "OpenAI")
            summary, ai_tags, ai_notes, input_tokens, output_tokens = self.run_summarization_sync(combined_ocr,
                                                                                                  provider)
            self.log_signal.emit(f"    ✓ Summarization complete (tokens: {input_tokens + output_tokens})")

            # Track this folder's cost
            if self.current_batch_id:
                self.cost_tracker.add_item(
                    batch_id=self.current_batch_id,
                    item_name=folder_name,
                    item_type="folder",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens
                )

                # Update batch totals
                self.cost_tracker.update_batch(
                    self.current_batch_id,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens
                )

        # Merge metadata
        merged_metadata = self.merge_metadata(user_metadata, ai_tags, ai_notes)

        # Build metadata
        metadata = self.build_metadata(subdir, merged_metadata, summary, combined_ocr)
        metadata["source_type"] = "ocr_folder"
        metadata["file_count"] = len(files)
        metadata["files"] = [f.name for f in files]

        # Generate markdown
        markdown_content = self.generate_markdown_content(
            title=merged_metadata.get("title", folder_name),
            source=merged_metadata.get("original_source", ""),
            tags=merged_metadata.get("tags", ""),
            content=summary
        )

        # Save files
        output_txt = ocr_output / f"{folder_name}.txt.gz"
        output_md = ocr_output / f"{folder_name}.md"
        output_json = ocr_output / f"{folder_name}.json"

        import gzip
        with gzip.open(output_txt, 'wt', encoding='utf-8') as f:
            f.write(combined_ocr)

        with open(output_md, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)

        self.log_signal.emit(f"    ✓ Saved: {folder_name}.txt.gz + {folder_name}.md + {folder_name}.json\n")

    def process_single_file(self, file_path, source_folder, ocr_output, preprocess, enable_summarization, assignment):
        """Process single file in thread"""
        # Run OCR
        ocr_text = self.run_ocr_sync(file_path, preprocess)

        if not ocr_text:
            self.log_signal.emit(f"    ✗ OCR failed - no text extracted")
            return

        self.log_signal.emit(f"    ✓ OCR complete ({len(ocr_text)} chars)")

        # Load user metadata
        stem = file_path.stem
        metadata_file = source_folder / f"{stem}_metadata.json"
        user_metadata = {}

        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    user_metadata = json.load(f)
                self.log_signal.emit(f"    ✓ Loaded user metadata")
            except:
                pass

        # Run summarization
        summary = ocr_text
        ai_tags = ""
        ai_notes = ""
        input_tokens = 0
        output_tokens = 0

        if enable_summarization:
            self.log_signal.emit(f"    ► Summarizing...")
            provider = assignment.get("ai_provider", "OpenAI")
            summary, ai_tags, ai_notes, input_tokens, output_tokens = self.run_summarization_sync(ocr_text, provider)
            self.log_signal.emit(f"    ✓ Summarization complete (tokens: {input_tokens + output_tokens})")

            # Track this item's cost
            if self.current_batch_id:
                self.cost_tracker.add_item(
                    batch_id=self.current_batch_id,
                    item_name=file_path.name,
                    item_type="file",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens
                )

                # Update batch totals
                self.cost_tracker.update_batch(
                    self.current_batch_id,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens
                )

        # Merge metadata
        merged_metadata = self.merge_metadata(user_metadata, ai_tags, ai_notes)

        # Build metadata
        metadata = self.build_metadata(file_path, merged_metadata, summary, ocr_text)

        # Generate markdown
        markdown_content = self.generate_markdown_content(
            title=metadata.get("title", stem),
            source=metadata.get("original_source", ""),
            tags=metadata.get("tags", ""),
            content=summary
        )

        # Save files
        output_txt = ocr_output / f"{stem}.txt.gz"
        output_md = ocr_output / f"{stem}.md"
        output_json = ocr_output / f"{stem}.json"

        import gzip
        with gzip.open(output_txt, 'wt', encoding='utf-8') as f:
            f.write(ocr_text)

        with open(output_md, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)

        self.log_signal.emit(f"    ✓ Saved: {stem}.txt.gz + {stem}.md + {stem}.json\n")

    def run_ocr_sync(self, image_path, preprocess):
        """Run OCR"""
        import cv2
        import pytesseract

        try:
            img = cv2.imread(str(image_path))

            if preprocess:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                gray = cv2.fastNlMeansDenoising(gray, h=10)

                configs = [
                    '--oem 3 --psm 3',
                    '--oem 3 --psm 6',
                    '--oem 3 --psm 4',
                ]

                best_text = ""
                for config in configs:
                    text = pytesseract.image_to_string(gray, config=config)
                    if len(text.strip()) > len(best_text.strip()):
                        best_text = text

                return best_text.strip()
            else:
                return pytesseract.image_to_string(img).strip()

        except Exception as e:
            self.log_signal.emit(f"    ✗ OCR Error: {e}")
            return ""

    def run_summarization_sync(self, text, provider="OpenAI"):
        """Run AI summarization with specified provider and return tokens used"""
        import os

        try:
            word_count = len(text.split())
            if word_count < 500:
                length_instruction = "a concise summary (2-3 paragraphs)"
            elif word_count < 2000:
                length_instruction = "a comprehensive summary (4-6 paragraphs covering all major points)"
            else:
                length_instruction = "a detailed summary (6-8 paragraphs covering all major sections and key details)"

            prompt = f"""Please analyze this text thoroughly and provide:
1. {length_instruction} - Cover ALL major topics and sections in the text, not just the first or last section
2. Relevant tags (comma-separated keywords covering ALL topics discussed)
3. Brief notes about the content structure and key takeaways

Text to analyze:
{text}

Format your response as:
SUMMARY:
[your summary here - make sure to cover ALL major topics and sections in the text]

TAGS:
[tag1, tag2, tag3, etc.]

NOTES:
[your notes here]"""

            if provider == "OpenAI":
                import openai
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    self.log_signal.emit(f"    ⚠ No OpenAI API key - skipping summarization")
                    return text, "", "", 0, 0

                client = openai.OpenAI(api_key=api_key)
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=2048
                )
                response_text = response.choices[0].message.content
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens

            elif provider == "Claude":
                import anthropic
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    self.log_signal.emit(f"    ⚠ No Anthropic API key - skipping summarization")
                    return text, "", "", 0, 0

                client = anthropic.Anthropic(api_key=api_key)
                message = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=2048,
                    messages=[{"role": "user", "content": prompt}]
                )
                response_text = message.content[0].text
                input_tokens = message.usage.input_tokens
                output_tokens = message.usage.output_tokens

            elif provider == "Gemini":
                import google.generativeai as genai
                api_key = os.getenv("GEMINI_API_KEY")
                if not api_key:
                    self.log_signal.emit(f"    ⚠ No Gemini API key - skipping summarization")
                    return text, "", "", 0, 0

                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-pro')
                response = model.generate_content(prompt)
                response_text = response.text
                input_tokens = response.usage_metadata.prompt_token_count
                output_tokens = response.usage_metadata.candidates_token_count

            else:
                self.log_signal.emit(f"    ⚠ Unknown provider: {provider}")
                return text, "", "", 0, 0

            # Parse response
            summary = ""
            tags = ""
            notes = ""

            if "SUMMARY:" in response_text:
                parts = response_text.split("TAGS:")
                summary = parts[0].replace("SUMMARY:", "").strip()

                if len(parts) > 1:
                    tags_notes = parts[1].split("NOTES:")
                    tags = tags_notes[0].strip()

                    if len(tags_notes) > 1:
                        notes = tags_notes[1].strip()
            else:
                summary = response_text

            return summary, tags, notes, input_tokens, output_tokens

        except Exception as e:
            self.log_signal.emit(f"    ⚠ Summarization error: {e}")
            return text, "", "", 0, 0

    def merge_metadata(self, user_metadata, ai_tags, ai_notes):
        """Merge user and AI metadata"""
        merged = user_metadata.copy()

        user_tags = user_metadata.get("tags", "").strip()
        if user_tags and ai_tags:
            merged["tags"] = f"{user_tags}, {ai_tags}"
        elif ai_tags:
            merged["tags"] = ai_tags
        elif user_tags:
            merged["tags"] = user_tags
        else:
            merged["tags"] = ""

        user_notes = user_metadata.get("notes", "").strip()
        if user_notes and ai_notes:
            if not user_notes.endswith('.'):
                user_notes += '.'
            merged["notes"] = f"{user_notes} {ai_notes}"
        elif ai_notes:
            merged["notes"] = ai_notes
        elif user_notes:
            merged["notes"] = user_notes
        else:
            merged["notes"] = ""

        return merged

    def build_metadata(self, file_path, merged_metadata, summary, raw_text):
        """Build metadata dictionary"""
        metadata = {
            "document_id": str(uuid.uuid4()),
            "title": merged_metadata.get("title", file_path.stem if hasattr(file_path, 'stem') else file_path.name),
            "original_source": merged_metadata.get("original_source", ""),
            "author": merged_metadata.get("author", ""),
            "page_numbers": merged_metadata.get("page_numbers", ""),
            "priority": merged_metadata.get("priority", "medium"),
            "ready_for_pipeline": merged_metadata.get("ready_for_pipeline", False),
            "tags": merged_metadata.get("tags", ""),
            "notes": merged_metadata.get("notes", ""),
            "source_type": "ocr",
            "source_file": str(file_path),
            "captured_date": datetime.now().isoformat(),
            "word_count_summary": len(summary.split()),
            "word_count_raw": len(raw_text.split()),
            "char_count_raw": len(raw_text)
        }

        return metadata

    def generate_markdown_content(self, title, source, tags, content):
        """Generate markdown"""
        lines = []

        if title:
            lines.append(f"# {title}")
            lines.append("")

        if source or tags:
            lines.append("## Metadata")
            lines.append("")

            if source:
                lines.append(f"**Source:** {source}")

            if tags:
                lines.append(f"**Tags:** {tags}")

            lines.append(f"**Captured:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append("")

        if content:
            lines.append(content)

        return "\n".join(lines)

    def process_pdf_assignment(self, assignment, base_output_folder):
        """Process PDF assignment - handles subdirectories like OCR/Text"""
        import fitz

        source_folder = assignment.get("source_folder", "")
        file_pattern = assignment.get("file_pattern", "*.pdf")
        detect_chapters = assignment.get("detect_chapters", False)
        use_ocr = assignment.get("use_ocr", False)
        enable_summarization = assignment.get("enable_summarization", True)

        if not Path(source_folder).exists():
            self.log_signal.emit(f"  ✗ Source folder not found: {source_folder}")
            return

        output_dir = Path(base_output_folder) / "pdf"
        output_dir.mkdir(exist_ok=True)

        self.log_signal.emit(f"  Source: {source_folder}")
        self.log_signal.emit(f"  Output: {output_dir}")

        source = Path(source_folder)
        patterns = [p.strip() for p in file_pattern.split(',')]

        subdirectories = [d for d in source.iterdir() if d.is_dir()]
        root_files = []
        for pattern in patterns:
            matches = [f for f in source.glob(pattern) if f.is_file() and f.parent == source]
            root_files.extend(matches)

        root_files = sorted(root_files, key=lambda x: x.name.lower())
        subdirectories = sorted(subdirectories, key=lambda x: x.name.lower())

        total_items = len(subdirectories) + len(root_files)

        if total_items == 0:
            self.log_signal.emit("  ⚠ No matching files or folders found")
            return

        self.log_signal.emit(f"  Found {len(subdirectories)} subdirectories and {len(root_files)} root files\n")

        current_item = 0

        for subdir in subdirectories:
            current_item += 1
            self.log_signal.emit(f"  [{current_item}/{total_items}] Processing subdirectory: {subdir.name}")
            try:
                self.process_pdf_subdirectory(subdir, patterns, output_dir, detect_chapters, use_ocr,
                                              enable_summarization, assignment)
            except Exception as e:
                self.log_signal.emit(f"    ✗ Error: {e}\n")

        for idx, file_path in enumerate(root_files, current_item + 1):
            self.log_signal.emit(f"  [{idx}/{total_items}] Processing: {file_path.name}")
            try:
                self.process_single_pdf_file(file_path, source, output_dir, detect_chapters, use_ocr,
                                             enable_summarization, assignment)
            except Exception as e:
                self.log_signal.emit(f"    ✗ Error: {e}\n")

        self.log_signal.emit(f"\n  ✓ Completed: {total_items} items processed")

    def process_pdf_subdirectory(self, subdir, patterns, output_dir, detect_chapters, use_ocr, enable_summarization,
                                 assignment):
        """Process PDF subdirectory - combine all PDFs"""
        import fitz

        files = []
        for pattern in patterns:
            files.extend(subdir.glob(pattern))

        files = sorted([f for f in files if f.is_file()], key=lambda x: x.name.lower())

        if not files:
            self.log_signal.emit(f"    ⚠ No matching files in subdirectory")
            return

        self.log_signal.emit(f"    Found {len(files)} files in subdirectory")

        all_text = []

        for file_idx, file_path in enumerate(files, 1):
            self.log_signal.emit(f"      [{file_idx}/{len(files)}] Extracting: {file_path.name}")
            text = self._extract_pdf_text(file_path, detect_chapters, use_ocr)
            if text:
                all_text.append(f"--- {file_path.name} ---\n{text}")
                self.log_signal.emit(f"        ✓ {len(text)} chars")
            else:
                self.log_signal.emit(f"        ✗ No text extracted")

        if not all_text:
            self.log_signal.emit(f"    ✗ No text extracted from any files")
            return

        combined_text = "\n\n".join(all_text)
        self.log_signal.emit(f"    ✓ Combined text: {len(combined_text)} chars total")

        folder_name = subdir.name
        metadata_file = subdir.parent / f"{folder_name}_metadata.json"
        user_metadata = {}

        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    user_metadata = json.load(f)
                self.log_signal.emit(f"    ✓ Loaded folder metadata")
            except:
                pass

        summary = combined_text
        ai_tags = ""
        ai_notes = ""
        input_tokens = 0
        output_tokens = 0

        if enable_summarization:
            self.log_signal.emit(f"    ► Summarizing combined content...")
            provider = assignment.get("ai_provider", "OpenAI")
            summary, ai_tags, ai_notes, input_tokens, output_tokens = self.run_summarization_sync(combined_text,
                                                                                                  provider)
            self.log_signal.emit(f"    ✓ Summarization complete (tokens: {input_tokens + output_tokens})")

            if self.current_batch_id:
                self.cost_tracker.add_item(
                    batch_id=self.current_batch_id,
                    item_name=folder_name,
                    item_type="pdf_folder",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens
                )
                self.cost_tracker.update_batch(
                    self.current_batch_id,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens
                )

        merged_metadata = self.merge_metadata(user_metadata, ai_tags, ai_notes)
        metadata = self.build_metadata(subdir, merged_metadata, summary, combined_text)
        metadata["source_type"] = "pdf_folder"
        metadata["file_count"] = len(files)
        metadata["files"] = [f.name for f in files]

        markdown_content = self.generate_markdown_content(
            title=merged_metadata.get("title", folder_name),
            source=merged_metadata.get("original_source", ""),
            tags=merged_metadata.get("tags", ""),
            content=summary
        )

        output_txt = output_dir / f"{folder_name}.txt.gz"
        output_md = output_dir / f"{folder_name}.md"
        output_json = output_dir / f"{folder_name}.json"

        import gzip
        with gzip.open(output_txt, 'wt', encoding='utf-8') as f:
            f.write(combined_text)
        with open(output_md, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)

        self.log_signal.emit(f"    ✓ Saved: {folder_name}.txt.gz + {folder_name}.md + {folder_name}.json\n")

    def process_single_pdf_file(self, file_path, source_folder, output_dir, detect_chapters, use_ocr,
                                enable_summarization, assignment):
        """Process single PDF file"""
        text = self._extract_pdf_text(file_path, detect_chapters, use_ocr)

        if not text:
            self.log_signal.emit(f"    ⚠ No text extracted")
            return

        self.log_signal.emit(f"    ✓ Extracted {len(text)} chars")

        summary = text
        ai_tags = ""
        ai_notes = ""
        input_tokens = 0
        output_tokens = 0

        if enable_summarization:
            self.log_signal.emit(f"    ► Summarizing...")
            provider = assignment.get("ai_provider", "OpenAI")
            summary, ai_tags, ai_notes, input_tokens, output_tokens = self.run_summarization_sync(text, provider)
            self.log_signal.emit(f"    ✓ Summarization complete (tokens: {input_tokens + output_tokens})")

            if self.current_batch_id:
                self.cost_tracker.add_item(
                    batch_id=self.current_batch_id,
                    item_name=file_path.name,
                    item_type="pdf_file",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens
                )
                self.cost_tracker.update_batch(
                    self.current_batch_id,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens
                )

        metadata_file = file_path.parent / f"{file_path.stem}_metadata.json"
        user_metadata = {}
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    user_metadata = json.load(f)
                self.log_signal.emit(f"    ✓ Loaded metadata")
            except:
                pass

        merged_metadata = self.merge_metadata(user_metadata, ai_tags, ai_notes)
        metadata = self.build_metadata(file_path, merged_metadata, summary, text)
        metadata["source_type"] = "pdf"

        markdown_content = self.generate_markdown_content(
            title=merged_metadata.get("title", ""),
            source=merged_metadata.get("original_source", ""),
            tags=merged_metadata.get("tags", ""),
            content=summary
        )

        output_txt = output_dir / f"{file_path.stem}.txt.gz"
        output_md = output_dir / f"{file_path.stem}.md"
        output_json = output_dir / f"{file_path.stem}.json"

        import gzip
        with gzip.open(output_txt, 'wt', encoding='utf-8') as f:
            f.write(text)
        with open(output_md, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)

        self.log_signal.emit(f"    ✓ Saved: {file_path.stem}.txt.gz + {file_path.stem}.md + {file_path.stem}.json\n")

    def _extract_pdf_text(self, pdf_path, detect_chapters, use_ocr):
        """Extract text from PDF"""
        import fitz

        try:
            doc = fitz.open(pdf_path)
            content = []

            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()

                if not text.strip() and use_ocr:
                    try:
                        import pytesseract
                        from PIL import Image
                        import io
                        pix = page.get_pixmap()
                        img = Image.open(io.BytesIO(pix.tobytes()))
                        text = pytesseract.image_to_string(img)
                    except:
                        pass

                if text.strip():
                    content.append(f"--- Page {page_num + 1} ---\n{text.strip()}")

            return "\n\n".join(content)
        except Exception as e:
            self.log_signal.emit(f"    ✗ PDF Error: {e}")
            return ""

    def process_text_assignment(self, assignment, base_output_folder):
        """Process text document assignment - handles subdirectories like OCR"""
        source_folder = assignment.get("source_folder", "")
        file_pattern = assignment.get("file_pattern", "*.txt, *.md")
        enable_summarization = assignment.get("enable_summarization", True)

        if not Path(source_folder).exists():
            self.log_signal.emit(f"  ✗ Source folder not found: {source_folder}")
            return

        # Create output subfolder
        output_dir = Path(base_output_folder) / "text"
        output_dir.mkdir(exist_ok=True)

        self.log_signal.emit(f"  Source: {source_folder}")
        self.log_signal.emit(f"  Output: {output_dir}")

        source = Path(source_folder)
        patterns = [p.strip() for p in file_pattern.split(',')]

        # Separate subdirectories and root-level files
        all_items = list(source.iterdir())
        subdirectories = [d for d in all_items if d.is_dir()]

        root_files = []
        for pattern in patterns:
            matches = [f for f in source.glob(pattern) if f.is_file() and f.parent == source]
            root_files.extend(matches)

        root_files = sorted(root_files, key=lambda x: x.name.lower())
        subdirectories = sorted(subdirectories, key=lambda x: x.name.lower())

        total_items = len(subdirectories) + len(root_files)

        if total_items == 0:
            self.log_signal.emit("  ⚠ No matching files or folders found")
            return

        self.log_signal.emit(f"  Found {len(subdirectories)} subdirectories and {len(root_files)} root files\n")

        current_item = 0

        # Process subdirectories first
        for subdir in subdirectories:
            current_item += 1
            self.log_signal.emit(f"  [{current_item}/{total_items}] Processing subdirectory: {subdir.name}")

            try:
                self.process_text_subdirectory(subdir, patterns, output_dir, enable_summarization, assignment)
            except Exception as e:
                self.log_signal.emit(f"    ✗ Error processing subdirectory: {e}\n")

        # Process root-level files
        for idx, file_path in enumerate(root_files, current_item + 1):
            self.log_signal.emit(f"  [{idx}/{total_items}] Processing: {file_path.name}")

            try:
                self.process_single_text_file(file_path, source, output_dir, enable_summarization, assignment)
            except Exception as e:
                self.log_signal.emit(f"    ✗ Error: {e}\n")

        self.log_signal.emit(f"\n  ✓ Completed: {total_items} items processed")

    def process_text_subdirectory(self, subdir, patterns, output_dir, enable_summarization, assignment):
        """Process subdirectory - combine all text files into one output"""
        # Collect files
        files = []
        for pattern in patterns:
            files.extend(subdir.glob(pattern))

        files = sorted([f for f in files if f.is_file()], key=lambda x: x.name.lower())

        if not files:
            self.log_signal.emit(f"    ⚠ No matching files in subdirectory")
            return

        self.log_signal.emit(f"    Found {len(files)} files in subdirectory")

        # Process each file and collect text
        all_text = []

        for file_idx, file_path in enumerate(files, 1):
            self.log_signal.emit(f"      [{file_idx}/{len(files)}] Reading: {file_path.name}")

            text = self._load_text_file(file_path)

            if text:
                all_text.append(f"--- {file_path.name} ---\n{text}")
                self.log_signal.emit(f"        ✓ {len(text)} chars")
            else:
                self.log_signal.emit(f"        ✗ No text extracted")

        if not all_text:
            self.log_signal.emit(f"    ✗ No text extracted from any files")
            return

        # Combine all text
        combined_text = "\n\n".join(all_text)
        self.log_signal.emit(f"    ✓ Combined text: {len(combined_text)} chars total")

        # Load folder metadata
        folder_name = subdir.name
        metadata_file = subdir.parent / f"{folder_name}_metadata.json"
        user_metadata = {}

        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    user_metadata = json.load(f)
                self.log_signal.emit(f"    ✓ Loaded folder metadata")
            except:
                pass

        # Run summarization
        summary = combined_text
        ai_tags = ""
        ai_notes = ""
        input_tokens = 0
        output_tokens = 0

        if enable_summarization:
            self.log_signal.emit(f"    ► Summarizing combined content...")
            provider = assignment.get("ai_provider", "OpenAI")
            summary, ai_tags, ai_notes, input_tokens, output_tokens = self.run_summarization_sync(combined_text,
                                                                                                  provider)
            self.log_signal.emit(f"    ✓ Summarization complete (tokens: {input_tokens + output_tokens})")

            # Track this folder's cost
            if self.current_batch_id:
                self.cost_tracker.add_item(
                    batch_id=self.current_batch_id,
                    item_name=folder_name,
                    item_type="text_folder",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens
                )

                # Update batch totals
                self.cost_tracker.update_batch(
                    self.current_batch_id,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens
                )

        # Merge metadata
        merged_metadata = self.merge_metadata(user_metadata, ai_tags, ai_notes)

        # Build metadata
        metadata = self.build_metadata(subdir, merged_metadata, summary, combined_text)
        metadata["source_type"] = "text_folder"
        metadata["file_count"] = len(files)
        metadata["files"] = [f.name for f in files]

        # Generate markdown
        markdown_content = self.generate_markdown_content(
            title=merged_metadata.get("title", folder_name),
            source=merged_metadata.get("original_source", ""),
            tags=merged_metadata.get("tags", ""),
            content=summary
        )

        # Save files (same as OCR)
        output_txt = output_dir / f"{folder_name}.txt.gz"
        output_md = output_dir / f"{folder_name}.md"
        output_json = output_dir / f"{folder_name}.json"

        import gzip
        with gzip.open(output_txt, 'wt', encoding='utf-8') as f:
            f.write(combined_text)

        with open(output_md, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)

        self.log_signal.emit(f"    ✓ Saved: {folder_name}.txt.gz + {folder_name}.md + {folder_name}.json\n")

    def process_single_text_file(self, file_path, source_folder, output_dir, enable_summarization, assignment):
        """Process single text file"""
        # Load text
        text = self._load_text_file(file_path)

        if not text:
            self.log_signal.emit(f"    ⚠ No text extracted")
            return

        self.log_signal.emit(f"    ✓ Loaded {len(text)} chars")

        # Run summarization
        summary = text
        ai_tags = ""
        ai_notes = ""
        input_tokens = 0
        output_tokens = 0

        if enable_summarization:
            self.log_signal.emit(f"    ► Summarizing...")
            provider = assignment.get("ai_provider", "OpenAI")
            summary, ai_tags, ai_notes, input_tokens, output_tokens = self.run_summarization_sync(text, provider)
            self.log_signal.emit(f"    ✓ Summarization complete (tokens: {input_tokens + output_tokens})")

            # Track cost
            if self.current_batch_id:
                self.cost_tracker.add_item(
                    batch_id=self.current_batch_id,
                    item_name=file_path.name,
                    item_type="text_file",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens
                )

                # Update batch totals
                self.cost_tracker.update_batch(
                    self.current_batch_id,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens
                )

        # Load user metadata
        metadata_file = file_path.parent / f"{file_path.stem}_metadata.json"
        user_metadata = {}

        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    user_metadata = json.load(f)
                self.log_signal.emit(f"    ✓ Loaded metadata")
            except:
                pass

        # Merge metadata
        merged_metadata = self.merge_metadata(user_metadata, ai_tags, ai_notes)

        # Build metadata
        metadata = self.build_metadata(file_path, merged_metadata, summary, text)
        metadata["source_type"] = "text"

        # Generate markdown
        markdown_content = self.generate_markdown_content(
            title=merged_metadata.get("title", ""),
            source=merged_metadata.get("original_source", ""),
            tags=merged_metadata.get("tags", ""),
            content=summary
        )

        # Save files (same pattern as OCR)
        output_txt = output_dir / f"{file_path.stem}.txt.gz"
        output_md = output_dir / f"{file_path.stem}.md"
        output_json = output_dir / f"{file_path.stem}.json"

        import gzip
        with gzip.open(output_txt, 'wt', encoding='utf-8') as f:
            f.write(text)

        with open(output_md, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)

        self.log_signal.emit(f"    ✓ Saved: {file_path.stem}.txt.gz + {file_path.stem}.md + {file_path.stem}.json\n")

    def _load_text_file(self, path: Path) -> str:
        """Load plain text file with encoding detection"""
        try:
            # Try UTF-8 first
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read()
            except UnicodeDecodeError:
                # Detect encoding
                import chardet
                with open(path, 'rb') as f:
                    raw_data = f.read()
                    result = chardet.detect(raw_data)
                    encoding = result['encoding'] or 'utf-8'

                with open(path, 'r', encoding=encoding, errors='ignore') as f:
                    return f.read()

        except Exception as e:
            self.log_signal.emit(f"      ✗ Error loading file: {e}")
            return ""


class AutoTab(QWidget):
    """Auto Mode - Batch processing and automation"""

    def __init__(self, parent, shared_components, metadata_panel):
        super().__init__(parent)
        self.parent = parent
        self.shared_components = shared_components
        self.metadata_panel = metadata_panel

        # Database path for project-specific cost tracking
        self.database_path = None

        # Store assignments (will be saved to JSON later)
        self.assignments = []
        self.assignment_queue = []
        self.assignment_data = {}  # Store assignment configurations by index

        # Track inspect mode
        self.inspect_mode = False
        self.inspected_assignment_index = None

        self.init_ui()

    def init_ui(self):
        """Initialize the Auto mode interface with sub-tabs"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create sub-tab widget for Auto features
        self.auto_tabs = QTabWidget()
        layout.addWidget(self.auto_tabs)

        # Sub-Tab 1: Assignment Builder
        self.builder_tab = self.create_assignment_builder()
        self.auto_tabs.addTab(self.builder_tab, "Assignment Builder")

        # Sub-Tab 2: Assignment Queue
        self.queue_tab = self.create_assignment_queue()
        self.auto_tabs.addTab(self.queue_tab, "Queue")

        # Sub-Tab 3: Cost Analytics
        self.analytics_tab = self.create_cost_analytics()
        self.auto_tabs.addTab(self.analytics_tab, "Analytics")

    def create_assignment_builder(self):
        """Create the Assignment Builder sub-tab"""
        widget = QWidget()
        layout = QHBoxLayout(widget)

        # Create splitter for left/right panels
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # Left panel - Assignment configuration
        left_panel = self.create_builder_left_panel()
        splitter.addWidget(left_panel)

        # Right panel - Preview and actions
        right_panel = self.create_builder_right_panel()
        splitter.addWidget(right_panel)

        # Set initial sizes (40% left, 60% right)
        splitter.setSizes([400, 600])

        return widget

    def create_builder_left_panel(self):
        """Create the left panel with assignment type selector and config"""
        from PySide6.QtWidgets import QStackedWidget

        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Assignment Type Selector with embedded info
        type_group = QGroupBox("Assignment Type")
        type_layout = QVBoxLayout(type_group)

        self.assignment_type = QComboBox()
        self.assignment_type.addItems([
            "Select Type...",
            "Folder of Files - OCR",
            "Folder of Files - Text",
            "Folder of Files - PDF",
            "Website Crawler",
            "Database Query",
            "API Integration",
            "Post-Processing",
            "Vector Migration"
        ])
        self.assignment_type.currentTextChanged.connect(self.on_assignment_type_changed)
        type_layout.addWidget(self.assignment_type)

        # Assignment info summary (replaces preview text)
        self.assignment_info = QLabel()
        self.assignment_info.setWordWrap(True)
        self.assignment_info.setStyleSheet(
            "color: #aaa; font-size: 11px; padding: 8px; background: #2a2a2a; border-radius: 4px;")
        self.assignment_info.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.assignment_info.setMinimumHeight(100)
        type_layout.addWidget(self.assignment_info)

        layout.addWidget(type_group)

        # Scrollable area for type-specific configuration
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.StyledPanel)
        layout.addWidget(scroll, 1)

        # Stacked widget to hold different configuration panels
        self.config_stack = QStackedWidget()
        scroll.setWidget(self.config_stack)

        # Add configuration panels for each type
        self.config_stack.addWidget(self.create_placeholder_config("Please select an assignment type"))
        self.config_stack.addWidget(self.create_folder_ocr_config())
        self.config_stack.addWidget(self.create_folder_text_config())
        self.config_stack.addWidget(self.create_folder_pdf_config())
        self.config_stack.addWidget(self.create_placeholder_config("Website Crawler - Coming Soon"))
        self.config_stack.addWidget(self.create_placeholder_config("Database Query - Coming Soon"))
        self.config_stack.addWidget(self.create_placeholder_config("API Integration - Coming Soon"))
        self.config_stack.addWidget(self.create_placeholder_config("Post-Processing - Coming Soon"))
        self.config_stack.addWidget(self.create_placeholder_config("Vector Migration - Coming Soon"))

        # Action buttons at bottom
        button_layout = QHBoxLayout()

        self.save_assignment_btn = QPushButton("Save Assignment")
        self.save_assignment_btn.setCursor(Qt.PointingHandCursor)
        self.save_assignment_btn.clicked.connect(self.save_assignment)
        self.save_assignment_btn.setEnabled(False)
        self.save_assignment_btn.setFixedHeight(40)
        button_layout.addWidget(self.save_assignment_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.cancel_inspect)
        self.cancel_btn.setEnabled(False)  # Only enabled in inspect mode
        self.cancel_btn.setFixedHeight(40)
        button_layout.addWidget(self.cancel_btn)

        self.reset_builder_btn = QPushButton("Reset")
        self.reset_builder_btn.setCursor(Qt.PointingHandCursor)
        self.reset_builder_btn.clicked.connect(self.reset_builder)
        self.reset_builder_btn.setFixedHeight(40)
        button_layout.addWidget(self.reset_builder_btn)

        layout.addLayout(button_layout)

        return panel

    def create_builder_right_panel(self):
        """Create the right panel with folder preview and metadata editing"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Folder contents preview
        preview_group = QGroupBox("Assignment Preview")
        preview_layout = QVBoxLayout(preview_group)

        # Tree widget for folder/file display
        self.folder_tree = QTreeWidget()
        self.folder_tree.setHeaderHidden(True)
        self.folder_tree.setAlternatingRowColors(True)
        self.folder_tree.itemSelectionChanged.connect(self.on_folder_item_selected)
        preview_layout.addWidget(self.folder_tree)

        # Add Metadata button
        self.add_metadata_btn = QPushButton("Add/Edit Metadata")
        self.add_metadata_btn.setCursor(Qt.PointingHandCursor)
        self.add_metadata_btn.setEnabled(False)
        self.add_metadata_btn.clicked.connect(self.open_metadata_dialog_from_builder)
        self.add_metadata_btn.setFixedHeight(35)
        preview_layout.addWidget(self.add_metadata_btn)

        layout.addWidget(preview_group, 2)

        # JSON configuration view
        json_group = QGroupBox("JSON Configuration (Advanced)")
        json_layout = QVBoxLayout(json_group)
        json_layout.setContentsMargins(8, 8, 8, 8)

        self.json_view = QTextEdit()
        self.json_view.setReadOnly(True)
        self.json_view.setPlaceholderText("JSON configuration will appear here...")
        json_layout.addWidget(self.json_view)

        layout.addWidget(json_group, 1)

        return panel

    def create_placeholder_config(self, message):
        """Create a placeholder widget for configuration panels not yet implemented"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        label = QLabel(message)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: #888; font-size: 14px; padding: 40px;")
        layout.addWidget(label)
        layout.addStretch()

        return widget

    def create_folder_ocr_config(self):
        """Create configuration panel for Folder OCR assignment type"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Basic settings group
        basic_group = QGroupBox("Basic Settings")
        basic_layout = QFormLayout(basic_group)
        basic_layout.setContentsMargins(12, 12, 12, 12)

        self.assignment_name = QLineEdit()
        self.assignment_name.setPlaceholderText("e.g., 'Process Book Scans - AI Textbook'")
        self.assignment_name.textChanged.connect(self.update_preview)
        basic_layout.addRow("Assignment Name:", self.assignment_name)

        # Folder selection
        folder_layout = QHBoxLayout()
        self.source_folder = QLineEdit()
        self.source_folder.setPlaceholderText("Select folder containing images...")
        self.source_folder.textChanged.connect(self.on_source_folder_changed)
        folder_layout.addWidget(self.source_folder)

        browse_btn = QPushButton("Browse...")
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.clicked.connect(self.browse_source_folder)
        folder_layout.addWidget(browse_btn)

        basic_layout.addRow("Source Folder:", folder_layout)

        layout.addWidget(basic_group)

        # OCR settings group
        ocr_group = QGroupBox("OCR Settings")
        ocr_layout = QFormLayout(ocr_group)
        ocr_layout.setContentsMargins(12, 12, 12, 12)

        self.ocr_preprocess = QCheckBox("Enable image preprocessing")
        self.ocr_preprocess.setChecked(True)
        self.ocr_preprocess.stateChanged.connect(self.update_preview)
        ocr_layout.addRow("Enhancement:", self.ocr_preprocess)

        self.ocr_file_pattern = QLineEdit()
        self.ocr_file_pattern.setText("*.png, *.jpg, *.jpeg")
        self.ocr_file_pattern.textChanged.connect(self.update_preview)
        ocr_layout.addRow("File Pattern:", self.ocr_file_pattern)

        layout.addWidget(ocr_group)

        # Processing options group
        processing_group = QGroupBox("Processing Options")
        processing_layout = QFormLayout(processing_group)
        processing_layout.setContentsMargins(12, 12, 12, 12)

        self.enable_summarization = QCheckBox("Enable AI summarization")
        self.enable_summarization.setChecked(True)
        self.enable_summarization.stateChanged.connect(self.update_preview)
        processing_layout.addRow("Summarization:", self.enable_summarization)

        # AI Provider selection
        self.ocr_ai_provider = QComboBox()
        self.ocr_ai_provider.addItems(["OpenAI", "Claude", "Gemini"])
        self.ocr_ai_provider.setCurrentText("OpenAI")
        self.ocr_ai_provider.currentTextChanged.connect(self.update_preview)
        processing_layout.addRow("AI Provider:", self.ocr_ai_provider)

        layout.addWidget(processing_group)

        layout.addStretch()

        return widget

    def create_folder_text_config(self):
        """Create configuration panel for Folder Text assignment type"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Basic settings group
        basic_group = QGroupBox("Basic Settings")
        basic_layout = QFormLayout(basic_group)
        basic_layout.setContentsMargins(12, 12, 12, 12)

        self.text_assignment_name = QLineEdit()
        self.text_assignment_name.setPlaceholderText("e.g., 'Process Research Notes'")
        self.text_assignment_name.textChanged.connect(self.update_preview)
        basic_layout.addRow("Assignment Name:", self.text_assignment_name)

        # Folder selection
        folder_layout = QHBoxLayout()
        self.text_source_folder = QLineEdit()
        self.text_source_folder.setPlaceholderText("Select folder containing text files...")
        self.text_source_folder.textChanged.connect(self.on_source_folder_changed)
        folder_layout.addWidget(self.text_source_folder)

        browse_btn = QPushButton("Browse...")
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.clicked.connect(self.browse_text_source_folder)
        folder_layout.addWidget(browse_btn)

        basic_layout.addRow("Source Folder:", folder_layout)

        layout.addWidget(basic_group)

        # Text settings group
        text_group = QGroupBox("Text Settings")
        text_layout = QFormLayout(text_group)
        text_layout.setContentsMargins(12, 12, 12, 12)

        self.text_file_pattern = QLineEdit()
        self.text_file_pattern.setText("*.txt, *.md")
        self.text_file_pattern.textChanged.connect(self.update_preview)
        text_layout.addRow("File Pattern:", self.text_file_pattern)

        layout.addWidget(text_group)

        # Processing options group
        processing_group = QGroupBox("Processing Options")
        processing_layout = QFormLayout(processing_group)
        processing_layout.setContentsMargins(12, 12, 12, 12)

        self.text_enable_summarization = QCheckBox("Enable AI summarization")
        self.text_enable_summarization.setChecked(True)
        self.text_enable_summarization.stateChanged.connect(self.update_preview)
        processing_layout.addRow("Summarization:", self.text_enable_summarization)

        # AI Provider selection
        self.text_ai_provider = QComboBox()
        self.text_ai_provider.addItems(["OpenAI", "Claude", "Gemini"])
        self.text_ai_provider.setCurrentText("OpenAI")
        self.text_ai_provider.currentTextChanged.connect(self.update_preview)
        processing_layout.addRow("AI Provider:", self.text_ai_provider)

        # Summary style
        self.text_summary_style = QComboBox()
        self.text_summary_style.addItems(["Concise", "Detailed", "Bullet Points"])
        self.text_summary_style.currentTextChanged.connect(self.update_preview)
        processing_layout.addRow("Summary Style:", self.text_summary_style)

        layout.addWidget(processing_group)

        layout.addStretch()

        return widget

    def create_folder_pdf_config(self):
        """Create configuration panel for Folder PDF assignment type"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        basic_group = QGroupBox("Basic Settings")
        basic_layout = QFormLayout(basic_group)
        basic_layout.setContentsMargins(12, 12, 12, 12)

        self.pdf_assignment_name = QLineEdit()
        self.pdf_assignment_name.setPlaceholderText("e.g., 'Process Research Papers'")
        self.pdf_assignment_name.textChanged.connect(self.update_preview)
        basic_layout.addRow("Assignment Name:", self.pdf_assignment_name)

        folder_layout = QHBoxLayout()
        self.pdf_source_folder = QLineEdit()
        self.pdf_source_folder.setPlaceholderText("Select folder containing PDFs...")
        self.pdf_source_folder.textChanged.connect(self.on_source_folder_changed)
        folder_layout.addWidget(self.pdf_source_folder)

        browse_btn = QPushButton("Browse...")
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.clicked.connect(self.browse_pdf_source_folder)
        folder_layout.addWidget(browse_btn)

        basic_layout.addRow("Source Folder:", folder_layout)
        layout.addWidget(basic_group)

        pdf_group = QGroupBox("PDF Settings")
        pdf_layout = QFormLayout(pdf_group)
        pdf_layout.setContentsMargins(12, 12, 12, 12)

        self.pdf_file_pattern = QLineEdit()
        self.pdf_file_pattern.setText("*.pdf")
        self.pdf_file_pattern.textChanged.connect(self.update_preview)
        pdf_layout.addRow("File Pattern:", self.pdf_file_pattern)

        self.pdf_detect_chapters = QCheckBox("Detect chapters")
        self.pdf_detect_chapters.setChecked(False)
        self.pdf_detect_chapters.stateChanged.connect(self.update_preview)
        pdf_layout.addRow("Chapter Detection:", self.pdf_detect_chapters)

        self.pdf_use_ocr = QCheckBox("Use OCR for failed pages")
        self.pdf_use_ocr.setChecked(False)
        self.pdf_use_ocr.stateChanged.connect(self.update_preview)
        pdf_layout.addRow("OCR Fallback:", self.pdf_use_ocr)

        layout.addWidget(pdf_group)

        processing_group = QGroupBox("Processing Options")
        processing_layout = QFormLayout(processing_group)
        processing_layout.setContentsMargins(12, 12, 12, 12)

        self.pdf_enable_summarization = QCheckBox("Enable AI summarization")
        self.pdf_enable_summarization.setChecked(True)
        self.pdf_enable_summarization.stateChanged.connect(self.update_preview)
        processing_layout.addRow("Summarization:", self.pdf_enable_summarization)

        self.pdf_ai_provider = QComboBox()
        self.pdf_ai_provider.addItems(["OpenAI", "Claude", "Gemini"])
        self.pdf_ai_provider.setCurrentText("OpenAI")
        self.pdf_ai_provider.currentTextChanged.connect(self.update_preview)
        processing_layout.addRow("AI Provider:", self.pdf_ai_provider)

        self.pdf_summary_style = QComboBox()
        self.pdf_summary_style.addItems(["Concise", "Detailed", "Bullet Points"])
        self.pdf_summary_style.currentTextChanged.connect(self.update_preview)
        processing_layout.addRow("Summary Style:", self.pdf_summary_style)

        layout.addWidget(processing_group)

        layout.addStretch()

        return widget

    def create_assignment_queue(self):
        """Create the Assignment Queue sub-tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Queue header with controls
        header_layout = QHBoxLayout()

        header_label = QLabel("Assignment Queue")
        header_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_layout.addWidget(header_label)

        header_layout.addStretch()

        # Queue control buttons
        self.run_queue_btn = QPushButton("Run Queue")
        self.run_queue_btn.setCursor(Qt.PointingHandCursor)
        self.run_queue_btn.setFixedHeight(35)
        self.run_queue_btn.setEnabled(False)
        self.run_queue_btn.clicked.connect(self.run_queue)
        header_layout.addWidget(self.run_queue_btn)

        self.pause_queue_btn = QPushButton("Pause")
        self.pause_queue_btn.setCursor(Qt.PointingHandCursor)
        self.pause_queue_btn.setFixedHeight(35)
        self.pause_queue_btn.setEnabled(False)
        header_layout.addWidget(self.pause_queue_btn)

        self.inspect_btn = QPushButton("Inspect")
        self.inspect_btn.setCursor(Qt.PointingHandCursor)
        self.inspect_btn.setFixedHeight(35)
        self.inspect_btn.setEnabled(False)
        self.inspect_btn.clicked.connect(self.inspect_assignment)
        header_layout.addWidget(self.inspect_btn)

        self.clear_log_btn = QPushButton("Clear Log")
        self.clear_log_btn.setCursor(Qt.PointingHandCursor)
        self.clear_log_btn.setFixedHeight(35)
        self.clear_log_btn.clicked.connect(self.clear_execution_log)
        header_layout.addWidget(self.clear_log_btn)

        self.clear_queue_btn = QPushButton("Clear Queue")
        self.clear_queue_btn.setCursor(Qt.PointingHandCursor)
        self.clear_queue_btn.setFixedHeight(35)
        self.clear_queue_btn.clicked.connect(self.clear_queue)
        header_layout.addWidget(self.clear_queue_btn)

        layout.addLayout(header_layout)

        # Queue list area
        from PySide6.QtWidgets import QListWidget

        self.queue_list = QListWidget()
        self.queue_list.setAlternatingRowColors(True)
        self.queue_list.itemSelectionChanged.connect(self.on_queue_selection_changed)
        layout.addWidget(self.queue_list, 2)

        # Console/log area
        console_group = QGroupBox("Execution Log")
        console_layout = QVBoxLayout(console_group)

        self.queue_console = QTextEdit()
        self.queue_console.setReadOnly(True)
        self.queue_console.setPlaceholderText("Queue execution log will appear here...")
        console_layout.addWidget(self.queue_console)

        layout.addWidget(console_group, 1)

        return widget

    def create_cost_analytics(self):
        """Create the Cost Analytics sub-tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header = QLabel("Cost Analytics Dashboard")
        header.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        layout.addWidget(header)

        # Real-time stats section (updates during processing)
        realtime_group = QGroupBox("Current Session")
        realtime_layout = QVBoxLayout(realtime_group)

        self.realtime_tokens_label = QLabel("Tokens: 0")
        self.realtime_tokens_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        realtime_layout.addWidget(self.realtime_tokens_label)

        self.realtime_cost_label = QLabel("Cost: $0.0000")
        self.realtime_cost_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #2ecc71;")
        realtime_layout.addWidget(self.realtime_cost_label)

        layout.addWidget(realtime_group)

        # All-time statistics section
        stats_group = QGroupBox("All-Time Statistics")
        stats_layout = QFormLayout(stats_group)
        stats_layout.setSpacing(10)

        self.total_batches_label = QLabel("0")
        self.total_batches_label.setStyleSheet("font-weight: bold;")
        stats_layout.addRow("Total Batches:", self.total_batches_label)

        self.total_tokens_label = QLabel("0")
        self.total_tokens_label.setStyleSheet("font-weight: bold;")
        stats_layout.addRow("Total Tokens:", self.total_tokens_label)

        self.total_cost_label = QLabel("$0.0000")
        self.total_cost_label.setStyleSheet("font-weight: bold; color: #3498db;")
        stats_layout.addRow("Total Cost:", self.total_cost_label)

        self.total_items_label = QLabel("0")
        self.total_items_label.setStyleSheet("font-weight: bold;")
        stats_layout.addRow("Total Items:", self.total_items_label)

        layout.addWidget(stats_group)

        # Recent batches table
        batches_group = QGroupBox("Recent Batches")
        batches_layout = QVBoxLayout(batches_group)

        from PySide6.QtWidgets import QTableWidget, QHeaderView, QAbstractItemView

        self.batches_table = QTableWidget()
        self.batches_table.setColumnCount(6)
        self.batches_table.setHorizontalHeaderLabels([
            "Batch Name", "Type", "Status", "Items", "Tokens", "Cost"
        ])

        # Configure table appearance
        self.batches_table.setAlternatingRowColors(True)
        self.batches_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.batches_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.batches_table.horizontalHeader().setStretchLastSection(True)
        self.batches_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

        batches_layout.addWidget(self.batches_table)

        # Refresh button
        refresh_btn = QPushButton("Refresh Data")
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.clicked.connect(self.refresh_analytics)
        batches_layout.addWidget(refresh_btn)

        layout.addWidget(batches_group, 1)  # Give it stretch factor

        # Load initial data
        self.refresh_analytics()

        return widget

    def refresh_analytics(self):
        """Refresh all analytics data from database"""
        from cost_tracker import CostTracker

        # Use project-specific database path if available
        tracker = CostTracker(db_path=self.database_path)

        # Update all-time stats
        stats = tracker.get_total_stats()

        self.total_batches_label.setText(f"{stats.get('total_batches', 0):,}")
        self.total_tokens_label.setText(f"{stats.get('total_tokens', 0):,}")
        self.total_cost_label.setText(f"${stats.get('total_cost', 0):.4f}")
        self.total_items_label.setText(f"{stats.get('total_items', 0):,}")

        # Update recent batches table
        batches = tracker.get_recent_batches(limit=10)

        self.batches_table.setRowCount(len(batches))

        for row_idx, batch in enumerate(batches):
            # Batch name
            from PySide6.QtWidgets import QTableWidgetItem

            name_item = QTableWidgetItem(batch['batch_name'] or "Unnamed")
            self.batches_table.setItem(row_idx, 0, name_item)

            # Type
            type_item = QTableWidgetItem(batch['assignment_type'])
            self.batches_table.setItem(row_idx, 1, type_item)

            # Status
            status = batch['status']
            status_item = QTableWidgetItem(status.capitalize())

            # Color code status
            if status == 'completed':
                status_item.setForeground(Qt.darkGreen)
            elif status == 'failed':
                status_item.setForeground(Qt.red)
            elif status == 'running':
                status_item.setForeground(Qt.blue)

            self.batches_table.setItem(row_idx, 2, status_item)

            # Items (processed/total)
            items_text = f"{batch['items_processed']}/{batch['items_total']}"
            items_item = QTableWidgetItem(items_text)
            self.batches_table.setItem(row_idx, 3, items_item)

            # Tokens
            tokens_item = QTableWidgetItem(f"{batch['total_tokens']:,}")
            self.batches_table.setItem(row_idx, 4, tokens_item)

            # Cost
            cost_item = QTableWidgetItem(f"${batch['estimated_cost']:.4f}")
            self.batches_table.setItem(row_idx, 5, cost_item)

        self.batches_table.resizeColumnsToContents()

    def update_realtime_analytics(self, stats: dict):
        """Update real-time analytics display during queue processing"""
        self.realtime_tokens_label.setText(f"Tokens: {stats.get('total_tokens', 0):,}")
        self.realtime_cost_label.setText(f"Cost: ${stats.get('total_cost', 0):.4f}")

    # Event handlers and utility methods

    def on_assignment_type_changed(self, text):
        """Handle assignment type selection change"""
        index = self.assignment_type.currentIndex()
        self.config_stack.setCurrentIndex(index)

        # Enable save button if valid type selected
        self.save_assignment_btn.setEnabled(index > 0)

        # Update preview
        self.update_preview()

    def browse_source_folder(self):
        """Open folder browser dialog"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Source Folder",
            ""
        )

        if folder:
            self.source_folder.setText(folder)

    def browse_text_source_folder(self):
        """Open folder browser dialog for text files"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Text Source Folder",
            ""
        )

        if folder:
            self.text_source_folder.setText(folder)

    def browse_pdf_source_folder(self):
        """Open folder browser dialog for PDF files"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select PDF Source Folder",
            ""
        )

        if folder:
            self.pdf_source_folder.setText(folder)

    def on_source_folder_changed(self):
        """Handle source folder path change - populate folder tree"""
        folder_path = self.source_folder.text()

        # Clear existing tree
        self.folder_tree.clear()

        if not folder_path or not Path(folder_path).exists():
            return

        # Populate tree with folder contents
        self.populate_folder_tree(folder_path)

        # Update preview
        self.update_preview()

    def populate_folder_tree(self, folder_path):
        """Populate the folder tree with files and subdirectories"""
        folder = Path(folder_path)

        if not folder.exists():
            return

        # Get file patterns
        patterns = [p.strip() for p in self.ocr_file_pattern.text().split(',')]

        # Process items alphabetically
        items = sorted(folder.iterdir(), key=lambda x: x.name.lower())

        for item in items:
            if item.is_dir():
                # Check if folder has metadata file
                metadata_file = folder / f"{item.name}_metadata.json"
                has_metadata = metadata_file.exists()

                # Add folder with folder icon and checkmark if has metadata
                display_text = f"📁 {item.name}"
                if has_metadata:
                    display_text += " ✓"

                tree_item = QTreeWidgetItem([display_text])
                tree_item.setData(0, Qt.UserRole, str(item))  # Store full path
                tree_item.setData(0, Qt.UserRole + 1, "folder")  # Store type
                tree_item.setData(0, Qt.UserRole + 2, has_metadata)  # Store metadata status
                self.folder_tree.addTopLevelItem(tree_item)
            elif item.is_file():
                # Check if matches pattern
                if any(item.match(pattern.strip()) for pattern in patterns):
                    # Check if file has metadata file
                    stem = item.stem
                    metadata_file = folder / f"{stem}_metadata.json"
                    has_metadata = metadata_file.exists()

                    # Add file with icon and checkmark if has metadata
                    display_text = f"📄 {item.name}"
                    if has_metadata:
                        display_text += " ✓"

                    tree_item = QTreeWidgetItem([display_text])
                    tree_item.setData(0, Qt.UserRole, str(item))  # Store full path
                    tree_item.setData(0, Qt.UserRole + 1, "file")  # Store type
                    tree_item.setData(0, Qt.UserRole + 2, has_metadata)  # Store metadata status
                    self.folder_tree.addTopLevelItem(tree_item)

    def on_folder_item_selected(self):
        """Handle selection in folder tree"""
        has_selection = len(self.folder_tree.selectedItems()) > 0
        self.add_metadata_btn.setEnabled(has_selection)

    def update_preview(self):
        """Update the assignment info summary and JSON view"""
        assignment_type = self.assignment_type.currentText()

        if assignment_type == "Select Type..." or not assignment_type:
            self.assignment_info.clear()
            self.json_view.clear()
            return

        # Build info text (compact summary)
        if assignment_type == "Folder of Files - OCR":
            name = self.assignment_name.text() or "(unnamed)"
            folder = self.source_folder.text() or "(not selected)"
            pattern = self.ocr_file_pattern.text()
            preprocess = "Yes" if self.ocr_preprocess.isChecked() else "No"
            summarize = "Yes" if self.enable_summarization.isChecked() else "No"
            provider = self.ocr_ai_provider.currentText()

            info_text = f"Name: {name}\n"
            info_text += f"Source: {folder}\n"
            info_text += f"Pattern: {pattern}\n"
            info_text += f"Preprocessing: {preprocess} | Summarization: {summarize}\n"
            info_text += f"AI Provider: {provider}"

            self.assignment_info.setText(info_text)

            # JSON preview
            config = {
                "type": "folder_ocr",
                "name": name,
                "source_folder": folder,
                "file_pattern": pattern,
                "ocr_settings": {
                    "preprocess": self.ocr_preprocess.isChecked()
                },
                "processing": {
                    "enable_summarization": self.enable_summarization.isChecked(),
                    "ai_provider": provider
                }
            }
            self.json_view.setPlainText(json.dumps(config, indent=2))

        elif assignment_type == "Folder of Files - Text":
            name = self.text_assignment_name.text() or "(unnamed)"
            folder = self.text_source_folder.text() or "(not selected)"
            pattern = self.text_file_pattern.text()
            summarize = "Yes" if self.text_enable_summarization.isChecked() else "No"
            provider = self.text_ai_provider.currentText()
            style = self.text_summary_style.currentText()

            info_text = f"Name: {name}\n"
            info_text += f"Source: {folder}\n"
            info_text += f"Pattern: {pattern}\n"
            info_text += f"Summarization: {summarize}\n"
            info_text += f"Provider: {provider} | Style: {style}"

            self.assignment_info.setText(info_text)

            # JSON preview
            config = {
                "type": "folder_text",
                "name": name,
                "source_folder": folder,
                "file_pattern": pattern,
                "processing": {
                    "enable_summarization": self.text_enable_summarization.isChecked(),
                    "ai_provider": provider,
                    "summary_style": style
                }
            }
            self.json_view.setPlainText(json.dumps(config, indent=2))

        elif assignment_type == "Folder of Files - PDF":
            name = self.pdf_assignment_name.text() or "(unnamed)"
            folder = self.pdf_source_folder.text() or "(not selected)"
            pattern = self.pdf_file_pattern.text()
            chapters = "Yes" if self.pdf_detect_chapters.isChecked() else "No"
            ocr = "Yes" if self.pdf_use_ocr.isChecked() else "No"
            summarize = "Yes" if self.pdf_enable_summarization.isChecked() else "No"
            provider = self.pdf_ai_provider.currentText()
            style = self.pdf_summary_style.currentText()

            info_text = f"Name: {name}\n"
            info_text += f"Source: {folder}\n"
            info_text += f"Pattern: {pattern}\n"
            info_text += f"Chapters: {chapters} | OCR: {ocr}\n"
            info_text += f"Summarization: {summarize}\n"
            info_text += f"Provider: {provider} | Style: {style}"

            self.assignment_info.setText(info_text)

            config = {
                "type": "folder_pdf",
                "name": name,
                "source_folder": folder,
                "file_pattern": pattern,
                "detect_chapters": self.pdf_detect_chapters.isChecked(),
                "use_ocr": self.pdf_use_ocr.isChecked(),
                "processing": {
                    "enable_summarization": self.pdf_enable_summarization.isChecked(),
                    "ai_provider": provider,
                    "summary_style": style
                }
            }
            self.json_view.setPlainText(json.dumps(config, indent=2))

    def open_metadata_dialog_from_builder(self):
        """Open metadata dialog for selected item in folder tree"""
        selected_items = self.folder_tree.selectedItems()
        if not selected_items:
            return

        item = selected_items[0]
        item_path = item.data(0, Qt.UserRole)
        item_type = item.data(0, Qt.UserRole + 1)
        item_name = Path(item_path).name

        # Create and show metadata dialog
        dialog = MetadataDialog(self, item_name, item_type)
        if dialog.exec():
            metadata = dialog.get_metadata()

            # Save metadata to file: <base_folder>/<item_name>_metadata.json
            folder_path = Path(self.source_folder.text())

            # Determine metadata filename
            if item_type == "folder":
                # For folders, metadata file sits at parent level
                metadata_filename = f"{item_name}_metadata.json"
            else:
                # For files, remove extension and add _metadata.json
                stem = Path(item_name).stem
                metadata_filename = f"{stem}_metadata.json"

            metadata_filepath = folder_path / metadata_filename

            # Write metadata to file
            try:
                with open(metadata_filepath, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2)

                # Update tree item to show checkmark
                current_text = item.text(0)
                if " ✓" not in current_text:
                    item.setText(0, current_text + " ✓")
                item.setData(0, Qt.UserRole + 2, True)  # Update metadata status

                self.parent.statusBar().showMessage(f"Metadata saved: {metadata_filename}")

                # Log to console if in queue view
                if hasattr(self, 'queue_console'):
                    self.queue_console.append(f"✓ Metadata saved: {metadata_filename}")

            except Exception as e:
                QMessageBox.warning(self, "Save Error", f"Failed to save metadata:\n{e}")
                self.parent.statusBar().showMessage(f"Failed to save metadata")

    def save_assignment(self):
        """Save the current assignment configuration"""
        assignment_type = self.assignment_type.currentText()

        if assignment_type == "Select Type...":
            QMessageBox.warning(self, "No Type Selected", "Please select an assignment type.")
            return

        # Generate assignment name if not provided
        if not self.assignment_name.text():
            # Count existing assignments to get next number
            assignment_count = self.queue_list.count()
            assignment_name = f"Assignment {assignment_count + 1}"
            self.assignment_name.setText(assignment_name)
        else:
            assignment_name = self.assignment_name.text()

        # Check for duplicate folder assignments (prevent processing same folder twice)
        if assignment_type == "Folder of Files - OCR":
            source_folder = self.source_folder.text()

            if not self.inspect_mode and source_folder:  # Only check on new assignments, not updates
                # Check if this folder is already in queue by comparing stored paths
                for i in range(self.queue_list.count()):
                    if i in self.assignment_data:
                        existing_data = self.assignment_data[i]
                        existing_folder = existing_data.get("source_folder", "")

                        # Compare folder paths
                        if existing_folder and Path(existing_folder) == Path(source_folder):
                            existing_name = existing_data.get("name", "Unknown")
                            QMessageBox.warning(
                                self,
                                "Duplicate Assignment",
                                f"This folder is already assigned for processing:\n\n"
                                f"Folder: {source_folder}\n"
                                f"Assignment: {existing_name}\n\n"
                                "Please select a different folder or remove the existing assignment first."
                            )
                            return

        if self.inspect_mode:
            # Update existing assignment in stored data
            if assignment_type == "Folder of Files - OCR":
                assignment_data = {
                    "type": assignment_type,
                    "name": assignment_name,
                    "source_folder": self.source_folder.text(),
                    "file_pattern": self.ocr_file_pattern.text(),
                    "preprocess": self.ocr_preprocess.isChecked(),
                    "enable_summarization": self.enable_summarization.isChecked(),
                    "ai_provider": self.ocr_ai_provider.currentText()
                }
            elif assignment_type == "Folder of Files - Text":
                assignment_data = {
                    "type": assignment_type,
                    "name": self.text_assignment_name.text(),
                    "source_folder": self.text_source_folder.text(),
                    "file_pattern": self.text_file_pattern.text(),
                    "enable_summarization": self.text_enable_summarization.isChecked(),
                    "ai_provider": self.text_ai_provider.currentText(),
                    "summary_style": self.text_summary_style.currentText()
                }
            elif assignment_type == "Folder of Files - PDF":
                assignment_data = {
                    "type": assignment_type,
                    "name": self.pdf_assignment_name.text(),
                    "source_folder": self.pdf_source_folder.text(),
                    "file_pattern": self.pdf_file_pattern.text(),
                    "detect_chapters": self.pdf_detect_chapters.isChecked(),
                    "use_ocr": self.pdf_use_ocr.isChecked(),
                    "enable_summarization": self.pdf_enable_summarization.isChecked(),
                    "ai_provider": self.pdf_ai_provider.currentText(),
                    "summary_style": self.pdf_summary_style.currentText()
                }
            else:
                assignment_data = {
                    "type": assignment_type,
                    "name": assignment_name
                }

            self.assignment_data[self.inspected_assignment_index] = assignment_data

            # Update queue list display
            self.queue_list.item(self.inspected_assignment_index).setText(
                f"{assignment_name} ({assignment_type})"
            )
            self.queue_console.append(f"✓ Assignment updated: {assignment_name}")

            # Exit inspect mode
            self.exit_inspect_mode()
        else:
            # Add new assignment - store data structure
            if assignment_type == "Folder of Files - OCR":
                assignment_data = {
                    "type": assignment_type,
                    "name": assignment_name,
                    "source_folder": self.source_folder.text(),
                    "file_pattern": self.ocr_file_pattern.text(),
                    "preprocess": self.ocr_preprocess.isChecked(),
                    "enable_summarization": self.enable_summarization.isChecked(),
                    "ai_provider": self.ocr_ai_provider.currentText()
                }
            elif assignment_type == "Folder of Files - Text":
                assignment_data = {
                    "type": assignment_type,
                    "name": self.text_assignment_name.text(),
                    "source_folder": self.text_source_folder.text(),
                    "file_pattern": self.text_file_pattern.text(),
                    "enable_summarization": self.text_enable_summarization.isChecked(),
                    "ai_provider": self.text_ai_provider.currentText(),
                    "summary_style": self.text_summary_style.currentText()
                }
            elif assignment_type == "Folder of Files - PDF":
                assignment_data = {
                    "type": assignment_type,
                    "name": self.pdf_assignment_name.text(),
                    "source_folder": self.pdf_source_folder.text(),
                    "file_pattern": self.pdf_file_pattern.text(),
                    "detect_chapters": self.pdf_detect_chapters.isChecked(),
                    "use_ocr": self.pdf_use_ocr.isChecked(),
                    "enable_summarization": self.pdf_enable_summarization.isChecked(),
                    "ai_provider": self.pdf_ai_provider.currentText(),
                    "summary_style": self.pdf_summary_style.currentText()
                }
            else:
                assignment_data = {
                    "type": assignment_type,
                    "name": assignment_name
                }

            # Store assignment data with current index
            current_index = self.queue_list.count()
            self.assignment_data[current_index] = assignment_data

            # Add to queue list
            self.queue_list.addItem(f"{assignment_name} ({assignment_type})")
            self.run_queue_btn.setEnabled(True)
            self.queue_console.append(f"✓ Assignment saved: {assignment_name}")

        # Reset the builder form
        self.reset_builder()

        # Switch to queue tab
        self.auto_tabs.setCurrentIndex(1)

        self.parent.statusBar().showMessage(f"Assignment saved: {assignment_name}")

    def reset_builder(self):
        """Reset the assignment builder"""
        self.assignment_type.setCurrentIndex(0)
        self.assignment_info.clear()
        self.json_view.clear()
        self.folder_tree.clear()

        # Reset OCR config fields if they exist
        if hasattr(self, 'assignment_name'):
            self.assignment_name.clear()
        if hasattr(self, 'source_folder'):
            self.source_folder.clear()

        self.parent.statusBar().showMessage("Assignment builder reset")

    def on_queue_selection_changed(self):
        """Handle queue selection change - enable/disable buttons"""
        has_selection = len(self.queue_list.selectedItems()) > 0
        self.inspect_btn.setEnabled(has_selection)

    def inspect_assignment(self):
        """Load selected assignment into Assignment Builder for inspection/editing"""
        selected_items = self.queue_list.selectedItems()
        if not selected_items:
            return

        # Enter inspect mode
        self.inspect_mode = True
        self.inspected_assignment_index = self.queue_list.row(selected_items[0])

        # Enable Cancel button
        self.cancel_btn.setEnabled(True)

        # Load assignment data
        if hasattr(self, 'assignment_data') and self.inspected_assignment_index in self.assignment_data:
            data = self.assignment_data[self.inspected_assignment_index]

            # Set assignment type first (triggers config panel switch)
            assignment_type = data.get("type", "")
            if assignment_type == "Folder of Files - OCR" or assignment_type == "folder_ocr":
                self.assignment_type.setCurrentText("Folder of Files - OCR")

                # Load OCR-specific fields
                self.assignment_name.setText(data.get("name", ""))
                self.ocr_file_pattern.setText(data.get("file_pattern", "*.png, *.jpg, *.jpeg"))
                self.ocr_preprocess.setChecked(data.get("preprocess", True))
                self.enable_summarization.setChecked(data.get("enable_summarization", True))

                # Set source folder last (this triggers folder tree population)
                source = data.get("source_folder", "")
                if source:
                    self.source_folder.setText(source)

        # Switch to builder tab
        self.auto_tabs.setCurrentIndex(0)

        selected_text = selected_items[0].text()
        self.queue_console.append(f"Inspecting: {selected_text}")
        self.parent.statusBar().showMessage(f"Inspect mode: {selected_text}")

    def cancel_inspect(self):
        """Cancel inspection and return to queue without saving"""
        if not self.inspect_mode:
            return

        self.exit_inspect_mode()

        # Switch back to queue
        self.auto_tabs.setCurrentIndex(1)

        self.queue_console.append("✓ Inspection cancelled")
        self.parent.statusBar().showMessage("Inspection cancelled")

    def exit_inspect_mode(self):
        """Exit inspect mode and reset state"""
        self.inspect_mode = False
        self.inspected_assignment_index = None
        self.cancel_btn.setEnabled(False)

    def clear_execution_log(self):
        """Clear the execution log console"""
        self.queue_console.clear()
        self.parent.statusBar().showMessage("Execution log cleared")

    def clear_queue(self):
        """Clear all items from the queue"""
        if self.queue_list.count() == 0:
            return

        reply = QMessageBox.question(
            self,
            "Clear Queue",
            "Are you sure you want to clear all assignments from the queue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.queue_list.clear()
            self.assignment_data.clear()
            self.run_queue_btn.setEnabled(False)
            self.queue_console.append("✓ Queue cleared")
            self.parent.statusBar().showMessage("Queue cleared")

    def browse_output_folder(self):
        """Browse for output folder"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Output Folder",
            self.queue_output_folder.text() or ""
        )

        if folder:
            self.queue_output_folder.setText(folder)
            self.parent.statusBar().showMessage(f"Output folder: {folder}")

    def run_queue(self):
        """Execute all assignments in the queue using background thread"""
        # Validate output folder
        output_folder = self.queue_output_folder.text()
        if not output_folder:
            QMessageBox.warning(
                self,
                "No Output Folder",
                "Please select an output folder before running the queue."
            )
            return

        if not Path(output_folder).exists():
            QMessageBox.warning(
                self,
                "Invalid Folder",
                f"Output folder does not exist:\n{output_folder}"
            )
            return

        # Disable/enable buttons
        self.run_queue_btn.setEnabled(False)
        self.pause_queue_btn.setEnabled(True)

        # Create and start worker thread
        assignments_list = [self.queue_list.item(i).text() for i in range(self.queue_list.count())]

        self.worker_thread = QueueProcessorThread(
            assignments_list,
            self.assignment_data,
            output_folder,
            database_path=self.database_path
        )

        # Connect signals
        self.worker_thread.log_signal.connect(self.append_to_log)
        self.worker_thread.finished_signal.connect(self.on_queue_finished)
        self.worker_thread.cost_update_signal.connect(self.update_realtime_analytics)

        # Start processing
        self.worker_thread.start()

    def append_to_log(self, message):
        """Append message to log (called from thread via signal)"""
        self.queue_console.append(message)

    def on_queue_finished(self):
        """Handle queue completion"""
        self.run_queue_btn.setEnabled(True)
        self.pause_queue_btn.setEnabled(False)
        self.parent.statusBar().showMessage("Queue processing complete")

        # Refresh analytics to show final data
        self.refresh_analytics()

    def set_database_path(self, db_path: str):
        """Set the database path for cost tracking (called by project selector)"""
        self.database_path = db_path

        # Refresh analytics to load data from new database
        if hasattr(self, 'refresh_analytics'):
            self.refresh_analytics()

    def get_database_path(self):
        """Get current database path"""
        return self.database_path


class MetadataDialog(QWidget):
    """Dialog for adding/editing metadata for assignments or files"""

    def __init__(self, parent, item_name, item_type="file"):
        # Create as QDialog instead of QWidget
        self.dialog = QDialog(parent)
        self.dialog.setWindowTitle("Add/Edit Metadata")
        self.dialog.setModal(True)
        self.dialog.setMinimumWidth(500)

        self.item_name = item_name
        self.item_type = item_type
        self.metadata = {}

        self.init_ui()

    def init_ui(self):
        """Initialize the metadata dialog UI"""
        layout = QVBoxLayout(self.dialog)

        # Header
        type_label = "Folder" if self.item_type == "folder" else "File"
        header = QLabel(f"Add Metadata: {self.item_name} ({type_label})")
        header.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px;")
        layout.addWidget(header)

        # Form layout for metadata fields
        form = QFormLayout()
        form.setContentsMargins(20, 10, 20, 10)
        form.setSpacing(12)

        # Title (display only - not editable to maintain file connection)
        self.title_input = QLineEdit()
        title = Path(self.item_name).stem  # Remove extension
        self.title_input.setText(title)
        self.title_input.setReadOnly(True)
        self.title_input.setStyleSheet("background: #2a2a2a; color: #aaa;")
        form.addRow("Title:", self.title_input)

        # Original Source
        self.source_input = QLineEdit()
        self.source_input.setPlaceholderText("e.g., RAG Implementation Guide")
        form.addRow("Original Source:", self.source_input)

        # Author
        self.author_input = QLineEdit()
        self.author_input.setPlaceholderText("e.g., Jon Holmes")
        form.addRow("Author:", self.author_input)

        # Page Numbers
        self.pages_input = QLineEdit()
        self.pages_input.setPlaceholderText("e.g., 35-45 or 35")
        form.addRow("Page Numbers:", self.pages_input)

        # Priority
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["low", "medium", "high", "critical"])
        self.priority_combo.setCurrentText("medium")
        form.addRow("Priority:", self.priority_combo)

        # Ready for Pipeline
        self.pipeline_ready = QCheckBox()
        form.addRow("Ready for Pipeline:", self.pipeline_ready)

        # Tags
        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("e.g., rag, technical, analysis")
        form.addRow("Tags:", self.tags_input)

        # Notes (multi-line)
        # NOTE: When AI summarization runs, tags and notes will be APPENDED to these values
        # not replaced. This preserves user-entered metadata while adding AI insights.
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Additional notes...")
        self.notes_input.setMaximumHeight(80)
        form.addRow("Notes:", self.notes_input)

        layout.addLayout(form)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.dialog.accept)
        button_box.rejected.connect(self.dialog.reject)
        layout.addWidget(button_box)

    def exec(self):
        """Show dialog and return result"""
        return self.dialog.exec()

    def get_metadata(self):
        """Get metadata from form fields"""
        return {
            "title": self.title_input.text(),
            "original_source": self.source_input.text(),
            "author": self.author_input.text(),
            "page_numbers": self.pages_input.text(),
            "priority": self.priority_combo.currentText(),
            "ready_for_pipeline": self.pipeline_ready.isChecked(),
            "tags": self.tags_input.text(),
            "notes": self.notes_input.toPlainText()
        }
