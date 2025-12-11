"""Instance type list screen"""

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import DataTable, Input, Static, Label
from textual.screen import Screen
from textual import events
from typing import List, Optional

from src.models.instance_type import InstanceType
from src.services.free_tier_service import FreeTierService
from src.debug import DebugLog, DebugPane
from textual.containers import Vertical
from src.ui.region_selector import RegionSelector


class InstanceList(Screen):
    """Screen for displaying list of instance types"""

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("escape", "back", "Back"),
        ("f", "toggle_free_tier_filter", "Filter Free Tier"),
        ("/", "focus_search", "Search"),
    ]

    def __init__(self, instance_types: List[InstanceType], region: str):
        super().__init__()
        self.all_instance_types = instance_types
        self.filtered_instance_types = instance_types
        self._region = region  # Use _region to avoid conflict with Screen.region property
        self.free_tier_filter = False
        self.search_term = ""
        self._pricing_loading = True  # Track if pricing is being loaded
        self._pricing_loaded_count = 0  # Track how many prices have been loaded

    def compose(self) -> ComposeResult:
        with Vertical():
            with Container(id="list-container"):
                yield Static(
                    f"EC2 Instance Types - {self._region}",
                    id="header"
                )
                yield Static(
                    "",
                    id="pricing-status-header"
                )
                with Horizontal(id="search-container"):
                    yield Label("Search: ", id="search-label")
                    yield Input(
                        placeholder="Type to search...",
                        id="search-input"
                    )
                yield DataTable(id="instance-table")
                with Horizontal(id="status-bar"):
                    yield Static("", id="status-text")
                yield Static(
                    "Enter: View Details | Esc: Back | Q: Quit | /: Search | F: Filter Free Tier",
                    id="help-text"
                )
            if DebugLog.is_enabled():
                yield DebugPane()

    def on_mount(self) -> None:
        """Initialize the table when screen is mounted"""
        table = self.query_one("#instance-table", DataTable)
        # Configure table for row selection (not cell selection)
        table.cursor_type = "row"
        table.add_columns(
            "Instance Type",
            "vCPU",
            "Memory",
            "Network",
            "On-Demand Price",
            "Architecture",
            "Free Tier"
        )
        self._update_pricing_header()
        self._populate_table()
        # Focus the table so it can receive keyboard input and scroll
        table.focus()

    def _populate_table(self) -> None:
        """Populate the table with instance types"""
        table = self.query_one("#instance-table", DataTable)
        table.clear()

        free_tier_service = FreeTierService()

        for instance in self.filtered_instance_types:
            # Format memory
            memory_gb = instance.memory_info.size_in_gb
            if memory_gb < 1:
                memory_str = f"{memory_gb:.2f} GB"
            else:
                memory_str = f"{memory_gb:.1f} GB"

            # Format architecture
            arch_str = ", ".join(instance.processor_info.supported_architectures)

            # Free tier indicator
            is_free_tier = free_tier_service.is_eligible(instance.instance_type)
            free_tier_str = "🆓 [FREE TIER]" if is_free_tier else ""

            # Format pricing
            if instance.pricing and instance.pricing.on_demand_price:
                price_str = f"${instance.pricing.on_demand_price:.4f}/hr"
            elif self._pricing_loading:
                price_str = "⏳ Loading..."
            else:
                price_str = "N/A"

            table.add_row(
                instance.instance_type,
                str(instance.vcpu_info.default_vcpus),
                memory_str,
                instance.network_info.network_performance,
                price_str,
                arch_str,
                free_tier_str,
            )

        # Update status bar
        total = len(self.all_instance_types)
        filtered = len(self.filtered_instance_types)
        free_tier_count = sum(
            1 for inst in self.filtered_instance_types
            if free_tier_service.is_eligible(inst.instance_type)
        )
        status = f"Showing {filtered} of {total} instance types"
        if free_tier_count > 0:
            status += f" | 🆓 {free_tier_count} free tier eligible"
        if self.free_tier_filter:
            status += " | [Free Tier Filter Active]"
        
        # Add pricing loading status
        if self._pricing_loading:
            pricing_loaded = sum(
                1 for inst in self.filtered_instance_types
                if inst.pricing and inst.pricing.on_demand_price is not None
            )
            if filtered > 0:
                status += f" | ⏳ Loading prices... ({pricing_loaded}/{filtered})"
            else:
                status += " | ⏳ Loading prices..."
        
        self.query_one("#status-text", Static).update(status)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes"""
        if event.input.id == "search-input":
            self.search_term = event.value.lower()
            self._apply_filters()

    def _apply_filters(self) -> None:
        """Apply search and free tier filters"""
        free_tier_service = FreeTierService()
        filtered = self.all_instance_types

        # Apply search filter
        if self.search_term:
            filtered = [
                inst for inst in filtered
                if self.search_term in inst.instance_type.lower()
            ]

        # Apply free tier filter
        if self.free_tier_filter:
            filtered = [
                inst for inst in filtered
                if free_tier_service.is_eligible(inst.instance_type)
            ]

        self.filtered_instance_types = filtered
        self._populate_table()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection - navigate to detail view"""
        if event.cursor_row is not None:
            self._navigate_to_detail(event.cursor_row)

    def on_key(self, event: events.Key) -> None:
        """Handle key presses"""
        if event.key == "enter":
            table = self.query_one("#instance-table", DataTable)
            cursor_row = table.cursor_row
            if cursor_row is not None:
                event.prevent_default()
                event.stop()
                self._navigate_to_detail(cursor_row)

    def _navigate_to_detail(self, row_key) -> None:
        """Navigate to detail view for selected row"""
        table = self.query_one("#instance-table", DataTable)
        try:
            # Convert row_key (which is an integer index) to actual RowKey object
            row_keys_list = list(table.rows.keys())
            
            if isinstance(row_key, int) and row_key < len(row_keys_list):
                actual_key = row_keys_list[row_key]
            else:
                # If it's already a RowKey, use it directly
                actual_key = row_key
            
            row_data = table.get_row(actual_key)
            instance_type_name = row_data[0]  # First column is instance type

            # Find the instance type object
            instance = next(
                (inst for inst in self.filtered_instance_types
                 if inst.instance_type == instance_type_name),
                None
            )

            if instance:
                # Push detail screen BEFORE dismissing - same pattern as region selector
                from src.ui.instance_detail import InstanceDetail
                detail_screen = InstanceDetail(instance)
                await_push = self.app.push_screen(detail_screen)
                DebugLog.log(f"Pushed detail screen for: {instance.instance_type}")
                self.app.refresh()
                
                # Wait for screen to mount, then dismiss this one
                async def dismiss_after_detail_mounts():
                    try:
                        await await_push
                        DebugLog.log("Detail screen mounted, dismissing instance list")
                        await asyncio.sleep(0.1)  # Give it time to render
                        self.dismiss(instance)  # This will trigger the handler but detail is already on top
                    except Exception as e:
                        DebugLog.log(f"Error in dismiss_after_detail_mounts: {e}")
                
                # Schedule the async task using the app's event loop
                import asyncio
                loop = asyncio.get_event_loop()
                loop.create_task(dismiss_after_detail_mounts())
        except Exception as e:
            DebugLog.log(f"Error navigating to detail: {e}")
            # Ignore errors if row doesn't exist

    def action_toggle_free_tier_filter(self) -> None:
        """Toggle free tier filter"""
        self.free_tier_filter = not self.free_tier_filter
        self._apply_filters()

    def action_focus_search(self) -> None:
        """Focus the search input"""
        self.query_one("#search-input", Input).focus()

    def action_back(self) -> None:
        """Go back to region selector"""
        # Push region selector BEFORE dismissing - same pattern as detail screen
        try:
            from src.services.aws_client import AWSClient
            aws_client = AWSClient("us-east-1", self.app.settings.aws_profile)
            accessible_regions = aws_client.get_accessible_regions()
        except:
            accessible_regions = None
        
        region_selector = RegionSelector(self.app.current_region or self.app.settings.aws_region, accessible_regions)
        await_push = self.app.push_screen(region_selector)
        self.app.refresh()
        
        # Wait for region selector to mount, then dismiss this screen
        async def dismiss_after_region_mounts():
            try:
                await await_push
                await asyncio.sleep(0.1)  # Give it time to render
                self.dismiss(None)  # This will trigger the handler but region selector is already on top
            except Exception as e:
                DebugLog.log(f"Error in dismiss_after_region_mounts: {e}")
        
        # Schedule the async task using the app's event loop
        import asyncio
        loop = asyncio.get_event_loop()
        loop.create_task(dismiss_after_region_mounts())

    def action_quit(self) -> None:
        """Quit application"""
        self.app.exit()
    
    def mark_pricing_loading(self, loading: bool) -> None:
        """Mark pricing loading state"""
        self._pricing_loading = loading
        self._update_pricing_header()
        self._populate_table()
    
    def update_pricing_progress(self) -> None:
        """Update the table to reflect pricing progress"""
        self._update_pricing_header()
        self._populate_table()
    
    def _update_pricing_header(self) -> None:
        """Update the pricing status header"""
        try:
            header = self.query_one("#pricing-status-header", Static)
            if self._pricing_loading:
                pricing_loaded = sum(
                    1 for inst in self.all_instance_types
                    if inst.pricing and inst.pricing.on_demand_price is not None
                )
                total = len(self.all_instance_types)
                header.update(f"💰 ⏳ Loading pricing information... ({pricing_loaded}/{total} loaded)")
                header.styles.color = "yellow"
            else:
                # Hide the header once loading is complete
                header.update("")
        except Exception:
            pass  # Header might not exist yet

