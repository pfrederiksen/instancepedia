"""Tests for filter_service.py - unified filtering logic"""

import pytest
from unittest.mock import Mock, patch
from argparse import Namespace

from src.services.filter_service import (
    FilterCriteria,
    apply_filters,
    _is_amd_instance,
    _apply_processor_filter,
    _apply_network_filter,
    _map_cli_storage_type,
    _map_cli_network_performance,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_instance():
    """Create a basic mock instance for testing."""
    inst = Mock()
    inst.instance_type = "t3.micro"
    inst.vcpu_info = Mock()
    inst.vcpu_info.default_vcpus = 2
    inst.memory_info = Mock()
    inst.memory_info.size_in_gb = 1.0
    inst.current_generation = True
    inst.burstable_performance_supported = True
    inst.gpu_info = None
    inst.processor_info = Mock()
    inst.processor_info.supported_architectures = ["x86_64"]
    inst.network_info = Mock()
    inst.network_info.network_performance = "Up to 5 Gigabit"
    inst.instance_storage_info = None
    inst.pricing = None
    return inst


@pytest.fixture
def mock_instances():
    """Create a list of mock instances for testing filters."""
    instances = []

    # t3.micro - burstable, current gen, x86_64
    t3_micro = Mock()
    t3_micro.instance_type = "t3.micro"
    t3_micro.vcpu_info.default_vcpus = 2
    t3_micro.memory_info.size_in_gb = 1.0
    t3_micro.current_generation = True
    t3_micro.burstable_performance_supported = True
    t3_micro.gpu_info = None
    t3_micro.processor_info.supported_architectures = ["x86_64"]
    t3_micro.network_info.network_performance = "Up to 5 Gigabit"
    t3_micro.instance_storage_info = None
    t3_micro.pricing = None
    instances.append(t3_micro)

    # m5.large - current gen, higher specs, x86_64
    m5_large = Mock()
    m5_large.instance_type = "m5.large"
    m5_large.vcpu_info.default_vcpus = 2
    m5_large.memory_info.size_in_gb = 8.0
    m5_large.current_generation = True
    m5_large.burstable_performance_supported = False
    m5_large.gpu_info = None
    m5_large.processor_info.supported_architectures = ["x86_64"]
    m5_large.network_info.network_performance = "Up to 10 Gigabit"
    m5_large.instance_storage_info = None
    m5_large.pricing = Mock()
    m5_large.pricing.on_demand_price = 0.096
    instances.append(m5_large)

    # m5a.large - AMD instance
    m5a_large = Mock()
    m5a_large.instance_type = "m5a.large"
    m5a_large.vcpu_info.default_vcpus = 2
    m5a_large.memory_info.size_in_gb = 8.0
    m5a_large.current_generation = True
    m5a_large.burstable_performance_supported = False
    m5a_large.gpu_info = None
    m5a_large.processor_info.supported_architectures = ["x86_64"]
    m5a_large.network_info.network_performance = "Up to 10 Gigabit"
    m5a_large.instance_storage_info = None
    m5a_large.pricing = Mock()
    m5a_large.pricing.on_demand_price = 0.086
    instances.append(m5a_large)

    # m6g.large - Graviton ARM
    m6g_large = Mock()
    m6g_large.instance_type = "m6g.large"
    m6g_large.vcpu_info.default_vcpus = 2
    m6g_large.memory_info.size_in_gb = 8.0
    m6g_large.current_generation = True
    m6g_large.burstable_performance_supported = False
    m6g_large.gpu_info = None
    m6g_large.processor_info.supported_architectures = ["arm64"]
    m6g_large.network_info.network_performance = "Up to 10 Gigabit"
    m6g_large.instance_storage_info = None
    m6g_large.pricing = Mock()
    m6g_large.pricing.on_demand_price = 0.077
    instances.append(m6g_large)

    # p3.2xlarge - GPU instance
    p3_2xlarge = Mock()
    p3_2xlarge.instance_type = "p3.2xlarge"
    p3_2xlarge.vcpu_info.default_vcpus = 8
    p3_2xlarge.memory_info.size_in_gb = 61.0
    p3_2xlarge.current_generation = True
    p3_2xlarge.burstable_performance_supported = False
    p3_2xlarge.gpu_info = Mock()
    p3_2xlarge.gpu_info.total_gpu_count = 1
    p3_2xlarge.processor_info.supported_architectures = ["x86_64"]
    p3_2xlarge.network_info.network_performance = "Up to 10 Gigabit"
    p3_2xlarge.instance_storage_info = None
    p3_2xlarge.pricing = Mock()
    p3_2xlarge.pricing.on_demand_price = 3.06
    instances.append(p3_2xlarge)

    # i3.large - instance storage with NVMe
    i3_large = Mock()
    i3_large.instance_type = "i3.large"
    i3_large.vcpu_info.default_vcpus = 2
    i3_large.memory_info.size_in_gb = 15.25
    i3_large.current_generation = True
    i3_large.burstable_performance_supported = False
    i3_large.gpu_info = None
    i3_large.processor_info.supported_architectures = ["x86_64"]
    i3_large.network_info.network_performance = "Up to 10 Gigabit"
    i3_large.instance_storage_info = Mock()
    i3_large.instance_storage_info.total_size_in_gb = 475
    i3_large.instance_storage_info.nvme_support = "required"
    i3_large.pricing = Mock()
    i3_large.pricing.on_demand_price = 0.156
    instances.append(i3_large)

    # c4.large - previous generation
    c4_large = Mock()
    c4_large.instance_type = "c4.large"
    c4_large.vcpu_info.default_vcpus = 2
    c4_large.memory_info.size_in_gb = 3.75
    c4_large.current_generation = False
    c4_large.burstable_performance_supported = False
    c4_large.gpu_info = None
    c4_large.processor_info.supported_architectures = ["x86_64"]
    c4_large.network_info.network_performance = "Moderate"
    c4_large.instance_storage_info = None
    c4_large.pricing = Mock()
    c4_large.pricing.on_demand_price = 0.10
    instances.append(c4_large)

    # c5n.18xlarge - high network
    c5n_18xlarge = Mock()
    c5n_18xlarge.instance_type = "c5n.18xlarge"
    c5n_18xlarge.vcpu_info.default_vcpus = 72
    c5n_18xlarge.memory_info.size_in_gb = 192.0
    c5n_18xlarge.current_generation = True
    c5n_18xlarge.burstable_performance_supported = False
    c5n_18xlarge.gpu_info = None
    c5n_18xlarge.processor_info.supported_architectures = ["x86_64"]
    c5n_18xlarge.network_info.network_performance = "100 Gigabit"
    c5n_18xlarge.instance_storage_info = None
    c5n_18xlarge.pricing = Mock()
    c5n_18xlarge.pricing.on_demand_price = 3.888
    instances.append(c5n_18xlarge)

    return instances


# =============================================================================
# FilterCriteria Tests
# =============================================================================

class TestFilterCriteriaInit:
    """Test FilterCriteria initialization"""

    def test_default_values(self):
        """Test default filter values"""
        criteria = FilterCriteria()

        assert criteria.search is None
        assert criteria.min_vcpu is None
        assert criteria.max_vcpu is None
        assert criteria.min_memory_gb is None
        assert criteria.max_memory_gb is None
        assert criteria.gpu_filter == "any"
        assert criteria.current_generation == "any"
        assert criteria.burstable == "any"
        assert criteria.free_tier == "any"
        assert criteria.architecture == "any"
        assert criteria.processor_family == "any"
        assert criteria.network_performance == "any"
        assert criteria.family_filter == ""
        assert criteria.storage_type == "any"
        assert criteria.nvme_support == "any"
        assert criteria.min_price is None
        assert criteria.max_price is None

    def test_custom_values(self):
        """Test creating criteria with custom values"""
        criteria = FilterCriteria(
            search="t3",
            min_vcpu=4,
            max_vcpu=16,
            min_memory_gb=8.0,
            gpu_filter="yes",
            processor_family="graviton"
        )

        assert criteria.search == "t3"
        assert criteria.min_vcpu == 4
        assert criteria.max_vcpu == 16
        assert criteria.min_memory_gb == 8.0
        assert criteria.gpu_filter == "yes"
        assert criteria.processor_family == "graviton"


class TestFilterCriteriaToDict:
    """Test FilterCriteria.to_dict()"""

    def test_to_dict_default(self):
        """Test to_dict with default values"""
        criteria = FilterCriteria()
        result = criteria.to_dict()

        assert result["search"] is None
        assert result["min_vcpu"] is None
        assert result["gpu_filter"] == "any"
        assert result["family_filter"] == ""
        assert len(result) == 17  # All fields present

    def test_to_dict_with_values(self):
        """Test to_dict with custom values"""
        criteria = FilterCriteria(search="m5", min_vcpu=4, gpu_filter="yes")
        result = criteria.to_dict()

        assert result["search"] == "m5"
        assert result["min_vcpu"] == 4
        assert result["gpu_filter"] == "yes"


class TestFilterCriteriaFromDict:
    """Test FilterCriteria.from_dict()"""

    def test_from_dict_full(self):
        """Test from_dict with all values"""
        data = {
            "search": "c5",
            "min_vcpu": 8,
            "max_vcpu": 32,
            "min_memory_gb": 16.0,
            "max_memory_gb": 64.0,
            "gpu_filter": "no",
            "current_generation": "yes",
            "burstable": "no",
            "free_tier": "any",
            "architecture": "x86_64",
            "processor_family": "intel",
            "network_performance": "high",
            "family_filter": "c5,c6i",
            "storage_type": "ebs_only",
            "nvme_support": "any",
            "min_price": 0.1,
            "max_price": 1.0,
        }
        criteria = FilterCriteria.from_dict(data)

        assert criteria.search == "c5"
        assert criteria.min_vcpu == 8
        assert criteria.max_vcpu == 32
        assert criteria.gpu_filter == "no"
        assert criteria.family_filter == "c5,c6i"
        assert criteria.min_price == 0.1

    def test_from_dict_partial(self):
        """Test from_dict with partial values uses defaults"""
        data = {"search": "t3", "min_vcpu": 2}
        criteria = FilterCriteria.from_dict(data)

        assert criteria.search == "t3"
        assert criteria.min_vcpu == 2
        assert criteria.gpu_filter == "any"  # Default
        assert criteria.architecture == "any"  # Default

    def test_from_dict_empty(self):
        """Test from_dict with empty dict"""
        criteria = FilterCriteria.from_dict({})

        assert criteria.search is None
        assert criteria.gpu_filter == "any"

    def test_to_from_dict_roundtrip(self):
        """Test that to_dict/from_dict roundtrip preserves data"""
        original = FilterCriteria(
            search="m5",
            min_vcpu=4,
            max_memory_gb=32.0,
            gpu_filter="yes",
            processor_family="amd"
        )
        data = original.to_dict()
        restored = FilterCriteria.from_dict(data)

        assert restored.search == original.search
        assert restored.min_vcpu == original.min_vcpu
        assert restored.max_memory_gb == original.max_memory_gb
        assert restored.gpu_filter == original.gpu_filter
        assert restored.processor_family == original.processor_family


class TestFilterCriteriaFromCliArgs:
    """Test FilterCriteria.from_cli_args()"""

    def test_from_cli_args_basic(self):
        """Test from_cli_args with basic args"""
        args = Namespace(
            search="t3",
            free_tier_only=True,
            family="m5",
            storage_type=None,
            nvme=None,
            processor_family=None,
            network_performance=None,
            min_price=None,
            max_price=None,
        )
        criteria = FilterCriteria.from_cli_args(args)

        assert criteria.search == "t3"
        assert criteria.free_tier == "yes"
        assert criteria.family_filter == "m5"

    def test_from_cli_args_storage_type_mapping(self):
        """Test storage type CLI to internal mapping"""
        args = Namespace(
            search=None,
            free_tier_only=False,
            family=None,
            storage_type="ebs-only",
            nvme=None,
            processor_family=None,
            network_performance=None,
            min_price=None,
            max_price=None,
        )
        criteria = FilterCriteria.from_cli_args(args)

        assert criteria.storage_type == "ebs_only"

    def test_from_cli_args_instance_store(self):
        """Test instance-store mapping"""
        args = Namespace(
            search=None,
            free_tier_only=False,
            family=None,
            storage_type="instance-store",
            nvme=None,
            processor_family=None,
            network_performance=None,
            min_price=None,
            max_price=None,
        )
        criteria = FilterCriteria.from_cli_args(args)

        assert criteria.storage_type == "has_instance_store"

    def test_from_cli_args_network_performance_mapping(self):
        """Test network performance very-high to very_high mapping"""
        args = Namespace(
            search=None,
            free_tier_only=False,
            family=None,
            storage_type=None,
            nvme=None,
            processor_family=None,
            network_performance="very-high",
            min_price=None,
            max_price=None,
        )
        criteria = FilterCriteria.from_cli_args(args)

        assert criteria.network_performance == "very_high"

    def test_from_cli_args_missing_attrs(self):
        """Test from_cli_args handles missing attributes"""
        args = Namespace()  # Empty namespace
        criteria = FilterCriteria.from_cli_args(args)

        assert criteria.search is None
        assert criteria.free_tier == "any"
        assert criteria.family_filter == ""


class TestFilterCriteriaHasActiveFilters:
    """Test FilterCriteria.has_active_filters()"""

    def test_no_active_filters(self):
        """Test has_active_filters with defaults"""
        criteria = FilterCriteria()
        assert criteria.has_active_filters() is False

    def test_search_active(self):
        """Test search filter is active"""
        criteria = FilterCriteria(search="t3")
        assert criteria.has_active_filters() is True

    def test_min_vcpu_active(self):
        """Test min_vcpu filter is active"""
        criteria = FilterCriteria(min_vcpu=4)
        assert criteria.has_active_filters() is True

    def test_gpu_filter_active(self):
        """Test gpu_filter is active when not 'any'"""
        criteria = FilterCriteria(gpu_filter="yes")
        assert criteria.has_active_filters() is True

    def test_family_filter_active(self):
        """Test family_filter is active"""
        criteria = FilterCriteria(family_filter="m5,c5")
        assert criteria.has_active_filters() is True

    def test_family_filter_whitespace_only(self):
        """Test family_filter with only whitespace is not active"""
        criteria = FilterCriteria(family_filter="   ")
        assert criteria.has_active_filters() is False

    def test_price_filter_active(self):
        """Test price filter is active"""
        criteria = FilterCriteria(max_price=1.0)
        assert criteria.has_active_filters() is True


class TestFilterCriteriaReset:
    """Test FilterCriteria.reset()"""

    def test_reset_clears_all(self):
        """Test reset clears all filters"""
        criteria = FilterCriteria(
            search="t3",
            min_vcpu=4,
            max_vcpu=16,
            gpu_filter="yes",
            processor_family="amd",
            family_filter="m5,c5",
            min_price=0.1,
        )

        criteria.reset()

        assert criteria.search is None
        assert criteria.min_vcpu is None
        assert criteria.max_vcpu is None
        assert criteria.gpu_filter == "any"
        assert criteria.processor_family == "any"
        assert criteria.family_filter == ""
        assert criteria.min_price is None
        assert criteria.has_active_filters() is False


# =============================================================================
# Mapping Function Tests
# =============================================================================

class TestMapCliStorageType:
    """Test _map_cli_storage_type()"""

    def test_none_returns_any(self):
        """Test None input returns 'any'"""
        assert _map_cli_storage_type(None) == "any"

    def test_empty_returns_any(self):
        """Test empty string returns 'any'"""
        assert _map_cli_storage_type("") == "any"

    def test_ebs_only_mapping(self):
        """Test ebs-only maps correctly"""
        assert _map_cli_storage_type("ebs-only") == "ebs_only"

    def test_instance_store_mapping(self):
        """Test instance-store maps correctly"""
        assert _map_cli_storage_type("instance-store") == "has_instance_store"

    def test_unknown_returns_any(self):
        """Test unknown value returns 'any'"""
        assert _map_cli_storage_type("unknown") == "any"


class TestMapCliNetworkPerformance:
    """Test _map_cli_network_performance()"""

    def test_none_returns_any(self):
        """Test None input returns 'any'"""
        assert _map_cli_network_performance(None) == "any"

    def test_empty_returns_any(self):
        """Test empty string returns 'any'"""
        assert _map_cli_network_performance("") == "any"

    def test_very_high_mapping(self):
        """Test very-high maps to very_high"""
        assert _map_cli_network_performance("very-high") == "very_high"

    def test_passthrough_values(self):
        """Test other values pass through unchanged"""
        assert _map_cli_network_performance("low") == "low"
        assert _map_cli_network_performance("moderate") == "moderate"
        assert _map_cli_network_performance("high") == "high"


# =============================================================================
# Helper Function Tests
# =============================================================================

class TestIsAmdInstance:
    """Test _is_amd_instance()"""

    def test_amd_instances(self):
        """Test AMD instances are detected"""
        assert _is_amd_instance("m5a.large") is True
        assert _is_amd_instance("c5a.xlarge") is True
        assert _is_amd_instance("r5a.2xlarge") is True
        assert _is_amd_instance("t3a.micro") is True

    def test_non_amd_instances(self):
        """Test non-AMD instances are not detected"""
        assert _is_amd_instance("m5.large") is False
        assert _is_amd_instance("c5.xlarge") is False
        assert _is_amd_instance("t3.micro") is False

    def test_graviton_not_amd(self):
        """Test Graviton instances (ending in 'g' or 'ga') are not AMD"""
        assert _is_amd_instance("m6g.large") is False
        assert _is_amd_instance("c6g.xlarge") is False
        assert _is_amd_instance("m6ga.large") is False  # 'ga' suffix should not match

    def test_edge_cases(self):
        """Test edge cases"""
        # a1 family is actually Graviton (ARM), not AMD - ends with '1' not 'a'
        assert _is_amd_instance("a1.medium") is False
        assert _is_amd_instance("") is False
        assert _is_amd_instance("invalid") is False


class TestApplyProcessorFilter:
    """Test _apply_processor_filter()"""

    def test_intel_filter(self, mock_instances):
        """Test Intel filter excludes AMD and ARM"""
        result = _apply_processor_filter(mock_instances, "intel")

        # Should include: t3.micro, m5.large, p3.2xlarge, i3.large, c4.large, c5n.18xlarge
        # Should exclude: m5a.large (AMD), m6g.large (ARM)
        instance_types = [i.instance_type for i in result]
        assert "m5a.large" not in instance_types
        assert "m6g.large" not in instance_types
        assert "m5.large" in instance_types
        assert "t3.micro" in instance_types

    def test_amd_filter(self, mock_instances):
        """Test AMD filter only includes AMD instances"""
        result = _apply_processor_filter(mock_instances, "amd")

        instance_types = [i.instance_type for i in result]
        assert instance_types == ["m5a.large"]

    def test_graviton_filter(self, mock_instances):
        """Test Graviton filter only includes ARM instances"""
        result = _apply_processor_filter(mock_instances, "graviton")

        instance_types = [i.instance_type for i in result]
        assert instance_types == ["m6g.large"]

    def test_any_filter_returns_all(self, mock_instances):
        """Test 'any' filter returns all instances"""
        result = _apply_processor_filter(mock_instances, "any")
        assert len(result) == len(mock_instances)

    def test_unknown_filter_returns_all(self, mock_instances):
        """Test unknown filter returns all instances"""
        result = _apply_processor_filter(mock_instances, "unknown")
        assert len(result) == len(mock_instances)


class TestApplyNetworkFilter:
    """Test _apply_network_filter()"""

    def test_low_network_filter(self, mock_instances):
        """Test low network filter"""
        result = _apply_network_filter(mock_instances, "low")

        # Should match "Up to 5 Gigabit"
        instance_types = [i.instance_type for i in result]
        assert "t3.micro" in instance_types

    def test_moderate_network_filter(self, mock_instances):
        """Test moderate network filter"""
        result = _apply_network_filter(mock_instances, "moderate")

        # Should match "Moderate" and "up to 10 gigabit"
        instance_types = [i.instance_type for i in result]
        assert "c4.large" in instance_types
        assert "m5.large" in instance_types

    def test_very_high_network_filter(self, mock_instances):
        """Test very_high network filter"""
        result = _apply_network_filter(mock_instances, "very_high")

        # Should match "100 Gigabit"
        instance_types = [i.instance_type for i in result]
        assert "c5n.18xlarge" in instance_types
        assert "t3.micro" not in instance_types


# =============================================================================
# apply_filters() Tests
# =============================================================================

class TestApplyFiltersSearch:
    """Test apply_filters with search filter"""

    def test_search_filter(self, mock_instances):
        """Test search filter matches instance type"""
        criteria = FilterCriteria(search="m5")
        result = apply_filters(mock_instances, criteria)

        instance_types = [i.instance_type for i in result]
        assert "m5.large" in instance_types
        assert "m5a.large" in instance_types
        assert "t3.micro" not in instance_types

    def test_search_case_insensitive(self, mock_instances):
        """Test search is case insensitive"""
        criteria = FilterCriteria(search="M5")
        result = apply_filters(mock_instances, criteria)

        instance_types = [i.instance_type for i in result]
        assert "m5.large" in instance_types

    def test_search_partial_match(self, mock_instances):
        """Test search matches partial strings"""
        criteria = FilterCriteria(search="large")
        result = apply_filters(mock_instances, criteria)

        # All instances with 'large' in name
        for inst in result:
            assert "large" in inst.instance_type.lower()


class TestApplyFiltersVcpu:
    """Test apply_filters with vCPU filters"""

    def test_min_vcpu_filter(self, mock_instances):
        """Test min_vcpu filter"""
        criteria = FilterCriteria(min_vcpu=8)
        result = apply_filters(mock_instances, criteria)

        for inst in result:
            assert inst.vcpu_info.default_vcpus >= 8

    def test_max_vcpu_filter(self, mock_instances):
        """Test max_vcpu filter"""
        criteria = FilterCriteria(max_vcpu=4)
        result = apply_filters(mock_instances, criteria)

        for inst in result:
            assert inst.vcpu_info.default_vcpus <= 4

    def test_vcpu_range_filter(self, mock_instances):
        """Test combined min/max vCPU filter"""
        criteria = FilterCriteria(min_vcpu=2, max_vcpu=8)
        result = apply_filters(mock_instances, criteria)

        for inst in result:
            assert 2 <= inst.vcpu_info.default_vcpus <= 8


class TestApplyFiltersMemory:
    """Test apply_filters with memory filters"""

    def test_min_memory_filter(self, mock_instances):
        """Test min_memory_gb filter"""
        criteria = FilterCriteria(min_memory_gb=8.0)
        result = apply_filters(mock_instances, criteria)

        for inst in result:
            assert inst.memory_info.size_in_gb >= 8.0

    def test_max_memory_filter(self, mock_instances):
        """Test max_memory_gb filter"""
        criteria = FilterCriteria(max_memory_gb=16.0)
        result = apply_filters(mock_instances, criteria)

        for inst in result:
            assert inst.memory_info.size_in_gb <= 16.0


class TestApplyFiltersGpu:
    """Test apply_filters with GPU filter"""

    def test_gpu_yes_filter(self, mock_instances):
        """Test GPU yes filter"""
        criteria = FilterCriteria(gpu_filter="yes")
        result = apply_filters(mock_instances, criteria)

        # Only p3.2xlarge has GPU
        assert len(result) == 1
        assert result[0].instance_type == "p3.2xlarge"

    def test_gpu_no_filter(self, mock_instances):
        """Test GPU no filter"""
        criteria = FilterCriteria(gpu_filter="no")
        result = apply_filters(mock_instances, criteria)

        # Should exclude p3.2xlarge
        instance_types = [i.instance_type for i in result]
        assert "p3.2xlarge" not in instance_types
        assert len(result) == len(mock_instances) - 1


class TestApplyFiltersGeneration:
    """Test apply_filters with current generation filter"""

    def test_current_gen_yes_filter(self, mock_instances):
        """Test current generation yes filter"""
        criteria = FilterCriteria(current_generation="yes")
        result = apply_filters(mock_instances, criteria)

        for inst in result:
            assert inst.current_generation is True

        instance_types = [i.instance_type for i in result]
        assert "c4.large" not in instance_types

    def test_current_gen_no_filter(self, mock_instances):
        """Test current generation no filter (previous gen only)"""
        criteria = FilterCriteria(current_generation="no")
        result = apply_filters(mock_instances, criteria)

        # Only c4.large is previous gen
        assert len(result) == 1
        assert result[0].instance_type == "c4.large"


class TestApplyFiltersBurstable:
    """Test apply_filters with burstable filter"""

    def test_burstable_yes_filter(self, mock_instances):
        """Test burstable yes filter"""
        criteria = FilterCriteria(burstable="yes")
        result = apply_filters(mock_instances, criteria)

        # Only t3.micro is burstable
        assert len(result) == 1
        assert result[0].instance_type == "t3.micro"

    def test_burstable_no_filter(self, mock_instances):
        """Test burstable no filter"""
        criteria = FilterCriteria(burstable="no")
        result = apply_filters(mock_instances, criteria)

        # All except t3.micro
        instance_types = [i.instance_type for i in result]
        assert "t3.micro" not in instance_types


class TestApplyFiltersFreeTier:
    """Test apply_filters with free tier filter"""

    @patch('src.services.filter_service.FreeTierService')
    def test_free_tier_yes_filter(self, mock_free_tier_class, mock_instances):
        """Test free tier yes filter"""
        mock_service = Mock()
        mock_service.is_eligible.side_effect = lambda x: x == "t3.micro"
        mock_free_tier_class.return_value = mock_service

        criteria = FilterCriteria(free_tier="yes")
        result = apply_filters(mock_instances, criteria)

        # Only t3.micro is free tier eligible
        assert len(result) == 1
        assert result[0].instance_type == "t3.micro"

    @patch('src.services.filter_service.FreeTierService')
    def test_free_tier_no_filter(self, mock_free_tier_class, mock_instances):
        """Test free tier no filter"""
        mock_service = Mock()
        mock_service.is_eligible.side_effect = lambda x: x == "t3.micro"
        mock_free_tier_class.return_value = mock_service

        criteria = FilterCriteria(free_tier="no")
        result = apply_filters(mock_instances, criteria)

        # All except t3.micro
        instance_types = [i.instance_type for i in result]
        assert "t3.micro" not in instance_types


class TestApplyFiltersArchitecture:
    """Test apply_filters with architecture filter"""

    def test_x86_64_filter(self, mock_instances):
        """Test x86_64 architecture filter"""
        criteria = FilterCriteria(architecture="x86_64")
        result = apply_filters(mock_instances, criteria)

        # Should exclude m6g.large (arm64)
        instance_types = [i.instance_type for i in result]
        assert "m6g.large" not in instance_types
        assert "m5.large" in instance_types

    def test_arm64_filter(self, mock_instances):
        """Test arm64 architecture filter"""
        criteria = FilterCriteria(architecture="arm64")
        result = apply_filters(mock_instances, criteria)

        # Only m6g.large is arm64
        assert len(result) == 1
        assert result[0].instance_type == "m6g.large"


class TestApplyFiltersFamily:
    """Test apply_filters with family filter"""

    def test_single_family_filter(self, mock_instances):
        """Test single family filter"""
        criteria = FilterCriteria(family_filter="m5")
        result = apply_filters(mock_instances, criteria)

        instance_types = [i.instance_type for i in result]
        assert "m5.large" in instance_types
        assert "m5a.large" in instance_types
        assert "t3.micro" not in instance_types

    def test_multiple_family_filter(self, mock_instances):
        """Test multiple families filter"""
        criteria = FilterCriteria(family_filter="t3,m6g")
        result = apply_filters(mock_instances, criteria)

        instance_types = [i.instance_type for i in result]
        assert "t3.micro" in instance_types
        assert "m6g.large" in instance_types
        assert "m5.large" not in instance_types


class TestApplyFiltersStorage:
    """Test apply_filters with storage filters"""

    def test_ebs_only_filter(self, mock_instances):
        """Test EBS-only filter"""
        criteria = FilterCriteria(storage_type="ebs_only")
        result = apply_filters(mock_instances, criteria)

        # Should exclude i3.large which has instance storage
        instance_types = [i.instance_type for i in result]
        assert "i3.large" not in instance_types
        assert "m5.large" in instance_types

    def test_has_instance_store_filter(self, mock_instances):
        """Test has_instance_store filter"""
        criteria = FilterCriteria(storage_type="has_instance_store")
        result = apply_filters(mock_instances, criteria)

        # Only i3.large has instance storage
        assert len(result) == 1
        assert result[0].instance_type == "i3.large"


class TestApplyFiltersNvme:
    """Test apply_filters with NVMe filter"""

    def test_nvme_required_filter(self, mock_instances):
        """Test NVMe required filter"""
        criteria = FilterCriteria(nvme_support="required")
        result = apply_filters(mock_instances, criteria)

        # Only i3.large has NVMe required
        assert len(result) == 1
        assert result[0].instance_type == "i3.large"

    def test_nvme_unsupported_filter(self, mock_instances):
        """Test NVMe unsupported filter"""
        criteria = FilterCriteria(nvme_support="unsupported")
        result = apply_filters(mock_instances, criteria)

        # All except i3.large
        instance_types = [i.instance_type for i in result]
        assert "i3.large" not in instance_types


class TestApplyFiltersPrice:
    """Test apply_filters with price filters"""

    def test_min_price_filter(self, mock_instances):
        """Test min_price filter"""
        criteria = FilterCriteria(min_price=1.0)
        result = apply_filters(mock_instances, criteria)

        # Should include p3.2xlarge (3.06) and c5n.18xlarge (3.888)
        # Also includes instances with no pricing
        for inst in result:
            if inst.pricing and inst.pricing.on_demand_price is not None:
                assert inst.pricing.on_demand_price >= 1.0

    def test_max_price_filter(self, mock_instances):
        """Test max_price filter"""
        criteria = FilterCriteria(max_price=0.10)
        result = apply_filters(mock_instances, criteria)

        for inst in result:
            if inst.pricing and inst.pricing.on_demand_price is not None:
                assert inst.pricing.on_demand_price <= 0.10

    def test_price_filter_keeps_no_pricing(self, mock_instances):
        """Test price filter keeps instances without pricing"""
        criteria = FilterCriteria(max_price=0.01)  # Very low
        result = apply_filters(mock_instances, criteria)

        # t3.micro has no pricing, should be kept
        instance_types = [i.instance_type for i in result]
        assert "t3.micro" in instance_types


class TestApplyFiltersCombined:
    """Test apply_filters with combined filters"""

    def test_multiple_filters(self, mock_instances):
        """Test multiple filters combined"""
        criteria = FilterCriteria(
            min_vcpu=2,
            max_vcpu=8,
            current_generation="yes",
            gpu_filter="no"
        )
        result = apply_filters(mock_instances, criteria)

        for inst in result:
            assert 2 <= inst.vcpu_info.default_vcpus <= 8
            assert inst.current_generation is True
            assert inst.gpu_info is None or inst.gpu_info.total_gpu_count == 0

    def test_empty_result(self, mock_instances):
        """Test filters that produce empty result"""
        criteria = FilterCriteria(
            min_vcpu=100,  # No instance has 100+ vCPUs
        )
        result = apply_filters(mock_instances, criteria)

        assert len(result) == 0


class TestApplyFiltersEdgeCases:
    """Test apply_filters edge cases"""

    def test_empty_instances_list(self):
        """Test filtering empty list"""
        criteria = FilterCriteria(search="t3")
        result = apply_filters([], criteria)

        assert result == []

    def test_no_active_filters(self, mock_instances):
        """Test with no active filters returns all"""
        criteria = FilterCriteria()
        result = apply_filters(mock_instances, criteria)

        assert len(result) == len(mock_instances)

    def test_processor_and_arch_filter(self, mock_instances):
        """Test processor and architecture filters combined"""
        # Graviton = ARM
        criteria = FilterCriteria(
            processor_family="graviton",
            architecture="arm64"
        )
        result = apply_filters(mock_instances, criteria)

        assert len(result) == 1
        assert result[0].instance_type == "m6g.large"

    def test_conflicting_filters(self, mock_instances):
        """Test conflicting filters produce empty result"""
        # Graviton is ARM, but filtering for x86_64
        criteria = FilterCriteria(
            processor_family="graviton",
            architecture="x86_64"
        )
        result = apply_filters(mock_instances, criteria)

        assert len(result) == 0
