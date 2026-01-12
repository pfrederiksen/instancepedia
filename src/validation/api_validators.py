"""API response validators for AWS API data"""

from typing import Any


class ValidationError(Exception):
    """Raised when API response validation fails"""
    pass


def validate_instance_type_response(data: dict) -> None:
    """
    Validate AWS DescribeInstanceTypes API response data

    Args:
        data: Instance type data from AWS API

    Raises:
        ValidationError: If required fields are missing or invalid
    """
    # Required fields
    instance_type = data.get("InstanceType")
    if not instance_type or not isinstance(instance_type, str):
        raise ValidationError(
            f"Missing or invalid 'InstanceType' field: {instance_type}"
        )

    # VCpu validation
    vcpu_info = data.get("VCpuInfo")
    if not vcpu_info or not isinstance(vcpu_info, dict):
        raise ValidationError(
            f"Missing or invalid 'VCpuInfo' for {instance_type}"
        )

    default_vcpus = vcpu_info.get("DefaultVCpus")
    if not isinstance(default_vcpus, int) or default_vcpus <= 0:
        raise ValidationError(
            f"Invalid 'DefaultVCpus' for {instance_type}: {default_vcpus} (must be positive integer)"
        )

    # Memory validation
    memory_info = data.get("MemoryInfo")
    if not memory_info or not isinstance(memory_info, dict):
        raise ValidationError(
            f"Missing or invalid 'MemoryInfo' for {instance_type}"
        )

    size_in_mib = memory_info.get("SizeInMiB")
    if not isinstance(size_in_mib, int) or size_in_mib <= 0:
        raise ValidationError(
            f"Invalid 'SizeInMiB' for {instance_type}: {size_in_mib} (must be positive integer)"
        )


def validate_pricing_response(data: dict, instance_type: str) -> None:
    """
    Validate AWS Pricing API response data

    Args:
        data: Parsed pricing data from AWS Pricing API
        instance_type: Instance type for error messages

    Raises:
        ValidationError: If required pricing fields are missing or invalid
    """
    # Check for terms structure
    terms = data.get("terms")
    if not isinstance(terms, dict):
        raise ValidationError(
            f"Missing or invalid 'terms' in pricing data for {instance_type}"
        )

    # Empty terms is acceptable (Reserved/Savings Plans may not have OnDemand)
    if not terms:
        return

    # For on-demand pricing
    on_demand = terms.get("OnDemand")
    if on_demand is None:
        # Not all responses will have OnDemand (e.g., Reserved/Savings Plans)
        # This is informational, not an error
        return

    if not isinstance(on_demand, dict):
        # Invalid type - this is an error
        raise ValidationError(
            f"Invalid 'OnDemand' type in pricing data for {instance_type}"
        )

    # Validate at least one pricing term exists
    if len(on_demand) == 0:
        raise ValidationError(
            f"No pricing terms found for {instance_type}"
        )

    # Check first term has price dimensions
    first_term = list(on_demand.values())[0]
    price_dimensions = first_term.get("priceDimensions")
    if not price_dimensions or not isinstance(price_dimensions, dict):
        raise ValidationError(
            f"Missing 'priceDimensions' in pricing data for {instance_type}"
        )


def validate_spot_price_response(response: dict) -> None:
    """
    Validate AWS DescribeSpotPriceHistory API response

    Args:
        response: Raw response from describe_spot_price_history

    Raises:
        ValidationError: If response structure is invalid
    """
    if not isinstance(response, dict):
        raise ValidationError(
            f"Invalid spot price response type: {type(response)}"
        )

    # SpotPriceHistory field is optional (empty if no data)
    spot_history = response.get("SpotPriceHistory")
    if spot_history is not None and not isinstance(spot_history, list):
        raise ValidationError(
            f"Invalid 'SpotPriceHistory' type: {type(spot_history)} (expected list)"
        )

    # Validate each price point if present
    if spot_history:
        for i, price_point in enumerate(spot_history):
            if not isinstance(price_point, dict):
                raise ValidationError(
                    f"Invalid spot price point {i}: {type(price_point)} (expected dict)"
                )

            # Validate required fields
            instance_type = price_point.get("InstanceType")
            if not instance_type or not isinstance(instance_type, str):
                raise ValidationError(
                    f"Missing or invalid 'InstanceType' in spot price point {i}"
                )

            spot_price = price_point.get("SpotPrice")
            if not spot_price or not isinstance(spot_price, str):
                raise ValidationError(
                    f"Missing or invalid 'SpotPrice' for {instance_type}"
                )

            # Validate price is numeric
            try:
                price_float = float(spot_price)
                if price_float < 0:
                    raise ValidationError(
                        f"Negative spot price for {instance_type}: {spot_price}"
                    )
            except (ValueError, TypeError) as e:
                raise ValidationError(
                    f"Invalid spot price format for {instance_type}: {spot_price}"
                ) from e


def validate_price_value(price: Any, context: str = "price") -> float:
    """
    Validate and convert a price value

    Args:
        price: Price value to validate (can be str, int, float)
        context: Description for error messages

    Returns:
        Validated price as float

    Raises:
        ValidationError: If price is invalid
    """
    if price is None:
        raise ValidationError(f"{context} is None")

    try:
        price_float = float(price)
    except (ValueError, TypeError) as e:
        raise ValidationError(
            f"Invalid {context} format: {price} (type: {type(price)})"
        ) from e

    if price_float < 0:
        raise ValidationError(
            f"Negative {context}: {price_float}"
        )

    # Sanity check: EC2 prices typically range from $0.001/hr to ~$100/hr
    # Anything above $10,000/hr is likely a data error
    if price_float > 10000:
        raise ValidationError(
            f"Unreasonably high {context}: ${price_float}/hr (likely data error)"
        )

    return price_float
