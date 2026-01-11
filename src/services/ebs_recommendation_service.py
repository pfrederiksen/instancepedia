"""EBS volume type recommendation service"""

from typing import Dict
from dataclasses import dataclass


@dataclass
class EbsVolumeRecommendation:
    """EBS volume type recommendation"""
    volume_type: str
    description: str
    use_cases: list[str]
    iops_range: str | None = None
    throughput_range: str | None = None
    notes: str | None = None


class EbsRecommendationService:
    """Service for recommending EBS volume types based on instance characteristics"""

    def __init__(self):
        # EBS volume type definitions
        self.volume_types = {
            "gp3": EbsVolumeRecommendation(
                volume_type="gp3",
                description="General Purpose SSD (gp3) - Latest generation",
                use_cases=[
                    "Boot volumes",
                    "Low-latency interactive applications",
                    "Development and test environments",
                    "Virtual desktops"
                ],
                iops_range="3,000-16,000 IOPS (baseline 3,000)",
                throughput_range="125-1,000 MB/s (baseline 125 MB/s)",
                notes="Best price-performance ratio. IOPS and throughput can be provisioned independently."
            ),
            "gp2": EbsVolumeRecommendation(
                volume_type="gp2",
                description="General Purpose SSD (gp2) - Previous generation",
                use_cases=[
                    "Boot volumes",
                    "Low-latency interactive applications",
                    "Development and test environments"
                ],
                iops_range="100-16,000 IOPS (3 IOPS/GB)",
                throughput_range="Up to 250 MB/s",
                notes="Legacy option. Consider upgrading to gp3 for better performance and cost."
            ),
            "io2": EbsVolumeRecommendation(
                volume_type="io2",
                description="Provisioned IOPS SSD (io2) - High durability",
                use_cases=[
                    "Mission-critical applications",
                    "Large databases (Oracle, SQL Server, MySQL, PostgreSQL)",
                    "I/O-intensive NoSQL databases"
                ],
                iops_range="100-64,000 IOPS (up to 1,000 IOPS/GB)",
                throughput_range="Up to 1,000 MB/s",
                notes="99.999% durability. Best for workloads requiring sustained IOPS performance."
            ),
            "io1": EbsVolumeRecommendation(
                volume_type="io1",
                description="Provisioned IOPS SSD (io1) - Previous generation",
                use_cases=[
                    "Critical business applications",
                    "Large relational databases"
                ],
                iops_range="100-64,000 IOPS (up to 50 IOPS/GB)",
                throughput_range="Up to 1,000 MB/s",
                notes="Legacy option. Consider upgrading to io2 for better durability and performance."
            ),
            "st1": EbsVolumeRecommendation(
                volume_type="st1",
                description="Throughput Optimized HDD",
                use_cases=[
                    "Big data",
                    "Data warehouses",
                    "Log processing",
                    "Streaming workloads"
                ],
                iops_range="Up to 500 IOPS",
                throughput_range="Up to 500 MB/s (baseline 40 MB/s/TB)",
                notes="Cannot be used as boot volume. Best for sequential, throughput-intensive workloads."
            ),
            "sc1": EbsVolumeRecommendation(
                volume_type="sc1",
                description="Cold HDD - Lowest cost",
                use_cases=[
                    "Throughput-oriented storage for infrequently accessed data",
                    "Scenarios where lowest storage cost is important"
                ],
                iops_range="Up to 250 IOPS",
                throughput_range="Up to 250 MB/s (baseline 12 MB/s/TB)",
                notes="Cannot be used as boot volume. Best for cold data requiring fewer scans per day."
            )
        }

    def get_recommendations(
        self,
        ebs_optimized_support: str,
        ebs_optimized_info: Dict | None = None
    ) -> list[EbsVolumeRecommendation]:
        """Get EBS volume type recommendations based on instance characteristics

        Args:
            ebs_optimized_support: EBS optimization support level (unsupported, supported, default)
            ebs_optimized_info: Optional dict with MaximumBandwidthMbps, MaximumThroughputMBps, MaximumIops

        Returns:
            List of recommended EBS volume types, ordered by recommendation priority
        """
        recommendations = []

        # Extract instance EBS capabilities
        max_throughput_mbps = None
        max_bandwidth_mbps = None
        max_iops = None

        if ebs_optimized_info:
            max_bandwidth_mbps = ebs_optimized_info.get("MaximumBandwidthMbps")
            max_throughput_mbps = ebs_optimized_info.get("MaximumThroughputMBps")
            max_iops = ebs_optimized_info.get("MaximumIops")

        # Determine recommendation strategy based on EBS optimization
        if ebs_optimized_support in ["default", "supported"]:
            # Instance supports EBS optimization - recommend based on capabilities

            if max_throughput_mbps and max_throughput_mbps >= 500:
                # High throughput instances - recommend io2 first, then gp3
                recommendations.append(self.volume_types["io2"])
                recommendations.append(self.volume_types["gp3"])
                recommendations.append(self.volume_types["io1"])  # Legacy fallback
            elif max_throughput_mbps and max_throughput_mbps >= 250:
                # Medium throughput - recommend gp3 first, then io2
                recommendations.append(self.volume_types["gp3"])
                recommendations.append(self.volume_types["io2"])
            else:
                # Standard throughput - recommend gp3, then gp2
                recommendations.append(self.volume_types["gp3"])
                recommendations.append(self.volume_types["gp2"])

            # Add HDD options for large sequential workloads
            if max_throughput_mbps and max_throughput_mbps >= 250:
                recommendations.append(self.volume_types["st1"])

            recommendations.append(self.volume_types["sc1"])

        else:
            # No EBS optimization - recommend general purpose options
            recommendations.append(self.volume_types["gp3"])
            recommendations.append(self.volume_types["gp2"])
            recommendations.append(self.volume_types["st1"])
            recommendations.append(self.volume_types["sc1"])

        return recommendations

    def get_volume_type_details(self, volume_type: str) -> EbsVolumeRecommendation | None:
        """Get details for a specific volume type"""
        return self.volume_types.get(volume_type)

    def format_recommendations(
        self,
        ebs_optimized_support: str,
        ebs_optimized_info: Dict | None = None,
        max_display: int = 3
    ) -> str:
        """Format recommendations as human-readable text

        Args:
            ebs_optimized_support: EBS optimization support level
            ebs_optimized_info: Optional EBS optimization details
            max_display: Maximum number of recommendations to display (default: 3)

        Returns:
            Formatted recommendation text
        """
        recommendations = self.get_recommendations(ebs_optimized_support, ebs_optimized_info)
        lines = []

        # Add instance EBS capabilities context
        if ebs_optimized_info:
            max_throughput = ebs_optimized_info.get("MaximumThroughputMBps")
            max_bandwidth = ebs_optimized_info.get("MaximumBandwidthMbps")

            if max_bandwidth:
                lines.append(f"Instance EBS Bandwidth: Up to {max_bandwidth} Mbps")
            if max_throughput:
                lines.append(f"Instance EBS Throughput: Up to {max_throughput} MB/s")
            lines.append("")

        lines.append("Recommended EBS Volume Types:")
        lines.append("")

        for i, rec in enumerate(recommendations[:max_display], 1):
            lines.append(f"{i}. {rec.volume_type.upper()} - {rec.description}")
            if rec.iops_range:
                lines.append(f"   IOPS: {rec.iops_range}")
            if rec.throughput_range:
                lines.append(f"   Throughput: {rec.throughput_range}")
            lines.append(f"   Use Cases: {', '.join(rec.use_cases[:2])}")
            if rec.notes:
                lines.append(f"   Note: {rec.notes}")
            lines.append("")

        return "\n".join(lines)
