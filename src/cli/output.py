"""Output formatters for CLI"""

import json
import csv
import sys
from io import StringIO
from typing import List, Dict, Any, Optional
from tabulate import tabulate

from src.models.instance_type import InstanceType


class OutputFormatter:
    """Base class for output formatters"""
    
    def format_instance_list(self, instances: List[InstanceType], region: str) -> str:
        """Format a list of instance types"""
        raise NotImplementedError
    
    def format_instance_detail(self, instance: InstanceType, region: str) -> str:
        """Format detailed information for a single instance type"""
        raise NotImplementedError
    
    def format_regions(self, regions: List[Dict[str, str]]) -> str:
        """Format a list of regions"""
        raise NotImplementedError
    
    def format_pricing(self, instance: InstanceType, region: str) -> str:
        """Format pricing information"""
        raise NotImplementedError
    
    def format_comparison(self, instance1: InstanceType, instance2: InstanceType, region: str) -> str:
        """Format comparison between two instance types"""
        raise NotImplementedError


class TableFormatter(OutputFormatter):
    """Table formatter for human-readable output"""
    
    def format_instance_list(self, instances: List[InstanceType], region: str) -> str:
        """Format instance list as a table"""
        if not instances:
            return f"No instance types found in region {region}"
        
        headers = [
            "Instance Type",
            "vCPU",
            "Memory (GB)",
            "Network",
            "On-Demand Price/hr",
            "Free Tier"
        ]
        
        rows = []
        for inst in instances:
            memory_gb = inst.memory_info.size_in_gb
            memory_str = f"{memory_gb:.1f}" if memory_gb >= 1 else f"{memory_gb:.2f}"
            
            price_str = "N/A"
            if inst.pricing and inst.pricing.on_demand_price is not None:
                price_str = f"${inst.pricing.on_demand_price:.4f}"
            
            free_tier = "🆓" if self._is_free_tier(inst.instance_type) else ""
            
            rows.append([
                inst.instance_type,
                inst.vcpu_info.default_vcpus,
                memory_str,
                inst.network_info.network_performance,
                price_str,
                free_tier
            ])
        
        return tabulate(rows, headers=headers, tablefmt="grid")
    
    def format_instance_detail(self, instance: InstanceType, region: str) -> str:
        """Format detailed instance information"""
        lines = []
        lines.append(f"Instance Type: {instance.instance_type}")
        lines.append(f"Region: {region}")
        lines.append("")
        
        # Compute
        lines.append("Compute:")
        lines.append(f"  vCPU: {instance.vcpu_info.default_vcpus}")
        if instance.vcpu_info.default_cores:
            lines.append(f"  Cores: {instance.vcpu_info.default_cores}")
        if instance.vcpu_info.default_threads_per_core:
            lines.append(f"  Threads per Core: {instance.vcpu_info.default_threads_per_core}")
        lines.append("")
        
        # Memory
        memory_gb = instance.memory_info.size_in_gb
        memory_str = f"{memory_gb:.1f} GB" if memory_gb >= 1 else f"{memory_gb:.2f} GB"
        lines.append(f"Memory: {memory_str}")
        lines.append("")
        
        # Network
        lines.append("Network:")
        lines.append(f"  Performance: {instance.network_info.network_performance}")
        lines.append(f"  Max Network Interfaces: {instance.network_info.maximum_network_interfaces}")
        lines.append(f"  Max IPv4 per Interface: {instance.network_info.maximum_ipv4_addresses_per_interface}")
        lines.append(f"  Max IPv6 per Interface: {instance.network_info.maximum_ipv6_addresses_per_interface}")
        lines.append("")
        
        # Processor
        lines.append("Processor:")
        lines.append(f"  Architectures: {', '.join(instance.processor_info.supported_architectures)}")
        if instance.processor_info.sustained_clock_speed_in_ghz:
            lines.append(f"  Clock Speed: {instance.processor_info.sustained_clock_speed_in_ghz} GHz")
        lines.append("")
        
        # Storage
        lines.append("Storage:")
        lines.append(f"  EBS Optimized: {instance.ebs_info.ebs_optimized_support}")
        if instance.instance_storage_info:
            if instance.instance_storage_info.total_size_in_gb:
                lines.append(f"  Instance Store: {instance.instance_storage_info.total_size_in_gb} GB")
            if instance.instance_storage_info.nvme_support:
                lines.append(f"  NVMe Support: {instance.instance_storage_info.nvme_support}")
        lines.append("")
        
        # Features
        lines.append("Features:")
        lines.append(f"  Current Generation: {instance.current_generation}")
        lines.append(f"  Burstable Performance: {instance.burstable_performance_supported}")
        lines.append(f"  Hibernation: {instance.hibernation_supported}")
        if self._is_free_tier(instance.instance_type):
            lines.append("  Free Tier Eligible: Yes 🆓")
        lines.append("")
        
        # Pricing
        if instance.pricing:
            lines.append("Pricing:")
            if instance.pricing.on_demand_price is not None:
                lines.append(f"  On-Demand: ${instance.pricing.on_demand_price:.4f}/hr")
                monthly = instance.pricing.calculate_monthly_cost()
                if monthly:
                    lines.append(f"  Monthly (730 hrs): ${monthly:.2f}")
                    annual = instance.pricing.calculate_annual_cost()
                    if annual:
                        lines.append(f"  Annual: ${annual:.2f}")
            else:
                lines.append("  On-Demand: N/A")
            
            if instance.pricing.spot_price is not None:
                lines.append(f"  Spot: ${instance.pricing.spot_price:.4f}/hr")
                if instance.pricing.on_demand_price:
                    savings = ((instance.pricing.on_demand_price - instance.pricing.spot_price) / instance.pricing.on_demand_price) * 100
                    lines.append(f"  Spot Savings: {savings:.1f}%")
            else:
                lines.append("  Spot: N/A")
        else:
            lines.append("Pricing: Not available")
        
        return "\n".join(lines)
    
    def format_regions(self, regions: List[Dict[str, str]]) -> str:
        """Format regions list"""
        if not regions:
            return "No regions available"
        
        headers = ["Region Code", "Region Name"]
        rows = [[r.get('code', ''), r.get('name', '')] for r in regions]
        return tabulate(rows, headers=headers, tablefmt="grid")
    
    def format_pricing(self, instance: InstanceType, region: str) -> str:
        """Format pricing information"""
        if not instance.pricing:
            return f"Pricing not available for {instance.instance_type} in {region}"
        
        lines = []
        lines.append(f"Pricing for {instance.instance_type} in {region}:")
        lines.append("")
        
        if instance.pricing.on_demand_price is not None:
            lines.append(f"On-Demand: ${instance.pricing.on_demand_price:.4f}/hr")
            monthly = instance.pricing.calculate_monthly_cost()
            if monthly:
                lines.append(f"Monthly (730 hrs): ${monthly:.2f}")
                annual = instance.pricing.calculate_annual_cost()
                if annual:
                    lines.append(f"Annual: ${annual:.2f}")
        else:
            lines.append("On-Demand: N/A")
        
        if instance.pricing.spot_price is not None:
            lines.append(f"Spot: ${instance.pricing.spot_price:.4f}/hr")
            if instance.pricing.on_demand_price:
                savings = ((instance.pricing.on_demand_price - instance.pricing.spot_price) / instance.pricing.on_demand_price) * 100
                lines.append(f"Spot Savings: {savings:.1f}%")
        else:
            lines.append("Spot: N/A")
        
        return "\n".join(lines)
    
    def format_comparison(self, instance1: InstanceType, instance2: InstanceType, region: str) -> str:
        """Format comparison between two instances"""
        headers = ["Property", instance1.instance_type, instance2.instance_type]
        
        rows = [
            ["Instance Type", instance1.instance_type, instance2.instance_type],
            ["vCPU", str(instance1.vcpu_info.default_vcpus), str(instance2.vcpu_info.default_vcpus)],
            ["Memory (GB)", f"{instance1.memory_info.size_in_gb:.1f}", f"{instance2.memory_info.size_in_gb:.1f}"],
            ["Network", instance1.network_info.network_performance, instance2.network_info.network_performance],
        ]
        
        # Pricing comparison
        price1 = f"${instance1.pricing.on_demand_price:.4f}" if (instance1.pricing and instance1.pricing.on_demand_price) else "N/A"
        price2 = f"${instance2.pricing.on_demand_price:.4f}" if (instance2.pricing and instance2.pricing.on_demand_price) else "N/A"
        rows.append(["On-Demand Price/hr", price1, price2])
        
        # Free tier
        free1 = "Yes 🆓" if self._is_free_tier(instance1.instance_type) else "No"
        free2 = "Yes 🆓" if self._is_free_tier(instance2.instance_type) else "No"
        rows.append(["Free Tier Eligible", free1, free2])
        
        return tabulate(rows, headers=headers, tablefmt="grid")
    
    def _is_free_tier(self, instance_type: str) -> bool:
        """Check if instance type is free tier eligible"""
        from src.services.free_tier_service import FreeTierService
        return FreeTierService().is_eligible(instance_type)


class JSONFormatter(OutputFormatter):
    """JSON formatter for machine-readable output"""
    
    def format_instance_list(self, instances: List[InstanceType], region: str) -> str:
        """Format instance list as JSON"""
        data = {
            "region": region,
            "count": len(instances),
            "instances": [self._instance_to_dict(inst) for inst in instances]
        }
        return json.dumps(data, indent=2)
    
    def format_instance_detail(self, instance: InstanceType, region: str) -> str:
        """Format instance detail as JSON"""
        data = {
            "region": region,
            "instance": self._instance_to_dict(instance, detailed=True)
        }
        return json.dumps(data, indent=2)
    
    def format_regions(self, regions: List[Dict[str, str]]) -> str:
        """Format regions as JSON"""
        return json.dumps({"regions": regions}, indent=2)
    
    def format_pricing(self, instance: InstanceType, region: str) -> str:
        """Format pricing as JSON"""
        pricing_data = {}
        if instance.pricing:
            pricing_data = {
                "on_demand_price_per_hour": instance.pricing.on_demand_price,
                "spot_price_per_hour": instance.pricing.spot_price,
            }
            if instance.pricing.on_demand_price:
                pricing_data["monthly_cost"] = instance.pricing.calculate_monthly_cost()
                pricing_data["annual_cost"] = instance.pricing.calculate_annual_cost()
        
        data = {
            "region": region,
            "instance_type": instance.instance_type,
            "pricing": pricing_data
        }
        return json.dumps(data, indent=2)
    
    def format_comparison(self, instance1: InstanceType, instance2: InstanceType, region: str) -> str:
        """Format comparison as JSON"""
        data = {
            "region": region,
            "comparison": {
                instance1.instance_type: self._instance_to_dict(instance1),
                instance2.instance_type: self._instance_to_dict(instance2)
            }
        }
        return json.dumps(data, indent=2)
    
    def _instance_to_dict(self, instance: InstanceType, detailed: bool = False) -> Dict[str, Any]:
        """Convert instance to dictionary"""
        data = {
            "instance_type": instance.instance_type,
            "vcpu": instance.vcpu_info.default_vcpus,
            "memory_gb": instance.memory_info.size_in_gb,
            "network_performance": instance.network_info.network_performance,
        }
        
        if detailed:
            data.update({
                "vcpu_info": {
                    "default_vcpus": instance.vcpu_info.default_vcpus,
                    "default_cores": instance.vcpu_info.default_cores,
                    "default_threads_per_core": instance.vcpu_info.default_threads_per_core,
                },
                "memory_info": {
                    "size_in_mib": instance.memory_info.size_in_mib,
                    "size_in_gb": instance.memory_info.size_in_gb,
                },
                "network_info": {
                    "network_performance": instance.network_info.network_performance,
                    "max_network_interfaces": instance.network_info.maximum_network_interfaces,
                    "max_ipv4_per_interface": instance.network_info.maximum_ipv4_addresses_per_interface,
                    "max_ipv6_per_interface": instance.network_info.maximum_ipv6_addresses_per_interface,
                },
                "processor_info": {
                    "supported_architectures": instance.processor_info.supported_architectures,
                    "sustained_clock_speed_ghz": instance.processor_info.sustained_clock_speed_in_ghz,
                },
                "ebs_info": {
                    "ebs_optimized_support": instance.ebs_info.ebs_optimized_support,
                    "is_ebs_optimized": instance.ebs_info.is_ebs_optimized,
                },
                "current_generation": instance.current_generation,
                "burstable_performance_supported": instance.burstable_performance_supported,
                "hibernation_supported": instance.hibernation_supported,
            })
            
            if instance.instance_storage_info:
                data["instance_storage_info"] = {
                    "total_size_gb": instance.instance_storage_info.total_size_in_gb,
                    "nvme_support": instance.instance_storage_info.nvme_support,
                }
        
        if instance.pricing:
            pricing = {
                "on_demand_price_per_hour": instance.pricing.on_demand_price,
                "spot_price_per_hour": instance.pricing.spot_price,
            }
            if instance.pricing.on_demand_price:
                pricing["monthly_cost"] = instance.pricing.calculate_monthly_cost()
                pricing["annual_cost"] = instance.pricing.calculate_annual_cost()
            data["pricing"] = pricing
        
        from src.services.free_tier_service import FreeTierService
        data["free_tier_eligible"] = FreeTierService().is_eligible(instance.instance_type)
        
        return data


class CSVFormatter(OutputFormatter):
    """CSV formatter for spreadsheet import"""
    
    def format_instance_list(self, instances: List[InstanceType], region: str) -> str:
        """Format instance list as CSV"""
        if not instances:
            return ""
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "Instance Type",
            "vCPU",
            "Memory (GB)",
            "Network Performance",
            "On-Demand Price/hr",
            "Spot Price/hr",
            "Monthly Cost",
            "Annual Cost",
            "Free Tier Eligible"
        ])
        
        # Rows
        for inst in instances:
            memory_gb = inst.memory_info.size_in_gb
            on_demand = inst.pricing.on_demand_price if (inst.pricing and inst.pricing.on_demand_price) else ""
            spot = inst.pricing.spot_price if (inst.pricing and inst.pricing.spot_price) else ""
            monthly = inst.pricing.calculate_monthly_cost() if inst.pricing else ""
            annual = inst.pricing.calculate_annual_cost() if inst.pricing else ""
            
            from src.services.free_tier_service import FreeTierService
            free_tier = "Yes" if FreeTierService().is_eligible(inst.instance_type) else "No"
            
            writer.writerow([
                inst.instance_type,
                inst.vcpu_info.default_vcpus,
                f"{memory_gb:.2f}",
                inst.network_info.network_performance,
                on_demand,
                spot,
                monthly,
                annual,
                free_tier
            ])
        
        return output.getvalue()
    
    def format_instance_detail(self, instance: InstanceType, region: str) -> str:
        """CSV doesn't support detailed format well, return summary"""
        return self.format_instance_list([instance], region)
    
    def format_regions(self, regions: List[Dict[str, str]]) -> str:
        """Format regions as CSV"""
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["Region Code", "Region Name"])
        for r in regions:
            writer.writerow([r.get('code', ''), r.get('name', '')])
        return output.getvalue()
    
    def format_pricing(self, instance: InstanceType, region: str) -> str:
        """Format pricing as CSV"""
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["Instance Type", "Region", "On-Demand Price/hr", "Spot Price/hr", "Monthly Cost", "Annual Cost"])
        
        on_demand = instance.pricing.on_demand_price if (instance.pricing and instance.pricing.on_demand_price) else ""
        spot = instance.pricing.spot_price if (instance.pricing and instance.pricing.spot_price) else ""
        monthly = instance.pricing.calculate_monthly_cost() if instance.pricing else ""
        annual = instance.pricing.calculate_annual_cost() if instance.pricing else ""
        
        writer.writerow([instance.instance_type, region, on_demand, spot, monthly, annual])
        return output.getvalue()
    
    def format_comparison(self, instance1: InstanceType, instance2: InstanceType, region: str) -> str:
        """Format comparison as CSV"""
        # CSV comparison is just two rows
        return self.format_instance_list([instance1, instance2], region)


def get_formatter(format_type: str) -> OutputFormatter:
    """Get formatter by type"""
    formatters = {
        "table": TableFormatter(),
        "json": JSONFormatter(),
        "csv": CSVFormatter(),
    }
    
    if format_type not in formatters:
        raise ValueError(f"Unknown format: {format_type}. Supported: {', '.join(formatters.keys())}")
    
    return formatters[format_type]
