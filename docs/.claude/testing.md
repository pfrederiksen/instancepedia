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

### Entry Point Test Pattern

Entry point tests (like `main.py`) require comprehensive mocking since they orchestrate TUI/CLI routing. These tests verify routing logic without actually running the TUI or CLI.

**When to use this pattern:**
- Application entry points (`main.py`, `app.py`)
- Functions that coordinate between TUI and CLI modes
- Mode detection and routing logic
- Entry-level error handling and initialization

**Test categories for entry points:**
1. **TUI mode tests**: Verify TUI is launched correctly
2. **CLI mode tests**: Verify CLI commands are routed correctly
3. **Error handling tests**: Verify graceful error handling
4. **Mode isolation tests**: Verify TUI and CLI modes don't interfere

**Example entry point test pattern:**

```python
from unittest.mock import Mock, patch
from src.main import main

class TestMainEntryPoint:
    """Tests for main() entry point"""

    @patch('src.main.parse_args')
    @patch('src.main.InstancepediaApp')
    @patch('src.main.Settings')
    @patch('src.main.setup_logging')
    def test_tui_mode_explicit_flag(
        self,
        mock_setup_logging,
        mock_settings_class,
        mock_app_class,
        mock_parse_args
    ):
        """Test TUI mode with explicit --tui flag"""
        # Setup mocks
        mock_args = Mock()
        mock_args.tui = True
        mock_args.command = None
        mock_args.debug = False
        mock_parse_args.return_value = mock_args

        mock_settings_instance = Mock()
        mock_settings_class.return_value = mock_settings_instance

        mock_app = Mock()
        mock_app_class.return_value = mock_app

        # Execute entry point
        main()

        # Verify TUI initialization
        mock_setup_logging.assert_called_once_with(level="INFO", enable_tui=False)
        mock_settings_class.assert_called_once()
        mock_app_class.assert_called_once_with(mock_settings_instance, debug=False)
        mock_app.run.assert_called_once()

    @patch('src.main.parse_args')
    @patch('src.main.run_cli')
    @patch('src.main.Settings')
    @patch('src.main.setup_logging')
    def test_cli_mode_with_command(
        self,
        mock_setup_logging,
        mock_settings_class,
        mock_run_cli,
        mock_parse_args
    ):
        """Test CLI mode when command is specified"""
        # Setup mocks
        mock_args = Mock()
        mock_args.tui = False
        mock_args.command = 'list'
        mock_args.debug = False
        mock_parse_args.return_value = mock_args

        mock_run_cli.return_value = 0  # Success exit code

        # Execute entry point
        exit_code = main()

        # Verify CLI routing
        mock_setup_logging.assert_called_once_with(level="INFO", enable_tui=False)
        mock_run_cli.assert_called_once_with(mock_args)
        assert exit_code == 0

    @patch('src.main.parse_args')
    @patch('src.main.InstancepediaApp')
    def test_tui_initialization_error(self, mock_app_class, mock_parse_args):
        """Test graceful handling of TUI initialization errors"""
        # Setup mocks
        mock_args = Mock()
        mock_args.tui = True
        mock_args.command = None
        mock_args.debug = False
        mock_parse_args.return_value = mock_args

        # Simulate TUI initialization error
        mock_app_class.side_effect = Exception("Failed to initialize TUI")

        # Execute entry point - should handle error gracefully
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

    @patch('src.main.parse_args')
    def test_keyboard_interrupt_handling(self, mock_parse_args):
        """Test graceful handling of Ctrl+C"""
        # Simulate KeyboardInterrupt during argument parsing
        mock_parse_args.side_effect = KeyboardInterrupt()

        # Execute entry point - should exit gracefully
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 130  # Standard Unix Ctrl+C exit code
```

**Key mocking strategy for entry points:**

1. **Mock all dependencies**: Mock argument parsing, app initialization, settings, logging
2. **Test routing logic**: Verify correct mode (TUI vs CLI) is invoked
3. **Test mode isolation**: Ensure TUI mode doesn't call CLI code and vice versa
4. **Test error paths**: Verify graceful handling of initialization errors
5. **Verify exit codes**: Check correct exit codes for success/failure scenarios

**Why this approach works:**

- **Tests routing without execution**: Verifies logic without running actual TUI/CLI
- **Fast test execution**: Mocked tests run in milliseconds
- **Deterministic**: No UI timing issues or CLI output capturing
- **Comprehensive coverage**: Can test error paths that are hard to trigger in integration tests
- **Isolated**: Tests only the entry point coordination logic

**Common pitfalls to avoid:**

```python
# ❌ Bad: Don't expect SystemExit for normal TUI mode
with pytest.raises(SystemExit):
    main()  # TUI mode returns normally, doesn't exit

# ✅ Good: Call main() directly for TUI mode
main()
mock_app.run.assert_called_once()

# ❌ Bad: Don't test actual TUI/CLI behavior in entry point tests
assert "Instance Type" in captured_output  # This is an integration test

# ✅ Good: Only verify routing and initialization
mock_app_class.assert_called_once_with(settings, debug=False)
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

### Dataclass Property Testing Pattern

Test computed properties on dataclasses with comprehensive edge case coverage.

**When to use:**
- Testing `@property` methods on dataclasses
- Testing calculations that depend on multiple fields
- Testing edge cases: None values, division by zero, empty collections

**Pattern:**
```python
def test_volatility_percentage_normal(self):
    """Test volatility percentage calculation with normal values"""
    from datetime import datetime, timezone
    from src.services.pricing_service import SpotPriceHistory

    now = datetime.now(timezone.utc)
    history = SpotPriceHistory(
        instance_type="t3.micro",
        region="us-east-1",
        days=30,
        current_price=0.0104,
        min_price=0.0095,
        max_price=0.0120,
        avg_price=0.0105,
        median_price=0.0104,
        std_dev=0.0010,
        price_points=[(now, 0.0104)]
    )

    volatility = history.volatility_percentage
    # std_dev / avg_price * 100 = 0.0010 / 0.0105 * 100 ≈ 9.52%
    assert volatility is not None
    assert abs(volatility - 9.52) < 0.1

def test_volatility_percentage_none_std_dev(self):
    """Test volatility percentage returns None for single price point"""
    history = SpotPriceHistory(
        instance_type="t3.micro",
        region="us-east-1",
        days=30,
        current_price=0.0104,
        min_price=0.0104,
        max_price=0.0104,
        avg_price=0.0104,
        median_price=0.0104,
        std_dev=None,  # Single price point
        price_points=[(now, 0.0104)]
    )

    # Cannot calculate volatility with single price
    assert history.volatility_percentage is None

def test_volatility_percentage_zero_avg_price(self):
    """Test volatility percentage returns None for zero average (no division by zero)"""
    history = SpotPriceHistory(
        instance_type="t3.micro",
        region="us-east-1",
        days=30,
        current_price=0.0,
        min_price=0.0,
        max_price=0.0,
        avg_price=0.0,  # Zero average
        median_price=0.0,
        std_dev=0.0010,
        price_points=[(now, 0.0)]
    )

    # Cannot divide by zero
    assert history.volatility_percentage is None
```

**Key aspects:**
1. **Normal case**: Test calculation with valid inputs
2. **None handling**: Test when dependencies are None (incomplete data)
3. **Division by zero**: Test zero denominators return None (not crash)
4. **Precision**: Use `abs(result - expected) < tolerance` for float comparisons

### Batch Chunking Pattern

Test batch operations that split requests into chunks due to API limits.

**When to use:**
- Testing methods that process large lists in chunks (AWS 50-instance limit)
- Verifying correct chunk sizes and number of API calls
- Testing that all items get processed despite chunking

**Pattern:**
```python
def test_get_spot_prices_batch_multiple_chunks(self, pricing_service, mock_aws_client):
    """Test batch fetch with multiple chunks (> 50 instances)"""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    mock_ec2_client = Mock()

    # Create 75 instance types (should trigger 2 chunks: 50 + 25)
    instance_types = [f't3.type{i}' for i in range(75)]

    # Mock responses for each chunk
    def mock_response(InstanceTypes, **kwargs):
        return {
            'SpotPriceHistory': [
                {'InstanceType': inst_type, 'SpotPrice': f'0.{i:04d}', 'Timestamp': now}
                for i, inst_type in enumerate(InstanceTypes)
            ]
        }

    mock_ec2_client.describe_spot_price_history.side_effect = mock_response
    mock_aws_client.ec2_client = mock_ec2_client

    # Call with 75 instance types
    result = pricing_service.get_spot_prices_batch(instance_types, 'us-east-1')

    # Verify all 75 instances have prices
    assert len(result) == 75
    # Verify 2 API calls (2 chunks: 50 + 25)
    assert mock_ec2_client.describe_spot_price_history.call_count == 2

def test_get_spot_prices_batch_mixed_success_failure(self, pricing_service, mock_aws_client):
    """Test batch fetch with mixed chunk success/failure"""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    mock_ec2_client = Mock()

    # Create 75 instance types (2 chunks: 50 + 25)
    instance_types = [f't3.type{i}' for i in range(75)]

    # First chunk succeeds, second chunk fails
    def mock_response(InstanceTypes, **kwargs):
        if len(InstanceTypes) == 50:  # First chunk
            return {
                'SpotPriceHistory': [
                    {'InstanceType': inst_type, 'SpotPrice': '0.0100', 'Timestamp': now}
                    for inst_type in InstanceTypes
                ]
            }
        else:  # Second chunk
            raise ClientError(
                {'Error': {'Code': 'InvalidParameterValue'}},
                'describe_spot_price_history'
            )

    mock_ec2_client.describe_spot_price_history.side_effect = mock_response
    mock_aws_client.ec2_client = mock_ec2_client

    result = pricing_service.get_spot_prices_batch(instance_types, 'us-east-1')

    # Verify first 50 have prices, last 25 are None
    for i in range(50):
        assert result[f't3.type{i}'] == 0.0100
    for i in range(50, 75):
        assert result[f't3.type{i}'] is None
```

**Key aspects:**
1. **Chunk size verification**: Test with count > limit to trigger multiple chunks
2. **API call count**: Verify expected number of calls (e.g., 75 items = 2 calls)
3. **Complete results**: Verify all items in result dict despite chunking
4. **Partial failure**: Test when some chunks succeed and others fail
5. **Use dynamic responses**: Mock function inspects `InstanceTypes` parameter to determine which chunk

### AWS Pagination Testing Pattern

Test AWS API pagination with NextToken across multiple pages.

**When to use:**
- Testing methods that handle AWS NextToken pagination
- Verifying complete data collection across pages
- Testing graceful degradation when pagination fails mid-stream

**Pattern:**
```python
def test_get_spot_prices_batch_with_pagination(self, pricing_service, mock_aws_client):
    """Test batch fetch with NextToken pagination"""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    mock_ec2_client = Mock()

    # Mock paginated responses
    mock_ec2_client.describe_spot_price_history.side_effect = [
        {
            'SpotPriceHistory': [
                {'InstanceType': 't3.micro', 'SpotPrice': '0.0104', 'Timestamp': now},
            ],
            'NextToken': 'token123'  # More pages available
        },
        {
            'SpotPriceHistory': [
                {'InstanceType': 't3.small', 'SpotPrice': '0.0208', 'Timestamp': now},
            ]
            # No NextToken - last page
        }
    ]
    mock_aws_client.ec2_client = mock_ec2_client

    # Call batch method
    result = pricing_service.get_spot_prices_batch(['t3.micro', 't3.small'], 'us-east-1')

    # Verify both prices collected from paginated results
    assert result == {
        't3.micro': 0.0104,
        't3.small': 0.0208
    }
    # Verify 2 API calls (pagination)
    assert mock_ec2_client.describe_spot_price_history.call_count == 2
    # Verify second call included NextToken
    second_call_kwargs = mock_ec2_client.describe_spot_price_history.call_args_list[1][1]
    assert second_call_kwargs['NextToken'] == 'token123'

def test_get_spot_prices_batch_pagination_error(self, pricing_service, mock_aws_client):
    """Test batch fetch handles pagination errors gracefully"""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    mock_ec2_client = Mock()

    # First page succeeds, second page fails
    mock_ec2_client.describe_spot_price_history.side_effect = [
        {
            'SpotPriceHistory': [
                {'InstanceType': 't3.micro', 'SpotPrice': '0.0104', 'Timestamp': now},
            ],
            'NextToken': 'token123'
        },
        Exception("Connection timeout")  # Second page fails
    ]
    mock_aws_client.ec2_client = mock_ec2_client

    result = pricing_service.get_spot_prices_batch(['t3.micro'], 'us-east-1')

    # Verify first page data was kept despite second page error
    assert result == {'t3.micro': 0.0104}
```

**Key aspects:**
1. **Multi-page responses**: Use `side_effect` list with multiple dicts
2. **NextToken presence**: Include `'NextToken': 'token123'` in all but last page
3. **Token verification**: Check second call receives NextToken parameter
4. **API call count**: Verify multiple calls made (one per page)
5. **Graceful degradation**: Test partial data retention when pagination fails
6. **Last page detection**: Verify loop stops when no NextToken returned

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

### Async Service Test Pattern

Async services (like `AsyncAWSClient`) use `AsyncMock` for async context managers and methods. This pattern is used for testing aioboto3 clients and other async AWS interactions.

**When to use this pattern:**
- Testing async context managers (e.g., `async with client.get_ec2_client()`)
- Testing async methods that use `await`
- Mocking aioboto3 session and client behavior
- Testing async error handling and cleanup

**Example: Testing async client context manager**

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch

@pytest.mark.asyncio
async def test_get_ec2_client_lazy_creation():
    """Test EC2 client is created on first access"""
    # Create mock client context manager
    mock_ec2_client = AsyncMock()
    mock_client_cm = AsyncMock()
    mock_client_cm.__aenter__.return_value = mock_ec2_client

    # Create mock session
    mock_session = Mock()
    mock_session.client.return_value = mock_client_cm

    client = AsyncAWSClient(region="us-east-1")

    # Patch _get_session to return our mock
    with patch.object(client, '_get_session', return_value=mock_session):
        # Initially None
        assert client._ec2_client is None

        # Access creates client
        async with client.get_ec2_client() as ec2:
            assert ec2 == mock_ec2_client
            assert client._ec2_client == mock_ec2_client

        # Verify session.client was called
        mock_session.client.assert_called_once()
        call_args = mock_session.client.call_args
        assert call_args[0][0] == "ec2"
        assert call_args[1]["region_name"] == "us-east-1"
```

**Example: Testing async methods with error handling**

```python
@pytest.mark.asyncio
async def test_connection_failure_client_error():
    """Test connection test with ClientError"""
    mock_ec2_client = AsyncMock()
    mock_ec2_client.describe_regions.side_effect = ClientError(
        {"Error": {"Code": "UnauthorizedOperation"}}, "DescribeRegions"
    )

    mock_client_cm = AsyncMock()
    mock_client_cm.__aenter__.return_value = mock_ec2_client
    mock_client_cm.__aexit__.return_value = None

    mock_session = Mock()
    mock_session.client.return_value = mock_client_cm

    client = AsyncAWSClient(region="us-east-1")

    with patch.object(client, '_get_session', return_value=mock_session):
        result = await client.test_connection()

    assert result is False
```

**Example: Testing client recreation after error**

```python
@pytest.mark.asyncio
async def test_get_ec2_client_recreates_after_error():
    """Test EC2 client is recreated after an error"""
    # First client - will error
    mock_ec2_client_1 = AsyncMock()
    mock_ec2_client_1.describe_instance_types.side_effect = ClientError(
        {"Error": {"Code": "Throttling"}}, "DescribeInstanceTypes"
    )

    # Second client - will succeed
    mock_ec2_client_2 = AsyncMock()

    mock_client_cm_1 = AsyncMock()
    mock_client_cm_1.__aenter__.return_value = mock_ec2_client_1

    mock_client_cm_2 = AsyncMock()
    mock_client_cm_2.__aenter__.return_value = mock_ec2_client_2

    mock_session = Mock()
    mock_session.client.side_effect = [mock_client_cm_1, mock_client_cm_2]

    client = AsyncAWSClient(region="us-east-1")

    with patch.object(client, '_get_session', return_value=mock_session):
        # First access - triggers error
        with pytest.raises(ClientError):
            async with client.get_ec2_client() as ec2:
                await ec2.describe_instance_types()

        # Client should be None after error
        assert client._ec2_client is None

        # Second access - creates new client
        async with client.get_ec2_client() as ec2:
            assert ec2 == mock_ec2_client_2

        # Verify client was created twice
        assert mock_session.client.call_count == 2
```

**Key aspects:**
1. **AsyncMock for async functions**: Use `AsyncMock()` for async context managers and methods
2. **Context manager protocol**: Mock `__aenter__` to return client, `__aexit__` for cleanup
3. **@pytest.mark.asyncio**: Required decorator for async test functions
4. **patch.object for instance methods**: Use `patch.object(instance, method_name)` instead of string path
5. **Error recovery**: Test that clients are recreated after errors (set to None, then recreated)
6. **Configuration verification**: Check that timeouts, regions, and pool settings are passed correctly

**Common pitfalls:**
- Forgetting `@pytest.mark.asyncio` decorator (test will fail silently)
- Using regular `Mock()` instead of `AsyncMock()` for async functions
- Not mocking both `__aenter__` and `__aexit__` for context managers
- Not using `await` when calling async methods in tests

### Edge Case & Validation Testing Pattern

Test validation functions and utility methods with comprehensive edge case coverage.

**When to use:**
- Testing validation functions (e.g., `is_valid_region()`)
- Testing utility functions with string inputs
- Testing boundary conditions and malformed inputs
- Testing functions that should gracefully handle unexpected input

**Pattern:**

```python
class TestIsValidRegion:
    """Tests for is_valid_region() function with comprehensive edge cases"""

    def test_is_valid_region_with_valid_regions(self):
        """Test is_valid_region with valid region codes"""
        assert is_valid_region('us-east-1') is True
        assert is_valid_region('eu-west-1') is True
        assert is_valid_region('ap-southeast-1') is True

    def test_is_valid_region_with_invalid_regions(self):
        """Test is_valid_region with invalid region codes"""
        assert is_valid_region('invalid-region') is False
        assert is_valid_region('us-east-99') is False

    def test_is_valid_region_with_empty_string(self):
        """Test is_valid_region with empty string (edge case)"""
        assert is_valid_region('') is False

    def test_is_valid_region_case_sensitivity(self):
        """Test that is_valid_region is case-sensitive"""
        assert is_valid_region('us-east-1') is True
        assert is_valid_region('US-EAST-1') is False  # Wrong case

    def test_is_valid_region_with_whitespace(self):
        """Test is_valid_region with whitespace (edge case)"""
        assert is_valid_region(' us-east-1') is False  # Leading space
        assert is_valid_region('us-east-1 ') is False  # Trailing space
        assert is_valid_region('   ') is False  # Only spaces

    def test_is_valid_region_with_special_characters(self):
        """Test is_valid_region with special characters (edge case)"""
        assert is_valid_region('us-east-1!') is False
        assert is_valid_region('us@east-1') is False
        assert is_valid_region('us-east-1\n') is False  # Newline
        assert is_valid_region('us-east-1\t') is False  # Tab

    def test_is_valid_region_with_partial_matches(self):
        """Test is_valid_region doesn't accept partial matches"""
        assert is_valid_region('us-east') is False  # Missing number
        assert is_valid_region('east-1') is False   # Missing region
```

**Key aspects:**
1. **Valid inputs**: Test all expected valid cases
2. **Invalid inputs**: Test clearly invalid cases
3. **Empty/None-like**: Test empty strings, whitespace, "None", "null"
4. **Case sensitivity**: Test uppercase, lowercase, mixed case
5. **Whitespace**: Test leading/trailing spaces, tabs, newlines
6. **Special characters**: Test punctuation, symbols that shouldn't be valid
7. **Partial matches**: Test that validation is strict (not substring matching)
8. **Boundary conditions**: Test edge of valid ranges (if applicable)

**Benefits:**
- Prevents crashes from unexpected input
- Documents expected behavior for all input types
- Achieves high coverage (often 100% for simple functions)
- Makes refactoring safer (tests catch behavior changes)

**Example - region.py edge case tests:**
```python
# tests/test_region.py
class TestIsValidRegion:
    """20 comprehensive tests covering all edge cases"""

    # Valid cases (4 tests)
    # Invalid cases (3 tests)
    # Edge cases (13 tests):
    #   - Empty string
    #   - None-like strings
    #   - Case sensitivity (3 tests)
    #   - Whitespace (4 tests)
    #   - Special characters (4 tests)
    #   - Partial matches (3 tests)
```

**Coverage achieved:**
- `region.py`: 0% → 100% (5 lines, all covered)
- Test count: +20 tests
- Verifies graceful handling of all invalid inputs

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
