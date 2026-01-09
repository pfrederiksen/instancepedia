"""Instance-related CLI commands"""

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.services.instance_service import InstanceService
from src.services.pricing_service import PricingService
from src.services.free_tier_service import FreeTierService
from src.models.instance_type import InstanceType, PricingInfo
from src.cli.output import get_formatter
from src.config.settings import Settings

from .base import print_error, get_aws_client, fetch_instance_pricing, write_output


def cmd_list(args) -> int:
    """List instance types command"""
    formatter = get_formatter(args.format)
    aws_client = get_aws_client(args.region, args.profile)
    instance_service = InstanceService(aws_client)

    try:
        print(f"Fetching instance types for region {args.region}...", file=sys.stderr)
        instances = instance_service.get_instance_types(fetch_pricing=args.include_pricing)

        # Apply filters
        instances = _apply_filters(instances, args)

        # Fetch pricing if requested and not already fetched
        if args.include_pricing and instances:
            instances = _fetch_pricing_for_instances(instances, args)

        # Apply price range filter (after pricing is fetched)
        instances = _apply_price_filter(instances, args)

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
    instance_service = InstanceService(aws_client)

    try:
        print(f"Fetching instance types for region {args.region}...", file=sys.stderr)
        instances = instance_service.get_instance_types()

        # Find the instance
        instance = next((inst for inst in instances if inst.instance_type == args.instance_type), None)
        if not instance:
            print(f"Error: Instance type '{args.instance_type}' not found in region {args.region}", file=sys.stderr)
            return 1

        # Fetch pricing if requested
        if args.include_pricing:
            print("Fetching pricing information...", file=sys.stderr)
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
    instance_service = InstanceService(aws_client)

    try:
        print(f"Fetching instance types for region {args.region}...", file=sys.stderr)
        instances = instance_service.get_instance_types()

        # Find both instances
        instance1 = next((inst for inst in instances if inst.instance_type == args.instance_type1), None)
        instance2 = next((inst for inst in instances if inst.instance_type == args.instance_type2), None)

        if not instance1:
            print(f"Error: Instance type '{args.instance_type1}' not found in region {args.region}", file=sys.stderr)
            return 1
        if not instance2:
            print(f"Error: Instance type '{args.instance_type2}' not found in region {args.region}", file=sys.stderr)
            return 1

        # Fetch pricing if requested
        if args.include_pricing:
            print("Fetching pricing information...", file=sys.stderr)
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
        if not args.quiet:
            print(f"Fetching {args.family} family instances from {args.region}...", file=sys.stderr)

        instances = instance_service.get_instance_types(fetch_pricing=False)

        # Filter to family
        family_instances = [i for i in instances if i.instance_type.startswith(args.family + '.')]

        if not family_instances:
            print(f"Error: No instances found for family '{args.family}' in region {args.region}", file=sys.stderr)
            return 1

        # Fetch pricing if requested
        if args.include_pricing:
            if not args.quiet:
                print(f"Fetching pricing for {len(family_instances)} instances...", file=sys.stderr)

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

def _apply_filters(instances: list, args) -> list:
    """Apply all non-price filters to instances."""
    if args.search:
        search_lower = args.search.lower()
        instances = [inst for inst in instances if search_lower in inst.instance_type.lower()]

    if args.free_tier_only:
        free_tier_service = FreeTierService()
        instances = [inst for inst in instances if free_tier_service.is_eligible(inst.instance_type)]

    if args.family:
        instances = [inst for inst in instances if inst.instance_type.startswith(args.family)]

    # Storage type filter
    if hasattr(args, 'storage_type') and args.storage_type:
        if args.storage_type == "ebs-only":
            instances = [
                inst for inst in instances
                if inst.instance_storage_info is None or inst.instance_storage_info.total_size_in_gb is None or inst.instance_storage_info.total_size_in_gb == 0
            ]
        elif args.storage_type == "instance-store":
            instances = [
                inst for inst in instances
                if inst.instance_storage_info and inst.instance_storage_info.total_size_in_gb and inst.instance_storage_info.total_size_in_gb > 0
            ]

    # NVMe support filter
    if hasattr(args, 'nvme') and args.nvme:
        if args.nvme == "required":
            instances = [inst for inst in instances if inst.instance_storage_info and inst.instance_storage_info.nvme_support == "required"]
        elif args.nvme == "supported":
            instances = [inst for inst in instances if inst.instance_storage_info and inst.instance_storage_info.nvme_support == "supported"]
        elif args.nvme == "unsupported":
            instances = [inst for inst in instances if not inst.instance_storage_info or not inst.instance_storage_info.nvme_support or inst.instance_storage_info.nvme_support == "unsupported"]

    # Processor family filter
    if hasattr(args, 'processor_family') and args.processor_family:
        instances = _apply_processor_filter(instances, args.processor_family)

    # Network performance filter
    if hasattr(args, 'network_performance') and args.network_performance:
        instances = _apply_network_filter(instances, args.network_performance)

    return instances


def _apply_processor_filter(instances: list, processor_family: str) -> list:
    """Apply processor family filter."""
    def is_amd_instance(instance_type: str) -> bool:
        """Check if instance type is AMD (has 'a' suffix before size)"""
        parts = instance_type.split('.')
        if len(parts) >= 1:
            family_part = parts[0]
            return family_part.endswith('a') and not family_part.endswith('ga')
        return False

    if processor_family == "intel":
        return [
            inst for inst in instances
            if not is_amd_instance(inst.instance_type) and "arm64" not in inst.processor_info.supported_architectures
        ]
    elif processor_family == "amd":
        return [inst for inst in instances if is_amd_instance(inst.instance_type)]
    elif processor_family == "graviton":
        return [inst for inst in instances if "arm64" in inst.processor_info.supported_architectures]

    return instances


def _apply_network_filter(instances: list, network_performance: str) -> list:
    """Apply network performance filter."""
    perf_map = {
        "low": ["low", "very low", "up to 5 gigabit"],
        "moderate": ["moderate", "up to 10 gigabit", "up to 12 gigabit"],
        "high": ["high", "10 gigabit", "12 gigabit", "25 gigabit", "up to 25 gigabit"],
        "very-high": ["50 gigabit", "100 gigabit", "200 gigabit", "up to 100 gigabit", "up to 200 gigabit"]
    }
    target_perfs = perf_map.get(network_performance, [])
    return [
        inst for inst in instances
        if any(perf.lower() in inst.network_info.network_performance.lower() for perf in target_perfs)
    ]


def _apply_price_filter(instances: list, args) -> list:
    """Apply price range filter (after pricing is fetched)."""
    if not hasattr(args, 'min_price') and not hasattr(args, 'max_price'):
        return instances

    min_price = getattr(args, 'min_price', None)
    max_price = getattr(args, 'max_price', None)

    if min_price is None and max_price is None:
        return instances

    def matches_price_range(inst):
        if not inst.pricing or inst.pricing.on_demand_price is None:
            return True  # Keep instances without pricing

        price = inst.pricing.on_demand_price
        if min_price is not None and price < min_price:
            return False
        if max_price is not None and price > max_price:
            return False
        return True

    return [inst for inst in instances if matches_price_range(inst)]


def _fetch_pricing_for_instances(instances: list, args) -> list:
    """Fetch pricing for a list of instances."""
    print("Fetching pricing information...", file=sys.stderr)
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
            if not args.quiet and completed % 10 == 0:
                print(f"Fetched pricing for {completed}/{len(instances)} instances...", file=sys.stderr)

    return instances
