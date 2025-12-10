"""Free tier eligibility data model"""

from typing import Dict, List, Set

# Free tier eligible instance types
# These are typically available for 750 hours/month for 12 months for new accounts
FREE_TIER_INSTANCES: Set[str] = {
    "t2.micro",
    "t3.micro",
    "t4g.micro",
}

# Region-specific free tier (most regions have the same, but some may differ)
# For now, we'll use a simple set, but this could be expanded to be region-specific
FREE_TIER_DATA: Dict[str, any] = {
    "instance_types": list(FREE_TIER_INSTANCES),
    "hours_per_month": 750,
    "duration_months": 12,
    "notes": "Free tier applies to accounts less than 12 months old",
}

def is_free_tier_eligible(instance_type: str) -> bool:
    """Check if an instance type is free tier eligible"""
    return instance_type in FREE_TIER_INSTANCES

def get_free_tier_info() -> Dict[str, any]:
    """Get free tier information"""
    return FREE_TIER_DATA.copy()

