"""Tests for OptimizationService"""

import pytest
from unittest.mock import Mock

from src.services.optimization_service import (
    OptimizationService,
    OptimizationRecommendation,
    OptimizationReport
)
from src.models.instance_type import (
    InstanceType,
    VCpuInfo,
    MemoryInfo,
    NetworkInfo,
    ProcessorInfo,
    EbsInfo,
    PricingInfo
)


@pytest.fixture
def sample_instance():
    """Create a sample instance for testing"""
    return InstanceType(
        instance_type="t3.large",
        vcpu_info=VCpuInfo(default_vcpus=2, default_cores=1, default_threads_per_core=2),
        memory_info=MemoryInfo(size_in_mib=8192),
        network_info=NetworkInfo(
            network_performance="Up to 5 Gigabit",
            maximum_network_interfaces=3,
            maximum_ipv4_addresses_per_interface=12,
            maximum_ipv6_addresses_per_interface=12
        ),
        processor_info=ProcessorInfo(
            supported_architectures=["x86_64"],
            sustained_clock_speed_in_ghz=2.5
        ),
        ebs_info=EbsInfo(ebs_optimized_support="default"),
        current_generation=True,
        pricing=PricingInfo(
            on_demand_price=0.0832,
            spot_price=0.0250,  # 70% savings
            savings_plan_1yr_no_upfront=0.0540,  # 35% savings
            savings_plan_3yr_no_upfront=0.0350,  # 58% savings
            ri_1yr_no_upfront=0.0600,  # 28% savings
            ri_1yr_partial_upfront=0.0580,  # 30% savings
            ri_3yr_no_upfront=0.0400,  # 52% savings
            ri_3yr_partial_upfront=0.0380   # 54% savings
        )
    )


@pytest.fixture
def cheaper_alternative():
    """Create a cheaper alternative instance"""
    return InstanceType(
        instance_type="t3.medium",
        vcpu_info=VCpuInfo(default_vcpus=2, default_cores=1, default_threads_per_core=2),
        memory_info=MemoryInfo(size_in_mib=7168),  # 7 GB (within 20% of 8 GB = 6.4 GB minimum)
        network_info=NetworkInfo(
            network_performance="Up to 5 Gigabit",
            maximum_network_interfaces=3,
            maximum_ipv4_addresses_per_interface=12,
            maximum_ipv6_addresses_per_interface=12
        ),
        processor_info=ProcessorInfo(
            supported_architectures=["x86_64"],
            sustained_clock_speed_in_ghz=2.5
        ),
        ebs_info=EbsInfo(ebs_optimized_support="default"),
        current_generation=True,
        pricing=PricingInfo(
            on_demand_price=0.0416  # Half the price
        )
    )


@pytest.fixture
def optimizer(sample_instance, cheaper_alternative):
    """Create OptimizationService with sample instances"""
    instances = [sample_instance, cheaper_alternative]
    return OptimizationService(instances, "us-east-1")


class TestOptimizationServiceInit:
    """Test OptimizationService initialization"""

    def test_init_with_instances(self, sample_instance):
        """Test initialization with instance list"""
        instances = [sample_instance]
        service = OptimizationService(instances, "us-east-1")

        assert service.instances == instances
        assert service.region == "us-east-1"

    def test_init_empty_instances(self):
        """Test initialization with empty instance list"""
        service = OptimizationService([], "us-west-2")

        assert service.instances == []
        assert service.region == "us-west-2"


class TestAnalyzeInstance:
    """Test analyze_instance method"""

    def test_analyze_instance_no_pricing(self, optimizer):
        """Test analysis with instance that has no pricing"""
        instance = InstanceType(
            instance_type="test.instance",
            vcpu_info=VCpuInfo(default_vcpus=2, default_cores=1, default_threads_per_core=2),
            memory_info=MemoryInfo(size_in_mib=4096),
            network_info=NetworkInfo(
                network_performance="Moderate",
                maximum_network_interfaces=2,
                maximum_ipv4_addresses_per_interface=4,
                maximum_ipv6_addresses_per_interface=4
            ),
            processor_info=ProcessorInfo(supported_architectures=["x86_64"]),
            ebs_info=EbsInfo(ebs_optimized_support="default"),
            current_generation=True,
            pricing=None  # No pricing
        )

        report = optimizer.analyze_instance(instance)

        assert report.instance_type == "test.instance"
        assert report.region == "us-east-1"
        assert len(report.recommendations) == 0
        assert report.total_potential_savings == 0.0

    def test_analyze_instance_standard_usage(self, optimizer, sample_instance):
        """Test analysis with standard usage pattern"""
        report = optimizer.analyze_instance(sample_instance, "standard")

        assert report.instance_type == "t3.large"
        assert report.region == "us-east-1"
        assert len(report.recommendations) > 0
        assert report.total_potential_savings > 0

        # Should include spot recommendation (70% savings)
        spot_recs = [r for r in report.recommendations if r.recommendation_type == "spot"]
        assert len(spot_recs) == 1
        assert spot_recs[0].savings_percentage >= 30

    def test_analyze_instance_continuous_usage(self, optimizer, sample_instance):
        """Test analysis with continuous usage pattern (no spot)"""
        report = optimizer.analyze_instance(sample_instance, "continuous")

        assert report.instance_type == "t3.large"

        # Should NOT include spot recommendation
        spot_recs = [r for r in report.recommendations if r.recommendation_type == "spot"]
        assert len(spot_recs) == 0

    def test_analyze_instance_burst_usage(self, optimizer, sample_instance):
        """Test analysis with burst usage pattern"""
        report = optimizer.analyze_instance(sample_instance, "burst")

        assert report.instance_type == "t3.large"

        # Should include spot recommendation for burst workloads
        spot_recs = [r for r in report.recommendations if r.recommendation_type == "spot"]
        assert len(spot_recs) == 1

    def test_recommendations_sorted_by_savings(self, optimizer, sample_instance):
        """Test that recommendations are sorted by savings (highest first)"""
        report = optimizer.analyze_instance(sample_instance, "standard")

        # Verify sorted order
        for i in range(len(report.recommendations) - 1):
            assert report.recommendations[i].savings_monthly >= report.recommendations[i + 1].savings_monthly


class TestSpotRecommendation:
    """Test spot instance recommendation logic"""

    def test_spot_suitable_standard_usage(self, optimizer, sample_instance):
        """Test spot suitability for standard usage"""
        assert optimizer._is_spot_suitable(sample_instance, "standard") is True

    def test_spot_not_suitable_continuous_usage(self, optimizer, sample_instance):
        """Test spot not suitable for continuous usage"""
        assert optimizer._is_spot_suitable(sample_instance, "continuous") is False

    def test_spot_not_suitable_low_savings(self, optimizer):
        """Test spot not suitable when savings < 30%"""
        instance = InstanceType(
            instance_type="test.instance",
            vcpu_info=VCpuInfo(default_vcpus=2, default_cores=1, default_threads_per_core=2),
            memory_info=MemoryInfo(size_in_mib=4096),
            network_info=NetworkInfo(
                network_performance="Moderate",
                maximum_network_interfaces=2,
                maximum_ipv4_addresses_per_interface=4,
                maximum_ipv6_addresses_per_interface=4
            ),
            processor_info=ProcessorInfo(supported_architectures=["x86_64"]),
            ebs_info=EbsInfo(ebs_optimized_support="default"),
            current_generation=True,
            pricing=PricingInfo(
                on_demand_price=0.10,
                spot_price=0.08  # Only 20% savings
            )
        )

        assert optimizer._is_spot_suitable(instance, "standard") is False

    def test_create_spot_recommendation(self, optimizer, sample_instance):
        """Test creating spot recommendation"""
        current_monthly = sample_instance.pricing.on_demand_price * 730

        rec = optimizer._create_spot_recommendation(sample_instance, current_monthly)

        assert rec is not None
        assert rec.recommendation_type == "spot"
        assert rec.current_instance == "t3.large"
        assert rec.recommended_instance is None  # Same instance, different pricing
        assert rec.current_cost_monthly == current_monthly
        assert rec.optimized_cost_monthly == sample_instance.pricing.spot_price * 730
        assert rec.savings_monthly > 0
        assert rec.savings_percentage >= 30
        assert "interrupted" in rec.considerations[0].lower()


class TestDownsizeRecommendation:
    """Test right-sizing/downsize recommendation logic"""

    def test_find_cheaper_alternatives(self, optimizer, sample_instance, cheaper_alternative):
        """Test finding cheaper alternatives"""
        candidates = optimizer._find_cheaper_alternatives(sample_instance)

        assert len(candidates) > 0
        assert cheaper_alternative in candidates

    def test_cheaper_alternative_requirements(self, optimizer, sample_instance):
        """Test that cheaper alternatives meet requirements"""
        candidates = optimizer._find_cheaper_alternatives(sample_instance)

        for candidate in candidates:
            # Must be cheaper
            assert candidate.pricing.on_demand_price < sample_instance.pricing.on_demand_price

            # Must have sufficient vCPU (within 2 of original)
            min_vcpu = max(1, sample_instance.vcpu_info.default_vcpus - 2)
            assert candidate.vcpu_info.default_vcpus >= min_vcpu

            # Must have sufficient memory (within 20% of original)
            required_memory = sample_instance.memory_info.size_in_gb * 0.8
            assert candidate.memory_info.size_in_gb >= required_memory

    def test_create_downsize_recommendation(self, optimizer, sample_instance, cheaper_alternative):
        """Test creating downsize recommendation"""
        current_monthly = sample_instance.pricing.on_demand_price * 730

        rec = optimizer._create_downsize_recommendation(
            sample_instance,
            cheaper_alternative,
            current_monthly
        )

        assert rec is not None
        assert rec.recommendation_type == "downsize"
        assert rec.current_instance == "t3.large"
        assert rec.recommended_instance == "t3.medium"
        assert rec.savings_monthly > 0
        assert rec.savings_percentage > 0
        assert len(rec.considerations) > 0


class TestSavingsPlanRecommendation:
    """Test Savings Plan recommendation logic"""

    def test_create_savings_plan_1yr(self, optimizer, sample_instance):
        """Test creating 1-year savings plan recommendation"""
        current_monthly = sample_instance.pricing.on_demand_price * 730

        rec = optimizer._create_savings_plan_recommendation(
            sample_instance,
            "1yr",
            current_monthly
        )

        assert rec is not None
        assert rec.recommendation_type == "savings_plan_1yr"
        assert rec.current_instance == "t3.large"
        assert rec.recommended_instance is None
        assert rec.savings_monthly > 0
        assert rec.savings_percentage >= 10
        assert "1-year" in rec.considerations[0].lower()

    def test_create_savings_plan_3yr(self, optimizer, sample_instance):
        """Test creating 3-year savings plan recommendation"""
        current_monthly = sample_instance.pricing.on_demand_price * 730

        rec = optimizer._create_savings_plan_recommendation(
            sample_instance,
            "3yr",
            current_monthly
        )

        assert rec is not None
        assert rec.recommendation_type == "savings_plan_3yr"
        assert "3-year" in rec.considerations[0].lower()

    def test_no_savings_plan_if_low_savings(self, optimizer):
        """Test no recommendation if savings < 10%"""
        instance = InstanceType(
            instance_type="test.instance",
            vcpu_info=VCpuInfo(default_vcpus=2, default_cores=1, default_threads_per_core=2),
            memory_info=MemoryInfo(size_in_mib=4096),
            network_info=NetworkInfo(
                network_performance="Moderate",
                maximum_network_interfaces=2,
                maximum_ipv4_addresses_per_interface=4,
                maximum_ipv6_addresses_per_interface=4
            ),
            processor_info=ProcessorInfo(supported_architectures=["x86_64"]),
            ebs_info=EbsInfo(ebs_optimized_support="default"),
            current_generation=True,
            pricing=PricingInfo(
                on_demand_price=0.10,
                savings_plan_1yr_no_upfront=0.095  # Only 5% savings
            )
        )

        current_monthly = instance.pricing.on_demand_price * 730
        rec = optimizer._create_savings_plan_recommendation(instance, "1yr", current_monthly)

        assert rec is None


class TestReservedInstanceRecommendation:
    """Test Reserved Instance recommendation logic"""

    def test_create_ri_recommendations(self, optimizer, sample_instance):
        """Test creating RI recommendations"""
        current_monthly = sample_instance.pricing.on_demand_price * 730

        recs = optimizer._create_ri_recommendations(sample_instance, current_monthly)

        # Should have multiple RI recommendations
        assert len(recs) > 0

        # Check types
        types = [r.recommendation_type for r in recs]
        assert "ri_1yr" in types or "ri_3yr" in types

        # All should have >= 10% savings
        for rec in recs:
            assert rec.savings_percentage >= 10

    def test_ri_no_upfront_recommendation(self, optimizer, sample_instance):
        """Test RI no upfront recommendation"""
        current_monthly = sample_instance.pricing.on_demand_price * 730

        recs = optimizer._create_ri_recommendations(sample_instance, current_monthly)

        # Find no upfront options by checking considerations
        no_upfront_recs = [r for r in recs if "No upfront" in str(r.considerations)]
        assert len(no_upfront_recs) > 0

        for rec in no_upfront_recs:
            assert rec.recommendation_type in ["ri_1yr", "ri_3yr"]
            assert "No upfront" in str(rec.considerations)

    def test_ri_partial_upfront_recommendation(self, optimizer, sample_instance):
        """Test RI partial upfront recommendation"""
        current_monthly = sample_instance.pricing.on_demand_price * 730

        recs = optimizer._create_ri_recommendations(sample_instance, current_monthly)

        # Find partial upfront options by checking considerations
        partial_recs = [r for r in recs if "Partial upfront" in str(r.considerations)]
        assert len(partial_recs) > 0

        for rec in partial_recs:
            assert rec.recommendation_type in ["ri_1yr", "ri_3yr"]
            assert "Partial upfront" in str(rec.considerations)


class TestOptimizationDataclasses:
    """Test OptimizationRecommendation and OptimizationReport dataclasses"""

    def test_optimization_recommendation_creation(self):
        """Test creating OptimizationRecommendation"""
        rec = OptimizationRecommendation(
            recommendation_type="spot",
            current_instance="t3.large",
            recommended_instance=None,
            current_cost_monthly=60.74,
            optimized_cost_monthly=18.25,
            savings_monthly=42.49,
            savings_percentage=70.0,
            reason="Spot price is significantly lower",
            considerations=["May be interrupted"]
        )

        assert rec.recommendation_type == "spot"
        assert rec.current_instance == "t3.large"
        assert rec.savings_monthly == 42.49
        assert rec.savings_percentage == 70.0

    def test_optimization_report_creation(self, sample_instance):
        """Test creating OptimizationReport"""
        rec1 = OptimizationRecommendation(
            recommendation_type="spot",
            current_instance="t3.large",
            recommended_instance=None,
            current_cost_monthly=60.74,
            optimized_cost_monthly=18.25,
            savings_monthly=42.49,
            savings_percentage=70.0,
            reason="Test",
            considerations=[]
        )

        report = OptimizationReport(
            instance_type="t3.large",
            region="us-east-1",
            current_pricing=sample_instance.pricing,
            recommendations=[rec1],
            total_potential_savings=42.49
        )

        assert report.instance_type == "t3.large"
        assert report.region == "us-east-1"
        assert len(report.recommendations) == 1
        assert report.total_potential_savings == 42.49
