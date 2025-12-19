# Instancepedia - EC2 Instance Type Browser

A Terminal User Interface (TUI) application for browsing AWS EC2 instance types with detailed information and free tier eligibility.

![Instance List Screen](screenshots/screenshot-instance-list.png)

![Instance Details Screen](screenshots/screenshot-details.png)

![Pricing Information](screenshots/screenshot-pricing.png)

## Features

- 🗺️ **Region Selection**: Browse instance types for any AWS region you have access to
- 📋 **Categorized Instance List**: View all available EC2 instance types organized by family and category
  - Hierarchical tree structure: Categories → Families → Instances
  - Categories include: General Purpose, Compute Optimized, Memory Optimized, Burstable Performance, GPU Instances, Storage Optimized, etc.
  - Instances grouped by family (e.g., m5, m6i, t2, t3) within categories
  - Root node and families expand automatically when parent categories are expanded
  - Expand/collapse categories and families to reduce clutter
  - Expanded state is preserved during pricing updates
- 💰 **Pricing Information**: See on-demand and spot prices for each instance type
  - Prices load in the background for all instance types
  - Real-time pricing updates in the tree view (throttled to preserve expanded state)
  - Batch fetching for optimal performance
  - Automatic retry with exponential backoff on rate limits
  - Pricing displayed directly in the instance list: instance type, vCPU, memory, and price per hour
- 💵 **Cost Calculator**: Automatic calculation of monthly and annual costs, plus cost per vCPU and GB RAM
- 🔍 **Search & Filter**: Search by instance type name, filter by free tier eligibility
- 📊 **Detailed Information**: Comprehensive details for each instance type including:
  - Compute specifications (vCPU, cores, threads)
  - Memory information
  - Network performance
  - Storage options (EBS, instance store)
  - Architecture support
  - Pricing and cost analysis with spot price savings
- 🆓 **Free Tier Indicators**: Clearly marked free tier eligible instances
- ⚡ **Fast Navigation**: Smooth screen transitions with loading indicators
- 🐛 **Debug Mode**: Scrolling debug log for troubleshooting (use `--debug` flag)

## Installation

### From PyPI (Recommended)

```bash
pip install instancepedia
```

### From Source

1. Clone the repository:
```bash
git clone https://github.com/pfrederiksen/instancepedia.git
cd instancepedia
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

Or install in development mode:
```bash
pip install -e .
```

### Configure AWS Credentials

After installation, configure AWS credentials (one of the following):
   - Run `aws configure`
   - Set environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
   - Use an AWS profile: `export AWS_PROFILE=your-profile`

## Usage

After installation from PyPI, simply run:
```bash
instancepedia
```

Or with debug mode enabled (shows scrolling debug log):
```bash
instancepedia --debug
```

If you installed from source (development mode), you can also run:
```bash
python3 -m src.main
```

Or with debug mode:
```bash
python3 -m src.main --debug
```

**Note**: Pricing information loads in the background after instance types are displayed. You'll see:
- A progress indicator in the header showing how many prices have been loaded
- "⏳ Loading..." in the tree for instances that don't have pricing yet
- Real-time updates as prices load (tree updates are throttled to preserve your expanded sections)
- The application uses parallel requests and batch processing to fetch pricing efficiently, with automatic retry logic for rate-limited requests
- Your expanded categories and families remain open during pricing updates

### Keyboard Shortcuts

#### Region Selector
- `↑` `↓` - Navigate regions
- `Enter` - Select region
- `Esc` / `Q` - Quit

#### Instance List
- `↑` `↓` - Navigate tree (move between categories, families, and instances)
- `Enter` - View details (on instance) or expand/collapse (on category/family)
- `Space` - Expand/collapse category or family
- `/` - Focus search input
- `F` - Toggle free tier filter (show only free tier eligible instances)
- `Esc` - Back to region selector
- `Q` - Quit

**Tree Navigation Tips:**
- The root "Instance Types" node is expanded by default
- Categories are collapsed by default to reduce initial clutter
- When you expand a category, all family nodes within it are automatically expanded
- Instance nodes show: instance type | vCPU count | memory | price | free tier indicator
- Search and filters work across all categories and families

#### Instance Detail
- `Esc` - Back to list
- `Q` - Quit

## Configuration

You can configure the application using environment variables:

- `INSTANCEPEDIA_AWS_REGION` - Default AWS region (default: us-east-1)
- `INSTANCEPEDIA_AWS_PROFILE` - AWS profile to use

## IAM Permissions

Instancepedia requires minimal AWS permissions to function. The application needs read-only access to EC2 instance type information and pricing data.

### Required IAM Policy

Create an IAM policy with the following JSON:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeRegions",
                "ec2:DescribeInstanceTypes",
                "ec2:DescribeSpotPriceHistory"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "pricing:GetProducts"
            ],
            "Resource": "*"
        }
    ]
}
```

**Note**: The `pricing:GetProducts` permission is required to display on-demand pricing. The `ec2:DescribeSpotPriceHistory` permission is required to display current spot prices. If you don't need pricing information, you can omit these permissions and the application will still function (pricing will show as "N/A").

The application handles AWS API rate limiting automatically with exponential backoff retry logic, so you don't need to worry about rate limit errors.

### Setting Up IAM Permissions

1. **Create the policy** (using AWS CLI):
   ```bash
   aws iam create-policy \
     --policy-name InstancepediaReadOnly \
     --policy-document file://instancepedia-policy.json
   ```

2. **Attach the policy to a user**:
   ```bash
   aws iam attach-user-policy \
     --user-name YOUR_USERNAME \
     --policy-arn arn:aws:iam::ACCOUNT_ID:policy/InstancepediaReadOnly
   ```

3. **Or attach to a role** (for EC2 instances, Lambda, etc.):
   ```bash
   aws iam attach-role-policy \
     --role-name YOUR_ROLE_NAME \
     --policy-arn arn:aws:iam::ACCOUNT_ID:policy/InstancepediaReadOnly
   ```

**Note**: Replace `YOUR_USERNAME`, `YOUR_ROLE_NAME`, and `ACCOUNT_ID` with your actual values.

Alternatively, you can use the AWS Console:
1. Go to IAM → Policies → Create policy
2. Select JSON tab and paste the policy above
3. Name it `InstancepediaReadOnly` and create it
4. Attach it to your user or role as needed

## Performance

Instancepedia is optimized for performance:

- **Parallel Pricing Fetching**: Uses thread pools to fetch pricing data concurrently (5 parallel workers)
- **Batch Spot Price Queries**: Fetches spot prices in batches of up to 50 instance types per API call
- **Automatic Retry**: Handles rate limiting with exponential backoff (1s, 2s, 4s, etc.)
- **Background Loading**: Pricing loads in the background so you can browse instance types immediately
- **Throttled UI Updates**: Tree updates are throttled (every 10 pricing updates) to prevent UI flicker and preserve expanded state
- **State Preservation**: Expanded categories and families are preserved during tree rebuilds

## Requirements

- Python 3.8+
- AWS credentials configured
- Dependencies (installed automatically with pip):
  - `boto3>=1.28.0` - AWS SDK
  - `textual>=0.40.0` - TUI framework
  - `pydantic>=2.0.0` - Data validation
  - `pydantic-settings>=2.0.0` - Settings management

## Development

### Setting Up Development Environment

1. Clone the repository:
```bash
git clone https://github.com/pfrederiksen/instancepedia.git
cd instancepedia
```

2. Install in development mode with dev dependencies:
```bash
pip install -e ".[dev]"
```

This installs the package in editable mode along with development tools (build, twine, pytest).

### Building and Publishing

To build the package for PyPI:

1. Install build tools (use a virtual environment):
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade build twine
```

2. Build the package:
```bash
python3 -m build
```

3. Check the package:
```bash
python3 -m twine check dist/*
```

4. Publish to TestPyPI (recommended first):
```bash
python3 -m twine upload --repository testpypi dist/*
```

5. Publish to PyPI:
```bash
python3 -m twine upload dist/*
```

Or use the helper script:
```bash
./scripts/publish.sh testpypi  # Test first
./scripts/publish.sh pypi      # Production
```

### Running Tests

```bash
pytest
```

## Project Structure

```
instancepedia/
├── src/                      # Source code
│   ├── __init__.py
│   ├── app.py                # Main application
│   ├── main.py               # Entry point
│   ├── debug.py              # Debug utilities
│   ├── config/               # Configuration
│   │   ├── __init__.py
│   │   └── settings.py       # Configuration settings
│   ├── models/               # Data models
│   │   ├── __init__.py
│   │   ├── free_tier.py
│   │   ├── instance_type.py
│   │   └── region.py
│   ├── services/             # AWS service wrappers
│   │   ├── __init__.py
│   │   ├── aws_client.py
│   │   ├── free_tier_service.py
│   │   ├── instance_service.py
│   │   └── pricing_service.py
│   └── ui/                   # TUI screens
│       ├── __init__.py
│       ├── instance_detail.py
│       ├── instance_list.py
│       └── region_selector.py
├── scripts/                  # Utility scripts
│   └── publish.sh            # PyPI publishing helper
├── screenshots/              # Application screenshots
├── .gitignore               # Git ignore rules
├── LICENSE                  # MIT License
├── MANIFEST.in              # Package manifest for PyPI
├── pyproject.toml           # Project configuration and metadata
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

## License

MIT

