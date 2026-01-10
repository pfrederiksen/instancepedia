"""Pricing history modal for spot price visualization"""

import logging
from typing import Optional
from textual.app import ComposeResult
from textual.containers import Container, Vertical, ScrollableContainer, Horizontal
from textual.widgets import Static, Button
from textual.screen import ModalScreen
from textual.worker import Worker

from src.services.async_aws_client import AsyncAWSClient
from src.services.async_pricing_service import AsyncPricingService
from src.services.pricing_service import SpotPriceHistory
from src.config.settings import Settings
from src.debug import DebugLog

logger = logging.getLogger("instancepedia")


class PricingHistoryModal(ModalScreen):
    """Modal for spot price history visualization"""

    BINDINGS = [
        ("escape", "dismiss", "Close"),
        ("q", "dismiss", "Close"),
    ]

    CSS = """
    PricingHistoryModal {
        align: center middle;
    }

    #history-container {
        width: 90;
        height: auto;
        max-height: 40;
        background: $panel;
        border: thick $primary;
    }

    #history-header {
        width: 100%;
        content-align: center middle;
        background: $primary;
        color: $text;
        padding: 1;
        text-style: bold;
    }

    #history-content {
        width: 100%;
        height: auto;
        max-height: 30;
    }

    #history-text {
        width: 100%;
        padding: 1 2;
    }

    #button-container {
        width: 100%;
        height: auto;
        align: center middle;
        padding: 1;
    }

    #close-button {
        width: 20;
    }
    """

    def __init__(
        self,
        instance_type: str,
        region: str,
        days: int = 30,
        profile: Optional[str] = None
    ):
        super().__init__()
        DebugLog.log(f"PricingHistoryModal.__init__() for {instance_type} in {region}")
        self.instance_type = instance_type
        self._region = region
        self.days = days
        self.profile = profile
        self.history: Optional[SpotPriceHistory] = None
        self._settings = Settings()
        self._fetch_worker: Optional[Worker] = None

    def compose(self) -> ComposeResult:
        """Compose the modal UI"""
        DebugLog.log("PricingHistoryModal.compose() called")
        with Container(id="history-container"):
            yield Static(
                f"Spot Price History: {self.instance_type} ({self._region})",
                id="history-header"
            )
            with ScrollableContainer(id="history-content"):
                yield Static("Loading spot price history...", id="history-text")
            with Horizontal(id="button-container"):
                yield Button("Close", id="close-button", variant="primary")

    def on_mount(self) -> None:
        """Fetch pricing history when mounted"""
        DebugLog.log("PricingHistoryModal.on_mount() called")
        self._fetch_worker = self.run_worker(self._fetch_history, exclusive=True)

    def on_unmount(self) -> None:
        """Cleanup when unmounted"""
        DebugLog.log("PricingHistoryModal.on_unmount() called")
        if self._fetch_worker:
            self._fetch_worker.cancel()

    async def _fetch_history(self) -> None:
        """Fetch spot price history from AWS"""
        DebugLog.log("PricingHistoryModal._fetch_history() started")
        try:
            async with AsyncAWSClient(
                self._region,
                self.profile,
                connect_timeout=self._settings.aws_connect_timeout,
                read_timeout=self._settings.aws_read_timeout,
                pricing_timeout=self._settings.pricing_read_timeout,
                max_pool_connections=self._settings.max_pool_connections
            ) as async_client:
                pricing_service = AsyncPricingService(
                    async_client,
                    settings=self._settings
                )

                # Fetch spot price history
                self.history = await pricing_service.get_spot_price_history(
                    self.instance_type,
                    self._region,
                    self.days
                )

                DebugLog.log(f"Fetched spot history: {len(self.history.price_points) if self.history else 0} points")

                # Update UI on main thread
                def update_ui():
                    if self.history:
                        content = self._format_history(self.history)
                    else:
                        content = self._format_no_history()

                    try:
                        text_widget = self.query_one("#history-text", Static)
                        text_widget.update(content)
                    except Exception as e:
                        logger.debug(f"Failed to update history text: {e}")

                self.call_later(update_ui)

        except Exception as e:
            logger.error(f"Failed to fetch spot price history: {e}", exc_info=True)
            DebugLog.log(f"ERROR in _fetch_history: {e}")

            def show_error():
                try:
                    text_widget = self.query_one("#history-text", Static)
                    text_widget.update(f"Error loading spot price history:\n{str(e)}")
                except Exception as inner_e:
                    logger.debug(f"Failed to show error: {inner_e}")

            self.call_later(show_error)

    def _format_history(self, history: SpotPriceHistory) -> str:
        """Format spot price history as text"""
        lines = []
        lines.append(f"Period: Last {history.days} days ({len(history.price_points)} data points)")
        lines.append("")
        lines.append("Price Statistics:")
        lines.append("─" * 70)

        # Statistics
        if history.current_price:
            lines.append(f"  Current Price:   ${history.current_price:.4f}/hr")
        else:
            lines.append("  Current Price:   N/A")

        if history.min_price:
            lines.append(f"  Minimum Price:   ${history.min_price:.4f}/hr")
        else:
            lines.append("  Minimum Price:   N/A")

        if history.max_price:
            lines.append(f"  Maximum Price:   ${history.max_price:.4f}/hr")
        else:
            lines.append("  Maximum Price:   N/A")

        if history.avg_price:
            lines.append(f"  Average Price:   ${history.avg_price:.4f}/hr")
        else:
            lines.append("  Average Price:   N/A")

        if history.median_price:
            lines.append(f"  Median Price:    ${history.median_price:.4f}/hr")
        else:
            lines.append("  Median Price:    N/A")

        lines.append("")

        # Price range and volatility
        if history.price_range is not None:
            lines.append(f"  Price Range:     ${history.price_range:.4f}/hr ({history.min_price:.4f} - {history.max_price:.4f})")

        if history.volatility_percentage is not None:
            lines.append(f"  Volatility:      {history.volatility_percentage:.1f}% (std dev / avg)")

            # Interpret volatility
            if history.volatility_percentage < 10:
                volatility_label = "Very Stable ✓"
            elif history.volatility_percentage < 20:
                volatility_label = "Stable"
            elif history.volatility_percentage < 30:
                volatility_label = "Moderate"
            elif history.volatility_percentage < 50:
                volatility_label = "Volatile ⚠"
            else:
                volatility_label = "Highly Volatile ⚠⚠"
            lines.append(f"  Stability:       {volatility_label}")

        lines.append("")

        # Savings potential
        if history.savings_vs_current is not None and history.savings_vs_current > 0:
            lines.append("Potential Savings:")
            lines.append("─" * 70)
            lines.append(f"  If you had bought at minimum price instead of current:")
            lines.append(f"  Savings: {history.savings_vs_current:.1f}% cheaper")
            lines.append("")

        # Price trend visualization
        lines.append("Price Trend (last 30 data points):")
        lines.append("─" * 70)

        # Show last 30 points or all if fewer
        recent_points = history.price_points[-30:] if len(history.price_points) > 30 else history.price_points

        if not recent_points:
            lines.append("  No price data available")
        else:
            for ts, price in recent_points:
                # Create simple bar chart
                if history.min_price and history.max_price and history.max_price > history.min_price:
                    normalized = (price - history.min_price) / (history.max_price - history.min_price)
                    bar_length = int(normalized * 40)
                    bar = "█" * bar_length
                    lines.append(f"  {ts.strftime('%Y-%m-%d %H:%M')}  ${price:.4f}  {bar}")
                else:
                    lines.append(f"  {ts.strftime('%Y-%m-%d %H:%M')}  ${price:.4f}")

        return "\n".join(lines)

    def _format_no_history(self) -> str:
        """Format message when no history is available"""
        lines = []
        lines.append(f"No spot price history available for {self.instance_type} in {self._region}")
        lines.append("")
        lines.append("Possible reasons:")
        lines.append("  • No spot capacity in this region for this instance type")
        lines.append("  • Instance type not offered as spot in this region")
        lines.append("  • Metal and Mac instances do not support spot pricing")
        lines.append("")
        lines.append("Try:")
        lines.append("  • Check a different region")
        lines.append("  • Consider Savings Plans or Reserved Instances instead")
        return "\n".join(lines)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press"""
        if event.button.id == "close-button":
            self.dismiss(None)

    def action_dismiss(self) -> None:
        """Dismiss the modal"""
        self.dismiss(None)
