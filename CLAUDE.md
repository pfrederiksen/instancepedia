# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Documentation Maintenance - CRITICAL

**ALWAYS update documentation when making changes!** This is non-negotiable for project maintainability.

### When to Update CLAUDE.md

Update `CLAUDE.md` when you:
- Add new architectural patterns or best practices
- Create new services or core components
- Discover bugs or issues to avoid
- Add new testing patterns
- Change how async/threading works
- Modify the TUI or CLI architecture
- Add configuration options (timeouts, settings, etc.)
- Learn something important about the codebase
- Add new AWS client features or error handling

**Examples**: New AWS client features, error handling patterns, caching mechanisms, testing strategies.

### When to Update README.md

Update `README.md` when you:
- Add new CLI commands or flags
- Add new TUI features or keyboard shortcuts
- Change installation or setup instructions
- Add new environment variables
- Modify configuration options users can set
- Add new features users will interact with
- Change how the application works from a user perspective
- Add new dependencies or requirements

**Examples**: New `cache clear` command, timeout configuration via env vars, new filters, new output formats.

### When to Update CONTRIBUTING.md

Update `CONTRIBUTING.md` when you:
- Change development setup process
- Add new coding standards or conventions
- Modify testing requirements or patterns
- Change the PR process or template
- Add new project structure or components
- Update contribution workflow

### When to Update TROUBLESHOOTING.md

Update `TROUBLESHOOTING.md` when you:
- Discover new common issues and solutions
- Find better solutions to existing problems
- Add new platform-specific guidance
- Update debug commands or procedures
- Add new error messages and their resolutions

### How to Update Documentation

**CRITICAL**: After ANY feature addition, bug fix, or change, review ALL documentation files (.md files) to ensure they're updated.

**All Documentation Files to Consider**:
- `README.md` - User-facing documentation
- `CLAUDE.md` - Developer/architecture documentation
- `CONTRIBUTING.md` - Contributor guidelines
- `TROUBLESHOOTING.md` - Common issues and solutions

**Documentation Update Process**:
1. **Make code changes first**
2. **Review ALL .md files** - determine which need updates based on your changes
3. **Update documentation in the SAME commit/PR** - never defer documentation to later
4. **Be specific** - include examples, code snippets, and clear explanations
5. **Update multiple files if needed** - features often require updates to both README.md (user docs) and CLAUDE.md (developer docs)
6. **Test your examples** - ensure code snippets and commands actually work

**Bad Practice**:
```
# Commit: Add timeout configuration
- Changes: Added timeout settings to AWSClient
- Documentation: None (will do later) ❌
```

**Good Practice**:
```
# Commit: Add timeout configuration
- Changes: Added timeout settings to AWSClient
- Documentation:
  - CLAUDE.md: Added AWS Client Configuration section with implementation details
  - README.md: Added environment variables section with examples ✅
```

## Project Overview

Instancepedia is an EC2 Instance Type Browser with both TUI (Terminal User Interface) and CLI (Command-Line Interface) modes. It provides detailed EC2 instance information, pricing (on-demand and spot), and free tier eligibility indicators.

### Documentation Structure

The project has comprehensive documentation for both users and developers:

- **README.md** - Main user-facing documentation with installation, usage, features, and examples
- **CLAUDE.md** - Developer documentation with architecture, patterns, and implementation details
- **CONTRIBUTING.md** - Contributor guidelines with setup, coding standards, and PR process
- **TROUBLESHOOTING.md** - Common issues and solutions organized by category
- **Use Cases** (in README.md) - Real-world scenarios with both TUI and CLI approaches

## CLI Commands

The CLI provides the following commands for users:

- `list` - List instance types with filtering
- `show` - Show detailed info for a specific instance type
- `search` - Search for instance types by name
- `pricing` - Get pricing information for an instance type
- `regions` - List available AWS regions
- `compare` - Compare two instance types side-by-side
- `cost-estimate` - Calculate cost estimates with different usage patterns
- `compare-regions` - Compare pricing across multiple regions
- `compare-family` - Compare all instances within a family
- `presets list` - List available filter presets (built-in and custom)
- `presets apply` - Apply a filter preset to list instances
- `cache stats` - Show cache statistics
- `cache clear` - Clear cache entries
- `spot-history` - Show historical spot price trends with statistics and volatility analysis

### Filter Presets

Filter presets allow users to quickly apply common filtering scenarios. Built-in presets include:
- `web-server` - 4+ vCPU, 8+ GB RAM, current generation
- `database` - Memory-optimized, 8+ vCPU, 32+ GB RAM
- `compute-intensive` - Compute-optimized, 16+ vCPU
- `gpu-ml` - GPU instances for machine learning
- `arm-graviton` - ARM-based instances
- `burstable` - T-series burstable instances
- `free-tier` - Free tier eligible instances
- `small-dev` - Small instances for development (1-2 vCPU, up to 4 GB RAM)

Presets are defined in `src/services/filter_preset_service.py` and stored in `~/.instancepedia/presets/filter_presets.json` for custom presets.

### Storage Filters

Storage-focused filtering allows users to find instances based on storage characteristics:

**Filter Options**:
- **Storage Type**:
  - `ebs_only` (TUI) / `ebs-only` (CLI): Instances with EBS-only storage (no instance store)
  - `has_instance_store` (TUI) / `instance-store` (CLI): Instances with attached instance store volumes

- **NVMe Support**:
  - `required`: Instances that require NVMe (high-performance instance store)
  - `supported`: Instances that support NVMe
  - `unsupported`: Instances without NVMe support

**Implementation** (`src/ui/filter_modal.py`, `src/ui/instance_list.py`):
- Added `storage_type` and `nvme_support` fields to `FilterCriteria`
- Storage type filter checks `instance_storage_info.total_size_in_gb`
- NVMe filter checks `instance_storage_info.nvme_support`
- Filters applied in `_apply_filters()` method

### Advanced Filtering

Advanced filtering options provide fine-grained control over instance selection:

**Processor Family Filter**:
- **Intel**: Filters to Intel processors (excludes AMD and Graviton)
- **AMD**: Filters to AMD processors (instances with 'a' suffix, e.g., m5a, c5a, r5a)
- **Graviton**: Filters to AWS Graviton ARM processors (arm64 architecture)
- TUI: Processor Family dropdown in filter modal
- CLI: `--processor-family {intel,amd,graviton}`

**Network Performance Filter**:
- **Low**: Up to 5 Gigabit network performance
- **Moderate**: 10-12 Gigabit network performance
- **High**: 10-25 Gigabit network performance
- **Very High**: 50+ Gigabit network performance
- TUI: Network Performance dropdown in filter modal
- CLI: `--network-performance {low,moderate,high,very-high}`

**Price Range Filter**:
- **Min Price**: Minimum hourly on-demand price in USD
- **Max Price**: Maximum hourly on-demand price in USD
- Only filters instances with pricing data loaded
- Instances without pricing are kept (not filtered out)
- TUI: Price Range input fields in filter modal
- CLI: `--min-price <float> --max-price <float>`

**Implementation** (`src/ui/filter_modal.py`, `src/ui/instance_list.py`, `src/cli/commands.py`):
- Added `processor_family`, `network_performance`, `min_price`, `max_price` to `FilterCriteria`
- Processor family uses heuristics (AMD has 'a' suffix, Graviton has arm64 arch)
- Network performance maps to keyword patterns in `network_info.network_performance`
- Price filter applied after pricing fetch in CLI, immediately in TUI
- All filters work in both TUI (filter modal) and CLI (command-line arguments)

**CLI Integration** (`src/cli/parser.py`, `src/cli/commands.py`):
- `--storage-type` argument: `ebs-only` or `instance-store`
- `--nvme` argument: `required`, `supported`, or `unsupported`
- Available for both `list` and `search` commands

**TUI Display** (`src/ui/instance_list.py`):
- Instance storage shown in list view (e.g., "150GB NVMe")
- Storage size displayed when available
- NVMe indicator added for NVMe-required instances
- Format: `{size}GB{" NVMe" if required}`

### EBS Recommendations

The `EbsRecommendationService` provides volume type recommendations based on instance EBS capabilities:
- Analyzes instance EBS optimization level and throughput
- Recommends appropriate volume types (gp3, io2, st1, etc.)
- Shows IOPS ranges, throughput specs, and use cases
- Integrated into both TUI instance detail and CLI `show` command

### Spot Price History

The spot price history feature (`spot-history` command) provides historical analysis of spot pricing trends:

**Implementation** (`src/services/pricing_service.py`):
- `SpotPriceHistory` dataclass stores price statistics and metadata
- `get_spot_price_history()` method fetches and analyzes historical data
- Uses AWS EC2 `describe-spot-price-history` API (free, no CloudWatch charges)
- Filters by product description: `Linux/UNIX` (most common)

**Statistical Analysis**:
- Current, minimum, maximum, average, median prices
- Standard deviation for volatility measurement
- Volatility percentage: `(std_dev / avg) * 100`
- Stability ratings based on volatility thresholds:
  - Very Stable: < 5%
  - Stable: 5-15%
  - Moderate: 15-30%
  - Volatile: 30-50%
  - Highly Volatile: > 50%

**Visualization**:
- Text-based bar chart using Unicode characters (█)
- Shows last 10 data points for trend visualization
- Bar lengths proportional to price values
- Includes price labels for clarity

**CLI Integration** (`src/cli/commands.py`):
- `cmd_spot_history()` handler with table and JSON output formats
- `--days` argument for customizable time periods (default: 30 days)
- Graceful error handling for regions/instances without spot pricing

**TUI Integration** (`src/ui/instance_detail.py`):
- Reference message in instance detail pricing section
- Directs users to CLI command for full analysis

All commands are implemented in `src/cli/commands.py` with argument parsing in `src/cli/parser.py`.

### Reserved Instance Pricing

The Reserved Instance (RI) pricing feature provides comprehensive pricing for Standard Reserved Instances with all payment options:

**Implementation** (`src/services/pricing_service.py`, `src/services/async_pricing_service.py`):
- `get_reserved_instance_price(instance_type, region, lease_length, payment_option)` method
- Supports lease lengths: `"1yr"`, `"3yr"`
- Supports payment options: `"no_upfront"`, `"partial_upfront"`, `"all_upfront"`
- Filters for Standard RIs only (excludes Convertible RIs via `OfferingClass='standard'`)
- Uses AWS Pricing API Reserved terms
- Cache keys: `ri_{lease}_{payment_option}` (e.g., `ri_1yr_partial_upfront`)

**Data Model** (`src/models/instance_type.py`):
- `PricingInfo` dataclass has 6 RI fields:
  - `ri_1yr_no_upfront`, `ri_1yr_partial_upfront`, `ri_1yr_all_upfront`
  - `ri_3yr_no_upfront`, `ri_3yr_partial_upfront`, `ri_3yr_all_upfront`
- Format methods: `format_ri_1yr_no_upfront()`, etc.
- `calculate_savings_percentage()` supports all RI price types

**AWS API Details**:
- Uses same filters as Savings Plans (ServiceCode, location, instanceType, tenancy, OS, etc.)
- Term matching logic:
  ```python
  if (lease_contract_length == api_lease and
      purchase_option == api_payment and
      offering_class == 'standard'):
      # Extract hourly price
  ```
- Payment option mapping:
  ```python
  {
      "no_upfront": "No Upfront",
      "partial_upfront": "Partial Upfront",
      "all_upfront": "All Upfront"
  }
  ```

**Pricing Display**:
- AWS returns effective hourly rates (upfront costs are amortized over the term)
- Displayed as-is with note: "* Effective hourly rate (includes prorated upfront payment)"
- Example: 1-year Partial Upfront at $500 upfront + $0.005/hr = $0.0622/hr effective rate

**TUI Integration** (`src/ui/instance_detail.py`):
- Display all 6 RI options in instance detail view
- Grouped by term (1-Year section, 3-Year section)
- Shows savings percentages vs on-demand
- Fetched in background via `_fetch_pricing_if_needed()`
- Proper cleanup: `on_unmount()` cancels pricing worker and closes async client

**CLI Integration** (`src/cli/commands.py`, `src/cli/output.py`):
- Fetched in `cmd_show()` when `--include-pricing` flag is used
- TableFormatter displays RI sections with savings percentages
- JSONFormatter includes nested `reserved_instances` object:
  ```json
  "reserved_instances": {
    "1yr": {
      "no_upfront": 0.0600,
      "partial_upfront": 0.0290,
      "all_upfront": null
    },
    "3yr": {
      "no_upfront": 0.0410,
      "partial_upfront": 0.0190,
      "all_upfront": null
    }
  }
  ```

**Cache Behavior**:
- Each RI price type cached separately
- TTL: 4 hours (same as other pricing)
- Cache miss returns None (common for unavailable RI pricing)
- Caches both successful lookups and None values

**Error Handling**:
- Logs at debug level (not error) for missing RI pricing (common scenario)
- Graceful degradation - shows "N/A" for unavailable prices
- Same retry logic as Savings Plans (exponential backoff on throttling)

**Example Output**:
```
Reserved Instances (Standard, 1-Year):
  No Upfront: $0.0600/hr (37.5% savings)
  Partial Upfront: $0.0290/hr (69.8% savings) *
  All Upfront: N/A

Reserved Instances (Standard, 3-Year):
  No Upfront: $0.0410/hr (57.3% savings)
  Partial Upfront: $0.0190/hr (80.2% savings) *
  All Upfront: N/A

* Effective hourly rate (includes prorated upfront payment)
```

## Common Commands

### Development Setup
```bash
# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Activate virtual environment (if needed)
source venv/bin/activate

# Run the application in TUI mode
instancepedia --tui

# Run with debug mode
instancepedia --tui --debug

# Run in development mode without installing
python -m src.main
```

### Testing
```bash
# Run all tests (both CLI and TUI tests)
pytest

# Run specific test file
pytest tests/test_tui_instance_list.py
pytest tests/test_cli_commands.py

# Run with verbose output
pytest -v

# Run single test by name
pytest tests/test_tui_instance_list.py::TestInstanceList::test_instance_list_displays
```

### Release and Publishing
```bash
# Create a new release (patch/minor/major)
# Note: release.sh requires confirmation - use echo "y" to auto-confirm
echo "y" | ./scripts/release.sh patch    # 0.2.2 -> 0.2.3
echo "y" | ./scripts/release.sh minor    # 0.2.2 -> 0.3.0
echo "y" | ./scripts/release.sh major    # 0.2.2 -> 1.0.0

# Build package
python3 -m build

# Publish to PyPI
./scripts/publish.sh testpypi  # Test first
./scripts/publish.sh pypi      # Production
```

## Architecture

### Dual-Mode Design

The application supports two distinct modes that share core services but have separate interfaces:

1. **TUI Mode** (`src/app.py`, `src/ui/`): Interactive Textual-based interface
2. **CLI Mode** (`src/cli/`): Headless command-line interface for scripting

Entry point (`src/main.py`) routes to TUI or CLI based on arguments.

### Core Services Layer

Services are shared between TUI and CLI modes:

- **`src/services/aws_client.py`**: Synchronous boto3 wrapper for CLI mode
- **`src/services/async_aws_client.py`**: Async aioboto3 wrapper for TUI mode (uses `run_worker()`)
- **`src/services/pricing_service.py`**: Synchronous pricing fetching (CLI)
- **`src/services/async_pricing_service.py`**: Async pricing with batch fetching and callbacks (TUI)
- **`src/services/instance_service.py`**: Instance type fetching and filtering
- **`src/services/free_tier_service.py`**: Free tier eligibility checking

**Important**: TUI uses async services with aioboto3, CLI uses sync services with boto3.

### TUI Architecture (Textual Framework)

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

### Testing

Tests use mocking to avoid requiring AWS credentials:

- **TUI tests** (`tests/test_tui_*.py`): Use Textual's `app.run_test()` async context
  - Use `await pilot.pause()` for UI updates
  - Use `await asyncio.sleep(0.3)` to wait for timers (e.g., `set_timer(0.2)`)
  - Test helper apps named `*TestApp` to avoid pytest collection warnings

- **CLI tests** (`tests/test_cli_*.py`): Use `@patch` decorators for boto3 mocking
  - Mock `boto3.client()` for synchronous services

### Data Models (Pydantic)

Located in `src/models/`:
- **`instance_type.py`**: `InstanceType` with nested models (`VCpuInfo`, `MemoryInfo`, `NetworkInfo`, `ProcessorInfo`, `EbsInfo`, `PricingInfo`)
- **`region.py`**: `Region` model
- **`free_tier.py`**: `FreeTierInfo` model

Models use Pydantic v2 for validation and serialization.

**NetworkInfo enhancements**:
- `baseline_bandwidth_in_gbps` - Baseline network bandwidth from AWS NetworkCards
- `peak_bandwidth_in_gbps` - Peak/burst network bandwidth from AWS NetworkCards
- `format_bandwidth()` - Formats bandwidth as human-readable string (e.g., "0.781-12.5 Gbps (baseline-peak)")
- Bandwidth is summed across multiple network cards for multi-card instances

**InstanceType enhancements**:
- `generation` property - Extracts generation number from instance type name (e.g., "m6i" → 6)
- `generation_label` property - Formats generation as human-readable label (e.g., "6th gen", "3rd gen")
- Uses regex pattern matching to extract generation: `[a-z]+(\d+)`

**GpuInfo enhancements**:
- `is_fractional_gpu` property - Detects fractional/shared GPU instances (count=0 but memory>0)
- `gpu_description` property - Human-readable GPU description
- Handles AWS API quirk where g6f instances report Count=0 despite having GPU memory
- Fractional GPUs displayed as "Shared {gpu_name} ({memory}GB)"
- Regular GPUs displayed as "{count}x {gpu_name} ({memory}GB)"
- Special handling in TUI and CLI output for fractional GPU instances

**PricingInfo enhancements**:
- `savings_plan_1yr_no_upfront` - 1-year savings plan pricing (no upfront payment)
- `savings_plan_3yr_no_upfront` - 3-year savings plan pricing (no upfront payment)
- `format_savings_plan_1yr()` / `format_savings_plan_3yr()` - Format savings plan prices
- `calculate_savings_percentage(price_type)` - Calculate savings vs on-demand (supports "1yr", "3yr", "spot")
- Savings plans pricing fetched from AWS Pricing API (Reserved terms with "No Upfront" purchase option)
- TUI: Fetched in background when viewing instance detail (like spot pricing)
- CLI: Fetched with `--include-pricing` flag in `show` and `pricing` commands

### Configuration

**`src/config/settings.py`**: Uses `pydantic-settings` for environment-based config:

**AWS Configuration:**
- `INSTANCEPEDIA_AWS_REGION` - Default region
- `INSTANCEPEDIA_AWS_PROFILE` - AWS profile

**Timeout Configuration:**
- `INSTANCEPEDIA_AWS_CONNECT_TIMEOUT` - Connection timeout (default: 10s)
- `INSTANCEPEDIA_AWS_READ_TIMEOUT` - Read timeout for AWS APIs (default: 60s)
- `INSTANCEPEDIA_PRICING_READ_TIMEOUT` - Read timeout for Pricing API (default: 90s)

**Performance Configuration:**
- `INSTANCEPEDIA_PRICING_CONCURRENCY` - Max concurrent pricing requests in TUI mode (default: 10)
- `INSTANCEPEDIA_PRICING_RETRY_CONCURRENCY` - Max concurrent requests for retries (default: 3)
- `INSTANCEPEDIA_CLI_PRICING_CONCURRENCY` - Max concurrent pricing requests in CLI mode (default: 5)
- `INSTANCEPEDIA_PRICING_REQUEST_DELAY_MS` - Delay between requests in milliseconds (default: 50)
- `INSTANCEPEDIA_SPOT_BATCH_SIZE` - Instance types per spot price API call (default: 50)
- `INSTANCEPEDIA_UI_UPDATE_THROTTLE` - Update TUI every N pricing updates (default: 10)
- `INSTANCEPEDIA_MAX_POOL_CONNECTIONS` - Max connections in HTTP connection pool (default: 50)

All settings are configurable via environment variables with the `INSTANCEPEDIA_` prefix.

## Key Implementation Details

### Performance Optimization

The application supports fine-grained performance tuning via configuration settings:

**Concurrency Control:**
- **TUI Mode**: Uses `pricing_concurrency` (default: 10) for parallel pricing requests
- **CLI Mode**: Uses `cli_pricing_concurrency` (default: 5) to avoid overwhelming scripts
- **Retries**: Uses `pricing_retry_concurrency` (default: 3) for lower concurrency on failed requests
- All concurrency is managed via `asyncio.Semaphore` (TUI) or `ThreadPoolExecutor` (CLI)

**Request Throttling:**
- `pricing_request_delay_ms` controls delay between requests (default: 50ms)
- Helps avoid AWS API rate limiting
- Configurable per environment (faster for good networks, slower for rate-limited accounts)

**Batch Sizing:**
- `spot_batch_size` controls how many instance types are queried per EC2 API call (default: 50)
- EC2 API supports up to ~50 instance types per spot price history request
- Can be tuned based on API limits and network conditions

**UI Update Optimization:**
- `ui_update_throttle` controls how often the TUI updates during pricing fetch (default: every 10 prices)
- Reduces UI flicker and improves responsiveness
- Higher values for large instance lists, lower values for better progress visibility

**Performance Metrics:**
- Async pricing service logs timing and throughput metrics
- Logs: "Batch pricing fetch completed in Xs: Y/Z prices fetched (success rate)"
- Helps users tune performance settings for their environment

**Usage in Code:**
```python
# TUI (app.py)
await pricing_service.get_on_demand_prices_batch(
    instance_types,
    region,
    concurrency=self.settings.pricing_concurrency  # Configurable
)

# CLI (commands.py)
with ThreadPoolExecutor(max_workers=settings.cli_pricing_concurrency) as executor:
    # Parallel pricing fetch
```

**Tuning Recommendations:**
- **Fast network, no rate limits**: Increase concurrency to 15-20, reduce delay to 25-30ms, increase pool connections to 100
- **Rate-limited account**: Decrease concurrency to 5, increase delay to 100ms
- **Large instance lists (500+)**: Increase UI throttle to 20-50
- **CI/CD scripts**: Increase CLI concurrency to 10 for faster batch operations
- **High concurrency**: Set max_pool_connections ≥ pricing_concurrency for optimal performance

### Async Improvements and Connection Pooling

The async AWS client implementation uses connection pooling and proper resource management for improved performance and reliability:

**Connection Pooling:**
- `AsyncAWSClient` maintains a pool of HTTP connections (default: 50, configurable via `max_pool_connections`)
- Client instances are reused across multiple API calls instead of creating new ones each time
- Uses `asyncio.Lock` to ensure thread-safe client initialization and cleanup
- Pool size should match or exceed concurrency settings for optimal performance

**Resource Management:**
- `AsyncAWSClient` implements async context manager protocol (`__aenter__`/`__aexit__`)
- Proper cleanup with `close()` method that closes all client connections
- All pricing workers use `async with AsyncAWSClient(...)` for automatic resource cleanup
- On error, clients are closed and recreated to prevent connection leaks

**Client Reuse Pattern:**
```python
# In app.py - proper resource management
async with AsyncAWSClient(
    region,
    profile,
    connect_timeout=settings.aws_connect_timeout,
    read_timeout=settings.aws_read_timeout,
    pricing_timeout=settings.pricing_read_timeout,
    max_pool_connections=settings.max_pool_connections
) as async_client:
    pricing_service = AsyncPricingService(async_client, settings=settings)
    # Clients are reused for all pricing requests
    await pricing_service.get_on_demand_prices_batch(...)
    await pricing_service.get_on_demand_prices_batch(...)  # Reuses same client
# Context manager ensures proper cleanup
```

**Benefits:**
- **Performance**: Reusing connections eliminates handshake overhead
- **Reliability**: Automatic cleanup prevents connection leaks
- **Scalability**: Connection pooling handles high concurrency efficiently
- **Resource efficiency**: Fewer open connections to AWS APIs

**Implementation Details** (`src/services/async_aws_client.py`):
- EC2 and Pricing clients are lazy-initialized and cached
- `get_ec2_client()` and `get_pricing_client()` are async context managers that yield cached clients
- On error, cached clients are closed and will be recreated on next request
- All initialization is protected by `asyncio.Lock` for thread safety

### Pricing API Region Mapping

The AWS Pricing API requires location names (e.g., "US East (N. Virginia)") not region codes. See `REGION_MAP` in `src/services/async_pricing_service.py`.

Pricing API is only available in `us-east-1`, so pricing client always uses that region regardless of target region for instance types.

### Debug Mode

Debug mode shows a scrolling pane at the bottom of TUI:
- Enable with `--debug` flag
- Uses `DebugLog.log()` throughout codebase
- Display controlled by `DebugPane` widget in `src/debug.py`

### Git Configuration

Git user is configured as:
- Email: `paul@paulfrederiksen.com`
- Name: `Paul Frederiksen`

### Python Version

Requires Python >= 3.9 (for async features and type hints).

### Branch Workflow

- Main branch: `main`
- Feature branches: `feature/<name>` (e.g., `feature/async-boto3`)
- Fix branches: `fix/<name>` (e.g., `fix/p0-error-handling-and-tests`)
- Create branch before starting work
- Merge to main after testing

### Caching System

The pricing cache (`src/cache.py`) provides persistent storage for pricing data:

**Architecture**:
- File-based cache in `~/.instancepedia/cache/`
- Individual JSON files per cache entry: `{region}_{instance_type}_{price_type}.json`
- Default TTL: 4 hours (configurable)
- Thread-safe using `threading.Lock()`
- Caches both successful lookups AND None values (to avoid repeated failures)

**Usage**:
- Both sync (`PricingService`) and async (`AsyncPricingService`) use the same cache
- Cache is checked first before API calls
- Results (including None) are cached to reduce API calls
- Cache statistics: `cache.get_stats()` returns total/valid/expired entries, size, age
- Cache management: `cache.clear()` with optional filters (region, instance_type)

**Cache Key Format**:
- Dots replaced with underscores: `us-east-1_t3_micro_on_demand.json`
- Separate files for on_demand vs spot prices

**Thread Safety**:
- All operations use `self._lock` for thread safety
- Safe for concurrent access from TUI and CLI modes
- Tested with ThreadPoolExecutor for concurrent operations

### Logging System

The logging system (`src/logging_config.py`) provides structured logging:

**Setup**:
- Use `logging.getLogger("instancepedia")` at module level
- Import logging: `import logging` then `logger = logging.getLogger("instancepedia")`
- TUI mode: Logs go to debug pane only (no console handler)
- CLI mode: Logs go to stderr

**Log Levels**:
- `logger.debug()` - Verbose information, cache hits, UI state changes
- `logger.info()` - General information, operations completed
- `logger.warning()` - Unexpected but recoverable situations
- `logger.error()` - Errors that need attention

**Example**:
```python
import logging

logger = logging.getLogger("instancepedia")

try:
    result = some_operation()
except Exception as e:
    logger.error(f"Operation failed: {e}", exc_info=True)
```

## Error Handling Best Practices

### Exception Handling

**NEVER use bare `except:` blocks** - they hide errors and make debugging difficult.

**Good**:
```python
try:
    widget.update("status")
except Exception as e:
    # Explain WHY this exception is expected
    logger.debug(f"Widget may not exist during screen transition: {e}")
```

**Bad**:
```python
try:
    widget.update("status")
except:  # ❌ Bare except - hides all errors
    pass
```

**Pattern for expected exceptions**:
```python
try:
    # Operation that may fail for valid reasons
    self.screen.pop_screen()
except Exception as e:
    # Log at debug level with explanation of why it's expected
    logger.debug(f"Screen already popped or app shutting down: {e}")
```

**Pattern for unexpected exceptions**:
```python
try:
    # Critical operation that should succeed
    result = fetch_critical_data()
except Exception as e:
    # Log at error level with full traceback
    logger.error(f"Critical operation failed: {e}", exc_info=True)
    # Handle the error appropriately (return None, raise custom exception, etc.)
    return None
```

### Testing Services

When adding new services or modifying existing ones, always add comprehensive tests:

**PricingService Test Pattern** (`tests/test_pricing_service.py`):
```python
@pytest.fixture
def pricing_service(mock_aws_client):
    """Create PricingService with mocked dependencies"""
    with patch('src.services.pricing_service.get_pricing_cache') as mock_get_cache:
        mock_cache = Mock()
        mock_cache.get = Mock(return_value=None)  # Cache miss
        mock_cache.set = Mock()
        mock_get_cache.return_value = mock_cache

        service = PricingService(mock_aws_client, use_cache=True)
        service.cache = mock_cache  # Store reference for assertions
        return service

def test_cache_hit(pricing_service):
    """Test cache returns immediately without API call"""
    pricing_service.cache.get.return_value = 0.0104

    price = pricing_service.get_on_demand_price("t3.micro", "us-east-1")

    assert price == 0.0104
    pricing_service.cache.set.assert_not_called()  # No cache write on hit
```

**Cache Thread Safety Test Pattern** (`tests/test_cache.py`):
```python
def test_concurrent_writes(cache):
    """Test multiple threads writing to same key"""
    num_threads = 10

    def write_price(thread_id):
        price = 0.01 + (thread_id * 0.001)
        cache.set("us-east-1", "t3.micro", "on_demand", price)
        return price

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(write_price, i) for i in range(num_threads)]
        results = [f.result() for f in as_completed(futures)]

    # Verify no corruption - final value should be one of the written values
    final_price = cache.get("us-east-1", "t3.micro", "on_demand")
    assert final_price in results
```

## AWS Client Configuration

### Timeout Configuration

AWS API clients support configurable timeouts to handle slow networks and improve reliability:

**Settings** (`src/config/settings.py`):
```python
class Settings(BaseSettings):
    aws_connect_timeout: int = 10  # Connection timeout in seconds
    aws_read_timeout: int = 60     # Read timeout for AWS APIs
    pricing_read_timeout: int = 90  # Read timeout for Pricing API (slower)
```

**Environment Variables**:
- `INSTANCEPEDIA_AWS_CONNECT_TIMEOUT` - Connection timeout
- `INSTANCEPEDIA_AWS_READ_TIMEOUT` - AWS API read timeout
- `INSTANCEPEDIA_PRICING_READ_TIMEOUT` - Pricing API read timeout

**Implementation**:
- Both `AWSClient` and `AsyncAWSClient` accept timeout parameters
- All boto3/aioboto3 clients configured with `botocore.config.Config`:
  ```python
  config = Config(
      connect_timeout=connect_timeout,
      read_timeout=read_timeout,
      retries={'max_attempts': 3, 'mode': 'standard'}
  )
  ```
- Allows users to fail fast or wait longer based on environment

### Region-Specific Error Handling

Enhanced error handling for region-related issues provides clear, actionable error messages:

**Custom Exceptions** (`src/exceptions.py`):
- `AWSRegionError` - Invalid or inaccessible regions
- `AWSCredentialsError` - Missing or invalid credentials
- `AWSConnectionError` - Connection failures
- `InstanceTypeError` - Instance type fetch failures

**Error Detection**:
- Invalid region names → Suggests using `instancepedia regions`
- Regions not enabled → Explains opt-in requirement
- Authorization failures → Identifies permissions issues
- All errors include region context

**Example**:
```python
# Before
AWS API error (AuthFailure): You are not authorized...

# After
Not authorized to access EC2 in region 'ap-southeast-4'.
This region may not be enabled for your account or you may lack permissions.
Use 'instancepedia regions' to see available regions.
```

### Cache Management

Cache commands are available via CLI to view statistics and clear cached data:

**Commands**:
```bash
# View cache statistics
instancepedia cache stats
instancepedia cache stats --format json

# Clear all cache
instancepedia cache clear

# Clear by region
instancepedia cache clear --region us-east-1

# Clear by instance type
instancepedia cache clear --instance-type t3.micro

# Skip confirmation
instancepedia cache clear --force
```

**Implementation** (`src/cli/commands.py`):
- `cmd_cache_stats()` - Shows cache location, entries, size, age
- `cmd_cache_clear()` - Clears cache with optional filters and confirmation

**Cache Statistics Tracking**:
- Cache hit tracking occurs DURING pricing fetch, not after
- `AsyncPricingService` uses `cache_hit_callback` to count hits
- Statistics passed to `InstanceList` when pricing completes
- Prevents false reporting where all prices appear cached

## Known Issues to Avoid

### Textual `Screen.region` Property Conflict

Do NOT use `self.region` in Textual Screen subclasses - it conflicts with `Screen.region` property. Use `self._region` or another name.

### Binding Format

`BINDINGS` in Textual screens are tuples `(key, action, description)`, not `Binding` objects. Access with `b[0]`, `b[1]`, `b[2]`.

### Test Class Naming

Test helper/container classes should NOT start with `Test*` or pytest will try to collect them. Use `*TestApp` suffix instead.

### UI Updates from Async Workers

When updating UI from `run_worker()` async functions, use `self.call_later(callback)` to schedule on main thread. Do NOT call widget methods directly from worker thread.

### Missing Logger Import

If you add `logger.debug()` or other logging calls to a file, make sure the file has:

1. `import logging` at the top
2. `logger = logging.getLogger("instancepedia")` at module level (after imports)

**Example** (from `src/app.py`):
```python
"""Main application class"""

import asyncio
import logging  # ← Must import logging
from textual.app import App, ComposeResult
# ... other imports ...

logger = logging.getLogger("instancepedia")  # ← Create logger at module level


class InstancepediaApp(App):
    # Now can use logger anywhere in the class
    def some_method(self):
        logger.debug("Operation starting")
```

Without these, you'll get `NameError: name 'logger' is not defined` at runtime.
