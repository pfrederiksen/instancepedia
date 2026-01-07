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

1. **Make code changes first**
2. **Update documentation in the SAME commit/PR** - never defer documentation to later
3. **Be specific** - include examples, code snippets, and clear explanations
4. **Update both files if needed** - CLAUDE.md for developers, README.md for users
5. **Test your examples** - ensure code snippets and commands actually work

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
- `cache stats` - Show cache statistics
- `cache clear` - Clear cache entries

All commands are implemented in `src/cli/commands.py` with argument parsing in `src/cli/parser.py`.

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
./scripts/release.sh patch    # 0.2.2 -> 0.2.3
./scripts/release.sh minor    # 0.2.2 -> 0.3.0
./scripts/release.sh major    # 0.2.2 -> 1.0.0

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

**PricingInfo enhancements**:
- `savings_plan_1yr_no_upfront` - 1-year savings plan pricing (no upfront payment)
- `savings_plan_3yr_no_upfront` - 3-year savings plan pricing (no upfront payment)
- `format_savings_plan_1yr()` / `format_savings_plan_3yr()` - Format savings plan prices
- `calculate_savings_percentage(price_type)` - Calculate savings vs on-demand (supports "1yr", "3yr", "spot")
- Savings plans pricing will show "N/A" until fetching is implemented

### Configuration

**`src/config/settings.py`**: Uses `pydantic-settings` for environment-based config:
- `INSTANCEPEDIA_AWS_REGION` - Default region
- `INSTANCEPEDIA_AWS_PROFILE` - AWS profile

## Key Implementation Details

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
