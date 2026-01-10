"""Cost optimization service for instance recommendations"""

from typing import List, Optional
from dataclasses import dataclass
import logging

from src.models.instance_type import InstanceType, PricingInfo

logger = logging.getLogger("instancepedia")


@dataclass
class OptimizationRecommendation:
    """Single cost optimization recommendation"""
    recommendation_type: str  # "downsize", "spot", "savings_plan_1yr", "savings_plan_3yr", "ri_1yr", "ri_3yr"
    current_instance: str
    recommended_instance: Optional[str]  # None for pricing model changes
    current_cost_monthly: float
    optimized_cost_monthly: float
    savings_monthly: float
    savings_percentage: float
    reason: str
    considerations: List[str]  # Potential drawbacks or things to consider


@dataclass
class OptimizationReport:
    """Full optimization report for an instance"""
    instance_type: str
    region: str
    current_pricing: PricingInfo
    recommendations: List[OptimizationRecommendation]
    total_potential_savings: float


class OptimizationService:
    """Service for analyzing instances and providing cost optimization recommendations"""

    def __init__(self, instances: List[InstanceType], region: str):
        """
        Initialize optimization service

        Args:
            instances: List of all available instances in the region
            region: AWS region code
        """
        self.instances = instances
        self.region = region

    def analyze_instance(
        self,
        instance: InstanceType,
        usage_pattern: str = "standard"  # standard, burst, continuous
    ) -> OptimizationReport:
        """
        Generate optimization recommendations for an instance

        Args:
            instance: Instance to analyze
            usage_pattern: Expected usage pattern
                - standard: Normal workloads, can tolerate some interruption
                - burst: Bursty workloads, flexible timing
                - continuous: Critical 24/7 workloads, no interruption tolerance

        Returns:
            OptimizationReport with all recommendations
        """
        recommendations = []

        # Only analyze if we have pricing data
        if not instance.pricing or not instance.pricing.on_demand_price:
            logger.debug(f"No pricing data for {instance.instance_type}, skipping analysis")
            return OptimizationReport(
                instance_type=instance.instance_type,
                region=self.region,
                current_pricing=instance.pricing,
                recommendations=[],
                total_potential_savings=0.0
            )

        current_monthly = instance.pricing.on_demand_price * 730

        # 1. Check for spot instance recommendation
        if self._is_spot_suitable(instance, usage_pattern):
            spot_rec = self._create_spot_recommendation(instance, current_monthly)
            if spot_rec:
                recommendations.append(spot_rec)

        # 2. Check for right-sizing opportunities (downsizing)
        downsizing_candidates = self._find_cheaper_alternatives(instance)
        for candidate in downsizing_candidates[:3]:  # Top 3 alternatives
            rec = self._create_downsize_recommendation(instance, candidate, current_monthly)
            if rec:
                recommendations.append(rec)

        # 3. Check for Savings Plan opportunities
        if instance.pricing.savings_plan_1yr_no_upfront:
            sp_1yr_rec = self._create_savings_plan_recommendation(instance, "1yr", current_monthly)
            if sp_1yr_rec:
                recommendations.append(sp_1yr_rec)

        if instance.pricing.savings_plan_3yr_no_upfront:
            sp_3yr_rec = self._create_savings_plan_recommendation(instance, "3yr", current_monthly)
            if sp_3yr_rec:
                recommendations.append(sp_3yr_rec)

        # 4. Check for Reserved Instance opportunities
        ri_recommendations = self._create_ri_recommendations(instance, current_monthly)
        recommendations.extend(ri_recommendations)

        # Sort by savings (highest first)
        recommendations.sort(key=lambda r: r.savings_monthly, reverse=True)

        total_savings = sum(r.savings_monthly for r in recommendations)

        return OptimizationReport(
            instance_type=instance.instance_type,
            region=self.region,
            current_pricing=instance.pricing,
            recommendations=recommendations,
            total_potential_savings=total_savings
        )

    def _find_cheaper_alternatives(
        self,
        instance: InstanceType
    ) -> List[InstanceType]:
        """
        Find instances with similar or better specs but lower price

        Args:
            instance: Instance to compare against

        Returns:
            List of cheaper alternative instances
        """
        candidates = []

        for candidate in self.instances:
            # Skip if no pricing
            if not candidate.pricing or not candidate.pricing.on_demand_price:
                continue

            # Skip if same instance
            if candidate.instance_type == instance.instance_type:
                continue

            # Must be cheaper
            if candidate.pricing.on_demand_price >= instance.pricing.on_demand_price:
                continue

            # Must have sufficient vCPU (allow 1-2 less for downsizing)
            min_vcpu = max(1, instance.vcpu_info.default_vcpus - 2)
            if candidate.vcpu_info.default_vcpus < min_vcpu:
                continue

            # Must have sufficient memory (within 20% is OK for downsizing)
            required_memory = instance.memory_info.size_in_gb * 0.8
            if candidate.memory_info.size_in_gb < required_memory:
                continue

            # Prefer current generation
            if instance.current_generation and not candidate.current_generation:
                continue

            # Calculate value score (price per vCPU per GB RAM)
            try:
                current_value = instance.pricing.on_demand_price / (
                    instance.vcpu_info.default_vcpus * instance.memory_info.size_in_gb
                )
                candidate_value = candidate.pricing.on_demand_price / (
                    candidate.vcpu_info.default_vcpus * candidate.memory_info.size_in_gb
                )

                # Add to candidates with value score
                candidates.append((candidate, candidate_value))
            except (ZeroDivisionError, AttributeError):
                continue

        # Sort by value score (lower is better)
        candidates.sort(key=lambda x: x[1])

        return [c[0] for c in candidates[:5]]  # Top 5 best value alternatives

    def _is_spot_suitable(
        self,
        instance: InstanceType,
        usage_pattern: str
    ) -> bool:
        """
        Determine if spot instances are suitable for this workload

        Args:
            instance: Instance to check
            usage_pattern: Usage pattern (standard, burst, continuous)

        Returns:
            True if spot is recommended
        """
        # Spot not suitable for continuous/critical workloads
        if usage_pattern == "continuous":
            return False

        # Must have spot pricing available
        if not instance.pricing or not instance.pricing.spot_price:
            return False

        # Must have significant savings (>30%)
        savings_pct = instance.pricing.calculate_savings_percentage("spot")
        if not savings_pct or savings_pct < 30:
            return False

        return True

    def _create_spot_recommendation(
        self,
        instance: InstanceType,
        current_monthly: float
    ) -> Optional[OptimizationRecommendation]:
        """Create spot instance recommendation"""
        if not instance.pricing.spot_price:
            return None

        spot_monthly = instance.pricing.spot_price * 730
        savings = current_monthly - spot_monthly
        savings_pct = (savings / current_monthly) * 100

        considerations = [
            "May be interrupted with 2-minute warning",
            "Best for fault-tolerant, flexible workloads",
            "Not suitable for critical or stateful applications",
            "Actual availability varies by AZ and time"
        ]

        return OptimizationRecommendation(
            recommendation_type="spot",
            current_instance=instance.instance_type,
            recommended_instance=None,  # Same instance, different pricing
            current_cost_monthly=current_monthly,
            optimized_cost_monthly=spot_monthly,
            savings_monthly=savings,
            savings_percentage=savings_pct,
            reason=f"Spot price is significantly lower ({savings_pct:.1f}% savings)",
            considerations=considerations
        )

    def _create_downsize_recommendation(
        self,
        current: InstanceType,
        candidate: InstanceType,
        current_monthly: float
    ) -> Optional[OptimizationRecommendation]:
        """Create downsizing recommendation"""
        if not candidate.pricing or not candidate.pricing.on_demand_price:
            return None

        candidate_monthly = candidate.pricing.on_demand_price * 730
        savings = current_monthly - candidate_monthly
        savings_pct = (savings / current_monthly) * 100

        # Build considerations based on differences
        considerations = []

        vcpu_diff = current.vcpu_info.default_vcpus - candidate.vcpu_info.default_vcpus
        if vcpu_diff > 0:
            considerations.append(
                f"{vcpu_diff} fewer vCPU ({candidate.vcpu_info.default_vcpus} vs {current.vcpu_info.default_vcpus})"
            )

        mem_diff = current.memory_info.size_in_gb - candidate.memory_info.size_in_gb
        if mem_diff > 0:
            considerations.append(
                f"{mem_diff:.1f} GB less memory ({candidate.memory_info.size_in_gb:.1f} vs {current.memory_info.size_in_gb:.1f} GB)"
            )

        considerations.append(
            f"Ensure workload doesn't require more than {candidate.vcpu_info.default_vcpus} vCPU "
            f"and {candidate.memory_info.size_in_gb:.1f} GB RAM"
        )

        # Build reason
        reason = f"Similar capabilities at {savings_pct:.1f}% lower cost"

        return OptimizationRecommendation(
            recommendation_type="downsize",
            current_instance=current.instance_type,
            recommended_instance=candidate.instance_type,
            current_cost_monthly=current_monthly,
            optimized_cost_monthly=candidate_monthly,
            savings_monthly=savings,
            savings_percentage=savings_pct,
            reason=reason,
            considerations=considerations
        )

    def _create_savings_plan_recommendation(
        self,
        instance: InstanceType,
        term: str,  # "1yr" or "3yr"
        current_monthly: float
    ) -> Optional[OptimizationRecommendation]:
        """Create savings plan recommendation"""
        if term == "1yr":
            sp_price = instance.pricing.savings_plan_1yr_no_upfront
            term_label = "1-year"
        else:  # "3yr"
            sp_price = instance.pricing.savings_plan_3yr_no_upfront
            term_label = "3-year"

        if not sp_price:
            return None

        sp_monthly = sp_price * 730
        savings = current_monthly - sp_monthly
        savings_pct = (savings / current_monthly) * 100

        # Only recommend if savings >= 10%
        if savings_pct < 10:
            return None

        considerations = [
            f"Requires {term_label} commitment",
            "No upfront payment option",
            "Provides flexibility across instance families",
            "Discount applies automatically to usage"
        ]

        return OptimizationRecommendation(
            recommendation_type=f"savings_plan_{term}",
            current_instance=instance.instance_type,
            recommended_instance=None,
            current_cost_monthly=current_monthly,
            optimized_cost_monthly=sp_monthly,
            savings_monthly=savings,
            savings_percentage=savings_pct,
            reason=f"Significant discount with {term_label} commitment",
            considerations=considerations
        )

    def _create_ri_recommendations(
        self,
        instance: InstanceType,
        current_monthly: float
    ) -> List[OptimizationRecommendation]:
        """Create Reserved Instance recommendations"""
        recommendations = []

        # Define RI options to check
        ri_options = [
            ("ri_1yr", "ri_1yr_partial_upfront", "1-year Partial Upfront RI"),
            ("ri_1yr", "ri_1yr_no_upfront", "1-year No Upfront RI"),
            ("ri_3yr", "ri_3yr_partial_upfront", "3-year Partial Upfront RI"),
            ("ri_3yr", "ri_3yr_no_upfront", "3-year No Upfront RI"),
        ]

        for rec_type, price_attr, label in ri_options:
            ri_price = getattr(instance.pricing, price_attr, None)
            if not ri_price:
                continue

            ri_monthly = ri_price * 730
            savings = current_monthly - ri_monthly
            savings_pct = (savings / current_monthly) * 100

            # Only recommend if savings >= 10%
            if savings_pct < 10:
                continue

            term = "1-year" if "1yr" in rec_type else "3-year"
            payment = "Partial upfront" if "partial" in price_attr else "No upfront"

            considerations = [
                f"Requires {term} commitment",
                f"{payment} payment",
                "Less flexible than Savings Plans",
                "Tied to specific instance type",
                "Effective hourly rate (upfront costs amortized)" if "partial" in price_attr else "Pay monthly"
            ]

            recommendations.append(OptimizationRecommendation(
                recommendation_type=rec_type,
                current_instance=instance.instance_type,
                recommended_instance=None,
                current_cost_monthly=current_monthly,
                optimized_cost_monthly=ri_monthly,
                savings_monthly=savings,
                savings_percentage=savings_pct,
                reason=f"{label} provides {savings_pct:.1f}% discount",
                considerations=considerations
            ))

        return recommendations
