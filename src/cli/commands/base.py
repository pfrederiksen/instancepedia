"""Base utilities for CLI commands"""

import logging
import sys
from typing import Optional, List

from src.services.aws_client import AWSClient
from src.services.instance_service import InstanceService
from src.services.pricing_service import PricingService
from src.models.instance_type import InstanceType, PricingInfo
from src.models.region import is_valid_region, AWS_REGIONS

logger = logging.getLogger("instancepedia")


def status(message: str, quiet: bool = False) -> None:
    """Print status message to stderr unless quiet mode is on.

    Args:
        message: Status message to display
        quiet: Whether to suppress the message
    """
    if not quiet:
        print(message, file=sys.stderr)


def progress(completed: int, total: int, item_type: str = "items", quiet: bool = False) -> None:
    """Print progress message to stderr unless quiet mode is on.

    Args:
        completed: Number of items completed
        total: Total number of items
        item_type: Description of items being processed
        quiet: Whether to suppress the message
    """
    if not quiet:
        print(f"Processed {completed}/{total} {item_type}...", file=sys.stderr)


def print_error(message: str, debug: bool = False, exception: Exception = None) -> None:
    """Print error message to stderr with consistent formatting.

    Args:
        message: Error message to display
        debug: Whether to print full traceback
        exception: Optional exception for traceback
    """
    print(f"Error: {message}", file=sys.stderr)
    if debug and exception:
        import traceback
        traceback.print_exc()


def validate_region(region: str, exit_on_error: bool = True) -> bool:
    """Validate an AWS region code.

    Args:
        region: AWS region code to validate (e.g., 'us-east-1')
        exit_on_error: Whether to exit the program on invalid region

    Returns:
        True if valid, False if invalid (only when exit_on_error=False)
    """
    if is_valid_region(region):
        return True

    # Try to find similar region names
    similar = [r for r in AWS_REGIONS.keys() if region in r or r in region]

    error_msg = f"Invalid region '{region}'."
    if similar:
        error_msg += f" Did you mean: {', '.join(similar[:3])}?"
    error_msg += "\nUse 'instancepedia regions' to see available regions."

    if exit_on_error:
        print(f"Error: {error_msg}", file=sys.stderr)
        sys.exit(1)
    return False


def validate_regions(regions: List[str], exit_on_error: bool = True) -> List[str]:
    """Validate multiple AWS region codes.

    Args:
        regions: List of AWS region codes to validate
        exit_on_error: Whether to exit the program on any invalid region

    Returns:
        List of invalid region codes (empty if all valid)
    """
    invalid = [r for r in regions if not is_valid_region(r)]
    if invalid and exit_on_error:
        for r in invalid:
            validate_region(r, exit_on_error=True)
    return invalid


def get_aws_client(region: str, profile: Optional[str] = None) -> AWSClient:
    """Get AWS client with error handling"""
    try:
        return AWSClient(region, profile)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def get_instance_by_name(
    aws_client: AWSClient,
    instance_type: str,
    region: str,
    quiet: bool = False,
    fetch_pricing: bool = False
) -> Optional[InstanceType]:
    """
    Fetch instance types and find one by name.

    Args:
        aws_client: AWS client instance
        instance_type: Instance type name to find (e.g., 't3.micro')
        region: AWS region (for status message)
        quiet: Whether to suppress status messages
        fetch_pricing: Whether to fetch pricing with instances

    Returns:
        InstanceType if found, None otherwise
    """
    status(f"Fetching instance types for region {region}...", quiet)
    instance_service = InstanceService(aws_client)
    instances = instance_service.get_instance_types(fetch_pricing=fetch_pricing)
    return next((inst for inst in instances if inst.instance_type == instance_type), None)


def get_instances_by_names(
    aws_client: AWSClient,
    instance_types: List[str],
    region: str,
    quiet: bool = False
) -> List[Optional[InstanceType]]:
    """
    Fetch instance types and find multiple by name.

    Args:
        aws_client: AWS client instance
        instance_types: List of instance type names to find
        region: AWS region (for status message)
        quiet: Whether to suppress status messages

    Returns:
        List of InstanceTypes (None for any not found), in same order as input
    """
    status(f"Fetching instance types for region {region}...", quiet)
    instance_service = InstanceService(aws_client)
    instances = instance_service.get_instance_types()

    result = []
    for name in instance_types:
        found = next((inst for inst in instances if inst.instance_type == name), None)
        result.append(found)
    return result


def fetch_instance_pricing(
    pricing_service: PricingService,
    instance_type: str,
    region: str,
    include_ri: bool = False
) -> PricingInfo:
    """
    Fetch pricing information for an instance type.

    Args:
        pricing_service: The pricing service to use
        instance_type: Instance type name (e.g., 't3.micro')
        region: AWS region code
        include_ri: Whether to include Reserved Instance pricing (slower)

    Returns:
        PricingInfo with all available pricing data
    """
    on_demand = pricing_service.get_on_demand_price(instance_type, region, max_retries=3)
    spot = pricing_service.get_spot_price(instance_type, region)
    savings_1yr = pricing_service.get_savings_plan_price(instance_type, region, "1yr")
    savings_3yr = pricing_service.get_savings_plan_price(instance_type, region, "3yr")

    pricing = PricingInfo(
        on_demand_price=on_demand,
        spot_price=spot,
        savings_plan_1yr_no_upfront=savings_1yr,
        savings_plan_3yr_no_upfront=savings_3yr
    )

    if include_ri:
        pricing.ri_1yr_no_upfront = pricing_service.get_reserved_instance_price(instance_type, region, "1yr", "no_upfront")
        pricing.ri_1yr_partial_upfront = pricing_service.get_reserved_instance_price(instance_type, region, "1yr", "partial_upfront")
        pricing.ri_1yr_all_upfront = pricing_service.get_reserved_instance_price(instance_type, region, "1yr", "all_upfront")
        pricing.ri_3yr_no_upfront = pricing_service.get_reserved_instance_price(instance_type, region, "3yr", "no_upfront")
        pricing.ri_3yr_partial_upfront = pricing_service.get_reserved_instance_price(instance_type, region, "3yr", "partial_upfront")
        pricing.ri_3yr_all_upfront = pricing_service.get_reserved_instance_price(instance_type, region, "3yr", "all_upfront")

    return pricing


def safe_write_file(
    file_path: str,
    content: str,
    create_dirs: bool = True
) -> None:
    """Safely write content to a file with error handling.

    Args:
        file_path: Path to file to write
        content: Content to write
        create_dirs: Whether to create parent directories if they don't exist

    Raises:
        IOError: If the file cannot be written
    """
    import os

    path = os.path.abspath(file_path)
    parent_dir = os.path.dirname(path)

    try:
        if create_dirs and parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)

        with open(path, 'w') as f:
            f.write(content)
    except PermissionError:
        raise IOError(f"Permission denied: Cannot write to '{file_path}'")
    except OSError as e:
        raise IOError(f"Failed to write to '{file_path}': {e}")


def write_output(output: str, output_path: Optional[str], quiet: bool = False) -> None:
    """Write output to file or stdout.

    Args:
        output: The output content
        output_path: Optional file path to write to
        quiet: Whether to suppress status messages

    Raises:
        IOError: If the file cannot be written
    """
    if output_path:
        safe_write_file(output_path, output)
        if not quiet:
            print(f"Output written to {output_path}", file=sys.stderr)
    else:
        print(output)
