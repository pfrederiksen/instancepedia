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
    baseline_bandwidth_in_gbps: Optional[float] = None
    peak_bandwidth_in_gbps: Optional[float] = None

    def format_bandwidth(self) -> str:
        """Format bandwidth information for display"""
        if self.baseline_bandwidth_in_gbps and self.peak_bandwidth_in_gbps:
            if self.baseline_bandwidth_in_gbps == self.peak_bandwidth_in_gbps:
                return f"{self.baseline_bandwidth_in_gbps} Gbps"
            else:
                return f"{self.baseline_bandwidth_in_gbps}-{self.peak_bandwidth_in_gbps} Gbps (baseline-peak)"
        elif self.baseline_bandwidth_in_gbps:
            return f"{self.baseline_bandwidth_in_gbps} Gbps (baseline)"
        elif self.peak_bandwidth_in_gbps:
            return f"Up to {self.peak_bandwidth_in_gbps} Gbps"
        else:
            return self.network_performance


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
class GpuDevice:
    """GPU device information"""
    name: str
    manufacturer: str
    count: int
    memory_in_mib: Optional[int] = None

    @property
    def memory_in_gb(self) -> Optional[float]:
        """Convert GPU memory from MiB to GB"""
        if self.memory_in_mib is None:
            return None
        return self.memory_in_mib / 1024.0


@dataclass
class GpuInfo:
    """GPU/Accelerator information"""
    gpus: List[GpuDevice]
    total_gpu_memory_in_mib: Optional[int] = None

    @property
    def total_gpu_count(self) -> int:
        """Total number of GPUs across all devices"""
        return sum(gpu.count for gpu in self.gpus)

    @property
    def total_gpu_memory_in_gb(self) -> Optional[float]:
        """Total GPU memory in GB"""
        if self.total_gpu_memory_in_mib is None:
            return None
        return self.total_gpu_memory_in_mib / 1024.0

    @property
    def is_fractional_gpu(self) -> bool:
        """Check if this is a fractional/shared GPU instance (count=0 but has memory)"""
        return self.total_gpu_count == 0 and self.total_gpu_memory_in_mib is not None and self.total_gpu_memory_in_mib > 0

    @property
    def gpu_description(self) -> str:
        """Get human-readable GPU description"""
        if self.is_fractional_gpu:
            # Fractional/shared GPU (e.g., g6f instances)
            gpu_name = self.gpus[0].name if self.gpus else "Unknown"
            memory_gb = self.total_gpu_memory_in_gb
            return f"Shared {gpu_name} ({memory_gb:.1f}GB)"
        elif self.total_gpu_count > 0:
            # Full GPUs
            gpu_name = self.gpus[0].name if self.gpus else "Unknown"
            count = self.total_gpu_count
            memory_gb = self.total_gpu_memory_in_gb
            if count == 1:
                return f"1x {gpu_name} ({memory_gb:.1f}GB)"
            else:
                return f"{count}x {gpu_name} ({memory_gb:.1f}GB)"
        return "No GPU"


@dataclass
class PricingInfo:
    """Pricing information"""
    on_demand_price: Optional[float] = None  # Price per hour in USD
    spot_price: Optional[float] = None  # Current spot price per hour in USD
    savings_plan_1yr_no_upfront: Optional[float] = None  # 1-year savings plan, no upfront
    savings_plan_3yr_no_upfront: Optional[float] = None  # 3-year savings plan, no upfront

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

    def format_savings_plan_1yr(self) -> str:
        """Format 1-year savings plan price for display"""
        if self.savings_plan_1yr_no_upfront is None:
            return "N/A"
        return f"${self.savings_plan_1yr_no_upfront:.4f}/hr"

    def format_savings_plan_3yr(self) -> str:
        """Format 3-year savings plan price for display"""
        if self.savings_plan_3yr_no_upfront is None:
            return "N/A"
        return f"${self.savings_plan_3yr_no_upfront:.4f}/hr"

    def calculate_savings_percentage(self, price_type: str = "1yr") -> Optional[float]:
        """Calculate savings percentage compared to on-demand

        Args:
            price_type: Either "1yr", "3yr", or "spot"

        Returns:
            Savings percentage (0-100) or None if prices not available
        """
        if self.on_demand_price is None:
            return None

        if price_type == "1yr" and self.savings_plan_1yr_no_upfront:
            savings = (self.on_demand_price - self.savings_plan_1yr_no_upfront) / self.on_demand_price * 100
            return max(0, savings)
        elif price_type == "3yr" and self.savings_plan_3yr_no_upfront:
            savings = (self.on_demand_price - self.savings_plan_3yr_no_upfront) / self.on_demand_price * 100
            return max(0, savings)
        elif price_type == "spot" and self.spot_price:
            savings = (self.on_demand_price - self.spot_price) / self.on_demand_price * 100
            return max(0, savings)

        return None

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
    gpu_info: Optional[GpuInfo] = None
    current_generation: bool = True
    burstable_performance_supported: bool = False
    hibernation_supported: bool = False
    pricing: Optional[PricingInfo] = None

    @property
    def generation(self) -> Optional[int]:
        """Extract generation number from instance type name

        Examples:
            m6i.large -> 6
            t3.micro -> 3
            c7g.xlarge -> 7
            mac2.metal -> 2
        """
        import re
        # Match pattern: family + generation number (e.g., m6, t3, c7)
        match = re.search(r'[a-z]+(\d+)', self.instance_type)
        if match:
            return int(match.group(1))
        return None

    @property
    def generation_label(self) -> str:
        """Format generation as human-readable label"""
        gen = self.generation
        if gen is None:
            return "Unknown generation"

        # Handle special cases for ordinal suffix
        if 10 <= gen % 100 <= 20:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(gen % 10, "th")

        return f"{gen}{suffix} gen"

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

        # Extract bandwidth information from NetworkCards if available
        baseline_bandwidth = None
        peak_bandwidth = None
        network_cards = network_data.get("NetworkCards")
        if network_cards:
            # Sum bandwidth across all network cards (for multi-card instances)
            baseline_sum = sum(card.get("BaselineBandwidthInGbps", 0) for card in network_cards if card.get("BaselineBandwidthInGbps"))
            peak_sum = sum(card.get("PeakBandwidthInGbps", 0) for card in network_cards if card.get("PeakBandwidthInGbps"))
            baseline_bandwidth = baseline_sum if baseline_sum > 0 else None
            peak_bandwidth = peak_sum if peak_sum > 0 else None

        network_info = NetworkInfo(
            network_performance=network_data.get("NetworkPerformance", "Unknown"),
            maximum_network_interfaces=network_data.get("MaximumNetworkInterfaces", 0),
            maximum_ipv4_addresses_per_interface=network_data.get("Ipv4AddressesPerInterface", 0),
            maximum_ipv6_addresses_per_interface=network_data.get("Ipv6AddressesPerInterface", 0),
            baseline_bandwidth_in_gbps=baseline_bandwidth,
            peak_bandwidth_in_gbps=peak_bandwidth,
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

        # Parse GPU information
        gpu_info = None
        gpu_data = data.get("GpuInfo")
        if gpu_data and gpu_data.get("Gpus"):
            gpu_devices = []
            for gpu_device_data in gpu_data.get("Gpus", []):
                memory_info_data = gpu_device_data.get("MemoryInfo", {})
                gpu_device = GpuDevice(
                    name=gpu_device_data.get("Name", "Unknown"),
                    manufacturer=gpu_device_data.get("Manufacturer", "Unknown"),
                    count=gpu_device_data.get("Count", 1),
                    memory_in_mib=memory_info_data.get("SizeInMiB"),
                )
                gpu_devices.append(gpu_device)

            gpu_info = GpuInfo(
                gpus=gpu_devices,
                total_gpu_memory_in_mib=gpu_data.get("TotalGpuMemoryInMiB"),
            )

        return cls(
            instance_type=data.get("InstanceType", ""),
            vcpu_info=vcpu_info,
            memory_info=memory_info,
            network_info=network_info,
            processor_info=processor_info,
            ebs_info=ebs_info,
            instance_storage_info=instance_storage_info,
            gpu_info=gpu_info,
            current_generation=data.get("CurrentGeneration", True),
            burstable_performance_supported=data.get("BurstablePerformanceSupported", False),
            hibernation_supported=data.get("HibernationSupported", False),
        )

