# Configuration Guide

Comprehensive guide to configuring Instancepedia for your workflow.

## Table of Contents

- [Configuration File](#configuration-file)
- [AWS Configuration](#aws-configuration)
- [TUI Settings](#tui-settings)
- [CLI Settings](#cli-settings)
- [Performance Tuning](#performance-tuning)
- [Cache Configuration](#cache-configuration)
- [Filter Presets](#filter-presets)
- [Environment Variables](#environment-variables)
- [Advanced Configuration](#advanced-configuration)

## Configuration File

Instancepedia uses a TOML configuration file located at:

```
~/.instancepedia/config.toml
```

### Creating the Configuration File

The config file is optional. Instancepedia works with defaults if no config exists.

To create a config file:

```bash
mkdir -p ~/.instancepedia
cat > ~/.instancepedia/config.toml <<EOF
# Instancepedia Configuration

# Default AWS region
default_region = "us-east-1"

# Enable Vim-style navigation (hjkl)
vim_keys = false

# TUI pricing concurrency (5-50)
tui_pricing_concurrency = 20

# CLI pricing concurrency (5-100)
cli_pricing_concurrency = 50

# Pricing cache TTL in seconds (default: 4 hours)
pricing_cache_ttl = 14400
EOF
```

### Configuration File Structure

```toml
# AWS Settings
default_region = "us-east-1"
aws_profile = "my-profile"  # Optional

# TUI Settings
vim_keys = false
tui_pricing_concurrency = 20

# CLI Settings
cli_pricing_concurrency = 50
default_output_format = "table"
default_sort = "name"

# Cache Settings
pricing_cache_ttl = 14400
instance_cache_ttl = 86400
spot_cache_ttl = 900
region_cache_ttl = 604800

# Debug Settings
debug_mode = false
log_level = "INFO"
```

## AWS Configuration

### Default Region

Set the default AWS region for all operations:

```toml
default_region = "us-east-1"
```

**Available Regions**:
- US East: `us-east-1`, `us-east-2`
- US West: `us-west-1`, `us-west-2`
- Europe: `eu-west-1`, `eu-west-2`, `eu-west-3`, `eu-central-1`, `eu-north-1`
- Asia Pacific: `ap-south-1`, `ap-northeast-1`, `ap-northeast-2`, `ap-southeast-1`, `ap-southeast-2`
- Canada: `ca-central-1`
- South America: `sa-east-1`
- Middle East: `me-south-1`
- Africa: `af-south-1`

**Note**: You can override the default region with `--region` flag in CLI commands.

### AWS Profile

Use a named AWS CLI profile:

```toml
aws_profile = "my-profile"
```

This is equivalent to `export AWS_PROFILE=my-profile`.

**When to use**:
- Multiple AWS accounts
- Different credential sets
- Separate development/production profiles

**Override in CLI**:
```bash
instancepedia --profile production list
```

### AWS Credentials

Instancepedia supports standard AWS credential methods (in order of precedence):

1. **Environment Variables**:
   ```bash
   export AWS_ACCESS_KEY_ID=your-key
   export AWS_SECRET_ACCESS_KEY=your-secret
   export AWS_SESSION_TOKEN=your-token  # Optional, for temporary credentials
   ```

2. **Named Profile** (via config or env var):
   ```bash
   export AWS_PROFILE=my-profile
   ```

3. **AWS CLI Configuration** (`~/.aws/credentials`):
   ```ini
   [default]
   aws_access_key_id = your-key
   aws_secret_access_key = your-secret

   [production]
   aws_access_key_id = prod-key
   aws_secret_access_key = prod-secret
   ```

4. **IAM Instance Profile** (when running on EC2)

### Required AWS Permissions

Minimum IAM policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstanceTypes",
        "ec2:DescribeSpotPriceHistory",
        "ec2:DescribeRegions",
        "pricing:GetProducts"
      ],
      "Resource": "*"
    }
  ]
}
```

**All these APIs are free** - Instancepedia never incurs AWS charges.

## TUI Settings

Settings specific to the interactive TUI mode.

### Vim-Style Navigation

Enable `hjkl` Vim-style navigation keys:

```toml
vim_keys = true
```

**When enabled**:
- `h`: Move left / Collapse
- `j`: Move down
- `k`: Move up
- `l`: Move right / Expand

**Default**: `false` (uses arrow keys only)

**Note**: Arrow keys still work when Vim keys are enabled.

### TUI Pricing Concurrency

Number of concurrent pricing API calls in TUI:

```toml
tui_pricing_concurrency = 20
```

**Range**: 5-50
**Default**: 20

**Considerations**:
- **Higher values** (30-50): Faster pricing loads, more API calls
- **Lower values** (5-15): Slower pricing loads, gentler on API limits
- **Sweet spot** (15-25): Balance between speed and API usage

**When to adjust**:
- **Increase** if you have high AWS API limits and want faster loads
- **Decrease** if you encounter rate limiting errors

### TUI Default Sort

Default sort order when launching TUI:

```toml
tui_default_sort = "name"
```

**Options**: `name`, `vcpu`, `memory`, `price`
**Default**: `name`

**Note**: You can cycle through sort options with `S` key in TUI.

## CLI Settings

Settings specific to CLI commands.

### CLI Pricing Concurrency

Number of concurrent pricing API calls in CLI:

```toml
cli_pricing_concurrency = 50
```

**Range**: 5-100
**Default**: 50

**Considerations**:
- **Higher values** (60-100): Much faster for bulk operations
- **Lower values** (10-30): Safer for accounts with API limits
- **Default** (50): Good balance for most users

**When to adjust**:
- **Increase** for large-scale automation with high API limits
- **Decrease** if encountering throttling errors

### Default Output Format

Default format for CLI list commands:

```toml
default_output_format = "table"
```

**Options**: `table`, `json`, `csv`
**Default**: `table`

**Examples**:
- `table`: Human-readable tabular output
- `json`: Machine-readable for scripting
- `csv`: Spreadsheet-friendly

**Override in CLI**:
```bash
instancepedia list --format json
```

### Default Sort Order

Default sort for CLI list commands:

```toml
default_sort = "name"
```

**Options**: `name`, `vcpu`, `memory`, `price`
**Default**: `name`

**Override in CLI**:
```bash
instancepedia list --sort price
```

### Quiet Mode Default

Suppress headers and formatting by default:

```toml
quiet_mode = false
```

**Default**: `false` (show headers)

**When enabled**: Removes headers and formatting for cleaner scripting output.

**Override in CLI**:
```bash
instancepedia list --quiet
```

## Performance Tuning

Optimize Instancepedia for your use case.

### Cache TTL Settings

Control how long data is cached:

```toml
# Pricing cache (default: 4 hours = 14400 seconds)
pricing_cache_ttl = 14400

# Instance types cache (default: 24 hours = 86400 seconds)
instance_cache_ttl = 86400

# Spot price cache (default: 15 minutes = 900 seconds)
spot_cache_ttl = 900

# Region list cache (default: 7 days = 604800 seconds)
region_cache_ttl = 604800
```

**Considerations**:
- **Longer TTL**: Fewer API calls, faster subsequent runs, potentially stale data
- **Shorter TTL**: More API calls, slower, fresher data

**Recommendations**:
- **Pricing**: 1-6 hours (pricing changes infrequently)
- **Spot**: 10-30 minutes (spot prices change frequently)
- **Instances**: 12-48 hours (instance types change rarely)
- **Regions**: 7+ days (regions almost never change)

### Aggressive Caching

For maximum speed, minimal API usage:

```toml
pricing_cache_ttl = 21600     # 6 hours
instance_cache_ttl = 172800   # 48 hours
spot_cache_ttl = 1800         # 30 minutes
region_cache_ttl = 2592000    # 30 days
```

### Fresh Data Priority

For minimum staleness, maximum freshness:

```toml
pricing_cache_ttl = 3600      # 1 hour
instance_cache_ttl = 43200    # 12 hours
spot_cache_ttl = 600          # 10 minutes
region_cache_ttl = 86400      # 1 day
```

## Cache Configuration

### Cache Location

Cache files are stored at:

```
~/.instancepedia/cache/
```

**Files**:
- `instance_types_{region}.json`: Instance specifications
- `pricing_{instance_type}_{region}.json`: Pricing data
- `spot_prices_{instance_type}_{region}.json`: Spot price history
- `regions.json`: Available AWS regions

### Cache Management

**View cache statistics**:
```bash
instancepedia cache stats
```

**Clear all caches**:
```bash
instancepedia cache clear
```

**Clear specific cache type**:
```bash
instancepedia cache clear --type pricing
instancepedia cache clear --type instances
instancepedia cache clear --type spot
instancepedia cache clear --type regions
```

**Clear for specific region**:
```bash
instancepedia cache clear --region us-east-1
```

### Cache Behavior

**First run**:
- Fetches all data from AWS APIs
- Populates cache
- Takes 20-60 seconds depending on concurrency settings

**Subsequent runs**:
- Reads from cache
- Instant results (< 1 second)
- Refreshes expired entries in background

**Cache invalidation**:
- Automatic based on TTL
- Manual with `cache clear` command
- Per-entry (individual instance types, regions, etc.)

## Filter Presets

Manage custom filter presets.

### Preset Location

Presets are stored at:

```
~/.instancepedia/presets/filter_presets.json
```

### Built-in Presets

Cannot be modified or deleted:
- `web-server`
- `database`
- `compute-intensive`
- `gpu-ml`
- `development`
- `memory-intensive`
- `budget`
- `arm`

### Custom Presets

**Create custom preset (CLI)**:
```bash
instancepedia presets save my-api-server \
  --min-vcpu 4 \
  --min-memory 8 \
  --architecture arm64 \
  --current-generation
```

**Create custom preset (TUI)**:
1. Press `F` to open filter modal
2. Set desired filters
3. Click **Save Preset** button
4. Enter preset name and description

**Load preset (CLI)**:
```bash
instancepedia presets apply my-api-server
```

**Load preset (TUI)**:
1. Press `F` to open filter modal
2. Select preset from dropdown
3. Filters auto-populate

**Delete preset (CLI)**:
```bash
instancepedia presets delete my-api-server
```

**List all presets**:
```bash
instancepedia presets list
```

### Preset File Format

`~/.instancepedia/presets/filter_presets.json`:

```json
{
  "custom_presets": [
    {
      "name": "my-api-server",
      "description": "API server instances",
      "min_vcpu": 4,
      "min_memory": 8,
      "architecture": "arm64",
      "current_generation_only": true
    }
  ]
}
```

## Environment Variables

Override configuration with environment variables.

| Environment Variable | Config Equivalent | Description |
|---------------------|-------------------|-------------|
| `AWS_REGION` | `default_region` | Default AWS region |
| `AWS_DEFAULT_REGION` | `default_region` | Default AWS region (alternate) |
| `AWS_PROFILE` | `aws_profile` | AWS CLI profile name |
| `AWS_ACCESS_KEY_ID` | N/A | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | N/A | AWS secret key |
| `AWS_SESSION_TOKEN` | N/A | AWS session token (temp creds) |
| `INSTANCEPEDIA_DEBUG` | `debug_mode` | Enable debug logging |
| `INSTANCEPEDIA_CONFIG` | N/A | Override config file path |

**Example**:

```bash
# Use specific region and profile
export AWS_REGION=us-west-2
export AWS_PROFILE=production
instancepedia

# Override config file location
export INSTANCEPEDIA_CONFIG=/custom/path/config.toml
instancepedia
```

**Precedence** (highest to lowest):
1. Command-line flags (`--region`, `--profile`)
2. Environment variables (`AWS_REGION`, `AWS_PROFILE`)
3. Configuration file (`~/.instancepedia/config.toml`)
4. Built-in defaults

## Advanced Configuration

### Debug Mode

Enable verbose debug logging:

```toml
debug_mode = true
log_level = "DEBUG"
```

**Logs include**:
- API requests and responses
- Cache hits/misses
- Timing information
- Error stack traces

**Enable via CLI**:
```bash
instancepedia --debug
```

**Enable via environment**:
```bash
export INSTANCEPEDIA_DEBUG=1
instancepedia
```

### Log Level

Control logging verbosity:

```toml
log_level = "INFO"
```

**Options**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
**Default**: `INFO`

**Descriptions**:
- `DEBUG`: Everything (very verbose)
- `INFO`: General information (default)
- `WARNING`: Warnings and errors
- `ERROR`: Errors only
- `CRITICAL`: Critical errors only

### Custom Cache Directory

Override default cache location:

```toml
cache_directory = "/custom/path/to/cache"
```

**Default**: `~/.instancepedia/cache/`

**Use cases**:
- Shared cache across users
- Network storage
- Custom backup strategy

### Custom Preset Directory

Override default preset location:

```toml
preset_directory = "/custom/path/to/presets"
```

**Default**: `~/.instancepedia/presets/`

**Use cases**:
- Team-shared presets (network drive)
- Version-controlled presets (git repo)
- Multiple preset collections

### Timeout Settings

Configure API request timeouts:

```toml
api_timeout = 30
api_retry_attempts = 3
api_retry_delay = 2
```

**Defaults**:
- `api_timeout`: 30 seconds
- `api_retry_attempts`: 3 retries
- `api_retry_delay`: 2 seconds between retries

**Increase timeouts** if you have slow/unstable internet connection.

**Decrease timeouts** for faster failure detection in automation.

## Configuration Examples

### Minimal Configuration

Just set the region:

```toml
default_region = "us-east-1"
```

### Recommended Configuration

Balanced settings for most users:

```toml
# AWS Settings
default_region = "us-east-1"

# TUI Settings
vim_keys = false
tui_pricing_concurrency = 20

# CLI Settings
cli_pricing_concurrency = 50
default_output_format = "table"

# Cache Settings (defaults)
pricing_cache_ttl = 14400
instance_cache_ttl = 86400
spot_cache_ttl = 900
```

### Power User Configuration

Maximum speed and concurrency:

```toml
# AWS Settings
default_region = "us-east-1"

# TUI Settings
vim_keys = true
tui_pricing_concurrency = 40

# CLI Settings
cli_pricing_concurrency = 80
default_output_format = "json"
quiet_mode = true

# Aggressive caching
pricing_cache_ttl = 21600     # 6 hours
instance_cache_ttl = 172800   # 48 hours
spot_cache_ttl = 1800         # 30 minutes
region_cache_ttl = 2592000    # 30 days
```

### Development Configuration

Fresh data and debug logging:

```toml
# AWS Settings
default_region = "us-east-1"

# Debug
debug_mode = true
log_level = "DEBUG"

# Fresh data
pricing_cache_ttl = 3600
instance_cache_ttl = 43200
spot_cache_ttl = 600

# Conservative concurrency
tui_pricing_concurrency = 10
cli_pricing_concurrency = 20
```

### Automation/CI Configuration

Optimized for scripts and pipelines:

```toml
# AWS Settings
default_region = "us-east-1"

# CLI optimized
cli_pricing_concurrency = 100
default_output_format = "json"
quiet_mode = true

# Aggressive caching (CI builds)
pricing_cache_ttl = 86400     # 24 hours
instance_cache_ttl = 604800   # 7 days

# Fast failure
api_timeout = 15
api_retry_attempts = 2
api_retry_delay = 1
```

## Troubleshooting Configuration

### Configuration Not Loading

**Symptom**: Changes to config file have no effect.

**Solutions**:
1. Check config file path: `~/.instancepedia/config.toml`
2. Verify TOML syntax (use a TOML validator)
3. Check for trailing whitespace or invalid characters
4. Ensure file permissions are readable: `chmod 644 ~/.instancepedia/config.toml`

### AWS Credentials Not Found

**Symptom**: "Unable to locate credentials" error.

**Solutions**:
1. Run `aws configure` to set up credentials
2. Verify credentials file exists: `~/.aws/credentials`
3. Check `AWS_PROFILE` environment variable
4. Verify IAM permissions (see [Required AWS Permissions](#required-aws-permissions))

### Rate Limiting Errors

**Symptom**: "Rate exceeded" or "Throttling" errors.

**Solutions**:
1. Reduce concurrency:
   ```toml
   tui_pricing_concurrency = 10
   cli_pricing_concurrency = 20
   ```
2. Increase cache TTL to reduce API calls:
   ```toml
   pricing_cache_ttl = 21600  # 6 hours
   ```
3. Wait a few minutes and retry
4. Contact AWS support to increase API limits

### Cache Issues

**Symptom**: Stale data or cache corruption.

**Solutions**:
1. Clear all caches: `instancepedia cache clear`
2. Clear specific cache: `instancepedia cache clear --type pricing`
3. Delete cache directory: `rm -rf ~/.instancepedia/cache/`
4. Restart instancepedia

## See Also

- [QUICKSTART.md](QUICKSTART.md) - Get started quickly
- [CLI_REFERENCE.md](CLI_REFERENCE.md) - All CLI commands
- [FEATURES.md](FEATURES.md) - Complete feature list
- [EXAMPLES.md](EXAMPLES.md) - Real-world scenarios
