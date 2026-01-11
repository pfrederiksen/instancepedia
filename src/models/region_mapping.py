"""AWS region code to Pricing API location name mappings.

This module provides the canonical mapping between AWS region codes and their
corresponding Pricing API location names. This mapping is used by both the
synchronous and asynchronous pricing services.
"""

# Map AWS region codes to Pricing API location names
REGION_MAP = {
    'us-east-1': 'US East (N. Virginia)',
    'us-east-2': 'US East (Ohio)',
    'us-east-3': 'US East (Columbus)',
    'us-west-1': 'US West (N. California)',
    'us-west-2': 'US West (Oregon)',
    'us-west-3': 'US West (Phoenix)',
    'us-west-4': 'US West (Las Vegas)',
    'af-south-1': 'Africa (Cape Town)',
    'ap-east-1': 'Asia Pacific (Hong Kong)',
    'ap-south-1': 'Asia Pacific (Mumbai)',
    'ap-south-2': 'Asia Pacific (Hyderabad)',
    'ap-northeast-1': 'Asia Pacific (Tokyo)',
    'ap-northeast-2': 'Asia Pacific (Seoul)',
    'ap-northeast-3': 'Asia Pacific (Osaka)',
    'ap-southeast-1': 'Asia Pacific (Singapore)',
    'ap-southeast-2': 'Asia Pacific (Sydney)',
    'ap-southeast-3': 'Asia Pacific (Jakarta)',
    'ap-southeast-4': 'Asia Pacific (Melbourne)',
    'ap-southeast-5': 'Asia Pacific (Osaka)',
    'ca-central-1': 'Canada (Central)',
    'eu-central-1': 'EU (Frankfurt)',
    'eu-central-2': 'EU (Zurich)',
    'eu-west-1': 'EU (Ireland)',
    'eu-west-2': 'EU (London)',
    'eu-west-3': 'EU (Paris)',
    'eu-north-1': 'EU (Stockholm)',
    'eu-north-2': 'EU (Warsaw)',
    'eu-south-1': 'EU (Milan)',
    'eu-south-2': 'EU (Spain)',
    'me-south-1': 'Middle East (Bahrain)',
    'me-central-1': 'Middle East (UAE)',
    'il-central-1': 'Israel (Tel Aviv)',
    'sa-east-1': 'South America (Sao Paulo)',
}


def get_pricing_region(region_code: str) -> str:
    """Get Pricing API location name for an AWS region code.

    Args:
        region_code: AWS region code (e.g., 'us-east-1')

    Returns:
        Pricing API location name (e.g., 'US East (N. Virginia)')
        Returns the region_code itself if no mapping exists.
    """
    return REGION_MAP.get(region_code, region_code)
