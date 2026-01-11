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
