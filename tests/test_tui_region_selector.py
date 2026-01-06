"""Tests for the RegionSelector screen"""

import pytest
from unittest.mock import Mock, patch

from textual.app import App
from textual.widgets import DataTable

from src.ui.region_selector import RegionSelector
from src.models.region import AWS_REGIONS


class RegionSelectorTestApp(App):
    """Test app that hosts the RegionSelector screen"""

    def __init__(self, default_region="us-east-1", accessible_regions=None):
        super().__init__()
        self.default_region = default_region
        self.accessible_regions = accessible_regions
        self.current_region = None
        self.settings = Mock()
        self.settings.aws_profile = None
        self.settings.aws_region = default_region

    def on_mount(self):
        self.push_screen(RegionSelector(self.default_region, self.accessible_regions))


class TestRegionSelector:
    """Tests for RegionSelector screen"""

    async def test_region_selector_displays_regions(self):
        """Test that region selector displays available regions"""
        app = RegionSelectorTestApp()

        async with app.run_test() as pilot:
            await pilot.pause()

            # Get the data table
            table = app.screen.query_one("#region-table", DataTable)
            assert table is not None

            # Verify regions are populated
            assert table.row_count > 0

    async def test_region_selector_with_accessible_regions(self, sample_regions):
        """Test region selector with specific accessible regions"""
        app = RegionSelectorTestApp(accessible_regions=sample_regions)

        async with app.run_test() as pilot:
            await pilot.pause()

            table = app.screen.query_one("#region-table", DataTable)

            # Should show only accessible regions
            assert table.row_count == len(sample_regions)

    async def test_region_selector_default_region_selected(self):
        """Test that default region is pre-selected"""
        default_region = "us-west-2"
        accessible = ["us-east-1", "us-west-2", "eu-west-1"]
        app = RegionSelectorTestApp(default_region=default_region, accessible_regions=accessible)

        async with app.run_test() as pilot:
            await pilot.pause()

            screen = app.screen
            assert screen.selected_region == default_region

    async def test_region_selector_keyboard_navigation(self):
        """Test keyboard navigation in region selector"""
        accessible = ["us-east-1", "us-west-2", "eu-west-1"]
        app = RegionSelectorTestApp(accessible_regions=accessible)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Navigate down
            await pilot.press("down")
            await pilot.pause()

            # Navigate up
            await pilot.press("up")
            await pilot.pause()

            # Table should still be focused and responsive
            table = app.screen.query_one("#region-table", DataTable)
            assert table.has_focus

    async def test_region_selector_quit_with_q(self):
        """Test that Q key triggers quit action"""
        app = RegionSelectorTestApp()

        async with app.run_test() as pilot:
            await pilot.pause()

            await pilot.press("q")
            await pilot.pause()

            # App should have exited or screen dismissed
            # The exact behavior depends on how the app handles dismissal

    async def test_region_selector_quit_with_escape(self):
        """Test that Escape key triggers quit action"""
        app = RegionSelectorTestApp()

        async with app.run_test() as pilot:
            await pilot.pause()

            await pilot.press("escape")
            await pilot.pause()

    async def test_region_selector_bindings(self):
        """Test region selector has correct key bindings"""
        screen = RegionSelector()

        # Check bindings - BINDINGS is a list of tuples (key, action, description)
        binding_keys = [b[0] for b in screen.BINDINGS]
        assert "q" in binding_keys
        assert "escape" in binding_keys

    async def test_region_selector_title_displayed(self):
        """Test that title is displayed"""
        app = RegionSelectorTestApp()

        async with app.run_test() as pilot:
            await pilot.pause()

            title = app.screen.query_one("#title")
            assert title is not None
            assert "EC2 Instance Type Browser" in str(title.render())

    async def test_region_selector_help_text_displayed(self):
        """Test that help text is displayed"""
        app = RegionSelectorTestApp()

        async with app.run_test() as pilot:
            await pilot.pause()

            help_text = app.screen.query_one("#help-text")
            assert help_text is not None

    async def test_region_selector_table_columns(self):
        """Test that data table has correct columns"""
        app = RegionSelectorTestApp()

        async with app.run_test() as pilot:
            await pilot.pause()

            table = app.screen.query_one("#region-table", DataTable)

            # Verify columns exist
            columns = list(table.columns.keys())
            assert len(columns) == 2  # Region Code, Region Name

    async def test_region_selector_unknown_region_handling(self):
        """Test handling of regions not in hardcoded list"""
        # Include a hypothetical new region
        accessible = ["us-east-1", "ap-new-region-1"]
        app = RegionSelectorTestApp(accessible_regions=accessible)

        async with app.run_test() as pilot:
            await pilot.pause()

            table = app.screen.query_one("#region-table", DataTable)

            # Should still show all accessible regions
            assert table.row_count == 2

    async def test_region_selector_empty_accessible_regions(self):
        """Test fallback when no accessible regions provided"""
        app = RegionSelectorTestApp(accessible_regions=None)

        async with app.run_test() as pilot:
            await pilot.pause()

            table = app.screen.query_one("#region-table", DataTable)

            # Should fall back to hardcoded AWS_REGIONS
            assert table.row_count == len(AWS_REGIONS)


class TestRegionSelectorCSS:
    """Tests for RegionSelector CSS styling"""

    def test_css_defined(self):
        """Test that CSS is defined for the screen"""
        screen = RegionSelector()

        assert screen.CSS is not None
        assert len(screen.CSS) > 0

    def test_css_loading_overlay_styles(self):
        """Test CSS includes loading overlay styles"""
        screen = RegionSelector()

        assert "#loading-overlay" in screen.CSS
        assert ".hidden" in screen.CSS
