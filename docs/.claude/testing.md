# Testing Guide

This document provides comprehensive testing patterns, requirements, and examples for instancepedia.

## Test Coverage - MANDATORY

**100% test coverage is required for all new code.** Every new feature, function, or bug fix MUST include corresponding tests.

### Test Requirements

1. **All CLI commands must have tests** - Every `cmd_*` function in `src/cli/commands/` requires tests in `tests/test_cli_commands.py`
2. **All services must have tests** - New service methods require unit tests with mocked dependencies
3. **All TUI components must have tests** - New screens, widgets, or interactions require TUI tests
4. **Error cases must be tested** - Test both success and failure scenarios
5. **Edge cases must be tested** - Empty inputs, None values, boundary conditions

### Before Submitting Code

1. **Run all tests**: `pytest tests/ -v`
2. **Verify new tests pass**: `pytest tests/test_your_new_file.py -v`
3. **Check test coverage for changed files**: Review that all new code paths are tested
4. **Test error scenarios**: Ensure exceptions and edge cases are covered

**Never skip tests.** If a test is difficult to write, that's often a sign the code needs refactoring.

### Test File Organization

- `tests/test_cli_commands.py` - CLI command tests
- `tests/test_pricing_service.py` - Pricing service tests
- `tests/test_pricing_info.py` - PricingInfo model tests
- `tests/test_cache.py` - Cache tests
- `tests/test_tui_*.py` - TUI component tests
- `tests/conftest.py` - Shared fixtures

## Test Patterns

### CLI Command Test Pattern

CLI command tests should mock AWS clients and verify proper data flow:

```python
class TestCmdNewFeature:
    """Tests for cmd_new_feature function"""

    @patch('src.cli.commands.SomeService')
    @patch('src.cli.commands.get_aws_client')
    @patch('src.cli.commands.get_formatter')
    def test_cmd_new_feature_success(self, mock_get_formatter, mock_get_client, mock_service_class):
        """Test successful new feature command"""
        # Setup mocks
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.some_method.return_value = expected_data

        mock_formatter = Mock()
        mock_get_formatter.return_value = mock_formatter

        # Create args
        args = Mock(
            region='us-east-1',
            profile=None,
            format='table',
            some_param='value'
        )

        # Execute command
        cmd_new_feature(args)

        # Verify calls
        mock_get_client.assert_called_once_with('us-east-1', None)
        mock_service.some_method.assert_called_once_with('value')
        mock_formatter.format_data.assert_called_once()

    @patch('src.cli.commands.get_aws_client')
    def test_cmd_new_feature_error(self, mock_get_client):
        """Test new feature with error"""
        # Setup error
        mock_get_client.side_effect = Exception("AWS Error")

        # Create args
        args = Mock(region='us-east-1', profile=None, debug=False)

        # Execute should handle error gracefully
        with pytest.raises(SystemExit):
            cmd_new_feature(args)
```

### Service Test Pattern

Service tests should mock AWS clients and verify business logic:

```python
@pytest.fixture
def service(mock_aws_client):
    """Create service with mocked dependencies"""
    with patch('src.services.some_service.get_cache') as mock_cache:
        mock_cache.return_value = Mock()
        return SomeService(mock_aws_client)

def test_service_method_success(service):
    """Test service method success case"""
    # Setup
    service.aws_client.some_api_call.return_value = {'Data': 'value'}

    # Execute
    result = service.some_method("input")

    # Verify
    assert result == expected_value
    service.aws_client.some_api_call.assert_called_once()

def test_service_method_error(service):
    """Test service method error handling"""
    # Setup error
    service.aws_client.some_api_call.side_effect = Exception("Error")

    # Execute
    result = service.some_method("input")

    # Verify graceful handling
    assert result is None  # Or appropriate error handling
```

### PricingService Test Pattern

Pricing service tests should mock cache and AWS Pricing API:

```python
@pytest.fixture
def pricing_service(mock_aws_client):
    """Create PricingService with mocked dependencies"""
    with patch('src.services.pricing_service.get_pricing_cache') as mock_get_cache:
        mock_cache = Mock()
        mock_cache.get = Mock(return_value=None)  # Cache miss by default
        mock_cache.set = Mock()
        mock_get_cache.return_value = mock_cache

        service = PricingService(mock_aws_client, use_cache=True)
        service.cache = mock_cache  # Store reference for assertions
        return service

def test_cache_hit(pricing_service):
    """Test cache returns immediately without API call"""
    # Setup cache hit
    pricing_service.cache.get.return_value = 0.0104

    # Execute
    price = pricing_service.get_on_demand_price("t3.micro", "us-east-1")

    # Verify
    assert price == 0.0104
    pricing_service.cache.set.assert_not_called()  # No cache write on hit
    pricing_service.aws_client.get_pricing_client.assert_not_called()  # No API call

def test_cache_miss_api_success(pricing_service):
    """Test API call on cache miss"""
    # Setup cache miss and API response
    pricing_service.cache.get.return_value = None
    mock_pricing = Mock()
    pricing_service.aws_client.get_pricing_client.return_value = mock_pricing

    mock_pricing.get_products.return_value = {
        'PriceList': [
            json.dumps({
                'terms': {
                    'OnDemand': {
                        'term1': {
                            'priceDimensions': {
                                'dim1': {
                                    'pricePerUnit': {'USD': '0.0104'}
                                }
                            }
                        }
                    }
                }
            })
        ]
    }

    # Execute
    price = pricing_service.get_on_demand_price("t3.micro", "us-east-1")

    # Verify
    assert price == 0.0104
    pricing_service.cache.set.assert_called_once()
    mock_pricing.get_products.assert_called_once()
```

### Cache Thread Safety Test Pattern

Cache tests should verify thread-safe operations:

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

def test_concurrent_reads_writes(cache):
    """Test concurrent reads and writes don't cause corruption"""
    cache.set("us-east-1", "t3.micro", "on_demand", 0.0104)

    read_results = []
    write_count = 0

    def read_price():
        price = cache.get("us-east-1", "t3.micro", "on_demand")
        read_results.append(price)

    def write_price():
        nonlocal write_count
        cache.set("us-east-1", "t3.micro", "on_demand", 0.0200)
        write_count += 1

    with ThreadPoolExecutor(max_workers=20) as executor:
        # Mix reads and writes
        futures = []
        for _ in range(10):
            futures.append(executor.submit(read_price))
            futures.append(executor.submit(write_price))

        # Wait for completion
        for f in as_completed(futures):
            f.result()

    # Verify no None values (corruption)
    assert all(price is not None for price in read_results)
    # Verify all writes completed
    assert write_count == 10
```

### TUI Test Pattern

TUI tests use Textual's `app.run_test()` async context:

```python
import pytest
from textual.widgets import Tree

@pytest.mark.asyncio
async def test_instance_list_displays(mock_region):
    """Test instance list screen displays correctly"""
    # Create test app
    class InstanceListTestApp(App):
        def __init__(self, region):
            super().__init__()
            self.region = region

        def on_mount(self):
            self.push_screen(InstanceList(self.region))

    # Run test
    app = InstanceListTestApp(mock_region)
    async with app.run_test() as pilot:
        # Wait for UI to update
        await pilot.pause()

        # Get screen
        screen = app.screen
        assert isinstance(screen, InstanceList)

        # Verify tree exists
        tree = screen.query_one(Tree)
        assert tree is not None

        # Verify categories populated
        assert len(tree.root.children) > 0

@pytest.mark.asyncio
async def test_instance_selection(mock_region, mock_instance):
    """Test selecting an instance pushes detail screen"""
    class InstanceListTestApp(App):
        def __init__(self, region, instances):
            super().__init__()
            self.region = region
            self.instances = instances

        def on_mount(self):
            screen = InstanceList(self.region)
            screen.instances = self.instances
            self.push_screen(screen)

    app = InstanceListTestApp(mock_region, [mock_instance])
    async with app.run_test() as pilot:
        await pilot.pause()

        # Simulate selection
        screen = app.screen
        tree = screen.query_one(Tree)

        # Select first instance
        await pilot.press("enter")
        await pilot.pause()

        # Verify detail screen pushed
        assert isinstance(app.screen, InstanceDetail)
```

**Important TUI Testing Notes:**
- Use `await pilot.pause()` for UI updates
- Use `await asyncio.sleep(0.3)` to wait for timers (e.g., `set_timer(0.2)`)
- Test helper apps named `*TestApp` to avoid pytest collection warnings
- Never name test classes starting with `Test*` unless they're actual test classes

### Testing Services

When adding new services or modifying existing ones, always add comprehensive tests:

**Coverage checklist:**
- Success case with valid input
- Cache hit scenario (if applicable)
- Cache miss scenario (if applicable)
- API error handling
- Invalid input handling
- Edge cases (None, empty, boundary values)
- Concurrent access (if thread-safe)

**Example comprehensive service test:**
```python
class TestPricingService:
    """Comprehensive PricingService tests"""

    def test_get_on_demand_price_cache_hit(self, pricing_service):
        """Test cache hit returns immediately"""
        # ... test implementation

    def test_get_on_demand_price_cache_miss_success(self, pricing_service):
        """Test API call on cache miss"""
        # ... test implementation

    def test_get_on_demand_price_api_error(self, pricing_service):
        """Test error handling on API failure"""
        # ... test implementation

    def test_get_on_demand_price_no_pricing_data(self, pricing_service):
        """Test handling when no pricing data available"""
        # ... test implementation

    def test_get_on_demand_price_invalid_region(self, pricing_service):
        """Test handling of invalid region"""
        # ... test implementation
```

## Running Tests

### Basic Commands

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

# Run tests matching pattern
pytest -k "pricing"
```

### Common Testing Scenarios

```bash
# Test only CLI commands
pytest tests/test_cli_commands.py -v

# Test only TUI components
pytest tests/test_tui_*.py -v

# Test only services
pytest tests/test_*_service.py -v

# Test with coverage report
pytest --cov=src --cov-report=html

# Test with debug output
pytest -v -s
```

## Test Fixtures

Common fixtures are defined in `tests/conftest.py`:

```python
@pytest.fixture
def mock_aws_client():
    """Mock AWS client for testing"""
    client = Mock()
    # ... setup common mocks
    return client

@pytest.fixture
def mock_region():
    """Mock AWS region"""
    return Region(
        region_name="us-east-1",
        region_code="us-east-1",
        endpoint="ec2.us-east-1.amazonaws.com"
    )

@pytest.fixture
def mock_instance():
    """Mock instance type"""
    return InstanceType(
        instance_type="t3.micro",
        vcpu_info=VCpuInfo(default_vcpus=2),
        memory_info=MemoryInfo(size_in_mib=1024),
        # ... other fields
    )
```

## Mocking Best Practices

### Patch Targets

Always patch at the import location, not the definition location:

```python
# Good - patch where it's used
@patch('src.cli.commands.get_aws_client')
def test_command(mock_get_client):
    pass

# Bad - patch where it's defined
@patch('src.services.aws_client.get_aws_client')
def test_command(mock_get_client):
    pass
```

### Mock Return Values

Set return values appropriately for the test scenario:

```python
# Simple value
mock_service.get_price.return_value = 0.0104

# Complex object
mock_service.get_instance.return_value = InstanceType(...)

# List of values
mock_service.list_instances.return_value = [instance1, instance2]

# Exception
mock_service.get_price.side_effect = Exception("Error")

# Multiple calls with different values
mock_service.get_price.side_effect = [0.01, 0.02, 0.03]
```

### Verify Mock Calls

Always verify that mocks were called correctly:

```python
# Called once
mock_service.get_price.assert_called_once()

# Called with specific args
mock_service.get_price.assert_called_once_with("t3.micro", "us-east-1")

# Called N times
assert mock_service.get_price.call_count == 3

# Not called
mock_service.get_price.assert_not_called()

# Any call with specific args
mock_service.get_price.assert_any_call("t3.micro", "us-east-1")
```
