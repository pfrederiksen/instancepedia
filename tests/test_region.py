"""Tests for region module"""

import pytest
from src.models.region import AWS_REGIONS, get_region_list, is_valid_region


class TestAWSRegions:
    """Tests for AWS_REGIONS constant"""

    def test_aws_regions_exists(self):
        """Test that AWS_REGIONS is defined and not empty"""
        assert AWS_REGIONS is not None
        assert len(AWS_REGIONS) > 0

    def test_aws_regions_structure(self):
        """Test that AWS_REGIONS has correct structure"""
        # All keys should be region codes (strings)
        for region_code, location_name in AWS_REGIONS.items():
            assert isinstance(region_code, str)
            assert isinstance(location_name, str)
            # Region codes should follow AWS pattern
            assert '-' in region_code
            # Location names should be descriptive
            assert len(location_name) > 0

    def test_common_regions_present(self):
        """Test that common AWS regions are present"""
        expected_regions = [
            'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
            'eu-west-1', 'eu-central-1',
            'ap-southeast-1', 'ap-northeast-1',
            'ca-central-1', 'sa-east-1'
        ]

        for region in expected_regions:
            assert region in AWS_REGIONS, f"Major region {region} not in AWS_REGIONS"


class TestGetRegionList:
    """Tests for get_region_list() function"""

    def test_get_region_list_returns_list(self):
        """Test that get_region_list returns a list"""
        result = get_region_list()
        assert isinstance(result, list)

    def test_get_region_list_not_empty(self):
        """Test that get_region_list returns non-empty list"""
        result = get_region_list()
        assert len(result) > 0

    def test_get_region_list_tuple_structure(self):
        """Test that each element is a tuple with correct structure"""
        result = get_region_list()
        for item in result:
            assert isinstance(item, tuple)
            assert len(item) == 2
            code, display_name = item
            assert isinstance(code, str)
            assert isinstance(display_name, str)

    def test_get_region_list_display_format(self):
        """Test that display names have correct format"""
        result = get_region_list()
        for code, display_name in result:
            # Display name should be: "code (name)"
            assert display_name.startswith(code)
            assert ' (' in display_name
            assert ')' in display_name

    def test_get_region_list_contains_all_regions(self):
        """Test that get_region_list contains all AWS_REGIONS"""
        result = get_region_list()
        result_codes = {code for code, _ in result}

        for region_code in AWS_REGIONS.keys():
            assert region_code in result_codes

    def test_get_region_list_sample_values(self):
        """Test specific region list values"""
        result = get_region_list()
        result_dict = dict(result)

        # Test specific regions
        assert result_dict['us-east-1'] == 'us-east-1 (N. Virginia)'
        assert result_dict['eu-west-1'] == 'eu-west-1 (Ireland)'
        assert result_dict['ap-northeast-1'] == 'ap-northeast-1 (Tokyo)'


class TestIsValidRegion:
    """Tests for is_valid_region() function"""

    def test_is_valid_region_with_valid_regions(self):
        """Test is_valid_region with valid region codes"""
        assert is_valid_region('us-east-1') is True
        assert is_valid_region('us-west-2') is True
        assert is_valid_region('eu-west-1') is True
        assert is_valid_region('ap-southeast-1') is True

    def test_is_valid_region_with_invalid_regions(self):
        """Test is_valid_region with invalid region codes"""
        assert is_valid_region('invalid-region') is False
        assert is_valid_region('us-east-99') is False
        assert is_valid_region('unknown-1') is False

    def test_is_valid_region_with_empty_string(self):
        """Test is_valid_region with empty string (edge case)"""
        assert is_valid_region('') is False

    def test_is_valid_region_with_none_like_strings(self):
        """Test is_valid_region with None-like strings (edge case)"""
        assert is_valid_region('None') is False
        assert is_valid_region('null') is False

    def test_is_valid_region_case_sensitivity(self):
        """Test that is_valid_region is case-sensitive"""
        # Valid lowercase
        assert is_valid_region('us-east-1') is True
        # Invalid uppercase
        assert is_valid_region('US-EAST-1') is False
        assert is_valid_region('Us-East-1') is False

    def test_is_valid_region_with_whitespace(self):
        """Test is_valid_region with whitespace (edge case)"""
        assert is_valid_region(' us-east-1') is False
        assert is_valid_region('us-east-1 ') is False
        assert is_valid_region(' us-east-1 ') is False
        assert is_valid_region('   ') is False

    def test_is_valid_region_with_partial_matches(self):
        """Test is_valid_region doesn't accept partial matches"""
        assert is_valid_region('us-east') is False
        assert is_valid_region('east-1') is False
        assert is_valid_region('us') is False

    def test_is_valid_region_with_special_characters(self):
        """Test is_valid_region with special characters (edge case)"""
        assert is_valid_region('us-east-1!') is False
        assert is_valid_region('us@east-1') is False
        assert is_valid_region('us-east-1\n') is False
        assert is_valid_region('us-east-1\t') is False

    def test_is_valid_region_all_aws_regions_are_valid(self):
        """Test that all regions in AWS_REGIONS are considered valid"""
        for region_code in AWS_REGIONS.keys():
            assert is_valid_region(region_code) is True, \
                f"Region {region_code} from AWS_REGIONS should be valid"


class TestRegionConsistency:
    """Tests for consistency between region utilities"""

    def test_region_list_and_validation_consistent(self):
        """Test that get_region_list and is_valid_region are consistent"""
        region_list = get_region_list()

        for code, _ in region_list:
            # Every region in the list should be valid
            assert is_valid_region(code) is True

    def test_aws_regions_and_validation_consistent(self):
        """Test that AWS_REGIONS and is_valid_region are consistent"""
        for region_code in AWS_REGIONS.keys():
            # Every region in AWS_REGIONS should be valid
            assert is_valid_region(region_code) is True
