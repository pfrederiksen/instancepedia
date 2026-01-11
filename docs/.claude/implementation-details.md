# Implementation Details

This document covers performance optimization, async improvements, caching, AWS client configuration, and other implementation details.

## Performance Optimization

The application supports fine-grained performance tuning via configuration settings:

### Concurrency Control

- **TUI Mode**: Uses `pricing_concurrency` (default: 10) for parallel pricing requests
- **CLI Mode**: Uses `cli_pricing_concurrency` (default: 5) to avoid overwhelming scripts
- **Retries**: Uses `pricing_retry_concurrency` (default: 3) for lower concurrency on failed requests
- All concurrency is managed via `asyncio.Semaphore` (TUI) or `ThreadPoolExecutor` (CLI)

### Request Throttling

- `pricing_request_delay_ms` controls delay between requests (default: 50ms)
- Helps avoid AWS API rate limiting
- Configurable per environment (faster for good networks, slower for rate-limited accounts)

### Batch Sizing

- `spot_batch_size` controls how many instance types are queried per EC2 API call (default: 50)
- EC2 API supports up to ~50 instance types per spot price history request
- Can be tuned based on API limits and network conditions

### UI Update Optimization

- `ui_update_throttle` controls how often the TUI updates during pricing fetch (default: every 10 prices)
- Reduces UI flicker and improves responsiveness
- Higher values for large instance lists, lower values for better progress visibility

### Performance Metrics (PricingMetrics)

The `PricingMetrics` dataclass (`src/services/async_pricing_service.py`) tracks pricing fetch performance:

**Fields**: `total_requests`, `cache_hits`, `api_calls`, `successful_fetches`, `failed_fetches`, `start_time`, `end_time`

**Calculated Properties**:
- `cache_hit_rate` - Percentage of requests served from cache
- `success_rate` - Percentage of successful fetches (cache + API)
- `elapsed_time` - Total time in seconds
- `requests_per_second` - Throughput metric

**Methods**:
- `record_cache_hit()` - Track a cache hit
- `record_api_call(success)` - Track an API call result
- `finish()` - Mark collection complete (freezes elapsed_time)
- `to_dict()` - Convert to dictionary for JSON serialization
- `summary()` - Human-readable summary string

**Usage:**
```python
# Get metrics from batch pricing
results, metrics = await service.get_on_demand_prices_batch(
    instance_types,
    region,
    return_metrics=True  # Request metrics
)
print(metrics.summary())  # "Pricing: 450/500 (90% success, 45% cached) in 12.3s"
print(metrics.to_dict())  # For JSON logging
```

**Logging:**
- Batch methods automatically log `metrics.summary()` at completion
- Logs throughput as requests/second for tuning
- Example: "Pricing: 450/500 (90% success, 45% cached) in 12.3s"

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

### Tuning Recommendations

- **Fast network, no rate limits**: Increase concurrency to 15-20, reduce delay to 25-30ms, increase pool connections to 100
- **Rate-limited account**: Decrease concurrency to 5, increase delay to 100ms
- **Large instance lists (500+)**: Increase UI throttle to 20-50
- **CI/CD scripts**: Increase CLI concurrency to 10 for faster batch operations
- **High concurrency**: Set max_pool_connections ≥ pricing_concurrency for optimal performance

## Async Improvements and Connection Pooling

The async AWS client implementation uses connection pooling, `AsyncExitStack`, and multi-layered cleanup for proper resource management:

### Connection Pooling

- `AsyncAWSClient` maintains a pool of HTTP connections (default: 50, configurable via `max_pool_connections`)
- Client instances are reused across multiple API calls instead of creating new ones each time
- Uses `asyncio.Lock` to ensure thread-safe client initialization and cleanup
- Pool size should match or exceed concurrency settings for optimal performance

### Resource Management with AsyncExitStack

- `AsyncAWSClient` uses `AsyncExitStack` for proper aioboto3 client lifecycle management
- Clients are registered via `self._exit_stack.enter_async_context(client_cm)` instead of manual `__aenter__`/`__aexit__` calls
- The exit stack ensures proper cleanup order and handles exceptions correctly
- All pricing workers use `async with AsyncAWSClient(...)` for automatic resource cleanup

### Multi-Layered Cleanup Strategy

The cleanup approach uses multiple layers to ensure no aiohttp warnings occur:

1. **Synchronous cleanup first** - `_close_connectors_sync()` closes TCP connectors and marks sessions as closed BEFORE any async cleanup. This prevents warnings even if async cleanup is cancelled.

2. **AsyncExitStack cleanup** - `await self._exit_stack.aclose()` properly closes all registered clients through their normal async cleanup path.

3. **Global atexit handler** - At interpreter exit, `_cleanup_all_aiohttp_resources()` performs a final sweep:
   - Closes any registered clients via `weakref.WeakSet` registry
   - Runs `gc.collect()` to find orphaned aiohttp resources
   - Closes any unclosed `ClientSession` or `TCPConnector` objects

### Client Reuse Pattern

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
# Context manager ensures proper cleanup (sync first, then async)
```

### Benefits

- **No warnings**: Multi-layered cleanup prevents "Unclosed client session" and "Unclosed connector" warnings
- **Performance**: Reusing connections eliminates handshake overhead
- **Reliability**: Automatic cleanup prevents connection leaks
- **Scalability**: Connection pooling handles high concurrency efficiently
- **Cancellation-safe**: Sync cleanup happens before async, so cancellation doesn't cause warnings

### Implementation Details

**`src/services/async_aws_client.py`**:
- EC2 and Pricing clients are lazy-initialized and cached
- `get_ec2_client()` and `get_pricing_client()` are async context managers that yield cached clients
- On error, cached clients are closed via `_close_single_client_sync()` and will be recreated on next request
- All initialization is protected by `asyncio.Lock` for thread safety
- Global `_active_clients: weakref.WeakSet` tracks all client instances for cleanup
- `atexit.register(_cleanup_all_aiohttp_resources)` ensures cleanup at interpreter exit

**CRITICAL: Using EC2/Pricing Clients Correctly**:

```python
# ❌ WRONG - get_ec2_client() returns async context manager, not client
ec2_client = await client.get_ec2_client()  # ERROR: Can't await context manager
response = await ec2_client.describe_instance_types(...)

# ✅ CORRECT - Use async with to get the client
async with client.get_ec2_client() as ec2_client:
    response = await ec2_client.describe_instance_types(...)
    # Client is valid within this block

# ✅ CORRECT - Multiple API calls with same client
async with client.get_ec2_client() as ec2_client:
    response1 = await ec2_client.describe_instance_types(InstanceTypes=[type1])
    response2 = await ec2_client.describe_regions()
    # Reuses same client for both calls
```

**Why this pattern?**:
- `get_ec2_client()` is decorated with `@asynccontextmanager` and uses `yield`
- Must use `async with` to properly enter/exit the context
- The context manager handles client initialization, caching, and error recovery
- Attempting to `await` the context manager directly causes: `"'_AsyncGeneratorContextManager' object can't be awaited"`

### Cleanup on Cancellation

- When workers are cancelled (e.g., user quits TUI during pricing fetch), `__aexit__` is called
- `_close_connectors_sync()` runs FIRST to close connectors synchronously - this prevents all warnings
- Then async cleanup via `close()` is attempted (may be cancelled, but that's OK)
- The sync cleanup marks `http_session._closed = True` to prevent `__del__` warnings
- Multiple attribute paths are tried to find the http session (aiobotocore uses different internal structures)

## Pricing API Region Mapping

The AWS Pricing API requires location names (e.g., "US East (N. Virginia)") not region codes.

**REGION_MAP locations:**
- Sync service: `PricingService.REGION_MAP` class constant in `src/services/pricing_service.py`
- Async service: `REGION_MAP` module constant in `src/services/async_pricing_service.py`

Pricing API is only available in `us-east-1`, so pricing client always uses that region regardless of target region for instance types.

**Helper Methods** (available in both sync and async services):
- `_get_pricing_region(region)` - Maps AWS region code to Pricing API location name
- `_build_ec2_filters(instance_type, pricing_region)` - Builds common EC2 pricing filters
- `_parse_hourly_price_from_dimensions(price_dimensions)` - Extracts hourly USD price (sync only)
- `_handle_throttling(attempt, max_retries, error)` - Handles API throttling with backoff (sync only)

These helpers consolidate common logic across `get_on_demand_price()`, `get_savings_plan_price()`, and `get_reserved_instance_price()` methods.

## Pricing API Response Schemas

The AWS Pricing API returns complex JSON structures that require careful parsing. Understanding these schemas is critical for maintaining pricing functionality.

### On-Demand Pricing Response

**API Call:** `pricing_client.get_products()` with filters for instance type, region, and product family.

**Response Structure:**
```json
{
  "PriceList": [
    "{\"product\": {\"attributes\": {...}}, \"terms\": {...}, \"version\": \"...\"}"
  ],
  "NextToken": "..."
}
```

**Important:** The `PriceList` contains JSON strings (not objects), so each item must be `json.loads()` parsed.

**Parsed Price List Item:**
```json
{
  "product": {
    "productFamily": "Compute Instance",
    "attributes": {
      "instanceType": "t3.micro",
      "location": "US East (N. Virginia)",
      "tenancy": "Shared",
      "operatingSystem": "Linux",
      "usagetype": "BoxUsage:t3.micro",
      ...
    }
  },
  "terms": {
    "OnDemand": {
      "JRTCKXETXF.JRTCKXETXF": {
        "priceDimensions": {
          "JRTCKXETXF.JRTCKXETXF.6YS6EN2CT7": {
            "unit": "Hrs",
            "pricePerUnit": {
              "USD": "0.0104000000"
            },
            "description": "...",
            "beginRange": "0",
            "endRange": "Inf"
          }
        },
        "termAttributes": {}
      }
    }
  }
}
```

**Parsing Pattern:**
1. Check `response.get('PriceList')` exists
2. `json.loads()` each `PriceList` item
3. Navigate: `price_data['terms']['OnDemand'][term_key]['priceDimensions'][dimension_key]`
4. Extract: `dimension_data['pricePerUnit']['USD']`
5. Filter by `unit == 'Hrs'` (hourly pricing)
6. Handle JPY prices: Convert to USD using approximate rate (150 JPY/USD)
7. Choose lowest price if multiple matches (avoids extended instances, convertible RI prices)

**Multi-Result Handling:**
- API can return multiple results for same instance type (different tenancy, capacity reservations, etc.)
- Verify `attributes['location']` matches target region
- Select lowest price among valid matches
- Fallback to first result if no matches found

### Spot Pricing Response

**API Call:** `ec2_client.describe_spot_price_history()` with filters for instance type and availability zones.

**Response Structure:**
```json
{
  "SpotPriceHistory": [
    {
      "InstanceType": "t3.micro",
      "SpotPrice": "0.003120",
      "Timestamp": "2024-01-11T20:30:00Z",
      "AvailabilityZone": "us-east-1a",
      "ProductDescription": "Linux/UNIX"
    },
    ...
  ]
}
```

**Parsing Pattern:**
1. Query all availability zones in region
2. Group results by AZ
3. Filter by `ProductDescription == 'Linux/UNIX'`
4. Average spot prices across all AZs
5. Return `float(spot_price_string)`

**Batching:**
- Up to 50 instance types per API call
- Set `MaxResults=100` to get history for all AZs
- Uses `asyncio.gather()` for parallel fetching

### Reserved Instance Pricing Response

**API Call:** `pricing_client.get_products()` with filters for instance type, region, and RI lease contract length.

**Response Structure:**
Similar to on-demand, but in `terms['Reserved']` instead of `OnDemand`:
```json
{
  "terms": {
    "Reserved": {
      "TERM_KEY": {
        "priceDimensions": {
          "DIMENSION_KEY.2TG2D8R56U": {
            "unit": "Quantity",
            "pricePerUnit": {
              "USD": "456"
            },
            "description": "Upfront Fee"
          },
          "DIMENSION_KEY.6YS6EN2CT7": {
            "unit": "Hrs",
            "pricePerUnit": {
              "USD": "0.0062"
            },
            "description": "USD 0.0062 per Linux/UNIX..."
          }
        },
        "termAttributes": {
          "LeaseContractLength": "1yr",
          "OfferingClass": "standard",
          "PurchaseOption": "Partial Upfront"
        }
      }
    }
  }
}
```

**Parsing Pattern:**
1. Navigate to `terms['Reserved']`
2. Find term matching: `termAttributes['LeaseContractLength']` (e.g., "1yr", "3yr")
3. Find term matching: `termAttributes['PurchaseOption']` (e.g., "No Upfront", "Partial Upfront", "All Upfront")
4. Calculate effective hourly rate:
   - Extract upfront fee: `unit == 'Quantity'` → `upfront_fee`
   - Extract hourly rate: `unit == 'Hrs'` → `hourly_rate`
   - Effective hourly = `(upfront_fee / (hours_in_term)) + hourly_rate`
   - For 1yr: 8760 hours, for 3yr: 26280 hours

**Payment Options:**
- **No Upfront:** Only hourly charges, no upfront fee
- **Partial Upfront:** Mix of upfront + reduced hourly
- **All Upfront:** Full upfront payment, $0 hourly

### Savings Plan Pricing Response

**API Call:** `pricing_client.get_products()` with filters for Compute Savings Plan.

**Response Structure:**
Similar to RI, but in `terms['savingsPlan']`:
```json
{
  "terms": {
    "savingsPlan": {
      "TERM_KEY": {
        "priceDimensions": {
          "DIMENSION_KEY": {
            "unit": "Hrs",
            "pricePerUnit": {
              "USD": "0.0062"
            }
          }
        },
        "termAttributes": {
          "LeaseContractLength": "1yr",
          "PurchaseOption": "No Upfront"
        }
      }
    }
  }
}
```

**Parsing Pattern:**
1. Navigate to `terms['savingsPlan']`
2. Match by `LeaseContractLength` (1yr/3yr)
3. Filter by `PurchaseOption` (typically "No Upfront")
4. Extract hourly rate from `priceDimensions`

**Note:** Savings Plans are simpler than RIs - typically no upfront fee dimension, just hourly rate.

### Error Responses and Edge Cases

**Empty PriceList:**
```json
{
  "PriceList": []
}
```
- Return `None` instead of failing
- Log at debug level for investigation
- Cache `None` to avoid repeated failures

**Throttling (429 Too Many Requests):**
```python
ClientError: An error occurred (Throttling) when calling the GetProducts operation...
```
- Caught as `botocore.exceptions.ClientError`
- Check `error.response['Error']['Code'] == 'Throttling'`
- Implement exponential backoff: 1s, 2s, 4s, 8s
- Configurable max retries (default: 3)

**Missing Currency:**
- Some regions return `JPY` instead of `USD`
- Convert using approximate rate: `150 JPY = 1 USD`
- Used primarily for `ap-northeast-1` (Tokyo) and `ap-northeast-3` (Osaka)

**Multiple Price Dimensions:**
- Some responses include multiple dimensions (different units, terms, etc.)
- Always filter by `unit == 'Hrs'` for hourly pricing
- Ignore dimensions with `unit == 'Quantity'` (upfront fees for RI) unless calculating effective rate

**Location Mismatch:**
- API sometimes returns results for similar region names
- Verify `attributes['location']` contains pricing_region substring
- Special handling for Osaka ("ap-northeast-3") which can match generic "Japan" location

### Caching Pricing Responses

**Cache Keys:** `{region}_{instance_type}_{price_type}.json`
- Example: `us-east-1_t3_micro_on_demand.json`
- Dots in instance type replaced with underscores

**What's Cached:**
- Raw price values (float or None)
- NOT full API responses (too large)
- Cache both successful lookups AND None values

**Cache TTL:** 4 hours (default, configurable)
- Pricing changes infrequently
- Reduces API calls by >90% in typical usage
- Spot prices updated every 5 minutes but averaged, so 4h TTL acceptable

## Caching System

The pricing cache (`src/cache.py`) provides persistent storage for pricing data:

### Architecture

- File-based cache in `~/.instancepedia/cache/`
- Individual JSON files per cache entry: `{region}_{instance_type}_{price_type}.json`
- Default TTL: 4 hours (configurable)
- Thread-safe using `threading.Lock()`
- Caches both successful lookups AND None values (to avoid repeated failures)

### Usage

- Both sync (`PricingService`) and async (`AsyncPricingService`) use the same cache
- Cache is checked first before API calls
- Results (including None) are cached to reduce API calls
- Cache statistics: `cache.get_stats()` returns total/valid/expired entries, size, age
- Cache management: `cache.clear()` with optional filters (region, instance_type)

### Cache Key Format

- Dots replaced with underscores: `us-east-1_t3_micro_on_demand.json`
- Separate files for on_demand vs spot prices

### Thread Safety

- All operations use `self._lock` for thread safety
- Safe for concurrent access from TUI and CLI modes
- Tested with ThreadPoolExecutor for concurrent operations

### Cache Statistics Tracking

- Cache hit tracking occurs DURING pricing fetch, not after
- `AsyncPricingService` uses `cache_hit_callback` to count hits
- Statistics passed to `InstanceList` when pricing completes
- Prevents false reporting where all prices appear cached

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

## Logging System

The logging system (`src/logging_config.py`) provides structured logging:

### Setup

- Use `logging.getLogger("instancepedia")` at module level
- Import logging: `import logging` then `logger = logging.getLogger("instancepedia")`
- TUI mode: Logs go to debug pane only (no console handler)
- CLI mode: Logs go to stderr

### Log Levels

- `logger.debug()` - Verbose information, cache hits, UI state changes
- `logger.info()` - General information, operations completed
- `logger.warning()` - Unexpected but recoverable situations
- `logger.error()` - Errors that need attention

### Example

```python
import logging

logger = logging.getLogger("instancepedia")

try:
    result = some_operation()
except Exception as e:
    logger.error(f"Operation failed: {e}", exc_info=True)
```
