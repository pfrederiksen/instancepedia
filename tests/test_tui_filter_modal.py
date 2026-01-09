"""Tests for TUI filter modal"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from textual.app import App, ComposeResult
from textual.widgets import Input, Select, Button
from textual.pilot import Pilot

from src.ui.filter_modal import FilterModal, FilterCriteria


class TestFilterCriteria:
    """Tests for FilterCriteria class"""

    def test_init_defaults(self):
        """Test FilterCriteria initializes with default values"""
        criteria = FilterCriteria()

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

    def test_to_dict(self):
        """Test FilterCriteria.to_dict() returns correct dictionary"""
        criteria = FilterCriteria()
        criteria.min_vcpu = 4
        criteria.max_vcpu = 16
        criteria.gpu_filter = "yes"
        criteria.storage_type = "ebs_only"

        result = criteria.to_dict()

        assert result["min_vcpu"] == 4
        assert result["max_vcpu"] == 16
        assert result["gpu_filter"] == "yes"
        assert result["storage_type"] == "ebs_only"
        assert result["architecture"] == "any"  # default

    def test_from_dict(self):
        """Test FilterCriteria.from_dict() loads values correctly"""
        criteria = FilterCriteria()
        data = {
            "min_vcpu": 2,
            "max_vcpu": 8,
            "min_memory_gb": 4.0,
            "max_memory_gb": 32.0,
            "gpu_filter": "no",
            "current_generation": "yes",
            "processor_family": "graviton",
            "storage_type": "has_instance_store",
            "nvme_support": "required",
            "min_price": 0.01,
            "max_price": 1.0,
        }

        criteria.from_dict(data)

        assert criteria.min_vcpu == 2
        assert criteria.max_vcpu == 8
        assert criteria.min_memory_gb == 4.0
        assert criteria.max_memory_gb == 32.0
        assert criteria.gpu_filter == "no"
        assert criteria.current_generation == "yes"
        assert criteria.processor_family == "graviton"
        assert criteria.storage_type == "has_instance_store"
        assert criteria.nvme_support == "required"
        assert criteria.min_price == 0.01
        assert criteria.max_price == 1.0

    def test_from_dict_with_missing_keys(self):
        """Test FilterCriteria.from_dict() handles missing keys gracefully"""
        criteria = FilterCriteria()
        criteria.min_vcpu = 4  # Set a non-default value first
        data = {}  # Empty dict

        criteria.from_dict(data)

        # Should use defaults for missing keys
        assert criteria.min_vcpu is None  # Reset to default
        assert criteria.gpu_filter == "any"
        assert criteria.storage_type == "any"

    def test_has_active_filters_false_by_default(self):
        """Test has_active_filters() returns False when no filters set"""
        criteria = FilterCriteria()

        assert criteria.has_active_filters() is False

    def test_has_active_filters_with_vcpu_filter(self):
        """Test has_active_filters() returns True with vCPU filter"""
        criteria = FilterCriteria()
        criteria.min_vcpu = 2

        assert criteria.has_active_filters() is True

    def test_has_active_filters_with_memory_filter(self):
        """Test has_active_filters() returns True with memory filter"""
        criteria = FilterCriteria()
        criteria.max_memory_gb = 16.0

        assert criteria.has_active_filters() is True

    def test_has_active_filters_with_gpu_filter(self):
        """Test has_active_filters() returns True with GPU filter"""
        criteria = FilterCriteria()
        criteria.gpu_filter = "yes"

        assert criteria.has_active_filters() is True

    def test_has_active_filters_with_storage_type_filter(self):
        """Test has_active_filters() returns True with storage type filter"""
        criteria = FilterCriteria()
        criteria.storage_type = "ebs_only"

        assert criteria.has_active_filters() is True

    def test_has_active_filters_with_nvme_filter(self):
        """Test has_active_filters() returns True with NVMe filter"""
        criteria = FilterCriteria()
        criteria.nvme_support = "required"

        assert criteria.has_active_filters() is True

    def test_has_active_filters_with_processor_family(self):
        """Test has_active_filters() returns True with processor family filter"""
        criteria = FilterCriteria()
        criteria.processor_family = "intel"

        assert criteria.has_active_filters() is True

    def test_has_active_filters_with_price_filter(self):
        """Test has_active_filters() returns True with price filter"""
        criteria = FilterCriteria()
        criteria.min_price = 0.01

        assert criteria.has_active_filters() is True

    def test_has_active_filters_with_family_filter(self):
        """Test has_active_filters() returns True with family filter"""
        criteria = FilterCriteria()
        criteria.family_filter = "t3, m5"

        assert criteria.has_active_filters() is True

    def test_has_active_filters_with_whitespace_family_filter(self):
        """Test has_active_filters() returns False with whitespace-only family filter"""
        criteria = FilterCriteria()
        criteria.family_filter = "   "

        assert criteria.has_active_filters() is False

    def test_reset(self):
        """Test FilterCriteria.reset() clears all filters"""
        criteria = FilterCriteria()
        criteria.min_vcpu = 4
        criteria.max_vcpu = 16
        criteria.gpu_filter = "yes"
        criteria.storage_type = "ebs_only"
        criteria.min_price = 0.01

        criteria.reset()

        assert criteria.min_vcpu is None
        assert criteria.max_vcpu is None
        assert criteria.gpu_filter == "any"
        assert criteria.storage_type == "any"
        assert criteria.min_price is None


# Test app for FilterModal tests
class FilterModalTestApp(App):
    """Test app for FilterModal"""

    CSS = """
    Screen {
        align: center middle;
    }
    """

    def __init__(self, initial_criteria: FilterCriteria = None):
        super().__init__()
        self.initial_criteria = initial_criteria
        self.dismiss_result = None

    def compose(self) -> ComposeResult:
        yield Button("Open Filter", id="open-filter")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "open-filter":
            self.push_screen(
                FilterModal(self.initial_criteria),
                callback=self._on_dismiss
            )

    def _on_dismiss(self, result):
        self.dismiss_result = result

    def get_modal(self):
        """Get the current modal screen if one is active"""
        if len(self.screen_stack) > 1:
            return self.screen_stack[-1]
        return None


class TestFilterModalUI:
    """Tests for FilterModal UI interactions"""

    @pytest.mark.asyncio
    async def test_filter_modal_opens(self):
        """Test that filter modal opens correctly"""
        app = FilterModalTestApp()
        async with app.run_test(size=(100, 80)) as pilot:
            # Open the modal
            await pilot.click("#open-filter")
            await pilot.pause()

            # Check that modal is displayed (on top of screen stack)
            modal = app.get_modal()
            assert modal is not None
            assert isinstance(modal, FilterModal)

    @pytest.mark.asyncio
    async def test_filter_modal_cancel_button(self):
        """Test that cancel button dismisses modal with None"""
        app = FilterModalTestApp()
        async with app.run_test(size=(100, 80)) as pilot:
            # Open the modal
            await pilot.click("#open-filter")
            await pilot.pause()

            # Click cancel button
            await pilot.click("#cancel-button")
            await pilot.pause()

            # Should have dismissed with None
            assert app.dismiss_result is None

    @pytest.mark.asyncio
    async def test_filter_modal_escape_key(self):
        """Test that escape key dismisses modal with None"""
        app = FilterModalTestApp()
        async with app.run_test(size=(100, 80)) as pilot:
            # Open the modal
            await pilot.click("#open-filter")
            await pilot.pause()

            # Press escape
            await pilot.press("escape")
            await pilot.pause()

            # Should have dismissed with None
            assert app.dismiss_result is None

    @pytest.mark.asyncio
    async def test_filter_modal_apply_empty_filters(self):
        """Test that applying with no filters returns empty criteria"""
        app = FilterModalTestApp()
        async with app.run_test(size=(100, 80)) as pilot:
            # Open the modal
            await pilot.click("#open-filter")
            await pilot.pause()

            # Click apply without changing anything
            await pilot.click("#apply-button")
            await pilot.pause()

            # Should have criteria with default values
            assert app.dismiss_result is not None
            assert app.dismiss_result.has_active_filters() is False

    @pytest.mark.asyncio
    async def test_filter_modal_preserves_initial_criteria(self):
        """Test that modal preserves initial filter criteria"""
        initial = FilterCriteria()
        initial.min_vcpu = 4
        initial.gpu_filter = "yes"

        app = FilterModalTestApp(initial_criteria=initial)
        async with app.run_test(size=(100, 80)) as pilot:
            # Open the modal
            await pilot.click("#open-filter")
            await pilot.pause()

            # Check that inputs have the initial values
            modal = app.get_modal()
            assert isinstance(modal, FilterModal)
            min_vcpu_input = modal.query_one("#min-vcpu", Input)
            assert min_vcpu_input.value == "4"

            gpu_select = modal.query_one("#gpu-filter", Select)
            assert gpu_select.value == "yes"

    @pytest.mark.asyncio
    async def test_filter_modal_reset_button(self):
        """Test that reset button clears all filters"""
        initial = FilterCriteria()
        initial.min_vcpu = 4
        initial.max_memory_gb = 32.0
        initial.gpu_filter = "yes"
        initial.storage_type = "ebs_only"

        app = FilterModalTestApp(initial_criteria=initial)
        async with app.run_test(size=(100, 80)) as pilot:
            # Open the modal
            await pilot.click("#open-filter")
            await pilot.pause()

            # Click reset button
            await pilot.click("#reset-button")
            await pilot.pause()

            # Check that inputs are reset
            modal = app.get_modal()
            assert isinstance(modal, FilterModal)
            min_vcpu_input = modal.query_one("#min-vcpu", Input)
            assert min_vcpu_input.value == ""

            gpu_select = modal.query_one("#gpu-filter", Select)
            assert gpu_select.value == "any"

            storage_select = modal.query_one("#storage-type-filter", Select)
            assert storage_select.value == "any"

    @pytest.mark.asyncio
    async def test_filter_modal_apply_with_values(self):
        """Test that applying with values returns correct criteria"""
        app = FilterModalTestApp()
        async with app.run_test(size=(100, 80)) as pilot:
            # Open the modal
            await pilot.click("#open-filter")
            await pilot.pause()

            # Set some filter values by clicking on the input and typing
            modal = app.get_modal()
            assert isinstance(modal, FilterModal)

            # Focus and type in min-vcpu
            min_vcpu_input = modal.query_one("#min-vcpu", Input)
            min_vcpu_input.focus()
            await pilot.pause()
            # Clear and type
            min_vcpu_input.value = "4"
            await pilot.pause()

            # Click apply
            await pilot.click("#apply-button")
            await pilot.pause()

            # Verify the result
            assert app.dismiss_result is not None
            assert app.dismiss_result.min_vcpu == 4

    @pytest.mark.asyncio
    async def test_filter_modal_invalid_vcpu_input(self):
        """Test that invalid vCPU input is ignored"""
        app = FilterModalTestApp()
        async with app.run_test(size=(100, 80)) as pilot:
            # Open the modal
            await pilot.click("#open-filter")
            await pilot.pause()

            modal = app.get_modal()
            assert isinstance(modal, FilterModal)

            # Set invalid value
            min_vcpu_input = modal.query_one("#min-vcpu", Input)
            min_vcpu_input.value = "not-a-number"
            await pilot.pause()

            # Click apply
            await pilot.click("#apply-button")
            await pilot.pause()

            # min_vcpu should be None (invalid input ignored)
            assert app.dismiss_result is not None
            assert app.dismiss_result.min_vcpu is None

    @pytest.mark.asyncio
    async def test_filter_modal_invalid_memory_input(self):
        """Test that invalid memory input is ignored"""
        app = FilterModalTestApp()
        async with app.run_test(size=(100, 80)) as pilot:
            # Open the modal
            await pilot.click("#open-filter")
            await pilot.pause()

            modal = app.get_modal()
            assert isinstance(modal, FilterModal)

            # Set invalid value
            min_memory_input = modal.query_one("#min-memory", Input)
            min_memory_input.value = "abc"
            await pilot.pause()

            # Click apply
            await pilot.click("#apply-button")
            await pilot.pause()

            # min_memory_gb should be None (invalid input ignored)
            assert app.dismiss_result is not None
            assert app.dismiss_result.min_memory_gb is None

    @pytest.mark.asyncio
    async def test_filter_modal_price_range(self):
        """Test that price range filters work correctly"""
        app = FilterModalTestApp()
        async with app.run_test(size=(100, 80)) as pilot:
            # Open the modal
            await pilot.click("#open-filter")
            await pilot.pause()

            modal = app.get_modal()
            assert isinstance(modal, FilterModal)

            # Set price range values
            min_price_input = modal.query_one("#min-price", Input)
            min_price_input.value = "0.05"
            await pilot.pause()

            max_price_input = modal.query_one("#max-price", Input)
            max_price_input.value = "1.50"
            await pilot.pause()

            # Click apply
            await pilot.click("#apply-button")
            await pilot.pause()

            # Verify the result
            assert app.dismiss_result is not None
            assert app.dismiss_result.min_price == 0.05
            assert app.dismiss_result.max_price == 1.50

    @pytest.mark.asyncio
    async def test_filter_modal_family_filter(self):
        """Test that family filter works correctly"""
        app = FilterModalTestApp()
        async with app.run_test(size=(100, 80)) as pilot:
            # Open the modal
            await pilot.click("#open-filter")
            await pilot.pause()

            modal = app.get_modal()
            assert isinstance(modal, FilterModal)

            # Set family filter value
            family_input = modal.query_one("#family-filter", Input)
            family_input.value = "t3, m5, c6i"
            await pilot.pause()

            # Click apply
            await pilot.click("#apply-button")
            await pilot.pause()

            # Verify the result
            assert app.dismiss_result is not None
            assert app.dismiss_result.family_filter == "t3, m5, c6i"
            assert app.dismiss_result.has_active_filters() is True

    @pytest.mark.asyncio
    async def test_filter_modal_has_all_expected_inputs(self):
        """Test that filter modal has all expected input fields"""
        app = FilterModalTestApp()
        async with app.run_test(size=(100, 80)) as pilot:
            # Open the modal
            await pilot.click("#open-filter")
            await pilot.pause()

            modal = app.get_modal()
            assert isinstance(modal, FilterModal)

            # Check for all expected inputs
            assert modal.query_one("#min-vcpu", Input) is not None
            assert modal.query_one("#max-vcpu", Input) is not None
            assert modal.query_one("#min-memory", Input) is not None
            assert modal.query_one("#max-memory", Input) is not None
            assert modal.query_one("#gpu-filter", Select) is not None
            assert modal.query_one("#current-gen-filter", Select) is not None
            assert modal.query_one("#burstable-filter", Select) is not None
            assert modal.query_one("#free-tier-filter", Select) is not None
            assert modal.query_one("#arch-filter", Select) is not None
            assert modal.query_one("#processor-family-filter", Select) is not None
            assert modal.query_one("#network-performance-filter", Select) is not None
            assert modal.query_one("#family-filter", Input) is not None
            assert modal.query_one("#storage-type-filter", Select) is not None
            assert modal.query_one("#nvme-filter", Select) is not None
            assert modal.query_one("#min-price", Input) is not None
            assert modal.query_one("#max-price", Input) is not None

    @pytest.mark.asyncio
    async def test_filter_modal_has_buttons(self):
        """Test that filter modal has all expected buttons"""
        app = FilterModalTestApp()
        async with app.run_test(size=(100, 80)) as pilot:
            # Open the modal
            await pilot.click("#open-filter")
            await pilot.pause()

            modal = app.get_modal()
            assert isinstance(modal, FilterModal)

            # Check for buttons
            assert modal.query_one("#apply-button", Button) is not None
            assert modal.query_one("#reset-button", Button) is not None
            assert modal.query_one("#cancel-button", Button) is not None
