# Instancepedia - EC2 Instance Type Browser

A Terminal User Interface (TUI) application for browsing AWS EC2 instance types with detailed information and free tier eligibility.

![Instance List Screen](screenshot-instance-list.png)

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

## IAM Permissions

Instancepedia requires minimal AWS permissions to function. The application only needs read-only access to EC2 instance type information.

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
                "ec2:DescribeInstanceTypes"
            ],
            "Resource": "*"
        }
    ]
}
```

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

