"""Tests for API response validators"""

import pytest

from src.validation.api_validators import (
    ValidationError,
    validate_instance_type_response,
    validate_pricing_response,
    validate_spot_price_response,
    validate_price_value,
)


class TestValidateInstanceTypeResponse:
    """Tests for validate_instance_type_response"""

    def test_valid_instance_type_response(self):
        """Test validation passes for valid instance data"""
        data = {
            "InstanceType": "t3.micro",
            "VCpuInfo": {
                "DefaultVCpus": 2,
                "DefaultCores": 1,
                "DefaultThreadsPerCore": 2
            },
            "MemoryInfo": {
                "SizeInMiB": 1024
            }
        }

        # Should not raise exception
        validate_instance_type_response(data)

    def test_missing_instance_type(self):
        """Test validation fails when InstanceType is missing"""
        data = {
            "VCpuInfo": {"DefaultVCpus": 2},
            "MemoryInfo": {"SizeInMiB": 1024}
        }

        with pytest.raises(ValidationError, match="Missing or invalid 'InstanceType'"):
            validate_instance_type_response(data)

    def test_empty_instance_type(self):
        """Test validation fails when InstanceType is empty string"""
        data = {
            "InstanceType": "",
            "VCpuInfo": {"DefaultVCpus": 2},
            "MemoryInfo": {"SizeInMiB": 1024}
        }

        with pytest.raises(ValidationError, match="Missing or invalid 'InstanceType'"):
            validate_instance_type_response(data)

    def test_invalid_instance_type_type(self):
        """Test validation fails when InstanceType is not a string"""
        data = {
            "InstanceType": 123,  # Should be string
            "VCpuInfo": {"DefaultVCpus": 2},
            "MemoryInfo": {"SizeInMiB": 1024}
        }

        with pytest.raises(ValidationError, match="Missing or invalid 'InstanceType'"):
            validate_instance_type_response(data)

    def test_missing_vcpu_info(self):
        """Test validation fails when VCpuInfo is missing"""
        data = {
            "InstanceType": "t3.micro",
            "MemoryInfo": {"SizeInMiB": 1024}
        }

        with pytest.raises(ValidationError, match="Missing or invalid 'VCpuInfo'"):
            validate_instance_type_response(data)

    def test_invalid_vcpu_info_type(self):
        """Test validation fails when VCpuInfo is not a dict"""
        data = {
            "InstanceType": "t3.micro",
            "VCpuInfo": "invalid",
            "MemoryInfo": {"SizeInMiB": 1024}
        }

        with pytest.raises(ValidationError, match="Missing or invalid 'VCpuInfo'"):
            validate_instance_type_response(data)

    def test_zero_default_vcpus(self):
        """Test validation fails when DefaultVCpus is 0"""
        data = {
            "InstanceType": "t3.micro",
            "VCpuInfo": {"DefaultVCpus": 0},
            "MemoryInfo": {"SizeInMiB": 1024}
        }

        with pytest.raises(ValidationError, match="Invalid 'DefaultVCpus'.*must be positive integer"):
            validate_instance_type_response(data)

    def test_negative_default_vcpus(self):
        """Test validation fails when DefaultVCpus is negative"""
        data = {
            "InstanceType": "t3.micro",
            "VCpuInfo": {"DefaultVCpus": -1},
            "MemoryInfo": {"SizeInMiB": 1024}
        }

        with pytest.raises(ValidationError, match="Invalid 'DefaultVCpus'.*must be positive integer"):
            validate_instance_type_response(data)

    def test_non_integer_default_vcpus(self):
        """Test validation fails when DefaultVCpus is not an integer"""
        data = {
            "InstanceType": "t3.micro",
            "VCpuInfo": {"DefaultVCpus": "2"},  # String instead of int
            "MemoryInfo": {"SizeInMiB": 1024}
        }

        with pytest.raises(ValidationError, match="Invalid 'DefaultVCpus'"):
            validate_instance_type_response(data)

    def test_missing_memory_info(self):
        """Test validation fails when MemoryInfo is missing"""
        data = {
            "InstanceType": "t3.micro",
            "VCpuInfo": {"DefaultVCpus": 2}
        }

        with pytest.raises(ValidationError, match="Missing or invalid 'MemoryInfo'"):
            validate_instance_type_response(data)

    def test_invalid_memory_info_type(self):
        """Test validation fails when MemoryInfo is not a dict"""
        data = {
            "InstanceType": "t3.micro",
            "VCpuInfo": {"DefaultVCpus": 2},
            "MemoryInfo": []
        }

        with pytest.raises(ValidationError, match="Missing or invalid 'MemoryInfo'"):
            validate_instance_type_response(data)

    def test_zero_memory_size(self):
        """Test validation fails when SizeInMiB is 0"""
        data = {
            "InstanceType": "t3.micro",
            "VCpuInfo": {"DefaultVCpus": 2},
            "MemoryInfo": {"SizeInMiB": 0}
        }

        with pytest.raises(ValidationError, match="Invalid 'SizeInMiB'.*must be positive integer"):
            validate_instance_type_response(data)

    def test_negative_memory_size(self):
        """Test validation fails when SizeInMiB is negative"""
        data = {
            "InstanceType": "t3.micro",
            "VCpuInfo": {"DefaultVCpus": 2},
            "MemoryInfo": {"SizeInMiB": -1024}
        }

        with pytest.raises(ValidationError, match="Invalid 'SizeInMiB'.*must be positive integer"):
            validate_instance_type_response(data)

    def test_non_integer_memory_size(self):
        """Test validation fails when SizeInMiB is not an integer"""
        data = {
            "InstanceType": "t3.micro",
            "VCpuInfo": {"DefaultVCpus": 2},
            "MemoryInfo": {"SizeInMiB": "1024"}
        }

        with pytest.raises(ValidationError, match="Invalid 'SizeInMiB'"):
            validate_instance_type_response(data)


class TestValidatePricingResponse:
    """Tests for validate_pricing_response"""

    def test_valid_pricing_response(self):
        """Test validation passes for valid pricing data"""
        data = {
            "terms": {
                "OnDemand": {
                    "TERM_123": {
                        "priceDimensions": {
                            "DIM_123": {
                                "pricePerUnit": {"USD": "0.0104"}
                            }
                        }
                    }
                }
            }
        }

        # Should not raise exception
        validate_pricing_response(data, "t3.micro")

    def test_missing_terms(self):
        """Test validation fails when terms is missing"""
        data = {}

        with pytest.raises(ValidationError, match="Missing or invalid 'terms'"):
            validate_pricing_response(data, "t3.micro")

    def test_invalid_terms_type(self):
        """Test validation fails when terms is not a dict"""
        data = {"terms": []}

        with pytest.raises(ValidationError, match="Missing or invalid 'terms'"):
            validate_pricing_response(data, "t3.micro")

    def test_missing_on_demand_not_error(self):
        """Test validation doesn't fail when OnDemand is missing (informational only)"""
        data = {"terms": {}}

        # Should not raise - Reserved/Savings Plans may not have OnDemand
        validate_pricing_response(data, "t3.micro")

    def test_invalid_on_demand_type(self):
        """Test validation fails when OnDemand is wrong type"""
        data = {"terms": {"OnDemand": []}}

        # Should raise - invalid type is an error
        with pytest.raises(ValidationError, match="Invalid 'OnDemand' type"):
            validate_pricing_response(data, "t3.micro")

    def test_empty_on_demand_terms(self):
        """Test validation fails when OnDemand terms dict is empty"""
        data = {"terms": {"OnDemand": {}}}

        with pytest.raises(ValidationError, match="No pricing terms found"):
            validate_pricing_response(data, "t3.micro")

    def test_missing_price_dimensions(self):
        """Test validation fails when priceDimensions is missing"""
        data = {
            "terms": {
                "OnDemand": {
                    "TERM_123": {}
                }
            }
        }

        with pytest.raises(ValidationError, match="Missing 'priceDimensions'"):
            validate_pricing_response(data, "t3.micro")

    def test_invalid_price_dimensions_type(self):
        """Test validation fails when priceDimensions is not a dict"""
        data = {
            "terms": {
                "OnDemand": {
                    "TERM_123": {
                        "priceDimensions": []
                    }
                }
            }
        }

        with pytest.raises(ValidationError, match="Missing 'priceDimensions'"):
            validate_pricing_response(data, "t3.micro")


class TestValidateSpotPriceResponse:
    """Tests for validate_spot_price_response"""

    def test_valid_spot_price_response(self):
        """Test validation passes for valid spot price data"""
        response = {
            "SpotPriceHistory": [
                {
                    "InstanceType": "t3.micro",
                    "SpotPrice": "0.0052",
                    "Timestamp": "2024-01-01T12:00:00Z"
                }
            ]
        }

        # Should not raise exception
        validate_spot_price_response(response)

    def test_empty_spot_price_history(self):
        """Test validation passes for empty SpotPriceHistory"""
        response = {"SpotPriceHistory": []}

        # Should not raise - empty history is valid
        validate_spot_price_response(response)

    def test_missing_spot_price_history(self):
        """Test validation passes when SpotPriceHistory is absent"""
        response = {}

        # Should not raise - field is optional
        validate_spot_price_response(response)

    def test_invalid_response_type(self):
        """Test validation fails when response is not a dict"""
        response = []

        with pytest.raises(ValidationError, match="Invalid spot price response type"):
            validate_spot_price_response(response)

    def test_invalid_spot_price_history_type(self):
        """Test validation fails when SpotPriceHistory is not a list"""
        response = {"SpotPriceHistory": "invalid"}

        with pytest.raises(ValidationError, match="Invalid 'SpotPriceHistory' type"):
            validate_spot_price_response(response)

    def test_invalid_price_point_type(self):
        """Test validation fails when price point is not a dict"""
        response = {
            "SpotPriceHistory": ["invalid"]
        }

        with pytest.raises(ValidationError, match="Invalid spot price point 0"):
            validate_spot_price_response(response)

    def test_missing_instance_type_in_price_point(self):
        """Test validation fails when InstanceType is missing from price point"""
        response = {
            "SpotPriceHistory": [
                {
                    "SpotPrice": "0.0052"
                }
            ]
        }

        with pytest.raises(ValidationError, match="Missing or invalid 'InstanceType'"):
            validate_spot_price_response(response)

    def test_missing_spot_price_in_price_point(self):
        """Test validation fails when SpotPrice is missing from price point"""
        response = {
            "SpotPriceHistory": [
                {
                    "InstanceType": "t3.micro"
                }
            ]
        }

        with pytest.raises(ValidationError, match="Missing or invalid 'SpotPrice'"):
            validate_spot_price_response(response)

    def test_invalid_spot_price_format(self):
        """Test validation fails when SpotPrice is not numeric"""
        response = {
            "SpotPriceHistory": [
                {
                    "InstanceType": "t3.micro",
                    "SpotPrice": "invalid"
                }
            ]
        }

        with pytest.raises(ValidationError, match="Invalid spot price format"):
            validate_spot_price_response(response)

    def test_negative_spot_price(self):
        """Test validation fails when SpotPrice is negative"""
        response = {
            "SpotPriceHistory": [
                {
                    "InstanceType": "t3.micro",
                    "SpotPrice": "-0.0052"
                }
            ]
        }

        with pytest.raises(ValidationError, match="Negative spot price"):
            validate_spot_price_response(response)


class TestValidatePriceValue:
    """Tests for validate_price_value"""

    def test_valid_float_price(self):
        """Test validation passes for valid float price"""
        price = validate_price_value(0.0104)
        assert price == 0.0104

    def test_valid_int_price(self):
        """Test validation converts int to float"""
        price = validate_price_value(1)
        assert price == 1.0
        assert isinstance(price, float)

    def test_valid_string_price(self):
        """Test validation converts string to float"""
        price = validate_price_value("0.0104")
        assert price == 0.0104
        assert isinstance(price, float)

    def test_zero_price(self):
        """Test validation allows zero price"""
        price = validate_price_value(0)
        assert price == 0.0

    def test_none_price(self):
        """Test validation fails for None"""
        with pytest.raises(ValidationError, match="price is None"):
            validate_price_value(None)

    def test_negative_price(self):
        """Test validation fails for negative price"""
        with pytest.raises(ValidationError, match="Negative price"):
            validate_price_value(-0.01)

    def test_invalid_format_price(self):
        """Test validation fails for non-numeric string"""
        with pytest.raises(ValidationError, match="Invalid price format"):
            validate_price_value("not_a_number")

    def test_unreasonably_high_price(self):
        """Test validation fails for extremely high prices"""
        with pytest.raises(ValidationError, match="Unreasonably high price"):
            validate_price_value(15000)

    def test_custom_context_in_error(self):
        """Test context string appears in error messages"""
        with pytest.raises(ValidationError, match="hourly rate is None"):
            validate_price_value(None, context="hourly rate")

    def test_large_but_reasonable_price(self):
        """Test validation allows high but reasonable prices"""
        # p5.48xlarge costs around $98/hr, should be valid
        price = validate_price_value(98.32)
        assert price == 98.32
