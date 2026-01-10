# CLI Reference

This document provides comprehensive reference for all CLI commands, modules, filters, and presets.

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
- `presets list` - List available filter presets (built-in and custom)
- `presets apply` - Apply a filter preset to list instances
- `presets save` - Save current filters as a custom preset
- `presets delete` - Delete a custom preset
- `cache stats` - Show cache statistics
- `cache clear` - Clear cache entries
- `spot-history` - Show historical spot price trends with statistics and volatility analysis
- `optimize` - Get cost optimization recommendations for an instance type

## CLI Module Architecture

Commands are organized in `src/cli/commands/` package:

```
src/cli/commands/
├── __init__.py           # Package init, exports all commands
├── base.py               # Common utilities (validation, instance fetching, file I/O)
├── instance_commands.py  # cmd_list, cmd_show, cmd_search, cmd_compare, cmd_compare_family, cmd_regions
├── pricing_commands.py   # cmd_pricing, cmd_cost_estimate, cmd_compare_regions, cmd_spot_history, cmd_optimize
├── cache_commands.py     # cmd_cache_stats, cmd_cache_clear
└── preset_commands.py    # cmd_presets_list, cmd_presets_apply, cmd_presets_save, cmd_presets_delete
```

### Base Utilities

**`src/cli/commands/base.py`** provides common utilities used across all commands:

- `status(message, quiet)` - Print status message to stderr (respects quiet mode)
- `progress(completed, total, item_type, quiet)` - Print progress update
- `print_error(message, debug, exception)` - Print error with optional traceback
- `validate_region(region, exit_on_error)` - Validate region with helpful error messages and suggestions
- `validate_regions(regions, exit_on_error)` - Validate multiple regions
- `get_aws_client(region, profile)` - Create AWS client with error handling
- `get_instance_by_name(aws_client, instance_type, region, quiet, fetch_pricing)` - Fetch and find single instance
- `get_instances_by_names(aws_client, instance_types, region, quiet)` - Fetch and find multiple instances
- `fetch_instance_pricing(pricing_service, instance_type, region, include_ri)` - Fetch all pricing types
- `safe_write_file(file_path, content, create_dirs)` - Write file with error handling and directory creation
- `write_output(output, output_path, quiet)` - Write to file or stdout

**Backwards Compatibility**: `src/cli/commands.py` re-exports all commands for compatibility.

## Shell Completions

Tab completion scripts are provided for bash and zsh shells in `scripts/completions/`:
- `instancepedia.bash` - Bash completion script (source or copy to `/etc/bash_completion.d/`)
- `_instancepedia` - Zsh completion script (copy to a directory in `$fpath`)

**Features:**
- Command and subcommand completion
- Option completion for all commands
- AWS region suggestions from built-in list
- Instance family suggestions
- Filter preset name completion
- AWS profile completion (reads from `~/.aws/credentials`)

**Implementation Notes:**
- Both scripts handle nested subcommands (presets list/apply/save/delete, cache stats/clear)
- Zsh script includes descriptions for commands and options
- Region list is hardcoded for instant completion without AWS API calls

## Filter Presets

Filter presets allow users to quickly apply common filtering scenarios. Built-in presets include:
- `web-server` - 4+ vCPU, 8+ GB RAM, current generation
- `database` - Memory-optimized, 8+ vCPU, 32+ GB RAM
- `compute-intensive` - Compute-optimized, 16+ vCPU
- `gpu-ml` - GPU instances for machine learning
- `arm-graviton` - ARM-based instances
- `burstable` - T-series burstable instances
- `free-tier` - Free tier eligible instances
- `small-dev` - Small instances for development (1-2 vCPU, up to 4 GB RAM)

Presets are defined in `src/services/filter_preset_service.py` and stored in `~/.instancepedia/presets/filter_presets.json` for custom presets.

### Custom Preset Persistence

Users can create, save, and delete custom filter presets via both CLI and TUI:

**CLI Commands:**
```bash
# Save a custom preset
instancepedia presets save my-preset --description "Description" --min-vcpu 4 --architecture arm64

# Delete a custom preset
instancepedia presets delete my-preset --force
```

**TUI Integration:**
- Filter modal includes a "Load Preset" dropdown at the top
- "Save Preset" button saves current filter values as a new preset
- Custom presets are marked with `*` in the dropdown
- `SavePresetModal` handles name/description input with validation

**Implementation Details** (`src/services/filter_preset_service.py`):
- `FilterPreset` dataclass with all filter fields (aligned with `FilterCriteria`)
- `FilterPreset.to_filter_criteria()` - Convert preset to TUI FilterCriteria
- `FilterPreset.from_filter_criteria()` - Create preset from current filters
- `FilterPresetService.save_custom_preset()` - Persist to JSON file
- `FilterPresetService.delete_custom_preset()` - Remove from JSON file
- `FilterPresetService.is_builtin_preset()` - Protect built-in presets from deletion

**FilterPreset Fields** (extended to match FilterCriteria):
```python
@dataclass
class FilterPreset:
    name: str
    description: Optional[str] = None
    min_vcpu: Optional[int] = None
    max_vcpu: Optional[int] = None
    min_memory: Optional[float] = None
    max_memory: Optional[float] = None
    has_gpu: Optional[bool] = None
    current_generation_only: bool = False
    burstable_only: bool = False
    free_tier_only: bool = False
    architecture: Optional[str] = None
    instance_families: Optional[List[str]] = None
    processor_family: Optional[str] = None
    network_performance: Optional[str] = None
    storage_type: Optional[str] = None
    nvme_support: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
```

**Storage Format** (`~/.instancepedia/presets/filter_presets.json`):
```json
{
  "my-preset": {
    "name": "my-preset",
    "description": "My custom filter",
    "min_vcpu": 4,
    "architecture": "arm64"
  }
}
```

## Storage Filters

Storage-focused filtering allows users to find instances based on storage characteristics:

**Filter Options**:
- **Storage Type**:
  - `ebs_only` (TUI) / `ebs-only` (CLI): Instances with EBS-only storage (no instance store)
  - `has_instance_store` (TUI) / `instance-store` (CLI): Instances with attached instance store volumes

- **NVMe Support**:
  - `required`: Instances that require NVMe (high-performance instance store)
  - `supported`: Instances that support NVMe
  - `unsupported`: Instances without NVMe support

**Implementation** (`src/services/filter_service.py`, `src/ui/filter_modal.py`):
- `storage_type` and `nvme_support` fields in `FilterCriteria` dataclass
- Storage type filter checks `instance_storage_info.total_size_in_gb`
- NVMe filter checks `instance_storage_info.nvme_support`
- Unified filtering via `apply_filters()` function

**CLI Integration** (`src/cli/parser.py`, `src/cli/commands/instance_commands.py`):
- `--storage-type` argument: `ebs-only` or `instance-store`
- `--nvme` argument: `required`, `supported`, or `unsupported`
- Available for both `list` and `search` commands

**TUI Display** (`src/ui/instance_list.py`):
- Instance storage shown in list view (e.g., "150GB NVMe")
- Storage size displayed when available
- NVMe indicator added for NVMe-required instances
- Format: `{size}GB{" NVMe" if required}`

## Advanced Filtering

Advanced filtering options provide fine-grained control over instance selection:

### Processor Family Filter

- **Intel**: Filters to Intel processors (excludes AMD and Graviton)
- **AMD**: Filters to AMD processors (instances with 'a' suffix, e.g., m5a, c5a, r5a)
- **Graviton**: Filters to AWS Graviton ARM processors (arm64 architecture)
- TUI: Processor Family dropdown in filter modal
- CLI: `--processor-family {intel,amd,graviton}`

### Network Performance Filter

- **Low**: Up to 5 Gigabit network performance
- **Moderate**: 10-12 Gigabit network performance
- **High**: 10-25 Gigabit network performance
- **Very High**: 50+ Gigabit network performance
- TUI: Network Performance dropdown in filter modal
- CLI: `--network-performance {low,moderate,high,very-high}`

### Price Range Filter

- **Min Price**: Minimum hourly on-demand price in USD
- **Max Price**: Maximum hourly on-demand price in USD
- Only filters instances with pricing data loaded
- Instances without pricing are kept (not filtered out)
- TUI: Price Range input fields in filter modal
- CLI: `--min-price <float> --max-price <float>`

### Unified Filter Service

**`src/services/filter_service.py`** provides unified filtering logic shared between TUI and CLI:

```python
from src.services.filter_service import FilterCriteria, apply_filters

# Create criteria from CLI args
criteria = FilterCriteria.from_cli_args(args)

# Or create manually
criteria = FilterCriteria(
    min_vcpu=4,
    min_memory=8.0,
    processor_family="graviton",
    current_gen_only=True
)

# Apply filters
filtered = apply_filters(instances, criteria)
```

**Implementation Details:**
- `FilterCriteria` dataclass contains all filter fields (search, vcpu, memory, GPU, generation, etc.)
- `apply_filters()` applies all active filters to an instance list
- `FilterCriteria.from_cli_args()` maps CLI arguments to filter criteria
- Processor family uses heuristics (AMD has 'a' suffix, Graviton has arm64 arch)
- Network performance maps to keyword patterns in `network_info.network_performance`
- Price filter applied after pricing fetch in CLI, immediately in TUI
- All filters work in both TUI (filter modal) and CLI (command-line arguments)

## EBS Recommendations

The `EbsRecommendationService` provides volume type recommendations based on instance EBS capabilities:
- Analyzes instance EBS optimization level and throughput
- Recommends appropriate volume types (gp3, io2, st1, etc.)
- Shows IOPS ranges, throughput specs, and use cases
- Integrated into both TUI instance detail and CLI `show` command

## Spot Price History

The spot price history feature (`spot-history` command) provides historical analysis of spot pricing trends:

**Implementation** (`src/services/pricing_service.py`):
- `SpotPriceHistory` dataclass stores price statistics and metadata
- `get_spot_price_history()` method fetches and analyzes historical data
- Uses AWS EC2 `describe-spot-price-history` API (free, no CloudWatch charges)
- Filters by product description: `Linux/UNIX` (most common)

**Statistical Analysis**:
- Current, minimum, maximum, average, median prices
- Standard deviation for volatility measurement
- Volatility percentage: `(std_dev / avg) * 100`
- Stability ratings based on volatility thresholds:
  - Very Stable: < 5%
  - Stable: 5-15%
  - Moderate: 15-30%
  - Volatile: 30-50%
  - Highly Volatile: > 50%

**Visualization**:
- Text-based bar chart using Unicode characters (█)
- Shows last 10 data points for trend visualization
- Bar lengths proportional to price values
- Includes price labels for clarity

**CLI Integration** (`src/cli/commands/pricing_commands.py`):
- `cmd_spot_history()` handler with table and JSON output formats
- `--days` argument for customizable time periods (default: 30 days)
- Graceful error handling for regions/instances without spot pricing

**TUI Integration** (`src/ui/instance_detail.py`):
- Reference message in instance detail pricing section
- Directs users to CLI command for full analysis

## Cost Optimization Recommendations

The cost optimization feature (`optimize` command) provides intelligent cost-saving recommendations:

**Implementation** (`src/services/optimization_service.py`):
- `OptimizationService` class analyzes instance costs and alternatives
- `OptimizationReport` dataclass stores recommendations with savings calculations
- `OptimizationRecommendation` dataclass represents each recommendation with details

**Recommendation Types**:
- **Spot Instances**: For fault-tolerant workloads (standard/burst usage patterns)
- **Right-Sizing**: Cheaper alternatives with similar/better specs
- **Savings Plans**: 1-year and 3-year compute savings plans
- **Reserved Instances**: 1-year and 3-year RIs (no upfront, partial, all upfront)

**Usage Pattern Support**:
- `standard`: Mixed workload (considers all recommendations)
- `burst`: Variable usage (spot + savings plans, not RIs)
- `continuous`: 24/7 workload (emphasizes RIs and savings plans)

**Analysis Features**:
- Compares current instance against all available alternatives
- Right-sizing requires 80%+ memory and vCPU-2 minimum
- Spot savings must exceed 30% to recommend
- Prefers current generation instances
- Includes considerations (interruptions, commitments, etc.)

**CLI Integration** (`src/cli/commands/pricing_commands.py`):
- `cmd_optimize()` handler with table and JSON output formats
- `--usage-pattern` argument (default: standard)
- Shows total potential savings summary
- Lists recommendations sorted by savings amount

**TUI Integration** (`src/ui/optimization_modal.py`, `src/ui/instance_detail.py`):
- Press `O` key in instance detail screen to open optimization modal
- Displays recommendations with emoji indicators
- Shows current vs optimized costs
- Batch pricing fetch for fast loading (20x concurrency)

## Reserved Instance Pricing

The Reserved Instance (RI) pricing feature provides comprehensive pricing for Standard Reserved Instances with all payment options:

**Implementation** (`src/services/pricing_service.py`, `src/services/async_pricing_service.py`):
- `get_reserved_instance_price(instance_type, region, lease_length, payment_option)` method
- Supports lease lengths: `"1yr"`, `"3yr"`
- Supports payment options: `"no_upfront"`, `"partial_upfront"`, `"all_upfront"`
- Filters for Standard RIs only (excludes Convertible RIs via `OfferingClass='standard'`)
- Uses AWS Pricing API Reserved terms
- Cache keys: `ri_{lease}_{payment_option}` (e.g., `ri_1yr_partial_upfront`)

**Data Model** (`src/models/instance_type.py`):
- `PricingInfo` dataclass has 6 RI fields:
  - `ri_1yr_no_upfront`, `ri_1yr_partial_upfront`, `ri_1yr_all_upfront`
  - `ri_3yr_no_upfront`, `ri_3yr_partial_upfront`, `ri_3yr_all_upfront`
- Format methods: `format_ri_1yr_no_upfront()`, etc.
- `calculate_savings_percentage()` supports all RI price types

**AWS API Details**:
- Uses same filters as Savings Plans (ServiceCode, location, instanceType, tenancy, OS, etc.)
- Term matching logic:
  ```python
  if (lease_contract_length == api_lease and
      purchase_option == api_payment and
      offering_class == 'standard'):
      # Extract hourly price
  ```
- Payment option mapping:
  ```python
  {
      "no_upfront": "No Upfront",
      "partial_upfront": "Partial Upfront",
      "all_upfront": "All Upfront"
  }
  ```

**Pricing Display**:
- AWS returns effective hourly rates (upfront costs are amortized over the term)
- Displayed as-is with note: "* Effective hourly rate (includes prorated upfront payment)"
- Example: 1-year Partial Upfront at $500 upfront + $0.005/hr = $0.0622/hr effective rate

**TUI Integration** (`src/ui/instance_detail.py`):
- Display all 6 RI options in instance detail view
- Grouped by term (1-Year section, 3-Year section)
- Shows savings percentages vs on-demand
- Fetched in background via `_fetch_pricing_if_needed()`
- Proper cleanup: `on_unmount()` cancels pricing worker and closes async client

**CLI Integration** (`src/cli/commands/instance_commands.py`, `src/cli/output.py`):
- Fetched in `cmd_show()` when `--include-pricing` flag is used
- TableFormatter displays RI sections with savings percentages
- JSONFormatter includes nested `reserved_instances` object:
  ```json
  "reserved_instances": {
    "1yr": {
      "no_upfront": 0.0600,
      "partial_upfront": 0.0290,
      "all_upfront": null
    },
    "3yr": {
      "no_upfront": 0.0410,
      "partial_upfront": 0.0190,
      "all_upfront": null
    }
  }
  ```

**Cache Behavior**:
- Each RI price type cached separately
- TTL: 4 hours (same as other pricing)
- Cache miss returns None (common for unavailable RI pricing)
- Caches both successful lookups and None values

**Error Handling**:
- Logs at debug level (not error) for missing RI pricing (common scenario)
- Graceful degradation - shows "N/A" for unavailable prices
- Same retry logic as Savings Plans (exponential backoff on throttling)

**Example Output**:
```
Reserved Instances (Standard, 1-Year):
  No Upfront: $0.0600/hr (37.5% savings)
  Partial Upfront: $0.0290/hr (69.8% savings) *
  All Upfront: N/A

Reserved Instances (Standard, 3-Year):
  No Upfront: $0.0410/hr (57.3% savings)
  Partial Upfront: $0.0190/hr (80.2% savings) *
  All Upfront: N/A

* Effective hourly rate (includes prorated upfront payment)
```

## Cache Management

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

**Implementation** (`src/cli/commands/cache_commands.py`):
- `cmd_cache_stats()` - Shows cache location, entries, size, age
- `cmd_cache_clear()` - Clears cache with optional filters and confirmation
