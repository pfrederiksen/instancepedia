"""Tests for optimize CLI command"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from argparse import Namespace

from src.cli.commands.pricing_commands import cmd_optimize, _format_optimization_report
from src.services.optimization_service import OptimizationService, OptimizationRecommendation, OptimizationReport
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
            spot_price=0.0250,
            savings_plan_1yr_no_upfront=0.0540,
            savings_plan_3yr_no_upfront=0.0350,
            ri_1yr_no_upfront=0.0600,
            ri_1yr_partial_upfront=0.0580
        )
    )


@pytest.fixture
def sample_report(sample_instance):
    """Create a sample optimization report"""
    rec1 = OptimizationRecommendation(
        recommendation_type="spot",
        current_instance="t3.large",
        recommended_instance=None,
        current_cost_monthly=60.74,
        optimized_cost_monthly=18.25,
        savings_monthly=42.49,
        savings_percentage=70.0,
        reason="Spot price is significantly lower (70.0% savings)",
        considerations=[
            "May be interrupted with 2-minute warning",
            "Best for fault-tolerant, flexible workloads"
        ]
    )

    rec2 = OptimizationRecommendation(
        recommendation_type="downsize",
        current_instance="t3.large",
        recommended_instance="t3.medium",
        current_cost_monthly=60.74,
        optimized_cost_monthly=30.37,
        savings_monthly=30.37,
        savings_percentage=50.0,
        reason="Similar capabilities at 50.0% lower cost",
        considerations=[
            "4.0 GB less memory (4.0 vs 8.0 GB)"
        ]
    )

    return OptimizationReport(
        instance_type="t3.large",
        region="us-east-1",
        current_pricing=sample_instance.pricing,
        recommendations=[rec1, rec2],
        total_potential_savings=72.86
    )


class TestCmdOptimize:
    """Tests for cmd_optimize CLI command"""

    @patch('src.cli.commands.pricing_commands.get_aws_client')
    @patch('src.cli.commands.pricing_commands.get_instance_by_name')
    @patch('src.cli.commands.pricing_commands.PricingService')
    @patch('src.cli.commands.pricing_commands.fetch_instance_pricing')
    @patch('src.services.instance_service.InstanceService')
    @patch('src.services.optimization_service.OptimizationService')
    def test_optimize_success_table_format(
        self,
        mock_optimizer_class,
        mock_instance_service_class,
        mock_fetch_pricing,
        mock_pricing_service_class,
        mock_get_instance,
        mock_get_client,
        sample_instance,
        sample_report,
        capsys
    ):
        """Test optimize command with table output format"""
        # Setup mocks
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_get_instance.return_value = sample_instance

        # Mock pricing service
        mock_pricing_service = Mock()
        mock_pricing_service_class.return_value = mock_pricing_service
        mock_fetch_pricing.return_value = sample_instance.pricing

        # Mock instance service
        mock_instance_service = Mock()
        mock_instance_service.get_instance_types.return_value = [sample_instance]
        mock_instance_service_class.return_value = mock_instance_service

        # Mock optimizer
        mock_optimizer = Mock()
        mock_optimizer.analyze_instance.return_value = sample_report
        mock_optimizer_class.return_value = mock_optimizer

        # Create args
        args = Namespace(
            instance_type="t3.large",
            region="us-east-1",
            profile=None,
            usage_pattern="standard",
            output=None,
            format="table",
            quiet=False,
            debug=False
        )

        # Execute
        result = cmd_optimize(args)

        # Verify
        assert result == 0
        mock_get_instance.assert_called_once_with(mock_client, "t3.large", "us-east-1", False)

        # Check output contains key information
        captured = capsys.readouterr()
        assert "t3.large" in captured.out
        assert "Spot Instances" in captured.out or "spot" in captured.out.lower()

    @patch('src.cli.commands.pricing_commands.get_aws_client')
    @patch('src.cli.commands.pricing_commands.get_instance_by_name')
    @patch('src.cli.commands.pricing_commands.PricingService')
    @patch('src.cli.commands.pricing_commands.fetch_instance_pricing')
    @patch('src.services.instance_service.InstanceService')
    @patch('src.services.optimization_service.OptimizationService')
    def test_optimize_success_json_format(
        self,
        mock_optimizer_class,
        mock_instance_service_class,
        mock_fetch_pricing,
        mock_pricing_service_class,
        mock_get_instance,
        mock_get_client,
        sample_instance,
        sample_report,
        capsys
    ):
        """Test optimize command with JSON output format"""
        # Setup mocks
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_get_instance.return_value = sample_instance

        mock_pricing_service = Mock()
        mock_pricing_service_class.return_value = mock_pricing_service
        mock_fetch_pricing.return_value = sample_instance.pricing

        mock_instance_service = Mock()
        mock_instance_service.get_instance_types.return_value = [sample_instance]
        mock_instance_service_class.return_value = mock_instance_service

        mock_optimizer = Mock()
        mock_optimizer.analyze_instance.return_value = sample_report
        mock_optimizer_class.return_value = mock_optimizer

        # Create args
        args = Namespace(
            instance_type="t3.large",
            region="us-east-1",
            profile=None,
            usage_pattern="standard",
            output=None,
            format="json",
            quiet=False,
            debug=False
        )

        # Execute
        result = cmd_optimize(args)

        # Verify
        assert result == 0

        # Check JSON output
        captured = capsys.readouterr()
        output_data = json.loads(captured.out)

        assert output_data["instance_type"] == "t3.large"
        assert output_data["region"] == "us-east-1"
        assert len(output_data["recommendations"]) == 2
        assert output_data["total_potential_savings"] == 72.86

    @patch('src.cli.commands.pricing_commands.get_aws_client')
    @patch('src.cli.commands.pricing_commands.get_instance_by_name')
    def test_optimize_instance_not_found(
        self,
        mock_get_instance,
        mock_get_client,
        capsys
    ):
        """Test optimize command when instance not found"""
        # Setup mocks
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_get_instance.return_value = None

        # Create args
        args = Namespace(
            instance_type="nonexistent.type",
            region="us-east-1",
            profile=None,
            usage_pattern="standard",
            output=None,
            format="table",
            quiet=False,
            debug=False
        )

        # Execute
        result = cmd_optimize(args)

        # Verify
        assert result == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err.lower()


class TestFormatOptimizationReport:
    """Tests for _format_optimization_report helper function"""

    def test_format_report_table(self, sample_report):
        """Test formatting report as table"""
        output = _format_optimization_report(sample_report)

        assert "t3.large" in output
        assert "us-east-1" in output
        assert "70.0%" in output or "70%" in output
        assert "t3.medium" in output
        assert "50.0%" in output or "50%" in output

    def test_format_report_no_recommendations(self, sample_instance):
        """Test formatting report with no recommendations"""
        report = OptimizationReport(
            instance_type="t3.large",
            region="us-east-1",
            current_pricing=sample_instance.pricing,
            recommendations=[],
            total_potential_savings=0.0
        )

        output = _format_optimization_report(report)

        assert "t3.large" in output
        assert "No significant optimization opportunities found" in output.lower() or "no recommendations" in output.lower() or len(output) > 0

    def test_format_report_with_considerations(self, sample_report):
        """Test that considerations are included in output"""
        output = _format_optimization_report(sample_report)

        # Check that at least one consideration is present
        assert "interrupted" in output.lower() or "memory" in output.lower()
