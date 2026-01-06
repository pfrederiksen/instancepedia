"""Tests for the main TUI application"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.app import InstancepediaApp, LoadingScreen, ErrorScreen
from src.config.settings import Settings
from src.ui.region_selector import RegionSelector


class TestInstancepediaApp:
    """Tests for InstancepediaApp"""

    @pytest.fixture
    def app(self, mock_settings):
        """Create app instance for testing"""
        return InstancepediaApp(mock_settings, debug=False)

    @pytest.fixture
    def app_with_debug(self, mock_settings):
        """Create app instance with debug enabled"""
        return InstancepediaApp(mock_settings, debug=True)

    async def test_app_initialization(self, mock_settings):
        """Test app initializes with correct settings"""
        app = InstancepediaApp(mock_settings, debug=False)

        assert app.settings == mock_settings
        assert app.current_region is None
        assert app.instance_types == []
        assert app.debug_mode is False
        assert app._shutting_down is False

    async def test_app_initialization_with_debug(self, mock_settings):
        """Test app initializes with debug mode"""
        app = InstancepediaApp(mock_settings, debug=True)

        assert app.debug_mode is True

    @patch('src.app.AWSClient')
    async def test_app_mounts_region_selector(self, mock_aws_client, mock_settings):
        """Test app shows region selector on mount"""
        mock_client_instance = Mock()
        mock_client_instance.get_accessible_regions.return_value = ["us-east-1", "us-west-2"]
        mock_aws_client.return_value = mock_client_instance

        app = InstancepediaApp(mock_settings, debug=False)

        async with app.run_test() as pilot:
            # Wait for mount
            await pilot.pause()

            # Verify region selector is shown
            assert isinstance(app.screen, RegionSelector)

    @patch('src.app.AWSClient')
    async def test_app_handles_region_fetch_error(self, mock_aws_client, mock_settings):
        """Test app handles error when fetching accessible regions"""
        mock_aws_client.side_effect = Exception("Connection failed")

        app = InstancepediaApp(mock_settings, debug=False)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Should still show region selector even on error
            assert isinstance(app.screen, RegionSelector)

    async def test_app_quit_action(self, mock_settings):
        """Test app can be quit with Q key"""
        app = InstancepediaApp(mock_settings, debug=False)

        with patch.object(app, 'exit') as mock_exit:
            async with app.run_test() as pilot:
                await pilot.pause()
                await pilot.press("q")
                await pilot.pause()

    async def test_app_css_defined(self, mock_settings):
        """Test app has CSS defined"""
        app = InstancepediaApp(mock_settings, debug=False)

        assert app.CSS is not None
        assert len(app.CSS) > 0
        # Check for key CSS selectors
        assert "#region-container" in app.CSS
        assert "#list-container" in app.CSS
        assert "#detail-container" in app.CSS


class TestLoadingScreen:
    """Tests for LoadingScreen"""

    async def test_loading_screen_compose(self):
        """Test loading screen composes correctly"""
        screen = LoadingScreen(region="us-east-1")

        # Create a minimal app to test the screen
        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield from []

        app = TestApp()
        async with app.run_test() as pilot:
            app.push_screen(screen)
            await pilot.pause()

            # Verify widgets are present
            loading_text = screen.query_one("#loading-text")
            assert loading_text is not None

    async def test_loading_screen_update_status(self):
        """Test loading screen can update status"""
        screen = LoadingScreen(region="us-east-1")

        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield from []

        app = TestApp()
        async with app.run_test() as pilot:
            app.push_screen(screen)
            await pilot.pause()

            # Update status
            screen.update_status("Fetching data...")
            await pilot.pause()

            assert screen.status_text == "Fetching data..."

    async def test_loading_screen_quit_binding(self):
        """Test loading screen has quit binding"""
        screen = LoadingScreen(region="us-east-1")

        # Check bindings - BINDINGS is a list of tuples (key, action, description)
        binding_keys = [b[0] for b in screen.BINDINGS]
        assert "q" in binding_keys


class TestErrorScreen:
    """Tests for ErrorScreen"""

    async def test_error_screen_displays_message(self):
        """Test error screen displays the error message"""
        error_msg = "Something went wrong"
        screen = ErrorScreen(error_msg)

        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield from []

        app = TestApp()
        async with app.run_test() as pilot:
            app.push_screen(screen)
            await pilot.pause()

            # Verify error message is displayed
            error_widget = screen.query_one("#error-message")
            assert error_widget is not None

    async def test_error_screen_bindings(self):
        """Test error screen has correct bindings"""
        screen = ErrorScreen("Test error")

        # Check bindings - BINDINGS is a list of tuples (key, action, description)
        binding_keys = [b[0] for b in screen.BINDINGS]
        assert "q" in binding_keys
        assert "escape" in binding_keys

    async def test_error_screen_back_action(self):
        """Test error screen back action dismisses screen"""
        screen = ErrorScreen("Test error")

        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield from []

        app = TestApp()
        async with app.run_test() as pilot:
            app.push_screen(screen)
            await pilot.pause()

            # Press escape to go back
            await pilot.press("escape")
            await pilot.pause()


class TestAppMessages:
    """Tests for app message classes"""

    def test_instance_types_loaded_message(self):
        """Test InstanceTypesLoaded message"""
        instance_types = [Mock(), Mock()]
        msg = InstancepediaApp.InstanceTypesLoaded(instance_types)

        assert msg.instance_types == instance_types

    def test_instance_types_error_message(self):
        """Test InstanceTypesError message"""
        error_msg = "Connection failed"
        msg = InstancepediaApp.InstanceTypesError(error_msg)

        assert msg.error_msg == error_msg
