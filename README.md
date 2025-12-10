# Instancepedia - EC2 Instance Type Browser

A Terminal User Interface (TUI) application for browsing AWS EC2 instance types with detailed information and free tier eligibility.

## Features

- 🗺️ **Region Selection**: Browse instance types for any AWS region you have access to
- 📋 **Instance List**: View all available EC2 instance types with key metrics
- 🔍 **Search & Filter**: Search by instance type name, filter by free tier eligibility
- 📊 **Detailed Information**: Comprehensive details for each instance type including:
  - Compute specifications (vCPU, cores, threads)
  - Memory information
  - Network performance
  - Storage options (EBS, instance store)
  - Architecture support
- 🆓 **Free Tier Indicators**: Clearly marked free tier eligible instances
- ⚡ **Fast Navigation**: Smooth screen transitions with loading indicators

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure AWS credentials (one of the following):
   - Run `aws configure`
   - Set environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
   - Use an AWS profile: `export AWS_PROFILE=your-profile`

## Usage

Run the application:
```bash
python3 -m src.main
```

Or with debug mode enabled:
```bash
python3 -m src.main --debug
```

Or install as a package and run:
```bash
pip install -e .
instancepedia
```

### Keyboard Shortcuts

#### Region Selector
- `↑` `↓` - Navigate regions
- `Enter` - Select region
- `Esc` / `Q` - Quit

#### Instance List
- `↑` `↓` - Navigate list
- `Enter` - View details
- `/` - Focus search
- `F` - Toggle free tier filter
- `Esc` - Back to region selector
- `Q` - Quit

#### Instance Detail
- `Esc` - Back to list
- `Q` - Quit

## Configuration

You can configure the application using environment variables:

- `INSTANCEPEDIA_AWS_REGION` - Default AWS region (default: us-east-1)
- `INSTANCEPEDIA_AWS_PROFILE` - AWS profile to use

## Requirements

- Python 3.8+
- AWS credentials configured
- boto3
- textual
- pydantic

## Project Structure

```
instancepedia/
├── src/
│   ├── models/          # Data models
│   ├── services/        # AWS service wrappers
│   ├── ui/              # TUI screens
│   ├── config/          # Configuration
│   ├── app.py           # Main application
│   └── main.py          # Entry point
├── requirements.txt
└── README.md
```

## License

MIT

