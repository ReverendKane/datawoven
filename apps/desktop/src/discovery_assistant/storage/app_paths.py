"""
Cross-platform application data directory management.

Handles all user data storage locations for Discovery Assistant including:
- Policy files
- SQLite database
- File attachments and screenshots
"""

import sys
from pathlib import Path

APP_NAME = "Discovery Assistant"


def get_app_data_dir() -> Path:
    """
    Get the base application data directory for the current platform.

    Returns:
        Path: Platform-specific application data directory
            - Windows: ~/AppData/Local/Discovery Assistant/
            - macOS: ~/Library/Application Support/Discovery Assistant/
            - Linux: ~/.discovery_assistant/
    """
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / APP_NAME
    elif sys.platform.startswith("win"):
        base = Path.home() / "AppData" / "Local" / APP_NAME
    else:
        base = Path.home() / f".{APP_NAME.lower().replace(' ', '_')}"

    base.mkdir(parents=True, exist_ok=True)
    return base


def get_policy_dir() -> Path:
    """
    Get the policy file directory.

    Returns:
        Path: Directory where governance.pol is stored
    """
    policy_dir = get_app_data_dir() / "policy"
    policy_dir.mkdir(parents=True, exist_ok=True)
    return policy_dir


def get_policy_path() -> Path:
    """
    Get the full path to the governance.pol file.

    Returns:
        Path: Full path to governance.pol
    """
    return get_policy_dir() / "governance.pol"


def get_database_dir() -> Path:
    """
    Get the database directory.

    Returns:
        Path: Directory where discovery.db and files/ are stored
    """
    return get_app_data_dir()


def get_database_path() -> Path:
    """
    Get the full path to the SQLite database file.

    Returns:
        Path: Full path to discovery.db
    """
    return get_database_dir() / "discovery.db"


def get_files_dir() -> Path:
    """
    Get the base files directory for attachments and screenshots.

    Returns:
        Path: Base files directory
    """
    files_dir = get_database_dir() / "files"
    files_dir.mkdir(parents=True, exist_ok=True)
    return files_dir


def get_section_files_dir(section_name: str) -> Path:
    """
    Get the files directory for a specific section.

    Args:
        section_name: Name of the section (e.g., 'processes', 'pain_points')

    Returns:
        Path: Section-specific files directory
    """
    section_dir = get_files_dir() / section_name
    section_dir.mkdir(parents=True, exist_ok=True)
    return section_dir


def get_attachments_dir(section_name: str) -> Path:
    """
    Get the attachments directory for a specific section.

    Args:
        section_name: Name of the section (e.g., 'processes', 'pain_points')

    Returns:
        Path: Section-specific attachments directory
    """
    attachments_dir = get_section_files_dir(section_name) / "attachments"
    attachments_dir.mkdir(parents=True, exist_ok=True)
    return attachments_dir


def get_screenshots_dir(section_name: str) -> Path:
    """
    Get the screenshots directory for a specific section.

    Args:
        section_name: Name of the section (e.g., 'processes', 'pain_points')

    Returns:
        Path: Section-specific screenshots directory
    """
    screenshots_dir = get_section_files_dir(section_name) / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    return screenshots_dir


def initialize_file_structure() -> None:
    """
    Initialize the complete file structure for Discovery Assistant.
    Creates all necessary directories if they don't exist.
    """
    # Ensure base app directory exists
    get_app_data_dir()

    # Ensure policy directory exists
    get_policy_dir()

    # Ensure files base directory exists
    get_files_dir()

    # Create all section directories
    sections = [
        "processes",
        "pain_points",
        "data_sources",
        "compliance",
        "feature_ideas",
        "reference_library"
    ]

    for section in sections:
        get_attachments_dir(section)
        get_screenshots_dir(section)
