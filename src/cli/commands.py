"""CLI command handlers"""

import sys
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.services.aws_client import AWSClient
from src.services.instance_service import InstanceService
from src.services.pricing_service import PricingService
from src.services.free_tier_service import FreeTierService
from src.models.instance_type import InstanceType, PricingInfo
from src.cli.output import get_formatter
from src.config.settings import Settings


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


def run_cli(args) -> int:
    """Run CLI command based on args"""
    if hasattr(args, 'func'):
        return args.func(args)
    else:
        print("Error: No command specified", file=sys.stderr)
        return 1
