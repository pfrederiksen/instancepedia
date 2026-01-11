"""Cache management CLI commands"""

import logging

from src.cache import get_pricing_cache
from src.cli.output import get_formatter

from .base import status, print_error, write_output

logger = logging.getLogger("instancepedia")


def cmd_cache_stats(args) -> int:
    """Show cache statistics command"""
    try:
        cache = get_pricing_cache()
        stats = cache.get_stats()

        # Format and write output
        formatter = get_formatter(args.format)
        output = formatter.format_cache_stats(stats, cache.cache_dir)
        write_output(output, args.output, quiet=args.quiet)

        return 0
    except Exception as e:
        print_error(str(e), debug=args.debug, exception=e)
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
                status("Aborted.")
                return 0

        # Clear cache
        count = cache.clear(region=region, instance_type=instance_type)

        # Log the cache clear action for audit trail
        if region and instance_type:
            logger.info(f"Cache cleared: {count} entries for {instance_type} in {region}")
        elif region:
            logger.info(f"Cache cleared: {count} entries for region {region}")
        elif instance_type:
            logger.info(f"Cache cleared: {count} entries for {instance_type}")
        else:
            logger.info(f"Cache cleared: {count} entries (all)")

        if region and instance_type:
            status(f"Cleared {count} cache entries for {instance_type} in {region}", quiet=args.quiet)
        elif region:
            status(f"Cleared {count} cache entries for region {region}", quiet=args.quiet)
        elif instance_type:
            status(f"Cleared {count} cache entries for {instance_type}", quiet=args.quiet)
        else:
            status(f"Cleared {count} cache entries", quiet=args.quiet)

        return 0
    except Exception as e:
        print_error(str(e), debug=args.debug, exception=e)
        return 1
