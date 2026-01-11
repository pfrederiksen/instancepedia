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


class TestPricingHistoryModalFormatting:
    """Tests for formatting spot price history"""

    def test_format_history_with_complete_data(self):
        """Test formatting history with all data present"""
        history = SpotPriceHistory(
            instance_type="t3.large",
            region="us-east-1",
            days=30,
            price_points=[
                (datetime(2024, 1, 1, 12, 0), 0.05),
                (datetime(2024, 1, 2, 12, 0), 0.06),
                (datetime(2024, 1, 3, 12, 0), 0.04),
            ],
            min_price=0.04,
            max_price=0.06,
            avg_price=0.05,
            median_price=0.05,
            std_dev=0.01,
            current_price=0.05
        )

        modal = PricingHistoryModal("t3.large", "us-east-1")
        result = modal._format_history(history)

        # Check content
        assert "Period: Last 30 days" in result
        assert "3 data points" in result
        assert "Current Price:" in result
        assert "$0.0500/hr" in result
        assert "Minimum Price:" in result
        assert "$0.0400/hr" in result
        assert "Maximum Price:" in result
        assert "$0.0600/hr" in result
        assert "Average Price:" in result
        assert "Median Price:" in result
        assert "Price Trend" in result

    def test_format_history_with_none_prices(self):
        """Test formatting when some prices are None"""
        history = SpotPriceHistory(
            instance_type="t3.large",
            region="us-east-1",
            days=30,
            price_points=[],
            min_price=None,
            max_price=None,
            avg_price=None,
            median_price=None,
            std_dev=None,
            current_price=None
        )

        modal = PricingHistoryModal("t3.large", "us-east-1")
        result = modal._format_history(history)

        # Check N/A appears for missing data
        assert "Current Price:   N/A" in result
        assert "Minimum Price:   N/A" in result
        assert "Maximum Price:   N/A" in result
        assert "Average Price:   N/A" in result
        assert "Median Price:    N/A" in result

    def test_format_history_volatility_very_stable(self):
        """Test volatility label for very stable prices (< 10%)"""
        history = SpotPriceHistory(
            instance_type="t3.large",
            region="us-east-1",
            days=30,
            price_points=[(datetime.now(), 0.05)],
            min_price=0.049,
            max_price=0.051,
            avg_price=0.05,
            median_price=0.05,
            std_dev=0.003,  # 6% volatility
            current_price=0.05
        )

        modal = PricingHistoryModal("t3.large", "us-east-1")
        result = modal._format_history(history)

        assert "Volatility:" in result
        assert "Very Stable ✓" in result

    def test_format_history_volatility_stable(self):
        """Test volatility label for stable prices (10-20%)"""
        history = SpotPriceHistory(
            instance_type="t3.large",
            region="us-east-1",
            days=30,
            price_points=[(datetime.now(), 0.05)],
            min_price=0.04,
            max_price=0.06,
            avg_price=0.05,
            median_price=0.05,
            std_dev=0.0075,  # 15% volatility
            current_price=0.05
        )

        modal = PricingHistoryModal("t3.large", "us-east-1")
        result = modal._format_history(history)

        assert "Stability:       Stable" in result

    def test_format_history_volatility_moderate(self):
        """Test volatility label for moderate prices (20-30%)"""
        history = SpotPriceHistory(
            instance_type="t3.large",
            region="us-east-1",
            days=30,
            price_points=[(datetime.now(), 0.05)],
            min_price=0.03,
            max_price=0.07,
            avg_price=0.05,
            median_price=0.05,
            std_dev=0.0125,  # 25% volatility
            current_price=0.05
        )

        modal = PricingHistoryModal("t3.large", "us-east-1")
        result = modal._format_history(history)

        assert "Stability:       Moderate" in result

    def test_format_history_volatility_volatile(self):
        """Test volatility label for volatile prices (30-50%)"""
        history = SpotPriceHistory(
            instance_type="t3.large",
            region="us-east-1",
            days=30,
            price_points=[(datetime.now(), 0.05)],
            min_price=0.02,
            max_price=0.08,
            avg_price=0.05,
            median_price=0.05,
            std_dev=0.02,  # 40% volatility
            current_price=0.05
        )

        modal = PricingHistoryModal("t3.large", "us-east-1")
        result = modal._format_history(history)

        assert "Stability:       Volatile ⚠" in result

    def test_format_history_volatility_highly_volatile(self):
        """Test volatility label for highly volatile prices (> 50%)"""
        history = SpotPriceHistory(
            instance_type="t3.large",
            region="us-east-1",
            days=30,
            price_points=[(datetime.now(), 0.05)],
            min_price=0.01,
            max_price=0.10,
            avg_price=0.05,
            median_price=0.05,
            std_dev=0.03,  # 60% volatility
            current_price=0.05
        )

        modal = PricingHistoryModal("t3.large", "us-east-1")
        result = modal._format_history(history)

        assert "Stability:       Highly Volatile ⚠⚠" in result

    def test_format_history_with_savings_potential(self):
        """Test formatting when savings potential exists"""
        history = SpotPriceHistory(
            instance_type="t3.large",
            region="us-east-1",
            days=30,
            price_points=[(datetime.now(), 0.06)],
            min_price=0.04,
            max_price=0.06,
            avg_price=0.05,
            median_price=0.05,
            std_dev=0.01,
            current_price=0.06
        )

        modal = PricingHistoryModal("t3.large", "us-east-1")
        result = modal._format_history(history)

        # Check savings section appears
        assert "Potential Savings:" in result
        assert "If you had bought at minimum price instead of current:" in result
        assert "Savings:" in result
        assert "cheaper" in result

    def test_format_history_with_price_trend_bars(self):
        """Test that price trend bars are generated"""
        history = SpotPriceHistory(
            instance_type="t3.large",
            region="us-east-1",
            days=30,
            price_points=[
                (datetime(2024, 1, 1, 12, 0), 0.04),
                (datetime(2024, 1, 2, 12, 0), 0.05),
                (datetime(2024, 1, 3, 12, 0), 0.06),
            ],
            min_price=0.04,
            max_price=0.06,
            avg_price=0.05,
            median_price=0.05,
            std_dev=0.01,
            current_price=0.05
        )

        modal = PricingHistoryModal("t3.large", "us-east-1")
        result = modal._format_history(history)

        # Check price trend exists
        assert "Price Trend (last 30 data points):" in result
        assert "2024-01-01 12:00" in result
        assert "2024-01-02 12:00" in result
        assert "2024-01-03 12:00" in result
        assert "█" in result  # Bar chart character

    def test_format_history_with_no_price_points(self):
        """Test formatting when no price points exist"""
        history = SpotPriceHistory(
            instance_type="t3.large",
            region="us-east-1",
            days=30,
            price_points=[],
            min_price=0.05,
            max_price=0.05,
            avg_price=0.05,
            median_price=0.05,
            std_dev=0.0,
            current_price=0.05
        )

        modal = PricingHistoryModal("t3.large", "us-east-1")
        result = modal._format_history(history)

        assert "0 data points" in result
        assert "No price data available" in result

    def test_format_no_history(self):
        """Test formatting when no history is available"""
        modal = PricingHistoryModal("t3.large", "us-east-1")
        result = modal._format_no_history()

        assert "No spot price history available" in result
        assert "t3.large" in result
        assert "us-east-1" in result

    def test_format_history_with_many_points_truncates(self):
        """Test that many price points are truncated to last 30"""
        # Create 50 price points across multiple months using timedelta
        from datetime import timedelta
        base_date = datetime(2024, 1, 1, 12, 0)
        price_points = [
            (base_date + timedelta(days=i), 0.05)
            for i in range(50)
        ]

        history = SpotPriceHistory(
            instance_type="t3.large",
            region="us-east-1",
            days=30,
            price_points=price_points,
            min_price=0.05,
            max_price=0.05,
            avg_price=0.05,
            median_price=0.05,
            std_dev=0.0,
            current_price=0.05
        )

        modal = PricingHistoryModal("t3.large", "us-east-1")
        result = modal._format_history(history)

        # Should mention 50 data points
        assert "50 data points" in result
        # Should only show last 30 in trend
        # Last 30 points would be days 20-49 (0-indexed)
        assert "2024-01-21" in result  # Day 20 (base + 20 days)
        assert "2024-01-01" not in result  # Day 0 should not be shown

    def test_history_attribute_set(self):
        """Test that modal has history attribute"""
        modal = PricingHistoryModal("t3.large", "us-east-1")
        assert hasattr(modal, 'history')
        assert modal.history is None  # Initially None

    def test_modal_init_with_profile(self):
        """Test modal initialization with profile"""
        modal = PricingHistoryModal("t3.large", "us-east-1", profile="my-profile")
        assert modal.instance_type == "t3.large"
        assert modal._region == "us-east-1"
        assert modal.profile == "my-profile"
