# file_manager.py - Centralized file management for Discovery Assistant

import shutil
import logging
from pathlib import Path
from typing import List, Optional, Set
from datetime import datetime

from discovery_assistant.storage import (
    get_attachments_dir,
    get_screenshots_dir,
    get_files_dir
)

_LOGGER = logging.getLogger("DISCOVERY.file_manager")


class FileManager:
    """Centralized file management for attachments and screenshots"""

    @staticmethod
    def copy_attachment_to_storage(source_path: Path, section: str, item_id: int,
                                   is_screenshot: bool = False) -> Optional[Path]:
        """
        Copy a file to organized storage and return the new path.

        Args:
            source_path: Original file path
            section: Section name (e.g., 'processes', 'feature_ideas')
            item_id: Database ID of the item
            is_screenshot: Whether this is a screenshot

        Returns:
            New file path in organized storage, or None if failed
        """
        try:
            if not source_path.exists():
                _LOGGER.warning(f"Source file does not exist: {source_path}")
                return None

            # Determine target directory
            if is_screenshot:
                target_dir = get_screenshots_dir(section)
            else:
                target_dir = get_attachments_dir(section)

            target_dir.mkdir(parents=True, exist_ok=True)

            # Create unique filename: itemID_timestamp_originalname
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = FileManager._sanitize_filename(source_path.name)
            target_filename = f"{item_id}_{timestamp}_{safe_name}"
            target_path = target_dir / target_filename

            # Copy file
            shutil.copy2(source_path, target_path)
            _LOGGER.info(f"Copied file: {source_path} -> {target_path}")

            return target_path

        except Exception as e:
            _LOGGER.error(f"Failed to copy file {source_path}: {e}")
            return None

    @staticmethod
    def delete_file(file_path: Path) -> bool:
        """
        Safely delete a file from storage.

        Args:
            file_path: Path to file to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            if file_path.exists():
                file_path.unlink()
                _LOGGER.info(f"Deleted file: {file_path}")
                return True
            else:
                _LOGGER.warning(f"File to delete does not exist: {file_path}")
                return False
        except Exception as e:
            _LOGGER.error(f"Failed to delete file {file_path}: {e}")
            return False

    @staticmethod
    def cleanup_section_files(section: str) -> int:
        """
        Clean up all files for a section (used during database reset).

        Args:
            section: Section name to clean up

        Returns:
            Number of files deleted
        """
        deleted_count = 0

        try:
            # Clean up attachments
            attachments_dir = get_attachments_dir(section)
            if attachments_dir.exists():
                for file_path in attachments_dir.iterdir():
                    if file_path.is_file():
                        if FileManager.delete_file(file_path):
                            deleted_count += 1

            # Clean up screenshots
            screenshots_dir = get_screenshots_dir(section)
            if screenshots_dir.exists():
                for file_path in screenshots_dir.iterdir():
                    if file_path.is_file():
                        if FileManager.delete_file(file_path):
                            deleted_count += 1

            _LOGGER.info(f"Cleaned up {deleted_count} files from section '{section}'")

        except Exception as e:
            _LOGGER.error(f"Error cleaning up section '{section}': {e}")

        return deleted_count

    @staticmethod
    def cleanup_all_files() -> int:
        """
        Clean up all files (used during complete database reset).

        Returns:
            Total number of files deleted
        """
        sections = ['processes', 'feature_ideas', 'reference_library', 'pain_points', 'data_sources', 'compliance']
        total_deleted = 0

        for section in sections:
            total_deleted += FileManager.cleanup_section_files(section)

        _LOGGER.info(f"Total files cleaned up: {total_deleted}")
        return total_deleted

    @staticmethod
    def validate_file_exists(file_path: Path) -> bool:
        """
        Check if a file exists and is accessible.

        Args:
            file_path: Path to validate

        Returns:
            True if file exists and is accessible
        """
        try:
            return file_path.exists() and file_path.is_file()
        except Exception as e:
            _LOGGER.warning(f"Error validating file {file_path}: {e}")
            return False

    @staticmethod
    def get_missing_files(file_paths: List[Path]) -> List[Path]:
        """
        Get list of files that are missing or inaccessible.

        Args:
            file_paths: List of file paths to check

        Returns:
            List of missing file paths
        """
        missing = []
        for path in file_paths:
            if not FileManager.validate_file_exists(path):
                missing.append(path)
        return missing

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """
        Sanitize a filename to be safe for filesystem storage.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        # Remove or replace problematic characters
        import re
        # Replace problematic chars with underscores
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Remove any remaining control characters
        sanitized = re.sub(r'[\x00-\x1f\x7f]', '', sanitized)
        # Limit length
        if len(sanitized) > 200:
            name, ext = Path(sanitized).stem, Path(sanitized).suffix
            sanitized = name[:200 - len(ext)] + ext
        return sanitized

    @staticmethod
    def get_storage_stats() -> dict:
        """
        Get statistics about file storage usage.

        Returns:
            Dictionary with storage statistics
        """
        stats = {
            'total_files': 0,
            'total_size_bytes': 0,
            'sections': {}
        }

        try:
            base_dir = get_files_dir()
            if not base_dir.exists():
                return stats

            for section_dir in base_dir.iterdir():
                if section_dir.is_dir():
                    section_stats = {
                        'attachments': 0,
                        'screenshots': 0,
                        'size_bytes': 0
                    }

                    for file_path in section_dir.rglob('*'):
                        if file_path.is_file():
                            try:
                                size = file_path.stat().st_size
                                section_stats['size_bytes'] += size
                                stats['total_size_bytes'] += size
                                stats['total_files'] += 1

                                if 'screenshots' in str(file_path.parent):
                                    section_stats['screenshots'] += 1
                                else:
                                    section_stats['attachments'] += 1
                            except Exception:
                                pass

                    stats['sections'][section_dir.name] = section_stats

        except Exception as e:
            _LOGGER.error(f"Error getting storage stats: {e}")

        return stats


# Integration methods for tabs

def integrate_file_management_to_tab(tab_class_name: str):
    """
    Add file management methods to a tab class.
    This would be mixed into existing tab classes.
    """

    def copy_attachments_to_storage(self, item_id: int, attachments: List) -> List:
        """Copy attachments to organized storage and return updated attachment list"""
        section = self._get_section_name()  # Each tab implements this
        updated_attachments = []

        for attachment in attachments:
            if not FileManager.validate_file_exists(attachment.file_path):
                _LOGGER.warning(f"Skipping missing file: {attachment.file_path}")
                continue

            # Check if file is already in our storage (avoid double-copying)
            if self._is_file_in_storage(attachment.file_path):
                updated_attachments.append(attachment)
                continue

            # Copy to storage
            new_path = FileManager.copy_attachment_to_storage(
                attachment.file_path,
                section,
                item_id,
                attachment.is_screenshot
            )

            if new_path:
                # Update attachment with new path
                attachment.file_path = new_path
                updated_attachments.append(attachment)
            else:
                _LOGGER.error(f"Failed to copy attachment: {attachment.file_path}")

        return updated_attachments

    def cleanup_item_files(self, attachments: List) -> None:
        """Clean up files when an item is deleted"""
        for attachment in attachments:
            if self._is_file_in_storage(attachment.file_path):
                FileManager.delete_file(attachment.file_path)

    def _is_file_in_storage(self, file_path: Path) -> bool:
        """Check if a file is in our organized storage directory"""
        try:
            files_dir = get_files_dir()
            return files_dir in file_path.parents
        except Exception:
            return False

    def _get_section_name(self) -> str:
        """Return the section name for this tab - implemented by each tab"""
        raise NotImplementedError("Each tab must implement _get_section_name()")


# Menu integration for main window

def add_files_menu_to_main_window():
    """
    Add file management menu items to the main window.
    This should be integrated into main_window.py
    """

    # Add to menu creation in MainWindow._make_actions():

    def _show_files_directory(self):
        """Open the files directory with a warning dialog"""
        from PySide6.QtWidgets import QMessageBox
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl

        # Show warning first
        reply = QMessageBox.warning(
            self,
            "Files Directory Access",
            "You are about to open the application's file storage directory.\n\n"
            "⚠️ WARNING: Do not modify, move, or delete any files in this directory. "
            "Doing so may cause application instability and data loss.\n\n"
            "This directory is provided for read-only viewing of your attached files.\n\n"
            "Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            files_dir = get_files_dir()
            files_dir.mkdir(parents=True, exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(files_dir)))

    def _show_storage_stats(self):
        """Show storage statistics dialog"""
        from PySide6.QtWidgets import QMessageBox

        stats = FileManager.get_storage_stats()

        # Format file size
        def format_bytes(bytes_val):
            for unit in ['B', 'KB', 'MB', 'GB']:
                if bytes_val < 1024:
                    return f"{bytes_val:.1f} {unit}"
                bytes_val /= 1024
            return f"{bytes_val:.1f} TB"

        message = f"Storage Statistics:\n\n"
        message += f"Total Files: {stats['total_files']}\n"
        message += f"Total Size: {format_bytes(stats['total_size_bytes'])}\n\n"

        for section, section_stats in stats['sections'].items():
            message += f"{section.title()}:\n"
            message += f"  Attachments: {section_stats['attachments']}\n"
            message += f"  Screenshots: {section_stats['screenshots']}\n"
            message += f"  Size: {format_bytes(section_stats['size_bytes'])}\n\n"

        QMessageBox.information(self, "Storage Statistics", message)

    # Add these to the File menu:
    # self.showFilesDirAct = QtGui.QAction("Show &Files Directory...", self)
    # self.showFilesDirAct.triggered.connect(self._show_files_directory)
    #
    # self.showStorageStatsAct = QtGui.QAction("Storage &Statistics...", self)
    # self.showStorageStatsAct.triggered.connect(self._show_storage_stats)


