# Error Handling Best Practices

This document provides guidelines for proper exception handling and error management in instancepedia.

## Exception Handling Principles

### NEVER Use Bare Except Blocks

**Bare `except:` blocks hide errors and make debugging extremely difficult.**

**Bad:**
```python
try:
    widget.update("status")
except:  # ❌ Bare except - hides all errors including KeyboardInterrupt
    pass
```

**Good:**
```python
try:
    widget.update("status")
except Exception as e:
    # Explain WHY this exception is expected
    logger.debug(f"Widget may not exist during screen transition: {e}")
```

**Why this matters:**
- Bare `except:` catches `SystemExit`, `KeyboardInterrupt`, and other critical exceptions
- Makes it impossible to debug unexpected errors
- Hides logic errors during development
- Can mask serious issues in production

### Pattern for Expected Exceptions

Use this pattern when an exception is expected and acceptable:

```python
try:
    # Operation that may fail for valid reasons
    self.screen.pop_screen()
except Exception as e:
    # Log at debug level with explanation of why it's expected
    logger.debug(f"Screen already popped or app shutting down: {e}")
```

**When to use:**
- UI updates during screen transitions
- Widget queries that may not exist yet
- Operations during app shutdown
- Race conditions between async operations

### Pattern for Unexpected Exceptions

Use this pattern when an exception should not occur and needs attention:

```python
try:
    # Critical operation that should succeed
    result = fetch_critical_data()
except Exception as e:
    # Log at error level with full traceback
    logger.error(f"Critical operation failed: {e}", exc_info=True)
    # Handle the error appropriately
    return None  # Or raise custom exception
```

**When to use:**
- Core business logic failures
- AWS API errors
- Data validation failures
- File I/O errors

## Custom Exceptions

Custom exceptions provide clear error types and better error handling:

### Custom Exception Classes

Located in `src/exceptions.py`:

```python
class AWSRegionError(Exception):
    """Raised when region is invalid or inaccessible"""
    pass

class AWSCredentialsError(Exception):
    """Raised when AWS credentials are missing or invalid"""
    pass

class AWSConnectionError(Exception):
    """Raised when connection to AWS fails"""
    pass

class InstanceTypeError(Exception):
    """Raised when instance type fetch fails"""
    pass
```

### Using Custom Exceptions

**Raising custom exceptions:**
```python
from src.exceptions import AWSRegionError

def validate_region(region: str):
    if region not in VALID_REGIONS:
        raise AWSRegionError(
            f"Invalid region '{region}'. "
            f"Use 'instancepedia regions' to see available regions."
        )
```

**Catching custom exceptions:**
```python
from src.exceptions import AWSRegionError, AWSCredentialsError

try:
    client = get_aws_client(region, profile)
except AWSRegionError as e:
    print(f"Region error: {e}", file=sys.stderr)
    sys.exit(1)
except AWSCredentialsError as e:
    print(f"Credentials error: {e}", file=sys.stderr)
    sys.exit(1)
```

## Region-Specific Error Handling

Enhanced error handling for region-related issues provides clear, actionable error messages:

### Error Detection and Messages

**Invalid region names:**
```python
# Before
AWS API error (InvalidRegion): The region 'us-west-99' is not valid

# After
Invalid AWS region: 'us-west-99'.
Use 'instancepedia regions' to see available regions.
```

**Regions not enabled:**
```python
# Before
AWS API error (AuthFailure): You are not authorized...

# After
Not authorized to access EC2 in region 'ap-southeast-4'.
This region may not be enabled for your account or you may lack permissions.
Use 'instancepedia regions' to see available regions.
```

### Implementation Pattern

```python
from src.exceptions import AWSRegionError

def handle_region_error(error, region):
    """Convert AWS errors to user-friendly messages"""
    error_str = str(error)

    if "InvalidRegion" in error_str:
        raise AWSRegionError(
            f"Invalid AWS region: '{region}'. "
            f"Use 'instancepedia regions' to see available regions."
        )

    if "AuthFailure" in error_str or "UnauthorizedOperation" in error_str:
        raise AWSRegionError(
            f"Not authorized to access EC2 in region '{region}'. "
            f"This region may not be enabled for your account or you may lack permissions. "
            f"Use 'instancepedia regions' to see available regions."
        )

    # Re-raise if not a known region error
    raise
```

## Logging Best Practices

### Log Levels

Use appropriate log levels for different scenarios:

```python
import logging
logger = logging.getLogger("instancepedia")

# DEBUG - Verbose information, useful for debugging
logger.debug(f"Cache hit for {instance_type} in {region}")
logger.debug(f"Tree state: {len(self.tree.root.children)} categories")

# INFO - General information about operations
logger.info(f"Fetched {len(instances)} instance types from {region}")
logger.info(f"Pricing fetch completed: {metrics.summary()}")

# WARNING - Unexpected but recoverable situations
logger.warning(f"Pricing unavailable for {instance_type}, using cached data")
logger.warning(f"Throttling detected, retrying in {delay}s")

# ERROR - Errors that need attention
logger.error(f"Failed to fetch pricing for {instance_type}: {e}", exc_info=True)
logger.error(f"AWS API error: {e}", exc_info=True)
```

### Logging with Stack Traces

Use `exc_info=True` to include full stack trace:

```python
try:
    result = risky_operation()
except Exception as e:
    # Include full traceback for debugging
    logger.error(f"Operation failed: {e}", exc_info=True)
```

### Conditional Debug Logging

Avoid expensive operations in debug logging:

```python
# Bad - always evaluates expression
logger.debug(f"Data: {expensive_serialization(data)}")

# Good - only evaluates if debug enabled
if logger.isEnabledFor(logging.DEBUG):
    logger.debug(f"Data: {expensive_serialization(data)}")
```

## Error Handling in Different Contexts

### CLI Error Handling

CLI commands should handle errors gracefully and exit with appropriate codes:

```python
def cmd_list(args):
    """List instance types"""
    try:
        # Get AWS client
        aws_client = get_aws_client(args.region, args.profile)

        # Fetch instances
        service = InstanceService(aws_client)
        instances = service.get_instance_types(args.region)

        # Display results
        formatter = get_formatter(args.format)
        print(formatter.format_instances(instances))

    except AWSRegionError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except AWSCredentialsError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        if args.debug:
            logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
```

### TUI Error Handling

TUI should display errors in the UI and not crash:

```python
async def fetch_data(self):
    """Fetch data with error handling"""
    try:
        # Fetch data
        data = await self.service.get_data()

        # Update UI
        self.update_display(data)

    except Exception as e:
        # Log error
        logger.error(f"Failed to fetch data: {e}", exc_info=True)

        # Show error in UI
        self.app.push_screen(
            ErrorScreen(
                error=e,
                title="Data Fetch Error",
                message="Failed to fetch data. Please try again."
            )
        )
```

### Service Error Handling

Services should handle AWS errors and return appropriate values:

```python
def get_on_demand_price(self, instance_type: str, region: str) -> Optional[float]:
    """Get on-demand price with error handling"""
    try:
        # Check cache
        cached = self.cache.get(region, instance_type, "on_demand")
        if cached is not None:
            return cached

        # Fetch from API
        price = self._fetch_price_from_api(instance_type, region)

        # Cache result
        self.cache.set(region, instance_type, "on_demand", price)

        return price

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')

        if error_code == 'Throttling':
            logger.warning(f"Throttled while fetching price for {instance_type}")
            # Retry with backoff
            return self._retry_with_backoff(instance_type, region)

        # Log error and return None
        logger.error(f"AWS error fetching price for {instance_type}: {e}")
        return None

    except Exception as e:
        # Unexpected error - log and return None
        logger.error(f"Unexpected error fetching price for {instance_type}: {e}", exc_info=True)
        return None
```

## Retry Logic

### Exponential Backoff Pattern

Use exponential backoff for retrying AWS API calls:

```python
def _handle_throttling(self, attempt: int, max_retries: int, error: Exception):
    """Handle API throttling with exponential backoff"""
    if attempt >= max_retries:
        logger.error(f"Max retries ({max_retries}) exceeded: {error}")
        return None

    # Exponential backoff: 1s, 2s, 4s, 8s
    delay = 2 ** attempt
    logger.warning(f"Throttled (attempt {attempt + 1}/{max_retries}), retrying in {delay}s")

    time.sleep(delay)
```

### Retry Decorator Pattern

Create reusable retry logic:

```python
from functools import wraps
import time

def retry_on_throttle(max_retries=3):
    """Decorator to retry on throttling errors"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except ClientError as e:
                    if e.response.get('Error', {}).get('Code') == 'Throttling':
                        if attempt < max_retries - 1:
                            delay = 2 ** attempt
                            logger.warning(f"Throttled, retrying in {delay}s")
                            time.sleep(delay)
                            continue
                    raise
            return None
        return wrapper
    return decorator

@retry_on_throttle(max_retries=3)
def fetch_pricing(instance_type, region):
    """Fetch pricing with automatic retry on throttling"""
    return api.get_products(...)
```

## Graceful Degradation

Services should degrade gracefully when non-critical features fail:

```python
def get_instance_with_pricing(self, instance_type: str, region: str) -> InstanceType:
    """Get instance with pricing, falling back to instance-only on error"""
    # Fetch instance (critical)
    instance = self.get_instance_type(instance_type, region)
    if not instance:
        raise InstanceTypeError(f"Instance type '{instance_type}' not found")

    # Fetch pricing (optional)
    try:
        pricing = self.get_pricing(instance_type, region)
        instance.pricing = pricing
    except Exception as e:
        # Log but don't fail - pricing is optional
        logger.warning(f"Could not fetch pricing for {instance_type}: {e}")
        instance.pricing = None

    return instance
```

## Error Messages

### User-Friendly Error Messages

Provide actionable error messages:

```python
# Bad
"Error: Invalid input"

# Good
"Invalid region 'us-west-99'. Use 'instancepedia regions' to see available regions."
```

### Include Context

Include relevant context in error messages:

```python
# Bad
raise Exception("Pricing not found")

# Good
raise Exception(
    f"Pricing not found for instance type '{instance_type}' "
    f"in region '{region}'. This instance may not be available in this region."
)
```

### Suggest Solutions

Help users resolve the issue:

```python
# Bad
"Authentication failed"

# Good
"AWS authentication failed. Please check:\n"
"1. AWS credentials are configured (aws configure)\n"
"2. Credentials have EC2 read permissions\n"
"3. Profile name is correct (use --profile if needed)"
```
