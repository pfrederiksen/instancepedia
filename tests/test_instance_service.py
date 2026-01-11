"""Tests for InstanceService"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from botocore.exceptions import ClientError, BotoCoreError

from src.services.instance_service import InstanceService
from src.models.instance_type import InstanceType, PricingInfo
from src.exceptions import AWSRegionError, InstanceTypeError


class TestInstanceService:
    """Tests for InstanceService"""

    def test_init(self):
        """Test InstanceService initialization"""
        mock_client = Mock()
        service = InstanceService(mock_client)
        assert service.aws_client == mock_client

    def test_get_instance_types_success(self):
        """Test successful instance types fetch"""
        # Setup mock AWS client
        mock_client = Mock()
        mock_client.region = "us-east-1"
        mock_client.ec2_client.describe_instance_types.return_value = {
            "InstanceTypes": [
                {
                    "InstanceType": "t3.micro",
                    "VCpuInfo": {"DefaultVCpus": 2},
                    "MemoryInfo": {"SizeInMiB": 1024},
                    "NetworkInfo": {
                        "NetworkPerformance": "Up to 5 Gigabit",
                        "MaximumNetworkInterfaces": 2,
                        "Ipv4AddressesPerInterface": 2,
                        "Ipv6AddressesPerInterface": 2
                    },
                    "ProcessorInfo": {"SupportedArchitectures": ["x86_64"]},
                    "EbsInfo": {"EbsOptimizedSupport": "default"},
                    "CurrentGeneration": True,
                    "BurstablePerformanceSupported": True
                }
            ]
        }

        service = InstanceService(mock_client)
        instances = service.get_instance_types(fetch_pricing=False)

        assert len(instances) == 1
        assert instances[0].instance_type == "t3.micro"
        assert instances[0].vcpu_info.default_vcpus == 2
        mock_client.ec2_client.describe_instance_types.assert_called_once()

    def test_get_instance_types_pagination(self):
        """Test instance types fetch with pagination"""
        mock_client = Mock()
        mock_client.region = "us-east-1"

        # First call returns NextToken, second call doesn't
        mock_client.ec2_client.describe_instance_types.side_effect = [
            {
                "InstanceTypes": [
                    {
                        "InstanceType": "t3.micro",
                        "VCpuInfo": {"DefaultVCpus": 2},
                        "MemoryInfo": {"SizeInMiB": 1024},
                        "NetworkInfo": {
                            "NetworkPerformance": "Up to 5 Gigabit",
                            "MaximumNetworkInterfaces": 2,
                            "Ipv4AddressesPerInterface": 2,
                            "Ipv6AddressesPerInterface": 2
                        },
                        "ProcessorInfo": {"SupportedArchitectures": ["x86_64"]},
                        "EbsInfo": {"EbsOptimizedSupport": "default"},
                        "CurrentGeneration": True
                    }
                ],
                "NextToken": "token123"
            },
            {
                "InstanceTypes": [
                    {
                        "InstanceType": "t3.small",
                        "VCpuInfo": {"DefaultVCpus": 2},
                        "MemoryInfo": {"SizeInMiB": 2048},
                        "NetworkInfo": {
                            "NetworkPerformance": "Up to 5 Gigabit",
                            "MaximumNetworkInterfaces": 3,
                            "Ipv4AddressesPerInterface": 4,
                            "Ipv6AddressesPerInterface": 4
                        },
                        "ProcessorInfo": {"SupportedArchitectures": ["x86_64"]},
                        "EbsInfo": {"EbsOptimizedSupport": "default"},
                        "CurrentGeneration": True
                    }
                ]
            }
        ]

        service = InstanceService(mock_client)
        instances = service.get_instance_types(fetch_pricing=False)

        assert len(instances) == 2
        assert instances[0].instance_type == "t3.micro"
        assert instances[1].instance_type == "t3.small"
        assert mock_client.ec2_client.describe_instance_types.call_count == 2

    def test_get_instance_types_auth_failure(self):
        """Test instance types fetch with auth failure"""
        mock_client = Mock()
        mock_client.region = "us-east-1"
        mock_client.ec2_client.describe_instance_types.side_effect = ClientError(
            {"Error": {"Code": "AuthFailure", "Message": "Not authorized"}},
            "DescribeInstanceTypes"
        )

        service = InstanceService(mock_client)
        with pytest.raises(AWSRegionError) as exc_info:
            service.get_instance_types()

        assert "Not authorized" in str(exc_info.value)
        assert "us-east-1" in str(exc_info.value)

    def test_get_instance_types_invalid_region(self):
        """Test instance types fetch with invalid region"""
        mock_client = Mock()
        mock_client.region = "invalid-region"
        mock_client.ec2_client.describe_instance_types.side_effect = ClientError(
            {"Error": {"Code": "InvalidRegionName", "Message": "Invalid region"}},
            "DescribeInstanceTypes"
        )

        service = InstanceService(mock_client)
        with pytest.raises(AWSRegionError) as exc_info:
            service.get_instance_types()

        assert "not valid" in str(exc_info.value)
        assert "invalid-region" in str(exc_info.value)

    def test_get_instance_types_generic_client_error(self):
        """Test instance types fetch with generic ClientError"""
        mock_client = Mock()
        mock_client.region = "us-east-1"
        mock_client.ec2_client.describe_instance_types.side_effect = ClientError(
            {"Error": {"Code": "Throttling", "Message": "Rate exceeded"}},
            "DescribeInstanceTypes"
        )

        service = InstanceService(mock_client)
        with pytest.raises(InstanceTypeError) as exc_info:
            service.get_instance_types()

        assert "Throttling" in str(exc_info.value)

    def test_get_instance_types_botocore_error(self):
        """Test instance types fetch with BotoCoreError"""
        mock_client = Mock()
        mock_client.region = "us-east-1"
        mock_client.ec2_client.describe_instance_types.side_effect = BotoCoreError()

        service = InstanceService(mock_client)
        with pytest.raises(InstanceTypeError) as exc_info:
            service.get_instance_types()

        assert "connection error" in str(exc_info.value).lower()

    def test_get_instance_types_generic_exception(self):
        """Test instance types fetch with generic exception"""
        mock_client = Mock()
        mock_client.region = "us-east-1"
        mock_client.ec2_client.describe_instance_types.side_effect = RuntimeError("Unknown error")

        service = InstanceService(mock_client)
        with pytest.raises(InstanceTypeError) as exc_info:
            service.get_instance_types()

        assert "Failed to fetch instance types" in str(exc_info.value)

    @patch('src.services.instance_service.PricingService')
    def test_get_instance_types_with_pricing(self, mock_pricing_service_class):
        """Test instance types fetch with pricing enabled"""
        # Setup mock AWS client
        mock_client = Mock()
        mock_client.region = "us-east-1"
        mock_client.ec2_client.describe_instance_types.return_value = {
            "InstanceTypes": [
                {
                    "InstanceType": "t3.micro",
                    "VCpuInfo": {"DefaultVCpus": 2},
                    "MemoryInfo": {"SizeInMiB": 1024},
                    "NetworkInfo": {
                        "NetworkPerformance": "Up to 5 Gigabit",
                        "MaximumNetworkInterfaces": 2,
                        "Ipv4AddressesPerInterface": 2,
                        "Ipv6AddressesPerInterface": 2
                    },
                    "ProcessorInfo": {"SupportedArchitectures": ["x86_64"]},
                    "EbsInfo": {"EbsOptimizedSupport": "default"},
                    "CurrentGeneration": True
                }
            ]
        }

        # Setup mock pricing service
        mock_pricing_service = Mock()
        mock_pricing_service.get_pricing.return_value = {
            'on_demand': 0.0104,
            'spot': 0.0031
        }
        mock_pricing_service_class.return_value = mock_pricing_service

        service = InstanceService(mock_client)
        instances = service.get_instance_types(fetch_pricing=True)

        assert len(instances) == 1
        assert instances[0].pricing is not None
        assert instances[0].pricing.on_demand_price == 0.0104
        assert instances[0].pricing.spot_price == 0.0031
        mock_pricing_service.get_pricing.assert_called_once_with("t3.micro", "us-east-1")

    @patch('src.services.instance_service.PricingService')
    def test_get_instance_types_with_pricing_failure(self, mock_pricing_service_class):
        """Test instance types fetch with pricing that fails"""
        # Setup mock AWS client
        mock_client = Mock()
        mock_client.region = "us-east-1"
        mock_client.ec2_client.describe_instance_types.return_value = {
            "InstanceTypes": [
                {
                    "InstanceType": "t3.micro",
                    "VCpuInfo": {"DefaultVCpus": 2},
                    "MemoryInfo": {"SizeInMiB": 1024},
                    "NetworkInfo": {
                        "NetworkPerformance": "Up to 5 Gigabit",
                        "MaximumNetworkInterfaces": 2,
                        "Ipv4AddressesPerInterface": 2,
                        "Ipv6AddressesPerInterface": 2
                    },
                    "ProcessorInfo": {"SupportedArchitectures": ["x86_64"]},
                    "EbsInfo": {"EbsOptimizedSupport": "default"},
                    "CurrentGeneration": True
                }
            ]
        }

        # Setup mock pricing service to fail
        mock_pricing_service = Mock()
        mock_pricing_service.get_pricing.side_effect = Exception("Pricing API error")
        mock_pricing_service_class.return_value = mock_pricing_service

        service = InstanceService(mock_client)
        instances = service.get_instance_types(fetch_pricing=True)

        # Should still return instances, just without pricing
        assert len(instances) == 1
        assert instances[0].pricing is None

    @patch('src.services.instance_service.PricingService')
    def test_update_instance_pricing_success(self, mock_pricing_service_class):
        """Test updating pricing for a single instance"""
        mock_client = Mock()
        mock_client.region = "us-east-1"

        # Create a mock instance type
        mock_instance = Mock(spec=InstanceType)
        mock_instance.instance_type = "t3.micro"
        mock_instance.pricing = None

        # Setup mock pricing service
        mock_pricing_service = Mock()
        mock_pricing_service.get_pricing.return_value = {
            'on_demand': 0.0104,
            'spot': 0.0031
        }
        mock_pricing_service_class.return_value = mock_pricing_service

        service = InstanceService(mock_client)
        service.update_instance_pricing(mock_instance)

        # Verify pricing was updated
        assert mock_instance.pricing is not None
        assert isinstance(mock_instance.pricing, PricingInfo)
        mock_pricing_service.get_pricing.assert_called_once_with("t3.micro", "us-east-1")

    @patch('src.services.instance_service.PricingService')
    def test_update_instance_pricing_failure(self, mock_pricing_service_class):
        """Test updating pricing when pricing service fails"""
        mock_client = Mock()
        mock_client.region = "us-east-1"

        # Create a mock instance type
        mock_instance = Mock(spec=InstanceType)
        mock_instance.instance_type = "t3.micro"
        mock_instance.pricing = None

        # Setup mock pricing service to fail
        mock_pricing_service = Mock()
        mock_pricing_service.get_pricing.side_effect = Exception("Pricing API error")
        mock_pricing_service_class.return_value = mock_pricing_service

        service = InstanceService(mock_client)
        service.update_instance_pricing(mock_instance)

        # Verify pricing is set to None on failure
        assert mock_instance.pricing is None


class TestInstanceTypeSorting:
    """Test instance type sorting behavior"""

    def test_instances_sorted_alphabetically(self):
        """Test that instance types are sorted alphabetically"""
        mock_client = Mock()
        mock_client.region = "us-east-1"

        # Return instances in random order
        mock_client.ec2_client.describe_instance_types.return_value = {
            "InstanceTypes": [
                {
                    "InstanceType": "m5.large",
                    "VCpuInfo": {"DefaultVCpus": 2},
                    "MemoryInfo": {"SizeInMiB": 8192},
                    "NetworkInfo": {
                        "NetworkPerformance": "Up to 10 Gigabit",
                        "MaximumNetworkInterfaces": 3,
                        "Ipv4AddressesPerInterface": 10,
                        "Ipv6AddressesPerInterface": 10
                    },
                    "ProcessorInfo": {"SupportedArchitectures": ["x86_64"]},
                    "EbsInfo": {"EbsOptimizedSupport": "default"},
                    "CurrentGeneration": True
                },
                {
                    "InstanceType": "a1.medium",
                    "VCpuInfo": {"DefaultVCpus": 1},
                    "MemoryInfo": {"SizeInMiB": 2048},
                    "NetworkInfo": {
                        "NetworkPerformance": "Up to 10 Gigabit",
                        "MaximumNetworkInterfaces": 2,
                        "Ipv4AddressesPerInterface": 4,
                        "Ipv6AddressesPerInterface": 4
                    },
                    "ProcessorInfo": {"SupportedArchitectures": ["arm64"]},
                    "EbsInfo": {"EbsOptimizedSupport": "default"},
                    "CurrentGeneration": True
                },
                {
                    "InstanceType": "t3.micro",
                    "VCpuInfo": {"DefaultVCpus": 2},
                    "MemoryInfo": {"SizeInMiB": 1024},
                    "NetworkInfo": {
                        "NetworkPerformance": "Up to 5 Gigabit",
                        "MaximumNetworkInterfaces": 2,
                        "Ipv4AddressesPerInterface": 2,
                        "Ipv6AddressesPerInterface": 2
                    },
                    "ProcessorInfo": {"SupportedArchitectures": ["x86_64"]},
                    "EbsInfo": {"EbsOptimizedSupport": "default"},
                    "CurrentGeneration": True,
                    "BurstablePerformanceSupported": True
                }
            ]
        }

        service = InstanceService(mock_client)
        instances = service.get_instance_types(fetch_pricing=False)

        # Verify sorting: a1.medium, m5.large, t3.micro
        assert len(instances) == 3
        assert instances[0].instance_type == "a1.medium"
        assert instances[1].instance_type == "m5.large"
        assert instances[2].instance_type == "t3.micro"

    def test_sorting_with_pagination(self):
        """Test that sorting works across paginated results"""
        mock_client = Mock()
        mock_client.region = "us-east-1"

        # First page: t3.micro, second page: a1.medium
        mock_client.ec2_client.describe_instance_types.side_effect = [
            {
                "InstanceTypes": [
                    {
                        "InstanceType": "t3.micro",
                        "VCpuInfo": {"DefaultVCpus": 2},
                        "MemoryInfo": {"SizeInMiB": 1024},
                        "NetworkInfo": {
                            "NetworkPerformance": "Up to 5 Gigabit",
                            "MaximumNetworkInterfaces": 2,
                            "Ipv4AddressesPerInterface": 2,
                            "Ipv6AddressesPerInterface": 2
                        },
                        "ProcessorInfo": {"SupportedArchitectures": ["x86_64"]},
                        "EbsInfo": {"EbsOptimizedSupport": "default"},
                        "CurrentGeneration": True
                    }
                ],
                "NextToken": "token123"
            },
            {
                "InstanceTypes": [
                    {
                        "InstanceType": "a1.medium",
                        "VCpuInfo": {"DefaultVCpus": 1},
                        "MemoryInfo": {"SizeInMiB": 2048},
                        "NetworkInfo": {
                            "NetworkPerformance": "Up to 10 Gigabit",
                            "MaximumNetworkInterfaces": 2,
                            "Ipv4AddressesPerInterface": 4,
                            "Ipv6AddressesPerInterface": 4
                        },
                        "ProcessorInfo": {"SupportedArchitectures": ["arm64"]},
                        "EbsInfo": {"EbsOptimizedSupport": "default"},
                        "CurrentGeneration": True
                    }
                ]
            }
        ]

        service = InstanceService(mock_client)
        instances = service.get_instance_types(fetch_pricing=False)

        # Verify sorting across pages: a1.medium comes first despite being on page 2
        assert len(instances) == 2
        assert instances[0].instance_type == "a1.medium"
        assert instances[1].instance_type == "t3.micro"


class TestEmptyResults:
    """Test handling of empty results"""

    def test_empty_instance_list(self):
        """Test handling when AWS returns empty instance list"""
        mock_client = Mock()
        mock_client.region = "us-east-1"
        mock_client.ec2_client.describe_instance_types.return_value = {
            "InstanceTypes": []
        }

        service = InstanceService(mock_client)
        instances = service.get_instance_types(fetch_pricing=False)

        assert instances == []
        assert len(instances) == 0

    def test_empty_response_key_missing(self):
        """Test handling when InstanceTypes key is missing from response"""
        mock_client = Mock()
        mock_client.region = "us-east-1"
        mock_client.ec2_client.describe_instance_types.return_value = {}

        service = InstanceService(mock_client)
        instances = service.get_instance_types(fetch_pricing=False)

        assert instances == []


class TestAdditionalErrorCodes:
    """Test additional AWS error codes"""

    def test_unauthorized_operation_error(self):
        """Test handling of UnauthorizedOperation error"""
        mock_client = Mock()
        mock_client.region = "ap-south-1"
        mock_client.ec2_client.describe_instance_types.side_effect = ClientError(
            {"Error": {"Code": "UnauthorizedOperation", "Message": "You are not authorized"}},
            "DescribeInstanceTypes"
        )

        service = InstanceService(mock_client)
        with pytest.raises(AWSRegionError) as exc_info:
            service.get_instance_types()

        assert "Not authorized" in str(exc_info.value)
        assert "ap-south-1" in str(exc_info.value)

    def test_invalid_parameter_value_error(self):
        """Test handling of InvalidParameterValue error"""
        mock_client = Mock()
        mock_client.region = "us-gov-west-1"
        mock_client.ec2_client.describe_instance_types.side_effect = ClientError(
            {"Error": {"Code": "InvalidParameterValue", "Message": "Invalid parameter"}},
            "DescribeInstanceTypes"
        )

        service = InstanceService(mock_client)
        with pytest.raises(AWSRegionError) as exc_info:
            service.get_instance_types()

        assert "not valid" in str(exc_info.value)
        assert "us-gov-west-1" in str(exc_info.value)


class TestPricingIntegration:
    """Test pricing integration scenarios"""

    @patch('src.services.instance_service.PricingService')
    def test_pricing_with_none_values(self, mock_pricing_service_class):
        """Test pricing when service returns None for prices"""
        mock_client = Mock()
        mock_client.region = "us-east-1"
        mock_client.ec2_client.describe_instance_types.return_value = {
            "InstanceTypes": [
                {
                    "InstanceType": "t3.micro",
                    "VCpuInfo": {"DefaultVCpus": 2},
                    "MemoryInfo": {"SizeInMiB": 1024},
                    "NetworkInfo": {
                        "NetworkPerformance": "Up to 5 Gigabit",
                        "MaximumNetworkInterfaces": 2,
                        "Ipv4AddressesPerInterface": 2,
                        "Ipv6AddressesPerInterface": 2
                    },
                    "ProcessorInfo": {"SupportedArchitectures": ["x86_64"]},
                    "EbsInfo": {"EbsOptimizedSupport": "default"},
                    "CurrentGeneration": True
                }
            ]
        }

        # Pricing service returns None values
        mock_pricing_service = Mock()
        mock_pricing_service.get_pricing.return_value = {
            'on_demand': None,
            'spot': None
        }
        mock_pricing_service_class.return_value = mock_pricing_service

        service = InstanceService(mock_client)
        instances = service.get_instance_types(fetch_pricing=True)

        assert len(instances) == 1
        assert instances[0].pricing is not None
        assert instances[0].pricing.on_demand_price is None
        assert instances[0].pricing.spot_price is None

    @patch('src.services.instance_service.PricingService')
    def test_pricing_with_partial_data(self, mock_pricing_service_class):
        """Test pricing when only some prices are available"""
        mock_client = Mock()
        mock_client.region = "us-east-1"
        mock_client.ec2_client.describe_instance_types.return_value = {
            "InstanceTypes": [
                {
                    "InstanceType": "t3.micro",
                    "VCpuInfo": {"DefaultVCpus": 2},
                    "MemoryInfo": {"SizeInMiB": 1024},
                    "NetworkInfo": {
                        "NetworkPerformance": "Up to 5 Gigabit",
                        "MaximumNetworkInterfaces": 2,
                        "Ipv4AddressesPerInterface": 2,
                        "Ipv6AddressesPerInterface": 2
                    },
                    "ProcessorInfo": {"SupportedArchitectures": ["x86_64"]},
                    "EbsInfo": {"EbsOptimizedSupport": "default"},
                    "CurrentGeneration": True
                }
            ]
        }

        # Only on-demand pricing available
        mock_pricing_service = Mock()
        mock_pricing_service.get_pricing.return_value = {
            'on_demand': 0.0104,
            'spot': None
        }
        mock_pricing_service_class.return_value = mock_pricing_service

        service = InstanceService(mock_client)
        instances = service.get_instance_types(fetch_pricing=True)

        assert len(instances) == 1
        assert instances[0].pricing.on_demand_price == 0.0104
        assert instances[0].pricing.spot_price is None

    @patch('src.services.instance_service.PricingService')
    def test_pricing_multiple_instances(self, mock_pricing_service_class):
        """Test pricing fetch for multiple instances"""
        mock_client = Mock()
        mock_client.region = "us-east-1"
        mock_client.ec2_client.describe_instance_types.return_value = {
            "InstanceTypes": [
                {
                    "InstanceType": "t3.micro",
                    "VCpuInfo": {"DefaultVCpus": 2},
                    "MemoryInfo": {"SizeInMiB": 1024},
                    "NetworkInfo": {
                        "NetworkPerformance": "Up to 5 Gigabit",
                        "MaximumNetworkInterfaces": 2,
                        "Ipv4AddressesPerInterface": 2,
                        "Ipv6AddressesPerInterface": 2
                    },
                    "ProcessorInfo": {"SupportedArchitectures": ["x86_64"]},
                    "EbsInfo": {"EbsOptimizedSupport": "default"},
                    "CurrentGeneration": True
                },
                {
                    "InstanceType": "t3.small",
                    "VCpuInfo": {"DefaultVCpus": 2},
                    "MemoryInfo": {"SizeInMiB": 2048},
                    "NetworkInfo": {
                        "NetworkPerformance": "Up to 5 Gigabit",
                        "MaximumNetworkInterfaces": 3,
                        "Ipv4AddressesPerInterface": 4,
                        "Ipv6AddressesPerInterface": 4
                    },
                    "ProcessorInfo": {"SupportedArchitectures": ["x86_64"]},
                    "EbsInfo": {"EbsOptimizedSupport": "default"},
                    "CurrentGeneration": True
                }
            ]
        }

        # Mock pricing service with different prices
        mock_pricing_service = Mock()
        mock_pricing_service.get_pricing.side_effect = [
            {'on_demand': 0.0104, 'spot': 0.0031},
            {'on_demand': 0.0208, 'spot': 0.0062}
        ]
        mock_pricing_service_class.return_value = mock_pricing_service

        service = InstanceService(mock_client)
        instances = service.get_instance_types(fetch_pricing=True)

        assert len(instances) == 2
        assert instances[0].pricing.on_demand_price == 0.0104
        assert instances[0].pricing.spot_price == 0.0031
        assert instances[1].pricing.on_demand_price == 0.0208
        assert instances[1].pricing.spot_price == 0.0062
        assert mock_pricing_service.get_pricing.call_count == 2

    @patch('src.services.instance_service.PricingService')
    def test_pricing_mixed_success_failure(self, mock_pricing_service_class):
        """Test pricing fetch when some instances succeed and some fail"""
        mock_client = Mock()
        mock_client.region = "us-east-1"
        mock_client.ec2_client.describe_instance_types.return_value = {
            "InstanceTypes": [
                {
                    "InstanceType": "t3.micro",
                    "VCpuInfo": {"DefaultVCpus": 2},
                    "MemoryInfo": {"SizeInMiB": 1024},
                    "NetworkInfo": {
                        "NetworkPerformance": "Up to 5 Gigabit",
                        "MaximumNetworkInterfaces": 2,
                        "Ipv4AddressesPerInterface": 2,
                        "Ipv6AddressesPerInterface": 2
                    },
                    "ProcessorInfo": {"SupportedArchitectures": ["x86_64"]},
                    "EbsInfo": {"EbsOptimizedSupport": "default"},
                    "CurrentGeneration": True
                },
                {
                    "InstanceType": "t3.small",
                    "VCpuInfo": {"DefaultVCpus": 2},
                    "MemoryInfo": {"SizeInMiB": 2048},
                    "NetworkInfo": {
                        "NetworkPerformance": "Up to 5 Gigabit",
                        "MaximumNetworkInterfaces": 3,
                        "Ipv4AddressesPerInterface": 4,
                        "Ipv6AddressesPerInterface": 4
                    },
                    "ProcessorInfo": {"SupportedArchitectures": ["x86_64"]},
                    "EbsInfo": {"EbsOptimizedSupport": "default"},
                    "CurrentGeneration": True
                }
            ]
        }

        # First succeeds, second fails
        mock_pricing_service = Mock()
        mock_pricing_service.get_pricing.side_effect = [
            {'on_demand': 0.0104, 'spot': 0.0031},
            Exception("Pricing API error")
        ]
        mock_pricing_service_class.return_value = mock_pricing_service

        service = InstanceService(mock_client)
        instances = service.get_instance_types(fetch_pricing=True)

        assert len(instances) == 2
        # First instance has pricing
        assert instances[0].pricing is not None
        assert instances[0].pricing.on_demand_price == 0.0104
        # Second instance has no pricing (failed)
        assert instances[1].pricing is None


class TestPaginationDetails:
    """Test pagination parameter handling"""

    def test_max_results_parameter(self):
        """Test that MaxResults=100 is used in API calls"""
        mock_client = Mock()
        mock_client.region = "us-east-1"
        mock_client.ec2_client.describe_instance_types.return_value = {
            "InstanceTypes": []
        }

        service = InstanceService(mock_client)
        service.get_instance_types(fetch_pricing=False)

        # Verify MaxResults parameter
        call_args = mock_client.ec2_client.describe_instance_types.call_args
        assert call_args[1]["MaxResults"] == 100

    def test_next_token_passed_correctly(self):
        """Test that NextToken is passed correctly on subsequent calls"""
        mock_client = Mock()
        mock_client.region = "us-east-1"

        mock_client.ec2_client.describe_instance_types.side_effect = [
            {
                "InstanceTypes": [
                    {
                        "InstanceType": "t3.micro",
                        "VCpuInfo": {"DefaultVCpus": 2},
                        "MemoryInfo": {"SizeInMiB": 1024},
                        "NetworkInfo": {
                            "NetworkPerformance": "Up to 5 Gigabit",
                            "MaximumNetworkInterfaces": 2,
                            "Ipv4AddressesPerInterface": 2,
                            "Ipv6AddressesPerInterface": 2
                        },
                        "ProcessorInfo": {"SupportedArchitectures": ["x86_64"]},
                        "EbsInfo": {"EbsOptimizedSupport": "default"},
                        "CurrentGeneration": True
                    }
                ],
                "NextToken": "my-next-token-123"
            },
            {
                "InstanceTypes": []
            }
        ]

        service = InstanceService(mock_client)
        service.get_instance_types(fetch_pricing=False)

        # Verify second call has NextToken
        assert mock_client.ec2_client.describe_instance_types.call_count == 2
        second_call_args = mock_client.ec2_client.describe_instance_types.call_args_list[1]
        assert second_call_args[1]["NextToken"] == "my-next-token-123"
        assert second_call_args[1]["MaxResults"] == 100

    def test_three_page_pagination(self):
        """Test pagination with three pages"""
        mock_client = Mock()
        mock_client.region = "us-east-1"

        mock_client.ec2_client.describe_instance_types.side_effect = [
            {
                "InstanceTypes": [
                    {
                        "InstanceType": "t3.micro",
                        "VCpuInfo": {"DefaultVCpus": 2},
                        "MemoryInfo": {"SizeInMiB": 1024},
                        "NetworkInfo": {
                            "NetworkPerformance": "Up to 5 Gigabit",
                            "MaximumNetworkInterfaces": 2,
                            "Ipv4AddressesPerInterface": 2,
                            "Ipv6AddressesPerInterface": 2
                        },
                        "ProcessorInfo": {"SupportedArchitectures": ["x86_64"]},
                        "EbsInfo": {"EbsOptimizedSupport": "default"},
                        "CurrentGeneration": True
                    }
                ],
                "NextToken": "token1"
            },
            {
                "InstanceTypes": [
                    {
                        "InstanceType": "t3.small",
                        "VCpuInfo": {"DefaultVCpus": 2},
                        "MemoryInfo": {"SizeInMiB": 2048},
                        "NetworkInfo": {
                            "NetworkPerformance": "Up to 5 Gigabit",
                            "MaximumNetworkInterfaces": 3,
                            "Ipv4AddressesPerInterface": 4,
                            "Ipv6AddressesPerInterface": 4
                        },
                        "ProcessorInfo": {"SupportedArchitectures": ["x86_64"]},
                        "EbsInfo": {"EbsOptimizedSupport": "default"},
                        "CurrentGeneration": True
                    }
                ],
                "NextToken": "token2"
            },
            {
                "InstanceTypes": [
                    {
                        "InstanceType": "t3.medium",
                        "VCpuInfo": {"DefaultVCpus": 2},
                        "MemoryInfo": {"SizeInMiB": 4096},
                        "NetworkInfo": {
                            "NetworkPerformance": "Up to 5 Gigabit",
                            "MaximumNetworkInterfaces": 3,
                            "Ipv4AddressesPerInterface": 6,
                            "Ipv6AddressesPerInterface": 6
                        },
                        "ProcessorInfo": {"SupportedArchitectures": ["x86_64"]},
                        "EbsInfo": {"EbsOptimizedSupport": "default"},
                        "CurrentGeneration": True
                    }
                ]
            }
        ]

        service = InstanceService(mock_client)
        instances = service.get_instance_types(fetch_pricing=False)

        assert len(instances) == 3
        assert mock_client.ec2_client.describe_instance_types.call_count == 3
        # Verify all three instances retrieved
        assert instances[0].instance_type == "t3.medium"
        assert instances[1].instance_type == "t3.micro"
        assert instances[2].instance_type == "t3.small"
