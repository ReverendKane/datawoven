# markdown_import_tab.py
"""
Markdown Import Mode Tab - Import pre-formatted markdown with metadata enhancement
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QGroupBox, QFormLayout, QLineEdit, QMessageBox, QLabel
)
from PySide6.QtCore import Qt
from pathlib import Path
import json
import uuid
from datetime import datetime


class MarkdownImportTab(QWidget):
    """Markdown Import Mode - Import and enhance pre-formatted markdown"""

    def __init__(self, parent, metadata_panel):
        super().__init__(parent)
        self.parent = parent
        self.metadata_panel = metadata_panel

        self.init_ui()

    def init_ui(self):
        """Initialize the markdown import mode interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Instructions
        info_group = QGroupBox("Markdown Import")
        info_layout = QVBoxLayout(info_group)
        info_label = QLabel(
            "Paste markdown content from documentation sites (LangGraph, LangChain, etc.) "
            "that already provide markdown export. No summarization needed—just add metadata and save."
        )
        info_label.setWordWrap(True)
        info_layout.addWidget(info_label)
        layout.addWidget(info_group)

        # Enhancement input
        enhancement_group = QGroupBox("Enhancements")
        enhancement_layout = QFormLayout(enhancement_group)

        # Persistent Tags field
        self.persistent_tags_input = QLineEdit()
        self.persistent_tags_input.setPlaceholderText(
            "Tags that persist across all captures (e.g., agentic, documentation)")
        enhancement_layout.addRow("Persistent Tags:", self.persistent_tags_input)

        # Generate Tags field with button
        generate_tags_layout = QHBoxLayout()
        self.generated_tags_input = QLineEdit()
        self.generated_tags_input.setPlaceholderText("AI-generated tags will appear here...")
        self.generated_tags_input.setReadOnly(True)
        generate_tags_layout.addWidget(self.generated_tags_input)

        self.generate_tags_btn = QPushButton("Generate")
        self.generate_tags_btn.setCursor(Qt.PointingHandCursor)
        self.generate_tags_btn.clicked.connect(self.generate_ai_metadata)
        self.generate_tags_btn.setEnabled(False)
        generate_tags_layout.addWidget(self.generate_tags_btn)

        enhancement_layout.addRow("Generate Tags:", generate_tags_layout)

        layout.addWidget(enhancement_group)

        # Markdown input area
        markdown_group = QGroupBox("Markdown Content")
        markdown_layout = QVBoxLayout(markdown_group)

        self.markdown_input = QTextEdit()
        self.markdown_input.setPlaceholderText("Paste markdown content here...")
        self.markdown_input.setMinimumHeight(300)
        markdown_layout.addWidget(self.markdown_input)

        layout.addWidget(markdown_group)

        # Preview/Save buttons
        button_layout = QHBoxLayout()

        preview_btn = QPushButton("Preview Markdown")
        preview_btn.setCursor(Qt.PointingHandCursor)
        preview_btn.clicked.connect(self.preview_markdown_modal)
        button_layout.addWidget(preview_btn)

        self.save_btn = QPushButton("Save Markdown + Metadata")
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.clicked.connect(self.save_markdown_direct)
        self.save_btn.setEnabled(False)
        button_layout.addWidget(self.save_btn)

        layout.addLayout(button_layout)

        # Enable save button when content is present
        self.markdown_input.textChanged.connect(self.on_markdown_input_changed)

    def on_markdown_input_changed(self):
        """Enable save button when markdown content is present"""
        has_content = bool(self.markdown_input.toPlainText().strip())
        self.save_btn.setEnabled(has_content)
        self.generate_tags_btn.setEnabled(has_content)

    def generate_ai_metadata(self):
        """Generate tags and notes using AI"""
        import os
        from dotenv import load_dotenv

        markdown_content = self.markdown_input.toPlainText().strip()

        if not markdown_content:
            QMessageBox.warning(self, "No Content", "Please paste markdown content first.")
            return

        # Check for OpenAI API key
        load_dotenv()
        if not os.getenv('OPENAI_API_KEY'):
            QMessageBox.warning(
                self,
                "API Key Missing",
                "OpenAI API key not found in .env file.\n\n"
                "Please add: OPENAI_API_KEY=your_key_here"
            )
            return

        # Disable button and show progress
        self.generate_tags_btn.setEnabled(False)
        self.generate_tags_btn.setText("Generating...")
        self.parent.statusBar().showMessage("Generating AI metadata...")

        # Get AIMetadataGenerator from parent
        AIMetadataGenerator = self.parent.AIMetadataGenerator

        # Start AI generation thread
        self.ai_metadata_thread = AIMetadataGenerator(markdown_content)
        self.ai_metadata_thread.generation_completed.connect(self.handle_ai_metadata_result)
        self.ai_metadata_thread.generation_failed.connect(self.handle_ai_metadata_error)
        self.ai_metadata_thread.start()

    def handle_ai_metadata_result(self, result):
        """Handle AI metadata generation completion"""
        self.generate_tags_btn.setEnabled(True)
        self.generate_tags_btn.setText("Generate")

        # Get persistent tags
        persistent_tags_text = self.persistent_tags_input.text().strip()
        if persistent_tags_text:
            persistent_tags = set(tag.strip().lower() for tag in persistent_tags_text.split(',') if tag.strip())
        else:
            persistent_tags = set()

        # Get generated tags
        generated_tags = set(result.get("tags", []))

        # Combine with persistent tags first, then generated
        all_tags = sorted(persistent_tags) + sorted(generated_tags - persistent_tags)

        # Update the generated tags display field
        self.generated_tags_input.setText(", ".join(sorted(generated_tags)))

        # Update the metadata panel tags field with combined tags
        self.metadata_panel.tags_input.setText(", ".join(all_tags))

        # Update notes in metadata panel
        notes = result.get("notes", "")
        self.metadata_panel.notes_input.setPlainText(notes)

        self.parent.statusBar().showMessage("AI metadata generated successfully")

        QMessageBox.information(
            self,
            "Metadata Generated",
            f"Generated {len(generated_tags)} tags and summary notes.\n\n"
            f"Tags have been added to the metadata panel.\n"
            f"Review and modify as needed before saving."
        )

    def handle_ai_metadata_error(self, error):
        """Handle AI metadata generation error"""
        self.generate_tags_btn.setEnabled(True)
        self.generate_tags_btn.setText("Generate")
        self.parent.statusBar().showMessage("AI generation failed")

        QMessageBox.warning(
            self,
            "Generation Error",
            f"Failed to generate metadata:\n\n{error}"
        )

    def preview_markdown_modal(self):
        """Show markdown preview in modal dialog using MarkdownDialog"""
        from markdown_dialog import MarkdownDialog

        content = self.markdown_input.toPlainText()

        if not content.strip():
            QMessageBox.information(self, "No Content", "Please paste markdown content first.")
            return

        try:
            # Test if markdown library is available
            try:
                import markdown
                print("✓ markdown library loaded")
            except ImportError as e:
                QMessageBox.warning(self, "Missing Library",
                                    f"markdown library not found:\n{e}\n\nInstall with: pip install markdown")
                return

            # Get title from metadata panel or use default
            title = self.metadata_panel.title_input.text().strip()
            if not title:
                title = "Markdown Preview"

            print(f"✓ About to show modal with title: {title}")
            print(f"✓ Content length: {len(content)} characters")

            # Show the modal with the markdown content
            result = MarkdownDialog.show_modal(self, content, title)

            print(f"✓ Modal returned with result code: {result}")

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"ERROR: {error_details}")
            QMessageBox.critical(
                self,
                "Preview Error",
                f"Failed to show markdown preview:\n\n{str(e)}\n\nFull traceback:\n{error_details}"
            )

    def save_markdown_direct(self):
        """Save markdown content directly without processing"""
        from markdown_dialog import clean_markdown

        content = self.markdown_input.toPlainText()

        if not content:
            return

        # Get URL from metadata panel's original_source field
        url = self.metadata_panel.original_source.text().strip()

        if not url:
            reply = QMessageBox.question(
                self,
                "No Source URL",
                "No source URL provided in either Source URL or Original Source field. Continue saving without URL?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        # Clean the markdown before saving
        cleaned_content = clean_markdown(content)
        print(f"✓ Markdown cleaned for saving")

        # Get metadata from panel
        metadata = self.metadata_panel.get_metadata(
            'markdown',
            "markdown_import_direct",
            "none",
            "none"
        )

        metadata["markdown_import"] = True
        metadata["source_url"] = url
        metadata["cleaned"] = True

        self.metadata_panel.print_metadata(metadata)

        # Generate filename
        if metadata.get("title"):
            filename = "".join(c for c in metadata["title"] if c.isalnum() or c in (' ', '-', '_')).rstrip()
            filename = filename.replace(' ', '_')
        else:
            filename = metadata["document_id"][:8]

        output_folder = self.metadata_panel.output_folder.text()
        output_dir = Path(output_folder)
        output_dir.mkdir(parents=True, exist_ok=True)

        md_path = output_dir / f"{filename}.md"
        json_path = output_dir / f"{filename}.json"

        try:
            # Save cleaned markdown
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)

            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            self.metadata_panel.save_as_defaults()

            self.parent.statusBar().showMessage(f"Saved: {md_path} and {json_path}")
            QMessageBox.information(
                self,
                "Saved",
                f"Cleaned markdown saved to:\n{md_path}\n\nMetadata saved to:\n{json_path}"
            )

            self.markdown_input.clear()

        except Exception as e:
            QMessageBox.warning(self, "Save Error", f"Failed to save files: {e}")

    def populate_loaded_content(self):
        """Populate markdown content from loaded document"""
        if hasattr(self.metadata_panel, 'loaded_markdown_content'):
            self.markdown_input.setPlainText(self.metadata_panel.loaded_markdown_content)

            # Clear the temporary storage
            delattr(self.metadata_panel, 'loaded_markdown_content')
            if hasattr(self.metadata_panel, 'loaded_metadata'):
                delattr(self.metadata_panel, 'loaded_metadata')
