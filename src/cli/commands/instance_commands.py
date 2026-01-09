"""Instance-related CLI commands"""

from concurrent.futures import ThreadPoolExecutor, as_completed

from src.services.instance_service import InstanceService
from src.services.pricing_service import PricingService
from src.services.filter_service import FilterCriteria, apply_filters
from src.models.instance_type import InstanceType, PricingInfo
from src.cli.output import get_formatter
from src.config.settings import Settings

from .base import (
    status, print_error, get_aws_client, fetch_instance_pricing, write_output,
    get_instance_by_name, get_instances_by_names
)


def cmd_list(args) -> int:
    """List instance types command"""
    formatter = get_formatter(args.format)
    aws_client = get_aws_client(args.region, args.profile)
    instance_service = InstanceService(aws_client)

    try:
        status(f"Fetching instance types for region {args.region}...", args.quiet)
        instances = instance_service.get_instance_types(fetch_pricing=args.include_pricing)

        # Apply non-price filters using unified filter service
        criteria = FilterCriteria.from_cli_args(args)
        instances = apply_filters(instances, criteria)

        # Fetch pricing if requested and not already fetched
        if args.include_pricing and instances:
            instances = _fetch_pricing_for_instances(instances, args)

        # Re-apply price filters after pricing is fetched
        if criteria.min_price is not None or criteria.max_price is not None:
            instances = apply_filters(instances, FilterCriteria(
                min_price=criteria.min_price,
                max_price=criteria.max_price
            ))

        # Sort instances
        instances = sorted(instances, key=lambda x: x.instance_type)

        # Output
        output = formatter.format_instance_list(instances, args.region)
        write_output(output, args.output, args.quiet)

        return 0

    except Exception as e:
        print_error(str(e), debug=args.debug, exception=e)
        return 1


def cmd_show(args) -> int:
    """Show instance details command"""
    formatter = get_formatter(args.format)
    aws_client = get_aws_client(args.region, args.profile)

    try:
        instance = get_instance_by_name(aws_client, args.instance_type, args.region, args.quiet)
        if not instance:
            print_error(f"Instance type '{args.instance_type}' not found in region {args.region}")
            return 1

        # Fetch pricing if requested
        if args.include_pricing:
            status("Fetching pricing information...", args.quiet)
            pricing_service = PricingService(aws_client)
            instance.pricing = fetch_instance_pricing(
                pricing_service, instance.instance_type, args.region, include_ri=True
            )

        # Output
        output = formatter.format_instance_detail(instance, args.region)
        write_output(output, args.output, args.quiet)

        return 0

    except Exception as e:
        print_error(str(e), debug=args.debug, exception=e)
        return 1


def cmd_search(args) -> int:
    """Search instance types command (alias for list with search)"""
    return cmd_list(args)


def cmd_compare(args) -> int:
    """Compare two instance types command"""
    formatter = get_formatter(args.format)
    aws_client = get_aws_client(args.region, args.profile)

    try:
        found = get_instances_by_names(
            aws_client,
            [args.instance_type1, args.instance_type2],
            args.region,
            args.quiet
        )
        instance1, instance2 = found[0], found[1]

        if not instance1:
            print_error(f"Instance type '{args.instance_type1}' not found in region {args.region}")
            return 1
        if not instance2:
            print_error(f"Instance type '{args.instance_type2}' not found in region {args.region}")
            return 1

        # Fetch pricing if requested
        if args.include_pricing:
            status("Fetching pricing information...", args.quiet)
            pricing_service = PricingService(aws_client)

            for instance in [instance1, instance2]:
                on_demand = pricing_service.get_on_demand_price(
                    instance.instance_type,
                    args.region,
                    max_retries=3
                )
                spot = pricing_service.get_spot_price(instance.instance_type, args.region)
                instance.pricing = PricingInfo(
                    on_demand_price=on_demand,
                    spot_price=spot
                )

        # Output
        output = formatter.format_comparison(instance1, instance2, args.region)
        write_output(output, args.output, args.quiet)

        return 0

    except Exception as e:
        print_error(str(e), debug=args.debug, exception=e)
        return 1


def cmd_compare_family(args) -> int:
    """Compare all instances in a family command"""
    formatter = get_formatter(args.format)
    aws_client = get_aws_client(args.region, args.profile)
    instance_service = InstanceService(aws_client)

    try:
        status(f"Fetching {args.family} family instances from {args.region}...", args.quiet)

        instances = instance_service.get_instance_types(fetch_pricing=False)

        # Filter to family
        family_instances = [i for i in instances if i.instance_type.startswith(args.family + '.')]

        if not family_instances:
            print_error(f"No instances found for family '{args.family}' in region {args.region}")
            return 1

        # Fetch pricing if requested
        if args.include_pricing:
            status(f"Fetching pricing for {len(family_instances)} instances...", args.quiet)

            settings = Settings()
            pricing_service = PricingService(aws_client, settings=settings)

            def fetch_price(instance: InstanceType):
                try:
                    on_demand = pricing_service.get_on_demand_price(instance.instance_type, args.region)
                    spot = pricing_service.get_spot_price(instance.instance_type, args.region)
                    instance.pricing = PricingInfo(on_demand_price=on_demand, spot_price=spot)
                except Exception:
                    pass

            with ThreadPoolExecutor(max_workers=settings.cli_pricing_concurrency) as executor:
                futures = {executor.submit(fetch_price, inst): inst for inst in family_instances}
                for future in as_completed(futures):
                    pass  # Just wait for completion

        # Sort instances
        if args.sort_by == "vcpu":
            family_instances.sort(key=lambda x: x.vcpu_info.default_vcpus)
        elif args.sort_by == "memory":
            family_instances.sort(key=lambda x: x.memory_info.size_in_gb)
        elif args.sort_by == "price":
            family_instances.sort(key=lambda x: x.pricing.on_demand_price if x.pricing and x.pricing.on_demand_price else float('inf'))
        else:  # name
            family_instances.sort(key=lambda x: x.instance_type)

        # Format output
        if args.format == "json":
            import json
            data = {
                'family': args.family,
                'region': args.region,
                'count': len(family_instances),
                'instances': [
                    {
                        'instance_type': i.instance_type,
                        'vcpu': i.vcpu_info.default_vcpus,
                        'memory_gb': i.memory_info.size_in_gb,
                        'generation': i.generation_label,
                        'on_demand_price': i.pricing.on_demand_price if i.pricing else None,
                        'spot_price': i.pricing.spot_price if i.pricing else None,
                    }
                    for i in family_instances
                ]
            }
            output = json.dumps(data, indent=2)
        else:
            # Table format
            from tabulate import tabulate
            headers = ["Instance Type", "Gen", "vCPU", "Memory (GB)", "Network"]
            if args.include_pricing:
                headers.extend(["On-Demand", "Spot"])

            rows = []
            for inst in family_instances:
                row = [
                    inst.instance_type,
                    inst.generation_label,
                    inst.vcpu_info.default_vcpus,
                    f"{inst.memory_info.size_in_gb:.1f}",
                    inst.network_info.network_performance,
                ]
                if args.include_pricing:
                    on_demand = f"${inst.pricing.on_demand_price:.4f}" if inst.pricing and inst.pricing.on_demand_price else "N/A"
                    spot = f"${inst.pricing.spot_price:.4f}" if inst.pricing and inst.pricing.spot_price else "N/A"
                    row.extend([on_demand, spot])
                rows.append(row)

            output = f"Family comparison for {args.family} in {args.region}:\n\n"
            output += tabulate(rows, headers=headers, tablefmt="grid")

        write_output(output, args.output, args.quiet)

        return 0

    except Exception as e:
        print_error(str(e), debug=args.debug, exception=e)
        return 1


def cmd_regions(args) -> int:
    """List available regions command"""
    formatter = get_formatter(args.format)

    try:
        # Try to get accessible regions
        aws_client = get_aws_client("us-east-1", args.profile)
        accessible_regions = aws_client.get_accessible_regions()

        if accessible_regions:
            # Use accessible regions with names
            from src.models.region import AWS_REGIONS
            regions = [
                {"code": code, "name": AWS_REGIONS.get(code, code)}
                for code in accessible_regions
            ]
        else:
            # Fall back to all known regions
            from src.models.region import AWS_REGIONS
            regions = [
                {"code": code, "name": name}
                for code, name in AWS_REGIONS.items()
            ]

        # Sort by code
        regions = sorted(regions, key=lambda x: x["code"])

        # Output
        output = formatter.format_regions(regions)
        write_output(output, args.output, args.quiet)

        return 0

    except Exception as e:
        print_error(str(e), debug=args.debug, exception=e)
        return 1


# =============================================================================
# Helper Functions
# =============================================================================

def _fetch_pricing_for_instances(instances: list, args) -> list:
    """Fetch pricing for a list of instances."""
    status("Fetching pricing information...", args.quiet)
    settings = Settings()
    aws_client = get_aws_client(args.region, args.profile)
    pricing_service = PricingService(aws_client, settings=settings)

    def fetch_price(instance: InstanceType):
        try:
            on_demand = pricing_service.get_on_demand_price(
                instance.instance_type,
                args.region,
                max_retries=3
            )
            spot = pricing_service.get_spot_price(instance.instance_type, args.region)
            instance.pricing = PricingInfo(
                on_demand_price=on_demand,
                spot_price=spot
            )
        except Exception:
            pass  # Continue if pricing fails for one instance

    with ThreadPoolExecutor(max_workers=settings.cli_pricing_concurrency) as executor:
        futures = {executor.submit(fetch_price, inst): inst for inst in instances}
        completed = 0
        for future in as_completed(futures):
            completed += 1
            if completed % 10 == 0:
                status(f"Fetched pricing for {completed}/{len(instances)} instances...", args.quiet)

    return instances
