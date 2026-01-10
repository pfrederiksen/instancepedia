"""Multi-region pricing comparison modal for TUI"""

from typing import List, Optional, Dict
import logging

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Container, VerticalScroll
from textual.widgets import Static, LoadingIndicator
from rich.table import Table

from src.services.async_aws_client import AsyncAWSClient
from src.services.async_pricing_service import AsyncPricingService
from src.models.instance_type import InstanceType, PricingInfo

logger = logging.getLogger("instancepedia")


class RegionComparisonModal(ModalScreen):
    """Modal for comparing instance pricing across multiple regions"""

    DEFAULT_CSS = """
    RegionComparisonModal {
        align: center middle;
    }

    RegionComparisonModal > Container {
        width: 100;
        height: auto;
        max-height: 90%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    RegionComparisonModal #modal-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    RegionComparisonModal #content-container {
        height: auto;
        max-height: 100%;
    }

    RegionComparisonModal #loading {
        text-align: center;
        margin: 2 0;
    }

    RegionComparisonModal .comparison-table {
        padding: 1;
        margin: 1 0;
    }

    RegionComparisonModal #help-text {
        text-align: center;
        margin-top: 1;
        color: $text-muted;
    }

    RegionComparisonModal #no-data {
        text-align: center;
        margin: 2 0;
        color: $warning;
    }

    RegionComparisonModal .summary {
        padding: 1;
        margin: 1 0;
        background: $success-darken-2;
        text-align: center;
    }
    """

    BINDINGS = [
        ("escape", "dismiss", "Close"),
        ("q", "dismiss", "Close"),
    ]

    def __init__(
        self,
        instance_type: str,
        regions: List[str],
        profile: Optional[str] = None
    ):
        """
        Initialize region comparison modal

        Args:
            instance_type: Instance type to compare (e.g., "t3.large")
            regions: List of AWS region codes to compare
            profile: AWS profile name
        """
        super().__init__()
        self.instance_type = instance_type
        self.regions = regions
        self.profile = profile
        self.region_data: Dict[str, Optional[InstanceType]] = {}

    def compose(self) -> ComposeResult:
        """Compose the modal UI"""
        with Container():
            yield Static(f"🌍 Multi-Region Comparison - {self.instance_type}", id="modal-title")

            with VerticalScroll(id="content-container"):
                yield LoadingIndicator(id="loading")

            yield Static(
                "Esc: Close | Q: Quit",
                id="help-text"
            )

    async def on_mount(self) -> None:
        """Fetch and display region comparison data"""
        await self._fetch_region_data()

    async def _fetch_region_data(self) -> None:
        """Fetch instance data from all selected regions"""
        try:
            # Get content container
            content = self.query_one("#content-container", VerticalScroll)
            loading = self.query_one("#loading", LoadingIndicator)

            # Fetch data for each region
            for region in self.regions:
                try:
                    logger.debug(f"Fetching {self.instance_type} data for {region}")

                    # Create AWS client for this region
                    client = AsyncAWSClient(region=region, profile=self.profile)
                    pricing_service = AsyncPricingService(client)

                    # Fetch instance details
                    instance = await client.get_instance_by_name(
                        self.instance_type,
                        region
                    )

                    if instance:
                        # Fetch pricing
                        await pricing_service.fetch_instance_pricing(
                            instance,
                            region,
                            include_spot=True,
                            include_ri=False  # Skip RI for comparison simplicity
                        )
                        self.region_data[region] = instance
                    else:
                        logger.debug(f"Instance {self.instance_type} not available in {region}")
                        self.region_data[region] = None

                except Exception as e:
                    logger.exception(f"Error fetching data for {region}: {e}")
                    self.region_data[region] = None

            # Remove loading indicator
            loading.remove()

            # Display comparison
            if any(data is not None for data in self.region_data.values()):
                self._display_comparison(content)
            else:
                content.mount(Static(
                    f"❌ Instance type '{self.instance_type}' not available in any selected region",
                    id="no-data"
                ))

        except Exception as e:
            logger.exception(f"Error fetching region comparison data: {e}")
            loading.remove()
            content.mount(Static(
                f"❌ Error: {str(e)}\n\n"
                "Unable to fetch region comparison data.",
                id="no-data"
            ))

    def _display_comparison(self, container: VerticalScroll) -> None:
        """Display region comparison table"""
        # Build comparison data
        comparison_rows = []

        for region in self.regions:
            instance = self.region_data.get(region)

            if instance is None:
                comparison_rows.append({
                    'region': region,
                    'available': False,
                    'on_demand': None,
                    'spot': None,
                    'savings_1yr': None,
                    'savings_3yr': None,
                    'monthly_cost': None,
                })
            else:
                pricing = instance.pricing
                on_demand = pricing.on_demand_price if pricing else None
                spot = pricing.spot_price if pricing else None
                savings_1yr = pricing.savings_plan_1yr_no_upfront if pricing else None
                savings_3yr = pricing.savings_plan_3yr_no_upfront if pricing else None
                monthly_cost = on_demand * 730 if on_demand else None

                comparison_rows.append({
                    'region': region,
                    'available': True,
                    'on_demand': on_demand,
                    'spot': spot,
                    'savings_1yr': savings_1yr,
                    'savings_3yr': savings_3yr,
                    'monthly_cost': monthly_cost,
                })

        # Find cheapest region
        cheapest_region = None
        cheapest_cost = float('inf')
        for row in comparison_rows:
            if row['available'] and row['on_demand'] is not None:
                if row['on_demand'] < cheapest_cost:
                    cheapest_cost = row['on_demand']
                    cheapest_region = row['region']

        # Show summary
        if cheapest_region:
            container.mount(Static(
                f"💡 Cheapest Region: {cheapest_region} at ${cheapest_cost:.4f}/hour",
                classes="summary"
            ))

        # Create comparison table
        table = Table(
            title=f"Pricing Comparison for {self.instance_type}",
            show_header=True,
            header_style="bold magenta",
            show_lines=True,
            expand=True
        )

        # Add columns
        table.add_column("Region", style="cyan", no_wrap=True)
        table.add_column("On-Demand\n($/hour)", justify="right", style="green")
        table.add_column("Spot\n($/hour)", justify="right", style="yellow")
        table.add_column("Savings 1yr\n($/hour)", justify="right", style="blue")
        table.add_column("Savings 3yr\n($/hour)", justify="right", style="blue")
        table.add_column("Monthly Cost\n(730 hrs)", justify="right", style="green")

        # Add rows
        for row in comparison_rows:
            if not row['available']:
                table.add_row(
                    row['region'],
                    "N/A",
                    "N/A",
                    "N/A",
                    "N/A",
                    "N/A",
                    style="dim"
                )
            else:
                # Highlight cheapest region
                style = "bold" if row['region'] == cheapest_region else None

                on_demand_str = f"${row['on_demand']:.4f}" if row['on_demand'] else "N/A"
                spot_str = f"${row['spot']:.4f}" if row['spot'] else "N/A"
                savings_1yr_str = f"${row['savings_1yr']:.4f}" if row['savings_1yr'] else "N/A"
                savings_3yr_str = f"${row['savings_3yr']:.4f}" if row['savings_3yr'] else "N/A"
                monthly_str = f"${row['monthly_cost']:.2f}" if row['monthly_cost'] else "N/A"

                # Add spot savings percentage if available
                if row['spot'] and row['on_demand']:
                    spot_savings_pct = ((row['on_demand'] - row['spot']) / row['on_demand']) * 100
                    spot_str += f"\n({spot_savings_pct:.0f}% off)"

                table.add_row(
                    row['region'],
                    on_demand_str,
                    spot_str,
                    savings_1yr_str,
                    savings_3yr_str,
                    monthly_str,
                    style=style
                )

        # Add insights
        insights_lines = []
        insights_lines.append("\n📊 Insights:")
        insights_lines.append("")

        # Calculate price variance
        available_prices = [r['on_demand'] for r in comparison_rows if r['available'] and r['on_demand']]
        if len(available_prices) > 1:
            min_price = min(available_prices)
            max_price = max(available_prices)
            variance = ((max_price - min_price) / min_price) * 100
            insights_lines.append(f"  • Price variance: {variance:.1f}% (${min_price:.4f} - ${max_price:.4f}/hour)")

            # Cost difference
            monthly_diff = (max_price - min_price) * 730
            annual_diff = (max_price - min_price) * 8760
            insights_lines.append(f"  • Potential savings: ${monthly_diff:.2f}/month, ${annual_diff:.2f}/year")

        # Spot availability
        spot_available = sum(1 for r in comparison_rows if r['available'] and r['spot'])
        if spot_available > 0:
            insights_lines.append(f"  • Spot pricing available in {spot_available}/{len(self.regions)} regions")

        # Render table and insights
        container.mount(Static(table, classes="comparison-table"))
        container.mount(Static("\n".join(insights_lines)))

    def action_dismiss(self) -> None:
        """Close the modal"""
        self.dismiss()
