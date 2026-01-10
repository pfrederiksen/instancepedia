"""Cost optimization recommendations modal for TUI"""

from typing import Optional
import logging

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Container, VerticalScroll
from textual.widgets import Static, LoadingIndicator

from src.services.async_aws_client import AsyncAWSClient
from src.services.async_pricing_service import AsyncPricingService
from src.services.optimization_service import OptimizationService, OptimizationReport
from src.models.instance_type import InstanceType

logger = logging.getLogger("instancepedia")


class OptimizationModal(ModalScreen):
    """Modal for displaying cost optimization recommendations"""

    DEFAULT_CSS = """
    OptimizationModal {
        align: center middle;
    }

    OptimizationModal > Container {
        width: 90;
        height: auto;
        max-height: 90%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    OptimizationModal #modal-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    OptimizationModal #content-container {
        height: auto;
        max-height: 100%;
    }

    OptimizationModal #loading {
        text-align: center;
        margin: 2 0;
    }

    OptimizationModal .recommendation {
        padding: 1;
        margin: 1 0;
        border: solid $primary;
        background: $panel;
    }

    OptimizationModal .rec-header {
        text-style: bold;
        margin-bottom: 1;
    }

    OptimizationModal .rec-details {
        margin-left: 2;
    }

    OptimizationModal .savings {
        color: $success;
        text-style: bold;
    }

    OptimizationModal .cost-line {
        margin: 0;
    }

    OptimizationModal .considerations {
        margin-top: 1;
        padding-top: 1;
        border-top: solid $primary-lighten-2;
    }

    OptimizationModal .consideration-item {
        margin-left: 2;
        color: $text-muted;
    }

    OptimizationModal #help-text {
        text-align: center;
        margin-top: 1;
        color: $text-muted;
    }

    OptimizationModal #no-recommendations {
        text-align: center;
        margin: 2 0;
        color: $warning;
    }

    OptimizationModal .summary {
        padding: 1;
        margin: 1 0;
        background: $success-darken-2;
        text-align: center;
        text-style: bold;
    }
    """

    BINDINGS = [
        ("escape", "dismiss", "Close"),
        ("q", "dismiss", "Close"),
    ]

    def __init__(
        self,
        instance_type: str,
        region: str,
        usage_pattern: str = "standard",
        profile: Optional[str] = None
    ):
        """
        Initialize optimization modal

        Args:
            instance_type: Instance type to analyze (e.g., "t3.large")
            region: AWS region code
            usage_pattern: Usage pattern (standard, burst, continuous)
            profile: AWS profile name
        """
        super().__init__()
        self.instance_type = instance_type
        self.region = region
        self.usage_pattern = usage_pattern
        self.profile = profile
        self.report: Optional[OptimizationReport] = None

    def compose(self) -> ComposeResult:
        """Compose the modal UI"""
        with Container():
            yield Static(f"💰 Cost Optimization - {self.instance_type}", id="modal-title")

            with VerticalScroll(id="content-container"):
                yield LoadingIndicator(id="loading")

            yield Static(
                "Esc: Close | Q: Quit",
                id="help-text"
            )

    async def on_mount(self) -> None:
        """Fetch and display optimization recommendations"""
        await self._fetch_recommendations()

    async def _fetch_recommendations(self) -> None:
        """Fetch optimization recommendations from AWS"""
        try:
            # Get content container
            content = self.query_one("#content-container", VerticalScroll)
            loading = self.query_one("#loading", LoadingIndicator)

            # Create AWS client and pricing service
            async with AsyncAWSClient(region=self.region, profile=self.profile) as client:
                pricing_service = AsyncPricingService(client)

                # Get EC2 client and fetch instance details
                async with client.get_ec2_client() as ec2_client:
                    logger.debug(f"Fetching {self.instance_type} from {self.region}")

                    response = await ec2_client.describe_instance_types(
                        InstanceTypes=[self.instance_type]
                    )

                    instance_data = response.get("InstanceTypes", [])

                    if not instance_data:
                        loading.remove()
                        content.mount(Static(
                            f"❌ Instance type '{self.instance_type}' not found in {self.region}",
                            id="no-recommendations"
                        ))
                        return

                    # Parse instance from AWS response
                    instance = InstanceType.from_aws_response(instance_data[0])

                    # Fetch pricing for current instance including savings plans and spot
                    on_demand = await pricing_service.get_on_demand_price(instance.instance_type, self.region)
                    spot_price = await pricing_service.get_spot_price(instance.instance_type, self.region)
                    savings_1yr = await pricing_service.get_savings_plan_price(instance.instance_type, self.region, "1yr")
                    savings_3yr = await pricing_service.get_savings_plan_price(instance.instance_type, self.region, "3yr")

                    # Create pricing info with all pricing types
                    instance.pricing = PricingInfo(
                        on_demand_price=on_demand,
                        spot_price=spot_price,
                        savings_plan_1yr_no_upfront=savings_1yr,
                        savings_plan_3yr_no_upfront=savings_3yr
                    )

                    # Fetch all instances for comparison
                    logger.debug(f"Fetching all instances in {self.region} for comparison")
                    all_instances_response = await ec2_client.describe_instance_types()
                    all_instances = [
                        InstanceType.from_aws_response(inst_data)
                        for inst_data in all_instances_response.get("InstanceTypes", [])
                    ]

                    # Fetch on-demand pricing for all alternative instances in batch
                    logger.debug(f"Fetching on-demand pricing for {len(all_instances)} alternatives")
                    instance_type_names = [inst.instance_type for inst in all_instances if inst.instance_type != self.instance_type]
                    pricing_results = await pricing_service.get_on_demand_prices_batch(
                        instance_type_names,
                        self.region,
                        concurrency=20  # Higher concurrency for faster fetching
                    )

                    # Apply pricing to instances
                    for inst in all_instances:
                        if inst.instance_type in pricing_results:
                            price = pricing_results[inst.instance_type]
                            if price is not None:
                                inst.pricing = PricingInfo(on_demand_price=price)

                    # Create optimization service and analyze
                    logger.debug(f"Analyzing {self.instance_type} with usage pattern: {self.usage_pattern}")
                    optimizer = OptimizationService(all_instances, self.region)
                    self.report = optimizer.analyze_instance(instance, self.usage_pattern)

                    # Remove loading indicator
                    loading.remove()

                    # Display recommendations
                    if not self.report.recommendations:
                        content.mount(Static(
                            "✅ No significant optimization opportunities found.\n"
                            "This instance is already well-optimized for your usage pattern.",
                            id="no-recommendations"
                        ))
                    else:
                        self._display_recommendations(content)

        except Exception as e:
            logger.exception(f"Error fetching optimization recommendations: {e}")
            loading.remove()
            content.mount(Static(
                f"❌ Error: {str(e)}\n\n"
                "Unable to fetch optimization recommendations.",
                id="no-recommendations"
            ))

    def _display_recommendations(self, container: VerticalScroll) -> None:
        """Display optimization recommendations in the container"""
        if not self.report:
            return

        # Show total potential savings summary
        if self.report.total_potential_savings > 0:
            total_savings = self.report.total_potential_savings
            current_monthly = self.report.current_pricing.on_demand_price * 730
            savings_pct = (total_savings / current_monthly) * 100 if current_monthly > 0 else 0

            container.mount(Static(
                f"💡 Total Potential Savings: ${total_savings:.2f}/month ({savings_pct:.1f}%)",
                classes="summary"
            ))

        # Display each recommendation
        for i, rec in enumerate(self.report.recommendations, 1):
            # Choose emoji based on recommendation type
            emoji_map = {
                "spot": "⚡",
                "downsize": "📉",
                "savings_plan_1yr": "📋",
                "savings_plan_3yr": "📋",
                "ri_1yr": "🔒",
                "ri_3yr": "🔒",
            }
            emoji = emoji_map.get(rec.recommendation_type, "💡")

            # Build recommendation type label
            type_labels = {
                "spot": "Spot Instances",
                "downsize": "Right-Sizing",
                "savings_plan_1yr": "1-Year Savings Plan",
                "savings_plan_3yr": "3-Year Savings Plan",
                "ri_1yr": "1-Year Reserved Instance",
                "ri_3yr": "3-Year Reserved Instance",
            }
            type_label = type_labels.get(rec.recommendation_type, rec.recommendation_type)

            # Build header text
            if rec.recommended_instance:
                header = f"{emoji} {type_label}: {rec.current_instance} → {rec.recommended_instance}"
            else:
                header = f"{emoji} {type_label}"

            # Build details
            details_lines = [
                f"💰 Current Cost:  ${rec.current_cost_monthly:,.2f}/month",
                f"💚 Optimized:     ${rec.optimized_cost_monthly:,.2f}/month",
                f"💵 Savings:       ${rec.savings_monthly:,.2f}/month ({rec.savings_percentage:.1f}%)",
                "",
                f"📝 {rec.reason}",
            ]

            # Add considerations
            if rec.considerations:
                details_lines.append("")
                details_lines.append("⚠️  Considerations:")
                for consideration in rec.considerations:
                    details_lines.append(f"  • {consideration}")

            # Create recommendation widget
            rec_content = "\n".join([
                header,
                "",
                "\n".join(details_lines)
            ])

            container.mount(Static(rec_content, classes="recommendation"))

    def action_dismiss(self) -> None:
        """Close the modal"""
        self.dismiss()
