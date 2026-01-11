# Quick Start Guide

Get productive with Instancepedia in 5 minutes.

## Installation

```bash
pip install instancepedia
```

## AWS Credentials Setup

Choose one method:

```bash
# Option 1: AWS CLI configuration (recommended)
aws configure

# Option 2: Environment variables
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret

# Option 3: Named profile
export AWS_PROFILE=your-profile
```

**Note**: Instancepedia uses only free AWS APIs. You'll never be charged for using this tool.

## Your First Session

### Launch the Interactive Browser

```bash
instancepedia
```

You'll see a hierarchical tree of EC2 instances organized by category and family. Pricing data will load in the background (takes ~30 seconds first time, then cached for 4 hours).

### Essential Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `↑` `↓` | Navigate instances |
| `Enter` | View instance details |
| `/` | Search instances |
| `F` | Open filter modal |
| `S` | Cycle sort order |
| `Q` | Quit |
| `?` | Show all shortcuts |

### Your First Search

Press `/` and type an instance family like `t3` or `m5`. Results appear instantly.

### Your First Filter

1. Press `F` to open the filter modal
2. Set **Min vCPU: 4** and **Min Memory: 8**
3. Check **Current Generation Only**
4. Click **Apply**

You'll see only instances matching your criteria.

### Your First Comparison

1. Navigate to an instance (e.g., `t3.medium`)
2. Press `C` to mark it
3. Navigate to another instance (e.g., `t3a.medium`)
4. Press `C` to mark it
5. Press `V` to view side-by-side comparison

## Common CLI Commands

### List Instances with Filters

```bash
# Find ARM instances with 4 vCPU and 16 GB RAM
instancepedia list --architecture arm64 --min-vcpu 4 --min-memory 16

# Find cheapest current-gen instances
instancepedia list --current-generation --sort price | head -20
```

### Get Pricing Information

```bash
# All pricing types for an instance
instancepedia pricing t3.micro --region us-east-1

# Spot price history (30 days)
instancepedia spot-history t3.micro --region us-east-1
```

### Compare Instance Types

```bash
# Compare two specific instances
instancepedia compare t3.medium t3a.medium

# Compare all instances in a family
instancepedia compare-family t3
```

### Multi-Region Pricing

```bash
# Find cheapest region for an instance
instancepedia compare-regions t3.micro --regions us-east-1,us-west-2,eu-west-1
```

## Using Filter Presets

Presets let you save common filter combinations:

```bash
# List built-in presets
instancepedia presets list

# Apply a preset
instancepedia presets apply web-server

# Create custom preset
instancepedia presets save my-preset --min-vcpu 4 --architecture arm64

# Delete custom preset
instancepedia presets delete my-preset
```

## Configuration

Create `~/.instancepedia/config.toml`:

```toml
# Default AWS region
default_region = "us-east-1"

# Enable Vim-style navigation (hjkl)
vim_keys = false

# Pricing concurrency (higher = faster, more API calls)
tui_pricing_concurrency = 20
cli_pricing_concurrency = 50

# Pricing cache TTL (seconds)
pricing_cache_ttl = 14400  # 4 hours
```

## What's Next?

- **Explore Features**: See [FEATURES.md](FEATURES.md) for complete feature list
- **Real-World Examples**: Check [EXAMPLES.md](EXAMPLES.md) for practical scenarios
- **All Shortcuts**: Review [KEYBOARD_SHORTCUTS.md](KEYBOARD_SHORTCUTS.md)
- **Advanced Config**: Read [CONFIGURATION.md](CONFIGURATION.md)
- **CLI Reference**: See [CLI_REFERENCE.md](CLI_REFERENCE.md) for all commands

## Troubleshooting

**Slow first launch?**
Pricing data is being fetched. Subsequent runs use cache and are instant.

**AWS credentials error?**
Run `aws configure` or check your environment variables.

**Permission errors?**
Ensure your credentials have these permissions:
- `ec2:DescribeInstanceTypes`
- `ec2:DescribeSpotPriceHistory`
- `pricing:GetProducts`

**Need debug info?**
Run with `--debug` flag: `instancepedia --debug`
