"""Instance type detail screen"""

from textual.app import ComposeResult
from textual.containers import Container, Vertical, ScrollableContainer
from textual.widgets import Static, Label
from textual.screen import Screen
from textual import events
from threading import Thread

from src.models.instance_type import InstanceType
from src.services.free_tier_service import FreeTierService
from src.services.aws_client import AWSClient
from src.services.pricing_service import PricingService
from src.debug import DebugLog, DebugPane
from textual.containers import Vertical


class InstanceDetail(Screen):
    """Screen for displaying instance type details"""

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("escape", "back", "Back"),
    ]

    def __init__(self, instance_type: InstanceType):
        super().__init__()
        DebugLog.log(f"InstanceDetail.__init__() called for: {instance_type.instance_type}")
        self.instance_type = instance_type
        self.free_tier_service = FreeTierService()

    def compose(self) -> ComposeResult:
        DebugLog.log("InstanceDetail.compose() called")
        with Vertical():
            with Container(id="detail-container"):
                yield Static("Instance Type Details", id="header")
                with ScrollableContainer(id="detail-content"):
                    yield Static("Loading...", id="detail-text")  # Show something immediately
                yield Static(
                    "Esc: Back | Q: Quit",
                    id="help-text"
                )
            if DebugLog.is_enabled():
                yield DebugPane()
        DebugLog.log("InstanceDetail.compose() completed")

    def on_mount(self) -> None:
        """Render detail content when screen is mounted"""
        DebugLog.log("InstanceDetail.on_mount() called")
        # Force immediate refresh to show the screen
        self.refresh()
        # Use set_timer to render details after a brief delay to ensure widgets are ready
        self.set_timer(0.2, self._render_details)
        # Fetch spot price if not already loaded
        self._fetch_spot_price_if_needed()

    def _render_details(self) -> None:
        """Render the detailed information"""
        DebugLog.log("InstanceDetail._render_details() called")
        try:
            inst = self.instance_type
            DebugLog.log(f"Rendering details for: {inst.instance_type}")
            is_free_tier = self.free_tier_service.is_eligible(inst.instance_type)
            free_tier_info = self.free_tier_service.get_info()

            lines = []
            lines.append(f"Instance Type: {inst.instance_type}")
            lines.append("")

            # Free tier section
            if is_free_tier:
                lines.append("━" * 60)
                lines.append("")
                lines.append("🆓 AWS FREE TIER ELIGIBLE")
                lines.append(f"  • {free_tier_info['hours_per_month']} hours/month for {free_tier_info['duration_months']} months (new accounts)")
                lines.append("  • Available in most regions")
                lines.append(f"  • Includes {', '.join(free_tier_info['instance_types'])}")
                lines.append("")
                lines.append("━" * 60)
                lines.append("")

            # Compute
            lines.append("Compute")
            lines.append(f"  • vCPU:              {inst.vcpu_info.default_vcpus}")
            if inst.vcpu_info.default_cores:
                lines.append(f"  • Default Cores:     {inst.vcpu_info.default_cores}")
            if inst.vcpu_info.default_threads_per_core:
                lines.append(f"  • Threads per Core:  {inst.vcpu_info.default_threads_per_core}")
            if inst.processor_info.sustained_clock_speed_in_ghz:
                lines.append(f"  • Sustained Clock:   {inst.processor_info.sustained_clock_speed_in_ghz} GHz")
            lines.append("")

            # Memory
            lines.append("Memory")
            memory_gb = inst.memory_info.size_in_gb
            lines.append(f"  • Total Memory:      {memory_gb:.2f} GB ({inst.memory_info.size_in_mib} MiB)")
            lines.append("")

            # Network
            lines.append("Network")
            lines.append(f"  • Performance:       {inst.network_info.network_performance}")
            lines.append(f"  • Max Interfaces:    {inst.network_info.maximum_network_interfaces}")
            lines.append(f"  • Max IPv4 per ENI:  {inst.network_info.maximum_ipv4_addresses_per_interface}")
            lines.append(f"  • Max IPv6 per ENI:  {inst.network_info.maximum_ipv6_addresses_per_interface}")
            lines.append("")

            # Storage
            lines.append("Storage")
            lines.append(f"  • EBS Optimized:     {inst.ebs_info.ebs_optimized_support.title()}")
            if inst.ebs_info.ebs_optimized_info:
                ebs_info = inst.ebs_info.ebs_optimized_info
                if "MaximumBandwidthMbps" in ebs_info:
                    lines.append(f"  • EBS Bandwidth:     Up to {ebs_info['MaximumBandwidthMbps']} Mbps")
                if "MaximumThroughputMBps" in ebs_info:
                    lines.append(f"  • EBS Throughput:    Up to {ebs_info['MaximumThroughputMBps']} MB/s")
            if inst.instance_storage_info:
                if inst.instance_storage_info.total_size_in_gb:
                    lines.append(f"  • Instance Storage:  {inst.instance_storage_info.total_size_in_gb} GB")
                if inst.instance_storage_info.nvme_support:
                    lines.append(f"  • NVMe Support:      {inst.instance_storage_info.nvme_support}")
            else:
                lines.append("  • Instance Storage:  Not Available")
            lines.append("")

            # Architecture & Virtualization
            lines.append("Architecture & Virtualization")
            arch_str = ", ".join(inst.processor_info.supported_architectures)
            lines.append(f"  • Supported Architectures:  {arch_str}")
            lines.append("")

            # Additional Info
            lines.append("Additional Info")
            lines.append(f"  • Burstable Performance:     {'Yes' if inst.burstable_performance_supported else 'No'}")
            lines.append(f"  • Current Generation:        {'Yes' if inst.current_generation else 'No'}")
            lines.append(f"  • Hibernation Supported:      {'Yes' if inst.hibernation_supported else 'No'}")
            lines.append("")

            # Pricing section
            lines.append("━" * 60)
            lines.append("")
            lines.append("Pricing")
            lines.append("")
            
            if inst.pricing:
                if inst.pricing.on_demand_price:
                    lines.append(f"  • On-Demand Price:        ${inst.pricing.on_demand_price:.4f} per hour")
                    
                    # Cost calculator
                    monthly_cost = inst.pricing.calculate_monthly_cost()
                    annual_cost = inst.pricing.calculate_annual_cost()
                    
                    if monthly_cost:
                        lines.append(f"  • Monthly Cost (730 hrs): ${monthly_cost:.2f}")
                    if annual_cost:
                        lines.append(f"  • Annual Cost (8,760 hrs): ${annual_cost:.2f}")
                    
                    # Cost per vCPU and per GB RAM
                    cost_per_vcpu = inst.pricing.on_demand_price / inst.vcpu_info.default_vcpus if inst.vcpu_info.default_vcpus > 0 else None
                    cost_per_gb = inst.pricing.on_demand_price / inst.memory_info.size_in_gb if inst.memory_info.size_in_gb > 0 else None
                    
                    if cost_per_vcpu:
                        lines.append(f"  • Cost per vCPU/hour:     ${cost_per_vcpu:.6f}")
                    if cost_per_gb:
                        lines.append(f"  • Cost per GB RAM/hour:   ${cost_per_gb:.6f}")
                else:
                    lines.append("  • On-Demand Price:        Not available")
                
                if inst.pricing.spot_price:
                    lines.append(f"  • Current Spot Price:     ${inst.pricing.spot_price:.4f} per hour")
                    if inst.pricing.on_demand_price:
                        savings = ((inst.pricing.on_demand_price - inst.pricing.spot_price) / inst.pricing.on_demand_price) * 100
                        lines.append(f"  • Spot Savings:           {savings:.1f}% off on-demand")
                elif inst.pricing and inst.pricing.on_demand_price:
                    # Spot price is being fetched
                    lines.append("  • Current Spot Price:     Loading...")
                else:
                    lines.append("  • Current Spot Price:     Not available")
            else:
                lines.append("  • Pricing information:     Not loaded")
                lines.append("  • (Pricing is fetched in the background)")

            detail_text = self.query_one("#detail-text", Static)
            detail_text.update("\n".join(lines))
            DebugLog.log("InstanceDetail content rendered successfully")
            # Force refresh to ensure content is visible
            self.refresh()
        except Exception as e:
            DebugLog.log(f"ERROR rendering details: {e}")
            import traceback
            DebugLog.log(f"Traceback: {traceback.format_exc()}")
            # Try to show error message
            try:
                detail_text = self.query_one("#detail-text", Static)
                detail_text.update(f"Error loading details: {str(e)}")
            except:
                pass

    def _fetch_spot_price_if_needed(self) -> None:
        """Fetch spot price for this instance if not already loaded"""
        inst = self.instance_type
        
        # Only fetch if we have on-demand price but no spot price yet
        if inst.pricing and inst.pricing.on_demand_price is not None and inst.pricing.spot_price is None:
            # Fetch spot price in background thread
            def fetch_spot_price():
                try:
                    # Get region and settings from app
                    if hasattr(self.app, 'current_region') and self.app.current_region:
                        region = self.app.current_region
                        profile = self.app.settings.aws_profile if hasattr(self.app, 'settings') else None
                        
                        DebugLog.log(f"Fetching spot price for {inst.instance_type} in {region}")
                        aws_client = AWSClient(region, profile)
                        pricing_service = PricingService(aws_client)
                        spot_price = pricing_service.get_spot_price(inst.instance_type, region)
                        
                        # Update the instance pricing
                        if inst.pricing:
                            inst.pricing.spot_price = spot_price
                        else:
                            from src.models.instance_type import PricingInfo
                            inst.pricing = PricingInfo(
                                on_demand_price=None,
                                spot_price=spot_price
                            )
                        
                        # Update the UI
                        def update_ui():
                            try:
                                self._render_details()
                            except Exception as e:
                                DebugLog.log(f"Error updating UI after spot price fetch: {e}")
                        
                        self.app.call_from_thread(update_ui)
                        DebugLog.log(f"Spot price for {inst.instance_type}: {spot_price}")
                    else:
                        DebugLog.log(f"Cannot fetch spot price: region not set")
                except Exception as e:
                    DebugLog.log(f"Error fetching spot price for {inst.instance_type}: {e}")
            
            # Start fetch in background thread
            thread = Thread(target=fetch_spot_price, daemon=True)
            thread.start()

    def action_back(self) -> None:
        """Go back to instance list"""
        self.dismiss(None)

    def action_quit(self) -> None:
        """Quit application"""
        self.app.exit()

