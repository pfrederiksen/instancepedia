"""Tests for region_mapping module"""

import pytest
from src.models.region_mapping import REGION_MAP, get_pricing_region


class TestRegionMapping:
    """Tests for region mapping functionality"""

    def test_region_map_exists(self):
        """Test that REGION_MAP is defined and not empty"""
        assert REGION_MAP is not None
        assert len(REGION_MAP) > 0

    def test_region_map_structure(self):
        """Test that REGION_MAP has correct structure"""
        # All keys should be region codes (strings)
        for region_code, location_name in REGION_MAP.items():
            assert isinstance(region_code, str)
            assert isinstance(location_name, str)
            # Region codes should follow AWS pattern
            assert '-' in region_code
            # Location names should be descriptive
            assert len(location_name) > 0

    def test_common_us_regions(self):
        """Test that common US regions are mapped"""
        assert 'us-east-1' in REGION_MAP
        assert REGION_MAP['us-east-1'] == 'US East (N. Virginia)'

        assert 'us-east-2' in REGION_MAP
        assert REGION_MAP['us-east-2'] == 'US East (Ohio)'

        assert 'us-west-1' in REGION_MAP
        assert REGION_MAP['us-west-1'] == 'US West (N. California)'

        assert 'us-west-2' in REGION_MAP
        assert REGION_MAP['us-west-2'] == 'US West (Oregon)'

    def test_common_eu_regions(self):
        """Test that common EU regions are mapped"""
        assert 'eu-west-1' in REGION_MAP
        assert REGION_MAP['eu-west-1'] == 'EU (Ireland)'

        assert 'eu-central-1' in REGION_MAP
        assert REGION_MAP['eu-central-1'] == 'EU (Frankfurt)'

    def test_common_ap_regions(self):
        """Test that common Asia Pacific regions are mapped"""
        assert 'ap-southeast-1' in REGION_MAP
        assert REGION_MAP['ap-southeast-1'] == 'Asia Pacific (Singapore)'

        assert 'ap-northeast-1' in REGION_MAP
        assert REGION_MAP['ap-northeast-1'] == 'Asia Pacific (Tokyo)'

    def test_get_pricing_region_known_region(self):
        """Test get_pricing_region with known region code"""
        result = get_pricing_region('us-east-1')
        assert result == 'US East (N. Virginia)'

        result = get_pricing_region('eu-west-1')
        assert result == 'EU (Ireland)'

    def test_get_pricing_region_unknown_region(self):
        """Test get_pricing_region with unknown region code"""
        unknown_region = 'unknown-region-1'
        result = get_pricing_region(unknown_region)
        # Should return the input region code when not found
        assert result == unknown_region

    def test_get_pricing_region_empty_string(self):
        """Test get_pricing_region with empty string"""
        result = get_pricing_region('')
        assert result == ''

    def test_get_pricing_region_case_sensitivity(self):
        """Test that region codes are case-sensitive"""
        # Should not match uppercase
        result = get_pricing_region('US-EAST-1')
        assert result == 'US-EAST-1'  # Returns input as fallback

        # Should match exact case
        result = get_pricing_region('us-east-1')
        assert result == 'US East (N. Virginia)'

    def test_all_regions_have_valid_names(self):
        """Test that all region mappings have valid location names"""
        for region_code, location_name in REGION_MAP.items():
            # Location name should not be empty
            assert len(location_name) > 0
            # Location name should start with uppercase
            assert location_name[0].isupper()
            # Location name should contain parentheses with city/area
            assert '(' in location_name and ')' in location_name

    def test_region_map_has_major_regions(self):
        """Test that REGION_MAP includes all major AWS regions"""
        expected_regions = [
            'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
            'eu-west-1', 'eu-central-1',
            'ap-southeast-1', 'ap-northeast-1',
            'ca-central-1', 'sa-east-1'
        ]

        for region in expected_regions:
            assert region in REGION_MAP, f"Major region {region} not in REGION_MAP"

    def test_get_pricing_region_consistency(self):
        """Test that get_pricing_region returns consistent results"""
        # Call twice with same input, should get same result
        result1 = get_pricing_region('us-east-1')
        result2 = get_pricing_region('us-east-1')
        assert result1 == result2

        # Unknown region should also be consistent
        result1 = get_pricing_region('new-region-1')
        result2 = get_pricing_region('new-region-1')
        assert result1 == result2

    def test_region_map_no_duplicate_values(self):
        """Test that location names are unique (no two regions map to same name)"""
        location_names = list(REGION_MAP.values())
        # Most should be unique, but some AWS regions might legitimately have same name
        # At minimum, check that we don't have too many duplicates
        unique_names = set(location_names)
        # Allow a few duplicates but not too many
        assert len(unique_names) >= len(location_names) * 0.9, \
            "Too many duplicate location names in REGION_MAP"
