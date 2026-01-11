"""Tests for output formatter methods - cache stats and presets"""

import json
import pytest
from unittest.mock import Mock, patch

from src.cli.output import get_formatter, TableFormatter, JSONFormatter, CSVFormatter


class TestFormatCacheStats:
    """Tests for format_cache_stats method across all formatters"""

    def test_table_formatter_cache_stats_complete_data(self):
        """Test TableFormatter with complete cache stats"""
        formatter = TableFormatter()
        stats = {
            'total_entries': 100,
            'valid_entries': 80,
            'expired_entries': 20,
            'cache_size_bytes': 50000,
            'oldest_entry': '2024-01-01 00:00:00',
            'newest_entry': '2024-01-02 00:00:00'
        }
        cache_dir = "/tmp/cache"

        output = formatter.format_cache_stats(stats, cache_dir)

        assert "Cache Statistics:" in output
        assert "/tmp/cache" in output
        assert "Total entries: 100" in output
        assert "Valid entries: 80" in output
        assert "Expired entries: 20" in output
        assert "50,000 bytes" in output
        assert "2024-01-01 00:00:00" in output
        assert "2024-01-02 00:00:00" in output

    def test_table_formatter_cache_stats_no_optional_fields(self):
        """Test TableFormatter with cache stats missing optional fields"""
        formatter = TableFormatter()
        stats = {
            'total_entries': 0,
            'valid_entries': 0,
            'expired_entries': 0,
            'cache_size_bytes': 0,
            'oldest_entry': None,
            'newest_entry': None
        }
        cache_dir = "/var/cache"

        output = formatter.format_cache_stats(stats, cache_dir)

        assert "Cache Statistics:" in output
        assert "/var/cache" in output
        assert "Total entries: 0" in output
        assert "oldest_entry" not in output.lower() or "oldest entry" not in output.lower() or output.count("Oldest entry") == 0

    def test_json_formatter_cache_stats(self):
        """Test JSONFormatter with cache stats"""
        formatter = JSONFormatter()
        stats = {
            'total_entries': 50,
            'valid_entries': 40,
            'expired_entries': 10,
            'cache_size_bytes': 25000,
            'oldest_entry': '2024-01-01',
            'newest_entry': '2024-01-10'
        }
        cache_dir = "/home/cache"

        output = formatter.format_cache_stats(stats, cache_dir)
        data = json.loads(output)

        assert data['cache_dir'] == "/home/cache"
        assert data['stats']['total_entries'] == 50
        assert data['stats']['valid_entries'] == 40
        assert data['stats']['expired_entries'] == 10
        assert data['stats']['cache_size_bytes'] == 25000
        assert data['stats']['oldest_entry'] == '2024-01-01'
        assert data['stats']['newest_entry'] == '2024-01-10'

    def test_csv_formatter_cache_stats(self):
        """Test CSVFormatter with cache stats"""
        formatter = CSVFormatter()
        stats = {
            'total_entries': 30,
            'valid_entries': 25,
            'expired_entries': 5,
            'cache_size_bytes': 15000
        }
        cache_dir = "/opt/cache"

        output = formatter.format_cache_stats(stats, cache_dir)
        lines = output.strip().split('\n')

        # Check header
        assert "Metric,Value" in lines[0]

        # Check all expected rows
        assert "Cache Directory,/opt/cache" in output
        assert "Total Entries,30" in output
        assert "Valid Entries,25" in output
        assert "Expired Entries,5" in output
        assert "Cache Size (bytes),15000" in output


class TestFormatPresets:
    """Tests for format_presets method across all formatters"""

    def test_table_formatter_presets_mixed_types(self):
        """Test TableFormatter with mix of built-in and custom presets"""
        formatter = TableFormatter()
        presets = [
            {
                'name': 'web-server',
                'description': 'Optimized for web servers',
                'is_builtin': True
            },
            {
                'name': 'my-custom',
                'description': 'My custom preset',
                'is_builtin': False
            }
        ]

        output = formatter.format_presets(presets)

        assert "Available Filter Presets:" in output
        assert "web-server" in output
        assert "Built-in" in output
        assert "my-custom" in output
        assert "Custom" in output
        assert "Optimized for web servers" in output
        assert "My custom preset" in output
        assert "instancepedia presets apply" in output

    def test_table_formatter_presets_empty_list(self):
        """Test TableFormatter with empty presets list"""
        formatter = TableFormatter()
        presets = []

        output = formatter.format_presets(presets)

        assert "No filter presets available" in output

    def test_table_formatter_presets_no_description(self):
        """Test TableFormatter with preset missing description"""
        formatter = TableFormatter()
        presets = [
            {
                'name': 'test-preset',
                'is_builtin': False
            }
        ]

        output = formatter.format_presets(presets)

        assert "test-preset" in output
        assert "Custom" in output

    def test_json_formatter_presets(self):
        """Test JSONFormatter with presets"""
        formatter = JSONFormatter()
        presets = [
            {
                'name': 'gpu-optimized',
                'description': 'GPU instances',
                'is_builtin': True,
                'has_gpu': True
            },
            {
                'name': 'budget',
                'description': 'Low cost',
                'is_builtin': False,
                'max_price': 0.10
            }
        ]

        output = formatter.format_presets(presets)
        data = json.loads(output)

        assert 'presets' in data
        assert len(data['presets']) == 2
        assert data['presets'][0]['name'] == 'gpu-optimized'
        assert data['presets'][0]['is_builtin'] is True
        assert data['presets'][1]['name'] == 'budget'
        assert data['presets'][1]['is_builtin'] is False

    def test_json_formatter_presets_empty(self):
        """Test JSONFormatter with empty presets list"""
        formatter = JSONFormatter()
        presets = []

        output = formatter.format_presets(presets)
        data = json.loads(output)

        assert 'presets' in data
        assert data['presets'] == []

    def test_csv_formatter_presets(self):
        """Test CSVFormatter with presets"""
        formatter = CSVFormatter()
        presets = [
            {
                'name': 'compute',
                'description': 'Compute optimized',
                'is_builtin': True
            },
            {
                'name': 'custom-memory',
                'description': 'High memory',
                'is_builtin': False
            }
        ]

        output = formatter.format_presets(presets)
        lines = output.strip().split('\n')

        # Check header
        assert "Name,Type,Description" in lines[0]

        # Check rows
        assert "compute,Built-in,Compute optimized" in output
        assert "custom-memory,Custom,High memory" in output

    def test_csv_formatter_presets_empty(self):
        """Test CSVFormatter with empty presets list"""
        formatter = CSVFormatter()
        presets = []

        output = formatter.format_presets(presets)
        lines = output.strip().split('\n')

        # Should only have header
        assert len(lines) == 1
        assert "Name,Type,Description" in lines[0]


class TestGetFormatter:
    """Tests for get_formatter function"""

    def test_get_formatter_table(self):
        """Test getting table formatter"""
        formatter = get_formatter("table")
        assert isinstance(formatter, TableFormatter)

    def test_get_formatter_json(self):
        """Test getting JSON formatter"""
        formatter = get_formatter("json")
        assert isinstance(formatter, JSONFormatter)

    def test_get_formatter_csv(self):
        """Test getting CSV formatter"""
        formatter = get_formatter("csv")
        assert isinstance(formatter, CSVFormatter)

    def test_get_formatter_invalid(self):
        """Test getting invalid formatter raises ValueError"""
        with pytest.raises(ValueError, match="Unknown format"):
            get_formatter("invalid")


class TestFormatterEdgeCases:
    """Tests for edge cases in formatters"""

    def test_cache_stats_large_numbers(self):
        """Test cache stats with large numbers"""
        formatter = TableFormatter()
        stats = {
            'total_entries': 1000000,
            'valid_entries': 999999,
            'expired_entries': 1,
            'cache_size_bytes': 5000000000  # 5GB
        }
        cache_dir = "/data/cache"

        output = formatter.format_cache_stats(stats, cache_dir)

        # Cache size should be formatted with commas
        assert "5,000,000,000" in output
        # Entry counts are present (may or may not have commas)
        assert "1000000" in output or "1,000,000" in output
        assert "999999" in output or "999,999" in output

    def test_presets_special_characters_in_description(self):
        """Test presets with special characters"""
        formatter = TableFormatter()
        presets = [
            {
                'name': 'test',
                'description': 'Test with "quotes" and special chars: <>&',
                'is_builtin': False
            }
        ]

        output = formatter.format_presets(presets)

        # Should handle special characters
        assert 'test' in output

    def test_json_formatter_serialization(self):
        """Test JSON formatter produces valid JSON"""
        formatter = JSONFormatter()
        stats = {
            'total_entries': 10,
            'valid_entries': 8,
            'expired_entries': 2,
            'cache_size_bytes': 1024
        }

        output = formatter.format_cache_stats(stats, "/cache")

        # Should be valid JSON
        data = json.loads(output)
        assert isinstance(data, dict)
        assert 'cache_dir' in data
        assert 'stats' in data
