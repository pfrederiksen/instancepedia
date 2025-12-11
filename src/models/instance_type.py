"""Instance type data models"""

from typing import List, Optional
from dataclasses import dataclass


@dataclass
class VCpuInfo:
    """vCPU information"""
    default_vcpus: int
    default_cores: Optional[int] = None
    default_threads_per_core: Optional[int] = None


@dataclass
class MemoryInfo:
    """Memory information"""
    size_in_mib: int

    @property
    def size_in_gb(self) -> float:
        """Convert MiB to GB"""
        return self.size_in_mib / 1024.0


@dataclass
class NetworkInfo:
    """Network information"""
    network_performance: str
    maximum_network_interfaces: int
    maximum_ipv4_addresses_per_interface: int
    maximum_ipv6_addresses_per_interface: int


@dataclass
class ProcessorInfo:
    """Processor information"""
    supported_architectures: List[str]
    sustained_clock_speed_in_ghz: Optional[float] = None


@dataclass
class EbsInfo:
    """EBS information"""
    ebs_optimized_support: str
    ebs_optimized_info: Optional[dict] = None

    @property
    def is_ebs_optimized(self) -> bool:
        """Check if EBS optimized is supported"""
        return self.ebs_optimized_support in ["supported", "default"]


@dataclass
class InstanceStorageInfo:
    """Instance storage information"""
    total_size_in_gb: Optional[int] = None
    disks: Optional[List[dict]] = None
    nvme_support: Optional[str] = None


@dataclass
class PricingInfo:
    """Pricing information"""
    on_demand_price: Optional[float] = None  # Price per hour in USD
    spot_price: Optional[float] = None  # Current spot price per hour in USD

    def format_on_demand(self) -> str:
        """Format on-demand price for display"""
        if self.on_demand_price is None:
            return "N/A"
        return f"${self.on_demand_price:.4f}/hr"

    def format_spot(self) -> str:
        """Format spot price for display"""
        if self.spot_price is None:
            return "N/A"
        return f"${self.spot_price:.4f}/hr"

    def calculate_monthly_cost(self, hours_per_month: float = 730) -> Optional[float]:
        """Calculate monthly cost based on hours per month (default 730 = 24*365/12)"""
        if self.on_demand_price is None:
            return None
        return self.on_demand_price * hours_per_month

    def calculate_annual_cost(self) -> Optional[float]:
        """Calculate annual cost"""
        monthly = self.calculate_monthly_cost()
        if monthly is None:
            return None
        return monthly * 12


@dataclass
class InstanceType:
    """Complete instance type information"""
    instance_type: str
    vcpu_info: VCpuInfo
    memory_info: MemoryInfo
    network_info: NetworkInfo
    processor_info: ProcessorInfo
    ebs_info: EbsInfo
    instance_storage_info: Optional[InstanceStorageInfo] = None
    current_generation: bool = True
    burstable_performance_supported: bool = False
    hibernation_supported: bool = False
    pricing: Optional[PricingInfo] = None

    @classmethod
    def from_aws_response(cls, data: dict) -> "InstanceType":
        """Create InstanceType from AWS API response"""
        vcpu_data = data.get("VCpuInfo", {})
        memory_data = data.get("MemoryInfo", {})
        network_data = data.get("NetworkInfo", {})
        processor_data = data.get("ProcessorInfo", {})
        ebs_data = data.get("EbsInfo", {})
        storage_data = data.get("InstanceStorageInfo")

        vcpu_info = VCpuInfo(
            default_vcpus=vcpu_data.get("DefaultVCpus", 0),
            default_cores=vcpu_data.get("DefaultCores"),
            default_threads_per_core=vcpu_data.get("DefaultThreadsPerCore"),
        )

        memory_info = MemoryInfo(
            size_in_mib=memory_data.get("SizeInMiB", 0)
        )

        network_info = NetworkInfo(
            network_performance=network_data.get("NetworkPerformance", "Unknown"),
            maximum_network_interfaces=network_data.get("MaximumNetworkInterfaces", 0),
            maximum_ipv4_addresses_per_interface=network_data.get("Ipv4AddressesPerInterface", 0),
            maximum_ipv6_addresses_per_interface=network_data.get("Ipv6AddressesPerInterface", 0),
        )

        processor_info = ProcessorInfo(
            supported_architectures=processor_data.get("SupportedArchitectures", []),
            sustained_clock_speed_in_ghz=processor_data.get("SustainedClockSpeedInGhz"),
        )

        ebs_info = EbsInfo(
            ebs_optimized_support=ebs_data.get("EbsOptimizedSupport", "unsupported"),
            ebs_optimized_info=ebs_data.get("EbsOptimizedInfo"),
        )

        instance_storage_info = None
        if storage_data:
            instance_storage_info = InstanceStorageInfo(
                total_size_in_gb=storage_data.get("TotalSizeInGB"),
                disks=storage_data.get("Disks"),
                nvme_support=storage_data.get("NvmeSupport"),
            )

        return cls(
            instance_type=data.get("InstanceType", ""),
            vcpu_info=vcpu_info,
            memory_info=memory_info,
            network_info=network_info,
            processor_info=processor_info,
            ebs_info=ebs_info,
            instance_storage_info=instance_storage_info,
            current_generation=data.get("CurrentGeneration", True),
            burstable_performance_supported=data.get("BurstablePerformanceSupported", False),
            hibernation_supported=data.get("HibernationSupported", False),
        )

