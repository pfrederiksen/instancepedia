# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Instancepedia is an EC2 Instance Type Browser with both TUI (Terminal User Interface) and CLI (Command-Line Interface) modes. It provides detailed EC2 instance information, pricing (on-demand and spot), and free tier eligibility indicators.

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
- Create branch before starting work
- Merge to main after testing

## Known Issues to Avoid

### Textual `Screen.region` Property Conflict

Do NOT use `self.region` in Textual Screen subclasses - it conflicts with `Screen.region` property. Use `self._region` or another name.

### Binding Format

`BINDINGS` in Textual screens are tuples `(key, action, description)`, not `Binding` objects. Access with `b[0]`, `b[1]`, `b[2]`.

### Test Class Naming

Test helper/container classes should NOT start with `Test*` or pytest will try to collect them. Use `*TestApp` suffix instead.

### UI Updates from Async Workers

When updating UI from `run_worker()` async functions, use `self.call_later(callback)` to schedule on main thread. Do NOT call widget methods directly from worker thread.
