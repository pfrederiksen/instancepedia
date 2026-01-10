# Architecture

This document describes the architecture of instancepedia, including the dual-mode design, core services, TUI architecture, data models, and configuration.

## Dual-Mode Design

The application supports two distinct modes that share core services but have separate interfaces:

1. **TUI Mode** (`src/app.py`, `src/ui/`): Interactive Textual-based interface
2. **CLI Mode** (`src/cli/`): Headless command-line interface for scripting

Entry point (`src/main.py`) routes to TUI or CLI based on arguments.

## Core Services Layer

Services are shared between TUI and CLI modes:

- **`src/services/aws_client.py`**: Synchronous boto3 wrapper for CLI mode
- **`src/services/async_aws_client.py`**: Async aioboto3 wrapper for TUI mode (uses `run_worker()`)
- **`src/services/pricing_service.py`**: Synchronous pricing fetching (CLI)
- **`src/services/async_pricing_service.py`**: Async pricing with batch fetching and callbacks (TUI)
- **`src/services/instance_service.py`**: Instance type fetching and filtering
- **`src/services/free_tier_service.py`**: Free tier eligibility checking
- **`src/services/filter_service.py`**: Unified filtering logic for both TUI and CLI
- **`src/services/filter_preset_service.py`**: Filter preset management

**Important**: TUI uses async services with aioboto3, CLI uses sync services with boto3.

## TUI Architecture (Textual Framework)

The TUI is built with Textual and follows a screen-based navigation pattern:

1. **`src/app.py`** - Main app (`InstancepediaApp`) with screens:
   - `LoadingScreen` - Initial region/instance loading
   - `ErrorScreen` - Error display
   - Pushes `RegionSelector` on mount

2. **`src/ui/region_selector.py`** - Region selection screen
   - On selection, pushes `InstanceList` screen

3. **`src/ui/instance_list.py`** - Hierarchical tree view
   - Categories → Families → Instance Types
   - Background pricing fetch using async workers
   - Uses callbacks to update UI (`call_later()` for thread-safe updates)
   - On instance selection, pushes `InstanceDetail` screen

4. **`src/ui/instance_detail.py`** - Detailed instance view
   - Shows compute, memory, network, storage, pricing
   - Fetches spot price in background if not loaded

### Async Pricing Pattern (TUI)

When fetching pricing in TUI mode:

1. Use `self.app.run_worker(async_function)` to run async code
2. Use `price_callback` to update instances immediately as prices arrive
3. Use `progress_callback` with `self.call_later()` to schedule UI updates on main thread
4. Instance updates must happen BEFORE progress callback (for accurate counts)

Example from `src/app.py`:
```python
def on_price(inst_type_name: str, price: Optional[float]):
    inst = instance_map.get(inst_type_name)
    if inst:
        inst.pricing = PricingInfo(on_demand_price=price, spot_price=None)

def on_progress(completed: int, total: int):
    if completed % 10 == 0 or completed == total:
        def do_update():
            instance_list.update_pricing_progress()
        self.call_later(do_update)  # Thread-safe UI update

await pricing_service.get_on_demand_prices_batch(
    instance_types=types,
    region=region,
    price_callback=on_price,      # Updates instances first
    progress_callback=on_progress  # Updates UI after
)
```

### Tree State Preservation

The instance list uses a hierarchical tree with categories and families. To prevent UI flicker during pricing updates:

1. Expanded state is captured before rebuilding tree
2. Tree is rebuilt with new data
3. Expanded state is restored after rebuild
4. Updates are throttled (every 10 prices) to minimize rebuilds

### Lazy Loading for Large Instance Lists

The tree uses lazy loading to improve performance with large instance lists (500+ instances):
- Category and family nodes are created immediately
- Instance leaves are only added when a family node is first expanded
- `_family_instances` dict stores instances per family for deferred loading
- `_populated_families` set tracks which families have been populated
- `_populate_family_instances()` method adds instance leaves on first expansion
- Expanded state is preserved across tree rebuilds during pricing updates

## Data Models (Pydantic)

Located in `src/models/`:
- **`instance_type.py`**: `InstanceType` with nested models (`VCpuInfo`, `MemoryInfo`, `NetworkInfo`, `ProcessorInfo`, `EbsInfo`, `PricingInfo`, `GpuInfo`)
- **`region.py`**: `Region` model
- **`free_tier.py`**: `FreeTierInfo` model

Models use Pydantic v2 for validation and serialization.

### NetworkInfo Enhancements

- `baseline_bandwidth_in_gbps` - Baseline network bandwidth from AWS NetworkCards
- `peak_bandwidth_in_gbps` - Peak/burst network bandwidth from AWS NetworkCards
- `format_bandwidth()` - Formats bandwidth as human-readable string (e.g., "0.781-12.5 Gbps (baseline-peak)")
- Bandwidth is summed across multiple network cards for multi-card instances

### InstanceType Enhancements

- `generation` property - Extracts generation number from instance type name (e.g., "m6i" → 6)
- `generation_label` property - Formats generation as human-readable label (e.g., "6th gen", "3rd gen")
- Uses regex pattern matching to extract generation: `[a-z]+(\d+)`

### GpuInfo Enhancements

- `is_fractional_gpu` property - Detects fractional/shared GPU instances (count=0 but memory>0)
- `gpu_description` property - Human-readable GPU description
- Handles AWS API quirk where g6f instances report Count=0 despite having GPU memory
- Fractional GPUs displayed as "Shared {gpu_name} ({memory}GB)"
- Regular GPUs displayed as "{count}x {gpu_name} ({memory}GB)"
- Special handling in TUI and CLI output for fractional GPU instances

### PricingInfo Enhancements

**Savings Plans:**
- `savings_plan_1yr_no_upfront` - 1-year savings plan pricing (no upfront payment)
- `savings_plan_3yr_no_upfront` - 3-year savings plan pricing (no upfront payment)
- `format_savings_plan_1yr()` / `format_savings_plan_3yr()` - Format savings plan prices

**Reserved Instances:**
- 6 RI fields for all payment options:
  - `ri_1yr_no_upfront`, `ri_1yr_partial_upfront`, `ri_1yr_all_upfront`
  - `ri_3yr_no_upfront`, `ri_3yr_partial_upfront`, `ri_3yr_all_upfront`
- Format methods: `format_ri_1yr_no_upfront()`, etc.

**Calculations:**
- `calculate_savings_percentage(price_type)` - Calculate savings vs on-demand (supports "1yr", "3yr", "spot", and all RI types)

**Fetching:**
- TUI: Fetched in background when viewing instance detail (like spot pricing)
- CLI: Fetched with `--include-pricing` flag in `show` and `pricing` commands

## Configuration

**`src/config/settings.py`**: Uses `pydantic-settings` with custom TOML config source.

### Settings Precedence

(highest to lowest):
1. Init settings (passed to constructor)
2. Environment variables (`INSTANCEPEDIA_*`)
3. TOML config file (`~/.instancepedia/config.toml`)
4. Default values

### Config File Support

- Location: `~/.instancepedia/config.toml`
- Uses `tomllib` (Python 3.11+) or `tomli` (Python 3.9-3.10)
- Silent error handling for config file issues
- `TomlConfigSettingsSource` custom pydantic settings source
- `create_default_config()` generates example config content

### AWS Configuration

- `aws_region` / `INSTANCEPEDIA_AWS_REGION` - Default region
- `aws_profile` / `INSTANCEPEDIA_AWS_PROFILE` - AWS profile

### Timeout Configuration

- `aws_connect_timeout` / `INSTANCEPEDIA_AWS_CONNECT_TIMEOUT` - Connection timeout (default: 10s)
- `aws_read_timeout` / `INSTANCEPEDIA_AWS_READ_TIMEOUT` - Read timeout for AWS APIs (default: 60s)
- `pricing_read_timeout` / `INSTANCEPEDIA_PRICING_READ_TIMEOUT` - Read timeout for Pricing API (default: 90s)

### Performance Configuration

- `pricing_concurrency` / `INSTANCEPEDIA_PRICING_CONCURRENCY` - Max concurrent pricing requests in TUI mode (default: 10)
- `pricing_retry_concurrency` / `INSTANCEPEDIA_PRICING_RETRY_CONCURRENCY` - Max concurrent requests for retries (default: 3)
- `cli_pricing_concurrency` / `INSTANCEPEDIA_CLI_PRICING_CONCURRENCY` - Max concurrent pricing requests in CLI mode (default: 5)
- `pricing_request_delay_ms` / `INSTANCEPEDIA_PRICING_REQUEST_DELAY_MS` - Delay between requests in milliseconds (default: 50)
- `spot_batch_size` / `INSTANCEPEDIA_SPOT_BATCH_SIZE` - Instance types per spot price API call (default: 50)
- `ui_update_throttle` / `INSTANCEPEDIA_UI_UPDATE_THROTTLE` - Update TUI every N pricing updates (default: 10)
- `max_pool_connections` / `INSTANCEPEDIA_MAX_POOL_CONNECTIONS` - Max connections in HTTP connection pool (default: 50)

### TUI Configuration

- `vim_keys` / `INSTANCEPEDIA_VIM_KEYS` - Enable vim-style navigation hjkl (default: false)

### Vim-Style Navigation

When `vim_keys = true` in config (or `INSTANCEPEDIA_VIM_KEYS=true`), enables:
- `j` - Move cursor down (same as ↓)
- `k` - Move cursor up (same as ↑)
- `h` - Collapse node or go to parent
- `l` - Expand node or enter detail view (same as Enter on leaf)

Implementation in `src/ui/instance_list.py` - `on_key()` method checks `self._settings.vim_keys` before processing hjkl keys.

## Debug Mode

Debug mode shows a scrolling pane at the bottom of TUI:
- Enable with `--debug` flag
- Uses `DebugLog.log()` throughout codebase
- Display controlled by `DebugPane` widget in `src/debug.py`
