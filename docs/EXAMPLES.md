# Real-World Examples

Practical scenarios showing how to use Instancepedia for common tasks.

## Table of Contents

- [Web Application Deployment](#web-application-deployment)
- [Database Server Selection](#database-server-selection)
- [Cost Optimization](#cost-optimization)
- [Development Environments](#development-environments)
- [Machine Learning Workloads](#machine-learning-workloads)
- [Batch Processing](#batch-processing)
- [Infrastructure Automation](#infrastructure-automation)
- [Budget Planning](#budget-planning)

## Web Application Deployment

### Scenario: Choosing an Instance for a Node.js Web Server

**Requirements**:
- 4+ vCPUs for handling concurrent requests
- 8-16 GB RAM for application and caching
- Current generation for best performance/price
- Cost-effective for 24/7 operation

**TUI Workflow**:

```bash
instancepedia
```

1. Press `F` to open filter modal
2. Set **Min vCPU: 4**
3. Set **Min Memory: 8**, **Max Memory: 16**
4. Check **Current Generation Only**
5. Click **Apply**
6. Press `S` until sort is **Price (Low-High)**
7. Review top candidates (likely t3.xlarge, t3a.xlarge, m5.large)
8. Press `C` on t3.xlarge and t3a.xlarge to mark them
9. Press `V` to compare side-by-side
10. Press `O` on preferred instance to see cost optimization options
11. Press `R` to compare pricing across regions

**CLI Workflow**:

```bash
# Find matching instances
instancepedia list \
  --min-vcpu 4 \
  --min-memory 8 \
  --max-memory 16 \
  --current-generation \
  --sort price \
  --format json

# Compare top two candidates
instancepedia compare t3.xlarge t3a.xlarge

# Check cost optimization for winner
instancepedia optimize t3a.xlarge --region us-east-1

# Compare across regions
instancepedia compare-regions t3a.xlarge \
  --regions us-east-1,us-west-2,eu-west-1

# Estimate monthly cost (730 hours)
instancepedia cost-estimate t3a.xlarge --hours 730 --region us-east-1
```

**Decision**: t3a.xlarge in us-east-1 with Compute Savings Plan (1-year) saves 30% vs on-demand.

---

## Database Server Selection

### Scenario: PostgreSQL Database for Production Application

**Requirements**:
- Memory-optimized for database workloads
- 32+ GB RAM for large dataset
- High network performance for replication
- EBS-optimized for storage performance

**TUI Workflow**:

```bash
instancepedia
```

1. Navigate to **Memory Optimized** category
2. Press `F` to filter
3. Set **Min Memory: 32**
4. Select **Instance Families**: r6i, r7g, r7iz (recent memory-optimized)
5. Apply filter
6. Press `S` to sort by **Price (Low-High)**
7. Review r6i.xlarge, r7g.xlarge (Graviton)
8. Press `Enter` to view details, check network performance
9. Press `P` to view spot price history (if considering spot for read replicas)

**CLI Workflow**:

```bash
# Find memory-optimized instances
instancepedia list \
  --family r6i,r7g,r7iz \
  --min-memory 32 \
  --current-generation \
  --sort price

# Compare the r6i family
instancepedia compare-family r6i --sort memory

# Detailed pricing for top candidate
instancepedia pricing r6i.xlarge --region us-east-1

# Check if Graviton (r7g) is cheaper
instancepedia compare r6i.xlarge r7g.xlarge

# Optimization recommendations
instancepedia optimize r6i.xlarge \
  --region us-east-1 \
  --usage-pattern database
```

**Decision**: r6i.xlarge with 3-year Reserved Instance (All Upfront) for maximum savings on stable database workload.

---

## Cost Optimization

### Scenario: Reducing Costs on Existing Fleet

**Current State**: 50 m5.2xlarge instances running 24/7 on on-demand pricing.

**Goal**: Reduce costs without changing instance types.

**Analysis Workflow**:

```bash
# Current on-demand cost
instancepedia pricing m5.2xlarge --region us-east-1

# Get optimization recommendations
instancepedia optimize m5.2xlarge \
  --region us-east-1 \
  --usage-pattern standard

# Check spot price history (for fault-tolerant workloads)
instancepedia spot-history m5.2xlarge --region us-east-1 --days 90

# Compare with alternative instance types
instancepedia list \
  --min-vcpu 8 \
  --min-memory 32 \
  --current-generation \
  --sort price

# Compare m5 vs m6i (newer generation)
instancepedia compare m5.2xlarge m6i.2xlarge

# Check if ARM is viable
instancepedia compare m5.2xlarge m6g.2xlarge

# Regional cost comparison
instancepedia compare-regions m5.2xlarge \
  --regions us-east-1,us-east-2,us-west-2
```

**Script for Reporting**:

```bash
#!/bin/bash
# Cost analysis report for m5.2xlarge fleet

INSTANCE_TYPE="m5.2xlarge"
REGION="us-east-1"
COUNT=50

echo "=== Current Fleet Analysis ==="
echo "Instance Type: $INSTANCE_TYPE"
echo "Count: $COUNT"
echo "Region: $REGION"
echo ""

# Get pricing data
PRICING=$(instancepedia pricing $INSTANCE_TYPE --region $REGION --format json)

ON_DEMAND=$(echo $PRICING | jq -r '.on_demand_price')
SPOT=$(echo $PRICING | jq -r '.spot_price')
RI_1Y=$(echo $PRICING | jq -r '.reserved_1y_no_upfront')
SP_1Y=$(echo $PRICING | jq -r '.savings_plan_1y')

# Calculate monthly costs (730 hours)
HOURS=730

ON_DEMAND_MONTHLY=$(echo "$ON_DEMAND * $HOURS * $COUNT" | bc)
SPOT_MONTHLY=$(echo "$SPOT * $HOURS * $COUNT" | bc)
RI_MONTHLY=$(echo "$RI_1Y * $HOURS * $COUNT" | bc)
SP_MONTHLY=$(echo "$SP_1Y * $HOURS * $COUNT" | bc)

echo "=== Monthly Cost Comparison ==="
echo "On-Demand:     \$$(printf '%0.2f' $ON_DEMAND_MONTHLY)"
echo "Spot:          \$$(printf '%0.2f' $SPOT_MONTHLY) ($(echo "scale=1; (1 - $SPOT/$ON_DEMAND) * 100" | bc)% savings)"
echo "RI (1yr):      \$$(printf '%0.2f' $RI_MONTHLY) ($(echo "scale=1; (1 - $RI_1Y/$ON_DEMAND) * 100" | bc)% savings)"
echo "Savings Plan:  \$$(printf '%0.2f' $SP_MONTHLY) ($(echo "scale=1; (1 - $SP_1Y/$ON_DEMAND) * 100" | bc)% savings)"
echo ""

# Potential annual savings
ANNUAL_SAVINGS=$(echo "($ON_DEMAND_MONTHLY - $SP_MONTHLY) * 12" | bc)
echo "=== Recommendation ==="
echo "Switch to Compute Savings Plan (1-year)"
echo "Annual Savings: \$$(printf '%0.2f' $ANNUAL_SAVINGS)"
```

**Recommendation**: Compute Savings Plan (1-year) saves ~$50,000/year vs on-demand.

---

## Development Environments

### Scenario: Setting Up Dev Boxes for Engineering Team

**Requirements**:
- Budget-friendly for 10 engineers
- Sufficient for local development (2-4 vCPUs, 4-8 GB RAM)
- Only needed during work hours (~50 hours/week)
- Regional flexibility

**Finding the Cheapest Option**:

```bash
# Find budget instances
instancepedia list \
  --min-vcpu 2 \
  --max-vcpu 4 \
  --min-memory 4 \
  --max-memory 8 \
  --current-generation \
  --sort price \
  --format table

# Apply the "development" preset
instancepedia presets apply development

# Compare top candidates
instancepedia compare t3.medium t3a.medium

# Check spot pricing (safe for dev boxes)
instancepedia spot-history t3a.medium --region us-east-1

# Multi-region comparison
instancepedia compare-regions t3a.medium \
  --regions us-east-1,us-east-2,us-west-1,us-west-2

# Monthly cost estimate (220 hours/month, 50 hrs/week * 4.4 weeks)
instancepedia cost-estimate t3a.medium --hours 220 --region us-east-1
```

**Create Custom Preset**:

```bash
# Save as reusable preset
instancepedia presets save dev-box \
  --min-vcpu 2 \
  --max-vcpu 4 \
  --min-memory 4 \
  --max-memory 8 \
  --current-generation \
  --architecture x86_64

# Use preset later
instancepedia presets apply dev-box
```

**Decision**: t3a.medium on spot (99.5% uptime for dev) in us-east-2 (cheapest region). Monthly cost per engineer: ~$15.

---

## Machine Learning Workloads

### Scenario: Training Deep Learning Models

**Requirements**:
- GPU acceleration (NVIDIA preferred)
- 16+ GB GPU memory for large models
- Sufficient CPU and RAM for preprocessing
- Cost-effective for intermittent training

**Finding GPU Instances**:

```bash
# Launch TUI
instancepedia

# Navigate to "Accelerated Computing" category
# Or use filter:
# Press F
# Check "Has GPU"
# Apply

# Review p3, p4, g5 families
```

**CLI Analysis**:

```bash
# Find GPU instances
instancepedia list --has-gpu --sort price

# Apply ML preset
instancepedia presets apply gpu-ml

# Compare GPU families
instancepedia compare p3.2xlarge p4d.24xlarge g5.xlarge

# Detailed specs for g5 family (latest, cost-effective)
instancepedia compare-family g5

# Spot pricing (good for training jobs that can be interrupted)
instancepedia spot-history g5.xlarge --region us-east-1 --days 30

# Check volatility across regions
for region in us-east-1 us-west-2 eu-west-1; do
  echo "=== $region ==="
  instancepedia spot-history g5.xlarge --region $region --days 7 | grep "Current spot"
done

# Cost optimization
instancepedia optimize g5.xlarge --region us-east-1 --usage-pattern intermittent
```

**Infrastructure-as-Code Integration**:

```python
#!/usr/bin/env python3
"""Select best GPU instance for ML training"""

import subprocess
import json

def get_best_gpu_instance(min_gpu_memory_gb=16, max_price_per_hour=5.0):
    """Find cheapest GPU instance meeting requirements"""

    # Get all GPU instances with pricing
    result = subprocess.run([
        'instancepedia', 'list',
        '--has-gpu',
        '--sort', 'price',
        '--format', 'json',
        '--quiet'
    ], capture_output=True, text=True)

    instances = json.loads(result.stdout)

    # Filter by requirements
    for inst in instances:
        # Check price
        if inst.get('pricing', {}).get('on_demand_price', 999) > max_price_per_hour:
            continue

        # Check GPU memory (would need to parse GPU info)
        # For demo, just return first match
        return inst['instance_type']

    return None

if __name__ == '__main__':
    instance = get_best_gpu_instance()
    print(f"Recommended GPU instance: {instance}")
```

**Decision**: g5.xlarge on spot for training jobs (70% cheaper than on-demand), with checkpoint-based resumption.

---

## Batch Processing

### Scenario: Nightly ETL Jobs

**Requirements**:
- High CPU for data transformation
- Runs 4 hours every night (120 hours/month)
- Can tolerate interruptions (spot-friendly)
- Process large data volumes

**Finding Compute-Optimized Instances**:

```bash
# Apply compute-intensive preset
instancepedia presets apply compute-intensive

# Or filter manually
instancepedia list \
  --family c6i,c7g \
  --min-vcpu 8 \
  --current-generation \
  --sort price

# Compare Intel vs Graviton
instancepedia compare c6i.2xlarge c7g.2xlarge

# Spot price analysis (critical for batch jobs)
instancepedia spot-history c6i.2xlarge --region us-east-1 --days 30

# Check spot price volatility
instancepedia optimize c6i.2xlarge \
  --region us-east-1 \
  --usage-pattern spot
```

**Automation Script**:

```bash
#!/bin/bash
# Batch job instance selector

FAMILY="c6i"
MIN_VCPU=8
REGION="us-east-1"

echo "Finding best instance for batch processing..."

# Get instances sorted by spot price
INSTANCES=$(instancepedia list \
  --family $FAMILY \
  --min-vcpu $MIN_VCPU \
  --region $REGION \
  --sort price \
  --format json \
  --quiet)

# Parse top instance
TOP_INSTANCE=$(echo $INSTANCES | jq -r '.[0].instance_type')
SPOT_PRICE=$(echo $INSTANCES | jq -r '.[0].pricing.spot_price')

echo "Selected: $TOP_INSTANCE"
echo "Spot Price: \$${SPOT_PRICE}/hour"

# Estimate monthly cost (120 hours)
MONTHLY_COST=$(echo "$SPOT_PRICE * 120" | bc)
echo "Monthly Cost: \$${MONTHLY_COST}"

# Export for Terraform/CloudFormation
echo $TOP_INSTANCE > selected_instance.txt
```

**Decision**: c6i.2xlarge on spot (~$0.17/hour vs $0.34 on-demand). Monthly cost: ~$20 for 120 hours.

---

## Infrastructure Automation

### Scenario: Terraform Module for Auto-Selecting Instance Types

**Goal**: Automatically select the cheapest instance matching requirements.

**Terraform Integration**:

```hcl
# instance_selector.tf

# External data source to run instancepedia
data "external" "selected_instance" {
  program = ["bash", "${path.module}/select_instance.sh"]

  query = {
    min_vcpu      = var.min_vcpu
    min_memory    = var.min_memory
    region        = var.aws_region
    architecture  = var.architecture
  }
}

resource "aws_instance" "app" {
  ami           = data.aws_ami.latest.id
  instance_type = data.external.selected_instance.result.instance_type

  tags = {
    Name = "Auto-selected instance"
    Type = data.external.selected_instance.result.instance_type
  }
}

output "selected_instance" {
  value = data.external.selected_instance.result.instance_type
}

output "estimated_hourly_cost" {
  value = data.external.selected_instance.result.price
}
```

**Selection Script** (`select_instance.sh`):

```bash
#!/bin/bash
# Parse Terraform query
eval "$(jq -r '@sh "MIN_VCPU=\(.min_vcpu) MIN_MEMORY=\(.min_memory) REGION=\(.region) ARCH=\(.architecture)"')"

# Find best instance
RESULT=$(instancepedia list \
  --min-vcpu $MIN_VCPU \
  --min-memory $MIN_MEMORY \
  --region $REGION \
  --architecture $ARCH \
  --current-generation \
  --sort price \
  --format json \
  --quiet | jq '.[0]')

# Extract details
INSTANCE_TYPE=$(echo $RESULT | jq -r '.instance_type')
PRICE=$(echo $RESULT | jq -r '.pricing.on_demand_price')

# Return as JSON for Terraform
jq -n \
  --arg instance_type "$INSTANCE_TYPE" \
  --arg price "$PRICE" \
  '{"instance_type": $instance_type, "price": $price}'
```

**Usage**:

```bash
terraform apply \
  -var="min_vcpu=4" \
  -var="min_memory=8" \
  -var="architecture=arm64" \
  -var="aws_region=us-east-1"
```

---

## Budget Planning

### Scenario: Annual Infrastructure Budget Forecast

**Goal**: Estimate infrastructure costs for the next year.

**Fleet Composition**:
- 20 web servers (t3.xlarge)
- 5 databases (r6i.xlarge)
- 10 batch workers (c6i.2xlarge, spot)
- 50 dev environments (t3a.medium, 50 hrs/week)

**Analysis Script**:

```bash
#!/bin/bash
# Annual budget calculator

echo "=== Infrastructure Budget Forecast ===" > budget_report.txt
echo "" >> budget_report.txt

REGION="us-east-1"

# Web servers (24/7, Savings Plan)
WEB_COUNT=20
WEB_TYPE="t3.xlarge"
WEB_PRICING=$(instancepedia pricing $WEB_TYPE --region $REGION --format json)
WEB_PRICE=$(echo $WEB_PRICING | jq -r '.savings_plan_1y')
WEB_MONTHLY=$(echo "$WEB_PRICE * 730 * $WEB_COUNT" | bc)
WEB_ANNUAL=$(echo "$WEB_MONTHLY * 12" | bc)

echo "Web Servers ($WEB_TYPE x $WEB_COUNT):" >> budget_report.txt
echo "  Pricing Model: Compute Savings Plan (1-year)" >> budget_report.txt
echo "  Monthly: \$$(printf '%0.2f' $WEB_MONTHLY)" >> budget_report.txt
echo "  Annual:  \$$(printf '%0.2f' $WEB_ANNUAL)" >> budget_report.txt
echo "" >> budget_report.txt

# Databases (24/7, Reserved Instance)
DB_COUNT=5
DB_TYPE="r6i.xlarge"
DB_PRICING=$(instancepedia pricing $DB_TYPE --region $REGION --format json)
DB_PRICE=$(echo $DB_PRICING | jq -r '.reserved_1y_partial_upfront')
DB_MONTHLY=$(echo "$DB_PRICE * 730 * $DB_COUNT" | bc)
DB_ANNUAL=$(echo "$DB_MONTHLY * 12" | bc)

echo "Databases ($DB_TYPE x $DB_COUNT):" >> budget_report.txt
echo "  Pricing Model: 1-Year RI (Partial Upfront)" >> budget_report.txt
echo "  Monthly: \$$(printf '%0.2f' $DB_MONTHLY)" >> budget_report.txt
echo "  Annual:  \$$(printf '%0.2f' $DB_ANNUAL)" >> budget_report.txt
echo "" >> budget_report.txt

# Batch workers (spot, 120 hours/month)
BATCH_COUNT=10
BATCH_TYPE="c6i.2xlarge"
BATCH_PRICING=$(instancepedia pricing $BATCH_TYPE --region $REGION --format json)
BATCH_PRICE=$(echo $BATCH_PRICING | jq -r '.spot_price')
BATCH_MONTHLY=$(echo "$BATCH_PRICE * 120 * $BATCH_COUNT" | bc)
BATCH_ANNUAL=$(echo "$BATCH_MONTHLY * 12" | bc)

echo "Batch Workers ($BATCH_TYPE x $BATCH_COUNT):" >> budget_report.txt
echo "  Pricing Model: Spot (120 hrs/month)" >> budget_report.txt
echo "  Monthly: \$$(printf '%0.2f' $BATCH_MONTHLY)" >> budget_report.txt
echo "  Annual:  \$$(printf '%0.2f' $BATCH_ANNUAL)" >> budget_report.txt
echo "" >> budget_report.txt

# Dev environments (spot, 220 hours/month)
DEV_COUNT=50
DEV_TYPE="t3a.medium"
DEV_PRICING=$(instancepedia pricing $DEV_TYPE --region $REGION --format json)
DEV_PRICE=$(echo $DEV_PRICING | jq -r '.spot_price')
DEV_MONTHLY=$(echo "$DEV_PRICE * 220 * $DEV_COUNT" | bc)
DEV_ANNUAL=$(echo "$DEV_MONTHLY * 12" | bc)

echo "Dev Environments ($DEV_TYPE x $DEV_COUNT):" >> budget_report.txt
echo "  Pricing Model: Spot (220 hrs/month)" >> budget_report.txt
echo "  Monthly: \$$(printf '%0.2f' $DEV_MONTHLY)" >> budget_report.txt
echo "  Annual:  \$$(printf '%0.2f' $DEV_ANNUAL)" >> budget_report.txt
echo "" >> budget_report.txt

# Total
TOTAL_MONTHLY=$(echo "$WEB_MONTHLY + $DB_MONTHLY + $BATCH_MONTHLY + $DEV_MONTHLY" | bc)
TOTAL_ANNUAL=$(echo "$TOTAL_MONTHLY * 12" | bc)

echo "=== TOTAL ===" >> budget_report.txt
echo "Monthly: \$$(printf '%0.2f' $TOTAL_MONTHLY)" >> budget_report.txt
echo "Annual:  \$$(printf '%0.2f' $TOTAL_ANNUAL)" >> budget_report.txt

cat budget_report.txt
```

**Output**:

```
=== Infrastructure Budget Forecast ===

Web Servers (t3.xlarge x 20):
  Pricing Model: Compute Savings Plan (1-year)
  Monthly: $2,920.00
  Annual:  $35,040.00

Databases (r6i.xlarge x 5):
  Pricing Model: 1-Year RI (Partial Upfront)
  Monthly: $1,095.00
  Annual:  $13,140.00

Batch Workers (c6i.2xlarge x 10):
  Pricing Model: Spot (120 hrs/month)
  Monthly: $204.00
  Annual:  $2,448.00

Dev Environments (t3a.medium x 50):
  Pricing Model: Spot (220 hrs/month)
  Monthly: $825.00
  Annual:  $9,900.00

=== TOTAL ===
Monthly: $5,044.00
Annual:  $60,528.00
```

---

## Tips for All Scenarios

### 1. Always Check Multiple Regions

Pricing varies significantly by region:

```bash
instancepedia compare-regions <instance-type> \
  --regions us-east-1,us-west-2,eu-west-1,ap-southeast-1
```

### 2. Use Filter Presets for Consistency

Create presets for your common use cases:

```bash
instancepedia presets save my-api-server \
  --min-vcpu 4 \
  --min-memory 8 \
  --current-generation \
  --architecture arm64
```

### 3. Verify Spot Price Stability

Before using spot instances, check 30-day history:

```bash
instancepedia spot-history <instance-type> --days 30
```

Look for low standard deviation (< 20% of mean).

### 4. Leverage ARM (Graviton) for Savings

Graviton instances often provide 20-40% cost savings:

```bash
instancepedia list --architecture arm64 --sort price
```

### 5. Export Data for Stakeholder Reports

```bash
# Generate comprehensive CSV
instancepedia list \
  --family t3,m5,c5,r5 \
  --current-generation \
  --format csv > instance_options.csv

# Import into Google Sheets or Excel for presentations
```
