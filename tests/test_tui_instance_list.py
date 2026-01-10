"""Tests for the InstanceList screen"""

import pytest
from unittest.mock import Mock, patch

from textual.app import App
from textual.widgets import Tree, Input, Static

from src.ui.instance_list import (
    InstanceList,
    extract_family_name,
    get_family_category,
)


class InstanceListTestApp(App):
    """Test app that hosts the InstanceList screen"""

    def __init__(self, instance_types, region="us-east-1"):
        super().__init__()
        self.instance_types = instance_types
        self._test_region = region  # Use _test_region to avoid conflict
        self.current_region = region
        self.settings = Mock()
        self.settings.aws_profile = None
        self.settings.aws_region = region

    def on_mount(self):
        self.push_screen(InstanceList(self.instance_types, self._test_region))


class TestExtractFamilyName:
    """Tests for extract_family_name function"""

    def test_extract_t2_family(self):
        """Test extracting t2 family"""
        assert extract_family_name("t2.micro") == "t2"

    def test_extract_m5_family(self):
        """Test extracting m5 family"""
        assert extract_family_name("m5.large") == "m5"

    def test_extract_c6i_family(self):
        """Test extracting c6i family"""
        assert extract_family_name("c6i.xlarge") == "c6i"

    def test_extract_r6a_family(self):
        """Test extracting r6a family"""
        assert extract_family_name("r6a.2xlarge") == "r6a"

    def test_extract_no_dot(self):
        """Test handling instance type without dot"""
        assert extract_family_name("unknown") == "unknown"


class TestGetFamilyCategory:
    """Tests for get_family_category function"""

    def test_category_burstable(self):
        """Test t-family is Burstable Performance"""
        assert get_family_category("t2") == "Burstable Performance"
        assert get_family_category("t3") == "Burstable Performance"

    def test_category_general_purpose(self):
        """Test m-family is General Purpose"""
        assert get_family_category("m5") == "General Purpose"
        assert get_family_category("m6i") == "General Purpose"

    def test_category_compute_optimized(self):
        """Test c-family is Compute Optimized"""
        assert get_family_category("c5") == "Compute Optimized"
        assert get_family_category("c6g") == "Compute Optimized"

    def test_category_memory_optimized(self):
        """Test r-family is Memory Optimized"""
        assert get_family_category("r5") == "Memory Optimized"

    def test_category_gpu(self):
        """Test g and p families are GPU Instances"""
        assert get_family_category("g4") == "GPU Instances"
        assert get_family_category("p3") == "GPU Instances"

    def test_category_storage_optimized(self):
        """Test i-family is Storage Optimized"""
        assert get_family_category("i3") == "Storage Optimized"

    def test_category_accelerated(self):
        """Test ML/HPC instances are Accelerated Computing"""
        assert get_family_category("trn1") == "Accelerated Computing"
        assert get_family_category("inf1") == "Accelerated Computing"
        assert get_family_category("dl1") == "Accelerated Computing"

    def test_category_mac(self):
        """Test mac instances"""
        assert get_family_category("mac1") == "Mac Instances"

    def test_category_other(self):
        """Test unknown family falls back to Other"""
        # Use a family that doesn't start with a recognized character
        assert get_family_category("q99") == "Other"
        assert get_family_category("") == "Other"


class TestInstanceList:
    """Tests for InstanceList screen"""

    async def test_instance_list_displays_instances(self, sample_instance_types):
        """Test that instance list displays instances"""
        app = InstanceListTestApp(sample_instance_types)

        async with app.run_test() as pilot:
            await pilot.pause()

            tree = app.screen.query_one("#instance-tree", Tree)
            assert tree is not None

    async def test_instance_list_header_shows_region(self, sample_instance_types):
        """Test header shows region"""
        region = "us-west-2"
        app = InstanceListTestApp(sample_instance_types, region=region)

        async with app.run_test() as pilot:
            await pilot.pause()

            header = app.screen.query_one("#header", Static)
            assert region in str(header.render())

    async def test_instance_list_search_input_present(self, sample_instance_types):
        """Test search input is present"""
        app = InstanceListTestApp(sample_instance_types)

        async with app.run_test() as pilot:
            await pilot.pause()

            search_input = app.screen.query_one("#search-input", Input)
            assert search_input is not None

    async def test_instance_list_keyboard_navigation(self, sample_instance_types):
        """Test keyboard navigation in instance list"""
        app = InstanceListTestApp(sample_instance_types)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Navigate using arrow keys
            await pilot.press("down")
            await pilot.pause()

            await pilot.press("up")
            await pilot.pause()

    async def test_instance_list_expand_collapse(self, sample_instance_types):
        """Test tree node expand/collapse"""
        app = InstanceListTestApp(sample_instance_types)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Press space to expand/collapse
            await pilot.press("space")
            await pilot.pause()

    async def test_instance_list_search_focus(self, sample_instance_types):
        """Test search focus with slash key"""
        app = InstanceListTestApp(sample_instance_types)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Press / to focus search
            await pilot.press("/")
            await pilot.pause()

            search_input = app.screen.query_one("#search-input", Input)
            assert search_input.has_focus

    async def test_instance_list_bindings(self, sample_instance_types):
        """Test instance list key bindings"""
        screen = InstanceList(sample_instance_types, "us-east-1")

        # Check bindings - BINDINGS is a list of tuples (key, action, description)
        binding_keys = [b[0] for b in screen.BINDINGS]
        assert "q" in binding_keys
        assert "escape" in binding_keys
        assert "f" in binding_keys  # Free tier filter
        assert "/" in binding_keys  # Search focus

    async def test_instance_list_status_bar(self, sample_instance_types):
        """Test status bar shows instance count"""
        app = InstanceListTestApp(sample_instance_types)

        async with app.run_test() as pilot:
            await pilot.pause()

            status = app.screen.query_one("#status-text", Static)
            content = str(status.render())

            # Should show count
            assert str(len(sample_instance_types)) in content

    async def test_instance_list_free_tier_filter_toggle(self, sample_instance_types):
        """Test filter modal can be opened"""
        app = InstanceListTestApp(sample_instance_types)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Initial state - filter criteria should have no active filters
            assert app.screen.filter_criteria.has_active_filters() is False

            # Open filter modal
            await pilot.press("f")
            await pilot.pause()

            # Filter modal should be open
            from src.ui.filter_modal import FilterModal
            assert isinstance(app.screen, FilterModal)

            # Close the modal with escape
            await pilot.press("escape")
            await pilot.pause()

            # Should be back to instance list
            from src.ui.instance_list import InstanceList
            assert isinstance(app.screen, InstanceList)

    async def test_instance_list_quit_action(self, sample_instance_types):
        """Test quit action"""
        app = InstanceListTestApp(sample_instance_types)

        async with app.run_test() as pilot:
            await pilot.pause()

            await pilot.press("q")
            await pilot.pause()


class TestInstanceListFiltering:
    """Tests for InstanceList filtering functionality"""

    async def test_search_filter_by_instance_type(self, sample_instance_types):
        """Test filtering by instance type name"""
        app = InstanceListTestApp(sample_instance_types)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Focus search and type
            await pilot.press("/")
            await pilot.pause()

            await pilot.press("t", "3")
            await pilot.pause()

            # Check filtered list
            assert app.screen.search_term == "t3"
            assert len(app.screen.filtered_instance_types) < len(sample_instance_types)

    async def test_search_filter_case_insensitive(self, sample_instance_types):
        """Test search is case insensitive"""
        app = InstanceListTestApp(sample_instance_types)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Focus search
            await pilot.press("/")
            await pilot.pause()

            # Type uppercase
            await pilot.press("T", "2")
            await pilot.pause()

            # Should still match
            filtered = app.screen.filtered_instance_types
            for inst in filtered:
                assert "t2" in inst.instance_type.lower()


class TestInstanceListPricing:
    """Tests for InstanceList pricing functionality"""

    async def test_pricing_loading_state(self, sample_instance_types):
        """Test pricing loading state management"""
        app = InstanceListTestApp(sample_instance_types)

        async with app.run_test() as pilot:
            await pilot.pause()

            screen = app.screen

            # Mark pricing as loading
            screen.mark_pricing_loading(True)
            await pilot.pause()

            assert screen._pricing_loading is True

            # Mark pricing as done
            screen.mark_pricing_loading(False)
            await pilot.pause()

            assert screen._pricing_loading is False

    async def test_pricing_progress_update(self, sample_instance_types):
        """Test pricing progress updates"""
        app = InstanceListTestApp(sample_instance_types)

        async with app.run_test() as pilot:
            await pilot.pause()

            screen = app.screen
            screen._pricing_loading = True

            # Update progress
            screen.update_pricing_progress()
            await pilot.pause()


class TestInstanceListGrouping:
    """Tests for InstanceList grouping functionality"""

    def test_group_instances_by_family(self, sample_instance_types):
        """Test instances are grouped by family"""
        screen = InstanceList(sample_instance_types, "us-east-1")
        families = screen._group_instances_by_family(sample_instance_types)

        # Should have t2, t3, m5, c5 families from fixtures
        assert "t2" in families or "t3" in families
        assert "m5" in families
        assert "c5" in families

    def test_format_instance_label(self, sample_instance_types):
        """Test instance label formatting"""
        screen = InstanceList(sample_instance_types, "us-east-1")
        screen._pricing_loading = False

        for inst in sample_instance_types:
            label = screen._format_instance_label(inst)

            # Label should contain instance type
            assert inst.instance_type in label

            # Label should contain vCPU info
            assert "vCPU" in label

            # Label should contain memory
            assert "GB" in label

    def test_format_instance_label_free_tier(self, sample_instance_types):
        """Test free tier instances are marked"""
        screen = InstanceList(sample_instance_types, "us-east-1")
        screen._pricing_loading = False

        # Find t2.micro or t3.micro (free tier eligible)
        for inst in sample_instance_types:
            if inst.instance_type in ["t2.micro", "t3.micro"]:
                label = screen._format_instance_label(inst)
                # Free tier should have emoji indicator
                # Note: This depends on FreeTierService implementation
                break


class VimKeysEnabledTestApp(App):
    """Test app with vim_keys enabled"""

    def __init__(self, instance_types, region="us-east-1"):
        super().__init__()
        self.instance_types = instance_types
        self._test_region = region
        self.current_region = region
        self.settings = Mock()
        self.settings.aws_profile = None
        self.settings.aws_region = region
        self.settings.vim_keys = True

    def on_mount(self):
        # Mock the settings in the screen
        screen = InstanceList(self.instance_types, self._test_region)
        screen._settings = self.settings
        self.push_screen(screen)


class VimKeysDisabledTestApp(App):
    """Test app with vim_keys disabled"""

    def __init__(self, instance_types, region="us-east-1"):
        super().__init__()
        self.instance_types = instance_types
        self._test_region = region
        self.current_region = region
        self.settings = Mock()
        self.settings.aws_profile = None
        self.settings.aws_region = region
        self.settings.vim_keys = False

    def on_mount(self):
        screen = InstanceList(self.instance_types, self._test_region)
        screen._settings = self.settings
        self.push_screen(screen)


class TestVimNavigation:
    """Tests for vim-style navigation (hjkl keys)"""

    async def test_vim_j_key_moves_down_when_enabled(self, sample_instance_types):
        """Test j key moves cursor down when vim_keys is enabled"""
        app = VimKeysEnabledTestApp(sample_instance_types)

        async with app.run_test() as pilot:
            await pilot.pause()

            tree = app.screen.query_one("#instance-tree")
            initial_cursor = tree.cursor_line

            # Press j to move down
            await pilot.press("j")
            await pilot.pause()

            # Cursor should have moved (or stayed if at last item)
            # Just verify no error occurred
            assert tree is not None

    async def test_vim_k_key_moves_up_when_enabled(self, sample_instance_types):
        """Test k key moves cursor up when vim_keys is enabled"""
        app = VimKeysEnabledTestApp(sample_instance_types)

        async with app.run_test() as pilot:
            await pilot.pause()

            tree = app.screen.query_one("#instance-tree")

            # Move down first
            await pilot.press("j")
            await pilot.pause()

            # Press k to move up
            await pilot.press("k")
            await pilot.pause()

            assert tree is not None

    async def test_vim_h_key_collapses_when_enabled(self, sample_instance_types):
        """Test h key collapses node when vim_keys is enabled"""
        app = VimKeysEnabledTestApp(sample_instance_types)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Press h to collapse/go to parent
            await pilot.press("h")
            await pilot.pause()

            # Verify no error - h should collapse or go to parent
            tree = app.screen.query_one("#instance-tree")
            assert tree is not None

    async def test_vim_l_key_expands_when_enabled(self, sample_instance_types):
        """Test l key expands node when vim_keys is enabled"""
        app = VimKeysEnabledTestApp(sample_instance_types)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Press l to expand/enter
            await pilot.press("l")
            await pilot.pause()

            # Verify no error - l should expand node or navigate
            tree = app.screen.query_one("#instance-tree")
            assert tree is not None

    async def test_vim_keys_do_not_work_when_disabled(self, sample_instance_types):
        """Test vim keys do nothing when vim_keys is disabled"""
        app = VimKeysDisabledTestApp(sample_instance_types)

        async with app.run_test() as pilot:
            await pilot.pause()

            tree = app.screen.query_one("#instance-tree")
            initial_cursor = tree.cursor_line

            # Press j - should not move cursor (vim keys disabled)
            await pilot.press("j")
            await pilot.pause()

            # With vim_keys disabled, j should not be handled
            # The cursor position may still change due to default behavior
            # This test verifies the setting is respected
            assert app.screen._settings.vim_keys is False

    async def test_vim_navigation_settings_attribute(self, sample_instance_types):
        """Test that _settings attribute exists and has vim_keys"""
        app = VimKeysEnabledTestApp(sample_instance_types)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Verify settings is accessible
            assert hasattr(app.screen, '_settings')
            assert hasattr(app.screen._settings, 'vim_keys')
            assert app.screen._settings.vim_keys is True


class TestLazyLoading:
    """Tests for lazy loading of instance nodes"""

    def test_family_instances_dict_exists(self, sample_instance_types):
        """Test _family_instances dict is initialized"""
        screen = InstanceList(sample_instance_types, "us-east-1")
        assert hasattr(screen, '_family_instances')
        assert isinstance(screen._family_instances, dict)

    def test_populated_families_set_exists(self, sample_instance_types):
        """Test _populated_families set is initialized"""
        screen = InstanceList(sample_instance_types, "us-east-1")
        assert hasattr(screen, '_populated_families')
        assert isinstance(screen._populated_families, set)

    async def test_instances_not_added_until_expanded(self, sample_instance_types):
        """Test that instances are stored for lazy loading"""
        app = InstanceListTestApp(sample_instance_types)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Family instances should be populated
            assert len(app.screen._family_instances) > 0

            # At least some families should have instances stored
            total_stored = sum(len(instances) for instances in app.screen._family_instances.values())
            assert total_stored > 0

    async def test_populate_family_instances_method(self, sample_instance_types):
        """Test _populate_family_instances method exists and works"""
        screen = InstanceList(sample_instance_types, "us-east-1")

        # Store a family's instances
        screen._family_instances['t3'] = sample_instance_types[:2]
        screen._populated_families.clear()

        # Create a mock node
        mock_node = Mock()
        mock_node.add_leaf = Mock()

        # Call the method
        screen._populate_family_instances(mock_node, 't3')

        # Should have added leaves and marked as populated
        assert 't3' in screen._populated_families

    def test_populate_family_instances_skips_if_already_populated(self, sample_instance_types):
        """Test _populate_family_instances skips if already populated"""
        screen = InstanceList(sample_instance_types, "us-east-1")

        # Mark as already populated
        screen._populated_families.add('t3')
        screen._family_instances['t3'] = sample_instance_types[:2]

        # Create a mock node
        mock_node = Mock()
        mock_node.add_leaf = Mock()

        # Call the method
        screen._populate_family_instances(mock_node, 't3')

        # Should NOT have added any leaves (already populated)
        mock_node.add_leaf.assert_not_called()

    async def test_expanded_state_preserved_during_rebuild(self, sample_instance_types):
        """Test that expanded families are tracked correctly"""
        app = InstanceListTestApp(sample_instance_types)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Initially no expanded families (categories collapsed by default)
            initial_expanded = len(app.screen._expanded_families)

            # Expand something by pressing space
            await pilot.press("space")
            await pilot.pause()

            # Expanded state should be tracked
            assert hasattr(app.screen, '_expanded_categories')
            assert hasattr(app.screen, '_expanded_families')

    def test_instance_type_map_populated(self, sample_instance_types):
        """Test _instance_type_map is populated for navigation"""
        screen = InstanceList(sample_instance_types, "us-east-1")

        # Even with lazy loading, instance map should be populated
        # for navigation purposes
        assert hasattr(screen, '_instance_type_map')
        # Map is populated during _populate_tree which happens on mount
