"""
Utility functions for policy generation and field key normalization.
Ensures consistency between UI component field keys and policy JSON structure.
"""


def normalize_field_key(field_name: str) -> str:
    """
    Convert field display names to consistent policy keys.

    This function ensures that field keys are generated consistently whether
    they're being created in the UI or parsed from display names in the policy builder.

    Examples:
        "Full Name" -> "full_name"
        "Role / Title" -> "role_title"
        "Screenshots/Attachments" -> "screenshots_attachments"
        "Work Email" -> "work_email"

    Args:
        field_name: The human-readable field display name

    Returns:
        Normalized field key suitable for use in policy JSON
    """
    # Replace common separators with underscores
    normalized = field_name.lower()
    normalized = normalized.replace(" / ", "_")
    normalized = normalized.replace("/", "_")
    normalized = normalized.replace(" ", "_")

    # Remove any duplicate underscores that might have been created
    while "__" in normalized:
        normalized = normalized.replace("__", "_")

    # Remove leading/trailing underscores
    normalized = normalized.strip("_")

    return normalized


def normalize_section_key(section_name: str) -> str:
    """
    Convert section display names to consistent policy keys.

    Examples:
        "Respondent Info" -> "respondent_info"
        "Org Map" -> "org_map"
        "Time & Resource Management" -> "time_resource_management"

    Args:
        section_name: The human-readable section display name

    Returns:
        Normalized section key suitable for use in policy JSON
    """
    # Replace special characters and spaces with underscores
    normalized = section_name.lower()
    normalized = normalized.replace(" & ", "_")
    normalized = normalized.replace("&", "_")
    normalized = normalized.replace(" ", "_")

    # Remove any duplicate underscores
    while "__" in normalized:
        normalized = normalized.replace("__", "_")

    # Remove leading/trailing underscores
    normalized = normalized.strip("_")

    return normalized
