"""Pytest configuration and fixtures"""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from src.models.instance_type import (
    InstanceType,
    VCpuInfo,
    MemoryInfo,
    NetworkInfo,
    ProcessorInfo,
    EbsInfo,
    PricingInfo
)
from src.config.settings import Settings


@pytest.fixture
def sample_instance_type():
    """Create a sample instance type for testing"""
    return InstanceType(
        instance_type="t3.micro",
        vcpu_info=VCpuInfo(
            default_vcpus=2,
            default_cores=1,
            default_threads_per_core=2
        ),
        memory_info=MemoryInfo(size_in_mib=1024),  # 1 GB
        network_info=NetworkInfo(
            network_performance="Up to 5 Gigabit",
            maximum_network_interfaces=2,
            maximum_ipv4_addresses_per_interface=4,
            maximum_ipv6_addresses_per_interface=4
        ),
        processor_info=ProcessorInfo(
            supported_architectures=["x86_64"],
            sustained_clock_speed_in_ghz=2.5
        ),
        ebs_info=EbsInfo(
            ebs_optimized_support="supported",
            ebs_optimized_info=None
        ),
        current_generation=True,
        burstable_performance_supported=True,
        hibernation_supported=False,
        pricing=PricingInfo(
            on_demand_price=0.0104,
            spot_price=0.0031
        )
    )


@pytest.fixture
def sample_instance_type_no_pricing():
    """Create a sample instance type without pricing"""
    return InstanceType(
        instance_type="m5.large",
        vcpu_info=VCpuInfo(default_vcpus=2),
        memory_info=MemoryInfo(size_in_mib=8192),  # 8 GB
        network_info=NetworkInfo(
            network_performance="Up to 10 Gigabit",
            maximum_network_interfaces=3,
            maximum_ipv4_addresses_per_interface=10,
            maximum_ipv6_addresses_per_interface=10
        ),
        processor_info=ProcessorInfo(
            supported_architectures=["x86_64"]
        ),
        ebs_info=EbsInfo(ebs_optimized_support="default"),
        current_generation=True,
        burstable_performance_supported=False,
        hibernation_supported=False,
        pricing=None
    )


@pytest.fixture
def mock_aws_client():
    """Create a mock AWS client"""
    client = Mock()
    client.region = "us-east-1"
    client.profile = None
    return client


@pytest.fixture
def mock_instance_service(mock_aws_client):
    """Create a mock instance service"""
    service = Mock()
    service.aws_client = mock_aws_client
    return service


@pytest.fixture
def mock_pricing_service(mock_aws_client):
    """Create a mock pricing service"""
    service = Mock()
    service.aws_client = mock_aws_client
    return service


# =============================================================================
# TUI Test Fixtures
# =============================================================================

@pytest.fixture
def mock_settings():
    """Create mock settings for TUI testing"""
    settings = Mock(spec=Settings)
    settings.aws_region = "us-east-1"
    settings.aws_profile = None
    return settings


@pytest.fixture
def sample_instance_types():
    """Create a list of sample instance types for TUI testing"""
    return [
        InstanceType(
            instance_type="t2.micro",
            vcpu_info=VCpuInfo(
                default_vcpus=1,
                default_cores=1,
                default_threads_per_core=1
            ),
            memory_info=MemoryInfo(size_in_mib=1024),
            network_info=NetworkInfo(
                network_performance="Low to Moderate",
                maximum_network_interfaces=2,
                maximum_ipv4_addresses_per_interface=2,
                maximum_ipv6_addresses_per_interface=2
            ),
            processor_info=ProcessorInfo(
                supported_architectures=["x86_64"]
            ),
            ebs_info=EbsInfo(ebs_optimized_support="unsupported"),
            current_generation=True,
            burstable_performance_supported=True,
            hibernation_supported=False,
            pricing=PricingInfo(on_demand_price=0.0116, spot_price=0.0035)
        ),
        InstanceType(
            instance_type="t3.micro",
            vcpu_info=VCpuInfo(
                default_vcpus=2,
                default_cores=1,
                default_threads_per_core=2
            ),
            memory_info=MemoryInfo(size_in_mib=1024),
            network_info=NetworkInfo(
                network_performance="Up to 5 Gigabit",
                maximum_network_interfaces=2,
                maximum_ipv4_addresses_per_interface=2,
                maximum_ipv6_addresses_per_interface=2
            ),
            processor_info=ProcessorInfo(
                supported_architectures=["x86_64"],
                sustained_clock_speed_in_ghz=2.5
            ),
            ebs_info=EbsInfo(ebs_optimized_support="supported"),
            current_generation=True,
            burstable_performance_supported=True,
            hibernation_supported=True,
            pricing=PricingInfo(on_demand_price=0.0104, spot_price=0.0031)
        ),
        InstanceType(
            instance_type="m5.large",
            vcpu_info=VCpuInfo(
                default_vcpus=2,
                default_cores=1,
                default_threads_per_core=2
            ),
            memory_info=MemoryInfo(size_in_mib=8192),
            network_info=NetworkInfo(
                network_performance="Up to 10 Gigabit",
                maximum_network_interfaces=3,
                maximum_ipv4_addresses_per_interface=10,
                maximum_ipv6_addresses_per_interface=10
            ),
            processor_info=ProcessorInfo(
                supported_architectures=["x86_64"],
                sustained_clock_speed_in_ghz=3.1
            ),
            ebs_info=EbsInfo(ebs_optimized_support="default"),
            current_generation=True,
            burstable_performance_supported=False,
            hibernation_supported=True,
            pricing=PricingInfo(on_demand_price=0.096, spot_price=0.038)
        ),
        InstanceType(
            instance_type="c5.large",
            vcpu_info=VCpuInfo(
                default_vcpus=2,
                default_cores=1,
                default_threads_per_core=2
            ),
            memory_info=MemoryInfo(size_in_mib=4096),
            network_info=NetworkInfo(
                network_performance="Up to 10 Gigabit",
                maximum_network_interfaces=3,
                maximum_ipv4_addresses_per_interface=10,
                maximum_ipv6_addresses_per_interface=10
            ),
            processor_info=ProcessorInfo(
                supported_architectures=["x86_64"],
                sustained_clock_speed_in_ghz=3.4
            ),
            ebs_info=EbsInfo(ebs_optimized_support="default"),
            current_generation=True,
            burstable_performance_supported=False,
            hibernation_supported=False,
            pricing=PricingInfo(on_demand_price=0.085, spot_price=0.034)
        ),
    ]


@pytest.fixture
def sample_regions():
    """Sample AWS regions for testing"""
    return ["us-east-1", "us-west-2", "eu-west-1", "ap-northeast-1"]
