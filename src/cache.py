"""Caching system for pricing data"""

import json
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import threading

logger = logging.getLogger("instancepedia")


class PricingCache:
    """
    Cache for EC2 pricing data with TTL support

    Cache entries are stored as JSON files in ~/.instancepedia/cache/
    Each entry includes timestamp, data, and TTL.
    """

    # Default TTL: 4 hours (pricing doesn't change frequently)
    DEFAULT_TTL_SECONDS = 4 * 60 * 60

    def __init__(self, cache_dir: Optional[Path] = None, ttl_seconds: Optional[int] = None):
        """
        Initialize pricing cache

        Args:
            cache_dir: Directory to store cache files (default: ~/.instancepedia/cache)
            ttl_seconds: Default TTL for cache entries in seconds (default: 4 hours)
        """
        self.cache_dir = cache_dir or Path.home() / ".instancepedia" / "cache"
        self.ttl_seconds = ttl_seconds or self.DEFAULT_TTL_SECONDS
        self._lock = threading.Lock()

        # Create cache directory if it doesn't exist
        self._ensure_cache_dir()

    def _ensure_cache_dir(self) -> None:
        """Create cache directory if it doesn't exist"""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Cache directory: {self.cache_dir}")
        except Exception as e:
            logger.warning(f"Failed to create cache directory: {e}")

    def _get_cache_key(self, region: str, instance_type: str, price_type: str) -> str:
        """
        Generate cache key for pricing data

        Args:
            region: AWS region code
            instance_type: EC2 instance type
            price_type: 'on_demand' or 'spot'

        Returns:
            Cache key string
        """
        # Sanitize to create valid filename
        safe_key = f"{region}_{instance_type}_{price_type}".replace(".", "_")
        return safe_key

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get file path for cache entry"""
        return self.cache_dir / f"{cache_key}.json"

    def get(self, region: str, instance_type: str, price_type: str) -> Optional[float]:
        """
        Get cached price if available and not expired

        Args:
            region: AWS region code
            instance_type: EC2 instance type
            price_type: 'on_demand' or 'spot'

        Returns:
            Cached price or None if not available/expired
        """
        cache_key = self._get_cache_key(region, instance_type, price_type)
        cache_path = self._get_cache_path(cache_key)

        if not cache_path.exists():
            logger.debug(f"Cache miss: {cache_key}")
            return None

        try:
            with self._lock:
                with open(cache_path, 'r') as f:
                    entry = json.load(f)

                # Check if entry is expired
                timestamp = entry.get('timestamp', 0)
                ttl = entry.get('ttl', self.ttl_seconds)
                age = time.time() - timestamp

                if age > ttl:
                    logger.debug(f"Cache expired: {cache_key} (age: {age:.0f}s, ttl: {ttl}s)")
                    # Remove expired entry
                    cache_path.unlink()
                    return None

                price = entry.get('price')
                logger.debug(f"Cache hit: {cache_key} (age: {age:.0f}s)")
                return price

        except Exception as e:
            logger.warning(f"Failed to read cache entry {cache_key}: {e}")
            # Clean up corrupted cache file
            try:
                cache_path.unlink()
            except Exception:
                pass
            return None

    def set(self, region: str, instance_type: str, price_type: str, price: Optional[float]) -> None:
        """
        Store price in cache

        Args:
            region: AWS region code
            instance_type: EC2 instance type
            price_type: 'on_demand' or 'spot'
            price: Price value (None for unavailable)
        """
        cache_key = self._get_cache_key(region, instance_type, price_type)
        cache_path = self._get_cache_path(cache_key)

        entry = {
            'timestamp': time.time(),
            'ttl': self.ttl_seconds,
            'region': region,
            'instance_type': instance_type,
            'price_type': price_type,
            'price': price
        }

        try:
            with self._lock:
                with open(cache_path, 'w') as f:
                    json.dump(entry, f, indent=2)
            logger.debug(f"Cached: {cache_key} = {price}")
        except Exception as e:
            logger.warning(f"Failed to write cache entry {cache_key}: {e}")

    def clear(self, region: Optional[str] = None, instance_type: Optional[str] = None) -> int:
        """
        Clear cache entries

        Args:
            region: If specified, only clear entries for this region
            instance_type: If specified, only clear entries for this instance type

        Returns:
            Number of entries cleared
        """
        count = 0

        try:
            with self._lock:
                for cache_file in self.cache_dir.glob("*.json"):
                    try:
                        # Read entry to check filters
                        with open(cache_file, 'r') as f:
                            entry = json.load(f)

                        # Apply filters
                        if region and entry.get('region') != region:
                            continue
                        if instance_type and entry.get('instance_type') != instance_type:
                            continue

                        # Delete matching entry
                        cache_file.unlink()
                        count += 1
                    except Exception as e:
                        logger.warning(f"Failed to clear cache file {cache_file}: {e}")

            logger.info(f"Cleared {count} cache entries")
            return count

        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return count

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Dictionary with cache stats
        """
        stats = {
            'total_entries': 0,
            'expired_entries': 0,
            'valid_entries': 0,
            'cache_size_bytes': 0,
            'oldest_entry': None,
            'newest_entry': None
        }

        try:
            current_time = time.time()
            oldest_timestamp = None
            newest_timestamp = None

            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    stats['total_entries'] += 1
                    stats['cache_size_bytes'] += cache_file.stat().st_size

                    with open(cache_file, 'r') as f:
                        entry = json.load(f)

                    timestamp = entry.get('timestamp', 0)
                    ttl = entry.get('ttl', self.ttl_seconds)
                    age = current_time - timestamp

                    if age > ttl:
                        stats['expired_entries'] += 1
                    else:
                        stats['valid_entries'] += 1

                    if oldest_timestamp is None or timestamp < oldest_timestamp:
                        oldest_timestamp = timestamp
                    if newest_timestamp is None or timestamp > newest_timestamp:
                        newest_timestamp = timestamp

                except Exception as e:
                    logger.warning(f"Failed to read cache file {cache_file} for stats: {e}")

            if oldest_timestamp:
                stats['oldest_entry'] = datetime.fromtimestamp(oldest_timestamp).isoformat()
            if newest_timestamp:
                stats['newest_entry'] = datetime.fromtimestamp(newest_timestamp).isoformat()

        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")

        return stats


# Global cache instance
_pricing_cache: Optional[PricingCache] = None


def get_pricing_cache() -> PricingCache:
    """Get global pricing cache instance"""
    global _pricing_cache
    if _pricing_cache is None:
        _pricing_cache = PricingCache()
    return _pricing_cache
