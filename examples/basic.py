"""
Basic example demonstrating KSEB Client usage.

This example shows the most common use case: getting complete grid capacity
information for a consumer.
"""

import logging
from kseb_client import KSEBClient, KSEBClientError, KSEBValidationError

# Configure logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def example_basic():
    """Basic example: Get grid capacity for a consumer."""
    print("\n" + "="*60)
    print("Basic Example: Get Grid Capacity")
    print("="*60)

    # Initialize the client
    client = KSEBClient()

    # Get consumer details from user input
    consumer_no = input("Enter consumer number: ").strip()
    mobile = input("Enter mobile number: ").strip()

    try:
        # Get complete grid capacity information
        logger.info(f"Fetching grid capacity for {consumer_no}")
        result = client.get_grid_capacity(consumer_no, mobile)

        # Display results
        print(f"\n✓ Grid Capacity Result:")
        print(f"  Section: {result.section.section}")
        print(f"  Consumer: {result.bill.consumer_name}")
        print(f"  DTR: {result.transformer.transformer_name}")
        print(f"  Available Balance: {result.transformer.balance_available} kW")
        print(f"  Division: {result.transformer.division}")
        print(f" Connected Load: {result.bill.connected_load}")
        print(f" Security Deposit: {result.bill.security_deposit}")
        print(f" Net Payable: {result.bill.net_payable}")


    except KSEBValidationError as e:
        print(f"✗ Validation Error: {e}")
    except KSEBClientError as e:
        print(f"✗ SDK Error: {e}")
    except Exception as e:
        print(f"✗ Unexpected Error: {e}")
    finally:
        client.close()


def example_step_by_step():
    """Example: Perform operations step by step."""
    print("\n" + "="*60)
    print("Step-by-Step Example")
    print("="*60)

    # Get consumer details from user input
    consumer_no = input("Enter consumer number: ").strip()
    mobile = input("Enter mobile number: ").strip()

    # Use context manager for automatic cleanup
    with KSEBClient() as client:

        try:
            # Step 1: Get section information
            print("\n1. Fetching section information...")
            section = client.get_section(consumer_no)
            print(f"   ✓ Section: {section.section}")
            print(f"   ✓ Division: {section.division}")
            print(f"   ✓ Email: {section.email}")

            # Step 2: Download bill
            print("\n2. Downloading bill...")
            pdf_bytes = client.download_bill(consumer_no, mobile)
            print(f"   ✓ Bill downloaded ({len(pdf_bytes)} bytes)")

            # Step 3: Parse bill
            print("\n3. Parsing bill...")
            bill = client.parse_bill(pdf_bytes, consumer_no)
            print(f"   ✓ Consumer: {bill.consumer_name}")
            print(f"   ✓ DTR: {bill.dtr}")
            print(f"   ✓ Connected Load: {bill.connected_load}")

            # Step 4: Get transformers
            print("\n4. Fetching transformer list...")
            section_code = consumer_no[2:6]
            transformers = client.get_transformers(section_code)
            print(f"   ✓ Found {len(transformers)} transformers")

            # Step 5: Find specific transformer
            print(f"\n5. Finding transformer: {bill.dtr}...")
            dtr = client.find_transformer(section_code, bill.dtr)
            print(f"   ✓ Transformer: {dtr.transformer_name}")
            print(f"   ✓ Available Balance: {dtr.balance_available} kW")
            print(f"   ✓ Allowed Capacity: {dtr.allowed_cap} kW")

        except KSEBClientError as e:
            print(f"   ✗ Error: {e}")


def example_error_handling():
    """Example: Proper error handling."""
    print("\n" + "="*60)
    print("Error Handling Example")
    print("="*60)

    client = KSEBClient()

    # Test 1: Invalid consumer number
    print("\n1. Testing invalid consumer number...")
    try:
        client.get_section("invalid123")
    except KSEBValidationError as e:
        print(f"   ✓ Caught validation error: {e}")

    # Test 2: Invalid mobile number
    print("\n2. Testing invalid mobile number...")
    try:
        client.get_grid_capacity("1145657015077", "123")
    except KSEBValidationError as e:
        print(f"   ✓ Caught validation error: {e}")

    # Test 3: Invalid credentials (might fail with authentication error)
    print("\n3. Testing with invalid credentials...")
    try:
        client.get_grid_capacity("0000000000000", "9999999999")
    except KSEBClientError as e:
        print(f"   ✓ Caught SDK error: {type(e).__name__}: {e}")

    client.close()


def example_with_caching():
    """Example: Using caching for performance."""
    print("\n" + "="*60)
    print("Caching Example")
    print("="*60)

    # Create client with 30-minute cache TTL
    client = KSEBClient(cache_ttl=1800)

    section_code = "1234"

    try:
        print(f"\n1. First call to get_transformers (will fetch from API)...")
        transformers1 = client.get_transformers(section_code)
        print(f"   ✓ Got {len(transformers1)} transformers")

        print(f"\n2. Second call to get_transformers (will use cache)...")
        transformers2 = client.get_transformers(section_code)
        print(f"   ✓ Got {len(transformers2)} transformers (from cache)")

        print(f"\n3. Third call with use_cache=False (will fetch from API)...")
        transformers3 = client.get_transformers(section_code, use_cache=False)
        print(f"   ✓ Got {len(transformers3)} transformers (fresh from API)")

        print(f"\n4. Clear cache...")
        client.clear_cache()
        print(f"   ✓ Cache cleared")

    except KSEBClientError as e:
        print(f"   ✗ Error: {e}")
    finally:
        client.close()


def example_configuration():
    """Example: Different client configurations."""
    print("\n" + "="*60)
    print("Configuration Example")
    print("="*60)

    # Configuration 1: Default settings
    print("\n1. Default configuration:")
    client1 = KSEBClient()
    print(f"   Timeout: 15s, Retries: 3, Cache TTL: 900s")
    client1.close()

    # Configuration 2: Custom settings (faster retries)
    print("\n2. Fast configuration (low timeout, fewer retries):")
    client2 = KSEBClient(timeout=5, retries=1)
    print(f"   Timeout: 5s, Retries: 1, Cache TTL: 900s")
    client2.close()

    # Configuration 3: Custom settings (robust retries)
    print("\n3. Robust configuration (high timeout, more retries):")
    client3 = KSEBClient(timeout=30, retries=5, backoff_factor=0.5, cache_ttl=3600)
    print(f"   Timeout: 30s, Retries: 5, Cache TTL: 3600s")
    client3.close()


if __name__ == "__main__":
    print("\nKSEB Client Examples")
    print("====================")

    # Run examples (comment out as needed)
    # example_basic()  # Note: Will fail without valid credentials
    example_step_by_step()  # Note: Will fail without valid credentials
    example_error_handling()
    # example_with_caching()  # Note: Will fail without valid credentials
    example_configuration()

    print("\n" + "="*60)
    print("Examples completed!")
    print("="*60 + "\n")
