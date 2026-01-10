"""Region selector modal for multi-region comparison"""

from typing import List, Optional, Callable
import logging

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Container, VerticalScroll, Horizontal
from textual.widgets import Static, Button, Checkbox, LoadingIndicator

from src.services.async_aws_client import AsyncAWSClient

logger = logging.getLogger("instancepedia")


class RegionSelectorModal(ModalScreen):
    """Modal for selecting regions to compare"""

    DEFAULT_CSS = """
    RegionSelectorModal {
        align: center middle;
    }

    RegionSelectorModal > Container {
        width: 70;
        height: auto;
        max-height: 90%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    RegionSelectorModal #modal-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    RegionSelectorModal #subtitle {
        text-align: center;
        color: $text-muted;
        margin-bottom: 1;
    }

    RegionSelectorModal #content-container {
        height: auto;
        max-height: 60;
    }

    RegionSelectorModal #loading {
        text-align: center;
        margin: 2 0;
    }

    RegionSelectorModal .region-checkbox {
        margin: 0 1;
    }

    RegionSelectorModal #button-container {
        height: auto;
        align: center middle;
        margin-top: 1;
    }

    RegionSelectorModal Button {
        margin: 0 1;
    }

    RegionSelectorModal #help-text {
        text-align: center;
        margin-top: 1;
        color: $text-muted;
    }

    RegionSelectorModal #error-message {
        text-align: center;
        margin: 1 0;
        color: $error;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("q", "cancel", "Cancel"),
    ]

    def __init__(
        self,
        instance_type: str,
        current_region: str,
        profile: Optional[str] = None,
        on_compare: Optional[Callable[[List[str]], None]] = None
    ):
        """
        Initialize region selector modal

        Args:
            instance_type: Instance type being compared
            current_region: Current region (will be pre-selected)
            profile: AWS profile name
            on_compare: Callback function when compare is clicked with selected regions
        """
        super().__init__()
        self.instance_type = instance_type
        self.current_region = current_region
        self.profile = profile
        self.on_compare = on_compare
        self.regions: List[str] = []
        self.checkboxes: List[Checkbox] = []

    def compose(self) -> ComposeResult:
        """Compose the modal UI"""
        with Container():
            yield Static("🌍 Select Regions to Compare", id="modal-title")
            yield Static(
                f"Comparing pricing for {self.instance_type}",
                id="subtitle"
            )

            with VerticalScroll(id="content-container"):
                yield LoadingIndicator(id="loading")

            with Horizontal(id="button-container"):
                yield Button("Compare", variant="primary", id="compare-button")
                yield Button("Cancel", variant="default", id="cancel-button")

            yield Static(
                "Space: Toggle | Enter: Compare | Esc: Cancel",
                id="help-text"
            )

    async def on_mount(self) -> None:
        """Fetch available regions and populate checkboxes"""
        await self._fetch_regions()

    async def _fetch_regions(self) -> None:
        """Fetch list of available AWS regions"""
        try:
            # Get content container
            content = self.query_one("#content-container", VerticalScroll)
            loading = self.query_one("#loading", LoadingIndicator)

            # Fetch regions
            logger.debug("Fetching available AWS regions")
            # Use current region for client initialization (any region works for listing regions)
            client = AsyncAWSClient(region=self.current_region, profile=self.profile)
            self.regions = await client.get_regions()

            # Remove loading indicator
            loading.remove()

            # Create checkboxes for each region
            # Common regions first, then alphabetically
            common_regions = [
                "us-east-1",
                "us-west-2",
                "eu-west-1",
                "ap-southeast-1",
            ]

            # Separate common and other regions
            common = [r for r in common_regions if r in self.regions]
            other = sorted([r for r in self.regions if r not in common_regions])

            # Add common regions first
            if common:
                content.mount(Static("\n🔥 Popular Regions:", classes="region-section"))
                for region in common:
                    is_current = region == self.current_region
                    checkbox = Checkbox(
                        region,
                        value=is_current,
                        classes="region-checkbox",
                        id=f"region-{region}"
                    )
                    self.checkboxes.append(checkbox)
                    content.mount(checkbox)

            # Add other regions
            if other:
                content.mount(Static("\n📍 All Regions:", classes="region-section"))
                for region in other:
                    is_current = region == self.current_region
                    checkbox = Checkbox(
                        region,
                        value=is_current,
                        classes="region-checkbox",
                        id=f"region-{region}"
                    )
                    self.checkboxes.append(checkbox)
                    content.mount(checkbox)

        except Exception as e:
            logger.exception(f"Error fetching regions: {e}")
            loading.remove()
            content.mount(Static(
                f"❌ Error: {str(e)}\n\nUnable to fetch regions.",
                id="error-message"
            ))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks"""
        if event.button.id == "compare-button":
            self._handle_compare()
        elif event.button.id == "cancel-button":
            self.action_cancel()

    def _handle_compare(self) -> None:
        """Handle compare button click"""
        # Get selected regions
        selected_regions = [
            cb.label.plain.strip() for cb in self.checkboxes if cb.value
        ]

        if len(selected_regions) < 2:
            # Show error - need at least 2 regions
            try:
                error = self.query_one("#error-message", Static)
                error.update("⚠️  Please select at least 2 regions to compare")
            except:
                # Error message widget doesn't exist, create it
                container = self.query_one("#button-container", Horizontal)
                container.mount_after(
                    Static(
                        "⚠️  Please select at least 2 regions to compare",
                        id="error-message"
                    ),
                    container
                )
            return

        # Call the compare callback
        if self.on_compare:
            self.on_compare(selected_regions)

        # Close this modal
        self.dismiss()

    def action_cancel(self) -> None:
        """Close the modal without comparing"""
        self.dismiss()
