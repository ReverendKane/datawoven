"""
Storage package for Discovery Assistant.

Handles all data persistence including:
- Cross-platform directory management
- SQLAlchemy database operations
- File attachment management
"""

from .app_paths import (
    get_app_data_dir,
    get_policy_dir,
    get_policy_path,
    get_database_dir,
    get_database_path,
    get_files_dir,
    get_section_files_dir,
    get_attachments_dir,
    get_screenshots_dir,
    initialize_file_structure,
)

from .database import (
    initialize_database,
    database_exists,
    get_database_session,
    reset_database,
    test_database_connection,
    DatabaseSession,
    # Models
    Respondent,
    OrgMap,
    Process,
    PainPoint,
    DataSource,
    Compliance,
    ComplianceRequirement,
    FeatureIdea,
    ReferenceDocument,
    TimeAllocation,
    TimeResourceManagement,
)

from .file_manager import FileManager

__all__ = [
    'get_app_data_dir',
    'get_policy_dir',
    'get_policy_path',
    'get_database_dir',
    'get_database_path',
    'get_files_dir',
    'get_section_files_dir',
    'get_attachments_dir',
    'get_screenshots_dir',
    'initialize_file_structure',
    'initialize_database',
    'database_exists',
    'get_database_session',
    'reset_database',
    'test_database_connection',
    'DatabaseSession',
    # Models
    'Respondent',
    'OrgMap',
    'Process',
    'PainPoint',
    'DataSource',
    'Compliance',
    'ComplianceRequirement',
    'FeatureIdea',
    'ReferenceDocument',
    'FileManager',
]
