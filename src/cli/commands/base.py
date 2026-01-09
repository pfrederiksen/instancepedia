"""Base utilities for CLI commands"""

import logging
import sys
from typing import Optional

from src.services.aws_client import AWSClient
from src.services.pricing_service import PricingService
from src.models.instance_type import PricingInfo

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


def get_aws_client(region: str, profile: Optional[str] = None) -> AWSClient:
    """Get AWS client with error handling"""
    try:
        return AWSClient(region, profile)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


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


def write_output(output: str, output_path: Optional[str], quiet: bool = False) -> None:
    """Write output to file or stdout.

    Args:
        output: The output content
        output_path: Optional file path to write to
        quiet: Whether to suppress status messages
    """
    if output_path:
        with open(output_path, 'w') as f:
            f.write(output)
        if not quiet:
            print(f"Output written to {output_path}", file=sys.stderr)
    else:
        print(output)
