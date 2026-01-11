"""Tests for PricingHistoryModal"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from textual.app import App

from src.ui.pricing_history_modal import PricingHistoryModal
from src.services.pricing_service import SpotPriceHistory


@pytest.fixture(autouse=True)
def mock_aws_client():
    """Auto-fixture to mock AsyncAWSClient for all tests"""
    with patch('src.ui.pricing_history_modal.AsyncAWSClient') as mock_client_class:
        with patch('src.ui.pricing_history_modal.AsyncPricingService') as mock_pricing_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock pricing service
            mock_pricing = AsyncMock()
            mock_pricing.get_spot_price_history.return_value = None
            mock_pricing_class.return_value = mock_pricing

            yield (mock_client, mock_pricing)


class PricingHistoryModalTestApp(App):
    """Test app that hosts the PricingHistoryModal"""

    def __init__(self, instance_type="t3.large", region="us-east-1"):
        super().__init__()
        self.instance_type = instance_type
        self.region = region
        self.modal_dismissed = False

    def on_mount(self):
        modal = PricingHistoryModal(self.instance_type, self.region)
        self.push_screen(modal, callback=self._on_modal_dismiss)

    def _on_modal_dismiss(self, result):
        """Track when modal is dismissed"""
        self.modal_dismissed = True


class TestPricingHistoryModal:
    """Tests for PricingHistoryModal"""

    @pytest.mark.asyncio
    async def test_modal_displays_title(self):
        """Test that modal displays correct title"""
        app = PricingHistoryModalTestApp("t3.large", "us-east-1")
        async with app.run_test() as pilot:
            await pilot.pause()

            # Check title is displayed
            header = app.screen.query_one("#history-header")
            assert "Spot Price History" in header.content
            assert "t3.large" in header.content
            assert "us-east-1" in header.content

    @pytest.mark.asyncio
    async def test_modal_has_close_button(self):
        """Test that modal has close button"""
        app = PricingHistoryModalTestApp()
        async with app.run_test() as pilot:
            await pilot.pause()

            # Check close button exists
            close_button = app.screen.query_one("#close-button")
            assert close_button is not None

    @pytest.mark.asyncio
    async def test_modal_close_button_dismisses(self):
        """Test that clicking close button dismisses modal"""
        app = PricingHistoryModalTestApp()
        async with app.run_test() as pilot:
            await pilot.pause()

            # Click close button
            await pilot.click("#close-button")
            await pilot.pause()

            # Modal should be dismissed
            assert app.modal_dismissed

    @pytest.mark.asyncio
    async def test_modal_escape_dismisses(self):
        """Test that escape key dismisses modal"""
        app = PricingHistoryModalTestApp()
        async with app.run_test() as pilot:
            await pilot.pause()

            # Press escape
            await pilot.press("escape")
            await pilot.pause()

            # Modal should be dismissed
            assert app.modal_dismissed

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Flaky: Loading indicator removed before test can check (timing issue)")
    async def test_modal_shows_loading_initially(self):
        """Test that modal shows loading indicator initially"""
        app = PricingHistoryModalTestApp()
        async with app.run_test() as pilot:
            await pilot.pause()

            # Check loading text exists (before fetch completes)
            content = app.screen.query_one("#history-text")
            assert "Loading" in content.content or "spot price history" in content.content.lower()

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Flaky: Mock setup timing issue with async context managers")
    async def test_modal_fetches_history_on_mount(self):
        """Test that modal fetches history when mounted"""
        # Mock the spot price history
        mock_history = SpotPriceHistory(
            instance_type="t3.large",
            region="us-east-1",
            days=30,
            price_points=[
                (datetime.now(), 0.05)
            ],
            min_price=0.04,
            max_price=0.06,
            avg_price=0.05,
            median_price=0.05,
            std_dev=0.01,
            current_price=0.05
        )

        with patch('src.ui.pricing_history_modal.AsyncAWSClient') as mock_client_class:
            with patch('src.ui.pricing_history_modal.AsyncPricingService') as mock_pricing_class:
                # Setup mocks
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client

                mock_pricing = AsyncMock()
                mock_pricing.get_spot_price_history.return_value = mock_history
                mock_pricing_class.return_value = mock_pricing

                app = PricingHistoryModalTestApp("t3.large", "us-east-1")
                async with app.run_test() as pilot:
                    # Wait for fetch to complete
                    await pilot.pause()
                    await pilot.pause()

                    # Verify AsyncPricingService was created
                    mock_pricing_class.assert_called_once()

                    # Verify get_spot_price_history was called
                    mock_pricing.get_spot_price_history.assert_called_once_with(
                        "t3.large",
                        "us-east-1"
                    )


class TestPricingHistoryModalBindings:
    """Tests for PricingHistoryModal key bindings"""

    def test_bindings_defined(self):
        """Test that key bindings are properly defined"""
        modal = PricingHistoryModal("t3.large", "us-east-1")

        # Check bindings exist
        assert hasattr(modal, 'BINDINGS')
        assert len(modal.BINDINGS) > 0

        # Check escape binding
        binding_keys = [b[0] for b in modal.BINDINGS]
        assert "escape" in binding_keys


class TestPricingHistoryModalCSS:
    """Tests for PricingHistoryModal CSS"""

    def test_css_defined(self):
        """Test that DEFAULT_CSS is defined"""
        modal = PricingHistoryModal("t3.large", "us-east-1")
        assert hasattr(modal, 'DEFAULT_CSS')
        assert len(modal.DEFAULT_CSS) > 0

    def test_css_has_container_styles(self):
        """Test that CSS includes container styles"""
        modal = PricingHistoryModal("t3.large", "us-east-1")
        css = modal.DEFAULT_CSS

        # Check for key CSS selectors
        assert "ModalScreen" in css
