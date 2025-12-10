"""Region configuration and utilities"""

from typing import List, Dict

# Common AWS regions
AWS_REGIONS: Dict[str, str] = {
    "us-east-1": "N. Virginia",
    "us-east-2": "Ohio",
    "us-west-1": "N. California",
    "us-west-2": "Oregon",
    "eu-west-1": "Ireland",
    "eu-west-2": "London",
    "eu-west-3": "Paris",
    "eu-central-1": "Frankfurt",
    "eu-north-1": "Stockholm",
    "ap-southeast-1": "Singapore",
    "ap-southeast-2": "Sydney",
    "ap-northeast-1": "Tokyo",
    "ap-northeast-2": "Seoul",
    "ap-south-1": "Mumbai",
    "ca-central-1": "Canada",
    "sa-east-1": "São Paulo",
    "af-south-1": "Cape Town",
    "me-south-1": "Bahrain",
    "ap-east-1": "Hong Kong",
    "eu-south-1": "Milan",
    "me-central-1": "UAE",
    "ap-southeast-3": "Jakarta",
    "ap-southeast-4": "Melbourne",
    "il-central-1": "Israel",
    "eu-central-2": "Zurich",
    "ap-south-2": "Hyderabad",
    "eu-south-2": "Spain",
    "ap-southeast-5": "Osaka",
    "us-west-3": "Phoenix",
    "us-west-4": "Las Vegas",
    "us-east-3": "Columbus",
    "eu-north-2": "Warsaw",
    "ap-northeast-3": "Osaka",
}

def get_region_list() -> List[tuple[str, str]]:
    """Get list of regions as (code, name) tuples"""
    return [(code, f"{code} ({name})") for code, name in AWS_REGIONS.items()]

def is_valid_region(region: str) -> bool:
    """Check if a region code is valid"""
    return region in AWS_REGIONS

