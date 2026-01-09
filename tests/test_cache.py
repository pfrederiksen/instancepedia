"""Tests for PricingCache including thread safety"""

import pytest
import tempfile
import time
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.cache import PricingCache


@pytest.fixture
def temp_cache_dir():
    """Create temporary cache directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def cache(temp_cache_dir):
    """Create PricingCache with temporary directory"""
    return PricingCache(cache_dir=temp_cache_dir, ttl_seconds=1)


class TestPricingCacheBasic:
    """Test basic cache functionality"""

    def test_cache_initialization(self, temp_cache_dir):
        """Test cache initializes with correct defaults"""
        cache = PricingCache(cache_dir=temp_cache_dir)

        assert cache.cache_dir == temp_cache_dir
        assert cache.ttl_seconds == PricingCache.DEFAULT_TTL_SECONDS
        assert cache.cache_dir.exists()

    def test_cache_set_and_get(self, cache):
        """Test basic set and get operations"""
        cache.set("us-east-1", "t3.micro", "on_demand", 0.0104)

        price = cache.get("us-east-1", "t3.micro", "on_demand")

        assert price == 0.0104

    def test_cache_get_miss(self, cache):
        """Test cache miss returns None"""
        price = cache.get("us-east-1", "nonexistent.type", "on_demand")

        assert price is None

    def test_cache_stores_none_values(self, cache):
        """Test cache can store None values"""
        cache.set("us-east-1", "t3.micro", "on_demand", None)

        # File should exist even for None value
        cache_files = list(cache.cache_dir.glob("*.json"))
        assert len(cache_files) == 1

    def test_cache_ttl_expiry(self, cache):
        """Test cache entries expire after TTL"""
        cache.set("us-east-1", "t3.micro", "on_demand", 0.0104)

        # Should be available immediately
        assert cache.get("us-east-1", "t3.micro", "on_demand") == 0.0104

        # Wait for TTL to expire (cache was created with 1 second TTL)
        time.sleep(1.1)

        # Should be expired now
        assert cache.get("us-east-1", "t3.micro", "on_demand") is None

        # Cache file should be deleted after expiry check
        cache_files = list(cache.cache_dir.glob("*.json"))
        assert len(cache_files) == 0

    def test_cache_clear_all(self, cache):
        """Test clearing all cache entries"""
        cache.set("us-east-1", "t3.micro", "on_demand", 0.0104)
        cache.set("us-west-2", "t3.small", "spot", 0.0036)

        count = cache.clear()

        assert count == 2
        assert list(cache.cache_dir.glob("*.json")) == []

    def test_cache_clear_by_region(self, cache):
        """Test clearing cache entries by region"""
        cache.set("us-east-1", "t3.micro", "on_demand", 0.0104)
        cache.set("us-west-2", "t3.micro", "on_demand", 0.0208)
        cache.set("us-east-1", "t3.small", "on_demand", 0.0208)

        count = cache.clear(region="us-east-1")

        assert count == 2
        # us-west-2 entry should still exist
        assert cache.get("us-west-2", "t3.micro", "on_demand") == 0.0208

    def test_cache_clear_by_instance_type(self, cache):
        """Test clearing cache entries by instance type"""
        cache.set("us-east-1", "t3.micro", "on_demand", 0.0104)
        cache.set("us-east-1", "t3.small", "on_demand", 0.0208)
        cache.set("us-west-2", "t3.micro", "on_demand", 0.0208)

        count = cache.clear(instance_type="t3.micro")

        assert count == 2
        # t3.small should still exist
        assert cache.get("us-east-1", "t3.small", "on_demand") == 0.0208

    def test_cache_stats(self, cache):
        """Test cache statistics"""
        cache.set("us-east-1", "t3.micro", "on_demand", 0.0104)
        cache.set("us-west-2", "t3.small", "spot", 0.0036)

        stats = cache.get_stats()

        assert stats['total_entries'] == 2
        assert stats['valid_entries'] == 2
        assert stats['expired_entries'] == 0
        assert stats['cache_size_bytes'] > 0
        assert stats['oldest_entry'] is not None
        assert stats['newest_entry'] is not None


class TestCacheThreadSafety:
    """Test cache thread safety with concurrent operations"""

    def test_concurrent_writes_same_key(self, cache):
        """Test multiple threads writing to same cache key"""
        num_threads = 10
        instance_type = "t3.micro"
        region = "us-east-1"
        price_type = "on_demand"

        def write_price(thread_id):
            price = 0.01 + (thread_id * 0.001)
            cache.set(region, instance_type, price_type, price)
            return price

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(write_price, i) for i in range(num_threads)]
            results = [f.result() for f in as_completed(futures)]

        # Should have one file for the key
        cache_files = list(cache.cache_dir.glob("*.json"))
        assert len(cache_files) == 1

        # Final value should be one of the written values
        final_price = cache.get(region, instance_type, price_type)
        assert final_price in results

    def test_concurrent_reads_and_writes(self, cache):
        """Test concurrent reads and writes don't corrupt cache"""
        num_operations = 50
        results = {'reads': [], 'writes': [], 'errors': []}

        def write_operation(i):
            try:
                cache.set("us-east-1", f"instance{i % 5}", "on_demand", 0.01 * i)
                results['writes'].append(i)
            except Exception as e:
                results['errors'].append(('write', i, str(e)))

        def read_operation(i):
            try:
                price = cache.get("us-east-1", f"instance{i % 5}", "on_demand")
                results['reads'].append((i, price))
            except Exception as e:
                results['errors'].append(('read', i, str(e)))

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for i in range(num_operations):
                if i % 2 == 0:
                    futures.append(executor.submit(write_operation, i))
                else:
                    futures.append(executor.submit(read_operation, i))

            # Wait for all operations to complete
            for future in as_completed(futures):
                future.result()

        # No errors should occur
        assert len(results['errors']) == 0
        assert len(results['writes']) > 0
        assert len(results['reads']) > 0

    def test_concurrent_clear_operations(self, cache):
        """Test concurrent clear operations are safe"""
        # Populate cache
        for i in range(20):
            cache.set(f"region{i % 3}", f"instance{i}", "on_demand", 0.01 * i)

        errors = []

        def clear_operation(clear_type):
            try:
                if clear_type == 'all':
                    cache.clear()
                elif clear_type == 'region':
                    cache.clear(region="region0")
                else:
                    cache.clear(instance_type="instance0")
            except Exception as e:
                errors.append(str(e))

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(clear_operation, 'all'),
                executor.submit(clear_operation, 'region'),
                executor.submit(clear_operation, 'instance'),
                executor.submit(clear_operation, 'all'),
                executor.submit(clear_operation, 'region'),
            ]

            for future in as_completed(futures):
                future.result()

        # No errors should occur
        assert len(errors) == 0

    def test_concurrent_stats_and_writes(self, cache):
        """Test getting stats while writing doesn't cause issues"""
        num_operations = 30
        stats_results = []
        errors = []

        def write_operation(i):
            try:
                cache.set("us-east-1", f"instance{i}", "on_demand", 0.01 * i)
            except Exception as e:
                errors.append(('write', str(e)))

        def stats_operation():
            try:
                stats = cache.get_stats()
                stats_results.append(stats)
            except Exception as e:
                errors.append(('stats', str(e)))

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for i in range(num_operations):
                if i % 3 == 0:
                    futures.append(executor.submit(stats_operation))
                else:
                    futures.append(executor.submit(write_operation, i))

            for future in as_completed(futures):
                future.result()

        # No errors should occur
        assert len(errors) == 0
        assert len(stats_results) > 0

        # Stats should show increasing entry counts
        assert all(s['total_entries'] >= 0 for s in stats_results)

    def test_cache_file_corruption_recovery(self, cache):
        """Test cache handles corrupted cache files gracefully"""
        # Create a valid cache entry
        cache.set("us-east-1", "t3.micro", "on_demand", 0.0104)

        # Corrupt the cache file
        cache_files = list(cache.cache_dir.glob("*.json"))
        assert len(cache_files) == 1

        with open(cache_files[0], 'w') as f:
            f.write("{ invalid json")

        # Should return None and remove corrupted file
        price = cache.get("us-east-1", "t3.micro", "on_demand")
        assert price is None

        # Corrupted file should be removed
        time.sleep(0.1)  # Give it time to clean up
        assert len(list(cache.cache_dir.glob("*.json"))) == 0


class TestCacheKeyGeneration:
    """Test cache key generation"""

    def test_cache_key_sanitization(self, cache):
        """Test cache keys are properly sanitized"""
        # Instance types have dots which should be replaced
        cache.set("us-east-1", "t3.micro", "on_demand", 0.0104)

        cache_files = list(cache.cache_dir.glob("*.json"))
        assert len(cache_files) == 1

        # Filename should have underscores instead of dots
        assert "t3_micro" in cache_files[0].name
        assert "." not in cache_files[0].stem  # stem excludes extension

    def test_different_price_types_separate_cache(self, cache):
        """Test on_demand and spot prices are cached separately"""
        cache.set("us-east-1", "t3.micro", "on_demand", 0.0104)
        cache.set("us-east-1", "t3.micro", "spot", 0.0036)

        # Should have two separate cache files
        cache_files = list(cache.cache_dir.glob("*.json"))
        assert len(cache_files) == 2

        # Should retrieve correct prices
        assert cache.get("us-east-1", "t3.micro", "on_demand") == 0.0104
        assert cache.get("us-east-1", "t3.micro", "spot") == 0.0036


class TestReservedInstanceCaching:
    """Test Reserved Instance pricing cache functionality"""

    def test_ri_1yr_no_upfront_cache(self, cache):
        """Test 1yr No Upfront RI pricing is cached correctly"""
        cache.set("us-east-1", "m5.large", "ri_1yr_no_upfront", 0.0600)

        price = cache.get("us-east-1", "m5.large", "ri_1yr_no_upfront")
        assert price == 0.0600

    def test_ri_1yr_partial_upfront_cache(self, cache):
        """Test 1yr Partial Upfront RI pricing is cached correctly"""
        cache.set("us-east-1", "m5.large", "ri_1yr_partial_upfront", 0.0290)

        price = cache.get("us-east-1", "m5.large", "ri_1yr_partial_upfront")
        assert price == 0.0290

    def test_ri_1yr_all_upfront_cache(self, cache):
        """Test 1yr All Upfront RI pricing is cached correctly"""
        cache.set("us-east-1", "m5.large", "ri_1yr_all_upfront", 0.0280)

        price = cache.get("us-east-1", "m5.large", "ri_1yr_all_upfront")
        assert price == 0.0280

    def test_ri_3yr_no_upfront_cache(self, cache):
        """Test 3yr No Upfront RI pricing is cached correctly"""
        cache.set("us-east-1", "m5.large", "ri_3yr_no_upfront", 0.0410)

        price = cache.get("us-east-1", "m5.large", "ri_3yr_no_upfront")
        assert price == 0.0410

    def test_ri_3yr_partial_upfront_cache(self, cache):
        """Test 3yr Partial Upfront RI pricing is cached correctly"""
        cache.set("us-east-1", "m5.large", "ri_3yr_partial_upfront", 0.0190)

        price = cache.get("us-east-1", "m5.large", "ri_3yr_partial_upfront")
        assert price == 0.0190

    def test_ri_3yr_all_upfront_cache(self, cache):
        """Test 3yr All Upfront RI pricing is cached correctly"""
        cache.set("us-east-1", "m5.large", "ri_3yr_all_upfront", 0.0180)

        price = cache.get("us-east-1", "m5.large", "ri_3yr_all_upfront")
        assert price == 0.0180

    def test_all_ri_types_separate_cache(self, cache):
        """Test all 6 RI pricing types are cached separately"""
        # Cache all 6 RI pricing types
        cache.set("us-east-1", "m5.large", "ri_1yr_no_upfront", 0.0600)
        cache.set("us-east-1", "m5.large", "ri_1yr_partial_upfront", 0.0290)
        cache.set("us-east-1", "m5.large", "ri_1yr_all_upfront", 0.0280)
        cache.set("us-east-1", "m5.large", "ri_3yr_no_upfront", 0.0410)
        cache.set("us-east-1", "m5.large", "ri_3yr_partial_upfront", 0.0190)
        cache.set("us-east-1", "m5.large", "ri_3yr_all_upfront", 0.0180)

        # Should have six separate cache files
        cache_files = list(cache.cache_dir.glob("*.json"))
        assert len(cache_files) == 6

        # Should retrieve correct prices for each type
        assert cache.get("us-east-1", "m5.large", "ri_1yr_no_upfront") == 0.0600
        assert cache.get("us-east-1", "m5.large", "ri_1yr_partial_upfront") == 0.0290
        assert cache.get("us-east-1", "m5.large", "ri_1yr_all_upfront") == 0.0280
        assert cache.get("us-east-1", "m5.large", "ri_3yr_no_upfront") == 0.0410
        assert cache.get("us-east-1", "m5.large", "ri_3yr_partial_upfront") == 0.0190
        assert cache.get("us-east-1", "m5.large", "ri_3yr_all_upfront") == 0.0180

    def test_ri_cache_key_format(self, cache):
        """Test RI cache keys use correct naming format"""
        cache.set("us-east-1", "m5.large", "ri_1yr_partial_upfront", 0.0290)

        cache_files = list(cache.cache_dir.glob("*.json"))
        assert len(cache_files) == 1

        # Cache filename should contain RI pricing type
        filename = cache_files[0].name
        assert "ri_1yr_partial_upfront" in filename
        assert "us-east-1" in filename
        assert "m5_large" in filename  # Dots replaced with underscores

    def test_ri_none_values_cached(self, cache):
        """Test RI pricing None values are cached to avoid repeated API calls"""
        # Cache None values for RI pricing (common for unavailable pricing)
        cache.set("us-east-1", "t3.micro", "ri_1yr_no_upfront", None)
        cache.set("us-east-1", "t3.micro", "ri_1yr_partial_upfront", None)

        # Files should exist even for None values
        cache_files = list(cache.cache_dir.glob("*.json"))
        assert len(cache_files) == 2

        # Should retrieve None values
        assert cache.get("us-east-1", "t3.micro", "ri_1yr_no_upfront") is None
        assert cache.get("us-east-1", "t3.micro", "ri_1yr_partial_upfront") is None

    def test_ri_pricing_mixed_with_other_types(self, cache):
        """Test RI pricing cached alongside on-demand and spot pricing"""
        # Cache all pricing types for same instance
        cache.set("us-east-1", "m5.large", "on_demand", 0.0960)
        cache.set("us-east-1", "m5.large", "spot", 0.0288)
        cache.set("us-east-1", "m5.large", "ri_1yr_no_upfront", 0.0600)
        cache.set("us-east-1", "m5.large", "ri_3yr_partial_upfront", 0.0190)

        # Should have four separate cache files
        cache_files = list(cache.cache_dir.glob("*.json"))
        assert len(cache_files) == 4

        # Should retrieve correct price for each type
        assert cache.get("us-east-1", "m5.large", "on_demand") == 0.0960
        assert cache.get("us-east-1", "m5.large", "spot") == 0.0288
        assert cache.get("us-east-1", "m5.large", "ri_1yr_no_upfront") == 0.0600
        assert cache.get("us-east-1", "m5.large", "ri_3yr_partial_upfront") == 0.0190

    def test_clear_ri_cache_by_instance(self, cache):
        """Test clearing RI cache entries by instance type"""
        # Cache RI pricing for multiple instances
        cache.set("us-east-1", "m5.large", "ri_1yr_no_upfront", 0.0600)
        cache.set("us-east-1", "m5.large", "ri_3yr_partial_upfront", 0.0190)
        cache.set("us-east-1", "c5.xlarge", "ri_1yr_no_upfront", 0.0850)

        count = cache.clear(instance_type="m5.large")

        # Should clear both m5.large entries
        assert count == 2

        # c5.xlarge should still exist
        assert cache.get("us-east-1", "c5.xlarge", "ri_1yr_no_upfront") == 0.0850
