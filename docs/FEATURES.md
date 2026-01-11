# Complete Feature List

Instancepedia provides comprehensive EC2 instance browsing capabilities in both TUI and CLI modes.

## Table of Contents

- [Interactive TUI Features](#interactive-tui-features)
- [CLI Features](#cli-features)
- [Pricing and Cost Analysis](#pricing-and-cost-analysis)
- [Filtering and Search](#filtering-and-search)
- [Comparison Tools](#comparison-tools)
- [Export and Automation](#export-and-automation)
- [Performance Features](#performance-features)

## Interactive TUI Features

### Instance Browsing

- **Hierarchical Tree View**: Instances organized by category → family → type
  - Compute Optimized (c5, c6i, c7g, etc.)
  - Memory Optimized (r5, r6i, r7g, etc.)
  - Storage Optimized (i3, i4i, d2, etc.)
  - Accelerated Computing (p3, p4, g5, etc.)
  - General Purpose (t3, m5, m6i, etc.)

- **Expandable/Collapsible Categories**: Navigate efficiently through 500+ instance types

- **Real-Time Pricing Display**: See prices directly in the tree view
  - On-demand hourly rate
  - Spot price (when available)
  - Pricing loads asynchronously without blocking UI

### Instance Details View

Press `Enter` on any instance to see:

- **Specifications**:
  - vCPU count and architecture (x86_64, arm64)
  - Memory (GB)
  - Network performance
  - Storage (EBS-only vs instance store)
  - GPU information (if applicable)
  - EBS optimization
  - Enhanced networking support

- **Pricing Information** (all types):
  - On-Demand hourly rate
  - Spot price (current)
  - Reserved Instance pricing (1-year, 3-year, all payment options)
  - Savings Plans pricing (1-year, 3-year, compute and EC2)

- **Free Tier Status**: Green indicator if instance is free tier eligible

- **Additional Attributes**:
  - Current vs previous generation
  - Burstable performance supported
  - Processor family
  - NVME support
  - IPv6 support

### Advanced Search

Press `/` to activate search:

- **Instant Results**: Search as you type
- **Fuzzy Matching**: Finds partial matches
- **Search Across**: Instance type, family, specs, attributes
- **Clear with Esc**: Quick exit from search mode

### Powerful Filtering

Press `F` to open filter modal with extensive options:

#### Compute Filters
- **vCPU Range**: Min/max vCPU count
- **Memory Range**: Min/max memory in GB
- **Architecture**: x86_64, arm64, or both
- **Processor Family**: Intel, AMD, Graviton

#### Performance Filters
- **Network Performance**: Low, Moderate, High, Very High
- **Storage Type**: EBS-only or has instance store
- **NVME Support**: Required, supported, or unsupported
- **Burstable Only**: Filter to T-series instances

#### Cost Filters
- **Price Range**: Min/max hourly on-demand price
- **Free Tier Only**: Show only free tier eligible instances
- **Current Generation Only**: Exclude previous-gen instances

#### GPU Filters
- **Has GPU**: Filter to GPU instances only
- **Instance Families**: Multi-select specific families (t3, m5, c6i, etc.)

#### Filter Presets
- **Built-in Presets**:
  - Web Server (balanced compute/memory)
  - Database (memory-optimized)
  - Compute Intensive (high vCPU)
  - GPU/ML (accelerated computing)
  - Development (low-cost, small instances)
  - Memory Intensive (high memory/vCPU ratio)
  - Budget (lowest-cost instances)
  - ARM (Graviton instances)

- **Custom Presets**: Save your own filter combinations
- **Load Presets**: Quick-apply from dropdown
- **Persistent**: Custom presets saved to `~/.instancepedia/presets/`

### Flexible Sorting

Press `S` to cycle through sort options:

- **Name (A-Z)**: Alphabetical by instance type
- **Name (Z-A)**: Reverse alphabetical
- **vCPU (Low-High)**: Fewest to most vCPUs
- **vCPU (High-Low)**: Most to fewest vCPUs
- **Memory (Low-High)**: Least to most memory
- **Memory (High-Low)**: Most to least memory
- **Price (Low-High)**: Cheapest to most expensive
- **Price (High-Low)**: Most expensive to cheapest

### Instance Comparison

Compare up to 2 instances side-by-side:

1. Navigate to first instance, press `C` to mark
2. Navigate to second instance, press `C` to mark
3. Press `V` to view comparison

**Comparison shows**:
- All specifications side-by-side
- Price differences (on-demand, spot, RI, savings plans)
- Feature differences highlighted
- Cost savings potential

### Spot Price History

Press `P` on any instance to see:

- **30-Day Price Chart**: Visual representation of spot price trends
- **Statistics**:
  - Current spot price
  - Average price over 30 days
  - Minimum and maximum prices
  - Standard deviation (volatility indicator)
  - Percentage of on-demand price
- **Volatility Analysis**: How stable the spot price is
- **Availability Zones**: Per-AZ pricing breakdown

### Cost Optimization Recommendations

Press `O` on any instance to get:

- **Spot Instance Savings**: Potential cost reduction using spot
- **Reserved Instance Savings**: 1-year and 3-year RI options
- **Savings Plans**: Compute and EC2 Savings Plans pricing
- **Right-Sizing Suggestions**: Alternative instances that might fit better
- **Usage Recommendations**: When to use each pricing model

### Multi-Region Comparison

Press `R` on any instance to see:

- **All AWS Regions**: Pricing for the same instance across regions
- **Sorted by Price**: Easily identify cheapest region
- **On-Demand and Spot**: Both pricing types compared
- **Cost Savings**: Potential savings by changing regions

### Export Functionality

Press `E` to export current view:

- **JSON Export**: Machine-readable format for automation
- **CSV Export**: Import into spreadsheets
- **Filtered Results**: Exports respects current filters and search
- **All Pricing Data**: Includes comprehensive pricing information

### UI Customization

- **Vim Keybindings**: Optional hjkl navigation (`vim_keys = true` in config)
- **Responsive Layout**: Adapts to terminal size
- **Status Bar**: Shows current filters, sort order, marked instances
- **Help Modal**: Press `?` for complete keyboard shortcut reference

## CLI Features

### Instance Listing

```bash
instancepedia list [options]
```

**Options**:
- All TUI filters available as command-line flags
- `--format`: Output format (table, json, csv)
- `--quiet`: Suppress headers for scripting
- `--sort`: Sort by name, vcpu, memory, or price
- `--region`: Specify AWS region

**Output formats**:
- **Table**: Human-readable tabular format
- **JSON**: Machine-readable for pipelines
- **CSV**: Import into spreadsheets/databases

### Instance Details

```bash
instancepedia show <instance-type>
```

Shows all specifications and pricing for a single instance.

### Search

```bash
instancepedia search <query>
```

Search across instance types and attributes, output matching instances.

### Pricing Commands

```bash
# All pricing types for an instance
instancepedia pricing <instance-type> [--region REGION]

# Spot price history (default 30 days)
instancepedia spot-history <instance-type> [--region REGION] [--days DAYS]

# Cost optimization recommendations
instancepedia optimize <instance-type> [--region REGION] [--usage-pattern PATTERN]

# Monthly cost estimate
instancepedia cost-estimate <instance-type> [--hours HOURS] [--region REGION]
```

### Comparison Commands

```bash
# Compare two specific instances
instancepedia compare <type1> <type2>

# Compare all instances in a family
instancepedia compare-family <family>

# Multi-region comparison
instancepedia compare-regions <instance-type> --regions r1,r2,r3
```

### Filter Preset Commands

```bash
# List all presets (built-in + custom)
instancepedia presets list

# Apply a preset
instancepedia presets apply <preset-name>

# Save custom preset
instancepedia presets save <name> [filter options]

# Delete custom preset
instancepedia presets delete <name>
```

### Utility Commands

```bash
# List all available regions
instancepedia regions

# Show cache statistics
instancepedia cache stats

# Clear pricing cache
instancepedia cache clear
```

## Pricing and Cost Analysis

### Pricing Types

- **On-Demand**: Standard hourly pricing, no commitment
- **Spot Instances**: Unused capacity, up to 90% savings
- **Reserved Instances**:
  - 1-year and 3-year terms
  - No Upfront, Partial Upfront, All Upfront
  - Standard and Convertible types
- **Savings Plans**:
  - Compute Savings Plans (cross-instance flexibility)
  - EC2 Instance Savings Plans (specific family)
  - 1-year and 3-year terms

### Cost Optimization Features

- **Automatic Recommendations**: Best pricing model based on usage pattern
- **Spot Price Volatility**: Historical analysis to assess risk
- **Right-Sizing Suggestions**: Alternative instances with better price/performance
- **Break-Even Analysis**: When RI/Savings Plans pay off
- **Multi-Region Optimization**: Find cheapest region

### Pricing Data Management

- **Smart Caching**: 4-hour TTL (configurable)
- **Batch API Calls**: Efficient AWS API usage
- **Parallel Fetching**: Async loading in TUI, concurrent in CLI
- **Persistent Cache**: Disk-based cache survives restarts
- **Cache Warmup**: Pre-fetch pricing for faster subsequent runs

## Filtering and Search

### Filter Criteria

- vCPU count (min/max)
- Memory size (min/max)
- Price range (min/max)
- Architecture (x86_64, arm64)
- Processor family (Intel, AMD, Graviton)
- Network performance
- Storage type
- NVME support
- GPU presence
- Instance families (multi-select)
- Free tier eligibility
- Current generation only
- Burstable performance

### Search Capabilities

- **Fuzzy Matching**: Finds partial matches
- **Multi-Field Search**: Searches across type, family, specs
- **Real-Time Results**: Instant feedback as you type
- **Case-Insensitive**: Flexible search terms

## Comparison Tools

### Instance Comparison

- Side-by-side spec comparison
- Price difference highlighting
- Feature presence/absence
- Performance ratio calculations

### Family Comparison

- All instances in a family
- Sorted by any attribute
- Quick identification of best value

### Regional Comparison

- Same instance across all regions
- On-demand and spot pricing
- Sorted by cost
- Regional availability indicators

## Export and Automation

### Export Formats

- **JSON**: Full data structure for automation
- **CSV**: Spreadsheet-friendly format
- **Custom Fields**: Export only what you need

### Scripting Support

- **Quiet Mode**: Clean output without headers
- **JSON Output**: Easy parsing with jq, Python, etc.
- **Exit Codes**: Proper error handling
- **Pipeline-Friendly**: Works with Unix pipes

### Use Cases

- Infrastructure-as-Code instance selection
- Cost analysis spreadsheets
- Automated instance recommendations
- Budget planning and forecasting
- Multi-cloud cost comparison (with external tools)

## Performance Features

### Caching Strategy

- **Instance Types**: Cached for 24 hours (rarely changes)
- **Pricing Data**: Cached for 4 hours (configurable)
- **Spot Prices**: Cached for 15 minutes (more volatile)
- **Region Data**: Cached for 7 days (very stable)

### Concurrency

- **TUI**: Configurable async concurrency (default 20)
- **CLI**: Configurable thread pool (default 50)
- **Rate Limiting**: Respects AWS API limits
- **Graceful Degradation**: Continues if some requests fail

### API Efficiency

- **Batch Requests**: Multiple instances per API call when possible
- **Pagination Handling**: Automatic for large result sets
- **Minimal Calls**: Fetches only what's needed
- **Free APIs Only**: No AWS charges ever

### Lazy Loading

- **TUI Tree View**: Expands categories on-demand
- **Pricing Data**: Loads in background, UI remains responsive
- **Spot History**: Only fetched when viewed
- **Regional Data**: Only fetched for multi-region comparison

## Configuration Options

All features can be customized via `~/.instancepedia/config.toml`:

- Default AWS region
- AWS profile
- Vim-style navigation
- Pricing concurrency levels
- Cache TTL values
- Default output format
- Default sort order
- Filter preset directory

See [CONFIGURATION.md](CONFIGURATION.md) for complete details.

## AWS Permissions Required

Minimum IAM permissions:

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

**Note**: All these APIs are free - you'll never be charged for using Instancepedia.
