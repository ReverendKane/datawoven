# post_processing_tab.py
"""
Post-Processing Tab - Validate and sync processed documents to S3
"""
import logging
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json
import hashlib

from dotenv import load_dotenv

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QLineEdit, QComboBox, QProgressBar, QCheckBox,
    QTextEdit, QFileDialog, QMessageBox, QSplitter, QListWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# AWS SDK
try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError

    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

# Load environment variables
load_dotenv()

_LOGGER = logging.getLogger(__name__)


@dataclass
class ProcessingStats:
    """Statistics for processing operation"""
    total: int = 0
    valid: int = 0
    invalid: int = 0
    duplicates: int = 0
    uploaded: int = 0
    skipped: int = 0
    failed: int = 0


@dataclass
class ValidationResult:
    """Result from document validation"""
    valid: bool
    errors: List[str]
    warnings: List[str]
    file_path: Path
    metadata: Optional[Dict] = None
    content_hash: str = ""


class PostProcessingTab(QWidget):
    """Post-Processing Tab - Validate and sync documents to S3"""

    def __init__(self, parent, shared_components, metadata_panel):
        super().__init__(parent)
        self.parent = parent
        self.shared_components = shared_components
        self.metadata_panel = metadata_panel

        # State tracking
        self.source_files: List[Path] = []
        self.validation_results: List[ValidationResult] = []
        self.processing_stats = ProcessingStats()
        self.is_validated = False

        self.init_ui()

    def init_ui(self):
        """Initialize the post-processing interface"""
        layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # Left panel - Configuration
        left_panel = self.create_config_panel()
        splitter.addWidget(left_panel)

        # Right panel - Results and Processing
        right_panel = self.create_results_panel()
        splitter.addWidget(right_panel)

        splitter.setSizes([450, 950])

    def create_config_panel(self):
        """Create the configuration panel (left side)"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Info section
        info_group = QGroupBox("Post-Processing")
        info_layout = QVBoxLayout(info_group)
        info_label = QLabel(
            "Validate and sync your processed documents to Amazon S3 for RAG ingestion."
        )
        info_label.setWordWrap(True)
        info_layout.addWidget(info_label)
        layout.addWidget(info_group)

        # Source Configuration
        source_group = self.create_source_config_group()
        layout.addWidget(source_group)

        # S3 Configuration
        s3_group = self.create_s3_config_group()
        layout.addWidget(s3_group)

        # Action buttons
        button_layout = QVBoxLayout()

        self.scan_btn = QPushButton("Scan Source")
        self.scan_btn.setCursor(Qt.PointingHandCursor)
        self.scan_btn.setFixedHeight(40)
        self.scan_btn.clicked.connect(self.scan_source_folder)
        button_layout.addWidget(self.scan_btn)

        self.validate_btn = QPushButton("Validate Files")
        self.validate_btn.setCursor(Qt.PointingHandCursor)
        self.validate_btn.setFixedHeight(40)
        self.validate_btn.clicked.connect(self.validate_documents)
        self.validate_btn.setEnabled(False)
        button_layout.addWidget(self.validate_btn)

        self.sync_btn = QPushButton("Sync to S3")
        self.sync_btn.setCursor(Qt.PointingHandCursor)
        self.sync_btn.setFixedHeight(40)
        self.sync_btn.clicked.connect(self.sync_to_s3)
        self.sync_btn.setEnabled(False)
        button_layout.addWidget(self.sync_btn)

        layout.addLayout(button_layout)
        layout.addStretch()

        return panel

    def create_source_config_group(self):
        """Create source configuration group"""
        group = QGroupBox("Source Configuration")
        layout = QVBoxLayout(group)

        # Source folder
        folder_layout = QHBoxLayout()
        self.source_folder_input = QLineEdit()
        self.source_folder_input.setPlaceholderText("Select folder containing processed .md + .json files...")
        self.source_folder_input.setReadOnly(True)
        folder_layout.addWidget(self.source_folder_input)

        browse_btn = QPushButton("Browse")
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.clicked.connect(self.browse_source_folder)
        folder_layout.addWidget(browse_btn)
        layout.addLayout(folder_layout)

        # File pattern and recursive search
        options_layout = QHBoxLayout()

        pattern_layout = QHBoxLayout()
        pattern_layout.addWidget(QLabel("Pattern:"))
        self.file_pattern_input = QLineEdit("*.md")
        self.file_pattern_input.setMaximumWidth(80)
        pattern_layout.addWidget(self.file_pattern_input)
        options_layout.addLayout(pattern_layout)

        self.recursive_checkbox = QCheckBox("Recursive")
        self.recursive_checkbox.setChecked(True)
        options_layout.addWidget(self.recursive_checkbox)

        options_layout.addStretch()
        layout.addLayout(options_layout)

        # Files found label
        self.files_found_label = QLabel("Files found: 0")
        font = QFont()
        font.setBold(True)
        self.files_found_label.setFont(font)
        layout.addWidget(self.files_found_label)

        return group

    def create_s3_config_group(self):
        """Create S3 configuration group"""
        group = QGroupBox("S3 Configuration")
        layout = QVBoxLayout(group)

        # Client Name (required)
        client_layout = QHBoxLayout()
        client_layout.addWidget(QLabel("Client Name:"))
        self.client_name_input = QLineEdit()
        self.client_name_input.setPlaceholderText("e.g., datawoven, acme-corp, client-name")
        self.client_name_input.textChanged.connect(self.on_client_name_changed)
        client_layout.addWidget(self.client_name_input)
        layout.addLayout(client_layout)

        # S3 Path preview
        self.s3_path_label = QLabel("S3 Path: (enter client name)")
        self.s3_path_label.setWordWrap(True)
        self.s3_path_label.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(self.s3_path_label)

        return group

    def create_results_panel(self):
        """Create results and processing panel (right side)"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Validation Results
        results_group = QGroupBox("Validation Results")
        results_layout = QVBoxLayout(results_group)

        # Stats display
        stats_layout = QHBoxLayout()
        self.total_label = QLabel("Total: 0")
        self.valid_label = QLabel("Valid: 0")
        self.invalid_label = QLabel("Invalid: 0")
        self.duplicates_label = QLabel("Duplicates: 0")

        for label in [self.total_label, self.valid_label,
                      self.invalid_label, self.duplicates_label]:
            font = QFont()
            font.setBold(True)
            label.setFont(font)
            stats_layout.addWidget(label)

        stats_layout.addStretch()
        results_layout.addLayout(stats_layout)

        # Validation issues list
        self.validation_output = QListWidget()
        self.validation_output.setMaximumHeight(150)
        results_layout.addWidget(self.validation_output)

        layout.addWidget(results_group)

        # Processing Log
        log_group = QGroupBox("Processing Log")
        log_layout = QVBoxLayout(log_group)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        log_layout.addWidget(self.progress_bar)

        # Current file label
        self.current_file_label = QLabel("")
        self.current_file_label.setVisible(False)
        log_layout.addWidget(self.current_file_label)

        # Log output
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        log_layout.addWidget(self.log_output)

        layout.addWidget(log_group)

        return panel

    # ==================== Event Handlers ====================

    def browse_source_folder(self):
        """Open folder dialog for source selection"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Source Folder",
            "",
            QFileDialog.ShowDirsOnly
        )
        if folder:
            self.source_folder_input.setText(folder)
            # Reset validation state
            self.is_validated = False
            self.validate_btn.setEnabled(False)
            self.sync_btn.setEnabled(False)

    def on_client_name_changed(self):
        """Update S3 path preview when client name changes"""
        client_name = self.client_name_input.text().strip()
        if client_name:
            bucket = os.getenv('AWS_S3_BUCKET', 'datawoven-storage')
            self.s3_path_label.setText(
                f"S3 Path: s3://{bucket}/{client_name}/processed/ and .../metadata/"
            )
        else:
            self.s3_path_label.setText("S3 Path: (enter client name)")

        # Update sync button state
        self.update_sync_button_state()

    def update_sync_button_state(self):
        """Update sync button enabled state based on validation and client name"""
        has_client_name = bool(self.client_name_input.text().strip())
        has_valid_files = self.processing_stats.valid > 0

        self.sync_btn.setEnabled(
            self.is_validated and
            has_client_name and
            has_valid_files
        )

    def scan_source_folder(self):
        """Scan source folder for .md files"""
        source_path = Path(self.source_folder_input.text())

        if not source_path.exists():
            QMessageBox.warning(self, "Invalid Path", "Source folder does not exist.")
            return

        self.log_message(f"Scanning: {source_path}")

        # Reset state
        self.is_validated = False
        self.validation_results.clear()
        self.validation_output.clear()
        self.processing_stats = ProcessingStats()

        try:
            # Find all .md files
            pattern = self.file_pattern_input.text()
            if self.recursive_checkbox.isChecked():
                self.source_files = list(source_path.rglob(pattern))
            else:
                self.source_files = list(source_path.glob(pattern))

            count = len(self.source_files)
            self.files_found_label.setText(f"Files found: {count}")
            self.log_message(f"Found {count} files matching pattern '{pattern}'")

            if count > 0:
                self.validate_btn.setEnabled(True)
                self.sync_btn.setEnabled(False)
            else:
                QMessageBox.information(
                    self,
                    "No Files Found",
                    f"No files matching pattern '{pattern}' were found."
                )
                self.validate_btn.setEnabled(False)
                self.sync_btn.setEnabled(False)

        except Exception as e:
            error_msg = f"Error scanning folder: {str(e)}"
            _LOGGER.error(error_msg, exc_info=True)
            QMessageBox.critical(self, "Scan Error", error_msg)

    def validate_documents(self):
        """Validate all scanned documents"""
        if not self.source_files:
            QMessageBox.warning(self, "No Files", "No files to validate. Please scan source folder first.")
            return

        self.log_message("=" * 50)
        self.log_message("Starting validation...")
        self.log_message("=" * 50)

        self.validation_output.clear()
        self.validation_results.clear()

        valid_count = 0
        invalid_count = 0
        duplicate_count = 0
        seen_hashes = {}

        # Disable buttons during validation
        self.scan_btn.setEnabled(False)
        self.validate_btn.setEnabled(False)

        for md_file in self.source_files:
            result = self.validate_single_document(md_file)
            self.validation_results.append(result)

            if result.valid:
                valid_count += 1

                # Check for duplicates
                if result.content_hash in seen_hashes:
                    duplicate_count += 1
                    msg = f"⚠️ DUPLICATE: {md_file.name} (matches {seen_hashes[result.content_hash]})"
                    self.validation_output.addItem(msg)
                    result.warnings.append(f"Duplicate of {seen_hashes[result.content_hash]}")
                    self.log_message(f"  {msg}")
                else:
                    seen_hashes[result.content_hash] = md_file.name
            else:
                invalid_count += 1
                msg = f"❌ INVALID: {md_file.name} - {', '.join(result.errors)}"
                self.validation_output.addItem(msg)
                self.log_message(f"  {msg}")

        # Update stats
        self.processing_stats.total = len(self.source_files)
        self.processing_stats.valid = valid_count
        self.processing_stats.invalid = invalid_count
        self.processing_stats.duplicates = duplicate_count

        self.total_label.setText(f"Total: {self.processing_stats.total}")
        self.valid_label.setText(f"Valid: {valid_count}")
        self.invalid_label.setText(f"Invalid: {invalid_count}")
        self.duplicates_label.setText(f"Duplicates: {duplicate_count}")

        self.log_message("=" * 50)
        self.log_message(
            f"Validation complete: {valid_count} valid, {invalid_count} invalid, {duplicate_count} duplicates")
        self.log_message("=" * 50)

        # Mark as validated
        self.is_validated = True

        # Re-enable buttons
        self.scan_btn.setEnabled(True)
        self.validate_btn.setEnabled(True)
        self.update_sync_button_state()

    def validate_single_document(self, md_file: Path) -> ValidationResult:
        """Validate a single document and its metadata"""
        errors = []
        warnings = []
        metadata = None
        content_hash = ""

        try:
            # Check if .md file exists and is not empty
            if not md_file.exists():
                errors.append("File does not exist")
                return ValidationResult(False, errors, warnings, md_file)

            if md_file.stat().st_size == 0:
                errors.append("File is empty")

            # Calculate content hash
            content_hash = self.calculate_content_hash(md_file)

            # Check for corresponding .json file
            json_file = md_file.with_suffix('.json')
            if not json_file.exists():
                errors.append("Missing metadata JSON file")
                return ValidationResult(False, errors, warnings, md_file)

            # Load and validate metadata
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            except json.JSONDecodeError as e:
                errors.append(f"Invalid JSON: {str(e)}")
                return ValidationResult(False, errors, warnings, md_file, metadata)

            # Validate required metadata fields
            required_fields = ['title', 'document_id', 'source_type']
            for field in required_fields:
                if not metadata.get(field):
                    errors.append(f"Missing required field: {field}")

            # Validate markdown content
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if not content.strip():
                        errors.append("Empty markdown content")
            except Exception as e:
                errors.append(f"Cannot read markdown: {str(e)}")

            valid = len(errors) == 0
            return ValidationResult(valid, errors, warnings, md_file, metadata, content_hash)

        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
            return ValidationResult(False, errors, warnings, md_file, metadata, content_hash)

    def calculate_content_hash(self, md_file: Path) -> str:
        """Calculate SHA256 hash of file content"""
        try:
            with open(md_file, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception as e:
            _LOGGER.error(f"Error calculating hash: {e}")
            return ""

    def sync_to_s3(self):
        """Sync validated documents to S3"""
        if not BOTO3_AVAILABLE:
            QMessageBox.critical(
                self,
                "boto3 Not Available",
                "The boto3 library is required for S3 sync.\n\nInstall it with: pip install boto3"
            )
            return

        # Get configuration
        client_name = self.client_name_input.text().strip()
        if not client_name:
            QMessageBox.warning(self, "Missing Client Name", "Please enter a client name.")
            return

        bucket = os.getenv('AWS_S3_BUCKET')
        region = os.getenv('AWS_S3_REGION')
        access_key = os.getenv('AWS_ACCESS_KEY_ID')
        secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')

        if not all([bucket, region, access_key, secret_key]):
            QMessageBox.critical(
                self,
                "Missing AWS Configuration",
                "AWS credentials not found in .env file.\n\n"
                "Required variables:\n"
                "- AWS_S3_BUCKET\n"
                "- AWS_S3_REGION\n"
                "- AWS_ACCESS_KEY_ID\n"
                "- AWS_SECRET_ACCESS_KEY"
            )
            return

        # Confirm with user
        valid_count = self.processing_stats.valid
        reply = QMessageBox.question(
            self,
            "Confirm S3 Sync",
            f"Upload {valid_count} valid documents to S3?\n\n"
            f"Bucket: {bucket}\n"
            f"Client: {client_name}",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # Track sync start time for audit
        import time
        start_time = time.time()

        # Start sync
        self.log_message("\n" + "=" * 50)
        self.log_message("Starting S3 sync...")
        self.log_message(f"Bucket: {bucket}")
        self.log_message(f"Client: {client_name}")
        self.log_message(f"Region: {region}")
        self.log_message("=" * 50)

        # Disable buttons during sync
        self.scan_btn.setEnabled(False)
        self.validate_btn.setEnabled(False)
        self.sync_btn.setEnabled(False)

        # Disable metadata panel
        self.disable_metadata_panel(True)

        # Show progress
        self.progress_bar.setVisible(True)
        self.current_file_label.setVisible(True)

        try:
            # Create S3 client
            s3_client = boto3.client(
                's3',
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region
            )

            # Test connection
            try:
                s3_client.head_bucket(Bucket=bucket)
                self.log_message("✓ Connected to S3")
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == '404':
                    raise Exception(f"S3 bucket '{bucket}' does not exist")
                elif error_code == '403':
                    raise Exception(f"Access denied to bucket '{bucket}'")
                else:
                    raise Exception(f"Error accessing bucket: {str(e)}")

            # Process valid files
            valid_results = [r for r in self.validation_results if r.valid]
            self.progress_bar.setMaximum(len(valid_results))
            self.progress_bar.setValue(0)

            # Load manifest once (single S3 request for all comparisons)
            self.log_message("\nLoading manifest for hash comparison...")
            manifest = self.load_manifest(s3_client, bucket, client_name)

            uploaded_count = 0
            skipped_count = 0
            failed_count = 0
            uploaded_files = []  # Track uploaded files for audit log

            for idx, result in enumerate(valid_results):
                try:
                    self.current_file_label.setText(f"Processing: {result.file_path.name}")
                    self.log_message(f"\n[{idx + 1}/{len(valid_results)}] {result.file_path.name}")

                    # Upload files and update metadata (passes manifest for comparison)
                    uploaded = self.upload_document_to_s3(
                        s3_client,
                        bucket,
                        client_name,
                        result,
                        manifest  # Pass manifest for in-memory hash comparison
                    )

                    if uploaded:
                        uploaded_count += 1
                        self.log_message("  ✓ Uploaded")
                        # Track for audit log
                        metadata = result.metadata or {}
                        uploaded_files.append({
                            "key": f"{client_name}/metadata/{result.file_path.with_suffix('.json').name}",
                            "sha256": metadata.get('raw_sha256', result.content_hash)
                        })
                    else:
                        skipped_count += 1
                        self.log_message("  ⊘ Skipped (unchanged)")

                except Exception as e:
                    failed_count += 1
                    self.log_message(f"  ✗ Failed: {str(e)}")
                    _LOGGER.error(f"Error syncing {result.file_path}: {e}", exc_info=True)

                self.progress_bar.setValue(idx + 1)

            # Calculate duration
            duration = time.time() - start_time

            # Create audit log
            if uploaded_count > 0 or skipped_count > 0:
                self.log_message("\nCreating audit log...")
                self.create_audit_log(
                    s3_client,
                    bucket,
                    client_name,
                    uploaded_files,
                    skipped_count,
                    failed_count,
                    duration
                )

            # Sync complete
            self.log_message("\n" + "=" * 50)
            self.log_message("S3 Sync Complete!")
            self.log_message(f"Uploaded: {uploaded_count}")
            self.log_message(f"Skipped: {skipped_count}")
            self.log_message(f"Failed: {failed_count}")
            self.log_message(f"Duration: {duration:.1f}s")
            self.log_message("=" * 50)

            # Show completion message
            QMessageBox.information(
                self,
                "Sync Complete",
                f"S3 sync completed successfully!\n\n"
                f"Uploaded: {uploaded_count}\n"
                f"Skipped: {skipped_count}\n"
                f"Failed: {failed_count}"
            )

        except Exception as e:
            error_msg = f"S3 sync error: {str(e)}"
            _LOGGER.error(error_msg, exc_info=True)
            QMessageBox.critical(self, "S3 Sync Failed", error_msg)
            self.log_message(f"\n✗ SYNC FAILED: {error_msg}")

        finally:
            # Re-enable UI
            self.progress_bar.setVisible(False)
            self.current_file_label.setVisible(False)
            self.scan_btn.setEnabled(True)
            self.validate_btn.setEnabled(False)  # Must re-validate
            self.sync_btn.setEnabled(False)  # Must re-validate
            self.is_validated = False  # Reset validation state
            self.disable_metadata_panel(False)

    def load_manifest(self, s3_client, bucket: str, client_name: str) -> dict:
        """Load the current manifest from S3, return empty dict if doesn't exist"""
        try:
            manifest_key = f"{client_name}/audit_logs/manifest.json"
            response = s3_client.get_object(Bucket=bucket, Key=manifest_key)
            manifest_data = json.loads(response['Body'].read().decode('utf-8'))
            self.log_message(f"✓ Loaded manifest: {manifest_data.get('total_files', 0)} files tracked")
            return manifest_data.get('manifest', {})
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                self.log_message("  No existing manifest found - will create new one")
                return {}
            else:
                _LOGGER.warning(f"Error loading manifest: {e}")
                self.log_message(f"  ⚠ Could not load manifest, will check files individually")
                return {}
        except Exception as e:
            _LOGGER.error(f"Unexpected error loading manifest: {e}", exc_info=True)
            return {}

    def upload_document_to_s3(self, s3_client, bucket: str, client_name: str,
                              result: ValidationResult, manifest: dict) -> bool:
        """Upload document and metadata to S3 with manifest-based hash comparison.
        Returns True if uploaded, False if skipped (unchanged)"""
        md_file = result.file_path
        json_file = md_file.with_suffix('.json')

        # Construct S3 keys (flat structure, no organization subdirectories)
        md_key = f"{client_name}/processed/{md_file.name}"
        json_key = f"{client_name}/metadata/{json_file.name}"

        # Get local file hash from metadata
        metadata = result.metadata or {}
        local_hash = metadata.get('raw_sha256', result.content_hash)

        # Intelligent sync: Check manifest for existing hash (in-memory, instant)
        s3_hash = manifest.get(json_key, '')

        if local_hash and s3_hash and local_hash == s3_hash:
            # Hashes match - file unchanged, skip upload
            return False

        # File is new or changed - upload it
        # Upload markdown file
        s3_client.upload_file(
            str(md_file),
            bucket,
            md_key,
            ExtraArgs={'ContentType': 'text/markdown'}
        )

        # Update and upload metadata
        self.update_and_upload_metadata(
            s3_client,
            bucket,
            json_file,
            json_key,
            md_key,
            client_name
        )

        return True

    def update_and_upload_metadata(self, s3_client, bucket: str, json_file: Path,
                                   json_key: str, md_key: str, client_name: str):
        """Update metadata with S3 info and upload"""
        try:
            # Load existing metadata
            with open(json_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            # Add S3 storage info
            metadata['s3_storage'] = {
                'bucket': bucket,
                'client': client_name,
                'processed_key': md_key,
                'metadata_key': json_key,
                'last_synced': datetime.now().isoformat(),
                'sync_sha256': metadata.get('raw_sha256', '')
            }

            # Save updated metadata locally
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            # Upload to S3
            s3_client.upload_file(
                str(json_file),
                bucket,
                json_key,
                ExtraArgs={'ContentType': 'application/json'}
            )

        except Exception as e:
            _LOGGER.error(f"Error updating metadata: {e}", exc_info=True)
            # Still upload original metadata
            s3_client.upload_file(
                str(json_file),
                bucket,
                json_key,
                ExtraArgs={'ContentType': 'application/json'}
            )

    def create_audit_log(self, s3_client, bucket: str, client_name: str,
                         uploaded_files: List[Dict], skipped_count: int,
                         failed_count: int, duration: float):
        """Create and upload sync operation audit log"""
        try:
            timestamp = datetime.now()
            sync_id = f"{timestamp.strftime('%Y-%m-%d_%H-%M-%S')}_{hashlib.md5(str(timestamp).encode()).hexdigest()[:8]}"

            # Create operation log
            operation_log = {
                "sync_id": sync_id,
                "client_name": client_name,
                "timestamp": timestamp.isoformat(),
                "duration_seconds": round(duration, 2),
                "summary": {
                    "scanned": len(self.validation_results),
                    "uploaded": len(uploaded_files),
                    "skipped_unchanged": skipped_count,
                    "failed": failed_count
                },
                "uploaded_files": uploaded_files,
                "failed_files": []  # Could be enhanced to track specific failures
            }

            # Upload operation log
            operation_key = f"{client_name}/audit_logs/sync_operations/{sync_id}.json"
            s3_client.put_object(
                Bucket=bucket,
                Key=operation_key,
                Body=json.dumps(operation_log, indent=2),
                ContentType='application/json'
            )

            # Update manifest
            self.update_manifest(s3_client, bucket, client_name, uploaded_files)

            self.log_message(f"  Audit log saved: {operation_key}")

        except Exception as e:
            _LOGGER.error(f"Error creating audit log: {e}", exc_info=True)
            self.log_message(f"  ⚠ Warning: Could not save audit log: {e}")

    def update_manifest(self, s3_client, bucket: str, client_name: str,
                        uploaded_files: List[Dict]):
        """Update or create the current manifest file with all file hashes"""
        try:
            manifest_key = f"{client_name}/audit_logs/manifest.json"

            # Try to load existing manifest
            manifest = {}
            try:
                response = s3_client.get_object(Bucket=bucket, Key=manifest_key)
                manifest = json.loads(response['Body'].read().decode('utf-8'))
            except ClientError:
                # Manifest doesn't exist yet, create new one
                manifest = {
                    "last_updated": datetime.now().isoformat(),
                    "total_files": 0,
                    "manifest": {}
                }

            # Update manifest with newly uploaded files
            for file_info in uploaded_files:
                manifest["manifest"][file_info["key"]] = file_info["sha256"]

            # Update metadata
            manifest["last_updated"] = datetime.now().isoformat()
            manifest["total_files"] = len(manifest["manifest"])

            # Upload updated manifest
            s3_client.put_object(
                Bucket=bucket,
                Key=manifest_key,
                Body=json.dumps(manifest, indent=2),
                ContentType='application/json'
            )

        except Exception as e:
            _LOGGER.error(f"Error updating manifest: {e}", exc_info=True)

    def disable_metadata_panel(self, disabled: bool):
        """Disable/enable metadata panel during processing"""
        if not self.metadata_panel:
            return

        self.metadata_panel.setEnabled(not disabled)
        if disabled:
            self.metadata_panel.setStyleSheet("QWidget { opacity: 0.5; }")
        else:
            self.metadata_panel.setStyleSheet("")

    def log_message(self, message: str):
        """Add message to log output"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_output.append(f"[{timestamp}] {message}")
        _LOGGER.info(message)
