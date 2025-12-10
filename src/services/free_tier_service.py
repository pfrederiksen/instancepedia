"""Free tier eligibility service"""

from src.models.free_tier import is_free_tier_eligible, get_free_tier_info


class FreeTierService:
    """Service for checking free tier eligibility"""

    @staticmethod
    def is_eligible(instance_type: str) -> bool:
        """Check if instance type is free tier eligible"""
        return is_free_tier_eligible(instance_type)

    @staticmethod
    def get_info() -> dict:
        """Get free tier information"""
        return get_free_tier_info()

