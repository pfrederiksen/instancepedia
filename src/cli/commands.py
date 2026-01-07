"""CLI command handlers"""

import sys
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.services.aws_client import AWSClient
from src.services.instance_service import InstanceService
from src.services.pricing_service import PricingService
from src.services.free_tier_service import FreeTierService
from src.services.filter_preset_service import FilterPresetService
from src.models.instance_type import InstanceType, PricingInfo
from src.cli.output import get_formatter
from src.config.settings import Settings
from src.cache import get_pricing_cache


def get_aws_client(region: str, profile: Optional[str] = None) -> AWSClient:
    """Get AWS client with error handling"""
    try:
        return AWSClient(region, profile)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_list(args) -> int:
    """List instance types command"""
    formatter = get_formatter(args.format)
    aws_client = get_aws_client(args.region, args.profile)
    instance_service = InstanceService(aws_client)
    
    try:
        print(f"Fetching instance types for region {args.region}...", file=sys.stderr)
        instances = instance_service.get_instance_types(fetch_pricing=args.include_pricing)
        
        # Apply filters
        if args.search:
            search_lower = args.search.lower()
            instances = [inst for inst in instances if search_lower in inst.instance_type.lower()]
        
        if args.free_tier_only:
            free_tier_service = FreeTierService()
            instances = [inst for inst in instances if free_tier_service.is_eligible(inst.instance_type)]
        
        if args.family:
            instances = [inst for inst in instances if inst.instance_type.startswith(args.family)]
        
        # Fetch pricing if requested and not already fetched
        if args.include_pricing and instances:
            print("Fetching pricing information...", file=sys.stderr)
            pricing_service = PricingService(aws_client)
            
            # Fetch pricing in parallel
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
            
            # Use thread pool for parallel pricing fetch
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {executor.submit(fetch_price, inst): inst for inst in instances}
                completed = 0
                for future in as_completed(futures):
                    completed += 1
                    if not args.quiet and completed % 10 == 0:
                        print(f"Fetched pricing for {completed}/{len(instances)} instances...", file=sys.stderr)
        
        # Sort instances
        instances = sorted(instances, key=lambda x: x.instance_type)
        
        # Output
        output = formatter.format_instance_list(instances, args.region)
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            if not args.quiet:
                print(f"Output written to {args.output}", file=sys.stderr)
        else:
            print(output)
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc()
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
        output = formatter.format_instance_detail(instance, args.region)
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            if not args.quiet:
                print(f"Output written to {args.output}", file=sys.stderr)
        else:
            print(output)
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


def cmd_search(args) -> int:
    """Search instance types command (alias for list with search)"""
    # This is essentially the same as list with search filter
    return cmd_list(args)


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
        on_demand = pricing_service.get_on_demand_price(
            instance.instance_type,
            args.region,
            max_retries=5
        )
        spot = pricing_service.get_spot_price(instance.instance_type, args.region)
        instance.pricing = PricingInfo(
            on_demand_price=on_demand,
            spot_price=spot
        )
        
        # Output
        output = formatter.format_pricing(instance, args.region)
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            if not args.quiet:
                print(f"Output written to {args.output}", file=sys.stderr)
        else:
            print(output)
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


def cmd_regions(args) -> int:
    """List available regions command"""
    formatter = get_formatter(args.format)
    
    try:
        # Try to get accessible regions
        settings = Settings()
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
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            if not args.quiet:
                print(f"Output written to {args.output}", file=sys.stderr)
        else:
            print(output)
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


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
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            if not args.quiet:
                print(f"Output written to {args.output}", file=sys.stderr)
        else:
            print(output)
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


def cmd_cache_stats(args) -> int:
    """Show cache statistics command"""
    try:
        cache = get_pricing_cache()
        stats = cache.get_stats()

        formatter = get_formatter(args.format)

        # Format output based on format
        if args.format == "json":
            import json
            print(json.dumps(stats, indent=2))
        else:
            # Table format
            print("\nCache Statistics:")
            print(f"  Location: {cache.cache_dir}")
            print(f"  Total entries: {stats['total_entries']}")
            print(f"  Valid entries: {stats['valid_entries']}")
            print(f"  Expired entries: {stats['expired_entries']}")
            print(f"  Cache size: {stats['cache_size_bytes']:,} bytes")
            if stats['oldest_entry']:
                print(f"  Oldest entry: {stats['oldest_entry']}")
            if stats['newest_entry']:
                print(f"  Newest entry: {stats['newest_entry']}")
            print()

        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


def cmd_cache_clear(args) -> int:
    """Clear cache command"""
    try:
        cache = get_pricing_cache()

        # Build filters
        region = args.region if hasattr(args, 'region') else None
        instance_type = args.instance_type if hasattr(args, 'instance_type') else None

        # Confirm if not --force
        if not args.force:
            if region and instance_type:
                confirm_msg = f"Clear cache for {instance_type} in {region}? (y/N): "
            elif region:
                confirm_msg = f"Clear all cache entries for region {region}? (y/N): "
            elif instance_type:
                confirm_msg = f"Clear all cache entries for {instance_type}? (y/N): "
            else:
                confirm_msg = "Clear ALL cache entries? (y/N): "

            response = input(confirm_msg)
            if response.lower() != 'y':
                print("Aborted.", file=sys.stderr)
                return 0

        # Clear cache
        count = cache.clear(region=region, instance_type=instance_type)

        if not args.quiet:
            if region and instance_type:
                print(f"Cleared {count} cache entries for {instance_type} in {region}")
            elif region:
                print(f"Cleared {count} cache entries for region {region}")
            elif instance_type:
                print(f"Cleared {count} cache entries for {instance_type}")
            else:
                print(f"Cleared {count} cache entries")

        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


def cmd_cost_estimate(args) -> int:
    """Cost estimate command"""
    formatter = get_formatter(args.format)
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
        on_demand = pricing_service.get_on_demand_price(args.instance_type, args.region)
        spot = pricing_service.get_spot_price(args.instance_type, args.region)

        instance.pricing = PricingInfo(
            on_demand_price=on_demand,
            spot_price=spot,
            # Savings plans would go here when implemented
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

        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            if not args.quiet:
                print(f"Output written to {args.output}", file=sys.stderr)
        else:
            print(output)

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc()
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

        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            if not args.quiet:
                print(f"Output written to {args.output}", file=sys.stderr)
        else:
            print(output)

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc()
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

            pricing_service = PricingService(aws_client)

            def fetch_price(instance: InstanceType):
                try:
                    on_demand = pricing_service.get_on_demand_price(instance.instance_type, args.region)
                    spot = pricing_service.get_spot_price(instance.instance_type, args.region)
                    instance.pricing = PricingInfo(on_demand_price=on_demand, spot_price=spot)
                except Exception:
                    pass

            with ThreadPoolExecutor(max_workers=5) as executor:
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

        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            if not args.quiet:
                print(f"Output written to {args.output}", file=sys.stderr)
        else:
            print(output)

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


def cmd_presets_list(args) -> int:
    """List filter presets command"""
    try:
        preset_service = FilterPresetService()
        all_presets = preset_service.get_all_presets()

        if args.format == "json":
            import json
            data = {
                name: {
                    "description": preset.description,
                    "min_vcpu": preset.min_vcpu,
                    "max_vcpu": preset.max_vcpu,
                    "min_memory": preset.min_memory,
                    "max_memory": preset.max_memory,
                    "has_gpu": preset.has_gpu,
                    "current_generation_only": preset.current_generation_only,
                    "burstable_only": preset.burstable_only,
                    "free_tier_only": preset.free_tier_only,
                    "architecture": preset.architecture,
                    "instance_families": preset.instance_families
                }
                for name, preset in all_presets.items()
            }
            print(json.dumps(data, indent=2))
        else:
            # Table format
            from tabulate import tabulate
            headers = ["Preset Name", "Description"]
            rows = []
            for name, preset in sorted(all_presets.items()):
                rows.append([name, preset.description or "No description"])

            print("Available Filter Presets:\n")
            print(tabulate(rows, headers=headers, tablefmt="grid"))
            print("\nUse 'instancepedia presets apply <preset_name>' to apply a preset")

        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_presets_apply(args) -> int:
    """Apply a filter preset command"""
    try:
        preset_service = FilterPresetService()
        preset = preset_service.get_preset(args.preset_name)

        if not preset:
            print(f"Error: Preset '{args.preset_name}' not found", file=sys.stderr)
            print(f"Use 'instancepedia presets list' to see available presets", file=sys.stderr)
            return 1

        if not args.quiet:
            print(f"Applying preset: {preset.name}", file=sys.stderr)
            if preset.description:
                print(f"Description: {preset.description}", file=sys.stderr)
            print(f"Fetching instance types for region {args.region}...", file=sys.stderr)

        # Fetch instances
        formatter = get_formatter(args.format)
        aws_client = get_aws_client(args.region, args.profile)
        instance_service = InstanceService(aws_client)
        instances = instance_service.get_instance_types(fetch_pricing=False)

        # Apply preset filters
        filtered_instances = instances

        if preset.min_vcpu is not None:
            filtered_instances = [i for i in filtered_instances if i.vcpu_info.default_vcpus >= preset.min_vcpu]

        if preset.max_vcpu is not None:
            filtered_instances = [i for i in filtered_instances if i.vcpu_info.default_vcpus <= preset.max_vcpu]

        if preset.min_memory is not None:
            filtered_instances = [i for i in filtered_instances if i.memory_info.size_in_gb >= preset.min_memory]

        if preset.max_memory is not None:
            filtered_instances = [i for i in filtered_instances if i.memory_info.size_in_gb <= preset.max_memory]

        if preset.has_gpu is not None:
            if preset.has_gpu:
                filtered_instances = [i for i in filtered_instances if i.gpu_info is not None]
            else:
                filtered_instances = [i for i in filtered_instances if i.gpu_info is None]

        if preset.current_generation_only:
            filtered_instances = [i for i in filtered_instances if i.current_generation]

        if preset.burstable_only:
            filtered_instances = [i for i in filtered_instances if i.burstable_performance_supported]

        if preset.free_tier_only:
            free_tier_service = FreeTierService()
            filtered_instances = [i for i in filtered_instances if free_tier_service.is_eligible(i.instance_type)]

        if preset.architecture:
            filtered_instances = [i for i in filtered_instances if preset.architecture in i.processor_info.supported_architectures]

        if preset.instance_families:
            filtered_instances = [i for i in filtered_instances if any(i.instance_type.startswith(f + '.') for f in preset.instance_families)]

        if not args.quiet:
            print(f"Found {len(filtered_instances)} instances matching preset criteria", file=sys.stderr)

        # Fetch pricing if requested
        if args.include_pricing and filtered_instances:
            if not args.quiet:
                print("Fetching pricing information...", file=sys.stderr)

            pricing_service = PricingService(aws_client)

            def fetch_price(instance: InstanceType):
                try:
                    on_demand = pricing_service.get_on_demand_price(instance.instance_type, args.region)
                    spot = pricing_service.get_spot_price(instance.instance_type, args.region)
                    instance.pricing = PricingInfo(on_demand_price=on_demand, spot_price=spot)
                except Exception:
                    pass

            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {executor.submit(fetch_price, inst): inst for inst in filtered_instances}
                for future in as_completed(futures):
                    pass

        # Sort and output
        filtered_instances = sorted(filtered_instances, key=lambda x: x.instance_type)

        output = formatter.format_instance_list(filtered_instances, args.region)
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            if not args.quiet:
                print(f"Output written to {args.output}", file=sys.stderr)
        else:
            print(output)

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


def run_cli(args) -> int:
    """Run CLI command based on args"""
    if hasattr(args, 'func'):
        return args.func(args)
    else:
        print("Error: No command specified", file=sys.stderr)
        return 1
