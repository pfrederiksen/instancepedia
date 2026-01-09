"""Pricing-related CLI commands"""

import sys

from src.services.instance_service import InstanceService
from src.services.pricing_service import PricingService
from src.cli.output import get_formatter

from .base import print_error, get_aws_client, fetch_instance_pricing, write_output


def cmd_pricing(args) -> int:
    """Get pricing information command"""
    formatter = get_formatter(args.format)
    aws_client = get_aws_client(args.region, args.profile)
    instance_service = InstanceService(aws_client)

    try:
        print(f"Fetching instance type information...", file=sys.stderr)
        instances = instance_service.get_instance_types()

        # Find the instance
        instance = next((inst for inst in instances if inst.instance_type == args.instance_type), None)
        if not instance:
            print(f"Error: Instance type '{args.instance_type}' not found in region {args.region}", file=sys.stderr)
            return 1

        # Fetch pricing
        print("Fetching pricing information...", file=sys.stderr)
        pricing_service = PricingService(aws_client)
        instance.pricing = fetch_instance_pricing(
            pricing_service, instance.instance_type, args.region
        )

        # Output
        output = formatter.format_pricing(instance, args.region)
        write_output(output, args.output, args.quiet)

        return 0

    except Exception as e:
        print_error(str(e), debug=args.debug, exception=e)
        return 1


def cmd_cost_estimate(args) -> int:
    """Cost estimate command"""
    aws_client = get_aws_client(args.region, args.profile)
    instance_service = InstanceService(aws_client)

    try:
        if not args.quiet:
            print(f"Fetching instance type {args.instance_type} in {args.region}...", file=sys.stderr)

        instances = instance_service.get_instance_types(fetch_pricing=False)
        instance = next((i for i in instances if i.instance_type == args.instance_type), None)

        if not instance:
            print(f"Error: Instance type '{args.instance_type}' not found in region {args.region}", file=sys.stderr)
            return 1

        # Fetch pricing
        if not args.quiet:
            print("Fetching pricing information...", file=sys.stderr)

        pricing_service = PricingService(aws_client)
        instance.pricing = fetch_instance_pricing(
            pricing_service, args.instance_type, args.region
        )

        # Calculate costs based on pricing model
        pricing_model = args.pricing_model
        hours_per_month = args.hours_per_month
        months = args.months

        price_per_hour = None
        model_name = pricing_model

        if pricing_model == "on-demand":
            price_per_hour = instance.pricing.on_demand_price
            model_name = "On-Demand"
        elif pricing_model == "spot":
            price_per_hour = instance.pricing.spot_price
            model_name = "Spot"
        elif pricing_model == "savings-1yr":
            price_per_hour = instance.pricing.savings_plan_1yr_no_upfront
            model_name = "1-Year Savings Plan"
        elif pricing_model == "savings-3yr":
            price_per_hour = instance.pricing.savings_plan_3yr_no_upfront
            model_name = "3-Year Savings Plan"

        if price_per_hour is None:
            print(f"Error: {model_name} pricing not available for {args.instance_type}", file=sys.stderr)
            return 1

        # Calculate costs
        monthly_cost = price_per_hour * hours_per_month
        total_cost = monthly_cost * months

        # Format output
        lines = []
        lines.append(f"Cost Estimate for {args.instance_type} in {args.region}")
        lines.append("")
        lines.append(f"Pricing Model: {model_name}")
        lines.append(f"Price per Hour: ${price_per_hour:.4f}")
        lines.append(f"Hours per Month: {hours_per_month}")
        lines.append(f"Duration: {months} month(s)")
        lines.append("")
        lines.append(f"Monthly Cost: ${monthly_cost:.2f}")
        lines.append(f"Total Cost ({months} months): ${total_cost:.2f}")

        # Show comparison with on-demand if using alternative pricing
        if pricing_model != "on-demand" and instance.pricing.on_demand_price:
            on_demand_monthly = instance.pricing.on_demand_price * hours_per_month
            on_demand_total = on_demand_monthly * months
            savings = on_demand_total - total_cost
            savings_pct = (savings / on_demand_total) * 100

            lines.append("")
            lines.append("Comparison with On-Demand:")
            lines.append(f"  On-Demand Total: ${on_demand_total:.2f}")
            lines.append(f"  Your Total: ${total_cost:.2f}")
            lines.append(f"  Savings: ${savings:.2f} ({savings_pct:.1f}%)")

        output = "\n".join(lines)
        write_output(output, args.output, args.quiet)

        return 0

    except Exception as e:
        print_error(str(e), debug=args.debug, exception=e)
        return 1


def cmd_compare_regions(args) -> int:
    """Compare pricing across regions command"""
    regions = [r.strip() for r in args.regions.split(',')]

    try:
        if not args.quiet:
            print(f"Fetching {args.instance_type} from {len(regions)} regions...", file=sys.stderr)

        results = []

        for region in regions:
            try:
                aws_client = get_aws_client(region, None)
                instance_service = InstanceService(aws_client)
                instances = instance_service.get_instance_types(fetch_pricing=False)

                instance = next((i for i in instances if i.instance_type == args.instance_type), None)

                if not instance:
                    results.append({
                        'region': region,
                        'error': 'Instance type not available'
                    })
                    continue

                # Fetch pricing
                pricing_service = PricingService(aws_client)
                on_demand = pricing_service.get_on_demand_price(args.instance_type, region)
                spot = pricing_service.get_spot_price(args.instance_type, region)

                results.append({
                    'region': region,
                    'on_demand': on_demand,
                    'spot': spot,
                    'error': None
                })

            except Exception as e:
                results.append({
                    'region': region,
                    'error': str(e)
                })

        # Format output
        if args.format == "json":
            import json
            output = json.dumps({
                'instance_type': args.instance_type,
                'regions': results
            }, indent=2)
        elif args.format == "csv":
            lines = ["Region,On-Demand Price,Spot Price,Error"]
            for r in results:
                on_demand = f"${r['on_demand']:.4f}" if r.get('on_demand') else "N/A"
                spot = f"${r['spot']:.4f}" if r.get('spot') else "N/A"
                error = r.get('error', '')
                lines.append(f"{r['region']},{on_demand},{spot},{error}")
            output = "\n".join(lines)
        else:
            # Table format
            from tabulate import tabulate
            headers = ["Region", "On-Demand Price", "Spot Price", "Status"]
            rows = []
            for r in results:
                on_demand = f"${r['on_demand']:.4f}/hr" if r.get('on_demand') else "N/A"
                spot = f"${r['spot']:.4f}/hr" if r.get('spot') else "N/A"
                status = r.get('error', 'OK')
                rows.append([r['region'], on_demand, spot, status])

            output = f"Pricing comparison for {args.instance_type} across regions:\n\n"
            output += tabulate(rows, headers=headers, tablefmt="grid")

        write_output(output, args.output, args.quiet)

        return 0

    except Exception as e:
        print_error(str(e), debug=args.debug, exception=e)
        return 1


def cmd_spot_history(args) -> int:
    """Spot price history command"""
    try:
        aws_client = get_aws_client(args.region, args.profile)
        pricing_service = PricingService(aws_client)

        if not args.quiet:
            print(f"Fetching spot price history for {args.instance_type} in {args.region}...", file=sys.stderr)
            print(f"Looking back {args.days} days...", file=sys.stderr)

        history = pricing_service.get_spot_price_history(
            args.instance_type,
            args.region,
            args.days
        )

        if not history:
            print(f"No spot price history available for {args.instance_type} in {args.region}", file=sys.stderr)
            return 1

        # Format output
        if args.format == "json":
            import json
            data = {
                "instance_type": history.instance_type,
                "region": history.region,
                "days": history.days,
                "statistics": {
                    "current_price": history.current_price,
                    "min_price": history.min_price,
                    "max_price": history.max_price,
                    "avg_price": history.avg_price,
                    "median_price": history.median_price,
                    "std_dev": history.std_dev,
                    "volatility_percentage": history.volatility_percentage,
                    "price_range": history.price_range,
                    "savings_vs_current": history.savings_vs_current
                },
                "price_points": [
                    {
                        "timestamp": ts.isoformat(),
                        "price": price
                    }
                    for ts, price in history.price_points
                ]
            }
            output = json.dumps(data, indent=2)
        else:
            output = _format_spot_history_table(history)

        write_output(output, args.output, args.quiet)

        return 0

    except Exception as e:
        print_error(str(e), debug=args.debug, exception=e)
        return 1


def _format_spot_history_table(history) -> str:
    """Format spot history as table output."""
    lines = []
    lines.append(f"Spot Price History for {history.instance_type} in {history.region}")
    lines.append(f"Period: Last {history.days} days ({len(history.price_points)} data points)")
    lines.append("")
    lines.append("Price Statistics:")
    lines.append(f"  Current Price:   ${history.current_price:.4f}/hr" if history.current_price else "  Current Price:   N/A")
    lines.append(f"  Minimum Price:   ${history.min_price:.4f}/hr" if history.min_price else "  Minimum Price:   N/A")
    lines.append(f"  Maximum Price:   ${history.max_price:.4f}/hr" if history.max_price else "  Maximum Price:   N/A")
    lines.append(f"  Average Price:   ${history.avg_price:.4f}/hr" if history.avg_price else "  Average Price:   N/A")
    lines.append(f"  Median Price:    ${history.median_price:.4f}/hr" if history.median_price else "  Median Price:    N/A")
    lines.append("")

    # Price range and volatility
    if history.price_range is not None:
        lines.append(f"  Price Range:     ${history.price_range:.4f}/hr ({history.min_price:.4f} - {history.max_price:.4f})")

    if history.volatility_percentage is not None:
        lines.append(f"  Volatility:      {history.volatility_percentage:.1f}% (std dev / avg)")

        # Interpret volatility
        if history.volatility_percentage < 10:
            volatility_label = "Very Stable"
        elif history.volatility_percentage < 20:
            volatility_label = "Stable"
        elif history.volatility_percentage < 30:
            volatility_label = "Moderate"
        elif history.volatility_percentage < 50:
            volatility_label = "Volatile"
        else:
            volatility_label = "Highly Volatile"
        lines.append(f"  Stability:       {volatility_label}")

    lines.append("")

    # Savings potential
    if history.savings_vs_current is not None and history.savings_vs_current > 0:
        lines.append(f"Potential Savings:")
        lines.append(f"  If you had bought at minimum price instead of current:")
        lines.append(f"  Savings: {history.savings_vs_current:.1f}% cheaper")
        lines.append("")

    # Simple text-based price trend visualization
    lines.append("Price Trend (last 10 data points):")
    recent_points = history.price_points[-10:] if len(history.price_points) > 10 else history.price_points

    for ts, price in recent_points:
        # Create simple bar chart
        if history.min_price and history.max_price and history.max_price > history.min_price:
            normalized = (price - history.min_price) / (history.max_price - history.min_price)
            bar_length = int(normalized * 40)
            bar = "█" * bar_length
            lines.append(f"  {ts.strftime('%Y-%m-%d %H:%M')}  ${price:.4f}  {bar}")
        else:
            lines.append(f"  {ts.strftime('%Y-%m-%d %H:%M')}  ${price:.4f}")

    return "\n".join(lines)
