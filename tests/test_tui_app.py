"""Tests for the main TUI application"""

import asyncio
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


class TestInstancepediaAppWorkers:
    """Tests for InstancepediaApp worker state management"""

    @pytest.fixture
    def app(self, mock_settings):
        """Create app instance for testing"""
        return InstancepediaApp(mock_settings, debug=False)

    @patch('src.app.InstanceList')
    def test_on_worker_state_changed_success(self, mock_instance_list, app):
        """Test worker state change handler with SUCCESS state"""
        from textual.worker import WorkerState

        # Create mock worker with SUCCESS state
        mock_worker = Mock()
        mock_worker.result = [Mock(), Mock()]  # Mock instance types

        # Set as current worker
        app._current_worker = mock_worker

        # Create state changed event
        event = Mock()
        event.worker = mock_worker
        event.state = WorkerState.SUCCESS

        # Mock the handler's internal methods
        with patch.object(app, '_handle_fetch_success') as mock_success:
            # Call handler
            app.on_worker_state_changed(event)

            # Verify success handler was called with correct args
            mock_success.assert_called_once_with(mock_worker.result)

    def test_on_worker_state_changed_error(self, app):
        """Test worker state change handler with ERROR state"""
        from textual.worker import WorkerState

        # Create mock worker with ERROR state
        mock_worker = Mock()
        mock_worker.error = Exception("Fetch failed")

        # Set as current worker
        app._current_worker = mock_worker

        # Create state changed event
        event = Mock()
        event.worker = mock_worker
        event.state = WorkerState.ERROR

        # Mock the handler's internal methods
        with patch.object(app, '_handle_fetch_error') as mock_error:
            # Call handler
            app.on_worker_state_changed(event)

            # Verify error handler was called with correct args
            mock_error.assert_called_once_with(mock_worker.error)

    def test_on_worker_state_changed_ignores_other_workers(self, app):
        """Test worker state change handler ignores events from other workers"""
        from textual.worker import WorkerState

        # Create two different workers
        our_worker = Mock()
        other_worker = Mock()

        # Set our worker as current
        app._current_worker = our_worker

        # Create event for other worker
        event = Mock()
        event.worker = other_worker
        event.state = WorkerState.SUCCESS

        # Mock dependencies
        app.push_screen = Mock()
        app.pop_screen = Mock()

        # Call handler
        app.on_worker_state_changed(event)

        # Verify no action was taken
        app.push_screen.assert_not_called()
        app.pop_screen.assert_not_called()

    def test_on_worker_state_changed_handles_result_exception(self, app):
        """Test worker state handler gracefully handles exception when getting result"""
        from textual.worker import WorkerState

        # Create mock worker that raises exception when accessing result
        mock_worker = Mock()
        # Configure result property to raise exception
        type(mock_worker).result = property(lambda self: (_ for _ in ()).throw(Exception("Result access failed")))

        # Set as current worker
        app._current_worker = mock_worker

        # Create state changed event
        event = Mock()
        event.worker = mock_worker
        event.state = WorkerState.SUCCESS

        # Mock the handler's internal methods
        with patch.object(app, '_handle_fetch_error') as mock_error:
            # Call handler - should not raise exception
            app.on_worker_state_changed(event)

            # Verify error handler was called (fallback behavior)
            assert mock_error.called


class TestInstancepediaAppErrorHandling:
    """Tests for InstancepediaApp error handling"""

    @pytest.fixture
    def app(self, mock_settings):
        """Create app instance for testing"""
        return InstancepediaApp(mock_settings, debug=False)

    @patch('src.app.ErrorScreen')
    def test_handle_fetch_error_opt_in_region(self, mock_error_screen, app):
        """Test _handle_fetch_error detects opt-in region errors"""
        # Create error with opt-in region message
        error = Exception("OptInRequired: The requested region is not enabled for this account")

        # Mock screen operations
        app.pop_screen = Mock()
        app.push_screen = Mock()

        # Mock isinstance check to return True for RegionSelector
        with patch('src.app.isinstance', return_value=True):
            # Call error handler
            app._handle_fetch_error(error)

        # Verify error screen was created with appropriate message
        assert mock_error_screen.called
        call_args = mock_error_screen.call_args[0][0]
        assert "not enabled" in call_args.lower() or "opt-in" in call_args.lower()

    @patch('src.app.ErrorScreen')
    def test_handle_fetch_error_generic(self, mock_error_screen, app):
        """Test _handle_fetch_error handles generic errors"""
        # Create generic error
        error = Exception("Connection timeout")

        # Mock screen operations
        app.pop_screen = Mock()
        app.push_screen = Mock()

        # Mock isinstance check to return True for RegionSelector
        with patch('src.app.isinstance', return_value=True):
            # Call error handler
            app._handle_fetch_error(error)

        # Verify error screen was created
        assert mock_error_screen.called

    @patch('src.app.ErrorScreen')
    def test_handle_fetch_success_empty_instances(self, mock_error_screen, app):
        """Test _handle_fetch_success shows error for empty instance list"""
        # Call with empty list
        app.pop_screen = Mock()
        app.push_screen = Mock()

        # Mock isinstance check to return True for RegionSelector
        with patch('src.app.isinstance', return_value=True):
            app._handle_fetch_success([])

        # Verify error screen was pushed
        assert mock_error_screen.called
        call_args = mock_error_screen.call_args[0][0]
        assert "no instance types" in call_args.lower()

    @patch('src.app.InstanceList')
    def test_handle_fetch_success_with_instances(self, mock_instance_list, app):
        """Test _handle_fetch_success transitions to instance list"""
        # Mock instance types
        mock_instances = [Mock(), Mock(), Mock()]

        # Mock screen operations
        app.pop_screen = Mock()
        app.push_screen = Mock()
        app._fetch_pricing_background = Mock()  # Mock pricing fetch

        # Mock isinstance check to return True for RegionSelector
        with patch('src.app.isinstance', return_value=True):
            # Call handler
            app._handle_fetch_success(mock_instances)

        # Verify instances were stored
        assert app.instance_types == mock_instances
        # Verify screen transition occurred
        assert app.push_screen.called
        # Verify pricing fetch was initiated
        assert app._fetch_pricing_background.called


class TestInstancepediaAppPricingWorker:
    """Tests for InstancepediaApp async pricing worker"""

    @pytest.fixture
    def app(self, mock_settings):
        """Create app instance for testing"""
        return InstancepediaApp(mock_settings, debug=False)


    @pytest.mark.asyncio
    @patch('src.app.AsyncAWSClient')
    @patch('src.app.AsyncPricingService')
    async def test_fetch_pricing_background_handles_shutdown(self, mock_pricing_service_class, mock_aws_client_class, app):
        """Test _fetch_pricing_background handles app shutdown gracefully"""
        mock_instance_list = Mock()
        mock_instance_list.mark_pricing_loading = Mock()

        # Set app as shutting down
        app._shutting_down = True
        app.current_region = "us-east-1"

        # Call the method
        app._fetch_pricing_background(mock_instance_list)

        # Give async tasks time to run
        await asyncio.sleep(0.1)

        # Verify no AWS client was created when shutting down
        assert not mock_aws_client_class.called


    @pytest.mark.asyncio
    async def test_retry_pricing_skips_when_shutting_down(self, app):
        """Test _retry_pricing_for_instances skips when app is shutting down"""
        mock_instance = Mock()
        mock_instance.instance_type = "t3.micro"
        mock_instance.pricing = None

        mock_instance_list = Mock()
        mock_instance_list.instance_types = [mock_instance]

        # Set app as shutting down
        app._shutting_down = True
        app.current_region = "us-east-1"

        with patch('src.app.AsyncAWSClient') as mock_client_class:
            # Call _retry_pricing_for_instances
            app._retry_pricing_for_instances(mock_instance_list, [mock_instance])

            # Give async tasks time to run
            await asyncio.sleep(0.1)

            # Verify no client was created
            assert not mock_client_class.called

    @pytest.mark.asyncio
    async def test_retry_pricing_with_no_failed_instances(self, app):
        """Test _retry_pricing_for_instances with empty failed list"""
        # Setup instance list with all successful pricing
        from src.models.instance_type import PricingInfo

        mock_instance = Mock()
        mock_instance.instance_type = "t3.micro"
        mock_instance.pricing = PricingInfo(on_demand_price=0.01)  # Has pricing

        mock_instance_list = Mock()
        mock_instance_list.instance_types = [mock_instance]

        app.current_region = "us-east-1"

        with patch('src.app.AsyncAWSClient') as mock_client_class:
            # Call _retry_pricing_for_instances with empty list
            app._retry_pricing_for_instances(mock_instance_list, [])

            # Give async tasks time to run
            await asyncio.sleep(0.1)

            # Verify no retry was attempted since all instances have pricing
            assert not mock_client_class.called
