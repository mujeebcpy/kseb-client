"""
Basic example demonstrating KSEB Client usage.

This example shows the most common use case: getting complete grid capacity
information for a consumer.
"""

import logging
from kseb_client import KSEBClient, KSEBClientError, KSEBTurnstileError, KSEBValidationError

# Configure logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def ask_turnstile_token() -> str:
    """Ask for a Turnstile token from the KSEB DTR Capacity page.

    In an app, the token comes from the person completing the Cloudflare check
    on https://wss.kseb.in/selfservices/reCap. Each token works once.
    """
    print("Complete the Cloudflare check on https://wss.kseb.in/selfservices/reCap")
    return input("Turnstile token (cf-turnstile-response): ").strip()


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
        bill_captcha = client.get_bill_captcha()
        with open("kseb_bill_captcha.png", "wb") as captcha_file:
            captcha_file.write(bill_captcha.image)
        print("Solve the captcha in kseb_bill_captcha.png")
        bill_captcha_code = input("Bill captcha: ").strip()

        turnstile_token = ask_turnstile_token()

        logger.info(f"Fetching grid capacity for {consumer_no}")
        result = client.get_grid_capacity(
            consumer_no,
            mobile,
            bill_captcha_code=bill_captcha_code,
            bill_session_id=bill_captcha.session_id,
            turnstile_token=turnstile_token,
        )

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

    except KSEBTurnstileError as e:
        print(f"✗ {e}")
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
            bill_captcha = client.get_bill_captcha()
            bill_captcha_path = "kseb_bill_captcha.png"
            with open(bill_captcha_path, "wb") as captcha_file:
                captcha_file.write(bill_captcha.image)
            print(f"   Solve the captcha in {bill_captcha_path}")
            pdf_bytes = client.download_bill(
                consumer_no,
                mobile,
                captcha_code=input("Captcha: ").strip(),
                session_id=bill_captcha.session_id,
            )
            print(f"   ✓ Bill downloaded ({len(pdf_bytes)} bytes)")

            # Step 3: Parse bill
            print("\n3. Parsing bill...")
            bill = client.parse_bill(pdf_bytes, consumer_no)
            print(f"   ✓ Consumer: {bill.consumer_name}")
            print(f"   ✓ DTR: {bill.dtr}")
            print(f"   ✓ Connected Load: {bill.connected_load}")

            # Step 4: Get the consumer's transformer
            print("\n4. Fetching transformer...")
            dtr = client.get_transformer(
                consumer_no, turnstile_token=ask_turnstile_token(), section_info=section
            )
            print(f"   ✓ Transformer: {dtr.transformer_name}")
            print(f"   ✓ Available Balance: {dtr.balance_available} kW")
            print(f"   ✓ Allowed Capacity: {dtr.allowed_cap} kW")
            print(f"   ✓ As on: {dtr.as_on}")

        except KSEBTurnstileError as e:
            print(f"   ✗ {e}")
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
        client.get_grid_capacity("1145657015077", "123", bill_captcha_code="x", bill_session_id="x", turnstile_token="x")
    except KSEBValidationError as e:
        print(f"   ✓ Caught validation error: {e}")

    # Test 3: Invalid credentials (might fail with authentication error)
    print("\n3. Testing with invalid credentials...")
    try:
        client.get_grid_capacity("0000000000000", "9999999999", bill_captcha_code="x", bill_session_id="x", turnstile_token="x")
    except KSEBClientError as e:
        print(f"   ✓ Caught SDK error: {type(e).__name__}: {e}")

    # Test 4: Rejected Turnstile token
    print("\n4. Testing with an invalid Turnstile token...")
    try:
        client.get_transformer("1145657015077", turnstile_token="invalid")
    except KSEBTurnstileError as e:
        print(f"   ✓ Caught Turnstile error: {e}")

    client.close()


def example_configuration():
    """Example: Different client configurations."""
    print("\n" + "="*60)
    print("Configuration Example")
    print("="*60)

    # Configuration 1: Default settings
    print("\n1. Default configuration:")
    client1 = KSEBClient()
    print(f"   Timeout: 15s, Retries: 3")
    client1.close()

    # Configuration 2: Custom settings (faster retries)
    print("\n2. Fast configuration (low timeout, fewer retries):")
    client2 = KSEBClient(timeout=5, retries=1)
    print(f"   Timeout: 5s, Retries: 1")
    client2.close()

    # Configuration 3: Custom settings (robust retries)
    print("\n3. Robust configuration (high timeout, more retries):")
    client3 = KSEBClient(timeout=30, retries=5, backoff_factor=0.5)
    print(f"   Timeout: 30s, Retries: 5")
    client3.close()


if __name__ == "__main__":
    print("\nKSEB Client Examples")
    print("====================")

    # Run examples (comment out as needed)
    # example_basic()  # Note: Will fail without valid credentials
    example_step_by_step()  # Note: Will fail without valid credentials
    example_error_handling()
    example_configuration()

    print("\n" + "="*60)
    print("Examples completed!")
    print("="*60 + "\n")
