"""Region selector screen"""

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import DataTable, Static
from textual.screen import Screen
from textual import events

from src.models.region import AWS_REGIONS
from src.debug import DebugLog, DebugPane


class RegionSelector(Screen):
    """Screen for selecting AWS region"""

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("escape", "quit", "Quit"),
    ]
    
    CSS = """
    #loading-overlay {
        width: 100%;
        height: 100%;
        align: center middle;
        background: $surface;
        border: solid $primary;
        padding: 2;
        layer: overlay;
    }
    
    #loading-overlay.hidden {
        display: none;
    }
    
    #loading-overlay Vertical {
        align: center middle;
        width: auto;
        height: auto;
    }
    
    #loading-text {
        text-align: center;
        margin: 2;
        text-style: bold;
        color: $primary;
    }
    
    #loading-indicator {
        align: center middle;
        margin: 3;
    }
    
    #loading-region {
        text-align: center;
        margin: 2;
        text-style: bold;
        color: $primary;
    }
    
    #loading-status {
        text-align: center;
        margin: 1;
        color: $text-muted;
    }
    
    #loading-spacer {
        height: 1;
    }
    """

    def __init__(self, default_region: str = "us-east-1", accessible_regions: list[str] = None):
        super().__init__()
        self.selected_region = default_region
        
        # Build region list: prioritize discovered regions, fall back to hardcoded list
        if accessible_regions:
            # Show all discovered regions, using hardcoded names where available
            # For regions not in hardcoded list, generate a name from the region code
            region_dict = {}
            for code in accessible_regions:
                if code in AWS_REGIONS:
                    region_dict[code] = AWS_REGIONS[code]
                else:
                    # Generate a readable name from region code
                    # Format: "ap-southeast-1" -> "Southeast 1"
                    parts = code.split('-')
                    if len(parts) >= 2:
                        # Capitalize and format
                        name_parts = [p.capitalize() for p in parts[1:]]
                        region_dict[code] = ' '.join(name_parts)
                    else:
                        region_dict[code] = code.upper()
            
            self.regions = [(code, name) for code, name in sorted(region_dict.items())]
        else:
            # If no accessible regions provided, show all from hardcoded list (fallback)
            self.regions = list(AWS_REGIONS.items())

    def compose(self) -> ComposeResult:
        with Vertical():
            with Container(id="region-container"):
                yield Static("EC2 Instance Type Browser", id="title")
                yield Static("Select AWS Region:", id="region-label")
                yield DataTable(id="region-table")
                yield Static(
                    "Enter: Select | Esc/Q: Exit | ↑↓: Navigate",
                    id="help-text"
                )
            # Loading overlay - will be shown when needed
            yield Container(id="loading-overlay", classes="hidden")
            if DebugLog.is_enabled():
                yield DebugPane()

    def on_mount(self) -> None:
        """Initialize the table when screen is mounted"""
        if DebugLog.is_enabled():
            DebugLog.log("Region selector mounted")
        table = self.query_one("#region-table", DataTable)
        # Configure table for row selection (not cell selection)
        table.cursor_type = "row"
        table.add_columns("Region Code", "Region Name")
        
        # Populate table and find default region index
        default_index = 0
        for idx, (code, name) in enumerate(self.regions):
            table.add_row(code, name)
            if code == self.selected_region:
                default_index = idx
        
        if DebugLog.is_enabled():
            DebugLog.log(f"Populated {len(self.regions)} regions, default index: {default_index}")
        
        # Focus table and move cursor to default region
        table.focus()
        # Move cursor to the default region row
        for _ in range(default_index):
            table.action_cursor_down()
        
        if DebugLog.is_enabled():
            DebugLog.log("Region selector initialized")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection"""
        self._select_region(event.cursor_row)

    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        """Handle cell selection - treat as row selection when Enter is pressed"""
        # This fires when navigating, but we'll handle Enter separately
        pass

    def on_key(self, event: events.Key) -> None:
        """Handle key presses at screen level"""
        # Handle Enter key to select region
        if event.key == "enter":
            table = self.query_one("#region-table", DataTable)
            # Try to get cursor row - it might be None if table doesn't have focus
            try:
                cursor_row = table.cursor_row
                if cursor_row is not None:
                    event.prevent_default()
                    event.stop()
                    self._select_region(cursor_row)
            except Exception:
                # If cursor_row access fails, try coordinate approach
                try:
                    coord = table.cursor_coordinate
                    if coord:
                        row_keys = list(table.rows.keys())
                        if coord.row < len(row_keys):
                            row_key = row_keys[coord.row]
                            event.prevent_default()
                            event.stop()
                            self._select_region(row_key)
                except Exception:
                    pass

    def _select_region(self, row_key) -> None:
        """Select region from row key"""
        try:
            DebugLog.log(f"_select_region called with row_key: {row_key}")
            table = self.query_one("#region-table", DataTable)
            
            # Convert row_key (which is an integer index) to actual RowKey object
            # cursor_row returns an integer, but get_row() needs a RowKey object
            row_keys_list = list(table.rows.keys())
            if isinstance(row_key, int) and row_key < len(row_keys_list):
                actual_key = row_keys_list[row_key]
            else:
                # If it's already a RowKey, use it directly
                actual_key = row_key
            
            # Get row data using the actual row key
            row_data = table.get_row(actual_key)
            DebugLog.log(f"Got row_data: {row_data}")
            
            if row_data and len(row_data) > 0:
                region_code = row_data[0]  # First column is region code
                DebugLog.log(f"Selected region_code: {region_code}")
                
                # Store region in app
                self.app.current_region = region_code
                
                # Update title immediately
                try:
                    title = self.query_one("#title", Static)
                    title.update("Fetching EC2 Instance Types...")
                except Exception:
                    pass
                
                # Use set_timer to update UI and start fetch after a brief delay
                def update_ui_and_fetch():
                    """Update UI and start fetch"""
                    try:
                        from textual.widgets import LoadingIndicator, Static
                        
                        container = self.query_one("#region-container", Container)
                        table = self.query_one("#region-table", DataTable)
                        region_label = self.query_one("#region-label", Static)
                        help_text = self.query_one("#help-text", Static)
                        
                        # Hide unhelpful elements
                        table.display = False
                        region_label.display = False
                        help_text.display = False
                        
                        # Clear container and add clean loading widgets
                        container.remove_children()
                        container.mount(
                            Static("", id="loading-spacer"),
                            LoadingIndicator(id="loading-indicator"),
                            Static(f"Region: {region_code}", id="loading-region"),
                            Static("Connecting to AWS...", id="loading-status")
                        )
                        self.refresh()
                        
                        # Start fetch
                        self.app._fetch_instance_types_simple(region_code)
                    except Exception:
                        # Still try to start fetch
                        self.app._fetch_instance_types_simple(region_code)
                
                # Use set_timer with 0.1 second delay to ensure title is visible first
                self.set_timer(0.1, update_ui_and_fetch)
                
                # Force refresh immediately
                self.refresh()
        except Exception as e:
            DebugLog.log(f"Exception in _select_region: {e}")
            # If that fails, try getting by coordinate
            try:
                table = self.query_one("#region-table", DataTable)
                coord = table.cursor_coordinate
                if coord:
                    row_keys = list(table.rows.keys())
                    if coord.row < len(row_keys):
                        row_key = row_keys[coord.row]
                        row_data = table.get_row(row_key)
                        if row_data and len(row_data) > 0:
                            region_code = row_data[0]
                            DebugLog.log(f"Dismissing with region_code (fallback): {region_code}")
                            self.dismiss(region_code)
            except Exception as e2:
                DebugLog.log(f"Fallback also failed: {e2}")



    def _show_loading_overlay(self, region_code: str) -> None:
        """Show loading overlay on this screen"""
        try:
            from textual.widgets import Static, LoadingIndicator
            from textual.containers import Vertical
            
            overlay = self.query_one("#loading-overlay", Container)
            
            # Clear and add loading widgets
            overlay.remove_children()
            
            # Mount widgets directly to overlay using Vertical container
            vertical = Vertical()
            vertical.mount(
                Static("Loading instance types...", id="loading-text"),
                LoadingIndicator(id="loading-indicator"),
                Static(f"Region: {region_code}", id="loading-region"),
                Static("Please wait...", id="loading-subtext")
            )
            overlay.mount(vertical)
            
            # Show overlay
            overlay.remove_class("hidden")
            self.refresh()
            DebugLog.log("Loading overlay mounted and shown")
        except Exception as e:
            DebugLog.log(f"ERROR in _show_loading_overlay: {e}")
            raise

    def action_quit(self) -> None:
        """Action to quit"""
        self.dismiss(None)

