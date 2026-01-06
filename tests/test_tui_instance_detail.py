"""Tests for the InstanceDetail screen"""

import asyncio
import pytest
from unittest.mock import Mock, patch

from textual.app import App
from textual.widgets import Static
from textual.containers import ScrollableContainer

from src.ui.instance_detail import InstanceDetail
from src.models.instance_type import (
    InstanceType,
    VCpuInfo,
    MemoryInfo,
    NetworkInfo,
    ProcessorInfo,
    EbsInfo,
    PricingInfo,
)


class InstanceDetailTestApp(App):
    """Test app that hosts the InstanceDetail screen"""

    def __init__(self, instance_type):
        super().__init__()
        self.instance = instance_type
        self.current_region = "us-east-1"
        self.settings = Mock()
        self.settings.aws_profile = None
        self.settings.aws_region = "us-east-1"

    def on_mount(self):
        self.push_screen(InstanceDetail(self.instance))


class TestInstanceDetail:
    """Tests for InstanceDetail screen"""

    async def _wait_for_render(self, pilot):
        """Wait for the detail content to render (it uses set_timer with 0.2s delay)"""
        # Wait for the timer to fire and content to render
        await asyncio.sleep(0.3)
        await pilot.pause()

    async def test_instance_detail_displays(self, sample_instance_type):
        """Test that instance detail screen displays"""
        app = InstanceDetailTestApp(sample_instance_type)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Check header is present
            header = app.screen.query_one("#header", Static)
            assert header is not None
            assert "Instance Type Details" in str(header.render())

    async def test_instance_detail_shows_instance_type(self, sample_instance_type):
        """Test instance type name is displayed"""
        app = InstanceDetailTestApp(sample_instance_type)

        async with app.run_test() as pilot:
            await self._wait_for_render(pilot)

            detail_text = app.screen.query_one("#detail-text", Static)
            content = str(detail_text.render())

            assert sample_instance_type.instance_type in content

    async def test_instance_detail_shows_vcpu(self, sample_instance_type):
        """Test vCPU info is displayed"""
        app = InstanceDetailTestApp(sample_instance_type)

        async with app.run_test() as pilot:
            await self._wait_for_render(pilot)

            detail_text = app.screen.query_one("#detail-text", Static)
            content = str(detail_text.render())

            assert "vCPU" in content

    async def test_instance_detail_shows_memory(self, sample_instance_type):
        """Test memory info is displayed"""
        app = InstanceDetailTestApp(sample_instance_type)

        async with app.run_test() as pilot:
            await self._wait_for_render(pilot)

            detail_text = app.screen.query_one("#detail-text", Static)
            content = str(detail_text.render())

            assert "Memory" in content

    async def test_instance_detail_shows_network(self, sample_instance_type):
        """Test network info is displayed"""
        app = InstanceDetailTestApp(sample_instance_type)

        async with app.run_test() as pilot:
            await self._wait_for_render(pilot)

            detail_text = app.screen.query_one("#detail-text", Static)
            content = str(detail_text.render())

            assert "Network" in content

    async def test_instance_detail_shows_pricing(self, sample_instance_type):
        """Test pricing info is displayed"""
        app = InstanceDetailTestApp(sample_instance_type)

        async with app.run_test() as pilot:
            await self._wait_for_render(pilot)

            detail_text = app.screen.query_one("#detail-text", Static)
            content = str(detail_text.render())

            assert "Pricing" in content

    async def test_instance_detail_bindings(self, sample_instance_type):
        """Test instance detail key bindings"""
        screen = InstanceDetail(sample_instance_type)

        # Check bindings - BINDINGS is a list of tuples (key, action, description)
        binding_keys = [b[0] for b in screen.BINDINGS]
        assert "q" in binding_keys
        assert "escape" in binding_keys

    async def test_instance_detail_back_action(self, sample_instance_type):
        """Test back action dismisses screen"""
        app = InstanceDetailTestApp(sample_instance_type)

        async with app.run_test() as pilot:
            await pilot.pause()

            await pilot.press("escape")
            await pilot.pause()

    async def test_instance_detail_quit_action(self, sample_instance_type):
        """Test quit action"""
        app = InstanceDetailTestApp(sample_instance_type)

        async with app.run_test() as pilot:
            await pilot.pause()

            await pilot.press("q")
            await pilot.pause()

    async def test_instance_detail_scrollable(self, sample_instance_type):
        """Test detail content is scrollable"""
        app = InstanceDetailTestApp(sample_instance_type)

        async with app.run_test() as pilot:
            await pilot.pause()

            scrollable = app.screen.query_one("#detail-content", ScrollableContainer)
            assert scrollable is not None

    async def test_instance_detail_help_text(self, sample_instance_type):
        """Test help text is displayed"""
        app = InstanceDetailTestApp(sample_instance_type)

        async with app.run_test() as pilot:
            await pilot.pause()

            help_text = app.screen.query_one("#help-text", Static)
            content = str(help_text.render())

            assert "Esc" in content
            assert "Back" in content


class TestInstanceDetailFreeTier:
    """Tests for free tier display in InstanceDetail"""

    async def _wait_for_render(self, pilot):
        """Wait for the detail content to render"""
        await asyncio.sleep(0.3)
        await pilot.pause()

    @pytest.fixture
    def free_tier_instance(self):
        """Create a free tier eligible instance"""
        return InstanceType(
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
        )

    async def test_free_tier_section_displayed(self, free_tier_instance):
        """Test free tier section is displayed for eligible instances"""
        app = InstanceDetailTestApp(free_tier_instance)

        async with app.run_test() as pilot:
            await self._wait_for_render(pilot)

            detail_text = app.screen.query_one("#detail-text", Static)
            content = str(detail_text.render())

            assert "FREE TIER" in content


class TestInstanceDetailPricing:
    """Tests for pricing display in InstanceDetail"""

    async def _wait_for_render(self, pilot):
        """Wait for the detail content to render"""
        await asyncio.sleep(0.3)
        await pilot.pause()

    @pytest.fixture
    def instance_with_pricing(self):
        """Create instance with full pricing"""
        return InstanceType(
            instance_type="m5.large",
            vcpu_info=VCpuInfo(default_vcpus=2),
            memory_info=MemoryInfo(size_in_mib=8192),
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
            hibernation_supported=True,
            pricing=PricingInfo(on_demand_price=0.096, spot_price=0.038)
        )

    @pytest.fixture
    def instance_no_pricing(self):
        """Create instance without pricing"""
        return InstanceType(
            instance_type="m5.large",
            vcpu_info=VCpuInfo(default_vcpus=2),
            memory_info=MemoryInfo(size_in_mib=8192),
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
            hibernation_supported=True,
            pricing=None
        )

    async def test_on_demand_price_displayed(self, instance_with_pricing):
        """Test on-demand price is displayed"""
        app = InstanceDetailTestApp(instance_with_pricing)

        async with app.run_test() as pilot:
            await self._wait_for_render(pilot)

            detail_text = app.screen.query_one("#detail-text", Static)
            content = str(detail_text.render())

            assert "On-Demand Price" in content

    async def test_spot_price_displayed(self, instance_with_pricing):
        """Test spot price is displayed"""
        app = InstanceDetailTestApp(instance_with_pricing)

        async with app.run_test() as pilot:
            await self._wait_for_render(pilot)

            detail_text = app.screen.query_one("#detail-text", Static)
            content = str(detail_text.render())

            assert "Spot" in content

    async def test_monthly_cost_displayed(self, instance_with_pricing):
        """Test monthly cost is displayed"""
        app = InstanceDetailTestApp(instance_with_pricing)

        async with app.run_test() as pilot:
            await self._wait_for_render(pilot)

            detail_text = app.screen.query_one("#detail-text", Static)
            content = str(detail_text.render())

            assert "Monthly" in content

    async def test_no_pricing_message(self, instance_no_pricing):
        """Test message shown when pricing unavailable"""
        app = InstanceDetailTestApp(instance_no_pricing)

        async with app.run_test() as pilot:
            await self._wait_for_render(pilot)

            detail_text = app.screen.query_one("#detail-text", Static)
            content = str(detail_text.render())

            # Should indicate pricing not loaded
            assert "Pricing" in content


class TestInstanceDetailSpotPriceFetch:
    """Tests for spot price fetching in InstanceDetail"""

    @pytest.fixture
    def instance_no_spot(self):
        """Create instance with on-demand but no spot price"""
        return InstanceType(
            instance_type="m5.large",
            vcpu_info=VCpuInfo(default_vcpus=2),
            memory_info=MemoryInfo(size_in_mib=8192),
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
            hibernation_supported=True,
            pricing=PricingInfo(on_demand_price=0.096, spot_price=None)
        )

    @patch('src.ui.instance_detail.AsyncAWSClient')
    @patch('src.ui.instance_detail.AsyncPricingService')
    async def test_spot_price_fetch_triggered(
        self, mock_pricing_service, mock_aws_client, instance_no_spot
    ):
        """Test spot price fetch is triggered when not available"""
        mock_client_instance = Mock()
        mock_aws_client.return_value = mock_client_instance

        mock_service_instance = Mock()
        # Make get_spot_price return an awaitable
        async def mock_get_spot_price(*args, **kwargs):
            return 0.038
        mock_service_instance.get_spot_price = mock_get_spot_price
        mock_pricing_service.return_value = mock_service_instance

        app = InstanceDetailTestApp(instance_no_spot)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Spot price fetch should have been triggered
            # (runs as async worker)
