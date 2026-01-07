"""Main application class"""

import asyncio
import logging
from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.containers import Container, Vertical
from textual.widgets import Static, LoadingIndicator, Button
from textual import events
from textual.message import Message
from textual.worker import Worker, WorkerState
from src.debug import DebugLog, DebugPane

from src.ui.region_selector import RegionSelector
from src.ui.instance_list import InstanceList
from src.ui.instance_detail import InstanceDetail
from src.services.aws_client import AWSClient
from src.services.async_aws_client import AsyncAWSClient
from src.services.instance_service import InstanceService
from src.services.pricing_service import PricingService
from src.services.async_pricing_service import AsyncPricingService
from src.config.settings import Settings

logger = logging.getLogger("instancepedia")


class InstancepediaApp(App):
    """Main application"""
    
    class InstanceTypesLoaded(Message):
        """Message sent when instance types are loaded"""
        def __init__(self, instance_types):
            super().__init__()
            self.instance_types = instance_types
    
    class InstanceTypesError(Message):
        """Message sent when loading fails"""
        def __init__(self, error_msg):
            super().__init__()
            self.error_msg = error_msg


    CSS = """
    Screen {
        background: $surface;
    }
    
    #region-container {
        width: 100%;
        height: 1fr;
        align: center middle;
        border: solid $primary;
        padding: 1;
    }
    
    #title {
        text-align: center;
        text-style: bold;
        margin: 1;
        color: $primary;
    }
    
    #region-label {
        text-align: center;
        margin: 1;
    }
    
    #region-table {
        margin: 1;
        width: 100%;
        height: 1fr;
        min-height: 10;
    }
    
    #help-text {
        text-align: center;
        margin: 1;
        color: $text-muted;
    }
    
    #list-container {
        width: 100%;
        height: 1fr;
        padding: 1;
    }
    
    #header {
        text-align: center;
        text-style: bold;
        margin: 1;
        color: $primary;
    }
    
    #pricing-status-header {
        text-align: center;
        margin: 1;
        text-style: bold;
    }
    
    #search-container {
        margin: 1;
        height: 3;
    }
    
    #search-label {
        width: 8;
        margin-right: 1;
    }
    
    #search-input {
        width: 1fr;
    }
    
    #instance-table {
        margin: 1;
        height: 1fr;
    }
    
    #instance-tree {
        margin: 1;
        height: 1fr;
    }
    
    #status-bar {
        margin: 1;
        height: 1;
    }
    
    #status-text {
        width: 1fr;
        color: $text-muted;
    }
    
    #detail-container {
        width: 100%;
        height: 1fr;
        padding: 1;
    }
    
    #detail-content {
        margin: 1;
        height: 1fr;
        border: solid $primary;
    }
    
    #detail-text {
        margin: 1;
        padding: 1;
    }
    """

    def __init__(self, settings: Settings, debug: bool = False):
        super().__init__()
        self.settings = settings
        self.current_region: str | None = None
        self.instance_types = []
        self.debug_mode = debug
        self._pricing_worker = None
        self._shutting_down = False
        if debug:
            DebugLog.enable()

    def on_mount(self) -> None:
        """Show region selector on mount"""
        if self.debug_mode:
            DebugLog.log("App mounted - Debug mode enabled")
        
        # Get accessible regions (only regions enabled for this account)
        try:
            from src.services.aws_client import AWSClient
            aws_client = AWSClient("us-east-1", self.settings.aws_profile)
            accessible_regions = aws_client.get_accessible_regions()
            if accessible_regions:
                DebugLog.log(f"Found {len(accessible_regions)} accessible regions for this account")
            else:
                DebugLog.log("Could not determine accessible regions, showing all from hardcoded list")
                accessible_regions = None
        except Exception as e:
            DebugLog.log(f"Error getting accessible regions: {e}, showing all from hardcoded list")
            accessible_regions = None
        
        self.push_screen(RegionSelector(self.settings.aws_region, accessible_regions))
        if self.debug_mode:
            DebugLog.log("Region selector screen pushed")

    def _fetch_instance_types_simple(self, region_code: str) -> None:
        """Fetch instance types - no loading screen, just update current screen"""
        DebugLog.log(f"Starting fetch for region: {region_code}")
        self.current_region = region_code
        
        def fetch_worker() -> list:
            """Worker function that runs in background thread"""
            DebugLog.log(f"Worker: Creating AWS client for region: {self.current_region}")
            
            # Update status on region selector screen
            try:
                if isinstance(self.screen, RegionSelector):
                    status_widget = self.screen.query_one("#loading-status", expect_none=True)
                    if status_widget:
                        self.call_from_thread(
                            lambda: status_widget.update("Fetching instance types from AWS...")
                        )
            except Exception as e:
                # Screen may have transitioned or widget may not exist anymore
                logger.debug(f"Failed to update status widget: {e}")
            
            aws_client = AWSClient(self.current_region, self.settings.aws_profile)
            instance_service = InstanceService(aws_client)

            DebugLog.log("Worker: Fetching instance types from AWS...")
            
            instance_types = instance_service.get_instance_types()
            DebugLog.log(f"Worker: Fetched {len(instance_types)} instance types")
            return instance_types
        
        # Run worker using Textual's worker system
        worker = self.run_worker(
            fetch_worker,
            name="fetch_instance_types",
            description="Fetching EC2 instance types from AWS",
            thread=True,
            exit_on_error=False,
        )
        
        # Store reference to worker for state handler
        self._current_worker = worker

    def on_region_selector_dismissed(self, event: RegionSelector.Dismissed) -> None:
        """Handle region selection"""
        DebugLog.log(f"Region selector dismissed with value: {event.value}")
        if event.value is None:
            DebugLog.log("Value is None, exiting")
            self.exit()
            return
        # This shouldn't be called in the new flow, but handle it just in case
        self.current_region = event.value

    def _fetch_instance_types_async(self, loading_screen: 'LoadingScreen') -> None:
        """Fetch instance types asynchronously using Textual's worker system"""
        DebugLog.log("Starting async fetch with worker")
        
        # Update loading screen status
        loading_screen.update_status("Connecting to AWS...")
        
        def fetch_worker() -> list:
            """Worker function that runs in background thread"""
            DebugLog.log(f"Worker: Creating AWS client for region: {self.current_region}")
            aws_client = AWSClient(self.current_region, self.settings.aws_profile)
            instance_service = InstanceService(aws_client)

            DebugLog.log("Worker: Fetching instance types from AWS...")
            # Update status during fetch - use call_from_thread since we're in a worker thread
            self.call_from_thread(
                lambda: loading_screen.update_status("Fetching instance types from AWS...")
            )
            
            instance_types = instance_service.get_instance_types()
            DebugLog.log(f"Worker: Fetched {len(instance_types)} instance types")
            return instance_types
        
        # Run worker using Textual's worker system
        worker = self.run_worker(
            fetch_worker,
            name="fetch_instance_types",
            description="Fetching EC2 instance types from AWS",
            thread=True,
            exit_on_error=False,
        )
        
        # Store reference to loading screen for use in worker state handler
        self._current_loading_screen = loading_screen
        self._current_worker = worker

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Handle worker state changes"""
        # Only handle our fetch worker
        if event.worker != getattr(self, '_current_worker', None):
            return
        
        if event.state == WorkerState.SUCCESS:
            DebugLog.log("Worker completed successfully")
            try:
                instance_types = event.worker.result
                self._handle_fetch_success(instance_types)
            except Exception as e:
                DebugLog.log(f"Error getting worker result: {e}")
                self._handle_fetch_error(e)
        elif event.state == WorkerState.ERROR:
            DebugLog.log("Worker failed with error")
            try:
                error = event.worker.error
                self._handle_fetch_error(error)
            except Exception as e:
                DebugLog.log(f"Error getting worker error: {e}")
                self._handle_fetch_error(e)

    def _handle_fetch_success(self, instance_types: list) -> None:
        """Handle successful fetch"""
        DebugLog.log(f"Fetch successful: {len(instance_types)} instance types")
        self.instance_types = instance_types
        
        # Show instance list - replace current screen
        if len(self.instance_types) > 0:
            DebugLog.log("Replacing screens with instance list")
            try:
                # Pop region selector (which is showing loading state)
                if isinstance(self.screen, RegionSelector):
                    self.pop_screen()
                    DebugLog.log("Region selector popped")
            except Exception as pop_err:
                DebugLog.log(f"Error popping screens: {pop_err}")
            
            DebugLog.log("Pushing instance list screen")
            instance_list = InstanceList(self.instance_types, self.current_region)
            self.push_screen(instance_list)
            DebugLog.log("Instance list screen pushed successfully")
            
            # Start fetching pricing in the background
            self._fetch_pricing_background(instance_list)
        else:
            DebugLog.log("No instance types found")
            try:
                if isinstance(self.screen, RegionSelector):
                    self.pop_screen()
            except Exception as e:
                # Screen may already be popped or app may be shutting down
                logger.debug(f"Failed to pop region selector screen: {e}")
            self.push_screen(ErrorScreen("No instance types found for this region."))
    
    def _fetch_pricing_background(self, instance_list: InstanceList) -> None:
        """Fetch pricing information in the background using async"""
        DebugLog.log("_fetch_pricing_background called")

        async def pricing_worker():
            """Async worker function to fetch pricing using aioboto3"""
            DebugLog.log("Async pricing worker started")
            try:
                # Check if we're shutting down before starting
                if self._shutting_down:
                    DebugLog.log("Pricing worker cancelled - app shutting down")
                    return

                # Mark pricing as loading
                def do_mark_loading():
                    try:
                        instance_list.mark_pricing_loading(True)
                    except Exception as e:
                        DebugLog.log(f"Error marking pricing as loading: {e}")
                self.call_later(do_mark_loading)
                DebugLog.log("Marked pricing as loading")

                DebugLog.log(f"Starting async pricing fetch for region: {self.current_region}")

                # Create async AWS client and pricing service
                async_client = AsyncAWSClient(self.current_region, self.settings.aws_profile)
                pricing_service = AsyncPricingService(async_client)
                DebugLog.log("Async pricing service created successfully")

                total_to_fetch = len(self.instance_types)
                DebugLog.log(f"Fetching on-demand prices for {total_to_fetch} instance types using async")
                DebugLog.log("Note: Spot prices will be fetched on-demand when viewing instance details")

                # Track progress and cache hits
                completed_count = 0
                cache_hits = 0
                failed_instances = []

                # Build a map of instance type names to objects for quick lookup
                from src.models.instance_type import PricingInfo
                instance_map = {inst.instance_type: inst for inst in self.instance_types}

                def on_price(inst_type_name: str, price: Optional[float]):
                    """Called when each price is fetched - update instance immediately"""
                    inst = instance_map.get(inst_type_name)
                    if inst:
                        inst.pricing = PricingInfo(
                            on_demand_price=price,
                            spot_price=None  # Fetched on-demand when viewing details
                        )
                        if price is None:
                            failed_instances.append(inst)

                def on_progress(completed: int, total: int):
                    """Progress callback for batch pricing fetch"""
                    nonlocal completed_count
                    completed_count = completed
                    # Update UI periodically - schedule on main thread
                    if completed % 10 == 0 or completed == total:
                        def do_update():
                            try:
                                instance_list.update_pricing_progress()
                            except Exception as e:
                                DebugLog.log(f"Error updating pricing progress: {e}")
                        # Schedule UI update on the main thread
                        self.call_later(do_update)

                def on_cache_hit():
                    """Called when a cache hit occurs"""
                    nonlocal cache_hits
                    cache_hits += 1

                # Fetch all on-demand prices concurrently with rate limiting
                instance_type_names = [inst.instance_type for inst in self.instance_types]

                # Use batch method with concurrency control
                await pricing_service.get_on_demand_prices_batch(
                    instance_type_names,
                    self.current_region,
                    concurrency=10,  # Concurrent requests (async handles this efficiently)
                    progress_callback=on_progress,
                    price_callback=on_price,
                    cache_hit_callback=on_cache_hit
                )

                # Update UI after all prices fetched
                def do_update_after_fetch():
                    try:
                        instance_list.update_pricing_progress()
                    except Exception:
                        pass
                self.call_later(do_update_after_fetch)

                # Retry failed instances with lower concurrency
                if failed_instances and not self._shutting_down:
                    DebugLog.log(f"Retrying {len(failed_instances)} failed pricing requests")
                    failed_names = [inst.instance_type for inst in failed_instances]

                    retry_prices = await pricing_service.get_on_demand_prices_batch(
                        failed_names,
                        self.current_region,
                        concurrency=3  # Lower concurrency for retries
                    )

                    for inst in failed_instances:
                        retry_price = retry_prices.get(inst.instance_type)
                        if retry_price is not None and inst.pricing:
                            inst.pricing.on_demand_price = retry_price

                # Mark pricing as done
                pricing_loaded_count = sum(
                    1 for inst in self.instance_types
                    if inst.pricing and inst.pricing.on_demand_price is not None
                )
                total_count = len(self.instance_types)
                DebugLog.log(f"Pricing fetch completed: {pricing_loaded_count}/{total_count} instance types have pricing data")
                DebugLog.log(f"Cache hits: {cache_hits}/{pricing_loaded_count} ({cache_hits/pricing_loaded_count*100:.1f}% from cache)" if pricing_loaded_count > 0 else "Cache hits: 0")

                def do_mark_done():
                    try:
                        instance_list.mark_pricing_loading(False, cache_hits=cache_hits, total_prices=pricing_loaded_count)
                    except Exception as e:
                        DebugLog.log(f"Error marking pricing as done: {e}")
                self.call_later(do_mark_done)

            except Exception as e:
                DebugLog.log(f"Error fetching pricing: {e}")
                import traceback
                DebugLog.log(f"Traceback: {traceback.format_exc()}")
                # Mark pricing as done even on error
                def do_mark_done_error():
                    try:
                        instance_list.mark_pricing_loading(False)
                    except Exception:
                        pass
                self.call_later(do_mark_done_error)

        # Run async pricing fetch as a worker
        DebugLog.log("Starting async pricing worker")
        worker = self.run_worker(
            pricing_worker,
            name="fetch_pricing",
            description="Fetching EC2 instance pricing",
            exit_on_error=False,
        )
        self._pricing_worker = worker
        DebugLog.log(f"Pricing worker started: {worker}")
    
    def on_exit(self) -> None:
        """Handle app exit - cancel pricing worker"""
        DebugLog.log("App exiting - cancelling pricing worker")
        self._shutting_down = True
        
        # Cancel the pricing worker if it's running
        if self._pricing_worker is not None:
            try:
                # Textual workers don't have a direct cancel, but setting shutdown flag
                # will cause the worker to exit on next check
                DebugLog.log("Pricing worker shutdown flag set")
            except Exception as e:
                DebugLog.log(f"Error cancelling pricing worker: {e}")
        
        # Also cancel the instance fetch worker if it's running
        if hasattr(self, '_current_worker') and self._current_worker is not None:
            try:
                DebugLog.log("Instance fetch worker shutdown flag set")
            except Exception as e:
                DebugLog.log(f"Error cancelling instance fetch worker: {e}")

    def _handle_fetch_error(self, error: Exception) -> None:
        """Handle fetch error"""
        import traceback
        error_str = str(error)
        
        # Check if it's an opt-in region error
        if "opt-in" in error_str.lower() or "OptInRequired" in error_str:
            error_msg = (
                f"Region '{self.current_region}' requires opt-in.\n\n"
                f"You need to enable this region in your AWS account first.\n"
                f"Visit the AWS Management Console to opt-in to this region."
            )
        else:
            error_msg = f"Error loading instance types:\n{error_str}"
        
        DebugLog.log(f"EXCEPTION: {error_str}")
        full_traceback = traceback.format_exc()
        DebugLog.log(f"Traceback: {full_traceback[:200]}...")  # Truncate long tracebacks
        
        try:
            # Pop region selector (which is showing loading state)
            if isinstance(self.screen, RegionSelector):
                self.pop_screen()
                DebugLog.log("Popped region selector after error")
        except Exception as pop_error:
            DebugLog.log(f"Error popping screen: {pop_error}")
        
        DebugLog.log("Pushing error screen")
        self.push_screen(ErrorScreen(error_msg))
        DebugLog.log("Error screen pushed")

    def on_instance_list_dismissed(self, event: InstanceList.Dismissed) -> None:
        """Handle instance list dismissal"""
        DebugLog.log(f"Instance list dismissed with value: {event.value}")
        if event.value is None:
            # Region selector should already be pushed by instance list
            # Just verify it's there and refresh
            DebugLog.log("Instance list dismissed, region selector should already be visible")
            self.refresh()
        else:
            # Detail screen should already be pushed by instance list
            # Just verify it's there and refresh
            DebugLog.log(f"Instance list dismissed, detail screen should already be visible")
            self.refresh()

    def on_instance_detail_dismissed(self, event: InstanceDetail.Dismissed) -> None:
        """Handle instance detail dismissal"""
        # Back to instance list
        self.push_screen(InstanceList(self.instance_types, self.current_region))


class LoadingScreen(Screen):
    """Loading screen"""
    
    BINDINGS = [("q", "quit", "Quit")]
    
    # Ensure screen is always visible
    AUTO_FOCUS = None

    def __init__(self, region: str = "", app: 'InstancepediaApp' = None):
        super().__init__()
        self._region = region  # Use _region to avoid conflict with Screen.region property
        self.status_text = "Initializing..."
        self.app_ref = app

    def compose(self) -> ComposeResult:
        """Compose the loading screen - keep it simple"""
        DebugLog.log("LoadingScreen.compose() called")
        yield Static("Loading instance types...", id="loading-text")
        yield Static("Please wait...", id="loading-subtext")
        if self._region:
            yield Static(f"Region: {self._region}", id="loading-region")
        yield LoadingIndicator(id="loading-indicator")
        # Add debug pane if enabled
        if DebugLog.is_enabled():
            DebugLog.log("Adding debug pane to loading screen")
            yield DebugPane()
        DebugLog.log("LoadingScreen.compose() completed successfully")

    CSS = """
    Screen {
        background: $surface;
        align: center middle;
    }
    
    #loading-text {
        text-align: center;
        margin: 2;
        text-style: bold;
        color: $primary;
        width: 100%;
    }
    
    #loading-subtext {
        text-align: center;
        margin: 1;
        color: $text-muted;
        width: 100%;
    }
    
    #loading-region {
        text-align: center;
        margin: 1;
        color: $text-muted;
        width: 100%;
    }
    
    #loading-indicator {
        text-align: center;
        margin: 2;
        width: 100%;
    }
    """

    def on_mount(self) -> None:
        """Loading screen mounted - ensure it's visible"""
        DebugLog.log("LoadingScreen.on_mount() called - screen should be visible now")
        DebugLog.log(f"Screen visible: {self.visible}, is_current: {self.is_current}, size: {self.size}")
        
        # Verify widgets are present and log their state
        try:
            loading_text = self.query_one("#loading-text", Static)
            loading_indicator = self.query_one("#loading-indicator", LoadingIndicator)
            subtext = self.query_one("#loading-subtext", Static)
            DebugLog.log(f"Loading text widget: {loading_text}, visible: {getattr(loading_text, 'visible', 'N/A')}")
            DebugLog.log(f"Loading indicator: {loading_indicator}, visible: {getattr(loading_indicator, 'visible', 'N/A')}")
            DebugLog.log(f"Loading subtext: {subtext}, visible: {getattr(subtext, 'visible', 'N/A')}")
        except Exception as e:
            import traceback
            DebugLog.log(f"ERROR finding loading widgets: {e}")
            DebugLog.log(f"Traceback: {traceback.format_exc()}")
        
        # Force multiple refreshes to ensure screen is visible
        self.refresh(layout=True)
        if self.app:
            self.app.refresh()
        DebugLog.log("LoadingScreen refresh called - screen should be visible")
    
    def on_screen_resume(self, event: events.ScreenResume) -> None:
        """Called when screen becomes active"""
        DebugLog.log("LoadingScreen.on_screen_resume() called - screen is now active")
        self.refresh(layout=True)
        if self.app:
            self.app.refresh()
        DebugLog.log("LoadingScreen resumed and refreshed")

    def update_status(self, status: str) -> None:
        """Update the status text"""
        self.status_text = status
        try:
            subtext = self.query_one("#loading-subtext", Static)
            subtext.update(status)
            self.refresh()
        except Exception:
            pass  # Widget might not be ready yet

    def action_quit(self) -> None:
        """Quit from loading screen"""
        self.app.exit()


class ErrorScreen(Screen):
    """Error screen"""

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("escape", "back", "Back"),
    ]

    def __init__(self, error_message: str):
        super().__init__()
        self.error_message = error_message

    def compose(self) -> ComposeResult:
        with Vertical():
            with Container():
                yield Static("Error", id="error-title")
                yield Static(self.error_message, id="error-message")
                yield Static("[Q] Quit  [Esc] Back", id="help-text")
            if DebugLog.is_enabled():
                yield DebugPane()

    CSS = """
    Screen {
        align: center middle;
    }
    
    #error-title {
        text-align: center;
        text-style: bold;
        color: $error;
        margin: 1;
    }
    
    #error-message {
        text-align: center;
        margin: 1;
        padding: 1;
        border: solid $error;
        width: 80;
    }
    
    #help-text {
        text-align: center;
        margin: 1;
        color: $text-muted;
    }
    """

    def action_quit(self) -> None:
        self.app.exit()

    def action_back(self) -> None:
        self.dismiss()

