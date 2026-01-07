"""Instance metadata service for deprecation and new instance tracking"""

from typing import Optional, Dict, Set, List
import re


class InstanceMetadata:
    """Metadata about instance lifecycle status"""

    # Instances that AWS has announced deprecation/retirement for
    # Format: instance_family -> (status, optional_retirement_date, message)
    DEPRECATED_INSTANCES: Dict[str, tuple] = {
        # Very old generations - officially deprecated
        "m1": ("deprecated", "2024-01-31", "Deprecated - migrate to M5 or M6i family"),
        "m2": ("deprecated", "2024-01-31", "Deprecated - migrate to R5 or R6i family"),
        "c1": ("deprecated", "2024-01-31", "Deprecated - migrate to C5 or C6i family"),
        "cc2": ("deprecated", "2024-01-31", "Deprecated - migrate to C5 or C6i family"),
        "cr1": ("deprecated", "2024-01-31", "Deprecated - migrate to R5 or R6i family"),
        "t1": ("deprecated", "2024-01-31", "Deprecated - migrate to T3 or T4g family"),
        "m3": ("deprecated", "2024-12-31", "Deprecated - migrate to M5 or M6i family"),
        "c3": ("deprecated", "2024-12-31", "Deprecated - migrate to C5 or C6i family"),
        "r3": ("deprecated", "2024-12-31", "Deprecated - migrate to R5 or R6i family"),
        "i2": ("deprecated", "2024-12-31", "Deprecated - migrate to I3 or I4i family"),
        "hs1": ("deprecated", "2024-01-31", "Deprecated - migrate to D2 or D3 family"),
        "g2": ("deprecated", "2024-12-31", "Deprecated - migrate to G4 or G5 family"),
    }

    @staticmethod
    def get_instance_family(instance_type: str) -> str:
        """Extract family from instance type (e.g., 't3.micro' -> 't3')"""
        # Handle special cases like 'm7i-flex'
        parts = instance_type.split('.')
        if len(parts) >= 1:
            family = parts[0]
            # Handle flex variants
            if '-' in family:
                return family  # Return full family like 'm7i-flex'
            return family
        return instance_type

    @staticmethod
    def is_deprecated(instance_type: str) -> bool:
        """Check if instance is deprecated"""
        family = InstanceMetadata.get_instance_family(instance_type)
        return family in InstanceMetadata.DEPRECATED_INSTANCES

    @staticmethod
    def get_deprecation_info(instance_type: str) -> Optional[tuple]:
        """Get deprecation info (status, retirement_date, message)"""
        family = InstanceMetadata.get_instance_family(instance_type)
        return InstanceMetadata.DEPRECATED_INSTANCES.get(family)

    @staticmethod
    def is_new(instance_type: str) -> bool:
        """Check if instance was launched recently (within 12 months)"""
        family = InstanceMetadata.get_instance_family(instance_type)
        return family in InstanceMetadata.NEW_INSTANCES

    @staticmethod
    def get_new_instance_info(instance_type: str) -> Optional[tuple]:
        """Get new instance info (launch_date, description)"""
        family = InstanceMetadata.get_instance_family(instance_type)
        return InstanceMetadata.NEW_INSTANCES.get(family)

    @staticmethod
    def get_status_badge(instance_type: str, current_generation: bool = True) -> str:
        """Get status badge for display (emoji or text)"""
        badges = []

        # Check for deprecation first (highest priority)
        if InstanceMetadata.is_deprecated(instance_type):
            badges.append("⚠️")
        # Then check for new instances
        elif InstanceMetadata.is_new(instance_type):
            badges.append("🆕")
        # Show previous generation indicator if not current
        elif not current_generation:
            badges.append("📦")  # Previous generation box

        return " ".join(badges) if badges else ""

    @staticmethod
    def get_status_text(instance_type: str, current_generation: bool = True) -> str:
        """Get status text for CLI display"""
        if InstanceMetadata.is_deprecated(instance_type):
            return "DEPRECATED"
        elif InstanceMetadata.is_new(instance_type):
            return "NEW"
        elif not current_generation:
            return "PREV-GEN"
        return ""
