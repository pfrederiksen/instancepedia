"""Main application class"""

import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
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
from src.services.instance_service import InstanceService
from src.services.pricing_service import PricingService
from src.config.settings import Settings


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
            except:
                pass
            
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
            except:
                pass
            self.push_screen(ErrorScreen("No instance types found for this region."))
    
    def _fetch_pricing_background(self, instance_list: InstanceList) -> None:
        """Fetch pricing information in the background"""
        DebugLog.log("_fetch_pricing_background called")
        def pricing_worker():
            """Worker function to fetch pricing"""
            DebugLog.log("pricing_worker started")
            try:
                # Check if we're shutting down before starting
                if self._shutting_down:
                    DebugLog.log("Pricing worker cancelled - app shutting down")
                    return
                
                # Mark pricing as loading
                def mark_loading():
                    try:
                        instance_list.mark_pricing_loading(True)
                    except Exception as e:
                        DebugLog.log(f"Error marking pricing as loading: {e}")
                self.call_from_thread(mark_loading)
                DebugLog.log("Marked pricing as loading")
                
                DebugLog.log(f"Starting pricing fetch for region: {self.current_region}")
                aws_client = AWSClient(self.current_region, self.settings.aws_profile)
                
                # Test pricing client creation
                try:
                    pricing_client = aws_client.pricing_client
                    DebugLog.log("Pricing client created successfully")
                except Exception as e:
                    DebugLog.log(f"Failed to create pricing client: {e}")
                    import traceback
                    DebugLog.log(f"Traceback: {traceback.format_exc()}")
                    # Mark as done and return - can't fetch pricing without client
                    self.call_from_thread(lambda: instance_list.mark_pricing_loading(False))
                    return
                
                try:
                    pricing_service = PricingService(aws_client)
                    DebugLog.log("Pricing service created successfully")
                except Exception as e:
                    DebugLog.log(f"Failed to create pricing service: {e}")
                    self.call_from_thread(lambda: instance_list.mark_pricing_loading(False))
                    return
                
                total_to_fetch = len(self.instance_types)
                DebugLog.log(f"Fetching on-demand prices for {total_to_fetch} instance types using parallel requests")
                DebugLog.log("Note: Spot prices will be fetched on-demand when viewing instance details")
                
                # Create a function to fetch on-demand price for a single instance type
                def fetch_on_demand_price(instance_type_obj):
                    """Fetch on-demand price for a single instance type with retry logic"""
                    if self._shutting_down:
                        return None, None
                    try:
                        # Add small delay to avoid rate limiting (spread out requests)
                        import time
                        time.sleep(0.1)  # 100ms delay between requests
                        
                        # get_on_demand_price already has retry logic built in
                        on_demand = pricing_service.get_on_demand_price(
                            instance_type_obj.instance_type,
                            self.current_region,
                            max_retries=5  # More retries for parallel requests
                        )
                        if on_demand is None:
                            DebugLog.log(f"Could not fetch price for {instance_type_obj.instance_type} in {self.current_region} - may not be available in this region")
                        return instance_type_obj.instance_type, on_demand
                    except Exception as e:
                        DebugLog.log(f"Error fetching on-demand price for {instance_type_obj.instance_type}: {e}")
                        import traceback
                        DebugLog.log(f"Traceback: {traceback.format_exc()}")
                        return instance_type_obj.instance_type, None
                
                # Fetch on-demand prices in parallel using thread pool
                # Use a conservative concurrency limit to avoid rate limiting
                # AWS Pricing API has strict rate limits
                max_workers = 5  # Reduced further to avoid rate limits
                completed_count = 0
                failed_instances = []  # Track failed instances for retry
                
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    # Submit all on-demand price fetches
                    future_to_instance = {
                        executor.submit(fetch_on_demand_price, inst): inst
                        for inst in self.instance_types
                    }
                    
                    # Process completed futures
                    for future in as_completed(future_to_instance):
                        if self._shutting_down:
                            DebugLog.log("Pricing worker cancelled - app shutting down")
                            # Cancel remaining futures
                            for f in future_to_instance:
                                f.cancel()
                            break
                        
                        try:
                            instance_type_name, on_demand_price = future.result()
                            # Find the instance type object and update it
                            instance_type = next(
                                (inst for inst in self.instance_types 
                                 if inst.instance_type == instance_type_name),
                                None
                            )
                            
                            if instance_type:
                                from src.models.instance_type import PricingInfo
                                # Only set on-demand price initially; spot prices fetched on-demand when viewing details
                                instance_type.pricing = PricingInfo(
                                    on_demand_price=on_demand_price,
                                    spot_price=None  # Will be fetched when viewing instance detail
                                )
                                
                                if on_demand_price is None:
                                    # Track failed instances for retry
                                    failed_instances.append(instance_type)
                                else:
                                    completed_count += 1
                                
                                # Update UI every 5 instances or when complete (more frequent updates)
                                if (completed_count + len(failed_instances)) % 5 == 0 or (completed_count + len(failed_instances)) == total_to_fetch:
                                    def update_progress():
                                        try:
                                            instance_list.update_pricing_progress()
                                        except Exception as e:
                                            DebugLog.log(f"Error updating pricing progress: {e}")
                                    self.call_from_thread(update_progress)
                        except Exception as e:
                            DebugLog.log(f"Error processing pricing result: {e}")
                            # Track which instance failed
                            instance_obj = future_to_instance.get(future)
                            if instance_obj:
                                failed_instances.append(instance_obj)
                
                # Retry failed instances with more conservative settings
                if failed_instances and not self._shutting_down:
                    DebugLog.log(f"Retrying {len(failed_instances)} failed pricing requests with reduced concurrency")
                    max_workers_retry = 2  # Very conservative for retries to avoid rate limits
                    
                    with ThreadPoolExecutor(max_workers=max_workers_retry) as executor:
                        retry_futures = {
                            executor.submit(fetch_on_demand_price, inst): inst
                            for inst in failed_instances
                        }
                        
                        for future in as_completed(retry_futures):
                            if self._shutting_down:
                                break
                            
                            try:
                                instance_type_name, on_demand_price = future.result()
                                instance_type = next(
                                    (inst for inst in failed_instances 
                                     if inst.instance_type == instance_type_name),
                                    None
                                )
                                
                                if instance_type and on_demand_price is not None:
                                    # Update pricing if we got it this time
                                    if instance_type.pricing:
                                        instance_type.pricing.on_demand_price = on_demand_price
                                    else:
                                        from src.models.instance_type import PricingInfo
                                        instance_type.pricing = PricingInfo(
                                            on_demand_price=on_demand_price,
                                            spot_price=None  # Will be fetched when viewing instance detail
                                        )
                                    completed_count += 1
                                    
                                    def update_progress():
                                        try:
                                            instance_list.update_pricing_progress()
                                        except Exception:
                                            pass
                                    self.call_from_thread(update_progress)
                            except Exception as e:
                                instance_obj = retry_futures.get(future)
                                inst_name = instance_obj.instance_type if instance_obj else "unknown"
                                DebugLog.log(f"Error in retry for {inst_name}: {e}")
                
                # Mark pricing as done and final update
                pricing_loaded_count = sum(
                    1 for inst in self.instance_types
                    if inst.pricing and inst.pricing.on_demand_price is not None
                )
                total_count = len(self.instance_types)
                DebugLog.log(f"Pricing fetch completed: {pricing_loaded_count}/{total_count} instance types have pricing data")
                
                def mark_done():
                    try:
                        instance_list.mark_pricing_loading(False)
                    except Exception as e:
                        DebugLog.log(f"Error marking pricing as done: {e}")
                self.call_from_thread(mark_done)
            except Exception as e:
                DebugLog.log(f"Error fetching pricing: {e}")
                import traceback
                DebugLog.log(f"Traceback: {traceback.format_exc()}")
                # Mark pricing as done even on error
                def mark_done_error():
                    try:
                        instance_list.mark_pricing_loading(False)
                    except Exception:
                        pass
                self.call_from_thread(mark_done_error)
        
        # Run pricing fetch in background
        DebugLog.log("Starting pricing worker")
        worker = self.run_worker(
            pricing_worker,
            name="fetch_pricing",
            description="Fetching EC2 instance pricing",
            thread=True,
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
        self.region = region
        self.status_text = "Initializing..."
        self.app_ref = app

    def compose(self) -> ComposeResult:
        """Compose the loading screen - keep it simple"""
        DebugLog.log("LoadingScreen.compose() called")
        yield Static("Loading instance types...", id="loading-text")
        yield Static("Please wait...", id="loading-subtext")
        if self.region:
            yield Static(f"Region: {self.region}", id="loading-region")
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

