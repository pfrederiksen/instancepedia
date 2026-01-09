"""Tests for CLI output formatters (JSON/CSV export)"""

import json
import csv
import pytest
from io import StringIO
from unittest.mock import Mock, patch

from src.cli.output import (
    TableFormatter,
    JSONFormatter,
    CSVFormatter,
    get_formatter,
    OutputFormatter,
)
from src.models.instance_type import (
    InstanceType,
    VCpuInfo,
    MemoryInfo,
    NetworkInfo,
    ProcessorInfo,
    EbsInfo,
    PricingInfo,
    InstanceStorageInfo,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def basic_instance():
    """Create a basic instance type for testing"""
    return InstanceType(
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
        hibernation_supported=True,
        pricing=PricingInfo(
            on_demand_price=0.0104,
            spot_price=0.0031
        )
    )


@pytest.fixture
def instance_with_pricing():
    """Create an instance with full pricing data"""
    return InstanceType(
        instance_type="m5.large",
        vcpu_info=VCpuInfo(default_vcpus=2, default_cores=1, default_threads_per_core=2),
        memory_info=MemoryInfo(size_in_mib=8192),
        network_info=NetworkInfo(
            network_performance="Up to 10 Gigabit",
            maximum_network_interfaces=3,
            maximum_ipv4_addresses_per_interface=10,
            maximum_ipv6_addresses_per_interface=10
        ),
        processor_info=ProcessorInfo(supported_architectures=["x86_64"], sustained_clock_speed_in_ghz=3.1),
        ebs_info=EbsInfo(ebs_optimized_support="default"),
        current_generation=True,
        burstable_performance_supported=False,
        hibernation_supported=True,
        pricing=PricingInfo(
            on_demand_price=0.096,
            spot_price=0.038,
            savings_plan_1yr_no_upfront=0.0624,
            savings_plan_3yr_no_upfront=0.0437,
            ri_1yr_no_upfront=0.0600,
            ri_1yr_partial_upfront=0.0290,
            ri_1yr_all_upfront=None,
            ri_3yr_no_upfront=0.0410,
            ri_3yr_partial_upfront=0.0190,
            ri_3yr_all_upfront=None
        )
    )


@pytest.fixture
def instance_no_pricing():
    """Create an instance without pricing"""
    return InstanceType(
        instance_type="t3.nano",
        vcpu_info=VCpuInfo(default_vcpus=2),
        memory_info=MemoryInfo(size_in_mib=512),
        network_info=NetworkInfo(
            network_performance="Up to 5 Gigabit",
            maximum_network_interfaces=2,
            maximum_ipv4_addresses_per_interface=2,
            maximum_ipv6_addresses_per_interface=2
        ),
        processor_info=ProcessorInfo(supported_architectures=["x86_64"]),
        ebs_info=EbsInfo(ebs_optimized_support="supported"),
        current_generation=True,
        burstable_performance_supported=True,
        hibernation_supported=False,
        pricing=None
    )


@pytest.fixture
def instance_with_storage():
    """Create an instance with instance storage"""
    return InstanceType(
        instance_type="i3.large",
        vcpu_info=VCpuInfo(default_vcpus=2),
        memory_info=MemoryInfo(size_in_mib=15360),
        network_info=NetworkInfo(
            network_performance="Up to 10 Gigabit",
            maximum_network_interfaces=3,
            maximum_ipv4_addresses_per_interface=10,
            maximum_ipv6_addresses_per_interface=10
        ),
        processor_info=ProcessorInfo(supported_architectures=["x86_64"]),
        ebs_info=EbsInfo(ebs_optimized_support="default"),
        current_generation=True,
        burstable_performance_supported=False,
        hibernation_supported=False,
        instance_storage_info=InstanceStorageInfo(
            total_size_in_gb=475,
            disks=[{"count": 1, "size_in_gb": 475, "type": "ssd"}],
            nvme_support="required"
        ),
        pricing=PricingInfo(on_demand_price=0.156, spot_price=0.047)
    )


@pytest.fixture
def sample_regions():
    """Create sample region data"""
    return [
        {"code": "us-east-1", "name": "US East (N. Virginia)"},
        {"code": "us-west-2", "name": "US West (Oregon)"},
        {"code": "eu-west-1", "name": "Europe (Ireland)"},
    ]


# =============================================================================
# Test get_formatter function
# =============================================================================

class TestGetFormatter:
    """Tests for get_formatter function"""

    def test_get_table_formatter(self):
        """Test getting table formatter"""
        formatter = get_formatter("table")
        assert isinstance(formatter, TableFormatter)

    def test_get_json_formatter(self):
        """Test getting JSON formatter"""
        formatter = get_formatter("json")
        assert isinstance(formatter, JSONFormatter)

    def test_get_csv_formatter(self):
        """Test getting CSV formatter"""
        formatter = get_formatter("csv")
        assert isinstance(formatter, CSVFormatter)

    def test_invalid_format_raises_error(self):
        """Test that invalid format raises ValueError"""
        with pytest.raises(ValueError) as exc_info:
            get_formatter("invalid")
        assert "Unknown format" in str(exc_info.value)
        assert "invalid" in str(exc_info.value)


# =============================================================================
# Test JSONFormatter
# =============================================================================

class TestJSONFormatter:
    """Tests for JSONFormatter"""

    def test_format_instance_list_basic(self, basic_instance):
        """Test JSON formatting of instance list"""
        formatter = JSONFormatter()
        result = formatter.format_instance_list([basic_instance], "us-east-1")

        data = json.loads(result)
        assert data["region"] == "us-east-1"
        assert data["count"] == 1
        assert len(data["instances"]) == 1

        inst = data["instances"][0]
        assert inst["instance_type"] == "t3.micro"
        assert inst["vcpu"] == 2
        assert inst["memory_gb"] == 1.0

    def test_format_instance_list_empty(self):
        """Test JSON formatting of empty instance list"""
        formatter = JSONFormatter()
        result = formatter.format_instance_list([], "us-east-1")

        data = json.loads(result)
        assert data["region"] == "us-east-1"
        assert data["count"] == 0
        assert data["instances"] == []

    def test_format_instance_list_multiple(self, basic_instance, instance_with_pricing):
        """Test JSON formatting of multiple instances"""
        formatter = JSONFormatter()
        result = formatter.format_instance_list([basic_instance, instance_with_pricing], "us-east-1")

        data = json.loads(result)
        assert data["count"] == 2
        assert len(data["instances"]) == 2
        assert data["instances"][0]["instance_type"] == "t3.micro"
        assert data["instances"][1]["instance_type"] == "m5.large"

    def test_format_instance_list_with_pricing(self, instance_with_pricing):
        """Test JSON formatting includes pricing data"""
        formatter = JSONFormatter()
        result = formatter.format_instance_list([instance_with_pricing], "us-east-1")

        data = json.loads(result)
        inst = data["instances"][0]
        assert "pricing" in inst
        assert inst["pricing"]["on_demand_price_per_hour"] == 0.096
        assert inst["pricing"]["spot_price_per_hour"] == 0.038

    def test_format_instance_list_with_reserved_instances(self, instance_with_pricing):
        """Test JSON formatting includes reserved instance pricing"""
        formatter = JSONFormatter()
        result = formatter.format_instance_list([instance_with_pricing], "us-east-1")

        data = json.loads(result)
        inst = data["instances"][0]

        assert "reserved_instances" in inst["pricing"]
        ri = inst["pricing"]["reserved_instances"]
        assert ri["1yr"]["no_upfront"] == 0.0600
        assert ri["1yr"]["partial_upfront"] == 0.0290
        assert ri["1yr"]["all_upfront"] is None
        assert ri["3yr"]["no_upfront"] == 0.0410

    def test_format_instance_list_with_savings_plans(self, instance_with_pricing):
        """Test JSON formatting includes savings plans pricing"""
        formatter = JSONFormatter()
        result = formatter.format_instance_list([instance_with_pricing], "us-east-1")

        data = json.loads(result)
        inst = data["instances"][0]

        assert "savings_plans" in inst["pricing"]
        assert inst["pricing"]["savings_plans"]["1yr_no_upfront"] == 0.0624
        assert inst["pricing"]["savings_plans"]["3yr_no_upfront"] == 0.0437

    def test_format_instance_list_no_pricing(self, instance_no_pricing):
        """Test JSON formatting handles missing pricing"""
        formatter = JSONFormatter()
        result = formatter.format_instance_list([instance_no_pricing], "us-east-1")

        data = json.loads(result)
        inst = data["instances"][0]
        assert "pricing" not in inst

    def test_format_instance_detail(self, basic_instance):
        """Test JSON formatting of instance detail"""
        formatter = JSONFormatter()
        result = formatter.format_instance_detail(basic_instance, "us-east-1")

        data = json.loads(result)
        assert data["region"] == "us-east-1"
        assert "instance" in data

        inst = data["instance"]
        assert inst["instance_type"] == "t3.micro"
        assert "vcpu_info" in inst
        assert "memory_info" in inst
        assert "network_info" in inst
        assert "processor_info" in inst
        assert "ebs_info" in inst

    def test_format_instance_detail_with_storage(self, instance_with_storage):
        """Test JSON detail includes instance storage info"""
        formatter = JSONFormatter()
        result = formatter.format_instance_detail(instance_with_storage, "us-east-1")

        data = json.loads(result)
        inst = data["instance"]
        assert "instance_storage_info" in inst
        assert inst["instance_storage_info"]["total_size_gb"] == 475
        assert inst["instance_storage_info"]["nvme_support"] == "required"

    def test_format_regions(self, sample_regions):
        """Test JSON formatting of regions"""
        formatter = JSONFormatter()
        result = formatter.format_regions(sample_regions)

        data = json.loads(result)
        assert "regions" in data
        assert len(data["regions"]) == 3
        assert data["regions"][0]["code"] == "us-east-1"

    def test_format_regions_empty(self):
        """Test JSON formatting of empty regions"""
        formatter = JSONFormatter()
        result = formatter.format_regions([])

        data = json.loads(result)
        assert data["regions"] == []

    def test_format_pricing(self, instance_with_pricing):
        """Test JSON formatting of pricing"""
        formatter = JSONFormatter()
        result = formatter.format_pricing(instance_with_pricing, "us-east-1")

        data = json.loads(result)
        assert data["region"] == "us-east-1"
        assert data["instance_type"] == "m5.large"
        assert data["pricing"]["on_demand_price_per_hour"] == 0.096
        assert data["pricing"]["spot_price_per_hour"] == 0.038
        assert "monthly_cost" in data["pricing"]
        assert "annual_cost" in data["pricing"]

    def test_format_pricing_no_pricing(self, instance_no_pricing):
        """Test JSON formatting when no pricing available"""
        formatter = JSONFormatter()
        result = formatter.format_pricing(instance_no_pricing, "us-east-1")

        data = json.loads(result)
        assert data["pricing"] == {}

    def test_format_comparison(self, basic_instance, instance_with_pricing):
        """Test JSON formatting of comparison"""
        formatter = JSONFormatter()
        result = formatter.format_comparison(basic_instance, instance_with_pricing, "us-east-1")

        data = json.loads(result)
        assert data["region"] == "us-east-1"
        assert "comparison" in data
        assert "t3.micro" in data["comparison"]
        assert "m5.large" in data["comparison"]

        t3 = data["comparison"]["t3.micro"]
        m5 = data["comparison"]["m5.large"]
        assert t3["vcpu"] == 2
        assert m5["memory_gb"] == 8.0

    def test_json_is_valid(self, basic_instance, instance_with_pricing, sample_regions):
        """Test all JSON outputs are valid JSON"""
        formatter = JSONFormatter()

        # All these should parse without errors
        json.loads(formatter.format_instance_list([basic_instance], "us-east-1"))
        json.loads(formatter.format_instance_detail(basic_instance, "us-east-1"))
        json.loads(formatter.format_regions(sample_regions))
        json.loads(formatter.format_pricing(instance_with_pricing, "us-east-1"))
        json.loads(formatter.format_comparison(basic_instance, instance_with_pricing, "us-east-1"))

    def test_free_tier_included(self):
        """Test that free tier eligibility is included in JSON"""
        formatter = JSONFormatter()

        # t2.micro is free tier eligible
        free_tier_instance = InstanceType(
            instance_type="t2.micro",
            vcpu_info=VCpuInfo(default_vcpus=1),
            memory_info=MemoryInfo(size_in_mib=1024),
            network_info=NetworkInfo(
                network_performance="Low to Moderate",
                maximum_network_interfaces=2,
                maximum_ipv4_addresses_per_interface=2,
                maximum_ipv6_addresses_per_interface=2
            ),
            processor_info=ProcessorInfo(supported_architectures=["x86_64"]),
            ebs_info=EbsInfo(ebs_optimized_support="unsupported"),
            current_generation=True,
            burstable_performance_supported=True,
            hibernation_supported=False,
            pricing=PricingInfo(on_demand_price=0.0116, spot_price=0.0035)
        )

        result = formatter.format_instance_list([free_tier_instance], "us-east-1")
        data = json.loads(result)
        assert data["instances"][0]["free_tier_eligible"] is True


# =============================================================================
# Test CSVFormatter
# =============================================================================

class TestCSVFormatter:
    """Tests for CSVFormatter"""

    def test_format_instance_list_basic(self, basic_instance):
        """Test CSV formatting of instance list"""
        formatter = CSVFormatter()
        result = formatter.format_instance_list([basic_instance], "us-east-1")

        # Parse CSV
        reader = csv.reader(StringIO(result))
        rows = list(reader)

        # Check header
        assert rows[0][0] == "Instance Type"
        assert "vCPU" in rows[0]
        assert "Memory (GB)" in rows[0]

        # Check data row
        assert rows[1][0] == "t3.micro"
        assert rows[1][1] == "2"  # vCPU

    def test_format_instance_list_empty(self):
        """Test CSV formatting of empty instance list"""
        formatter = CSVFormatter()
        result = formatter.format_instance_list([], "us-east-1")

        assert result == ""

    def test_format_instance_list_multiple(self, basic_instance, instance_with_pricing):
        """Test CSV formatting of multiple instances"""
        formatter = CSVFormatter()
        result = formatter.format_instance_list([basic_instance, instance_with_pricing], "us-east-1")

        reader = csv.reader(StringIO(result))
        rows = list(reader)

        assert len(rows) == 3  # 1 header + 2 data rows
        assert rows[1][0] == "t3.micro"
        assert rows[2][0] == "m5.large"

    def test_format_instance_list_with_pricing(self, instance_with_pricing):
        """Test CSV formatting includes pricing columns"""
        formatter = CSVFormatter()
        result = formatter.format_instance_list([instance_with_pricing], "us-east-1")

        reader = csv.reader(StringIO(result))
        rows = list(reader)
        header = rows[0]

        assert "On-Demand Price/hr" in header
        assert "Spot Price/hr" in header
        assert "Monthly Cost" in header
        assert "Annual Cost" in header

        # Check pricing values
        price_idx = header.index("On-Demand Price/hr")
        assert rows[1][price_idx] == "0.096"

    def test_format_instance_list_no_pricing(self, instance_no_pricing):
        """Test CSV formatting handles missing pricing"""
        formatter = CSVFormatter()
        result = formatter.format_instance_list([instance_no_pricing], "us-east-1")

        reader = csv.reader(StringIO(result))
        rows = list(reader)
        header = rows[0]

        # Price columns should be empty
        price_idx = header.index("On-Demand Price/hr")
        assert rows[1][price_idx] == ""

    def test_format_instance_list_free_tier_column(self):
        """Test CSV includes free tier column"""
        formatter = CSVFormatter()

        free_tier_instance = InstanceType(
            instance_type="t2.micro",
            vcpu_info=VCpuInfo(default_vcpus=1),
            memory_info=MemoryInfo(size_in_mib=1024),
            network_info=NetworkInfo(
                network_performance="Low to Moderate",
                maximum_network_interfaces=2,
                maximum_ipv4_addresses_per_interface=2,
                maximum_ipv6_addresses_per_interface=2
            ),
            processor_info=ProcessorInfo(supported_architectures=["x86_64"]),
            ebs_info=EbsInfo(ebs_optimized_support="unsupported"),
            current_generation=True,
            burstable_performance_supported=True,
            hibernation_supported=False,
            pricing=PricingInfo(on_demand_price=0.0116, spot_price=0.0035)
        )

        result = formatter.format_instance_list([free_tier_instance], "us-east-1")
        reader = csv.reader(StringIO(result))
        rows = list(reader)
        header = rows[0]

        assert "Free Tier Eligible" in header
        ft_idx = header.index("Free Tier Eligible")
        assert rows[1][ft_idx] == "Yes"

    def test_format_instance_detail(self, basic_instance):
        """Test CSV detail format returns instance list format"""
        formatter = CSVFormatter()
        result = formatter.format_instance_detail(basic_instance, "us-east-1")

        # CSV detail is same as single-item list
        reader = csv.reader(StringIO(result))
        rows = list(reader)

        assert len(rows) == 2  # header + 1 row
        assert rows[1][0] == "t3.micro"

    def test_format_regions(self, sample_regions):
        """Test CSV formatting of regions"""
        formatter = CSVFormatter()
        result = formatter.format_regions(sample_regions)

        reader = csv.reader(StringIO(result))
        rows = list(reader)

        assert rows[0] == ["Region Code", "Region Name"]
        assert rows[1][0] == "us-east-1"
        assert rows[1][1] == "US East (N. Virginia)"
        assert len(rows) == 4  # header + 3 regions

    def test_format_regions_empty(self):
        """Test CSV formatting of empty regions"""
        formatter = CSVFormatter()
        result = formatter.format_regions([])

        reader = csv.reader(StringIO(result))
        rows = list(reader)

        assert len(rows) == 1  # Only header
        assert rows[0] == ["Region Code", "Region Name"]

    def test_format_pricing(self, instance_with_pricing):
        """Test CSV formatting of pricing"""
        formatter = CSVFormatter()
        result = formatter.format_pricing(instance_with_pricing, "us-east-1")

        reader = csv.reader(StringIO(result))
        rows = list(reader)

        assert rows[0] == ["Instance Type", "Region", "On-Demand Price/hr", "Spot Price/hr", "Monthly Cost", "Annual Cost"]
        assert rows[1][0] == "m5.large"
        assert rows[1][1] == "us-east-1"
        assert rows[1][2] == "0.096"
        assert rows[1][3] == "0.038"

    def test_format_pricing_no_pricing(self, instance_no_pricing):
        """Test CSV formatting when no pricing available"""
        formatter = CSVFormatter()
        result = formatter.format_pricing(instance_no_pricing, "us-east-1")

        reader = csv.reader(StringIO(result))
        rows = list(reader)

        assert rows[1][2] == ""  # On-demand price empty
        assert rows[1][3] == ""  # Spot price empty

    def test_format_comparison(self, basic_instance, instance_with_pricing):
        """Test CSV formatting of comparison"""
        formatter = CSVFormatter()
        result = formatter.format_comparison(basic_instance, instance_with_pricing, "us-east-1")

        reader = csv.reader(StringIO(result))
        rows = list(reader)

        # Comparison is two rows in list format
        assert len(rows) == 3  # header + 2 instances
        assert rows[1][0] == "t3.micro"
        assert rows[2][0] == "m5.large"

    def test_csv_is_valid(self, basic_instance, instance_with_pricing, sample_regions):
        """Test all CSV outputs are valid CSV"""
        formatter = CSVFormatter()

        # All these should parse without errors
        for result in [
            formatter.format_instance_list([basic_instance], "us-east-1"),
            formatter.format_instance_detail(basic_instance, "us-east-1"),
            formatter.format_regions(sample_regions),
            formatter.format_pricing(instance_with_pricing, "us-east-1"),
            formatter.format_comparison(basic_instance, instance_with_pricing, "us-east-1"),
        ]:
            if result:  # Some may be empty
                list(csv.reader(StringIO(result)))

    def test_csv_memory_precision(self, basic_instance):
        """Test CSV memory values have correct precision"""
        formatter = CSVFormatter()
        result = formatter.format_instance_list([basic_instance], "us-east-1")

        reader = csv.reader(StringIO(result))
        rows = list(reader)
        header = rows[0]

        mem_idx = header.index("Memory (GB)")
        # 1024 MiB = 1.0 GB
        assert rows[1][mem_idx] == "1.00"


# =============================================================================
# Test TableFormatter
# =============================================================================

class TestTableFormatter:
    """Tests for TableFormatter"""

    def test_format_instance_list_basic(self, basic_instance):
        """Test table formatting of instance list"""
        formatter = TableFormatter()
        result = formatter.format_instance_list([basic_instance], "us-east-1")

        assert "t3.micro" in result
        assert "Instance Type" in result
        assert "vCPU" in result
        assert "Memory" in result

    def test_format_instance_list_empty(self):
        """Test table formatting of empty list"""
        formatter = TableFormatter()
        result = formatter.format_instance_list([], "us-east-1")

        assert "No instance types found" in result
        assert "us-east-1" in result

    def test_format_instance_list_with_pricing(self, instance_with_pricing):
        """Test table formatting includes pricing"""
        formatter = TableFormatter()
        result = formatter.format_instance_list([instance_with_pricing], "us-east-1")

        assert "$0.0960" in result

    def test_format_instance_list_no_pricing(self, instance_no_pricing):
        """Test table formatting shows N/A for missing pricing"""
        formatter = TableFormatter()
        result = formatter.format_instance_list([instance_no_pricing], "us-east-1")

        assert "N/A" in result

    def test_format_instance_detail(self, basic_instance):
        """Test table formatting of instance detail"""
        formatter = TableFormatter()
        result = formatter.format_instance_detail(basic_instance, "us-east-1")

        assert "Instance Type: t3.micro" in result
        assert "Region: us-east-1" in result
        assert "vCPU: 2" in result
        assert "Memory:" in result
        assert "Network:" in result
        assert "Processor:" in result
        assert "Storage:" in result
        assert "Features:" in result

    def test_format_instance_detail_with_pricing(self, instance_with_pricing):
        """Test table detail includes pricing section"""
        formatter = TableFormatter()
        result = formatter.format_instance_detail(instance_with_pricing, "us-east-1")

        assert "Pricing:" in result
        assert "On-Demand:" in result
        assert "Spot:" in result
        assert "Savings Plan" in result
        assert "Reserved Instances" in result

    def test_format_instance_detail_reserved_instances(self, instance_with_pricing):
        """Test table detail shows all RI options"""
        formatter = TableFormatter()
        result = formatter.format_instance_detail(instance_with_pricing, "us-east-1")

        assert "Reserved Instances (Standard, 1-Year):" in result
        assert "Reserved Instances (Standard, 3-Year):" in result
        assert "No Upfront:" in result
        assert "Partial Upfront:" in result
        assert "All Upfront:" in result

    def test_format_regions(self, sample_regions):
        """Test table formatting of regions"""
        formatter = TableFormatter()
        result = formatter.format_regions(sample_regions)

        assert "Region Code" in result
        assert "Region Name" in result
        assert "us-east-1" in result
        assert "US East (N. Virginia)" in result

    def test_format_regions_empty(self):
        """Test table formatting of empty regions"""
        formatter = TableFormatter()
        result = formatter.format_regions([])

        assert "No regions available" in result

    def test_format_pricing(self, instance_with_pricing):
        """Test table formatting of pricing"""
        formatter = TableFormatter()
        result = formatter.format_pricing(instance_with_pricing, "us-east-1")

        assert "Pricing for m5.large" in result
        assert "us-east-1" in result
        assert "On-Demand:" in result
        assert "Spot:" in result
        assert "Monthly" in result

    def test_format_pricing_no_pricing(self, instance_no_pricing):
        """Test table formatting when no pricing available"""
        formatter = TableFormatter()
        result = formatter.format_pricing(instance_no_pricing, "us-east-1")

        assert "not available" in result

    def test_format_comparison(self, basic_instance, instance_with_pricing):
        """Test table formatting of comparison"""
        formatter = TableFormatter()
        result = formatter.format_comparison(basic_instance, instance_with_pricing, "us-east-1")

        assert "t3.micro" in result
        assert "m5.large" in result
        assert "Property" in result
        assert "vCPU" in result
        assert "Memory" in result

    def test_free_tier_emoji(self):
        """Test free tier emoji appears for eligible instances"""
        formatter = TableFormatter()

        free_tier_instance = InstanceType(
            instance_type="t2.micro",
            vcpu_info=VCpuInfo(default_vcpus=1),
            memory_info=MemoryInfo(size_in_mib=1024),
            network_info=NetworkInfo(
                network_performance="Low to Moderate",
                maximum_network_interfaces=2,
                maximum_ipv4_addresses_per_interface=2,
                maximum_ipv6_addresses_per_interface=2
            ),
            processor_info=ProcessorInfo(supported_architectures=["x86_64"]),
            ebs_info=EbsInfo(ebs_optimized_support="unsupported"),
            current_generation=True,
            burstable_performance_supported=True,
            hibernation_supported=False,
            pricing=PricingInfo(on_demand_price=0.0116, spot_price=0.0035)
        )

        result = formatter.format_instance_list([free_tier_instance], "us-east-1")
        assert "🆓" in result

    def test_format_instance_detail_with_storage(self, instance_with_storage):
        """Test table detail shows instance storage"""
        formatter = TableFormatter()
        result = formatter.format_instance_detail(instance_with_storage, "us-east-1")

        assert "Instance Store:" in result
        assert "475" in result
        assert "NVMe Support:" in result


# =============================================================================
# Test Edge Cases
# =============================================================================

class TestFormatterEdgeCases:
    """Tests for edge cases across formatters"""

    def test_json_special_characters(self):
        """Test JSON handles special characters"""
        formatter = JSONFormatter()

        instance = InstanceType(
            instance_type="t3.micro",
            vcpu_info=VCpuInfo(default_vcpus=2),
            memory_info=MemoryInfo(size_in_mib=1024),
            network_info=NetworkInfo(
                network_performance='Up to 5 Gigabit "fast"',  # Quotes
                maximum_network_interfaces=2,
                maximum_ipv4_addresses_per_interface=2,
                maximum_ipv6_addresses_per_interface=2
            ),
            processor_info=ProcessorInfo(supported_architectures=["x86_64"]),
            ebs_info=EbsInfo(ebs_optimized_support="supported"),
            current_generation=True,
            burstable_performance_supported=True,
            hibernation_supported=False,
            pricing=None
        )

        result = formatter.format_instance_list([instance], "us-east-1")
        data = json.loads(result)  # Should not raise
        assert 'fast' in data["instances"][0]["network_performance"]

    def test_csv_commas_in_values(self):
        """Test CSV handles commas in values"""
        formatter = CSVFormatter()

        instance = InstanceType(
            instance_type="t3.micro",
            vcpu_info=VCpuInfo(default_vcpus=2),
            memory_info=MemoryInfo(size_in_mib=1024),
            network_info=NetworkInfo(
                network_performance="Up to 5 Gigabit, burstable",  # Comma
                maximum_network_interfaces=2,
                maximum_ipv4_addresses_per_interface=2,
                maximum_ipv6_addresses_per_interface=2
            ),
            processor_info=ProcessorInfo(supported_architectures=["x86_64"]),
            ebs_info=EbsInfo(ebs_optimized_support="supported"),
            current_generation=True,
            burstable_performance_supported=True,
            hibernation_supported=False,
            pricing=None
        )

        result = formatter.format_instance_list([instance], "us-east-1")
        reader = csv.reader(StringIO(result))
        rows = list(reader)

        # Value should be properly quoted/escaped
        assert "burstable" in rows[1][3]

    def test_large_memory_values(self):
        """Test formatting of large memory values"""
        formatter = JSONFormatter()

        instance = InstanceType(
            instance_type="x2idn.32xlarge",
            vcpu_info=VCpuInfo(default_vcpus=128),
            memory_info=MemoryInfo(size_in_mib=2097152),  # 2048 GB
            network_info=NetworkInfo(
                network_performance="100 Gigabit",
                maximum_network_interfaces=15,
                maximum_ipv4_addresses_per_interface=50,
                maximum_ipv6_addresses_per_interface=50
            ),
            processor_info=ProcessorInfo(supported_architectures=["x86_64"]),
            ebs_info=EbsInfo(ebs_optimized_support="default"),
            current_generation=True,
            burstable_performance_supported=False,
            hibernation_supported=False,
            pricing=PricingInfo(on_demand_price=13.34, spot_price=4.0)
        )

        result = formatter.format_instance_list([instance], "us-east-1")
        data = json.loads(result)

        assert data["instances"][0]["memory_gb"] == 2048.0

    def test_very_small_prices(self):
        """Test formatting of very small prices"""
        json_formatter = JSONFormatter()
        csv_formatter = CSVFormatter()

        instance = InstanceType(
            instance_type="t4g.nano",
            vcpu_info=VCpuInfo(default_vcpus=2),
            memory_info=MemoryInfo(size_in_mib=512),
            network_info=NetworkInfo(
                network_performance="Up to 5 Gigabit",
                maximum_network_interfaces=2,
                maximum_ipv4_addresses_per_interface=2,
                maximum_ipv6_addresses_per_interface=2
            ),
            processor_info=ProcessorInfo(supported_architectures=["arm64"]),
            ebs_info=EbsInfo(ebs_optimized_support="supported"),
            current_generation=True,
            burstable_performance_supported=True,
            hibernation_supported=False,
            pricing=PricingInfo(on_demand_price=0.0042, spot_price=0.0013)
        )

        json_result = json_formatter.format_instance_list([instance], "us-east-1")
        csv_result = csv_formatter.format_instance_list([instance], "us-east-1")

        json_data = json.loads(json_result)
        assert json_data["instances"][0]["pricing"]["on_demand_price_per_hour"] == 0.0042
        assert json_data["instances"][0]["pricing"]["spot_price_per_hour"] == 0.0013

        reader = csv.reader(StringIO(csv_result))
        rows = list(reader)
        assert "0.0042" in rows[1][4]  # On-demand price column
