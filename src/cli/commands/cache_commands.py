"""Cache management CLI commands"""

import logging
import sys

from src.cache import get_pricing_cache
from src.cli.output import get_formatter

from .base import print_error

logger = logging.getLogger("instancepedia")


def cmd_cache_stats(args) -> int:
    """Show cache statistics command"""
    try:
        cache = get_pricing_cache()
        stats = cache.get_stats()

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
                print("Aborted.", file=sys.stderr)
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
        print_error(str(e), debug=args.debug, exception=e)
        return 1
