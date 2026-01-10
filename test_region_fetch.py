"""Test script to verify region comparison and instance fetching"""
import asyncio
import sys
from src.services.async_aws_client import AsyncAWSClient
from src.services.async_pricing_service import AsyncPricingService
from src.models.instance_type import InstanceType


async def test_instance_fetch(instance_type: str, regions: list):
    """Test fetching an instance from multiple regions"""
    print(f"\n🧪 Testing fetch of {instance_type} across {len(regions)} regions...")
    print("=" * 80)

    results = {}

    for region in regions:
        try:
            print(f"\n📍 Testing {region}...")

            async with AsyncAWSClient(region=region, profile=None) as client:
                # Get EC2 client
                async with client.get_ec2_client() as ec2_client:
                    # Fetch instance type
                    response = await ec2_client.describe_instance_types(
                        InstanceTypes=[instance_type]
                    )

                    instance_data = response.get("InstanceTypes", [])

                    if instance_data:
                        # Parse instance
                        instance = InstanceType.from_aws_response(instance_data[0])

                        # Fetch pricing
                        pricing_service = AsyncPricingService(client)
                        on_demand = await pricing_service.get_on_demand_price(instance.instance_type, region)
                        spot_price = await pricing_service.get_spot_price(instance.instance_type, region)

                        # Create pricing info
                        from src.models.instance_type import PricingInfo
                        instance.pricing = PricingInfo(
                            on_demand_price=on_demand,
                            spot_price=spot_price
                        )

                        results[region] = {
                            'found': True,
                            'instance': instance,
                            'on_demand': instance.pricing.on_demand_price if instance.pricing else None,
                            'spot': instance.pricing.spot_price if instance.pricing else None
                        }

                        print(f"  ✅ Found: {instance.instance_type}")
                        print(f"  💰 On-Demand: ${instance.pricing.on_demand_price:.4f}/hr" if instance.pricing and instance.pricing.on_demand_price else "  💰 On-Demand: N/A")
                        print(f"  ⚡ Spot: ${instance.pricing.spot_price:.4f}/hr" if instance.pricing and instance.pricing.spot_price else "  ⚡ Spot: N/A")
                    else:
                        results[region] = {'found': False}
                        print(f"  ❌ Not found in {region}")

        except Exception as e:
            results[region] = {'found': False, 'error': str(e)}
            print(f"  ❌ Error: {str(e)}")

    # Summary
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)

    found_count = sum(1 for r in results.values() if r.get('found'))
    error_count = sum(1 for r in results.values() if 'error' in r)

    print(f"\n✅ Found in: {found_count}/{len(regions)} regions")
    print(f"❌ Errors: {error_count}/{len(regions)} regions")

    if found_count > 0:
        print(f"\n💡 SUCCESS: Instance {instance_type} is accessible via API")

        # Show pricing comparison
        print(f"\n💰 Pricing Comparison:")
        for region, data in results.items():
            if data.get('found'):
                on_demand = data.get('on_demand', 'N/A')
                spot = data.get('spot', 'N/A')
                if isinstance(on_demand, float):
                    print(f"  {region:20} On-Demand: ${on_demand:.4f}/hr" + (f"  Spot: ${spot:.4f}/hr" if isinstance(spot, float) else ""))
    else:
        print(f"\n❌ FAILED: Instance {instance_type} not found in any region")
        print("This could indicate:")
        print("  1. Invalid instance type name")
        print("  2. Instance not available in tested regions")
        print("  3. AWS API access issues")

    return results


async def test_region_list():
    """Test fetching list of regions"""
    print("\n🧪 Testing region list fetch...")
    print("=" * 80)

    try:
        async with AsyncAWSClient(region='us-east-1', profile=None) as client:
            regions = await client.get_accessible_regions()

            print(f"\n✅ Found {len(regions)} accessible regions:")
            for i, region in enumerate(regions[:10], 1):
                print(f"  {i}. {region}")

            if len(regions) > 10:
                print(f"  ... and {len(regions) - 10} more")

            return regions
    except Exception as e:
        print(f"\n❌ Error fetching regions: {e}")
        return []


async def main():
    """Run all tests"""
    print("\n🚀 Region Comparison Test Suite")
    print("=" * 80)

    # Test 1: Fetch regions
    regions = await test_region_list()

    if not regions:
        print("\n❌ Cannot proceed without regions")
        return 1

    # Test 2: Test a common instance across multiple regions
    # Use a subset of popular regions for faster testing
    test_regions = ['us-east-1', 'us-west-2', 'eu-west-1']
    test_instance = 'm5.large'  # Very common instance type

    results = await test_instance_fetch(test_instance, test_regions)

    # Determine success
    found_count = sum(1 for r in results.values() if r.get('found'))

    if found_count >= 2:
        print("\n✅ TEST PASSED: Instance fetching works correctly")
        return 0
    else:
        print("\n❌ TEST FAILED: Instance fetching is broken")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
