"""Tests for TUI instance comparison screen"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from textual.app import App, ComposeResult
from textual.widgets import Static, Button
from textual.pilot import Pilot

from src.ui.instance_comparison import InstanceComparison
from src.models.instance_type import (
    InstanceType,
    VCpuInfo,
    MemoryInfo,
    NetworkInfo,
    ProcessorInfo,
    EbsInfo,
    PricingInfo,
    GpuInfo,
    GpuDevice,
    InstanceStorageInfo,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def basic_instance_1():
    """Create a basic instance for comparison (t3.micro)"""
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
        hibernation_supported=True,
        pricing=PricingInfo(
            on_demand_price=0.0104,
            spot_price=0.0031
        )
    )


@pytest.fixture
def basic_instance_2():
    """Create a second basic instance for comparison (m5.large)"""
    return InstanceType(
        instance_type="m5.large",
        vcpu_info=VCpuInfo(
            default_vcpus=2,
            default_cores=1,
            default_threads_per_core=2
        ),
        memory_info=MemoryInfo(size_in_mib=8192),  # 8 GB
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
        ebs_info=EbsInfo(
            ebs_optimized_support="default",
            ebs_optimized_info=None
        ),
        current_generation=True,
        burstable_performance_supported=False,
        hibernation_supported=True,
        pricing=PricingInfo(
            on_demand_price=0.096,
            spot_price=0.038
        )
    )


@pytest.fixture
def instance_with_gpu():
    """Create an instance with GPU"""
    return InstanceType(
        instance_type="p3.2xlarge",
        vcpu_info=VCpuInfo(default_vcpus=8),
        memory_info=MemoryInfo(size_in_mib=61440),
        network_info=NetworkInfo(
            network_performance="Up to 10 Gigabit",
            maximum_network_interfaces=4,
            maximum_ipv4_addresses_per_interface=15,
            maximum_ipv6_addresses_per_interface=15
        ),
        processor_info=ProcessorInfo(supported_architectures=["x86_64"]),
        ebs_info=EbsInfo(ebs_optimized_support="default"),
        current_generation=True,
        burstable_performance_supported=False,
        hibernation_supported=False,
        gpu_info=GpuInfo(
            gpus=[GpuDevice(name="Tesla V100", manufacturer="NVIDIA", count=1, memory_in_mib=16384)],
            total_gpu_memory_in_mib=16384
        ),
        pricing=PricingInfo(on_demand_price=3.06, spot_price=0.918)
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
def instance_no_pricing():
    """Create an instance without pricing data"""
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
def instance_arm():
    """Create an ARM-based Graviton instance"""
    return InstanceType(
        instance_type="m6g.large",
        vcpu_info=VCpuInfo(default_vcpus=2),
        memory_info=MemoryInfo(size_in_mib=8192),
        network_info=NetworkInfo(
            network_performance="Up to 10 Gigabit",
            maximum_network_interfaces=3,
            maximum_ipv4_addresses_per_interface=10,
            maximum_ipv6_addresses_per_interface=10
        ),
        processor_info=ProcessorInfo(supported_architectures=["arm64"]),
        ebs_info=EbsInfo(ebs_optimized_support="default"),
        current_generation=True,
        burstable_performance_supported=False,
        hibernation_supported=False,
        pricing=PricingInfo(on_demand_price=0.077, spot_price=0.023)
    )


@pytest.fixture
def free_tier_instance():
    """Create a free tier eligible instance (t2.micro)"""
    return InstanceType(
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


# =============================================================================
# Test App for InstanceComparison Tests
# =============================================================================

class ComparisonTestApp(App):
    """Test app for InstanceComparison screen"""

    CSS = """
    Screen {
        align: center middle;
    }
    #comparison-container {
        width: 100%;
        height: 100%;
    }
    """

    def __init__(self, instance1: InstanceType, instance2: InstanceType, region: str = "us-east-1"):
        super().__init__()
        self.instance1 = instance1
        self.instance2 = instance2
        self._region = region
        self.dismiss_result = None
        self.exited = False

    def compose(self) -> ComposeResult:
        yield Button("Open Comparison", id="open-comparison")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "open-comparison":
            self.push_screen(
                InstanceComparison(self.instance1, self.instance2, self._region),
                callback=self._on_dismiss
            )

    def _on_dismiss(self, result):
        self.dismiss_result = result

    def get_comparison_screen(self):
        """Get the current comparison screen if one is active"""
        if len(self.screen_stack) > 1:
            screen = self.screen_stack[-1]
            if isinstance(screen, InstanceComparison):
                return screen
        return None

    def exit(self, result=None):
        """Track when exit is called"""
        self.exited = True
        super().exit(result)


# =============================================================================
# Test Cases
# =============================================================================

class TestInstanceComparisonInit:
    """Tests for InstanceComparison initialization"""

    def test_init_stores_instances(self, basic_instance_1, basic_instance_2):
        """Test that InstanceComparison stores instance references correctly"""
        comparison = InstanceComparison(basic_instance_1, basic_instance_2, "us-east-1")

        assert comparison.instance1 == basic_instance_1
        assert comparison.instance2 == basic_instance_2
        assert comparison._region == "us-east-1"

    def test_init_creates_free_tier_service(self, basic_instance_1, basic_instance_2):
        """Test that InstanceComparison creates FreeTierService"""
        comparison = InstanceComparison(basic_instance_1, basic_instance_2, "us-east-1")

        assert comparison.free_tier_service is not None

    def test_bindings_defined(self, basic_instance_1, basic_instance_2):
        """Test that InstanceComparison has expected keybindings"""
        comparison = InstanceComparison(basic_instance_1, basic_instance_2, "us-east-1")

        bindings = dict((b[0], b[1]) for b in comparison.BINDINGS)
        assert "q" in bindings
        assert "escape" in bindings
        assert bindings["q"] == "quit"
        assert bindings["escape"] == "back"


class TestInstanceComparisonUI:
    """Tests for InstanceComparison UI rendering"""

    @pytest.mark.asyncio
    async def test_comparison_screen_opens(self, basic_instance_1, basic_instance_2):
        """Test that comparison screen opens correctly"""
        app = ComparisonTestApp(basic_instance_1, basic_instance_2)
        async with app.run_test(size=(100, 50)) as pilot:
            await pilot.click("#open-comparison")
            await pilot.pause()

            screen = app.get_comparison_screen()
            assert screen is not None
            assert isinstance(screen, InstanceComparison)

    @pytest.mark.asyncio
    async def test_header_shows_instance_names(self, basic_instance_1, basic_instance_2):
        """Test that header shows both instance type names"""
        app = ComparisonTestApp(basic_instance_1, basic_instance_2)
        async with app.run_test(size=(100, 50)) as pilot:
            await pilot.click("#open-comparison")
            await pilot.pause()
            # Wait for timer-based rendering
            await asyncio.sleep(0.3)

            screen = app.get_comparison_screen()
            header = screen.query_one("#header", Static)
            header_text = str(header.render())
            assert "t3.micro" in header_text
            assert "m5.large" in header_text

    @pytest.mark.asyncio
    async def test_comparison_shows_vcpu(self, basic_instance_1, basic_instance_2):
        """Test that comparison shows vCPU counts"""
        app = ComparisonTestApp(basic_instance_1, basic_instance_2)
        async with app.run_test(size=(100, 50)) as pilot:
            await pilot.click("#open-comparison")
            await pilot.pause()
            await asyncio.sleep(0.3)

            screen = app.get_comparison_screen()
            content = screen.query_one("#comparison-text", Static)
            text = str(content.render())
            assert "vCPU" in text

    @pytest.mark.asyncio
    async def test_comparison_shows_memory(self, basic_instance_1, basic_instance_2):
        """Test that comparison shows memory values"""
        app = ComparisonTestApp(basic_instance_1, basic_instance_2)
        async with app.run_test(size=(100, 50)) as pilot:
            await pilot.click("#open-comparison")
            await pilot.pause()
            await asyncio.sleep(0.3)

            screen = app.get_comparison_screen()
            content = screen.query_one("#comparison-text", Static)
            text = str(content.render())
            assert "Memory" in text
            assert "1.00 GB" in text  # t3.micro
            assert "8.00 GB" in text  # m5.large

    @pytest.mark.asyncio
    async def test_comparison_shows_network(self, basic_instance_1, basic_instance_2):
        """Test that comparison shows network performance"""
        app = ComparisonTestApp(basic_instance_1, basic_instance_2)
        async with app.run_test(size=(100, 50)) as pilot:
            await pilot.click("#open-comparison")
            await pilot.pause()
            await asyncio.sleep(0.3)

            screen = app.get_comparison_screen()
            content = screen.query_one("#comparison-text", Static)
            text = str(content.render())
            assert "Network Performance" in text
            assert "Up to 5 Gigabit" in text
            assert "Up to 10 Gigabit" in text

    @pytest.mark.asyncio
    async def test_comparison_shows_pricing(self, basic_instance_1, basic_instance_2):
        """Test that comparison shows pricing information"""
        app = ComparisonTestApp(basic_instance_1, basic_instance_2)
        async with app.run_test(size=(100, 50)) as pilot:
            await pilot.click("#open-comparison")
            await pilot.pause()
            await asyncio.sleep(0.3)

            screen = app.get_comparison_screen()
            content = screen.query_one("#comparison-text", Static)
            text = str(content.render())
            assert "On-Demand" in text
            assert "$0.0104/hr" in text  # t3.micro
            assert "$0.096" in text  # m5.large

    @pytest.mark.asyncio
    async def test_comparison_shows_spot_pricing(self, basic_instance_1, basic_instance_2):
        """Test that comparison shows spot pricing"""
        app = ComparisonTestApp(basic_instance_1, basic_instance_2)
        async with app.run_test(size=(100, 50)) as pilot:
            await pilot.click("#open-comparison")
            await pilot.pause()
            await asyncio.sleep(0.3)

            screen = app.get_comparison_screen()
            content = screen.query_one("#comparison-text", Static)
            text = str(content.render())
            assert "Spot Price" in text
            assert "$0.0031/hr" in text  # t3.micro spot
            assert "$0.038" in text  # m5.large spot

    @pytest.mark.asyncio
    async def test_comparison_shows_region(self, basic_instance_1, basic_instance_2):
        """Test that comparison shows region"""
        app = ComparisonTestApp(basic_instance_1, basic_instance_2, region="eu-west-1")
        async with app.run_test(size=(100, 50)) as pilot:
            await pilot.click("#open-comparison")
            await pilot.pause()
            await asyncio.sleep(0.3)

            screen = app.get_comparison_screen()
            content = screen.query_one("#comparison-text", Static)
            text = str(content.render())
            assert "eu-west-1" in text

    @pytest.mark.asyncio
    async def test_comparison_shows_ebs_optimized(self, basic_instance_1, basic_instance_2):
        """Test that comparison shows EBS optimized status"""
        app = ComparisonTestApp(basic_instance_1, basic_instance_2)
        async with app.run_test(size=(100, 50)) as pilot:
            await pilot.click("#open-comparison")
            await pilot.pause()
            await asyncio.sleep(0.3)

            screen = app.get_comparison_screen()
            content = screen.query_one("#comparison-text", Static)
            text = str(content.render())
            assert "EBS Optimized" in text
            assert "Supported" in text  # t3.micro
            assert "Default" in text  # m5.large

    @pytest.mark.asyncio
    async def test_comparison_shows_architectures(self, basic_instance_1, instance_arm):
        """Test that comparison shows CPU architectures"""
        app = ComparisonTestApp(basic_instance_1, instance_arm)
        async with app.run_test(size=(100, 50)) as pilot:
            await pilot.click("#open-comparison")
            await pilot.pause()
            await asyncio.sleep(0.3)

            screen = app.get_comparison_screen()
            content = screen.query_one("#comparison-text", Static)
            text = str(content.render())
            assert "Architectures" in text
            assert "x86_64" in text
            assert "arm64" in text


class TestInstanceComparisonSpecialCases:
    """Tests for InstanceComparison special case handling"""

    @pytest.mark.asyncio
    async def test_comparison_no_pricing_shows_na(self, instance_no_pricing, basic_instance_2):
        """Test that N/A is shown when pricing is not available"""
        app = ComparisonTestApp(instance_no_pricing, basic_instance_2)
        async with app.run_test(size=(100, 50)) as pilot:
            await pilot.click("#open-comparison")
            await pilot.pause()
            await asyncio.sleep(0.3)

            screen = app.get_comparison_screen()
            content = screen.query_one("#comparison-text", Static)
            text = str(content.render())
            assert "N/A" in text

    @pytest.mark.asyncio
    async def test_comparison_with_gpu(self, basic_instance_1, instance_with_gpu):
        """Test that GPU count is shown correctly"""
        app = ComparisonTestApp(basic_instance_1, instance_with_gpu)
        async with app.run_test(size=(100, 50)) as pilot:
            await pilot.click("#open-comparison")
            await pilot.pause()
            await asyncio.sleep(0.3)

            screen = app.get_comparison_screen()
            content = screen.query_one("#comparison-text", Static)
            text = str(content.render())
            assert "GPUs" in text
            # instance_with_gpu has 1 GPU, basic_instance_1 has 0

    @pytest.mark.asyncio
    async def test_comparison_with_instance_storage(self, basic_instance_1, instance_with_storage):
        """Test that instance storage is shown correctly"""
        app = ComparisonTestApp(basic_instance_1, instance_with_storage)
        async with app.run_test(size=(100, 50)) as pilot:
            await pilot.click("#open-comparison")
            await pilot.pause()
            await asyncio.sleep(0.3)

            screen = app.get_comparison_screen()
            content = screen.query_one("#comparison-text", Static)
            text = str(content.render())
            assert "Instance Storage" in text
            assert "EBS Only" in text  # t3.micro
            assert "475 GB" in text  # i3.large

    @pytest.mark.asyncio
    async def test_comparison_burstable_vs_non_burstable(self, basic_instance_1, basic_instance_2):
        """Test that burstable performance is shown correctly"""
        app = ComparisonTestApp(basic_instance_1, basic_instance_2)
        async with app.run_test(size=(100, 50)) as pilot:
            await pilot.click("#open-comparison")
            await pilot.pause()
            await asyncio.sleep(0.3)

            screen = app.get_comparison_screen()
            content = screen.query_one("#comparison-text", Static)
            text = str(content.render())
            assert "Burstable Performance" in text
            # t3.micro is burstable (Yes), m5.large is not (No)

    @pytest.mark.asyncio
    async def test_comparison_cost_efficiency_metrics(self, basic_instance_1, basic_instance_2):
        """Test that cost efficiency metrics are calculated correctly"""
        app = ComparisonTestApp(basic_instance_1, basic_instance_2)
        async with app.run_test(size=(100, 50)) as pilot:
            await pilot.click("#open-comparison")
            await pilot.pause()
            await asyncio.sleep(0.3)

            screen = app.get_comparison_screen()
            content = screen.query_one("#comparison-text", Static)
            text = str(content.render())
            assert "Cost per vCPU" in text
            assert "Cost per GB RAM" in text

    @pytest.mark.asyncio
    async def test_comparison_free_tier_eligible(self, free_tier_instance, basic_instance_2):
        """Test that free tier eligibility is shown correctly"""
        app = ComparisonTestApp(free_tier_instance, basic_instance_2)
        async with app.run_test(size=(100, 50)) as pilot:
            await pilot.click("#open-comparison")
            await pilot.pause()
            await asyncio.sleep(0.3)

            screen = app.get_comparison_screen()
            content = screen.query_one("#comparison-text", Static)
            text = str(content.render())
            assert "Free Tier Eligible" in text
            # t2.micro is free tier eligible

    @pytest.mark.asyncio
    async def test_comparison_monthly_cost_calculation(self, basic_instance_1, basic_instance_2):
        """Test that monthly cost is calculated and displayed"""
        app = ComparisonTestApp(basic_instance_1, basic_instance_2)
        async with app.run_test(size=(100, 50)) as pilot:
            await pilot.click("#open-comparison")
            await pilot.pause()
            await asyncio.sleep(0.3)

            screen = app.get_comparison_screen()
            content = screen.query_one("#comparison-text", Static)
            text = str(content.render())
            assert "Monthly Cost" in text
            assert "/mo" in text


class TestInstanceComparisonKeyBindings:
    """Tests for InstanceComparison keyboard navigation"""

    @pytest.mark.asyncio
    async def test_escape_dismisses_screen(self, basic_instance_1, basic_instance_2):
        """Test that escape key dismisses the comparison screen"""
        app = ComparisonTestApp(basic_instance_1, basic_instance_2)
        async with app.run_test(size=(100, 50)) as pilot:
            await pilot.click("#open-comparison")
            await pilot.pause()

            # Verify comparison screen is open
            assert app.get_comparison_screen() is not None

            # Press escape
            await pilot.press("escape")
            await pilot.pause()

            # Screen should be dismissed
            assert app.get_comparison_screen() is None
            assert app.dismiss_result is None

    @pytest.mark.asyncio
    async def test_q_quits_application(self, basic_instance_1, basic_instance_2):
        """Test that q key exits the application"""
        app = ComparisonTestApp(basic_instance_1, basic_instance_2)
        async with app.run_test(size=(100, 50)) as pilot:
            await pilot.click("#open-comparison")
            await pilot.pause()

            # Press q to quit
            await pilot.press("q")
            await pilot.pause()

            # App should have exited
            assert app.exited is True


class TestInstanceComparisonEdgeCases:
    """Tests for InstanceComparison edge cases"""

    @pytest.mark.asyncio
    async def test_comparison_both_no_pricing(self, instance_no_pricing):
        """Test comparison when both instances have no pricing"""
        instance2 = InstanceType(
            instance_type="t3.small",
            vcpu_info=VCpuInfo(default_vcpus=2),
            memory_info=MemoryInfo(size_in_mib=2048),
            network_info=NetworkInfo(
                network_performance="Up to 5 Gigabit",
                maximum_network_interfaces=3,
                maximum_ipv4_addresses_per_interface=4,
                maximum_ipv6_addresses_per_interface=4
            ),
            processor_info=ProcessorInfo(supported_architectures=["x86_64"]),
            ebs_info=EbsInfo(ebs_optimized_support="supported"),
            current_generation=True,
            burstable_performance_supported=True,
            hibernation_supported=False,
            pricing=None
        )
        app = ComparisonTestApp(instance_no_pricing, instance2)
        async with app.run_test(size=(100, 50)) as pilot:
            await pilot.click("#open-comparison")
            await pilot.pause()
            await asyncio.sleep(0.3)

            screen = app.get_comparison_screen()
            content = screen.query_one("#comparison-text", Static)
            text = str(content.render())
            # Should show N/A for pricing fields
            assert text.count("N/A") >= 4  # Multiple pricing fields

    @pytest.mark.asyncio
    async def test_comparison_spot_price_none(self, basic_instance_1):
        """Test comparison when spot price is None"""
        instance_no_spot = InstanceType(
            instance_type="m5.xlarge",
            vcpu_info=VCpuInfo(default_vcpus=4),
            memory_info=MemoryInfo(size_in_mib=16384),
            network_info=NetworkInfo(
                network_performance="Up to 10 Gigabit",
                maximum_network_interfaces=4,
                maximum_ipv4_addresses_per_interface=15,
                maximum_ipv6_addresses_per_interface=15
            ),
            processor_info=ProcessorInfo(supported_architectures=["x86_64"]),
            ebs_info=EbsInfo(ebs_optimized_support="default"),
            current_generation=True,
            burstable_performance_supported=False,
            hibernation_supported=True,
            pricing=PricingInfo(on_demand_price=0.192, spot_price=None)
        )
        app = ComparisonTestApp(basic_instance_1, instance_no_spot)
        async with app.run_test(size=(100, 50)) as pilot:
            await pilot.click("#open-comparison")
            await pilot.pause()
            await asyncio.sleep(0.3)

            screen = app.get_comparison_screen()
            content = screen.query_one("#comparison-text", Static)
            text = str(content.render())
            # Spot price should show N/A for instance without spot
            assert "$0.0031/hr" in text  # t3.micro spot price
            assert "N/A" in text  # m5.xlarge spot N/A

    @pytest.mark.asyncio
    async def test_comparison_same_instance_type(self, basic_instance_1):
        """Test comparison of same instance type (edge case)"""
        instance_copy = InstanceType(
            instance_type=basic_instance_1.instance_type,
            vcpu_info=basic_instance_1.vcpu_info,
            memory_info=basic_instance_1.memory_info,
            network_info=basic_instance_1.network_info,
            processor_info=basic_instance_1.processor_info,
            ebs_info=basic_instance_1.ebs_info,
            current_generation=basic_instance_1.current_generation,
            burstable_performance_supported=basic_instance_1.burstable_performance_supported,
            hibernation_supported=basic_instance_1.hibernation_supported,
            pricing=basic_instance_1.pricing
        )
        app = ComparisonTestApp(basic_instance_1, instance_copy)
        async with app.run_test(size=(100, 50)) as pilot:
            await pilot.click("#open-comparison")
            await pilot.pause()
            await asyncio.sleep(0.3)

            screen = app.get_comparison_screen()
            header = screen.query_one("#header", Static)
            # Should show same instance type in both columns
            assert "t3.micro vs t3.micro" in str(header.render())

    @pytest.mark.asyncio
    async def test_comparison_current_vs_previous_generation(self, basic_instance_1):
        """Test comparison of current gen vs previous gen instance"""
        prev_gen_instance = InstanceType(
            instance_type="m4.large",
            vcpu_info=VCpuInfo(default_vcpus=2),
            memory_info=MemoryInfo(size_in_mib=8192),
            network_info=NetworkInfo(
                network_performance="Moderate",
                maximum_network_interfaces=2,
                maximum_ipv4_addresses_per_interface=10,
                maximum_ipv6_addresses_per_interface=10
            ),
            processor_info=ProcessorInfo(supported_architectures=["x86_64"]),
            ebs_info=EbsInfo(ebs_optimized_support="supported"),
            current_generation=False,  # Previous generation
            burstable_performance_supported=False,
            hibernation_supported=False,
            pricing=PricingInfo(on_demand_price=0.1, spot_price=0.04)
        )
        app = ComparisonTestApp(basic_instance_1, prev_gen_instance)
        async with app.run_test(size=(100, 50)) as pilot:
            await pilot.click("#open-comparison")
            await pilot.pause()
            await asyncio.sleep(0.3)

            screen = app.get_comparison_screen()
            content = screen.query_one("#comparison-text", Static)
            text = str(content.render())
            assert "Current Generation" in text
            # Should show Yes/No for current generation field

    @pytest.mark.asyncio
    async def test_help_text_displayed(self, basic_instance_1, basic_instance_2):
        """Test that help text with keybindings is displayed"""
        app = ComparisonTestApp(basic_instance_1, basic_instance_2)
        async with app.run_test(size=(100, 50)) as pilot:
            await pilot.click("#open-comparison")
            await pilot.pause()

            screen = app.get_comparison_screen()
            help_text = screen.query_one("#help-text", Static)
            text = str(help_text.render())
            assert "Esc" in text
            assert "Back" in text
            assert "Q" in text or "q" in text
            assert "Quit" in text
