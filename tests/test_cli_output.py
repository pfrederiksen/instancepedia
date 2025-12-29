"""Tests for CLI output formatters"""

import pytest
from src.cli.output import TableFormatter, JSONFormatter, CSVFormatter, get_formatter
from tests.conftest import sample_instance_type, sample_instance_type_no_pricing


class TestTableFormatter:
    """Tests for TableFormatter"""
    
    def test_format_instance_list(self, sample_instance_type):
        """Test formatting instance list as table"""
        formatter = TableFormatter()
        result = formatter.format_instance_list([sample_instance_type], "us-east-1")
        
        assert "Instance Type" in result
        assert "t3.micro" in result
        assert "vCPU" in result
        assert "2" in result  # vCPU count
        assert "1.0" in result or "1" in result  # Memory in GB
    
    def test_format_instance_list_empty(self):
        """Test formatting empty instance list"""
        formatter = TableFormatter()
        result = formatter.format_instance_list([], "us-east-1")
        assert "No instance types found" in result
    
    def test_format_instance_detail(self, sample_instance_type):
        """Test formatting instance detail"""
        formatter = TableFormatter()
        result = formatter.format_instance_detail(sample_instance_type, "us-east-1")
        
        assert "Instance Type: t3.micro" in result
        assert "Region: us-east-1" in result
        assert "vCPU: 2" in result
        assert "Memory: 1.0 GB" in result or "Memory: 1 GB" in result
        assert "Network:" in result
        assert "Pricing:" in result
    
    def test_format_regions(self):
        """Test formatting regions list"""
        formatter = TableFormatter()
        regions = [
            {"code": "us-east-1", "name": "N. Virginia"},
            {"code": "us-west-2", "name": "Oregon"}
        ]
        result = formatter.format_regions(regions)
        
        assert "Region Code" in result
        assert "us-east-1" in result
        assert "us-west-2" in result
    
    def test_format_pricing(self, sample_instance_type):
        """Test formatting pricing information"""
        formatter = TableFormatter()
        result = formatter.format_pricing(sample_instance_type, "us-east-1")
        
        assert "t3.micro" in result
        assert "On-Demand" in result
        assert "Spot" in result
        assert "$0.0104" in result or "0.0104" in result
    
    def test_format_comparison(self, sample_instance_type, sample_instance_type_no_pricing):
        """Test formatting comparison"""
        formatter = TableFormatter()
        result = formatter.format_comparison(
            sample_instance_type,
            sample_instance_type_no_pricing,
            "us-east-1"
        )
        
        assert "Property" in result
        assert "t3.micro" in result
        assert "m5.large" in result


class TestJSONFormatter:
    """Tests for JSONFormatter"""
    
    def test_format_instance_list(self, sample_instance_type):
        """Test formatting instance list as JSON"""
        formatter = JSONFormatter()
        result = formatter.format_instance_list([sample_instance_type], "us-east-1")
        
        import json
        data = json.loads(result)
        
        assert data["region"] == "us-east-1"
        assert data["count"] == 1
        assert len(data["instances"]) == 1
        assert data["instances"][0]["instance_type"] == "t3.micro"
        assert data["instances"][0]["vcpu"] == 2
    
    def test_format_instance_detail(self, sample_instance_type):
        """Test formatting instance detail as JSON"""
        formatter = JSONFormatter()
        result = formatter.format_instance_detail(sample_instance_type, "us-east-1")
        
        import json
        data = json.loads(result)
        
        assert data["region"] == "us-east-1"
        assert data["instance"]["instance_type"] == "t3.micro"
        assert "vcpu_info" in data["instance"]
        assert "pricing" in data["instance"]
    
    def test_format_regions(self):
        """Test formatting regions as JSON"""
        formatter = JSONFormatter()
        regions = [
            {"code": "us-east-1", "name": "N. Virginia"}
        ]
        result = formatter.format_regions(regions)
        
        import json
        data = json.loads(result)
        
        assert "regions" in data
        assert len(data["regions"]) == 1
        assert data["regions"][0]["code"] == "us-east-1"
    
    def test_format_pricing(self, sample_instance_type):
        """Test formatting pricing as JSON"""
        formatter = JSONFormatter()
        result = formatter.format_pricing(sample_instance_type, "us-east-1")
        
        import json
        data = json.loads(result)
        
        assert data["region"] == "us-east-1"
        assert data["instance_type"] == "t3.micro"
        assert "pricing" in data
        assert data["pricing"]["on_demand_price_per_hour"] == 0.0104
    
    def test_format_comparison(self, sample_instance_type, sample_instance_type_no_pricing):
        """Test formatting comparison as JSON"""
        formatter = JSONFormatter()
        result = formatter.format_comparison(
            sample_instance_type,
            sample_instance_type_no_pricing,
            "us-east-1"
        )
        
        import json
        data = json.loads(result)
        
        assert data["region"] == "us-east-1"
        assert "comparison" in data
        assert "t3.micro" in data["comparison"]
        assert "m5.large" in data["comparison"]


class TestCSVFormatter:
    """Tests for CSVFormatter"""
    
    def test_format_instance_list(self, sample_instance_type):
        """Test formatting instance list as CSV"""
        formatter = CSVFormatter()
        result = formatter.format_instance_list([sample_instance_type], "us-east-1")
        
        assert "Instance Type" in result
        assert "t3.micro" in result
        assert "vCPU" in result
        # Check it's valid CSV (has commas)
        assert "," in result
    
    def test_format_instance_list_empty(self):
        """Test formatting empty instance list as CSV"""
        formatter = CSVFormatter()
        result = formatter.format_instance_list([], "us-east-1")
        assert result == ""
    
    def test_format_regions(self):
        """Test formatting regions as CSV"""
        formatter = CSVFormatter()
        regions = [
            {"code": "us-east-1", "name": "N. Virginia"}
        ]
        result = formatter.format_regions(regions)
        
        assert "Region Code" in result
        assert "us-east-1" in result
        assert "," in result
    
    def test_format_pricing(self, sample_instance_type):
        """Test formatting pricing as CSV"""
        formatter = CSVFormatter()
        result = formatter.format_pricing(sample_instance_type, "us-east-1")
        
        assert "Instance Type" in result
        assert "t3.micro" in result
        assert "," in result


class TestGetFormatter:
    """Tests for get_formatter function"""
    
    def test_get_table_formatter(self):
        """Test getting table formatter"""
        formatter = get_formatter("table")
        assert isinstance(formatter, TableFormatter)
    
    def test_get_json_formatter(self):
        """Test getting JSON formatter"""
        formatter = get_formatter("json")
        assert isinstance(formatter, JSONFormatter)
    
    def test_get_csv_formatter(self):
        """Test getting CSV formatter"""
        formatter = get_formatter("csv")
        assert isinstance(formatter, CSVFormatter)
    
    def test_get_invalid_formatter(self):
        """Test getting invalid formatter raises error"""
        with pytest.raises(ValueError, match="Unknown format"):
            get_formatter("invalid")
