"""Instance comparison screen"""

from textual.app import ComposeResult
from textual.containers import Container, Vertical, ScrollableContainer, Horizontal
from textual.widgets import Static
from textual.screen import Screen

from src.models.instance_type import InstanceType
from src.services.free_tier_service import FreeTierService
from src.debug import DebugLog, DebugPane


class InstanceComparison(Screen):
    """Screen for comparing two instance types side-by-side"""

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("escape", "back", "Back"),
    ]

    def __init__(self, instance1: InstanceType, instance2: InstanceType, region: str):
        super().__init__()
        DebugLog.log(f"InstanceComparison.__init__() called for: {instance1.instance_type} vs {instance2.instance_type}")
        self.instance1 = instance1
        self.instance2 = instance2
        self._region = region
        self.free_tier_service = FreeTierService()

    def compose(self) -> ComposeResult:
        DebugLog.log("InstanceComparison.compose() called")
        with Vertical():
            with Container(id="comparison-container"):
                yield Static(f"Comparing: {self.instance1.instance_type} vs {self.instance2.instance_type}", id="header")
                with ScrollableContainer(id="comparison-content"):
                    yield Static("Loading...", id="comparison-text")
                yield Static(
                    "Esc: Back | Q: Quit",
                    id="help-text"
                )
            if DebugLog.is_enabled():
                yield DebugPane()
        DebugLog.log("InstanceComparison.compose() completed")

    def on_mount(self) -> None:
        """Render comparison content when screen is mounted"""
        DebugLog.log("InstanceComparison.on_mount() called")
        self.refresh()
        self.set_timer(0.2, self._render_comparison)

    def _render_comparison(self) -> None:
        """Render the comparison table"""
        DebugLog.log("InstanceComparison._render_comparison() called")
        try:
            inst1 = self.instance1
            inst2 = self.instance2

            is_free_tier1 = self.free_tier_service.is_eligible(inst1.instance_type)
            is_free_tier2 = self.free_tier_service.is_eligible(inst2.instance_type)

            lines = []
            lines.append(f"Region: {self._region}")
            lines.append("")
            lines.append("━" * 80)
            lines.append("")

            # Comparison table header
            lines.append(f"{'Property':<30} {inst1.instance_type:<25} {inst2.instance_type:<25}")
            lines.append("─" * 80)

            # Instance Type
            lines.append(f"{'Instance Type':<30} {inst1.instance_type:<25} {inst2.instance_type:<25}")

            # vCPU
            lines.append(f"{'vCPU':<30} {inst1.vcpu_info.default_vcpus:<25} {inst2.vcpu_info.default_vcpus:<25}")

            # Memory
            mem1 = f"{inst1.memory_info.size_in_gb:.2f} GB"
            mem2 = f"{inst2.memory_info.size_in_gb:.2f} GB"
            lines.append(f"{'Memory':<30} {mem1:<25} {mem2:<25}")

            # Network
            lines.append(f"{'Network Performance':<30} {inst1.network_info.network_performance:<25} {inst2.network_info.network_performance:<25}")

            # GPU
            gpu1 = str(inst1.gpu_info.total_gpu_count) if inst1.gpu_info else "0"
            gpu2 = str(inst2.gpu_info.total_gpu_count) if inst2.gpu_info else "0"
            lines.append(f"{'GPUs':<30} {gpu1:<25} {gpu2:<25}")

            # Storage
            storage1 = f"{inst1.instance_storage_info.total_size_in_gb} GB" if inst1.instance_storage_info and inst1.instance_storage_info.total_size_in_gb else "EBS Only"
            storage2 = f"{inst2.instance_storage_info.total_size_in_gb} GB" if inst2.instance_storage_info and inst2.instance_storage_info.total_size_in_gb else "EBS Only"
            lines.append(f"{'Instance Storage':<30} {storage1:<25} {storage2:<25}")

            # EBS Optimized
            ebs1 = inst1.ebs_info.ebs_optimized_support.title()
            ebs2 = inst2.ebs_info.ebs_optimized_support.title()
            lines.append(f"{'EBS Optimized':<30} {ebs1:<25} {ebs2:<25}")

            # Architecture
            arch1 = ", ".join(inst1.processor_info.supported_architectures)
            arch2 = ", ".join(inst2.processor_info.supported_architectures)
            lines.append(f"{'Architectures':<30} {arch1:<25} {arch2:<25}")

            # Current Generation
            gen1 = "Yes" if inst1.current_generation else "No"
            gen2 = "Yes" if inst2.current_generation else "No"
            lines.append(f"{'Current Generation':<30} {gen1:<25} {gen2:<25}")

            # Burstable
            burst1 = "Yes" if inst1.burstable_performance_supported else "No"
            burst2 = "Yes" if inst2.burstable_performance_supported else "No"
            lines.append(f"{'Burstable Performance':<30} {burst1:<25} {burst2:<25}")

            lines.append("")
            lines.append("━" * 80)
            lines.append("")
            lines.append("Pricing")
            lines.append("─" * 80)

            # On-Demand Pricing
            if inst1.pricing and inst1.pricing.on_demand_price is not None:
                price1 = f"${inst1.pricing.on_demand_price:.4f}/hr"
                monthly1 = f"${inst1.pricing.calculate_monthly_cost():.2f}/mo"
            else:
                price1 = "N/A"
                monthly1 = "N/A"

            if inst2.pricing and inst2.pricing.on_demand_price is not None:
                price2 = f"${inst2.pricing.on_demand_price:.4f}/hr"
                monthly2 = f"${inst2.pricing.calculate_monthly_cost():.2f}/mo"
            else:
                price2 = "N/A"
                monthly2 = "N/A"

            lines.append(f"{'On-Demand (hourly)':<30} {price1:<25} {price2:<25}")
            lines.append(f"{'Monthly Cost (730h)':<30} {monthly1:<25} {monthly2:<25}")

            # Spot Pricing
            if inst1.pricing and inst1.pricing.spot_price is not None:
                spot1 = f"${inst1.pricing.spot_price:.4f}/hr"
            else:
                spot1 = "N/A"

            if inst2.pricing and inst2.pricing.spot_price is not None:
                spot2 = f"${inst2.pricing.spot_price:.4f}/hr"
            else:
                spot2 = "N/A"

            lines.append(f"{'Spot Price (current)':<30} {spot1:<25} {spot2:<25}")

            # Cost per vCPU
            if inst1.pricing and inst1.pricing.on_demand_price:
                cost_vcpu1 = f"${inst1.pricing.on_demand_price / inst1.vcpu_info.default_vcpus:.6f}/hr"
            else:
                cost_vcpu1 = "N/A"

            if inst2.pricing and inst2.pricing.on_demand_price:
                cost_vcpu2 = f"${inst2.pricing.on_demand_price / inst2.vcpu_info.default_vcpus:.6f}/hr"
            else:
                cost_vcpu2 = "N/A"

            lines.append(f"{'Cost per vCPU':<30} {cost_vcpu1:<25} {cost_vcpu2:<25}")

            # Cost per GB RAM
            if inst1.pricing and inst1.pricing.on_demand_price:
                cost_ram1 = f"${inst1.pricing.on_demand_price / inst1.memory_info.size_in_gb:.6f}/hr"
            else:
                cost_ram1 = "N/A"

            if inst2.pricing and inst2.pricing.on_demand_price:
                cost_ram2 = f"${inst2.pricing.on_demand_price / inst2.memory_info.size_in_gb:.6f}/hr"
            else:
                cost_ram2 = "N/A"

            lines.append(f"{'Cost per GB RAM':<30} {cost_ram1:<25} {cost_ram2:<25}")

            # Free Tier
            ft1 = "Yes 🆓" if is_free_tier1 else "No"
            ft2 = "Yes 🆓" if is_free_tier2 else "No"
            lines.append(f"{'Free Tier Eligible':<30} {ft1:<25} {ft2:<25}")

            comparison_text = self.query_one("#comparison-text", Static)
            comparison_text.update("\n".join(lines))
            DebugLog.log("InstanceComparison content rendered successfully")
            self.refresh()
        except Exception as e:
            DebugLog.log(f"ERROR rendering comparison: {e}")
            import traceback
            import logging
            DebugLog.log(f"Traceback: {traceback.format_exc()}")
            logger = logging.getLogger("instancepedia")
            logger.error(f"Failed to render instance comparison: {e}", exc_info=True)
            try:
                comparison_text = self.query_one("#comparison-text", Static)
                comparison_text.update(f"Error loading comparison: {str(e)}")
            except Exception as inner_e:
                logger.debug(f"Failed to update error message: {inner_e}")

    def action_back(self) -> None:
        """Go back to instance list"""
        self.dismiss(None)

    def action_quit(self) -> None:
        """Quit application"""
        self.app.exit()
