# CLI Command Reference

Complete reference for all Instancepedia CLI commands.

## Table of Contents

- [Global Options](#global-options)
- [Instance Commands](#instance-commands)
- [Pricing Commands](#pricing-commands)
- [Comparison Commands](#comparison-commands)
- [Preset Commands](#preset-commands)
- [Utility Commands](#utility-commands)
- [Filter Options](#filter-options)
- [Output Formats](#output-formats)

## Global Options

Available for all commands:

| Option | Description |
|--------|-------------|
| `--region REGION` | Override default AWS region |
| `--profile PROFILE` | Use specific AWS CLI profile |
| `--debug` | Enable debug logging |
| `--version` | Show version and exit |
| `--help` | Show help message |

**Examples**:

```bash
# Use specific region
instancepedia list --region us-west-2

# Use specific AWS profile
instancepedia --profile production list

# Enable debug mode
instancepedia --debug list
```

## Instance Commands

### `instancepedia` (TUI Mode)

Launch interactive Terminal User Interface.

```bash
instancepedia [--region REGION] [--profile PROFILE]
```

**Options**:
- `--region`: Override default region
- `--profile`: Use specific AWS profile
- `--debug`: Enable debug mode

**Examples**:

```bash
# Launch TUI with defaults
instancepedia

# Launch TUI for specific region
instancepedia --region eu-west-1

# Launch with debug logging
instancepedia --debug
```

### `list`

List instance types with optional filters.

```bash
instancepedia list [FILTER_OPTIONS] [OUTPUT_OPTIONS]
```

**Output Options**:
- `--format FORMAT`: Output format (table, json, csv)
- `--sort FIELD`: Sort by field (name, vcpu, memory, price)
- `--quiet`: Suppress headers (for scripting)

**Examples**:

```bash
# List all instances (table format)
instancepedia list

# List with filters
instancepedia list --min-vcpu 4 --min-memory 8 --current-generation

# JSON output for scripting
instancepedia list --format json

# Sorted by price, CSV format
instancepedia list --sort price --format csv

# Quiet mode for piping
instancepedia list --quiet --format json | jq '.[0].instance_type'

# Find cheapest current-gen instances
instancepedia list --current-generation --sort price | head -20
```

**See [Filter Options](#filter-options) for all filter flags.**

### `show`

Show detailed information for a specific instance type.

```bash
instancepedia show INSTANCE_TYPE [--region REGION]
```

**Arguments**:
- `INSTANCE_TYPE`: Instance type to show (e.g., t3.micro, m5.large)

**Options**:
- `--region`: AWS region for pricing
- `--format`: Output format (table, json)

**Examples**:

```bash
# Show details for t3.micro
instancepedia show t3.micro

# Show with pricing for specific region
instancepedia show m5.xlarge --region us-west-2

# JSON output
instancepedia show c6i.2xlarge --format json
```

### `search`

Search for instances matching a query.

```bash
instancepedia search QUERY [FILTER_OPTIONS] [OUTPUT_OPTIONS]
```

**Arguments**:
- `QUERY`: Search query (instance type, family, or attribute)

**Examples**:

```bash
# Search for t3 instances
instancepedia search t3

# Search with filters
instancepedia search graviton --architecture arm64

# Search and export
instancepedia search "memory optimized" --format csv > results.csv
```

## Pricing Commands

### `pricing`

Get comprehensive pricing information for an instance type.

```bash
instancepedia pricing INSTANCE_TYPE [--region REGION] [--format FORMAT]
```

**Arguments**:
- `INSTANCE_TYPE`: Instance type to price

**Options**:
- `--region`: AWS region (default: us-east-1)
- `--format`: Output format (table, json)

**Pricing Types Shown**:
- On-Demand (hourly)
- Spot (current price)
- Reserved Instances (1-year, 3-year, all payment options)
- Savings Plans (Compute and EC2, 1-year and 3-year)

**Examples**:

```bash
# Get all pricing for t3.micro
instancepedia pricing t3.micro

# Pricing in specific region
instancepedia pricing m5.xlarge --region us-west-2

# JSON output for scripting
instancepedia pricing c6i.2xlarge --format json
```

### `spot-history`

Get historical spot price data with statistics.

```bash
instancepedia spot-history INSTANCE_TYPE [OPTIONS]
```

**Arguments**:
- `INSTANCE_TYPE`: Instance type

**Options**:
- `--region REGION`: AWS region
- `--days DAYS`: Number of days of history (default: 30)
- `--format FORMAT`: Output format (table, json)

**Statistics Shown**:
- Current spot price
- Average price over period
- Minimum and maximum prices
- Standard deviation (volatility)
- Percentage of on-demand price

**Examples**:

```bash
# 30-day spot history for t3.micro
instancepedia spot-history t3.micro

# 90-day history in specific region
instancepedia spot-history m5.large --region us-east-1 --days 90

# JSON output
instancepedia spot-history c5.xlarge --format json
```

### `optimize`

Get cost optimization recommendations for an instance type.

```bash
instancepedia optimize INSTANCE_TYPE [OPTIONS]
```

**Arguments**:
- `INSTANCE_TYPE`: Instance type to optimize

**Options**:
- `--region REGION`: AWS region
- `--usage-pattern PATTERN`: Usage pattern (standard, spot, database, intermittent)
- `--format FORMAT`: Output format (table, json)

**Recommendations Include**:
- Spot instance savings potential
- Reserved Instance options (1-year, 3-year)
- Savings Plans options
- Right-sizing suggestions
- Alternative instance types

**Examples**:

```bash
# Basic optimization recommendations
instancepedia optimize t3.medium

# Optimize for database workload
instancepedia optimize r6i.xlarge --usage-pattern database

# Optimize for intermittent use (spot-friendly)
instancepedia optimize m5.large --usage-pattern intermittent

# JSON output
instancepedia optimize c6i.2xlarge --format json --region us-west-2
```

### `cost-estimate`

Estimate monthly cost for an instance.

```bash
instancepedia cost-estimate INSTANCE_TYPE [OPTIONS]
```

**Arguments**:
- `INSTANCE_TYPE`: Instance type

**Options**:
- `--hours HOURS`: Hours per month (default: 730 = 24/7)
- `--region REGION`: AWS region
- `--pricing-model MODEL`: Pricing model (on-demand, spot, reserved-1y, savings-plan-1y)
- `--format FORMAT`: Output format (table, json)

**Examples**:

```bash
# Estimate 24/7 cost (730 hours/month)
instancepedia cost-estimate t3.medium

# Estimate for 50 hours/week (220 hours/month)
instancepedia cost-estimate t3.medium --hours 220

# Estimate with spot pricing
instancepedia cost-estimate m5.xlarge --pricing-model spot

# Estimate with 1-year savings plan
instancepedia cost-estimate c6i.2xlarge --pricing-model savings-plan-1y
```

## Comparison Commands

### `compare`

Compare two instance types side-by-side.

```bash
instancepedia compare INSTANCE_TYPE1 INSTANCE_TYPE2 [OPTIONS]
```

**Arguments**:
- `INSTANCE_TYPE1`: First instance type
- `INSTANCE_TYPE2`: Second instance type

**Options**:
- `--region REGION`: AWS region for pricing
- `--format FORMAT`: Output format (table, json)

**Comparison Shows**:
- Side-by-side specifications
- Price differences
- Feature differences
- Performance ratios

**Examples**:

```bash
# Compare t3.medium vs t3a.medium
instancepedia compare t3.medium t3a.medium

# Compare Intel vs Graviton
instancepedia compare m5.large m6g.large

# JSON output
instancepedia compare c6i.xlarge c7g.xlarge --format json
```

### `compare-family`

Compare all instances within a family.

```bash
instancepedia compare-family FAMILY [OPTIONS]
```

**Arguments**:
- `FAMILY`: Instance family (e.g., t3, m5, c6i)

**Options**:
- `--region REGION`: AWS region for pricing
- `--sort FIELD`: Sort by field (name, vcpu, memory, price)
- `--format FORMAT`: Output format (table, json, csv)

**Examples**:

```bash
# Compare all t3 instances
instancepedia compare-family t3

# Compare m5 family, sorted by memory
instancepedia compare-family m5 --sort memory

# Compare c6i family, sorted by price
instancepedia compare-family c6i --sort price --format csv
```

### `compare-regions`

Compare pricing for an instance across multiple regions.

```bash
instancepedia compare-regions INSTANCE_TYPE --regions REGION_LIST [OPTIONS]
```

**Arguments**:
- `INSTANCE_TYPE`: Instance type

**Required Options**:
- `--regions REGIONS`: Comma-separated list of regions

**Other Options**:
- `--format FORMAT`: Output format (table, json, csv)

**Shows**:
- On-demand and spot pricing for each region
- Sorted by price (cheapest first)
- Regional availability

**Examples**:

```bash
# Compare t3.micro across 3 regions
instancepedia compare-regions t3.micro \
  --regions us-east-1,us-west-2,eu-west-1

# Compare all US regions
instancepedia compare-regions m5.xlarge \
  --regions us-east-1,us-east-2,us-west-1,us-west-2

# JSON output
instancepedia compare-regions c6i.2xlarge \
  --regions us-east-1,eu-west-1,ap-southeast-1 \
  --format json
```

## Preset Commands

### `presets list`

List all available filter presets (built-in and custom).

```bash
instancepedia presets list [--format FORMAT]
```

**Options**:
- `--format FORMAT`: Output format (table, json)

**Shows**:
- Preset name
- Description
- Filter criteria
- Type (built-in or custom)

**Examples**:

```bash
# List all presets
instancepedia presets list

# JSON output
instancepedia presets list --format json
```

### `presets apply`

Apply a preset and show matching instances.

```bash
instancepedia presets apply PRESET_NAME [OUTPUT_OPTIONS]
```

**Arguments**:
- `PRESET_NAME`: Name of preset to apply

**Output Options**:
- `--format FORMAT`: Output format (table, json, csv)
- `--sort FIELD`: Sort results
- `--region REGION`: AWS region

**Examples**:

```bash
# Apply web-server preset
instancepedia presets apply web-server

# Apply preset and sort by price
instancepedia presets apply database --sort price

# Apply custom preset
instancepedia presets apply my-api-server --format json
```

### `presets save`

Save current filters as a custom preset.

```bash
instancepedia presets save PRESET_NAME [FILTER_OPTIONS] [--description DESC]
```

**Arguments**:
- `PRESET_NAME`: Name for the new preset

**Options**:
- `--description DESC`: Optional description
- `--force`: Overwrite existing preset without confirmation
- All filter options (see [Filter Options](#filter-options))

**Examples**:

```bash
# Save a simple preset
instancepedia presets save my-dev-box \
  --min-vcpu 2 \
  --max-vcpu 4 \
  --min-memory 4 \
  --description "Development workstation"

# Save complex preset
instancepedia presets save ml-training \
  --has-gpu \
  --min-vcpu 16 \
  --min-memory 64 \
  --architecture x86_64 \
  --current-generation \
  --description "ML training instances"

# Overwrite existing preset
instancepedia presets save api-server \
  --min-vcpu 4 \
  --architecture arm64 \
  --force
```

### `presets delete`

Delete a custom preset.

```bash
instancepedia presets delete PRESET_NAME [--force]
```

**Arguments**:
- `PRESET_NAME`: Name of preset to delete

**Options**:
- `--force`: Skip confirmation prompt

**Notes**:
- Cannot delete built-in presets
- Confirmation required unless `--force` is used

**Examples**:

```bash
# Delete preset (with confirmation)
instancepedia presets delete my-old-preset

# Delete without confirmation
instancepedia presets delete my-preset --force
```

## Utility Commands

### `regions`

List all available AWS regions.

```bash
instancepedia regions [--format FORMAT]
```

**Options**:
- `--format FORMAT`: Output format (table, json)

**Shows**:
- Region code
- Region name
- Geographic location

**Examples**:

```bash
# List all regions
instancepedia regions

# JSON output
instancepedia regions --format json
```

### `cache stats`

Show cache statistics.

```bash
instancepedia cache stats
```

**Shows**:
- Cache directory location
- Cache size
- Number of cached items by type
- Cache hit rate (if available)

**Example**:

```bash
instancepedia cache stats
```

### `cache clear`

Clear cached data.

```bash
instancepedia cache clear [OPTIONS]
```

**Options**:
- `--type TYPE`: Clear specific cache type (pricing, instances, spot, regions, all)
- `--region REGION`: Clear cache for specific region only
- `--force`: Skip confirmation

**Examples**:

```bash
# Clear all caches (with confirmation)
instancepedia cache clear

# Clear only pricing cache
instancepedia cache clear --type pricing

# Clear cache for specific region
instancepedia cache clear --region us-east-1

# Clear without confirmation
instancepedia cache clear --force

# Clear specific type for specific region
instancepedia cache clear --type pricing --region us-west-2 --force
```

## Filter Options

Available for `list`, `search`, and `presets save` commands.

### Compute Filters

| Option | Description | Example |
|--------|-------------|---------|
| `--min-vcpu N` | Minimum vCPU count | `--min-vcpu 4` |
| `--max-vcpu N` | Maximum vCPU count | `--max-vcpu 16` |
| `--min-memory N` | Minimum memory (GB) | `--min-memory 8` |
| `--max-memory N` | Maximum memory (GB) | `--max-memory 32` |
| `--architecture ARCH` | Architecture (x86_64, arm64) | `--architecture arm64` |
| `--processor-family FAMILY` | Processor (intel, amd, graviton) | `--processor-family graviton` |

### Performance Filters

| Option | Description | Example |
|--------|-------------|---------|
| `--network-performance LEVEL` | Network (low, moderate, high, very_high) | `--network-performance high` |
| `--storage-type TYPE` | Storage (ebs_only, has_instance_store) | `--storage-type has_instance_store` |
| `--nvme-support SUPPORT` | NVME (required, supported, unsupported) | `--nvme-support required` |
| `--burstable-only` | Only burstable instances | `--burstable-only` |

### Cost Filters

| Option | Description | Example |
|--------|-------------|---------|
| `--min-price N` | Minimum hourly price | `--min-price 0.05` |
| `--max-price N` | Maximum hourly price | `--max-price 0.50` |
| `--free-tier-only` | Only free tier eligible | `--free-tier-only` |

### GPU Filters

| Option | Description | Example |
|--------|-------------|---------|
| `--has-gpu` | Only instances with GPU | `--has-gpu` |

### Generation Filters

| Option | Description | Example |
|--------|-------------|---------|
| `--current-generation` | Only current generation | `--current-generation` |

### Family Filters

| Option | Description | Example |
|--------|-------------|---------|
| `--family FAMILIES` | Comma-separated families | `--family t3,t3a,m5` |

## Output Formats

### Table Format (Default)

Human-readable tabular output.

```bash
instancepedia list --format table
```

**Features**:
- Column headers
- Aligned columns
- Easy to read

**Best for**: Interactive terminal use

### JSON Format

Machine-readable JSON output.

```bash
instancepedia list --format json
```

**Features**:
- Structured data
- Easy to parse
- Complete information

**Best for**: Scripting, automation, piping to `jq`

**Example**:
```bash
instancepedia list --format json | jq '.[0].instance_type'
```

### CSV Format

Comma-separated values for spreadsheets.

```bash
instancepedia list --format csv
```

**Features**:
- Spreadsheet compatible
- Column headers
- Easy import

**Best for**: Excel, Google Sheets, data analysis

**Example**:
```bash
instancepedia list --format csv > instances.csv
```

## Common Patterns

### Find Cheapest Instance Matching Criteria

```bash
instancepedia list \
  --min-vcpu 4 \
  --min-memory 8 \
  --current-generation \
  --sort price \
  --format json \
  | jq '.[0]'
```

### Export Filtered List

```bash
instancepedia list \
  --family t3,m5,c5 \
  --current-generation \
  --format csv \
  > instances.csv
```

### Get Pricing for Multiple Instances

```bash
for instance in t3.micro t3.small t3.medium; do
  echo "=== $instance ==="
  instancepedia pricing $instance --region us-east-1
  echo ""
done
```

### Compare Instance Across All US Regions

```bash
instancepedia compare-regions t3.medium \
  --regions us-east-1,us-east-2,us-west-1,us-west-2 \
  --format table
```

### Find Best GPU Instance

```bash
instancepedia list \
  --has-gpu \
  --sort price \
  --format json \
  | jq -r '.[0] | "\(.instance_type) - $\(.pricing.on_demand_price)/hr"'
```

### Check Spot Price Volatility

```bash
instancepedia spot-history m5.large --days 30 --region us-east-1 | grep "Standard deviation"
```

## Scripting Examples

### Terraform Instance Selector

```bash
#!/bin/bash
# select_instance.sh - Select cheapest instance for Terraform

MIN_VCPU=${1:-4}
MIN_MEMORY=${2:-8}
REGION=${3:-us-east-1}

instancepedia list \
  --min-vcpu $MIN_VCPU \
  --min-memory $MIN_MEMORY \
  --current-generation \
  --region $REGION \
  --sort price \
  --format json \
  --quiet \
  | jq -r '.[0].instance_type'
```

### Cost Analysis Script

```bash
#!/bin/bash
# cost_analysis.sh - Analyze costs for instance fleet

INSTANCES=("t3.xlarge" "m5.large" "r6i.xlarge")
REGION="us-east-1"

echo "Instance,On-Demand,Spot,RI-1Y,Savings-Plan" > costs.csv

for instance in "${INSTANCES[@]}"; do
  PRICING=$(instancepedia pricing $instance --region $REGION --format json)

  ON_DEMAND=$(echo $PRICING | jq -r '.on_demand_price')
  SPOT=$(echo $PRICING | jq -r '.spot_price')
  RI_1Y=$(echo $PRICING | jq -r '.reserved_1y_no_upfront')
  SP_1Y=$(echo $PRICING | jq -r '.savings_plan_1y')

  echo "$instance,$ON_DEMAND,$SPOT,$RI_1Y,$SP_1Y" >> costs.csv
done

cat costs.csv
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid arguments |
| 3 | AWS credentials error |
| 4 | AWS API error |
| 5 | Not found (instance type, preset, etc.) |

**Example usage in scripts**:

```bash
if instancepedia show t3.micro > /dev/null 2>&1; then
  echo "Instance type exists"
else
  echo "Instance type not found"
fi
```

## See Also

- [QUICKSTART.md](QUICKSTART.md) - Get started quickly
- [EXAMPLES.md](EXAMPLES.md) - Real-world scenarios
- [CONFIGURATION.md](CONFIGURATION.md) - Configuration options
- [KEYBOARD_SHORTCUTS.md](KEYBOARD_SHORTCUTS.md) - TUI shortcuts
