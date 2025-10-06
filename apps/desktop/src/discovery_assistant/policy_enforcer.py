"""
Policy Enforcement Utility
Provides centralized governance rule checking for UI components.
"""

from typing import Optional, Dict, Any
from discovery_assistant.policy_utils import normalize_section_key, normalize_field_key
from discovery_assistant.baselogger import logging

_LOGGER = logging.getLogger("DISCOVERY.policy_enforcer")


class PolicyEnforcer:
    """
    Centralized policy governance enforcement.
    Tabs use this to check which fields/sections are enabled, required, etc.
    """

    def __init__(self, policy: Optional[Dict[str, Any]] = None):
        """
        Initialize the enforcer with a policy dict.

        Args:
            policy: The loaded policy dictionary, or None for no enforcement
        """
        self._policy = policy
        self._sections = policy.get('data', {}).get('sections', {}) if policy else {}

    def has_policy(self) -> bool:
        """Check if a policy is loaded"""
        return self._policy is not None

    def is_section_enabled(self, section_name: str) -> bool:
        """
        Check if a section is enabled.

        Args:
            section_name: Display name of the section (e.g., "Respondent Info")

        Returns:
            True if enabled or not in policy, False if explicitly disabled
        """
        if not self.has_policy():
            return True

        section_key = normalize_section_key(section_name)

        if section_key not in self._sections:
            return True  # Not in policy = enabled by default

        return self._sections[section_key].get('enabled', True)

    def is_field_enabled(self, section_name: str, field_name: str) -> bool:
        """
        Check if a specific field is enabled.

        Args:
            section_name: Display name of the section
            field_name: Display name or key of the field

        Returns:
            True if enabled or not in policy, False if explicitly disabled
        """
        if not self.has_policy():
            return True

        section_key = normalize_section_key(section_name)
        field_key = normalize_field_key(field_name)

        # Get section config
        if section_key not in self._sections:
            return True  # Section not in policy

        section_config = self._sections[section_key]

        # Search through all field groups for this field
        field_groups = section_config.get('field_groups', {})
        for group_name, group_config in field_groups.items():
            fields = group_config.get('fields', {})
            if field_key in fields:
                return fields[field_key].get('enabled', True)

        # Field not found in policy = enabled by default
        return True

    def is_field_required(self, section_name: str, field_name: str) -> bool:
        """
        Check if a specific field is required.

        Args:
            section_name: Display name of the section
            field_name: Display name or key of the field

        Returns:
            True if required, False otherwise
        """
        if not self.has_policy():
            return False

        section_key = normalize_section_key(section_name)
        field_key = normalize_field_key(field_name)

        if section_key not in self._sections:
            return False

        section_config = self._sections[section_key]
        field_groups = section_config.get('field_groups', {})

        for group_name, group_config in field_groups.items():
            fields = group_config.get('fields', {})
            if field_key in fields:
                return fields[field_key].get('required', False)

        return False

    def get_field_display_name(self, section_name: str, field_name: str) -> Optional[str]:
        """
        Get the display name for a field from the policy.

        Args:
            section_name: Display name of the section
            field_name: Field key

        Returns:
            Display name from policy, or None if not found
        """
        if not self.has_policy():
            return None

        section_key = normalize_section_key(section_name)
        field_key = normalize_field_key(field_name)

        if section_key not in self._sections:
            return None

        section_config = self._sections[section_key]
        field_groups = section_config.get('field_groups', {})

        for group_name, group_config in field_groups.items():
            fields = group_config.get('fields', {})
            if field_key in fields:
                return fields[field_key].get('display_name')

        return None
