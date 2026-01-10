# Known Issues and Common Pitfalls

This document catalogs known issues, common pitfalls, and how to avoid them when working with instancepedia.

## Textual Framework Issues

### Screen.region Property Conflict

**Issue:** Textual's `Screen` class has a built-in `region` property that returns the screen's rendered region. Using `self.region` in Screen subclasses will conflict with this property.

**Bad:**
```python
class MyScreen(Screen):
    def __init__(self, region: str):
        super().__init__()
        self.region = region  # ❌ Conflicts with Screen.region property
```

**Good:**
```python
class MyScreen(Screen):
    def __init__(self, region: str):
        super().__init__()
        self._region = region  # ✅ Use underscore prefix or different name
```

**Solution:** Always use `self._region` or another name when storing AWS region in Screen subclasses.

### Binding Format

**Issue:** Textual `BINDINGS` are tuples, not `Binding` objects, despite what the typing suggests.

**Bad:**
```python
for binding in self.BINDINGS:
    key = binding.key  # ❌ AttributeError: 'tuple' has no attribute 'key'
```

**Good:**
```python
for binding in self.BINDINGS:
    key = binding[0]         # ✅ Access by index
    action = binding[1]
    description = binding[2]
```

**Solution:** Access binding elements by index: `b[0]` (key), `b[1]` (action), `b[2]` (description).

### UI Updates from Async Workers

**Issue:** Calling widget methods directly from `run_worker()` async functions causes thread safety issues.

**Bad:**
```python
async def fetch_data(self):
    data = await get_data()
    self.widget.update(data)  # ❌ Not thread-safe
```

**Good:**
```python
async def fetch_data(self):
    data = await get_data()

    def update_ui():
        self.widget.update(data)

    self.call_later(update_ui)  # ✅ Thread-safe UI update
```

**Solution:** Use `self.call_later(callback)` to schedule UI updates on the main thread.

## Testing Issues

### Test Class Naming

**Issue:** Pytest tries to collect classes starting with `Test*` as test classes, causing errors for helper classes.

**Bad:**
```python
class TestApp(App):  # ❌ Pytest tries to collect this
    """Helper app for testing"""
    pass
```

**Good:**
```python
class InstanceListTestApp(App):  # ✅ Suffix instead of prefix
    """Helper app for testing"""
    pass
```

**Solution:** Use `*TestApp` suffix for helper classes, not `Test*` prefix.

### Missing Logger Import

**Issue:** Adding logging calls without importing logging module causes runtime errors.

**Bad:**
```python
# No import
def some_function():
    logger.debug("Starting")  # ❌ NameError: name 'logger' is not defined
```

**Good:**
```python
import logging

logger = logging.getLogger("instancepedia")  # At module level

def some_function():
    logger.debug("Starting")  # ✅ Works correctly
```

**Solution:** Always add these two lines at the top of files that use logging:
1. `import logging`
2. `logger = logging.getLogger("instancepedia")`

### TUI Test Timing

**Issue:** TUI tests fail intermittently because UI updates haven't completed.

**Bad:**
```python
async def test_screen():
    async with app.run_test() as pilot:
        await pilot.press("enter")
        # Immediate check - may fail
        assert app.screen.title == "New Screen"  # ❌ Race condition
```

**Good:**
```python
async def test_screen():
    async with app.run_test() as pilot:
        await pilot.press("enter")
        await pilot.pause()  # ✅ Wait for UI update
        assert app.screen.title == "New Screen"

        # For timers, wait longer
        await asyncio.sleep(0.3)  # ✅ Wait for 0.2s timer to fire
```

**Solution:** Use `await pilot.pause()` after actions. For timers, use `await asyncio.sleep(timer_duration + 0.1)`.

## AWS Client Issues

### aioboto3 Resource Cleanup

**Issue:** Improper cleanup of aioboto3 clients causes "Unclosed client session" warnings.

**Bad:**
```python
async def get_price():
    client = AsyncAWSClient(region)
    price = await client.get_pricing()
    # ❌ Client not properly closed
    return price
```

**Good:**
```python
async def get_price():
    async with AsyncAWSClient(region) as client:  # ✅ Context manager
        price = await client.get_pricing()
        return price
```

**Solution:** Always use `async with AsyncAWSClient(...)` to ensure proper cleanup. The multi-layered cleanup strategy handles:
1. Synchronous cleanup first (prevents warnings even if cancelled)
2. AsyncExitStack cleanup for normal cases
3. Global atexit handler for interpreter shutdown

### Cache Statistics Timing

**Issue:** Cache hit statistics reported incorrectly when counted after pricing fetch completes.

**Bad:**
```python
# Fetch pricing
await pricing_service.get_prices(instances)

# Check cache hits - all appear cached!
stats = cache.get_stats()  # ❌ Everything in cache now
```

**Good:**
```python
# Track hits during fetch
def on_cache_hit():
    cache_hits[0] += 1

await pricing_service.get_prices(
    instances,
    cache_hit_callback=on_cache_hit  # ✅ Track during fetch
)
```

**Solution:** Track cache hits during pricing fetch using callbacks, not after completion.

## Performance Issues

### UI Flicker During Pricing Updates

**Issue:** Updating the TUI tree for every price causes excessive rebuilds and flicker.

**Bad:**
```python
async def on_price(instance, price):
    instance.pricing = price
    self.rebuild_tree()  # ❌ Called hundreds of times
```

**Good:**
```python
async def on_price(instance, price):
    instance.pricing = price
    self.price_count += 1
    if self.price_count % 10 == 0:  # ✅ Throttle updates
        self.rebuild_tree()
```

**Solution:** Use `ui_update_throttle` setting to update every N prices instead of every price.

### Tree State Loss on Rebuild

**Issue:** Rebuilding tree loses expanded/collapsed state.

**Bad:**
```python
def update_tree(self):
    self.tree.clear()
    self.tree.root.add("Category1")  # ❌ Loses expanded state
```

**Good:**
```python
def update_tree(self):
    # Capture state
    expanded = self._get_expanded_nodes()

    # Rebuild
    self.tree.clear()
    self.tree.root.add("Category1")

    # Restore state
    self._restore_expanded_nodes(expanded)  # ✅ Preserves state
```

**Solution:** Capture and restore expanded state around tree rebuilds.

### Connection Pool Exhaustion

**Issue:** High concurrency without sufficient connection pool size causes bottlenecks.

**Bad:**
```python
settings = Settings(
    pricing_concurrency=50,  # High concurrency
    max_pool_connections=10  # ❌ Too few connections
)
```

**Good:**
```python
settings = Settings(
    pricing_concurrency=50,
    max_pool_connections=50  # ✅ Match or exceed concurrency
)
```

**Solution:** Set `max_pool_connections` >= `pricing_concurrency` for optimal performance.

## Data Model Issues

### Fractional GPU Detection

**Issue:** AWS API reports `Count=0` for fractional GPU instances like g6f, making them appear GPU-less.

**Bad:**
```python
def has_gpu(instance):
    return instance.gpu_info.count > 0  # ❌ False for g6f instances
```

**Good:**
```python
def has_gpu(instance):
    # Check both count and memory
    return (instance.gpu_info.count > 0 or
            (instance.gpu_info.total_gpu_memory_in_mib or 0) > 0)  # ✅ Handles fractional GPUs
```

**Solution:** Use the `is_fractional_gpu` property or check both count and memory.

### PricingInfo None Values

**Issue:** Pricing fields can be None when pricing is unavailable, causing AttributeErrors.

**Bad:**
```python
def display_price(instance):
    return f"${instance.pricing.on_demand_price:.4f}"  # ❌ None.on_demand_price raises AttributeError
```

**Good:**
```python
def display_price(instance):
    if instance.pricing and instance.pricing.on_demand_price:
        return f"${instance.pricing.on_demand_price:.4f}"
    return "N/A"  # ✅ Handle None gracefully
```

**Solution:** Always check for None before accessing pricing fields.

## Caching Issues

### Cache Key Collisions

**Issue:** Using dots in cache keys can cause filesystem issues on some systems.

**Bad:**
```python
cache_key = f"{region}_{instance_type}"  # ❌ "us-east-1_t3.micro" has dot
```

**Good:**
```python
cache_key = f"{region}_{instance_type}".replace(".", "_")  # ✅ "us-east-1_t3_micro"
```

**Solution:** Replace dots with underscores in cache keys (already done in `src/cache.py`).

### Cache None Values

**Issue:** Not caching None results causes repeated API calls for unavailable pricing.

**Bad:**
```python
price = fetch_price(instance)
if price is not None:
    cache.set(key, price)  # ❌ None values not cached
```

**Good:**
```python
price = fetch_price(instance)
cache.set(key, price)  # ✅ Cache both success and failure
```

**Solution:** Cache None values to avoid repeated failed API calls.

## Git Workflow Issues

### Direct Pushes to Main

**Issue:** Pushing directly to main bypasses review and can break the codebase.

**Bad:**
```bash
git checkout main
git commit -m "Quick fix"
git push  # ❌ Direct push to main
```

**Good:**
```bash
git checkout -b fix/issue-description
git commit -m "Fix issue"
git push -u origin fix/issue-description
gh pr create  # ✅ Create PR for review
```

**Solution:** ALWAYS use feature branches and Pull Requests. Never push directly to main.

### Skipping Documentation Updates

**Issue:** Making code changes without updating documentation leads to outdated docs.

**Bad:**
```bash
# Commit only code changes
git add src/
git commit -m "Add new feature"  # ❌ Docs not updated
```

**Good:**
```bash
# Update both code and docs
git add src/ README.md CLAUDE.md
git commit -m "Add new feature with documentation"  # ✅ Docs updated
```

**Solution:** Update relevant documentation files (README.md, CLAUDE.md, docs/.claude/) in the same commit as code changes.

## Configuration Issues

### Environment Variable Precedence

**Issue:** Not understanding settings precedence causes confusion about which values are used.

**Precedence (highest to lowest):**
1. Init settings (passed to constructor)
2. Environment variables (`INSTANCEPEDIA_*`)
3. TOML config file (`~/.instancepedia/config.toml`)
4. Default values

**Solution:** Check all three sources when debugging unexpected configuration values.

### Invalid TOML Syntax

**Issue:** TOML syntax errors cause config file to be silently ignored.

**Bad:**
```toml
# Invalid TOML
pricing_concurrency = "10"  # ❌ Should be integer, not string
```

**Good:**
```toml
# Valid TOML
pricing_concurrency = 10  # ✅ Correct type
```

**Solution:** Validate TOML syntax. Check logs for config file parsing errors.

## Pricing API Issues

### Region Name vs Code Confusion

**Issue:** Pricing API requires location names, not region codes.

**Bad:**
```python
location = region  # ❌ "us-east-1" not recognized by Pricing API
```

**Good:**
```python
location = REGION_MAP.get(region, region)  # ✅ "US East (N. Virginia)"
```

**Solution:** Use `_get_pricing_region()` helper to map region codes to location names.

### Pricing API Throttling

**Issue:** High concurrency can trigger Pricing API throttling.

**Bad:**
```python
# No retry logic
price = pricing_client.get_products(...)  # ❌ May fail on throttle
```

**Good:**
```python
# Retry with exponential backoff
for attempt in range(3):
    try:
        price = pricing_client.get_products(...)
        break
    except ClientError as e:
        if e.response['Error']['Code'] == 'Throttling':
            time.sleep(2 ** attempt)  # ✅ Backoff and retry
```

**Solution:** Use `_handle_throttling()` helper for automatic retry with backoff.

### Reserved Instance Pricing Availability

**Issue:** Not all RI pricing options are available for all instance types.

**Bad:**
```python
# Expect all RI prices to exist
for option in ['no_upfront', 'partial_upfront', 'all_upfront']:
    price = get_ri_price(instance, option)
    display_price(price)  # ❌ May be None
```

**Good:**
```python
# Handle None values
for option in ['no_upfront', 'partial_upfront', 'all_upfront']:
    price = get_ri_price(instance, option)
    display_price(price if price else "N/A")  # ✅ Graceful None handling
```

**Solution:** Always check for None and display "N/A" for unavailable pricing.

## Async/Threading Issues

### Mixing Sync and Async Code

**Issue:** Calling async functions from sync code or vice versa causes errors.

**Bad:**
```python
# Sync function
def get_data():
    return await fetch_data()  # ❌ SyntaxError: 'await' outside async function
```

**Good:**
```python
# Async function
async def get_data():
    return await fetch_data()  # ✅ Correct

# Or use run_sync for calling from sync code
def get_data():
    return asyncio.run(fetch_data())  # ✅ Run async from sync
```

**Solution:** Use `async def` for async functions. Use `asyncio.run()` to call async from sync code (but avoid mixing contexts).

### Worker Cancellation Not Handled

**Issue:** Workers cancelled on app shutdown can cause resource leaks.

**Bad:**
```python
async def fetch_data(self):
    client = await get_client()
    data = await client.fetch()  # ❌ Client not closed on cancellation
    return data
```

**Good:**
```python
async def fetch_data(self):
    async with get_client() as client:  # ✅ Cleaned up even on cancellation
        data = await client.fetch()
        return data
```

**Solution:** Use async context managers to ensure cleanup even on cancellation.
